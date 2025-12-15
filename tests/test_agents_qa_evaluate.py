import pytest

from backend.agents import qa_evaluate
from backend.db import Provider


def test_qa_evaluate_creates_explanation_inputs(db_session):
    provider = Provider(
        id=1,
        external_id="1234567890",   # required
        name="Test Provider",       # REQUIRED (fix)
        phone="123",
        address="Old Addr",
        specialty="Cardiology",
        license_no="LIC123",
        license_expiry="2026",
        affiliations=None,
    )
    db_session.add(provider)
    db_session.commit()

    external_data = {
        "candidates": {
            "phone": [
                {"source": "npi", "value": "456"},
                {"source": "hospital", "value": "456"},
            ]
        }
    }

    enrichment = {}

    decisions = qa_evaluate(
        db=db_session,
        provider_id=provider.id,
        external_data=external_data,
        enrichment=enrichment,
    )

    assert "phone" in decisions["explanation_inputs"]

    payload = decisions["explanation_inputs"]["phone"]
    assert payload["field"] == "phone"
    assert payload["chosen_value"] == "456"
