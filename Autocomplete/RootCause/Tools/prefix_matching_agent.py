from __future__ import annotations

import logging
from difflib import get_close_matches
from typing import Any, Dict, List

from Autocomplete.state_repository import AutocompleteStateRepository


class PrefixMatchingAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.repo = AutocompleteStateRepository()

    @staticmethod
    def _normalize(text: Any) -> str:
        return str(text or "").strip().lower()

    @staticmethod
    def _candidate_prefixes(query: str) -> List[str]:
        max_len = min(len(query), 4)
        return [query[:idx] for idx in range(max_len, 0, -1) if query[:idx]]

    async def run(self, signal: dict):
        state = self.repo.load_state()
        query = self._normalize(signal.get("search_input") or signal.get("query") or signal.get("affected_prefix"))
        prefix_state = state.get("prefix_index", {}) if isinstance(state.get("prefix_index"), dict) else {}
        coverage = prefix_state.get("coverage", {}) if isinstance(prefix_state.get("coverage"), dict) else {}
        suggestions = prefix_state.get("suggestions", {}) if isinstance(prefix_state.get("suggestions"), dict) else {}
        stale_prefixes = {self._normalize(item) for item in prefix_state.get("stale_prefixes", []) if item}
        catalog_terms = []
        for item in state.get("catalog_terms", []):
            if isinstance(item, dict) and item.get("term"):
                catalog_terms.append(self._normalize(item["term"]))
            elif isinstance(item, str):
                catalog_terms.append(self._normalize(item))

        matched_prefix = ""
        for candidate in self._candidate_prefixes(query):
            if candidate in coverage or candidate in suggestions or candidate in stale_prefixes:
                matched_prefix = candidate
                break

        if not matched_prefix:
            matched_prefix = query[:3] if len(query) >= 3 else query

        prefix_coverage = coverage.get(matched_prefix)
        prefix_suggestions = suggestions.get(matched_prefix, [])
        close_terms = get_close_matches(query, catalog_terms, n=1, cutoff=0.72) if query else []
        typo_like = bool(close_terms and close_terms[0] != query)

        evidence: List[str] = []
        confidence = 0.18
        root_cause = "none"

        if prefix_coverage is not None:
            evidence.append(
                f"Prefix '{matched_prefix}' has coverage {prefix_coverage:.2f} in the local prefix index."
            )
        if prefix_suggestions:
            evidence.append(
                f"Prefix '{matched_prefix}' currently returns {len(prefix_suggestions)} suggestion(s): {', '.join(map(str, prefix_suggestions[:3]))}."
            )
        if matched_prefix in stale_prefixes:
            evidence.append(f"Prefix '{matched_prefix}' is marked stale in the local state.")
            root_cause = "prefix_index_stale"
            confidence = 0.82 if prefix_coverage is None or prefix_coverage < 0.25 else 0.68
        elif prefix_coverage is not None and prefix_coverage < 0.25:
            evidence.append(f"Coverage for '{matched_prefix}' is low enough to point at the prefix index.")
            root_cause = "prefix_index_stale"
            confidence = 0.74

        if typo_like:
            evidence.append(
                f"Query '{query}' is also a close lexical match for catalog term '{close_terms[0]}', which weakens a prefix-only diagnosis."
            )
            confidence = max(confidence - 0.35, 0.15)

        if not root_cause and prefix_suggestions:
            root_cause = "prefix_index_stale"
            confidence = 0.56

        summary = (
            "Prefix coverage looks stale for the affected prefix."
            if root_cause == "prefix_index_stale"
            else "No strong prefix-index failure was found."
        )

        return {
            "root_cause_candidate": root_cause,
            "confidence": round(confidence, 2),
            "recommended_fix": "adjust_prefix_weights" if root_cause == "prefix_index_stale" else "none",
            "matched_prefix": matched_prefix,
            "summary": summary,
            "evidence": evidence,
        }
