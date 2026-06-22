import asyncio
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import logging

from google.genai import types as genai_types

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from base_agent import BaseAgent

from Catalog.Release.Tools.canary_router_tool import CanaryRouterTool
from Catalog.Release.Tools.rollback_tool import RollbackTool

logger = logging.getLogger(__name__)

@dataclass
class ReleaseOutput:
    final_status: str
    action_taken: str
    summary: str


class ReleaseAgent(BaseAgent):
    """
    Agent responsible for safely deploying approved changes via canaries
    or executing rollbacks if evaluation fails.
    """
    def __init__(self):
        super().__init__(model_name="gemini-2.5-flash", enable_deep_rca=False)
        
        self.canary_tool = CanaryRouterTool()
        self.rollback_tool = RollbackTool()

        self.register_tool(
            name="initiate_canary_release", 
            func=self.canary_tool.run, 
            description="Shifts a small percentage of live user traffic to a newly deployed fix."
        )
        self.register_tool(
            name="execute_rollback", 
            func=self.rollback_tool.run, 
            description="Reverts all traffic back to the stable production index if a fix fails evaluation."
        )

    def get_system_prompt(self) -> str:
        return """
        You are a Release Orchestration Agent for an E-commerce Search Platform.
        You have just received a final 'decision' from the EvalAgent.

        Your job is to execute the correct deployment action:
        - If the decision is 'PROMOTE_TO_CANARY', you MUST run `initiate_canary_release`.
        - If the decision is 'ROLLBACK', you MUST run `execute_rollback`.

        Return ONLY a valid JSON string with the final status and a summary of your action.
        """

if __name__ == "__main__":
    async def main():
        agent = ReleaseAgent()

        # --- TEST 1: SIMULATE A SUCCESSFUL PROMOTION ---
        print("\n🚀 Running Release Agent (PROMOTION case)...\n")
        eval_output_promote = {
            "decision": "PROMOTE_TO_CANARY",
            "summary": "Shadow test passed with +75% improvement in NDCG@10."
        }
        result_promote = await agent.run_agent(eval_output_promote)
        print("\n📦 FINAL RELEASE REPORT (PROMOTION):\n")
        print(json.dumps(result_promote, indent=2))

        # --- TEST 2: SIMULATE A FAILED ROLLBACK ---
        print("\n\n🚀 Running Release Agent (ROLLBACK case)...\n")
        eval_output_rollback = {
            "decision": "ROLLBACK",
            "summary": "Shadow test failed with a -15% regression in NDCG@10."
        }
        result_rollback = await agent.run_agent(eval_output_rollback)
        print("\n📦 FINAL RELEASE REPORT (ROLLBACK):\n")
        print(json.dumps(result_rollback, indent=2))

    asyncio.run(main())
