import asyncio
import json
from dataclasses import asdict

from base_agent import BaseGoogleADKAgent
from .Tools.catalog_coverage_tool import CatalogCoverageTool
from .Tools.schema_validation import CatalogSchemaValidationTool
from .Tools.freshness import CatalogFreshnessTool
from .Tools.historical_intent import CatalogHistoricalIntentTool
from .Tools.search_Quality import CatalogSearchQualityTool
from .Tools.capability_mapping_tools import CatalogCapabilityMappingTool
from .Tools.catalog_repository import CatalogRepository
from .Tools.embedding import CatalogEmbeddingTool
from .Tools.vector_sync import CatalogVectorSyncTool
from .Tools.query_intent import QueryIntentDriftTool
from .Tools.index import SearchIndexCoverageTool
from .Tools.query_intent_repository import QueryIntentRepository
from .Tools.search_index_repository import SearchIndexRepository
from .Tools.common_signals import sample_signal

class RootCauseAgent(BaseGoogleADKAgent):
    """
    The full Root Cause Analysis Agent utilizing all tools and fast-rlm deep investigation.
    """
    def __init__(self):
        super().__init__(model_name="gemini-2.5-flash", enable_deep_rca=True)
        
        repo = CatalogRepository()
        query_repo = QueryIntentRepository()
        search_repo = SearchIndexRepository()

        # Register tools
        self.register_tool("catalog_coverage", CatalogCoverageTool(repo).run, "Check catalog coverage gaps")
        self.register_tool("schema_validation", CatalogSchemaValidationTool(repo).run, "Validate catalog schema correctness")
        self.register_tool("freshness_check", CatalogFreshnessTool(repo).run, "Check if catalog data is stale")
        self.register_tool("historical_intent", CatalogHistoricalIntentTool(repo).run, "Analyze historical search intent")
        self.register_tool("search_quality", CatalogSearchQualityTool(repo).run, "Evaluate search relevance quality")
        self.register_tool("capability_mapping", CatalogCapabilityMappingTool(repo).run, "Map catalog issues to capabilities")
        self.register_tool("catalog_embedding", CatalogEmbeddingTool(repo).run, "Generate embeddings for catalog products")
        self.register_tool("vector_sync", CatalogVectorSyncTool(repo).run, "Sync catalog embeddings to vector database")
        self.register_tool("query_intent_drift", QueryIntentDriftTool(query_repo).run, "Detect if search query intent is drifting")
        self.register_tool("search_index_coverage", SearchIndexCoverageTool(search_repo).run, "Check if search index misses items from catalog")

    def get_system_prompt(self) -> str:
        return """
        You are a Root Cause Analysis Agent for a retail catalog. Your primary role is to orchestrate diagnostic tools.

        ROUTING LOGIC:
        - For standard catalog issues (missing attributes, stale data, index coverage), use specific tools like `catalog_coverage`, `freshness_check`, `search_index_coverage`, etc.
        - If the issue is complex, unknown, or requires deep data analysis beyond what the standard tools provide, use `run_deep_rca_investigation`.
        - ALWAYS use `capability_mapping` at the end to aggregate findings.

        You MUST:
        1. Call necessary tools to diagnose the signal.
        2. Return ONLY a valid JSON string matching the output schema.
        """

class CatalogHealthAgent(BaseGoogleADKAgent):
    """
    A lightweight, specialized agent that only checks coverage and freshness.
    No deep RCA enabled.
    """
    def __init__(self):
        super().__init__(model_name="gemini-2.5-flash", enable_deep_rca=False)
        repo = CatalogRepository()
        
        self.register_tool("catalog_coverage", CatalogCoverageTool(repo).run, "Check catalog coverage gaps")
        self.register_tool("freshness_check", CatalogFreshnessTool(repo).run, "Check if catalog data is stale")

    def get_system_prompt(self) -> str:
        return """
        You are a Catalog Health Specialist. 
        Your ONLY job is to determine if products are missing attributes or are stale.
        Run `catalog_coverage` and `freshness_check`.
        Synthesize their results into the final required JSON schema.
        """

# Example execution
async def main():
    print("\n🚀 Running Specialized CatalogHealthAgent...")
    health_agent = CatalogHealthAgent()
    result = await health_agent.run_agent(sample_signal)
    print("\n📦 Health Agent Output:")
    print(json.dumps(asdict(result), indent=2))
    
    print("\n\n🚀 Running Full RootCauseAgent...")
    rca_agent = RootCauseAgent()
    result2 = await rca_agent.run_agent(sample_signal)
    print("\n📦 Root Cause Agent Output:")
    print(json.dumps(asdict(result2), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
