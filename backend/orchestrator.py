from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from .db import Provider, ValidationRun
from .agents import (
    DataValidationAgent,
    InformationEnrichmentAgent,
    extract_from_pdf,
    qa_evaluate,
    apply_updates,
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

    validation_agent = DataValidationAgent()
    enrichment_agent = InformationEnrichmentAgent()

    for provider in providers:
        validation = validation_agent.validate_provider(db, provider.id)
        ocr_data = extract_from_pdf(db, provider.id)
        enrichment = enrichment_agent.enrich_provider(db, provider.id)

        serialized_candidates = _serialize_candidates(validation.raw_evidence.get("candidates", {}))
        decisions = qa_evaluate(
            db,
            provider.id,
            {
                "candidates": serialized_candidates,
                "validated_fields": validation.validated_fields,
            },
            enrichment.enriched_fields,
        )
        res = apply_updates(db, provider.id, decisions)
        auto_updates += res["auto_updates"]
        manual_reviews += res["manual_reviews"]

    recompute_pcs_for_all(db)
    recompute_drift_for_all(db)

    run.count_processed = len(providers)
    run.auto_updates = auto_updates
    run.manual_reviews = manual_reviews
    run.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run
