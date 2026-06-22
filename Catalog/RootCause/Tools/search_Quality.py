import asyncio
import json
from dataclasses import dataclass, asdict
from typing import Any

from .catalog_repository import CatalogRepository
from .catalog_models import CatalogProduct
from .common_signals import sample_signal


@dataclass
class SearchQualityResult:
    tool_name: str
    status: str
    query: str
    total_products_checked: int
    relevant_products_found: int
    quality_score: float
    root_cause_candidate: str
    evidence: list[str]

class CatalogSearchQualityTool:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    async def run(self, signal_data: dict[str, 'Any']) -> 'SearchQualityResult':
        query_text = signal_data.get("search_query", "").strip().lower()
        brand = signal_data.get("catalog_entity", {}).get("brand")
        category = signal_data.get("catalog_entity", {}).get("category")

        if not query_text:
            return SearchQualityResult(
                tool_name="CatalogSearchQualityTool",
                status="failed",
                query=query_text,
                total_products_checked=0,
                relevant_products_found=0,
                quality_score=0.0,
                root_cause_candidate="missing_search_query",
                evidence=["Search query is missing."],
            )

        products = await self.repository.get_products(brand=brand, category=category)

        if not products:
            return SearchQualityResult(
                tool_name="CatalogSearchQualityTool",
                status="failed",
                query=query_text,
                total_products_checked=0,
                relevant_products_found=0,
                quality_score=0.0,
                root_cause_candidate="catalog_not_found",
                evidence=["No catalog products found for specified brand/category."],
            )

        total_products_checked = len(products)
        relevant_products_found = 0
        evidence: List[str] = []

        for product in products:
            if self._is_relevant(query_text, product):
                relevant_products_found += 1
                evidence.append(f"SKU {product.sku} is relevant.")
            else:
                evidence.append(f"SKU {product.sku} is not directly relevant to query.")

        quality_score = (relevant_products_found / total_products_checked) * 100 if total_products_checked > 0 else 0.0
        status = "healthy" if quality_score > 50 else "degraded"
        root_cause_candidate = "none" if status == "healthy" else "low_search_relevance"

        return SearchQualityResult(
            tool_name="CatalogSearchQualityTool",
            status=status,
            query=query_text,
            total_products_checked=total_products_checked,
            relevant_products_found=relevant_products_found,
            quality_score=round(quality_score, 2),
            root_cause_candidate=root_cause_candidate,
            evidence=evidence,
        )

    def _is_relevant(self, query: str, product: CatalogProduct) -> bool:
        # Simple keyword matching for relevance. In a real system, this would use embeddings.
        product_text = f"{product.brand} {product.category} {product.terrain_type} {product.status}".lower()
        return query in product_text


if __name__ == "__main__":
    async def main():
        repo = CatalogRepository()
        tool = CatalogSearchQualityTool(repo)

        # Example signal with a search query
        search_signal = {
            "catalog_entity": {
                "category": "Footwear",
                "brand": "Trailhead XT"
            },
            "search_query": "trail waterproof"
        }

        result = await tool.run(search_signal)

        print("\n")
        print("=" * 70)
        print("CATALOG SEARCH QUALITY RESULT")
        print("=" * 70)

        print(json.dumps(asdict(result), indent=2))

    asyncio.run(main())
