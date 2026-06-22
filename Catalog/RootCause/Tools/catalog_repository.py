"""
Catalog Repository

Purpose:
--------
Abstracts catalog data access behind a stable async interface so
CatalogCoverageTool remains unchanged when the backing store changes.

Current implementation:
    Reads from mock_catalog_db.py (in-memory list).

Future implementations (swap without touching the tool):
    - PostgreSQLCatalogRepository  -> SQL queries against product tables
    - MongoCatalogRepository       -> document queries against a products collection
    - AtlanCatalogRepository       -> REST calls to Atlan metadata API
    - CatalogServiceRepository     -> internal Catalog Service HTTP/gRPC API

Design notes:
    - CatalogCoverageTool depends on CatalogRepositoryProtocol, not mock details.
    - Inject a concrete repository at construction time for testing or prod.
    - All I/O methods are async to match future network/database latency.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable
import json
import lancedb
import pyarrow as pa
import pandas as pd
import os

from .catalog_models import CatalogProduct


def _parse_utc_timestamp(timestamp: str) -> datetime:
    """
    Parse an ISO-8601 UTC timestamp into a timezone-aware datetime.

    Supports the trailing 'Z' suffix used throughout the mock dataset.
    """

    normalized = timestamp.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _read_products_from_db() -> list['CatalogProduct']:
    with open("/Users/bhsingh/Documents/Capstone5/mock_catalog_db.db", "r") as f:
        data = json.load(f)
    return [CatalogProduct(**item) for item in data]


def _read_rules_from_db() -> dict[str, 'Any']:
    try:
        with open("/Users/bhsingh/Documents/Capstone5/mock_search_rules_db.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"synonyms": {}, "query_expansions": {}}

def _write_rules_to_db(data: dict[str, 'Any']) -> None:
    with open("/Users/bhsingh/Documents/Capstone5/mock_search_rules_db.json", "w") as f:
        json.dump(data, f, indent=4)

def _read_vectors_from_db() -> dict[str, list[float]]:
    try:
        with open("/Users/bhsingh/Documents/Capstone5/mock_vector_db.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def _write_vectors_to_db(data: dict[str, list[float]]) -> None:
    with open("/Users/bhsingh/Documents/Capstone5/mock_vector_db.json", "w") as f:
        json.dump(data, f, indent=4)

@runtime_checkable
class CatalogRepositoryProtocol(Protocol):
    """
    Contract for catalog data access.

    Any future repository must implement these methods so CatalogCoverageTool
    can be wired to PostgreSQL, MongoDB, Atlan, or a catalog microservice
    without modification.
    """

    async def get_products(
        self,
        brand: str,
        category: str,
    ) -> List[CatalogProduct]:
        ...

    async def get_last_update_time(
        self,
        brand: str,
        category: str,
    ) -> Optional[str]:
        ...


class CatalogRepository(CatalogRepositoryProtocol):
    """
    Mock-backed catalog repository for local development and testing.

    Filters the in-memory product list by brand and category. When migrating
    to a real database, create a new class that implements the same methods
    and inject it into CatalogCoverageTool instead of this one.
    """

    async def get_products(
        self,
        brand: str,
        category: str,
    ) -> List[CatalogProduct]:
        """
        Return all catalog products matching the given brand and category.

        Production equivalent:
            SELECT * FROM catalog_products
            WHERE brand = $1 AND category = $2;
        """

        products = _read_products_from_db()
        return [
            product
            for product in products
            if product.brand == brand and product.category == category
        ]

    async def update_product(self, updated_product: CatalogProduct) -> None:
        products = _read_products_from_db()
        updated_products = []
        found = False
        for product in products:
            if product.sku == updated_product.sku:
                updated_products.append(updated_product)
                found = True
            else:
                updated_products.append(product)
        if not found:
            updated_products.append(updated_product)

        with open("/Users/bhsingh/Documents/Capstone5/mock_catalog_db.db", "w") as f:
            json.dump([product.__dict__ for product in updated_products], f, indent=4)

    async def apply_patch(self, skus: list[str], patch_data: dict[str, 'Any']) -> int:
        """Applies a JSON patch to specific SKUs in the catalog."""
        products = _read_products_from_db()
        updated_count = 0
        
        for i, product in enumerate(products):
            if product.sku in skus:
                # Convert dataclass to dict to apply patch, then back to dataclass
                prod_dict = product.__dict__
                prod_dict.update(patch_data)
                # Update timestamp
                prod_dict["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                products[i] = CatalogProduct(**prod_dict)
                updated_count += 1
                
        if updated_count > 0:
            with open("/Users/bhsingh/Documents/Capstone5/mock_catalog_db.db", "w") as f:
                json.dump([p.__dict__ for p in products], f, indent=4)
                
        return updated_count

    async def add_synonym_rule(self, query: str, synonyms: list[str]) -> None:
        rules = _read_rules_from_db()
        rules["synonyms"][query] = synonyms
        _write_rules_to_db(rules)

    async def add_query_expansion_rule(self, query: str, expansions: list[str]) -> None:
        rules = _read_rules_from_db()
        rules["query_expansions"][query] = expansions
        _write_rules_to_db(rules)

    def _get_lancedb_table(self):
        # Initialize LanceDB connection and return the table
        db_path = "/Users/bhsingh/Documents/Capstone5/mock_lancedb"
        os.makedirs(db_path, exist_ok=True)
        db = lancedb.connect(db_path)
        
        # Define schema using pyarrow
        schema = pa.schema([
            pa.field("sku", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 4)) # We mock 4-dimensional vectors
        ])
        
        table_name = "product_vectors"
        if table_name in db.table_names():
            return db.open_table(table_name)
        else:
            return db.create_table(table_name, schema=schema)

    async def upsert_product_vectors(self, vectors_map: dict[str, list[float]]) -> None:
        """Upserts dense embeddings to the mock LanceDB vector database for specific SKUs."""
        table = self._get_lancedb_table()
        
        # Format data for LanceDB (list of dicts)
        data = []
        for sku, vector in vectors_map.items():
            data.append({"sku": sku, "vector": vector})
            
        if data:
            # Upsert requires a primary key in LanceDB. If it's a new table or 
            # schema doesn't have it, we just add or overwrite manually for this mock.
            # For simplicity in this mock, we'll delete existing SKUs and append new ones 
            # to simulate an upsert without complex primary key setup in the basic schema.
            skus_to_update = [item["sku"] for item in data]
            sku_filter = ", ".join([f"'{s}'" for s in skus_to_update])
            
            try:
                # Attempt to delete existing matching SKUs to simulate upsert
                table.delete(f"sku IN ({sku_filter})")
            except Exception:
                pass # Table might be empty
                
            table.add(data)

    async def search_vectors(self, query_vector: list[float], limit: int = 5) -> list[dict[str, 'Any']]:
        """Searches the LanceDB table using a query vector."""
        table = self._get_lancedb_table()
        # LanceDB returns a PyArrow table, we convert to pandas then dicts
        results = table.search(query_vector).limit(limit).to_pandas()
        return results.to_dict('records')

    async def get_last_update_time(
        self,
        brand: str,
        category: str,
    ) -> Optional[str]:
        """
        Return the most recent updated_at timestamp for the brand/category slice.

        Returns None when no products exist (caller handles empty-catalog case).

        Production equivalent:
            SELECT MAX(updated_at) FROM catalog_products
            WHERE brand = $1 AND category = $2;
        """

        products = await self.get_products(brand=brand, category=category)
        if not products:
            return None

        latest = max(
            products,
            key=lambda product: _parse_utc_timestamp(product.updated_at),
        )
        return latest.updated_at


class BaseCatalogRepository(ABC):
    """
    Optional abstract base for class-based repository implementations.

    Subclass this when building PostgreSQL/MongoDB/Atlan adapters so shared
    typing and documentation stay consistent across backends.
    """

    @abstractmethod
    async def get_products(
        self,
        brand: str,
        category: str,
    ) -> List[CatalogProduct]:
        raise NotImplementedError

    @abstractmethod
    async def get_last_update_time(
        self,
        brand: str,
        category: str,
    ) -> Optional[str]:
        raise NotImplementedError
