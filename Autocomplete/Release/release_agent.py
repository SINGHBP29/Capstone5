import asyncio
import json
import os
import sys
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from base_agent import BaseAgent

from .Tools.initiate_autocomplete_canary_tool import InitiateAutocompleteCanaryTool
from .Tools.execute_autocomplete_rollback_tool import ExecuteAutocompleteRollbackTool

logger = logging.getLogger(__name__)

class AutocompleteReleaseAgent(BaseAgent):
    """
    Manages the release of autocomplete changes (deterministic).
    """
    def __init__(self):
        super().__init__()
        
        self.canary_tool = InitiateAutocompleteCanaryTool()
        self.rollback_tool = ExecuteAutocompleteRollbackTool()

        self.register_tool(
            name="initiate_autocomplete_canary",
            func=self.canary_tool.run,
            description="Initiates a canary release for autocomplete tuning."
        )
        self.register_tool(
            name="execute_autocomplete_rollback",
            func=self.rollback_tool.run,
            description="Executes a rollback of autocomplete tuning."
        )

    async def run(self, eval_data: dict):
        """Runs the release agent deterministically based on Eval decision."""
        decision = eval_data.get("decision")
        
        if decision == "PROMOTE_TO_CANARY":
            result = await self.execute_tool("initiate_autocomplete_canary", {"args": {}})
            action = "initiate_autocomplete_canary"
        elif decision == "ROLLBACK_FIX":
            result = await self.execute_tool("execute_autocomplete_rollback", {"args": {}})
            action = "execute_autocomplete_rollback"
        else:
            return {"status": "no_action_needed", "summary": "No clear decision from evaluation."}
        
        return {
            "status": "success",
            "action_taken": action,
            "details": result,
        }

async def main():
    agent = AutocompleteReleaseAgent()
    eval_decision = {"decision": "PROMOTE_TO_CANARY"}
    result = await agent.run(eval_decision)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
