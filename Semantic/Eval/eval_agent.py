import asyncio
import json
import os
import sys
import logging

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from base_agent import BaseAgent
# from .Tools.metrics_evaluator_tool import SemanticMetricsEvaluatorTool
# from .Tools.diffy_api_tool import SemanticDiffyApiTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemanticEvalAgent(BaseAgent):
    """
    Evaluates the success of a semantic fix.
    """
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        super().__init__(model_name=model_name, enable_deep_rca=False)
        # self._register_tools()

    def _register_tools(self):
        # Placeholder for where you would register the specific tools for this agent
        pass

    def get_system_prompt(self) -> str:
        return """
        You are a Release Evaluation Agent for a Semantic Search system.
        A fix has been deployed. Your task is to evaluate its effectiveness.
        Return a final decision and summary in a structured JSON format.
        """

async def main():
    agent = SemanticEvalAgent()
    fix_input = {"summary": "Retrained embedding model to resolve drift."}
    result = await agent.run_agent(fix_input)
    print("Agent Output:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
