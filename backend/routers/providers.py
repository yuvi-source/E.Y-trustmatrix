from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import (
    get_db,
    Provider,
    ProviderScore,
    DriftScore,
    FieldConfidence,
    AuditLog,
    Document,
)
from ..agents import InformationEnrichmentAgent

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/{provider_id}/ocr")
async def get_provider_ocr(provider_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.provider_id == provider_id).first()
    if not doc:
        return {"exists": False}
    return {
        "exists": True,
        "doc_type": doc.doc_type,
        "ocr_text": doc.ocr_text,
        "ocr_confidence": doc.ocr_confidence,
        "path": doc.path
    }


@router.get("/{provider_id}/details")
async def get_provider_details(provider_id: int, db: Session = Depends(get_db)):
    # This endpoint aggregates everything for the detail page
    provider = db.query(Provider).get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    score = db.query(ProviderScore).filter(ProviderScore.provider_id == provider.id).first()
    drift = db.query(DriftScore).filter(DriftScore.provider_id == provider.id).first()
    
    # Validation data from FieldConfidence records
    confs = db.query(FieldConfidence).filter(FieldConfidence.provider_id == provider.id).all()
    validation_data = {}
    for c in confs:
        validation_data[c.field_name] = {
            "confidence": c.confidence,
            "sources": c.sources  # list of source names like ["npi", "maps"]
        }

    # On-demand enrichment summary (non-persistent) to show in UI
    enrichment_agent = InformationEnrichmentAgent()
    enrichment_result = enrichment_agent.enrich_provider(db, provider.id)
    enrichment_payload = {
        "summary": enrichment_result.enriched_fields.get("summary"),
        "certifications": enrichment_result.enriched_fields.get("certifications"),
        "affiliations": enrichment_result.enriched_fields.get("affiliations"),
        "education": enrichment_result.enriched_fields.get("education"),
        "secondary_specialties": enrichment_result.enriched_fields.get("secondary_specialties"),
    }

    return {
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "phone": provider.phone,
            "address": provider.address,
            "specialty": provider.specialty,
            "license_no": provider.license_no,
            "license_expiry": provider.license_expiry,
        },
        "validation": validation_data,
        "pcs": {
            "score": score.pcs if score else 0,
            "band": score.band if score else "N/A",
            "components": {
                "srm": score.srm if score else 0,
                "fr": score.fr if score else 0,
                "st": score.st if score else 0,
                "mb": score.mb if score else 0,
                "dq": score.dq if score else 0,
                "rp": score.rp if score else 0,
                "lh": score.lh if score else 0,
                "ha": score.ha if score else 0,
            }
        } if score else None,
        "drift": {
            "score": drift.score if drift else 0,
            "bucket": drift.bucket if drift else "Low",
            "explanation": "High drift detected due to license expiry proximity." if drift and drift.bucket == "High" else "Stable data patterns."
        } if drift else None,
        "enrichment": enrichment_payload,
    }


@router.get("")
def list_providers(db: Session = Depends(get_db)):
    rows = (
        db.query(Provider, ProviderScore, DriftScore)
        .outerjoin(ProviderScore, ProviderScore.provider_id == Provider.id)
        .outerjoin(DriftScore, DriftScore.provider_id == Provider.id)
        .all()
    )
    return [
        {
            "id": provider.id,
            "external_id": provider.external_id,
            "name": provider.name,
            "specialty": provider.specialty,
            "phone": provider.phone,
            "address": provider.address,
            "pcs": score.pcs if score else None,
            "pcs_band": score.band if score else None,
            "drift_score": drift.score if drift else None,
            "drift_bucket": drift.bucket if drift else None,
        }
        for (provider, score, drift) in rows
    ]


@router.get("/{provider_id}")
async def get_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(Provider).get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    score = db.query(ProviderScore).filter(ProviderScore.provider_id == provider.id).first()
    drift = db.query(DriftScore).filter(DriftScore.provider_id == provider.id).first()
    logs = db.query(AuditLog).filter(AuditLog.provider_id == provider.id).order_by(AuditLog.created_at.desc()).all()
    return {
        "id": provider.id,
        "external_id": provider.external_id,
        "name": provider.name,
        "phone": provider.phone,
        "address": provider.address,
        "specialty": provider.specialty,
        "license_no": provider.license_no,
        "license_expiry": provider.license_expiry,
        "affiliations": provider.affiliations,
        "last_verified_at": provider.last_verified_at,
        "score": {
            "pcs": score.pcs if score else None,
            "band": score.band if score else None,
            "srm": score.srm if score else None,
            "fr": score.fr if score else None,
            "st": score.st if score else None,
            "mb": score.mb if score else None,
            "dq": score.dq if score else None,
            "rp": score.rp if score else None,
            "lh": score.lh if score else None,
            "ha": score.ha if score else None,
        } if score else None,
        "drift": {
            "score": drift.score if drift else None,
            "bucket": drift.bucket if drift else None,
            "recommended_next_check_days": drift.recommended_next_check_days if drift else None,
        } if drift else None,
        "audit_log": [
            {
                "field_name": l.field_name,
                "old_value": l.old_value,
                "new_value": l.new_value,
                "action": l.action,
                "actor": l.actor,
                "created_at": l.created_at,
            }
            for l in logs
        ],
    }


@router.get("/{provider_id}/qa")
async def get_provider_qa(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(Provider).get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    confs = (
        db.query(FieldConfidence)
        .filter(FieldConfidence.provider_id == provider.id)
        .order_by(FieldConfidence.created_at.desc())
        .all()
    )

    return [
        {
            "field_name": c.field_name,
            "confidence": c.confidence,
            "sources": c.sources,
            "created_at": c.created_at,
        }
        for c in confs
    ]
