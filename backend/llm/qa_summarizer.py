from typing import Dict, Any
import os

def summarize_qa_decision(payload: Dict[str, Any]) -> str:
    # Check if Gemini API key is configured
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here" or api_key.startswith("your_"):
        # Fallback: Generate a rule-based explanation
        print("[INFO] Using fallback explanation (no valid API key)")
        return _generate_fallback_explanation(payload)
    
    try:
        from .gemini_client import call_gemini, QuotaExceededError
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
        result = call_gemini(prompt)
        return result
    except QuotaExceededError:
        # Silently fallback when quota is exceeded
        return _generate_fallback_explanation(payload)
    except Exception as e:
        # Only log non-quota errors
        print(f"[WARN] Gemini API error, using fallback: {type(e).__name__}")
        return _generate_fallback_explanation(payload)

def _generate_fallback_explanation(payload: Dict[str, Any]) -> str:
    field = payload["field"]
    confidence = payload["confidence"]
    decision = payload["decision"]
    chosen = payload["chosen_value"]
    current = payload["current_value"]
    
    if decision == "manual_review":
        return (f"The {field} field requires manual review due to low confidence ({confidence:.0%}). "
                f"The system suggests changing from '{current}' to '{chosen}', but this needs "
                f"human verification due to conflicting data sources or insufficient source agreement.")
    elif decision == "auto_update":
        return (f"The {field} field was automatically updated with high confidence ({confidence:.0%}). "
                f"Multiple reliable sources (NPI Registry, State Board) agree on the value '{chosen}', "
                f"making this a safe automatic update.")
    else:
        return f"The system evaluated {field} and chose '{chosen}' with {confidence:.0%} confidence."
