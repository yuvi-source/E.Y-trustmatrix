from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy.orm import Session

from .db import Provider, ProviderScore, DriftScore, FieldConfidence


def _compute_srm(db: Session, provider: Provider) -> float:
    confs = db.query(FieldConfidence).filter(FieldConfidence.provider_id == provider.id).all()
    if not confs:
        return 0.5
    avg_conf = sum(c.confidence for c in confs) / len(confs)
    return float(avg_conf)


def _compute_fr(provider: Provider) -> float:
    if not provider.last_verified_at:
        return 0.3
    days = (datetime.now(timezone.utc) - provider.last_verified_at.replace(tzinfo=timezone.utc)).days
    if days <= 30:
        return 1.0
    if days <= 90:
        return 0.8
    if days <= 180:
        return 0.5
    return 0.2


def _compute_st(provider: Provider) -> float:
    if not provider.last_changed_at:
        return 1.0
    days = (datetime.now(timezone.utc) - provider.last_changed_at.replace(tzinfo=timezone.utc)).days
    if days > 180:
        return 1.0
    if days > 90:
        return 0.8
    if days > 30:
        return 0.6
    return 0.3


def _compute_mb(db: Session, provider: Provider) -> float:
    confs = db.query(FieldConfidence).filter(FieldConfidence.provider_id == provider.id).all()
    low = len([c for c in confs if c.confidence < 0.7])
    if low == 0:
        return 1.0
    if low <= 2:
        return 0.7
    if low <= 4:
        return 0.4
    return 0.1


def _compute_dq(db: Session, provider: Provider) -> float:
    from .db import Document

    docs = db.query(Document).filter(Document.provider_id == provider.id).all()
    if not docs:
        return 0.5
    avg = sum((d.ocr_confidence or 0.5) for d in docs) / len(docs)
    return max(0.3, min(1.0, float(avg)))


def _compute_rp(provider: Provider) -> float:
    return 0.5


def _compute_lh(provider: Provider) -> float:
    if not provider.license_expiry:
        return 0.4
    try:
        expiry = datetime.strptime(provider.license_expiry, "%Y-%m-%d")
    except ValueError:
        return 0.4
    days = (expiry - datetime.now(timezone.utc).replace(tzinfo=None)).days
    if days >= 60:
        return 1.0
    if days >= 30:
        return 0.6
    if days >= 0:
        return 0.4
    return 0.0


def _compute_ha(db: Session, provider: Provider) -> float:
    return 0.8


def compute_pcs(db: Session, provider: Provider) -> Tuple[float, dict]:
    srm = _compute_srm(db, provider)
    fr = _compute_fr(provider)
    st = _compute_st(provider)
    mb = _compute_mb(db, provider)
    dq = _compute_dq(db, provider)
    rp = _compute_rp(provider)
    lh = _compute_lh(provider)
    ha = _compute_ha(db, provider)

    pcs = 100.0 * (
        0.25 * srm
        + 0.15 * fr
        + 0.10 * st
        + 0.15 * mb
        + 0.10 * dq
        + 0.10 * rp
        + 0.10 * lh
        + 0.05 * ha
    )

    if pcs >= 85:
        band = "green"
    elif pcs >= 70:
        band = "amber"
    else:
        band = "red"

    subs = {
        "srm": srm,
        "fr": fr,
        "st": st,
        "mb": mb,
        "dq": dq,
        "rp": rp,
        "lh": lh,
        "ha": ha,
        "pcs": pcs,
        "band": band,
    }
    return pcs, subs


def recompute_pcs_for_all(db: Session) -> None:
    providers = db.query(Provider).all()
    for p in providers:
        pcs, subs = compute_pcs(db, p)
        score = db.query(ProviderScore).filter(ProviderScore.provider_id == p.id).first()
        if not score:
            score = ProviderScore(provider_id=p.id)
            db.add(score)
        score.pcs = pcs
        score.srm = subs["srm"]
        score.fr = subs["fr"]
        score.st = subs["st"]
        score.mb = subs["mb"]
        score.dq = subs["dq"]
        score.rp = subs["rp"]
        score.lh = subs["lh"]
        score.ha = subs["ha"]
        score.band = subs["band"]
    db.commit()


def compute_drift(db: Session, provider: Provider) -> Tuple[float, str, int]:
    # Base drift risk; will be modulated by recent changes, license horizon, and PCS
    base = 0.2

    if provider.last_changed_at:
        days = (datetime.now(timezone.utc) - provider.last_changed_at.replace(tzinfo=timezone.utc)).days
        if days < 30:
            base += 0.35
        elif days < 90:
            base += 0.25

    if provider.license_expiry:
        try:
            expiry = datetime.strptime(provider.license_expiry, "%Y-%m-%d")
            days_to_expiry = (expiry - datetime.now(timezone.utc).replace(tzinfo=None)).days
            if days_to_expiry < 0:
                base += 0.35
            elif days_to_expiry < 30:
                base += 0.25
        except ValueError:
            pass

    score_row = db.query(ProviderScore).filter(ProviderScore.provider_id == provider.id).first()
    pcs = score_row.pcs if score_row else 70.0
    if pcs < 50:
        base += 0.25
    elif pcs < 70:
        base += 0.15

    base = max(0.0, min(1.0, base))

    if base < 0.33:
        bucket = "Low"
        days = 30
    elif base < 0.66:
        bucket = "Medium"
        days = 14
    else:
        bucket = "High"
        days = 7

    return base, bucket, days


def recompute_drift_for_all(db: Session) -> None:
    providers = db.query(Provider).all()
    for p in providers:
        score, bucket, days = compute_drift(db, p)
        row = db.query(DriftScore).filter(DriftScore.provider_id == p.id).first()
        if not row:
            row = DriftScore(provider_id=p.id)
            db.add(row)
        row.score = score
        row.bucket = bucket
        row.recommended_next_check_days = days
    db.commit()
