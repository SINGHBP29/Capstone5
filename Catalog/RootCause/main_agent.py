import asyncio
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Union, Optional
import os # Import os for environment variable access
from dotenv import load_dotenv # Import load_dotenv

from langchain.agents.executors import AgentExecutor
from langchain.agents.react.agent import create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

# Import our custom tools
from .Tools.catalog_coverage_tool import CatalogCoverageTool, CatalogCoverageResult
from .Tools.schema_validation import CatalogSchemaValidationTool, CatalogSchemaValidationResult
from .Tools.freshness import CatalogFreshnessTool, CatalogFreshnessResult
from .Tools.historical_intent import CatalogHistoricalIntentTool, HistoricalIntentResult
from .Tools.search_Quality import CatalogSearchQualityTool, SearchQualityResult
from .Tools.capability_mapping_tools import CatalogCapabilityMappingTool, CapabilityMappingResult
from .Tools.catalog_repository import CatalogRepository # Assuming repository is needed by tools
from .Tools.common_signals import sample_signal # For local testing


class RootCauseAgent:
    def __init__(self, llm: ChatGoogleGenerativeAI, repository: CatalogRepository):
        self.repository = repository
        self.llm = llm

        # Initialize our custom tools
        self.coverage_tool_instance = CatalogCoverageTool(self.repository)
        self.schema_tool_instance = CatalogSchemaValidationTool(self.repository)
        self.freshness_tool_instance = CatalogFreshnessTool(self.repository)
        self.historical_intent_tool_instance = CatalogHistoricalIntentTool(self.repository)
        self.search_quality_tool_instance = CatalogSearchQualityTool(self.repository)
        self.capability_mapping_tool_instance = CatalogCapabilityMappingTool(self.repository)

        # Wrap our custom tools for LangChain
        self.tools = [
            Tool(
                name="CatalogCoverageTool",
                func=lambda s: asyncio.run(self.coverage_tool_instance.run(json.loads(s))),
                description="Analyzes catalog coverage for a brand/category slice. Input is a JSON string of signal_data.",
            ),
            Tool(
                name="CatalogSchemaValidationTool",
                func=lambda s: asyncio.run(self.schema_tool_instance.run(json.loads(s))),
                description="Validates catalog records against the expected schema. Input is a JSON string of signal_data.",
            ),
            Tool(
                name="CatalogFreshnessTool",
                func=lambda s: asyncio.run(self.freshness_tool_instance.run(json.loads(s))),
                description="Determines whether catalog data is stale. Input is a JSON string of signal_data.",
            ),
            Tool(
                name="CatalogHistoricalIntentTool",
                func=lambda s: asyncio.run(self.historical_intent_tool_instance.run(json.loads(s))),
                description="Analyzes historical search queries for a given catalog entity. Input is a JSON string of signal_data.",
            ),
            Tool(
                name="CatalogSearchQualityTool",
                func=lambda s: asyncio.run(self.search_quality_tool_instance.run(json.loads(s))),
                description="Evaluates search quality based on product data and a search query. Input is a JSON string of signal_data with 'search_query' field.",
            ),
            Tool(
                name="CatalogCapabilityMappingTool",
                func=lambda s: asyncio.run(self.capability_mapping_tool_instance.run(json.loads(s))),
                description="Maps catalog data issues to affected search capabilities by running other diagnostic tools. Input is a JSON string of signal_data.",
            ),
        ]

        # Define the agent's prompt
        self.prompt = PromptTemplate.from_template("""
        You are a Root Cause Analysis Agent for SearchOps. Your goal is to analyze issues related to catalog data impacting search quality.
        You have access to the following tools: {tools}

        Based on the user's signal, use the appropriate tools to:
        1. Identify potential root causes (e.g., stale data, schema violations, coverage gaps).
        2. Determine affected search capabilities.
        3. Provide clear evidence for your findings.

        The input will be a JSON string representing a 'signal_data'.
        You should always output a JSON string with the following structure:
        {{
            "overall_status": "healthy" | "degraded" | "failed",
            "root_cause": "none" | "stale_catalog_data" | "catalog_schema_violation" | "catalog_coverage_gap" | "low_search_relevance" | "embedding_failure" | "missing_catalog_entity",
            "affected_capabilities": ["list_of_affected_capabilities"],
            "summary": "A concise summary of the findings and recommended actions.",
            "detailed_evidence": ["list_of_detailed_evidence_from_tools"]
        }}

        Begin!

        Signal: {input}
        {agent_scratchpad}
        """)

        # Create the agent
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True) # Modified as per request

    async def run_agent(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.agent_executor.invoke({"input": json.dumps(signal_data)})
        return json.loads(result["output"])


async def main():
    load_dotenv() # Load environment variables from .env file
    # Ensure your GOOGLE_API_KEY is set as an environment variable
    # For example: export GOOGLE_API_KEY="YOUR_API_KEY"
    if "GOOGLE_API_KEY" not in os.environ:
        raise ValueError("GOOGLE_API_KEY environment variable not set. Please set it before running the agent.")

    llm = ChatGoogleGenerativeAI(model="gemini-pro")

    repository = CatalogRepository()
    agent_instance = RootCauseAgent(llm, repository)

    print("\n--- Running Root Cause Agent with sample_signal ---")
    final_result = await agent_instance.run_agent(sample_signal)
    print("\n--- Root Cause Agent Final Result ---")
    print(json.dumps(final_result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
