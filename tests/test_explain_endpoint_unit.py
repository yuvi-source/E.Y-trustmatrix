from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_explain_endpoint_mocked(mocker):
    mocker.patch(
        "backend.api.summarize_qa_decision",  # ✅ correct patch target
        return_value="Chosen because trusted sources agree."
    )

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
    assert response.json()["explanation"] == "Chosen because trusted sources agree."
