from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db, ValidationRun, ProviderScore, DriftScore

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    latest = (
        db.query(ValidationRun)
        .order_by(ValidationRun.started_at.desc())
        .first()
    )
    total_pcs = db.query(func.count(ProviderScore.id)).scalar() or 0
    avg_pcs = db.query(func.avg(ProviderScore.pcs)).scalar() if total_pcs else None

    drift_dist = {"Low": 0, "Medium": 0, "High": 0}
    drift_counts = db.query(DriftScore.bucket, func.count(DriftScore.id)).group_by(DriftScore.bucket).all()
    for bucket, count in drift_counts:
        if bucket in drift_dist:
            drift_dist[bucket] = count

    # PCS Distribution
    pcs_scores = [row[0] for row in db.query(ProviderScore.pcs).all()]
    pcs_dist = {"0-50": 0, "50-70": 0, "70-90": 0, "90-100": 0}
    for score in pcs_scores:
        if score < 50:
            pcs_dist["0-50"] += 1
        elif score < 70:
            pcs_dist["50-70"] += 1
        elif score < 90:
            pcs_dist["70-90"] += 1
        else:
            pcs_dist["90-100"] += 1

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
