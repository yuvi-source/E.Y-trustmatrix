from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..orchestrator import run_batch

router = APIRouter(prefix="/run-batch", tags=["batch"])


@router.post("")
def run_batch_endpoint(type: str = "daily", db: Session = Depends(get_db)):
    run = run_batch(db, batch_type=type)
    return {
        "id": run.id,
        "type": run.run_type,
        "count_processed": run.count_processed,
        "auto_updates": run.auto_updates,
        "manual_reviews": run.manual_reviews,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }
