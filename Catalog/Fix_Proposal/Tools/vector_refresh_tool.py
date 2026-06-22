from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class VectorRefreshTool:
    """Takes newly patched catalog data, re-embeds it, and syncs to the vector DB."""
    
    def __init__(self, repository=None):
        self.repository = repository

    async def run(self, signal: dict[str, Any]) -> dict[str, Any]:
        skus = signal.get("affected_skus", ["TH-XT-001", "TH-XT-002", "TH-XT-003"])
        
        if not self.repository:
            return {
                "tool_name": "VectorRefreshTool",
                "status": "failed",
                "message": "Repository not provided."
            }

        # 1. We fetch the LATEST data from the catalog (which PatchApplyTool just updated!)
        # In a real setup, we'd fetch by SKU. We'll simulate fetching all and filtering.
        brand = signal.get("catalog_entity", {}).get("brand", "Trailhead XT")
        category = signal.get("catalog_entity", {}).get("category", "Footwear")
        all_products = await self.repository.get_products(brand=brand, category=category)
        
        target_products = [p for p in all_products if p.sku in skus]
        
        # 2. Generate new embeddings (mocked here as simple float arrays)
        # The new embedding values logically reflect the newly patched 'waterproof' data
        vectors_to_upsert = {}
        for p in target_products:
            # Simple hash logic to generate a consistent dummy vector
            mock_vector = [
                len(p.brand) * 0.1,
                len(p.category) * 0.1,
                1.0 if p.waterproof_flag else 0.0, # Semantic value changed!
                len(p.terrain_type) * 0.1 if p.terrain_type else 0.0
            ]
            vectors_to_upsert[p.sku] = mock_vector
            
        # 3. Upsert into the Vector DB
        await self.repository.upsert_product_vectors(vectors_to_upsert)
        
        logger.info(f"Upserted vectors for {len(vectors_to_upsert)} SKUs into Vector DB.")

        return {
            "tool_name": "VectorRefreshTool",
            "status": "success",
            "message": f"Generated new embeddings and synced {len(skus)} SKUs to the Vector Database."
        }
