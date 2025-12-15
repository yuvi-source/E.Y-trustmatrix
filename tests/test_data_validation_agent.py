import json

from backend.agents.data_validation_agent import DataValidationAgent
from backend.db import Provider


def test_data_validation_agent_returns_validated_fields(db_session, monkeypatch):
    provider = Provider(
        external_id="X123",
        name="Dr. Jane Doe",
        phone="555-0001",
        address="123 Baker St",
        specialty="Dermatologist",
    )
    db_session.add(provider)
    db_session.commit()

    def fake_call_gemini(prompt: str) -> str:
        return json.dumps(
            {
                "value": "555-0001",
                "confidence": 0.92,
                "sources": ["original"],
            }
        )

    monkeypatch.setattr("backend.agents.data_validation_agent.call_gemini", fake_call_gemini)

    agent = DataValidationAgent(use_live_npi=False)
    result = agent.validate_provider(db_session, provider.id)

    assert result.provider_id == provider.id
    assert "phone" in result.validated_fields
    assert result.validated_fields["phone"]["value"] == "555-0001"
    assert result.validated_fields["phone"]["confidence"] == 0.92

