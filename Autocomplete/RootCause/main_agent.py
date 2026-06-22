import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from base_agent import BaseAgent

from .Tools.prefix_matching_agent import PrefixMatchingAgent
from .Tools.popularity_bias_agent import PopularityBiasAgent
from .Tools.typo_tolerance_agent import TypoToleranceAgent

logger = logging.getLogger(__name__)

class AutocompleteRootCauseAgent(BaseAgent):
    """Orchestrates specialized agents for autocomplete root cause analysis."""
    
    def __init__(self):
        super().__init__(model_name="gemini-2.5-flash", enable_deep_rca=True)
        self.prefix_agent = PrefixMatchingAgent()
        self.popularity_agent = PopularityBiasAgent()
        self.typo_agent = TypoToleranceAgent()

        self.register_tool(name="run_prefix_matching_analysis", func=self.prefix_agent.run, description="Analyzes prefix matching issues.")
        self.register_tool(name="run_popularity_bias_analysis", func=self.popularity_agent.run, description="Analyzes popularity bias issues.")
        self.register_tool(name="run_typo_tolerance_analysis", func=self.typo_agent.run, description="Analyzes typo tolerance issues.")

    def get_system_prompt(self) -> str:
        return """You are a Root Cause Analysis agent for an autocomplete system. Your goal is to identify the root cause of issues affecting autocomplete suggestions.

When a signal is provided, methodically use your tools to:
1. Understand the nature of the problem (e.g., no results for a common misspelling).
2. Gather evidence using the appropriate tools.
3. Analyze the evidence to pinpoint the exact root cause.
4. Formulate a clear, concise root cause statement.

If the issue is complex or not covered by the standard tools, use `run_deep_rca_investigation` to perform a deeper analysis.

Always respond with a structured JSON output, including:
- `root_cause`: A clear and concise statement of the root cause.
- `summary`: A brief summary of your findings.
- `detailed_evidence`: A list of strings, each providing specific evidence supporting the root cause.
- `executed_tools`: A list of tools that were executed during the investigation.
"""

    async def run(self, signal_data: dict):
        """Runs the root cause analysis pipeline."""
        return await self.run_agent(signal_data)


async def main():
    agent = AutocompleteRootCauseAgent()
    signal = {"search_input": "shos", "issue": "Autocomplete shows no results for typo"}
    result = await agent.run(signal)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
