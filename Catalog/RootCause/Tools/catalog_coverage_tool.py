"""
Catalog Coverage Tool

Purpose:
--------
Detect catalog coverage issues for the SearchOps Root Cause Agent:
  - Missing required product attributes
  - Empty catalog slices (no products for brand/category)
  - Stale catalog data (last update beyond threshold)

Architecture:
-------------
CatalogCoverageTool -> CatalogRepositoryProtocol -> mock / DB / API

The tool never imports mock_catalog_db directly; all data access flows
through the injected repository so backend swaps require no tool changes.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Set

from .catalog_repository import CatalogRepository, CatalogRepositoryProtocol
from .catalog_models import CatalogProduct


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STALE_THRESHOLD_HOURS: int = 24

REQUIRED_ATTRIBUTES: List[str] = [
    "waterproof_flag",
    "terrain_type",
]


@dataclass
class CatalogCoverageResult:
    """Structured output returned to the Root Cause Agent."""

    status: str
    coverage_score: float
    total_products: int
    active_products: int
    affected_products: int
    missing_attributes: List[str]
    db_stale: bool
    last_update: Optional[str]
    root_cause_candidate: str
    evidence: List[str]


class CatalogCoverageTool:
    """
    Analyzes catalog coverage for a brand/category slice.

    Accepts an optional repository for dependency injection during tests or
    when pointing at PostgreSQL, MongoDB, Atlan, or a catalog service.
    """

    def __init__(
        self,
        repository: Optional[CatalogRepositoryProtocol] = None,
    ) -> None:
        self._repository: CatalogRepositoryProtocol = (
            repository if repository is not None else CatalogRepository()
        )

    async def run(self, signal_data: dict[str, 'Any']) -> 'CatalogCoverageResult':
        """
        Execute coverage analysis for the catalog entity in signal_data.

        Expected input shape:
            {
              "catalog_entity": {
                "category": "Footwear",
                "brand": "Trailhead XT"
              }
            }
        """

        catalog_entity = signal_data.get("catalog_entity", {})
        brand = str(catalog_entity.get("brand", "")).strip()
        category = str(catalog_entity.get("category", "")).strip()

        # Step 1: Query catalog via repository abstraction.
        products = await self._repository.get_products(
            brand=brand,
            category=category,
        )
        last_update = await self._repository.get_last_update_time(
            brand=brand,
            category=category,
        )

        evidence: List[str] = []
        missing_attributes: Set[str] = set()
        root_cause_candidate = "none"

        # Step 2: Verify products exist.
        if not products:
            return CatalogCoverageResult(
                status="degraded",
                coverage_score=0.0,
                total_products=0,
                active_products=0,
                affected_products=0,
                missing_attributes=[],
                db_stale=False,
                last_update=None,
                root_cause_candidate="catalog_coverage_gap",
                evidence=[
                    f"No catalog products found for brand '{brand}' "
                    f"and category '{category}'"
                ],
            )

        # Step 3: Count total and active products.
        total_products = len(products)
        active_products = sum(
            1 for product in products if product.status == "active"
        )

        # Steps 4-5: Detect and collect missing required attributes.
        affected_products = 0
        for product in products:
            product_missing = self._get_missing_attributes(product)
            if product_missing:
                affected_products += 1
                missing_attributes.update(product_missing)

        sorted_missing = sorted(missing_attributes)

        # Step 6: Calculate coverage score across the full product slice.
        coverage_score = round(
            ((total_products - affected_products) / total_products) * 100,
            2,
        )

        # Step 7: Check catalog freshness against the latest updated_at.
        db_stale = self._is_catalog_stale(last_update)
        if db_stale:
            root_cause_candidate = "stale_catalog_data"

        # Attribute gaps take second priority when data is fresh.
        if affected_products > 0 and root_cause_candidate == "none":
            root_cause_candidate = "catalog_attribute_gap"

        # Step 8: Build human-readable evidence for the Root Cause Agent.
        if db_stale:
            evidence.append("Catalog data is stale")

        if affected_products > 0:
            noun = "product" if affected_products == 1 else "products"
            evidence.append(
                f"{affected_products} {noun} missing required attributes"
            )

        for attribute in sorted_missing:
            evidence.append(f"Missing attribute: {attribute}")

        status = self._resolve_status(
            affected_products=affected_products,
            db_stale=db_stale,
        )

        return CatalogCoverageResult(
            status=status,
            coverage_score=coverage_score,
            total_products=total_products,
            active_products=active_products,
            affected_products=affected_products,
            missing_attributes=sorted_missing,
            db_stale=db_stale,
            last_update=last_update,
            root_cause_candidate=root_cause_candidate,
            evidence=evidence,
        )

    @staticmethod
    def _get_missing_attributes(product: CatalogProduct) -> list[str]:
        """
        Return required attribute names that are absent on a single product.

        A value is considered missing when it is None or an empty string.
        """

        missing: List[str] = []
        for attribute in REQUIRED_ATTRIBUTES:
            value = getattr(product, attribute, None)
            if value is None or value == "":
                missing.append(attribute)
        return missing

    @staticmethod
    def _parse_utc_timestamp(timestamp: str) -> datetime:
        """Parse ISO-8601 UTC timestamps, including trailing 'Z'."""

        normalized = timestamp.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)

    def _is_catalog_stale(self, last_update: Optional[str]) -> bool:
        """
        Compare current UTC time against the latest catalog update.

        Returns True when last_update is older than STALE_THRESHOLD_HOURS.
        """

        if last_update is None:
            return False

        last_update_dt = self._parse_utc_timestamp(last_update)
        now_utc = datetime.now(timezone.utc)
        age_hours = (now_utc - last_update_dt).total_seconds() / 3600
        return age_hours > STALE_THRESHOLD_HOURS

    @staticmethod
    def _resolve_status(
        affected_products: int,
        db_stale: bool,
    ) -> str:
        """
        Map detected issues to an overall health status.

        healthy  -> no stale data and no attribute gaps
        degraded -> stale data and/or products missing required attributes
        """

        if db_stale or affected_products > 0:
            return "degraded"
        return "healthy"


# ---------------------------------------------------------------------------
# Local testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from Catalog.RootCause.Tools.common_signals import sample_signal


    async def main() -> None:
        tool = CatalogCoverageTool()
        result = await tool.run(sample_signal)

        print()
        print("=" * 60)
        print("CATALOG COVERAGE RESULT")
        print("=" * 60)
        print(json.dumps(asdict(result), indent=2))

    asyncio.run(main())
