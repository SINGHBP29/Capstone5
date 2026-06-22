from typing import List, Dict, Any

class SearchIndexRepository:
    async def get_catalog_products(self) -> List[Dict[str, Any]]:
        return [
            {"sku": "TH-XT-001", "updated_at": "2026-06-05T10:00:00Z"},
            {"sku": "TH-XT-002", "updated_at": "2026-06-05T10:00:00Z"}
        ]

    async def get_search_index(self) -> List[Dict[str, Any]]:
        return [
            {"sku": "TH-XT-001", "indexed_at": "2026-06-04T10:00:00Z"}
        ]

    async def get_latest_index_job(self) -> Dict[str, Any]:
        return {"status": "FAILED"}
