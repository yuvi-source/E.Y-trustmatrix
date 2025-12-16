import os
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

MODEL_NAME = "gemini-flash-latest"

class QuotaExceededError(Exception):
    """Raised when API quota is exceeded"""
    pass

def call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except google_exceptions.ResourceExhausted as e:
        # Quota exceeded - raise custom error so agents can handle gracefully
        raise QuotaExceededError(f"Gemini API quota exceeded: {str(e)}") from e
    except Exception as e:
        # Re-raise other exceptions
        raise
