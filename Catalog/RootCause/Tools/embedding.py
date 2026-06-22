import asyncio
import json
from dataclasses import dataclass, asdict
from typing import Any

from .catalog_repository import CatalogRepository
from .catalog_models import CatalogProduct
from Catalog.RootCause.Tools.common_signals import sample_signal


@dataclass
class ProductEmbedding:
    sku: str
    embedding: list[float]


@dataclass
class CatalogEmbeddingResult:
    tool_name: str
    status: str
    total_products_embedded: int
    embeddings: list[ProductEmbedding]
    root_cause_candidate: str
    evidence: list[str]

class CatalogEmbeddingTool:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    async def run(self, signal_data: dict[str, 'Any']) -> 'CatalogEmbeddingResult':
        entity = signal_data.get("catalog_entity", {})
        brand = entity.get("brand")
        category = entity.get("category")

        products = await self.repository.get_products(brand=brand, category=category)

        if not products:
            return CatalogEmbeddingResult(
                tool_name="CatalogEmbeddingTool",
                status="failed",
                total_products_embedded=0,
                embeddings=[],
                root_cause_candidate="catalog_not_found",
                evidence=["No catalog products found."],
            )

        embeddings: list[ProductEmbedding] = []
        for product in products:
            # Simple embedding logic: combine relevant attributes into a vector
            embedding_vector = self._generate_simple_embedding(product)
            embeddings.append(ProductEmbedding(sku=product.sku, embedding=embedding_vector))

        status = "healthy"
        root_cause_candidate = "none"
        evidence = [f"{len(products)} products successfully embedded."]

        return CatalogEmbeddingResult(
            tool_name="CatalogEmbeddingTool",
            status=status,
            total_products_embedded=len(products),
            embeddings=embeddings,
            root_cause_candidate=root_cause_candidate,
            evidence=evidence,
        )

    def _generate_simple_embedding(self, product: CatalogProduct) -> list[float]:
        # A very basic embedding: numerical representation of some attributes.
        # This is a placeholder for a real embedding model (e.g., using BERT, TF-IDF, etc.)
        embedding = []

        # Example: One-hot encoding for categorical/boolean attributes, numerical for others.
        # brand and category would typically use more sophisticated encoding (e.g., learned embeddings)
        # For this simple example, we'll use a hash or simple index if we had a vocabulary.
        # Since we don't, we'll just represent them as a single float (e.g., based on length or a hash).

        # Basic numerical representation
        embedding.append(len(product.brand) * 1.0)
        embedding.append(len(product.category) * 1.0)
        embedding.append(1.0 if product.waterproof_flag else 0.0)
        embedding.append(len(product.terrain_type) * 1.0 if product.terrain_type else 0.0)
        embedding.append(1.0 if product.status == "active" else 0.0)

        return embedding


if __name__ == "__main__":

    async def main():
        repo = CatalogRepository()
        tool = CatalogEmbeddingTool(repo)
        result = await tool.run(sample_signal)

        print("\n")
        print("=" * 70)
        print("CATALOG EMBEDDING RESULT")
        print("=" * 70)

        print(json.dumps(asdict(result), indent=2))

    asyncio.run(main())
