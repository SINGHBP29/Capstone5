"""Semantic search quality evaluation tool."""

from typing import List, Dict, Any, Optional
from ..Tools.semantic_models import SemanticSearchQualityResult
from ..Tools.vector_db_repository import VectorDBRepository


class SemanticSearchQualityTool:
    """Evaluates semantic search quality for a given query."""

    def __init__(self, repository: VectorDBRepository):
        self.repository = repository

    async def run(self, signal_data: Dict[str, Any]) -> SemanticSearchQualityResult:
        query = signal_data.get("search_query", "").strip().lower()
        if not query:
            query = "waterproof trail shoe"

        evidence: List[str] = []

        mock_query_vector = [0.0, 0.0, 0.5, 1.0]

        results = await self.repository.search_vectors(mock_query_vector, limit=5)

        total_results = len(results)
        zero_result = total_results == 0
        avg_score = sum(r["score"] for r in results) / total_results if total_results > 0 else 0.0
        top_sku: Optional[str] = results[0]["sku"] if results else None

        root_cause = "none"
        status = "healthy"

        if zero_result:
            status = "failed"
            root_cause = "zero_semantic_results"
            evidence.append(f"Zero results for query '{query}'.")
        elif avg_score < 0.6:
            status = "degraded"
            root_cause = "low_semantic_relevance"
            evidence.append(
                f"Low avg relevance score ({avg_score:.2f}) for query '{query}'."
            )
        else:
            evidence.append(
                f"Query '{query}': {total_results} results, avg score {avg_score:.2f}."
            )

        if results:
            evidence.append(f"Top result: {results[0]['sku']} (score: {results[0]['score']:.3f}).")

        return SemanticSearchQualityResult(
            tool_name="SemanticSearchQualityTool",
            status=status,
            query=query,
            total_results=total_results,
            zero_result=zero_result,
            avg_score=round(avg_score, 4),
            top_sku=top_sku,
            root_cause_candidate=root_cause,
            evidence=evidence,
        )
