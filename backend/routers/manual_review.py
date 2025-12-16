from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, ManualReviewItem, Provider, AuditLog

router = APIRouter(prefix="/manual-review", tags=["manual_review"])


@router.get("")
async def list_manual_review(db: Session = Depends(get_db)):
    items = db.query(ManualReviewItem).order_by(ManualReviewItem.created_at.desc()).all()
    return [
        {
            "id": i.id,
            "provider_id": i.provider_id,
            "field_name": i.field_name,
            "current_value": i.current_value,
            "suggested_value": i.suggested_value,
            "reason": i.reason,
            "status": i.status,
            "created_at": i.created_at,
        }
        for i in items
    ]


@router.post("/{item_id}/approve")
async def approve_manual_review(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ManualReviewItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    provider = db.get(Provider, item.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    old = getattr(provider, item.field_name)
    setattr(provider, item.field_name, item.suggested_value)
    item.status = "approved"

    log = AuditLog(
        provider_id=provider.id,
        field_name=item.field_name,
        old_value=str(old) if old is not None else None,
        new_value=str(item.suggested_value) if item.suggested_value is not None else None,
        action="manual_approve",
        actor="human_reviewer",
    )
    db.add(log)
    db.commit()

    return {"status": "ok"}


@router.post("/{item_id}/override")
async def override_manual_review(item_id: int, value: str, db: Session = Depends(get_db)):
    item = db.get(ManualReviewItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    provider = db.get(Provider, item.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    old = getattr(provider, item.field_name)
    setattr(provider, item.field_name, value)
    item.status = "overridden"

    log = AuditLog(
        provider_id=provider.id,
        field_name=item.field_name,
        old_value=str(old) if old is not None else None,
        new_value=str(value) if value is not None else None,
        action="manual_override",
        actor="human_reviewer",
    )
    db.add(log)
    db.commit()

    return {"status": "ok"}


@router.post("/{item_id}/reject")
async def reject_manual_review(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ManualReviewItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Rejecting means we keep the current value (or do nothing) and mark as rejected
    item.status = "rejected"
    
    log = AuditLog(
        provider_id=item.provider_id,
        field_name=item.field_name,
        old_value=item.current_value,
        new_value=item.current_value, # No change
        action="manual_reject",
        actor="human_reviewer",
    )
    db.add(log)
    db.commit()

    return {"status": "ok"}
