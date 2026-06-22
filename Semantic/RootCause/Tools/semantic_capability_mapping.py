"""Semantic capability mapping tool — maps index issues to affected capabilities."""

from typing import List, Dict, Any
from ..Tools.semantic_models import SemanticCapabilityMappingResult


class SemanticCapabilityMappingTool:
    """Aggregates findings from all semantic tools into a capability impact map."""

    CAPABILITY_MAP = {
        "stale_embeddings": ["semantic_search", "vector_retrieval"],
        "embedding_drift": ["semantic_search", "product_discovery"],
        "embedding_failure": ["semantic_search", "embedding_pipeline"],
        "index_coverage_gap": ["semantic_search", "product_discovery", "attribute_filtering"],
        "vector_db_unreachable": ["semantic_search", "vector_retrieval", "search_api"],
        "zero_semantic_results": ["semantic_search", "product_discovery"],
        "low_semantic_relevance": ["semantic_search", "search_relevance"],
        "stale_index_partitions": ["semantic_search", "index_refresh_pipeline"],
        "intent_drift": ["semantic_search", "autocomplete", "search_relevance"],
        "empty_index": ["semantic_search", "search_api"],
        "none": [],
    }

    async def run(self, signal_data: Dict[str, Any]) -> SemanticCapabilityMappingResult:
        evidence: List[str] = []

        tool_results = signal_data.get("tool_results", {})
        root_causes = set()

        for tool_name, result in tool_results.items():
            if isinstance(result, dict):
                rc = result.get("root_cause_candidate", "")
                if rc and rc != "none":
                    root_causes.add(rc)
                    evidence.append(f"{tool_name}: {rc}")

        if not root_causes:
            rc = signal_data.get("root_cause", "none")
            if rc != "none":
                root_causes.add(rc)

        affected: List[str] = []
        for cause in root_causes:
            affected.extend(self.CAPABILITY_MAP.get(cause, []))

        affected = list(set(affected))
        status = "degraded" if affected else "healthy"
        root_cause = ", ".join(sorted(root_causes)) if root_causes else "none"

        if not evidence:
            evidence.append("No issues detected — all capabilities healthy.")

        evidence.append(f"Affected capabilities: {affected}.")

        return SemanticCapabilityMappingResult(
            tool_name="SemanticCapabilityMappingTool",
            status=status,
            affected_capabilities=affected,
            root_cause_candidate=root_cause,
            evidence=evidence,
        )
