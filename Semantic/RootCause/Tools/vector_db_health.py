"""Vector DB health check tool."""

from dataclasses import dataclass
from typing import List, Dict, Any
from ..Tools.semantic_models import VectorDBHealthResult
from ..Tools.vector_db_repository import VectorDBRepository


class VectorDBHealthTool:
    """Checks vector database reachability, latency, partition health."""

    def __init__(self, repository: VectorDBRepository):
        self.repository = repository

    async def run(self, signal_data: Dict[str, Any]) -> VectorDBHealthResult:
        evidence: List[str] = []

        reachable, latency = await self.repository.ping_vector_db()
        if not reachable:
            return VectorDBHealthResult(
                tool_name="VectorDBHealthTool",
                status="failed",
                reachable=False,
                latency_ms=0.0,
                total_vectors=0,
                total_partitions=0,
                stale_partitions=0,
                index_version="unknown",
                root_cause_candidate="vector_db_unreachable",
                evidence=["Vector database is unreachable."],
            )

        evidence.append(f"Vector DB reachable (latency: {latency:.1f}ms).")

        vectors = await self.repository.get_all_vectors()
        total_vectors = len(vectors)

        stale_parts, total_parts = await self.repository.get_stale_partition_count()

        index_version = await self.repository.get_embedding_model_version()

        root_cause = "none"
        status = "healthy"

        if stale_parts > 0:
            status = "degraded"
            root_cause = "stale_index_partitions"
            evidence.append(f"{stale_parts}/{total_parts} partitions are stale.")

        if total_vectors == 0:
            status = "failed"
            root_cause = "empty_index"
            evidence.append("Vector index is empty.")

        evidence.append(f"Total vectors: {total_vectors}, partitions: {total_parts}.")

        return VectorDBHealthResult(
            tool_name="VectorDBHealthTool",
            status=status,
            reachable=reachable,
            latency_ms=latency,
            total_vectors=total_vectors,
            total_partitions=total_parts,
            stale_partitions=stale_parts,
            index_version=index_version,
            root_cause_candidate=root_cause,
            evidence=evidence,
        )
