from dataclasses import dataclass
from dataclasses import asdict

from typing import List
from typing import Dict
from typing import Any

from .query_intent_repository import (
    QueryIntentRepository
)


@dataclass
class QueryIntentDriftResult:

    tool_name: str

    status: str

    total_queries: int

    emerging_intents: int

    vocabulary_shifts: int

    synonym_gaps: int

    low_ctr_intents: int

    root_cause_candidate: str

    evidence: List[str]


class QueryIntentDriftTool:

    MIN_SEARCH_VOLUME = 100

    LOW_CTR_THRESHOLD = 0.05

    def __init__(
        self,
        repository: QueryIntentRepository
    ):
        self.repository = repository

    async def run(
        self,
        signal_data: Dict[str, Any]
    ) -> QueryIntentDriftResult:

        query_history = (
            await self.repository.get_query_history()
        )

        synonyms = (
            await self.repository.get_synonyms()
        )

        known_intents = (
            await self.repository.get_known_intents()
        )

        evidence = []

        emerging_intents = 0
        vocabulary_shifts = 0
        synonym_gaps = 0
        low_ctr_intents = 0

        total_queries = len(
            query_history
        )

        known_intent_set = set(
            intent.lower()
            for intent in known_intents
        )

        synonym_terms = set()

        for canonical, values in synonyms.items():

            synonym_terms.add(
                canonical.lower()
            )

            for value in values:

                synonym_terms.add(
                    value.lower()
                )

        for query_data in query_history:

            query = (
                query_data["query"]
                .lower()
                .strip()
            )

            search_count = (
                query_data["search_count"]
            )

            ctr = (
                query_data["ctr"]
            )

            # -----------------------------
            # Emerging Intent Detection
            # -----------------------------

            if (
                query not in known_intent_set
                and search_count >= self.MIN_SEARCH_VOLUME
            ):

                emerging_intents += 1

                evidence.append(
                    f"Emerging intent detected: "
                    f"{query}"
                )

            # -----------------------------
            # Low CTR Intent Detection
            # -----------------------------

            if ctr < self.LOW_CTR_THRESHOLD:

                low_ctr_intents += 1

                evidence.append(
                    f"Low CTR intent: "
                    f"{query} "
                    f"(CTR={ctr:.2%})"
                )

            # -----------------------------
            # Synonym Gap Detection
            # -----------------------------

            if (
                query not in synonym_terms
                and query not in known_intent_set
            ):

                synonym_gaps += 1

                evidence.append(
                    f"Possible synonym gap: "
                    f"{query}"
                )

            # -----------------------------
            # Vocabulary Drift Detection
            # -----------------------------

            query_words = set(
                query.split()
            )

            vocabulary_match = False

            for intent in known_intent_set:

                intent_words = set(
                    intent.split()
                )

                overlap = (
                    query_words
                    &
                    intent_words
                )

                if len(overlap) > 0:

                    vocabulary_match = True
                    break

            if not vocabulary_match:

                vocabulary_shifts += 1

                evidence.append(
                    f"Vocabulary drift: "
                    f"{query}"
                )

        # -----------------------------
        # RCA Decision
        # -----------------------------

        degraded = (
            emerging_intents
            or vocabulary_shifts
            or synonym_gaps
            or low_ctr_intents
        )

        if degraded:

            status = "degraded"

            if emerging_intents > 0:

                root_cause = (
                    "intent_drift"
                )

            elif synonym_gaps > 0:

                root_cause = (
                    "synonym_gap"
                )

            elif vocabulary_shifts > 0:

                root_cause = (
                    "vocabulary_shift"
                )

            else:

                root_cause = (
                    "search_relevance_degradation"
                )

        else:

            status = "healthy"

            root_cause = "none"

            evidence.append(
                "No intent drift detected."
            )

        return QueryIntentDriftResult(
            tool_name="QueryIntentDriftTool",
            status=status,
            total_queries=total_queries,
            emerging_intents=emerging_intents,
            vocabulary_shifts=vocabulary_shifts,
            synonym_gaps=synonym_gaps,
            low_ctr_intents=low_ctr_intents,
            root_cause_candidate=root_cause,
            evidence=evidence
        )