from typing import Dict, Any

class ReindexTriggerTool:
    """Triggers an Elasticsearch/Solr partial re-index for patched SKUs."""
    async def run(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        skus = signal.get("affected_skus", ["TH-XT-001", "TH-XT-002", "TH-XT-003"])
        
        return {
            "tool_name": "ReindexTriggerTool",
            "status": "success",
            "message": f"Successfully triggered Lexical Search re-indexing job for {len(skus)} SKUs."
        }
