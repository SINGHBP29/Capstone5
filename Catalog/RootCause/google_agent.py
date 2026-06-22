import asyncio
import json
import os
from dataclasses import dataclass, asdict, field
from typing import Any, Callable
import logging
import io
import subprocess
        
from dotenv import load_dotenv

load_dotenv()

import fast_rlm
from fast_rlm import RLMConfig

from base_agent import BaseAgent
from Catalog.RootCause.Tools.common_signals import sample_signal
from Catalog.RootCause.Tools.catalog_coverage_tool import CatalogCoverageTool
from Catalog.RootCause.Tools.schema_validation import CatalogSchemaValidationTool
from Catalog.RootCause.Tools.freshness import CatalogFreshnessTool
from Catalog.RootCause.Tools.historical_intent import CatalogHistoricalIntentTool
from Catalog.RootCause.Tools.search_Quality import CatalogSearchQualityTool
from Catalog.RootCause.Tools.capability_mapping_tools import CatalogCapabilityMappingTool
from Catalog.RootCause.Tools.catalog_repository import CatalogRepository
from Catalog.RootCause.Tools.embedding import CatalogEmbeddingTool
from Catalog.RootCause.Tools.vector_sync import CatalogVectorSyncTool
from Catalog.RootCause.Tools.query_intent import QueryIntentDriftTool
from Catalog.RootCause.Tools.index import SearchIndexCoverageTool
from Catalog.RootCause.Tools.query_intent_repository import QueryIntentRepository
from Catalog.RootCause.Tools.search_index_repository import SearchIndexRepository
# from Catalog.RootCause.Tools.common_signals import sample_signal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HeartbeatingStream(io.StringIO):
    def write(self, s):
        if s and s.strip():
            details = s[:3800]  # Truncate to avoid hitting Temporal heartbeat limits
            try:
                activity.heartbeat(details)
                logger.info(f"Heartbeat: {details}")  # Also log to worker console
            except RuntimeError:  # Thrown when not in an activity context
                pass
        super().write(s)


# =========================
# OUTPUT MODEL
# =========================

@dataclass
class AgentOutput:
    overall_status: str
    root_cause: str
    affected_capabilities: list[str]
    summary: str
    detailed_evidence: list[str]
    executed_tools: list[str] = field(default_factory=list)


# =========================
# ADK AGENT
# =========================
def _get_vertex_access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()

class GoogleRootCauseAgent(BaseAgent):

    def __init__(self, model: str = "gemini-2.5-flash"):
        super().__init__(model_name="gemini-2.5-flash", enable_deep_rca=True)

        self.repo = CatalogRepository()
        self.query_repo = QueryIntentRepository()
        self.search_repo = SearchIndexRepository()

        # -------------------------
        # NATIVE TOOL IMPLEMENTATIONS
        # -------------------------
        self.register_tool(name="catalog_coverage", func=CatalogCoverageTool(self.repo).run, description="Checks for missing products or attributes in the catalog.")
        self.register_tool(name="schema_validation", func=CatalogSchemaValidationTool(self.repo).run, description="Validates the catalog data against a predefined schema.")
        self.register_tool(name="freshness_check", func=CatalogFreshnessTool(self.repo).run, description="Checks the freshness of catalog data.")
        self.register_tool(name="historical_intent", func=CatalogHistoricalIntentTool(self.repo).run, description="Analyzes historical search intent data for patterns.")
        self.register_tool(name="search_quality", func=CatalogSearchQualityTool(self.repo).run, description="Evaluates the quality of search results for specific queries.")
        self.register_tool(name="capability_mapping", func=CatalogCapabilityMappingTool(self.repo).run, description="Maps identified root causes to affected business capabilities.")
    
    def get_system_prompt(self) -> str:
        return """You are an expert Root Cause Analysis agent specializing in e-commerce catalog and search systems.
Your primary goal is to identify the root cause of issues affecting product catalogs and search quality.
You have access to a suite of tools to investigate various aspects of the catalog and search index.
When a signal is provided, methodically use your tools to:
1. Understand the nature of the problem (e.g., missing products, incorrect data, search relevance issues) from the `description` field of the signal.
2. Based on the problem, select and use the most appropriate tools from your toolkit to gather evidence.
3. If the signal includes a `raw_data_sample` and the problem suggests data corruption or malformed data, use the `run_deep_rca_investigation` tool to analyze *only* the relevant portion of the `raw_data_sample` for corruption or issues. Do NOT pass the entire signal to `run_deep_rca_investigation`.
4. Analyze all evidence to pinpoint the exact root cause.
5. Identify affected business capabilities (e.g., Product Discovery, Search Relevance, Data Freshness).
6. Formulate a clear, concise root cause statement.
7. Provide detailed evidence supporting your conclusion, including findings from any tools used.

Always respond with a structured JSON output using the `AgentOutput` format, including:
- `overall_status`: "SUCCESS" if root cause is found, "FAILED" if not.
- `root_cause`: A clear and concise statement of the root cause.
- `affected_capabilities`: A list of business capabilities impacted by this root cause.
- `summary`: A brief summary of your findings, specifically mentioning `raw_data_sample` analysis if performed.
- `detailed_evidence`: A list of strings, each providing specific evidence supporting the root cause (e.g., tool outputs, data points).
- `executed_tools`: A list of tools that were executed during the investigation, including `run_deep_rca_investigation` if used.

Example of a good chain of thought:
1. User provides a signal about missing products and a raw data sample in `signal.raw_data_sample`.
2. I identify the problem as 'missing products'.
3. I use `catalog_coverage` to check if the products are in the catalog.
4. If `catalog_coverage` confirms products are missing, and the `signal.raw_data_sample` contains relevant data (e.g., product IDs, a small JSON snippet of potentially corrupted data), I use `run_deep_rca_investigation` to analyze *that specific part* of the raw data.
5. Based on all tool outputs, I identify the root cause (e.g., data corruption and missing attributes) and compile the `AgentOutput`.

If you encounter an issue that your native tools cannot resolve, or if deep data inspection is required for a small, targeted `raw_data_sample` (as indicated by the problem description), use `run_deep_rca_investigation` to perform a more in-depth, recursive analysis.
        """
    # The run_agent method is now inherited from BaseAgent.
    # The default format_user_message in the base class is sufficient.


async def main():
    agent = GoogleRootCauseAgent()
    
    # Using the sample_signal from common_signals.py
    # You can modify this signal to test different scenarios
    signal_data = {
        "signal_id": "unknown-error-999",
        "description": "System performance degraded, logs show random unstructured errors related to data formats. Need deep analysis of the raw DB string to find what is corrupted."
   }
    sample_signal2 = "Catalog/search_events.jsonl"

    print(f"Running agent with signal: {json.dumps(sample_signal2, indent=2)}")
    result = await agent.run_agent(sample_signal2)
    print("\nAgent Output:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())

