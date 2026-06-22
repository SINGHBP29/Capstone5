"""Repository for semantic data access."""
import json
from typing import List, Dict, Any, Tuple

# Mock data for demonstration purposes
class SemanticRepository:
    """Handles data access for semantic index, embeddings, and catalog."""

    def __init__(self, vector_db_path="mock_vector_db.json", catalog_path="mock_catalog.json"):
        with open(vector_db_path, 'r') as f:
            self._vector_db = json.load(f)
        # In a real scenario, you'd have a catalog mock as well
        # with open(catalog_path, 'r') as f:
        #     self._catalog = json.load(f)

    async def ping_vector_db(self) -> Tuple[bool, float]:
        """Pings the vector database to check reachability and latency."""
        return True, 25.5

    async def get_all_vectors(self) -> List[Dict[str, Any]]:
        """Retrieves all vectors from the database."""
        return self._vector_db.get("product_vectors", [])

    async def get_stale_partition_count(self) -> Tuple[int, int]:
        """Gets the count of stale partitions."""
        return 0, 10 # Mock data

    async def get_embedding_model_version(self) -> str:
        """Gets the current embedding model version."""
        return "v2.1.0"

    async def get_baseline_embeddings(self) -> List[Dict[str, Any]]:
        """Retrieves baseline embeddings for drift comparison."""
        # This would come from a separate, versioned store
        return self._vector_db.get("product_vectors", [])[::2] # Mocking baseline

    async def get_catalog_products_for_index(self, brand: str, category: str) -> List[Dict[str, Any]]:
        """Gets catalog products that should be in the index."""
        # This would query a real catalog API or DB
        return [
            {"sku": "A123", "updated_at": "2023-10-01T10:00:00Z"},
            {"sku": "B456", "updated_at": "2023-10-01T10:00:00Z"},
            {"sku": "C789", "updated_at": "2023-10-01T10:00:00Z"},
        ]

    async def search_vectors(self, vector: List[float], limit: int) -> List[Dict[str, Any]]:
        """Performs a semantic search."""
        # This would be a real vector search
        return [
            {"sku": "A123", "score": 0.9},
            {"sku": "D101", "score": 0.85},
        ]
