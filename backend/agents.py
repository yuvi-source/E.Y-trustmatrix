from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pytesseract
from PIL import Image
from sqlalchemy.orm import Session

from .external.npi_client import fetch_npi_data
from .db import (
    Provider,
    Document,
    FieldConfidence,
    ManualReviewItem,
)

# -------------------------------------------------
# Config / Data
# -------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"

SOURCE_PRIORITY = ["npi", "state_board", "hospital", "maps", "original"]

USE_REAL_NPI = os.getenv("USE_REAL_NPI", "false").lower() == "true"


def _load_json(name: str) -> Any:
    path = DATA_DIR / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


NPI_REGISTRY = _load_json("npi_registry.json")
STATE_BOARD = _load_json("state_board.json")
MAPS_DIR = _load_json("maps_directory.json")
HOSPITAL_DIR = _load_json("hospital_directory.json")


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def looks_like_npi(value: str) -> bool:
    return value.isdigit() and len(value) == 10


# -------------------------------------------------
# External Validation
# -------------------------------------------------

def validate_provider(db: Session, provider_id: int) -> Dict[str, Any]:
    provider = db.query(Provider).get(provider_id)
    if not provider:
        return {}

    external_id = provider.external_id

    if USE_REAL_NPI and looks_like_npi(external_id):
        npi = fetch_npi_data(external_id)
    else:
        npi = NPI_REGISTRY.get(external_id, {})

    board = STATE_BOARD.get(external_id, {})
    maps = MAPS_DIR.get(external_id, {})
    hospital = HOSPITAL_DIR.get(external_id, {})

    candidates = {
        "phone": [],
        "address": [],
        "specialty": [],
        "license_no": [],
        "license_expiry": [],
    }

    def add_candidate(field: str, source: str, value: Any):
        if value:
            candidates[field].append({"source": source, "value": value})

    for src_name, src_data in [
        ("npi", npi),
        ("state_board", board),
        ("hospital", hospital),
        ("maps", maps),
    ]:
        add_candidate("phone", src_name, src_data.get("phone"))
        add_candidate("address", src_name, src_data.get("address"))
        add_candidate("specialty", src_name, src_data.get("specialty"))
        add_candidate("license_no", src_name, src_data.get("license_no"))
        add_candidate("license_expiry", src_name, src_data.get("license_expiry"))

    # Original values
    add_candidate("phone", "original", provider.phone)
    add_candidate("address", "original", provider.address)
    add_candidate("specialty", "original", provider.specialty)
    add_candidate("license_no", "original", provider.license_no)
    add_candidate("license_expiry", "original", provider.license_expiry)

    return {
        "provider_id": provider_id,
        "candidates": candidates,
    }


# -------------------------------------------------
# OCR
# -------------------------------------------------

def extract_from_pdf(db: Session, provider_id: int) -> Dict[str, Any]:
    doc = (
        db.query(Document)
        .filter(Document.provider_id == provider_id, Document.doc_type == "license")
        .first()
    )

    if not doc or not doc.path:
        return {}

    img_path = Path(doc.path)
    if not img_path.exists():
        return {}

    image = Image.open(img_path)

    try:
        ocr_result = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT
        )
        text = " ".join(ocr_result.get("text", []))
        confidences = [
            float(c) for c in ocr_result.get("conf", []) if c not in ("-1", -1)
        ]
        ocr_conf = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
    except Exception:
        text = "OCR Unavailable"
        ocr_conf = 0.7

    doc.ocr_text = text
    doc.ocr_confidence = ocr_conf
    db.commit()

    return {
        "license_no": None,
        "expiry_date": None,
        "name": None,
        "ocr_confidence": ocr_conf,
    }


# -------------------------------------------------
# Enrichment
# -------------------------------------------------

def enrich_provider(
    db: Session,
    provider_id: int,
    external_data: Dict[str, Any],
    ocr_data: Dict[str, Any],
) -> Dict[str, Any]:
    provider = db.query(Provider).get(provider_id)
    enrichment: Dict[str, Any] = {}

    if not provider.affiliations:
        enrichment["affiliations"] = "Synthetic Hospital Group"

    if ocr_data.get("license_no") and not provider.license_no:
        enrichment["license_no"] = ocr_data["license_no"]

    return enrichment


# -------------------------------------------------
# Confidence Engine (NO LLM)
# -------------------------------------------------

