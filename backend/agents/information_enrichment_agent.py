"""
InformationEnrichmentAgent
--------------------------
LLM-assisted enrichment that fills missing provider metadata from directory
and web-like sources, then normalizes the fields.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..db import Provider
from ..llm.gemini_client import call_gemini

logger = logging.getLogger(__name__)


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    import json

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


HOSPITAL_DIR = _load_json(DATA_DIR / "hospital_directory.json")


@dataclass
class EnrichmentResult:
    provider_id: int
    enriched_fields: Dict[str, Any]
    raw_evidence: Dict[str, Any] = field(default_factory=dict)


class InformationEnrichmentAgent:
    """
    Uses heuristic scraping data plus LLM summarization to enrich provider info.
    """

    def __init__(self):
        self.llm_enabled = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

    def _fallback_extract(self, snippets: List[str]) -> Dict[str, Any]:
        summary = " ".join(snippets)[:240] if snippets else ""
        return {
            "certifications": [],
            "affiliations": [],
            "education": "",
            "secondary_specialties": [],
            "summary": summary or "No enrichment data available.",
        }

    def _fetch_directory_blurbs(self, provider: Provider) -> List[str]:
        """Return text snippets from hospital directory JSON as pseudo-scraped text."""
        entry = HOSPITAL_DIR.get(provider.external_id)
        if not entry:
            return []
        blurbs = []
        for key in ["bio", "about", "services"]:
            if entry.get(key):
                blurbs.append(str(entry[key]))
        return blurbs

    def _llm_structured_extract(self, provider: Provider, snippets: List[str]) -> Dict[str, Any]:
        # If no LLM key, return empty defaults.
        if not self.llm_enabled:
            return self._fallback_extract(snippets)

        prompt = f"""
You are enriching a clinician profile.
Provider name: {provider.name}
Existing specialty: {provider.specialty}
Text snippets: {snippets}

Extract and return JSON with keys:
- certifications (list of strings)
- affiliations (list of org names)
- education (string)
- secondary_specialties (list)
- summary (short supporting note)
Normalize specialties (e.g., Dermatologist -> Dermatology).
Keep empty lists/strings if not found.
"""
        import json

        try:
            response = call_gemini(prompt)
            # Clean markdown code blocks
            cleaned = response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
        except Exception as exc:
            # Silently fallback for quota errors
            from ..llm.gemini_client import QuotaExceededError
            if not isinstance(exc, QuotaExceededError):
                logger.warning("LLM enrichment failed for provider %s: %s", provider.id, str(exc)[:100])
            return self._fallback_extract(snippets)

        if not isinstance(parsed, dict):
            return {}

        parsed.setdefault("certifications", [])
        parsed.setdefault("affiliations", [])
        parsed.setdefault("education", "")
        parsed.setdefault("secondary_specialties", [])
        parsed.setdefault("summary", "")
        return parsed

    def enrich_provider(self, db: Session, provider_id: int) -> EnrichmentResult:
        provider = db.get(Provider, provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        snippets = self._fetch_directory_blurbs(provider)
        extracted = self._llm_structured_extract(provider, snippets)

        enriched_fields: Dict[str, Any] = {}
        if extracted.get("certifications"):
            enriched_fields["certifications"] = extracted["certifications"]
        if extracted.get("affiliations"):
            enriched_fields["affiliations"] = extracted["affiliations"]
        if extracted.get("education") is not None:
            enriched_fields["education"] = extracted.get("education", "")
        if extracted.get("secondary_specialties"):
            enriched_fields["secondary_specialties"] = extracted["secondary_specialties"]
        if extracted.get("summary"):
            enriched_fields["summary"] = extracted["summary"]

        raw_evidence = {
            "snippets": snippets,
            "llm_extracted": extracted,
        }

        logger.info("Enrichment complete for provider %s", provider.id)
        return EnrichmentResult(
            provider_id=provider_id,
            enriched_fields=enriched_fields,
            raw_evidence=raw_evidence,
        )


__all__ = ["InformationEnrichmentAgent", "EnrichmentResult"]

