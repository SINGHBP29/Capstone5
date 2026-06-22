"""
Catalog Freshness Tool

Purpose:
--------
Determine whether catalog data is stale and may be causing
search relevance degradation, stale embeddings, outdated
results, or missing catalog updates.

This tool is deterministic and uses CatalogRepository.
"""

from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime, timezone
import json

from .catalog_repository import CatalogRepository


@dataclass
class CatalogFreshnessResult:
    tool_name: str
    status: str
    last_update: Optional[str]
    age_hours: float
    stale_threshold_hours: int
    is_stale: bool
    root_cause_candidate: str
    evidence: list[str]


class CatalogFreshnessTool:

    STALE_THRESHOLD_HOURS = 24

    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    async def run(self, signal_data: dict) -> 'CatalogFreshnessResult':
        """
        Analyze catalog freshness.

        Input:
        {
            "catalog_entity": {
                "brand": "Trailhead XT",
                "category": "Footwear"
            }
        }
        """

        entity = signal_data.get("catalog_entity", {})

        brand = entity.get("brand")
        category = entity.get("category")

        evidence = []

        last_update = await self.repository.get_last_update_time(
            brand=brand,
            category=category
        )

        if not last_update:

            return CatalogFreshnessResult(
                tool_name="CatalogFreshnessTool",
                status="failed",
                last_update=None,
                age_hours=0,
                stale_threshold_hours=self.STALE_THRESHOLD_HOURS,
                is_stale=False,
                root_cause_candidate="catalog_not_found",
                evidence=[
                    "No catalog records found for supplied entity."
                ]
            )

        # Parse timestamp

        last_update_dt = datetime.fromisoformat(
            last_update.replace("Z", "+00:00")
        )

        current_time = datetime.now(timezone.utc)

        age_hours = round(
            (
                current_time - last_update_dt
            ).total_seconds() / 3600,
            2
        )

        is_stale = (
            age_hours > self.STALE_THRESHOLD_HOURS
        )

        if is_stale:

            status = "stale"

            root_cause = "stale_catalog_data"

            evidence.append(
                f"Catalog age is {age_hours} hours."
            )

            evidence.append(
                f"Exceeded threshold of "
                f"{self.STALE_THRESHOLD_HOURS} hours."
            )

            evidence.append(
                f"Last update was {last_update}."
            )

        else:

            status = "healthy"

            root_cause = "none"

            evidence.append(
                f"Catalog freshness is healthy."
            )

            evidence.append(
                f"Age: {age_hours} hours."
            )

        return CatalogFreshnessResult(
            tool_name="CatalogFreshnessTool",
            status=status,
            last_update=last_update,
            age_hours=age_hours,
            stale_threshold_hours=self.STALE_THRESHOLD_HOURS,
            is_stale=is_stale,
            root_cause_candidate=root_cause,
            evidence=evidence
        )


# ---------------------------------------------------
# LOCAL TESTING
# ---------------------------------------------------

if __name__ == "__main__":

    import asyncio

    from Catalog.RootCause.Tools.common_signals import sample_signal
    async def main():

        repo = CatalogRepository()

        tool = CatalogFreshnessTool(repo)

        result = await tool.run(
            sample_signal
        )

        print("\n")
        print("=" * 60)
        print("CATALOG FRESHNESS RESULT")
        print("=" * 60)

        print(
            json.dumps(
                asdict(result),
                indent=2
            )
        )

    asyncio.run(main())