"""
DataValidationAgent
-------------------
LLM-assisted validation that aggregates external signals (NPI registry,
maps, state board, hospital directories) and uses an LLM to perform fuzzy
matching, conflict reasoning, and unified confidence scoring.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..db import FieldConfidence, Provider
from ..external.npi_client import fetch_npi_data
from ..llm.gemini_client import call_gemini

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lightweight directory loaders (used when real APIs are unavailable)
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    import json

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


MAPS_DIR = _load_json(DATA_DIR / "maps_directory.json")
STATE_BOARD = _load_json(DATA_DIR / "state_board.json")
HOSPITAL_DIR = _load_json(DATA_DIR / "hospital_directory.json")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    value: Any
    source: str
    score_hint: float = 0.0


@dataclass
class ValidationResult:
    provider_id: int
    validated_fields: Dict[str, Dict[str, Any]]
    raw_evidence: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent implementation
# ---------------------------------------------------------------------------

class DataValidationAgent:
    """
    Aggregates candidate values from multiple sources and lets an LLM choose
    the best value with a confidence score per field.
    """

    def __init__(self, use_live_npi: bool = False):
        self.use_live_npi = use_live_npi
        self.llm_enabled = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

    def _fetch_sources(self, provider: Provider) -> Dict[str, Any]:
        external_id = provider.external_id

        npi_payload = fetch_npi_data(external_id) if self.use_live_npi else {}
        board_payload = STATE_BOARD.get(external_id, {})
        maps_payload = MAPS_DIR.get(external_id, {})
        hospital_payload = HOSPITAL_DIR.get(external_id, {})

        logger.info("Fetched external signals for provider %s", provider.id)
        return {
            "npi": npi_payload,
            "state_board": board_payload,
            "maps": maps_payload,
            "hospital": hospital_payload,
            "original": {
                "phone": provider.phone,
                "address": provider.address,
                "specialty": provider.specialty,
            },
        }

    def _gather_candidates(self, provider: Provider, sources: Dict[str, Any]) -> Dict[str, List[Candidate]]:
        candidates: Dict[str, List[Candidate]] = {
            "phone": [],
            "address": [],
            "specialty": [],
        }

        default_scores = {
            "npi": 1.0,
            "state_board": 0.9,
            "hospital": 0.8,
            "maps": 0.6,
            "original": 0.4,
        }

        for src, payload in sources.items():
            if not payload:
                continue
            for field in candidates.keys():
                value = payload.get(field)
                if value:
                    candidates[field].append(
                        Candidate(value=value, source=src, score_hint=default_scores.get(src, 0.3))
                    )

        logger.debug("Candidate aggregation complete for provider %s", provider.id)
        return candidates

    def get_best_value_with_llm(self, field_name: str, candidates: List[Candidate]) -> Optional[Dict[str, Any]]:
        """
        Use the LLM to pick the best candidate with fuzzy matching and reasoning.
        Returns a dict with value, confidence, and sources.
        """
        if not candidates:
            return None

        # If no LLM key, fall back deterministically to top-scoring candidate.
        if not self.llm_enabled:
            top = max(candidates, key=lambda c: c.score_hint)
            return {"value": top.value, "confidence": 0.6, "sources": [top.source]}

        # Prepare a prompt that instructs the LLM how to decide.
        prompt = f"""
You are a healthcare data validation assistant.
Field: {field_name}
Candidates (value, source, score_hint): {[(c.value, c.source, c.score_hint) for c in candidates]}

Tasks:
- Normalize and compare values (fuzzy match addresses/phones/specialties).
- Prefer sources with higher score_hint but reconcile conflicts logically.
- Return the single best value and a confidence between 0 and 1.
- Return the contributing sources list.

Respond in JSON with keys: value, confidence, sources.
"""
        try:
            llm_response = call_gemini(prompt)
        except Exception as exc:
            # Silently fallback for quota errors to avoid log spam
            from ..llm.gemini_client import QuotaExceededError
            if not isinstance(exc, QuotaExceededError):
                logger.warning("LLM call failed for field %s: %s", field_name, str(exc)[:100])
            top = max(candidates, key=lambda c: c.score_hint)
            return {"value": top.value, "confidence": 0.6, "sources": [top.source]}

        # Basic safety parsing: expect a JSON-like response; if parsing fails, fallback.
        import json

        parsed = None
        try:
            parsed = json.loads(llm_response)
        except Exception:
            # If the model returned plain text, fallback to first candidate
            logger.warning("LLM response not JSON for field %s: %s", field_name, llm_response)
            top = max(candidates, key=lambda c: c.score_hint)
            return {"value": top.value, "confidence": 0.6, "sources": [top.source]}

        if not isinstance(parsed, dict) or "value" not in parsed:
            top = max(candidates, key=lambda c: c.score_hint)
            return {"value": top.value, "confidence": 0.6, "sources": [top.source]}

        # Ensure sources list exists
        parsed.setdefault("sources", [c.source for c in candidates])
        parsed.setdefault("confidence", 0.5)
        return parsed

    def validate_provider(self, db: Session, provider_id: int) -> ValidationResult:
        """
        Main entry: fetch external signals, run LLM reasoning, persist confidence.
        """
        provider = db.query(Provider).get(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        sources = self._fetch_sources(provider)
        candidates = self._gather_candidates(provider, sources)

        validated_fields: Dict[str, Dict[str, Any]] = {}
        raw_evidence: Dict[str, Any] = {"candidates": candidates, "sources": sources}

        for field_name, field_candidates in candidates.items():
            best = self.get_best_value_with_llm(field_name, field_candidates)
            if not best:
                continue

            validated_fields[field_name] = {
                "value": best.get("value"),
                "confidence": float(best.get("confidence", 0.0)),
                "sources": best.get("sources", []),
            }

            db.add(
                FieldConfidence(
                    provider_id=provider_id,
                    field_name=field_name,
                    confidence=float(best.get("confidence", 0.0)),
                    sources=best.get("sources", []),
                )
            )

        db.commit()

        return ValidationResult(
            provider_id=provider_id,
            validated_fields=validated_fields,
            raw_evidence=raw_evidence,
        )


__all__ = ["DataValidationAgent", "ValidationResult", "Candidate"]

