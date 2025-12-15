from datetime import datetime, timedelta

from backend.pcs_drift import _compute_fr, _compute_st, compute_drift
from backend.db import Provider, ProviderScore


def test_freshness_scores():
    now = datetime.utcnow()
    p = Provider(name="Test", external_id="T1")
    p.last_verified_at = now
    assert _compute_fr(p) == 1.0

    p.last_verified_at = now - timedelta(days=60)
    assert _compute_fr(p) == 0.8

    p.last_verified_at = now - timedelta(days=120)
    assert _compute_fr(p) == 0.5


def test_stability_scores():
    now = datetime.utcnow()
    p = Provider(name="Test", external_id="T1")
    p.last_changed_at = now - timedelta(days=10)
    assert _compute_st(p) == 0.3

    p.last_changed_at = now - timedelta(days=40)
    assert _compute_st(p) == 0.6

    p.last_changed_at = now - timedelta(days=100)
    assert _compute_st(p) == 0.8


def test_drift_bucket_low_medium_high(db_session):
    p = Provider(name="Test", external_id="T1")
    db_session.add(p)
    db_session.commit()

    score = ProviderScore(
        provider_id=p.id,
        pcs=90,
        srm=1,
        fr=1,
        st=1,
        mb=1,
        dq=1,
        rp=1,
        lh=1,
        ha=1,
        band="green",
    )
    db_session.add(score)
    db_session.commit()

    s, bucket, days = compute_drift(db_session, p)

    assert bucket in {"Low", "Medium", "High"}
