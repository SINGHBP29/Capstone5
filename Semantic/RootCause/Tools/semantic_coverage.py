"""Semantic index coverage check tool."""

from datetime import datetime
from typing import List, Dict, Any
from ..Tools.semantic_models import SemanticCoverageResult
from ..Tools.vector_db_repository import VectorDBRepository


class SemanticCoverageTool:
    """Checks which catalog products are missing from the semantic index."""

    def __init__(self, repository: VectorDBRepository):
        self.repository = repository

    async def run(self, signal_data: Dict[str, Any]) -> SemanticCoverageResult:
        evidence: List[str] = []
        brand = signal_data.get("catalog_entity", {}).get("brand")
        category = signal_data.get("catalog_entity", {}).get("category")

        catalog = await self.repository.get_catalog_products_for_index(brand, category)
        index = await self.repository.get_all_vectors()

        catalog_skus = {p["sku"] for p in catalog}
        index_skus = {v["sku"] for v in index}
        missing_skus = catalog_skus - index_skus

        catalog_count = len(catalog)
        indexed_count = len(index)
        missing_count = len(missing_skus)
        coverage_pct = round((indexed_count / catalog_count) * 100, 2) if catalog_count > 0 else 100.0

        stale_count = 0
        index_map = {v["sku"]: v["indexed_at"] for v in index}

        for product in catalog:
            sku = product["sku"]
            if sku not in index_map:
                stale_count += 1
                continue
            try:
                cat_time = datetime.fromisoformat(product["updated_at"].replace("Z", "+00:00"))
                idx_time = datetime.fromisoformat(index_map[sku].replace("Z", "+00:00"))
                if idx_time < cat_time:
                    stale_count += 1
            except (ValueError, KeyError):
                stale_count += 1

        root_cause = "none"
        status = "healthy"

        if missing_count > 0:
            status = "degraded"
            root_cause = "index_coverage_gap"
            evidence.append(
                f"{missing_count} products missing from index "
                f"(sample: {list(missing_skus)[:3]}). "
                f"Coverage: {coverage_pct}%."
            )

        if stale_count > 0:
            status = "degraded"
            if root_cause == "none":
                root_cause = "stale_embeddings"
            evidence.append(f"{stale_count} embeddings are stale.")

        if root_cause == "none":
            evidence.append(f"Index coverage healthy: {indexed_count}/{catalog_count}.")

        return SemanticCoverageResult(
            tool_name="SemanticCoverageTool",
            status=status,
            catalog_count=catalog_count,
            indexed_count=indexed_count,
            missing_from_index=missing_count,
            stale_embeddings=stale_count,
            coverage_percent=coverage_pct,
            root_cause_candidate=root_cause,
            evidence=evidence,
        )
