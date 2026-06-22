"""Release agent for the semantic pipeline."""
import asyncio
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from base_agent import BaseAgent
from .Tools.canary_router_tool import SemanticCanaryRouterTool
from .Tools.rollback_tool import SemanticRollbackTool

class SemanticReleaseAgent(BaseAgent):
    """
    Manages the release of semantic index changes, either by
    initiating a canary release or rolling back a failed fix.
    """
    def __init__(self):
        super().__init__(model_name="gemini-2.5-flash")
        self.canary_tool = SemanticCanaryRouterTool()
        self.rollback_tool = SemanticRollbackTool()

        self.register_tool(name="initiate_semantic_canary", func=self.canary_tool.run, description="Initiates a canary release for the semantic index.")
        self.register_tool(name="execute_semantic_rollback", func=self.rollback_tool.run, description="Executes a rollback of the semantic index.")

    def get_system_prompt(self) -> str:
        return """
        You are a Release Orchestration Agent for a Semantic Search system.
        You have received a decision from the EvalAgent.

        If the decision is 'PROMOTE_TO_CANARY', run `initiate_semantic_canary`.
        If the decision is 'ROLLBACK_FIX', run `execute_semantic_rollback`.

        Return a JSON summary of the action taken.
        """

    async def run(self, eval_data: dict):
        """Runs the release agent."""
        decision = eval_data.get("decision")
        if decision == "PROMOTE_TO_CANARY":
            result = await self.canary_tool.run()
            action = "initiate_semantic_canary"
        elif decision == "ROLLBACK_FIX":
            result = await self.rollback_tool.run()
            action = "execute_semantic_rollback"
        else:
            return {"status": "no_action_needed", "summary": "No clear decision from evaluation."}
        
        return {
            "status": "success",
            "action_taken": action,
            "details": result.__dict__,
        }

async def main():
    agent = SemanticReleaseAgent()
    
    # Test PROMOTE
    eval_promote = {"decision": "PROMOTE_TO_CANARY"}
    result_promote = await agent.run(eval_promote)
    print("--- Promotion Case ---")
    print(json.dumps(result_promote, indent=2))

    # Test ROLLBACK
    eval_rollback = {"decision": "ROLLBACK_FIX"}
    result_rollback = await agent.run(eval_rollback)
    print("\\n--- Rollback Case ---")
    print(json.dumps(result_rollback, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
