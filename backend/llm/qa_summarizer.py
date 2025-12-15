from typing import Dict, Any
from .gemini_client import call_gemini

def summarize_qa_decision(payload: Dict[str, Any]) -> str:
    prompt = f"""
You are a healthcare data quality analyst.

Summarize the reasoning behind this provider data decision.

Field: {payload["field"]}
Current value: {payload["current_value"]}

Candidate values:
{payload["candidates"]}

Chosen value: {payload["chosen_value"]}
Confidence score: {payload["confidence"]}
Decision: {payload["decision"]}

Explain:
- Why this value was chosen
- How source agreement influenced confidence
- Whether the decision is safe to auto-apply

Keep the explanation concise and professional.
"""
    return call_gemini(prompt)
