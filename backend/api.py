from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.llm.qa_summarizer import summarize_qa_decision
import time
from collections import defaultdict

router = APIRouter()

RATE_LIMIT = 5        # max 5 explanations
RATE_WINDOW = 60      # per 60 seconds
_request_log = defaultdict(list)


class ExplainRequest(BaseModel):
    field: str
    current_value: str | None
    candidates: list
    chosen_value: str | None
    confidence: float
    decision: str


class ExplainResponse(BaseModel):
    explanation: str


@router.post("/explain", response_model=ExplainResponse)
def explain_decision(payload: ExplainRequest, request: Request):
    # -------- RATE LIMIT (DEV-SAFE) --------
    client_ip = request.client.host
    now = time.time()

    # Keep only recent timestamps
    _request_log[client_ip] = [
        t for t in _request_log[client_ip]
        if now - t < RATE_WINDOW
    ]

    if len(_request_log[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before requesting more explanations."
        )

    _request_log[client_ip].append(now)
    # --------------------------------------

    try:
        explanation = summarize_qa_decision(payload.model_dump())
        return {"explanation": explanation}
    except Exception as e:
        # Fallback to deterministic explanation to keep endpoint responsive
        fallback = (
            f"Decision for {payload.field}: chose {payload.chosen_value} "
            f"with confidence {payload.confidence:.2f} from sources {payload.candidates}."
        )
        return {"explanation": fallback}
