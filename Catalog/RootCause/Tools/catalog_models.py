from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CatalogProduct:
    """
    Canonical catalog product record shared across all repository implementations.

    Keeping a single schema here ensures mock and production repositories
    return the same shape to CatalogCoverageTool.
    """

    sku: str
    brand: str
    category: str
    waterproof_flag: Optional[bool]
    terrain_type: Optional[str]
    status: str
    updated_at: str  # ISO-8601 UTC, e.g. "2026-06-05T10:00:00Z"
