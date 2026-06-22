import asyncio
import json
import logging
import os
import sys

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from base_agent import BaseAgent
from typing import Any, Dict

# from .Tools.adjust_prefix_weights_tool import AdjustPrefixWeightsTool
# from .Tools.boost_popular_entities_tool import BoostPopularEntitiesTool
# from .Tools.update_typo_dictionary_tool import UpdateTypoDictionaryTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutocompleteFixProposalAgent(BaseAgent):
    """
    Proposes and executes fixes for autocomplete issues.
    """
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        super().__init__(model_name=model_name, enable_deep_rca=True)
        # self._register_tools()

    def _register_tools(self):
        # Placeholder for where you would register the specific tools for this agent
        pass

    def get_system_prompt(self) -> str:
        return """You are a Fix Proposal agent for e-commerce autocomplete systems.
Based on the provided root cause analysis, propose and execute a fix.
Return a summary of the actions taken in a structured JSON format.
"""

    def format_user_message(self, signal_data: Dict[str, Any]) -> str:
        # Assuming signal_data contains RCA output
        rca_summary = signal_data.get("summary", "No RCA summary provided.")
        return f"Here is the Root Cause Analysis output. Please propose and execute a fix.\\nRCA Summary: {rca_summary}"

async def main():
    agent = AutocompleteFixProposalAgent()
    rca_output = {"root_cause": "The suggestion model is over-weighting unpopular terms.", "summary": "Model bias found."}
    result = await agent.run_agent(rca_output)
    print("Agent Output:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
