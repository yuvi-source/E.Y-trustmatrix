from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db, ValidationRun, ProviderScore, DriftScore

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(db: Session = Depends(get_db)):
    latest = (
        db.query(ValidationRun)
        .order_by(ValidationRun.started_at.desc())
        .first()
    )
    
    # Use SQL aggregation instead of loading all scores
    total_pcs = db.query(func.count(ProviderScore.id)).scalar() or 0
    avg_pcs = db.query(func.avg(ProviderScore.pcs)).scalar() if total_pcs else None

    drift_rows = db.query(DriftScore).all()
    drift_dist = {"Low": 0, "Medium": 0, "High": 0}
    for d in drift_rows:
        if d.bucket in drift_dist:
            drift_dist[d.bucket] += 1

    # PCS Distribution - use SQL for efficiency
    pcs_dist = {"0-50": 0, "50-70": 0, "70-90": 0, "90-100": 0}
    pcs_dist["0-50"] = db.query(func.count(ProviderScore.id)).filter(ProviderScore.pcs < 50).scalar() or 0
    pcs_dist["50-70"] = db.query(func.count(ProviderScore.id)).filter(ProviderScore.pcs >= 50, ProviderScore.pcs < 70).scalar() or 0
    pcs_dist["70-90"] = db.query(func.count(ProviderScore.id)).filter(ProviderScore.pcs >= 70, ProviderScore.pcs < 90).scalar() or 0
    pcs_dist["90-100"] = db.query(func.count(ProviderScore.id)).filter(ProviderScore.pcs >= 90).scalar() or 0

    # Trend (Last 5 runs)
    last_runs = (
        db.query(ValidationRun)
        .order_by(ValidationRun.started_at.desc())
        .limit(5)
        .all()
    )
    trend = [
        {
            "id": r.id,
            "date": r.started_at.strftime("%Y-%m-%d"),
            "auto_updates": r.auto_updates,
            "manual_reviews": r.manual_reviews
        }
        for r in reversed(last_runs)
    ]

    return {
        "latest_run": {
            "id": latest.id if latest else None,
            "type": latest.run_type if latest else None,
            "count_processed": latest.count_processed if latest else 0,
            "auto_updates": latest.auto_updates if latest else 0,
            "manual_reviews": latest.manual_reviews if latest else 0,
            "started_at": latest.started_at if latest else None,
            "finished_at": latest.finished_at if latest else None,
        },
        "avg_pcs": avg_pcs,
        "drift_distribution": drift_dist,
        "pcs_distribution": pcs_dist,
        "trend": trend
    }