def _confidence_for_candidates(candidates: list) -> Dict[str, Any]:
    if not candidates:
        return {"best": None, "confidence": 0.0, "sources": []}

    scores = {
        "npi": 1.0,
        "state_board": 0.9,
        "hospital": 0.7,
        "maps": 0.5,
        "original": 0.3,
    }

    grouped: Dict[str, Dict[str, Any]] = {}

    for c in candidates:
        key = c["value"]
        if key not in grouped:
            grouped[key] = {"value": key, "sources": [], "score": 0.0}
        grouped[key]["sources"].append(c["source"])
        grouped[key]["score"] += scores.get(c["source"], 0.2)

    best = max(grouped.values(), key=lambda x: x["score"])
    max_possible = sum(
        sorted(scores.values(), reverse=True)[: len(best["sources"])] or [1.0]
    )
    confidence = min(1.0, best["score"] / max_possible)

    return {
        "best": best["value"],
        "confidence": confidence,
        "sources": best["sources"],
    }


# -------------------------------------------------
# QA Evaluation (LLM-FREE)
# -------------------------------------------------

def qa_evaluate(
    db: Session,
    provider_id: int,
    external_data: Dict[str, Any],
    enrichment: Dict[str, Any],
):
    provider = db.query(Provider).get(provider_id)
    candidates = external_data.get("candidates", {}) if external_data else {}

    decisions = {
        "auto_updates": {},
        "manual_reviews": [],
        "explanation_inputs": {},  # 👈 store inputs, NOT LLM text
    }

    threshold = 0.75

    for field in [
        "phone",
        "address",
        "specialty",
        "license_no",
        "license_expiry",
    ]:
        field_candidates = candidates.get(field, [])
        result = _confidence_for_candidates(field_candidates)

        best = result["best"]
        conf = result["confidence"]
        sources = result["sources"]

        db.add(
            FieldConfidence(
                provider_id=provider_id,
                field_name=field,
                confidence=conf,
                sources=sources,
            )
        )

        current_value = getattr(provider, field)

        if best is None or best == current_value:
            continue

        explanation_payload = {
            "field": field,
            "current_value": current_value,
            "candidates": field_candidates,
            "chosen_value": best,
            "confidence": conf,
        }

        if conf >= threshold:
            decisions["auto_updates"][field] = {
                "from": current_value,
                "to": best,
                "confidence": conf,
            }
            explanation_payload["decision"] = "auto_update"
        else:
            item = ManualReviewItem(
                provider_id=provider_id,
                field_name=field,
                current_value=current_value,
                suggested_value=best,
                reason=f"low confidence ({conf:.2f})",
            )
            db.add(item)
            decisions["manual_reviews"].append(item)
            explanation_payload["decision"] = "manual_review"

        decisions["explanation_inputs"][field] = explanation_payload

    # Enrichment (still deterministic)
    if enrichment.get("affiliations") and not provider.affiliations:
        decisions["auto_updates"]["affiliations"] = {
            "from": provider.affiliations,
            "to": enrichment["affiliations"],
            "confidence": 0.8,
        }
        decisions["explanation_inputs"]["affiliations"] = {
            "field": "affiliations",
            "current_value": provider.affiliations,
            "candidates": [
                {"source": "enrichment_agent", "value": enrichment["affiliations"]}
            ],
            "chosen_value": enrichment["affiliations"],
            "confidence": 0.8,
            "decision": "auto_update",
        }

    db.commit()
    return decisions


# -------------------------------------------------
# Apply Updates
# -------------------------------------------------

def apply_updates(db: Session, provider_id: int, decisions):
    from .db import AuditLog

    provider = db.query(Provider).get(provider_id)
    auto_updates = 0
    manual_reviews = len(decisions.get("manual_reviews", []))

    for field, info in decisions.get("auto_updates", {}).items():
        old = info["from"]
        new = info["to"]

        setattr(provider, field, new)
        provider.last_changed_at = datetime.utcnow()
        provider.last_verified_at = datetime.utcnow()

        db.add(
            AuditLog(
                provider_id=provider_id,
                field_name=field,
                old_value=str(old) if old is not None else None,
                new_value=str(new) if new is not None else None,
                action="auto_update",
                actor="validation_agent",
            )
        )
        auto_updates += 1

    db.commit()
    return {
        "auto_updates": auto_updates,
        "manual_reviews": manual_reviews,
    }
