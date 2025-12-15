from backend.llm.qa_summarizer import summarize_qa_decision

def test_qa_summarizer_prompt_structure(mocker):
    mocker.patch(
        "backend.llm.qa_summarizer.call_gemini",
        return_value="Chosen because multiple reliable sources agree."
    )

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

    assert "Chosen because" in result
