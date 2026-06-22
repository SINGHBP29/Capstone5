import asyncio
import json
import os
from dataclasses import dataclass
from typing import List, Any, Dict
import logging
from copy import deepcopy

from dotenv import load_dotenv
load_dotenv()

import fast_rlm
from base_agent import BaseAgent, _get_vertex_access_token

from .Tools.llm_inference_tool import LLMInferenceTool
from .Tools.patch_apply_tool import PatchApplyTool
from .Tools.vector_refresh_tool import VectorRefreshTool
from .Tools.reindex_trigger_tool import ReindexTriggerTool
from .Tools.synonym_generator_tool import SynonymGeneratorTool
from .Tools.synonym_apply_tool import SynonymApplyTool
from .Tools.semantic_intent_tool import SemanticIntentMappingTool
from .Tools.semantic_rules_tool import SemanticRulesTool
from Catalog.RootCause.Tools.catalog_repository import CatalogRepository

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =========================
# OUTPUT MODEL
# =========================
@dataclass
class FixAgentOutput:
    overall_status: str
    actions_taken: List[str]
    summary: str

# =========================
# HELPER
# =========================
def _format_root_cause_for_prompt(signal_data: dict[str, Any]) -> str:
    """Formats the root cause data into a string for the prompt."""
    root_cause = signal_data.get('root_cause', 'N/A')
    summary = signal_data.get('summary', 'N/A')
    evidence = signal_data.get('detailed_evidence', 'N/A')
    return (
        f"Problem: {root_cause}\\n"
        f"Summary: {summary}\\n"
        f"Evidence: {evidence}"
    )

# =========================
# FIX PROPOSAL AGENT
# =========================
class GoogleFixProposalAgent(BaseAgent):

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        # Call the parent constructor. enable_deep_rca is now controlled here.
        super().__init__(model_name=model_name, enable_deep_rca=True) 

        # Instantiate tools
        self.repo = CatalogRepository()
        self.inference_tool = LLMInferenceTool()
        self.patch_tool = PatchApplyTool(repository=self.repo)
        self.vector_tool = VectorRefreshTool(repository=self.repo)
        self.reindex_tool = ReindexTriggerTool()
        self.synonym_generator = SynonymGeneratorTool()
        self.synonym_apply = SynonymApplyTool(repository=self.repo)
        self.semantic_mapping = SemanticIntentMappingTool()
        self.semantic_rules = SemanticRulesTool(repository=self.repo)

        # Register all the specific tools for this agent
        self._register_fix_tools()

    def _register_fix_tools(self):
        """A single method to register all tools for this agent."""
        self.register_tool(
            name="llm_inference",
            func=self.inference_tool.run,
            description="Runs LLM inference to generate new catalog data."
        )
        self.register_tool(
            name="apply_patch",
            func=self.patch_tool.run,
            description="Applies a patch to the catalog data."
        )
        self.register_tool(
            name="vector_refresh",
            func=self.vector_tool.run,
            description="Refreshes the vector embeddings for the catalog."
        )
        self.register_tool(
            name="trigger_reindex",
            func=self.reindex_tool.run,
            description="Triggers a reindex of the search catalog."
        )
        self.register_tool(
            name="generate_synonyms",
            func=self.synonym_generator.run,
            description="Generates synonyms for a given query."
        )
        self.register_tool(
            name="apply_synonyms",
            func=self.synonym_apply.run,
            description="Applies synonym rules to the catalog."
        )
        self.register_tool(
            name="map_semantic_intent",
            func=self.semantic_mapping.run,
            description="Maps semantic intent to catalog attributes."
        )
        self.register_tool(
            name="apply_semantic_rules",
            func=self.semantic_rules.run,
            description="Applies semantic rules to the catalog."
        )
        # Note: The deep investigation tool is now registered in the BaseAgent
        # and renamed to avoid confusion. We will call it directly.

    def get_system_prompt(self) -> str:
        """Provides the specific system prompt for the Fix Proposal Agent."""
        return """You are a Fix Execution Agent. Your primary goal is to remediate issues identified by a Root Cause Analysis.

Given the RCA input, you MUST determine and execute the appropriate remediation tools to fix the issue.

Prioritize the `run_deep_rca_investigation` tool if the RCA indicates data quality issues, malformed data, or complex data cleanup is required. For other issues, choose from the available tools.

After executing the tools, provide a concise summary of the fixes applied.

Return the final output ONLY as a JSON string matching this exact schema:
{
  "overall_status": "success | partial | failed",
  "actions_taken": ["tool_name_1", "tool_name_2"],
  "summary": "A brief summary of what was done."
}
"""
    
    def format_user_message(self, signal_data: dict) -> str:
        """Overrides base method to format RCA data for the fix agent."""
        formatted_rca = _format_root_cause_for_prompt(signal_data)
        return f"Here is the Root Cause Analysis output. Please generate and execute a fix.\\n{formatted_rca}"

    # The run_agent method is now inherited from the BaseAgent.


# =========================
# MAIN FUNCTION
# =========================
async def main():
    agent = GoogleFixProposalAgent()

    # Example RCA input signal from the Root Cause Agent
    rca_input = {
        "overall_status": "SUCCESS",
        "root_cause": "Data corruption and missing attributes",
        "affected_capabilities": ["Product Discovery", "Data Freshness"],
        "summary": "Malformed encoding and missing attributes identified in raw data sample.",
        "detailed_evidence": [
            "run_deep_rca_investigation found malformed encoding.",
            "catalog_coverage confirmed missing attributes."
        ],
        "raw_data_sample": {
            "sku": "ABC-123",
            "description": "This is corrupted text with � characters"
        }
    }

    print("\n🚀 Running Fix Proposal Agent...\n")
    result = await agent.run_agent(rca_input)

    print("\n📦 FINAL OUTPUT\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())