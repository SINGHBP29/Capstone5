import asyncio
import json
from dataclasses import dataclass, asdict
from typing import Any
from collections import Counter

from .catalog_repository import CatalogRepository
from .common_signals import sample_signal


@dataclass
class HistoricalIntentResult:
    tool_name: str
    status: str
    brand: str
    category: str
    total_queries_analyzed: int
    top_keywords: list[dict[str, 'Any']]
    root_cause_candidate: str
    evidence: list[str]


class CatalogHistoricalIntentTool:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    async def run(self, signal_data: dict[str, 'Any']) -> 'HistoricalIntentResult':
        brand = signal_data.get("catalog_entity", {}).get("brand")
        category = signal_data.get("catalog_entity", {}).get("category")

        if not brand or not category:
            return HistoricalIntentResult(
                tool_name="CatalogHistoricalIntentTool",
                status="failed",
                brand=brand,
                category=category,
                total_queries_analyzed=0,
                top_keywords=[],
                root_cause_candidate="missing_catalog_entity",
                evidence=["Brand or category is missing from signal data."],
            )

        # Simulate fetching historical queries for the given brand and category
        historical_queries = self._get_simulated_historical_queries(brand, category)

        if not historical_queries:
            return HistoricalIntentResult(
                tool_name="CatalogHistoricalIntentTool",
                status="healthy",
                brand=brand,
                category=category,
                total_queries_analyzed=0,
                top_keywords=[],
                root_cause_candidate="none",
                evidence=["No historical queries found for this catalog entity."],
            )

        total_queries_analyzed = len(historical_queries)
        keywords = []
        for query in historical_queries:
            keywords.extend(query.lower().split())

        top_keywords_count = Counter(keywords).most_common(5)
        top_keywords = [{
            "keyword": kw,
            "count": count
        } for kw, count in top_keywords_count]

        status = "healthy"
        root_cause_candidate = "none"
        evidence = [
            f"Analyzed {total_queries_analyzed} historical queries.",
            f"Top keywords: {', '.join([k['keyword'] for k in top_keywords])}"
        ]

        return HistoricalIntentResult(
            tool_name="CatalogHistoricalIntentTool",
            status=status,
            brand=brand,
            category=category,
            total_queries_analyzed=total_queries_analyzed,
            top_keywords=top_keywords,
            root_cause_candidate=root_cause_candidate,
            evidence=evidence,
        )

    def _get_simulated_historical_queries(self, brand: str, category: str) -> list[str]:
        # This would typically query a historical data store (e.g., search logs)
        # For simulation, we provide some canned responses.
        if brand == "Trailhead XT" and category == "Footwear":
            return [
                "trail running shoes",
                "waterproof hiking boots",
                "durable trail footwear",
                "comfortable hiking shoes trailhead xt",
                "footwear for rough terrain",
                "trailhead xt review",
                "buy trailhead xt"
            ]
        elif brand == "Summit Wear" and category == "Footwear":
            return [
                "urban sneakers summit wear",
                "casual shoes",
                "lightweight walking shoes"
            ]
        return []


if __name__ == "__main__":
    async def main():
        repo = CatalogRepository()
        tool = CatalogHistoricalIntentTool(repo)

        # Example signal for historical intent analysis
        intent_signal = {
            "catalog_entity": {
                "category": "Footwear",
                "brand": "Trailhead XT"
            }
        }

        result = await tool.run(intent_signal)

        print("\n")
        print("=" * 70)
        print("CATALOG HISTORICAL INTENT RESULT")
        print("=" * 70)

        print(json.dumps(asdict(result), indent=2))

    asyncio.run(main())
