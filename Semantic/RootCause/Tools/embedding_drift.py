"""Embedding drift analysis tool."""

import math
from typing import List, Dict, Any
from ..Tools.semantic_models import EmbeddingDriftResult
from ..Tools.vector_db_repository import VectorDBRepository


class EmbeddingDriftTool:
    """Compares current embeddings to baselines to detect drift."""

    DRIFT_THRESHOLD = 0.15  # cosine distance above this = drifted

    def __init__(self, repository: VectorDBRepository):
        self.repository = repository

    async def run(self, signal_data: Dict[str, Any]) -> EmbeddingDriftResult:
        evidence: List[str] = []

        current = await self.repository.get_all_vectors()
        baseline = await self.repository.get_baseline_embeddings()

        if not current or not baseline:
            return EmbeddingDriftResult(
                tool_name="EmbeddingDriftTool",
                status="failed",
                total_products_compared=0,
                drifted_products=0,
                max_cosine_distance=0.0,
                avg_cosine_distance=0.0,
                root_cause_candidate="insufficient_data",
                evidence=["No embedding data available for drift analysis."],
            )

        baseline_map = {b["sku"]: b["vector"] for b in baseline}

        drifted_count = 0
        total_distances = []
        total_compared = 0

        for entry in current:
            sku = entry["sku"]
            current_vec = entry["vector"]
            if sku not in baseline_map:
                continue

            baseline_vec = baseline_map[sku]
            dist = self._cosine_distance(current_vec, baseline_vec)
            total_distances.append(dist)
            total_compared += 1

            if dist > self.DRIFT_THRESHOLD:
                drifted_count += 1
                evidence.append(
                    f"SKU {sku}: cosine distance {dist:.4f} exceeds "
                    f"threshold {self.DRIFT_THRESHOLD}."
                )

        if not total_distances:
            return EmbeddingDriftResult(
                tool_name="EmbeddingDriftTool",
                status="failed",
                total_products_compared=0,
                drifted_products=0,
                max_cosine_distance=0.0,
                avg_cosine_distance=0.0,
                root_cause_candidate="no_baseline_match",
                evidence=["No baseline embeddings matched current vectors."],
            )

        max_dist = max(total_distances)
        avg_dist = sum(total_distances) / len(total_distances)

        status = "healthy"
        root_cause = "none"

        if drifted_count > 0:
            status = "degraded"
            root_cause = "embedding_drift"
            evidence.append(
                f"{drifted_count}/{total_compared} embeddings drifted "
                f"(max: {max_dist:.4f}, avg: {avg_dist:.4f})."
            )
        else:
            evidence.append(f"No drift detected across {total_compared} embeddings.")

        return EmbeddingDriftResult(
            tool_name="EmbeddingDriftTool",
            status=status,
            total_products_compared=total_compared,
            drifted_products=drifted_count,
            max_cosine_distance=round(max_dist, 4),
            avg_cosine_distance=round(avg_dist, 4),
            root_cause_candidate=root_cause,
            evidence=evidence,
        )

    @staticmethod
    def _cosine_distance(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 1.0
        return 1.0 - (dot / (norm_a * norm_b))
