"""
Catalog Schema Validation Tool

Purpose:
--------
Validate catalog records against the expected schema.

Detect:
- Missing required fields
- Type mismatches
- Null violations

This tool is deterministic and uses CatalogRepository.
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional
import json

from .catalog_repository import CatalogRepository
from .catalog_models import CatalogProduct # Import CatalogProduct


@dataclass
class CatalogSchemaValidationResult:
    tool_name: str
    status: str
    total_products_checked: int
    missing_fields: list[str]
    type_mismatches: list[str]
    null_violations: list[str]
    root_cause_candidate: str
    evidence: list[str]


class CatalogSchemaValidationTool:

    REQUIRED_SCHEMA: dict[str, Any] = {
        "sku": str,
        "brand": str,
        "category": str,
        "waterproof_flag": Optional[bool],
        "terrain_type": Optional[str],
        "status": str,
        "updated_at": str
    }

    REQUIRED_NON_NULL_FIELDS: list[str] = [
        "sku",
        "brand",
        "category",
        "status",
        "updated_at"
    ]

    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    async def run(
        self,
        signal_data: dict[str, 'Any']
    ) -> 'CatalogSchemaValidationResult':

        entity = signal_data.get("catalog_entity", {})

        brand = entity.get("brand")
        category = entity.get("category")

        products = await self.repository.get_products(
            brand=brand,
            category=category
        )

        if not products:

            return CatalogSchemaValidationResult(
                tool_name="CatalogSchemaValidationTool",
                status="failed",
                total_products_checked=0,
                missing_fields=[],
                type_mismatches=[],
                null_violations=[],
                root_cause_candidate="catalog_not_found",
                evidence=[
                    "No catalog products found."
                ]
            )

        missing_fields = set()
        type_mismatches = set()
        null_violations = set()
        evidence = []

        for product in products:
            sku = product.sku # Use direct attribute access for SKU

            # --------------------------
            # Check required fields exist and types
            # --------------------------

            for field_name, expected_type in self.REQUIRED_SCHEMA.items():
                # Check if attribute exists on the CatalogProduct object
                if not hasattr(product, field_name):
                    missing_fields.add(field_name)
                    evidence.append(f"{sku}: Missing field '{field_name}'")
                    continue

                value = getattr(product, field_name)

                # Type validation, handling Optional types
                if value is not None:
                    if expected_type is Optional[bool] and not isinstance(value, bool):
                        type_mismatches.add(field_name)
                        evidence.append(f"{sku}: Type mismatch for '{field_name}'. Expected bool or None, got {type(value).__name__}")
                    elif expected_type is Optional[str] and not isinstance(value, str):
                        type_mismatches.add(field_name)
                        evidence.append(f"{sku}: Type mismatch for '{field_name}'. Expected str or None, got {type(value).__name__}")
                    elif not (expected_type is Optional[bool] or expected_type is Optional[str]) and not isinstance(value, expected_type):
                        type_mismatches.add(field_name)
                        evidence.append(f"{sku}: Type mismatch for '{field_name}'. Expected {expected_type.__name__}, got {type(value).__name__}")

            # --------------------------
            # Null validation for explicitly non-null fields
            # --------------------------

            for field_name in self.REQUIRED_NON_NULL_FIELDS:
                if hasattr(product, field_name) and getattr(product, field_name) is None:
                    null_violations.add(field_name)
                    evidence.append(f"{sku}: Null value found for '{field_name}'")


        # ---------------------------------
        # Determine status
        # ---------------------------------

        has_errors = (
            len(missing_fields) > 0
            or len(type_mismatches) > 0
            or len(null_violations) > 0
        )

        if has_errors:

            status = "failed"

            root_cause = "catalog_schema_violation"

        else:

            status = "healthy"

            root_cause = "none"

            evidence.append(
                "All products passed schema validation."
            )

        return CatalogSchemaValidationResult(
            tool_name="CatalogSchemaValidationTool",
            status=status,
            total_products_checked=len(products),
            missing_fields=sorted(list(missing_fields)),
            type_mismatches=sorted(list(type_mismatches)),
            null_violations=sorted(list(null_violations)),
            root_cause_candidate=root_cause,\
            evidence=evidence
        )


# --------------------------------------------------
# LOCAL TESTING
# --------------------------------------------------

if __name__ == "__main__":

    import asyncio
    from Catalog.RootCause.Tools.common_signals import sample_signal # Corrected import path

    async def main():

        repo = CatalogRepository()

        tool = CatalogSchemaValidationTool(repo)

        result = await tool.run(
            sample_signal
        )

        print("\n")
        print("=" * 70)
        print("CATALOG SCHEMA VALIDATION RESULT")
        print("=" * 70)

        print(
            json.dumps(
                asdict(result),
                indent=2
            )
        )

    asyncio.run(main())
