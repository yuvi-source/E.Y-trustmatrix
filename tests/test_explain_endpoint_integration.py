import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


@pytest.mark.integration
def test_explain_endpoint_real_gemini():
    payload = {
        "field": "phone",
        "current_value": "123",
        "candidates": [
            {"source": "npi", "value": "456"},
            {"source": "hospital", "value": "456"},
        ],
        "chosen_value": "456",
        "confidence": 0.92,
        "decision": "auto_update",
    }

    response = client.post("/explain", json=payload)

    assert response.status_code == 200
    explanation = response.json()["explanation"]

    assert isinstance(explanation, str)
    assert len(explanation) > 20
