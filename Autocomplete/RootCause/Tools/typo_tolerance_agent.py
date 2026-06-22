from __future__ import annotations

import logging
from difflib import get_close_matches
from typing import Any, List

from Autocomplete.state_repository import AutocompleteStateRepository


class TypoToleranceAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.repo = AutocompleteStateRepository()

    @staticmethod
    def _normalize(text: Any) -> str:
        return str(text or "").strip().lower()

    async def run(self, signal: dict):
        state = self.repo.load_state()
        query = self._normalize(signal.get("search_input") or signal.get("query"))
        typo_dictionary = state.get("typo_dictionary", {}) if isinstance(state.get("typo_dictionary"), dict) else {}
        catalog_terms: List[str] = []
        for item in state.get("catalog_terms", []):
            if isinstance(item, dict) and item.get("term"):
                catalog_terms.append(self._normalize(item["term"]))
            elif isinstance(item, str):
                catalog_terms.append(self._normalize(item))

        evidence: List[str] = []
        confidence = 0.08
        root_cause = "none"

        if not query:
            return {
                "root_cause_candidate": root_cause,
                "confidence": confidence,
                "recommended_fix": "update_typo_dictionary",
                "summary": "No query was supplied for typo analysis.",
                "evidence": ["The signal does not contain a query to compare against the typo dictionary."],
            }

        if query in typo_dictionary:
            mapped = typo_dictionary.get(query, [])
            evidence.append(f"Query '{query}' already has typo mappings: {', '.join(map(str, mapped[:3]))}.")
            return {
                "root_cause_candidate": root_cause,
                "confidence": confidence,
                "recommended_fix": "update_typo_dictionary",
                "summary": "The query is already covered by the typo dictionary.",
                "evidence": evidence,
            }

        close_terms = get_close_matches(query, catalog_terms, n=3, cutoff=0.68)
        if close_terms:
            root_cause = "missing_typo_synonyms"
            confidence = 0.97
            evidence.append(
                f"Query '{query}' is a close lexical match for catalog term '{close_terms[0]}'."
            )
            evidence.append(
                f"No typo dictionary entry exists for '{query}', so the query is not being normalized to the intended term."
            )
            issue_text = self._normalize(signal.get("issue"))
            if "misspell" in issue_text or "typo" in issue_text or "no results" in issue_text:
                evidence.append("The incoming issue text explicitly describes a misspelling or empty autocomplete result.")
        else:
            evidence.append(
                f"Query '{query}' does not have a sufficiently close catalog match to prove a typo synonym gap."
            )

        return {
            "root_cause_candidate": root_cause,
            "confidence": round(confidence, 2),
            "is_typo": root_cause == "missing_typo_synonyms",
            "recommended_fix": "update_typo_dictionary" if root_cause == "missing_typo_synonyms" else "none",
            "summary": (
                "Missing typo synonyms are the most likely failure."
                if root_cause == "missing_typo_synonyms"
                else "No missing typo synonym was confirmed."
            ),
            "evidence": evidence,
        }
