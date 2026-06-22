import asyncio
import json
import logging
import os
import sys

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from base_agent import BaseAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReleaseAgent(BaseAgent):
    """
    A simple agent that simulates the final release or deployment of a fix
    after it has been approved.
    """
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        super().__init__(model_name=model_name)

    def get_system_prompt(self) -> str:
        return """You are a Release Agent. Your task is to analyze the evaluation output and decide on the next release action.
Based on the 'eval_output' and 'approval_status', determine if the fix should be 'PROMOTE_CANARY', 'ROLLBACK', or 'NO_ACTION'.
Return your decision in a structured JSON format with a 'decision' key.

Example Output for Promotion:
```json
{
  "decision": "PROMOTE_CANARY",
  "summary": "The evaluation metrics are good, promoting the canary to production."
}
```

Example Output for Rollback:
```json
{
  "decision": "ROLLBACK",
  "summary": "The evaluation metrics are poor, initiating a rollback."
}
```

Example Output for No Action (e.g., waiting for more data or manual intervention):
```json
{
  "decision": "NO_ACTION",
  "summary": "Evaluation is inconclusive or requires further action. No automated action taken."
}
```
"""

async def main():
    agent = ReleaseAgent()
    approval_signal = {"status": "Deployment Approved", "final_ndcg": 0.92}
    result = await agent.run_agent(approval_signal)
    print("Agent Output:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
