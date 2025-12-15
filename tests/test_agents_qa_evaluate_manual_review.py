from backend.agents import qa_evaluate
from backend.db import Provider


def test_qa_evaluate_manual_review_path(db_session):
    provider = Provider(
        id=1,
        external_id="9999999999",
        name="Test Provider",
        phone="111",
        address="Addr",
        specialty="Cardiology",
        license_no="LIC1",
        license_expiry="2026",
    )
    db_session.add(provider)
    db_session.commit()

    # Low-confidence candidates (different values)
    external_data = {
        "candidates": {
            "phone": [
                {"source": "maps", "value": "222"},
                {"source": "original", "value": "111"},
            ]
        }
    }

    decisions = qa_evaluate(
        db=db_session,
        provider_id=provider.id,
        external_data=external_data,
        enrichment={},
    )

    assert len(decisions["manual_reviews"]) == 1
    assert "phone" in decisions["explanation_inputs"]

    payload = decisions["explanation_inputs"]["phone"]
    assert payload["decision"] == "manual_review"
    assert payload["chosen_value"] == "222"
