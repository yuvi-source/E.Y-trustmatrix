"""Gemini LLM client for AI-assisted validation."""

import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Support both API key environment variables
_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if _api_key:
    genai.configure(api_key=_api_key)

MODEL_NAME = "gemini-2.5-flash"


def call_gemini(prompt: str) -> str:
    """Call Gemini API with the given prompt.
    
    Args:
        prompt: The prompt to send to Gemini.
        
    Returns:
        The response text from Gemini.
        
    Raises:
        RuntimeError: If API key is not configured.
    """
    if not _api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not configured")
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise
