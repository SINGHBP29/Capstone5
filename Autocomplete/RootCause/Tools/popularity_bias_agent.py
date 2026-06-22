from __future__ import annotations

import logging
from typing import Any, Dict, List

from Autocomplete.state_repository import AutocompleteStateRepository


class PopularityBiasAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.repo = AutocompleteStateRepository()

    @staticmethod
    def _normalize(text: Any) -> str:
        return str(text or "").strip().lower()

    async def run(self, signal: dict):
        state = self.repo.load_state()
        query = self._normalize(signal.get("search_input") or signal.get("query"))
        popularity = state.get("popularity", {}) if isinstance(state.get("popularity"), dict) else {}
        entity_clicks = popularity.get("entity_clicks", {}) if isinstance(popularity.get("entity_clicks"), dict) else {}
        ranking_by_query = popularity.get("ranking_by_query", {}) if isinstance(popularity.get("ranking_by_query"), dict) else {}

        observed_ranking = signal.get("ranked_suggestions") or signal.get("top_results") or signal.get("suggestions")
        if not isinstance(observed_ranking, list):
            observed_ranking = ranking_by_query.get(query, []) if query in ranking_by_query else []

        evidence: List[str] = []
        confidence = 0.12
        root_cause = "none"

        if not query:
            return {
                "root_cause_candidate": root_cause,
                "confidence": confidence,
                "recommended_fix": "boost_popular_entities",
                "summary": "No query was supplied for popularity analysis.",
                "evidence": ["The signal does not contain a query or ranked suggestions."],
            }

        if not observed_ranking:
            evidence.append(f"No ranking evidence was provided for query '{query}'.")
            return {
                "root_cause_candidate": root_cause,
                "confidence": confidence,
                "recommended_fix": "boost_popular_entities",
                "summary": "No ranking inversion could be proven from the signal.",
                "evidence": evidence,
            }

        ranked_terms = []
        for item in observed_ranking:
            if isinstance(item, dict) and item.get("term"):
                ranked_terms.append(self._normalize(item["term"]))
            elif isinstance(item, str):
                ranked_terms.append(self._normalize(item))

        if len(ranked_terms) < 2:
            evidence.append("Ranking evidence did not contain enough suggestions to compare popularity.")
            return {
                "root_cause_candidate": root_cause,
                "confidence": confidence,
                "recommended_fix": "boost_popular_entities",
                "summary": "Not enough ranking data to diagnose a popularity bias.",
                "evidence": evidence,
            }

        top_term = ranked_terms[0]
        top_clicks = float(entity_clicks.get(top_term, 0))
        inverted_term = None
        inverted_clicks = top_clicks
        for term in ranked_terms[1:]:
            clicks = float(entity_clicks.get(term, 0))
            if clicks > inverted_clicks * 1.15:
                inverted_term = term
                inverted_clicks = clicks

        if inverted_term:
            root_cause = "popularity_bias_low"
            confidence = min(0.96, 0.65 + ((inverted_clicks - top_clicks) / max(inverted_clicks, 1.0)))
            evidence.append(
                f"'{top_term}' is ranked above '{inverted_term}' even though '{inverted_term}' has {int(inverted_clicks)} clicks versus {int(top_clicks)}."
            )
            evidence.append("The local popularity weights are not aligned with observed click demand.")
        else:
            evidence.append(
                f"The observed ranking for '{query}' does not show a strong click-popularity inversion."
            )

        return {
            "root_cause_candidate": root_cause,
            "confidence": round(confidence, 2),
            "recommended_fix": "boost_popular_entities" if root_cause == "popularity_bias_low" else "none",
            "summary": (
                "Popularity weights are suppressing a higher-click suggestion."
                if root_cause == "popularity_bias_low"
                else "No strong popularity bias was confirmed."
            ),
            "evidence": evidence,
        }
