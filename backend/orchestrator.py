from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from .db import Provider, ValidationRun
from .agents import (
    extract_from_pdf,
    qa_evaluate,
    apply_updates,
    validate_provider,
)
from .pcs_drift import recompute_pcs_for_all, recompute_drift_for_all


BatchType = Literal["daily", "weekly", "onboarding"]


def _serialize_candidates(candidates):
    """Convert Candidate objects (from LLM agent) to plain dicts for legacy QA."""
    if not candidates:
        return {}
    serialized = {}
    for field, items in candidates.items():
        serialized[field] = []
        for c in items:
            if isinstance(c, dict):
                serialized[field].append(c)
            else:
                serialized[field].append({"value": getattr(c, "value", None), "source": getattr(c, "source", None)})
    return serialized


def run_batch(db: Session, batch_type: BatchType = "daily", limit: int = 200) -> ValidationRun:
    run = ValidationRun(run_type=batch_type, started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    db.refresh(run)

    providers = (
        db.query(Provider)
        .order_by(Provider.last_verified_at.is_(None), Provider.last_verified_at)
        .limit(limit)
        .all()
    )

    auto_updates = 0
    manual_reviews = 0

    processed = 0

    try:
        for provider in providers:
            try:
                external = validate_provider(db, provider.id)
                _ = extract_from_pdf(db, provider.id)

                # Keep batch deterministic and responsive: enrichment is on-demand in the detail API.
                enrichment_fields = {}

                decisions = qa_evaluate(
                    db,
                    provider.id,
                    {
                        "candidates": external.get("candidates", {}) if external else {},
                        "validated_fields": {},
                    },
                    enrichment_fields,
                )
                res = apply_updates(db, provider.id, decisions)
                auto_updates += res["auto_updates"]
                manual_reviews += res["manual_reviews"]
                processed += 1
            except Exception:
                # Skip provider-level failures but keep the batch run alive.
                db.rollback()

        recompute_pcs_for_all(db)
        recompute_drift_for_all(db)

        run.count_processed = processed
        run.auto_updates = auto_updates
        run.manual_reviews = manual_reviews
        run.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(run)
        return run
    except Exception:
        # Ensure the run is marked finished even if a fatal error occurs.
        db.rollback()
        run.count_processed = processed
        run.auto_updates = auto_updates
        run.manual_reviews = manual_reviews
        run.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(run)
        return run
