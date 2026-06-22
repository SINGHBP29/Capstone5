"""Repository for vector database and semantic index data access.

Mirrors the pattern of Catalog's CatalogRepository but focused on
LanceDB/vector DB state, embedding metadata, and index partitions.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import math


class VectorDBRepository:
    """Data access layer for the semantic index / vector database.

    In production this would wrap LanceDB, Pinecone, Weaviate, etc.
    For now it returns mock data that mirrors the real index state.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    async def ping_vector_db(self) -> Tuple[bool, float]:
        """Check if the vector DB is reachable and measure latency."""
        return True, 8.5

    async def get_all_vectors(self) -> List[Dict[str, Any]]:
        """Return all embedding records from the vector index."""
        base_time = "2026-06-10T08:00:00Z"
        return [
            {
                "sku": "TH-XT-001",
                "vector": [0.15, 0.22, 0.31, 0.42],
                "indexed_at": base_time,
                "model_version": "text-embedding-004-v2",
                "dimension": 4,
            },
            {
                "sku": "TH-XT-002",
                "vector": [0.18, 0.24, 0.0, 0.0],  # zero in last 2 dims — suspicious
                "indexed_at": base_time,
                "model_version": "text-embedding-004-v2",
                "dimension": 4,
            },
            {
                "sku": "TH-XT-003",
                "vector": [0.12, 0.19, 0.28, 0.38],
                "indexed_at": "2026-06-01T10:00:00Z",  # stale — catalog updated 2026-06-05
                "model_version": "text-embedding-004-v1",  # older model!
                "dimension": 4,
            },
            {
                "sku": "TH-XT-004",
                "vector": [0.0, 0.0, 0.0, 0.0],  # zero vector — embedding failure
                "indexed_at": base_time,
                "model_version": "text-embedding-004-v2",
                "dimension": 4,
            },
        ]

    async def get_vectors_by_sku(self, skus: List[str]) -> List[Dict[str, Any]]:
        """Get specific vectors by SKU."""
        all_vectors = await self.get_all_vectors()
        return [v for v in all_vectors if v["sku"] in skus]

    async def get_vector_count(self) -> int:
        """Get total number of vectors in the index."""
        vectors = await self.get_all_vectors()
        return len(vectors)

    async def get_partitions(self) -> List[Dict[str, Any]]:
        """Get index partition metadata."""
        return [
            {
                "partition_id": "p-001",
                "created_at": "2026-06-10T08:00:00Z",
                "vector_count": 2,
                "status": "active",
            },
            {
                "partition_id": "p-002",
                "created_at": "2026-06-01T10:00:00Z",
                "vector_count": 2,
                "status": "active",
            },
            {
                "partition_id": "p-003",
                "created_at": "2026-05-15T12:00:00Z",
                "vector_count": 1,
                "status": "stale",
            },
        ]

    async def get_stale_partition_count(
        self, threshold_hours: int = 72
    ) -> Tuple[int, int]:
        """Count partitions older than threshold."""
        partitions = await self.get_partitions()
        now = datetime.now(timezone.utc)
        stale = 0
        for p in partitions:
            try:
                created = datetime.fromisoformat(
                    p["created_at"].replace("Z", "+00:00")
                )
                age = (now - created).total_seconds() / 3600
                if age > threshold_hours:
                    stale += 1
            except (ValueError, KeyError):
                stale += 1
        return stale, len(partitions)

    async def get_catalog_products_for_index(
        self, brand: Optional[str] = None, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get catalog products that should be in the index.

        Mirrors CatalogRepository.get_products but returns dicts
        matching the index comparison schema.
        """
        return [
            {
                "sku": "TH-XT-001",
                "brand": "Trailhead XT",
                "category": "Footwear",
                "updated_at": "2026-06-12T10:00:00Z",
            },
            {
                "sku": "TH-XT-002",
                "brand": "Trailhead XT",
                "category": "Footwear",
                "updated_at": "2026-06-12T10:00:00Z",
            },
            {
                "sku": "TH-XT-003",
                "brand": "Trailhead XT",
                "category": "Footwear",
                "updated_at": "2026-06-12T10:00:00Z",
            },
            {
                "sku": "TH-XT-004",
                "brand": "Trailhead XT",
                "category": "Footwear",
                "updated_at": "2026-06-12T10:00:00Z",
            },
            {
                "sku": "TH-XT-005",
                "brand": "Trailhead XT",
                "category": "Footwear",
                "updated_at": "2026-06-12T10:00:00Z",
            },
        ]

    async def get_embedding_model_version(self) -> str:
        """Get the current embedding model version in use."""
        return "text-embedding-004-v2"

    async def get_baseline_embeddings(self) -> List[Dict[str, Any]]:
        """Get baseline embeddings for drift comparison (e.g. from a golden dataset)."""
        return [
            {
                "sku": "TH-XT-001",
                "vector": [0.15, 0.22, 0.32, 0.43],
                "model_version": "text-embedding-004-v2",
            },
            {
                "sku": "TH-XT-002",
                "vector": [0.18, 0.25, 0.30, 0.40],
                "model_version": "text-embedding-004-v2",
            },
            {
                "sku": "TH-XT-003",
                "vector": [0.12, 0.20, 0.29, 0.39],
                "model_version": "text-embedding-004-v2",
            },
        ]

    async def search_vectors(
        self, query_vector: List[float], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Simulate a vector similarity search.

        Returns results with calculated cosine distance from the query.
        """
        vectors = await self.get_all_vectors()
        results = []
        for v in vectors:
            vec = v["vector"]
            dot = sum(q * vv for q, vv in zip(query_vector, vec))
            norm_q = math.sqrt(sum(q * q for q in query_vector))
            norm_v = math.sqrt(sum(vv * vv for vv in vec))
            if norm_q == 0 or norm_v == 0:
                distance = 1.0
            else:
                cosine = dot / (norm_q * norm_v)
                distance = 1.0 - cosine
            results.append({
                "sku": v["sku"],
                "_distance": round(distance, 4),
                "score": round(1.0 - distance, 4),
                "vector": vec,
            })
        results.sort(key=lambda r: r["_distance"])
        return results[:limit]
