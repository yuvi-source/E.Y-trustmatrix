import os
import pytest
from backend.llm.qa_summarizer import summarize_qa_decision

@pytest.mark.integration
def test_qa_summarizer_real_gemini():
    assert os.getenv("GEMINI_API_KEY") is not None, "GEMINI_API_KEY not loaded"

    payload = {
        "field": "phone",
        "current_value": "123",
        "candidates": [
            {"source": "npi", "value": "456"},
            {"source": "hospital", "value": "456"},
        ],
        "chosen_value": "456",
        "confidence": 0.9,
        "decision": "auto_update",
    }

    result = summarize_qa_decision(payload)

    assert isinstance(result, str)
    assert len(result) > 10
