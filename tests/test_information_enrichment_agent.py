import json

from backend.agents.information_enrichment_agent import InformationEnrichmentAgent
from backend.db import Provider


def test_information_enrichment_agent_extracts_fields(db_session, monkeypatch):
    provider = Provider(
        external_id="H001",
        name="Dr. John Smith",
        specialty="Cardiology",
    )
    db_session.add(provider)
    db_session.commit()

    def fake_call_gemini(prompt: str) -> str:
        return json.dumps(
            {
                "certifications": ["Board Certified Cardiology"],
                "affiliations": ["City Hospital"],
                "education": "Harvard Medical School",
                "secondary_specialties": ["Interventional Cardiology"],
                "summary": "Experienced cardiologist with interventional focus.",
            }
        )

    monkeypatch.setattr(
        "backend.agents.information_enrichment_agent.call_gemini", fake_call_gemini
    )

    agent = InformationEnrichmentAgent()
    agent.llm_enabled = True  # Enable LLM so the mocked call_gemini is used
    result = agent.enrich_provider(db_session, provider.id)

    assert result.provider_id == provider.id
    assert result.enriched_fields["education"] == "Harvard Medical School"
    assert "City Hospital" in result.enriched_fields["affiliations"]

