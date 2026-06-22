import asyncio
import json
import os
import sys
from dataclasses import dataclass
import logging
from typing import Callable

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from base_agent import BaseAgent
from .Tools.diffy_api_tool import DiffyApiTool
from .Tools.metrics_evaluator_tool import MetricsEvaluatorTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EvalOutput:
    overall_status: str
    decision: str
    regression_risk: str
    summary: str

class GoogleEvalAgent(BaseAgent):
    """
    Evaluates the success of a fix by analyzing traffic comparison reports.
    """
    def __init__(self, model_name="gemini-2.5-flash"):
        super().__init__(model_name=model_name, enable_deep_rca=False)
        
        self.diffy_tool = DiffyApiTool()
        self.metrics_tool = MetricsEvaluatorTool()

        self.register_tool(
            name="fetch_diffy_report", 
            func=self.diffy_tool.run, 
            description="Fetches a traffic comparison report from the Diffy API by its ID."
        )
        self.register_tool(
            name="evaluate_metrics", 
            func=self.metrics_tool.run, 
            description="Calculates NDCG and other relevance metrics from a Diffy report to evaluate ranking quality."
        )

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
    ):
        """Registers a Python callable as a tool for the fast-rlm agent."""

        async def wrapper(*args, **kwargs):
            # Re-inspect the original function's signature *inside* the wrapper
            # to ensure correct scope, even when run in a sub-agent.
            func_sig = inspect.signature(func)
            needs_signal = "signal" in func_sig.parameters
            needs_signal_data = "signal_data" in func_sig.parameters

            # Auto-inject signal data if the tool function expects it
            if (needs_signal and "signal" not in kwargs) or \
               (needs_signal_data and "signal_data" not in kwargs):
                if self.current_signal_data is None:
                    raise ValueError(f"Tool '{name}' needs signal data but it is not set.")
                # Provide both for convenience, as some tools might use one or the other
                kwargs["signal"] = self.current_signal_data
                kwargs["signal_data"] = self.current_signal_data

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return await asyncio.to_thread(func, *args, **kwargs)

        wrapper.__name__ = name
        wrapper.__doc__ = func.__doc__ or description
        self._tool_functions[name] = wrapper
        logger.info(f"Registered tool: {name}")

    def get_system_prompt(self) -> str:
        return """
        You are a Release Evaluation Agent for a Search Engineering team.
        A fix has been deployed to a shadow environment and compared against production using live traffic.

        You MUST:
        1. Run `fetch_diffy_report` using the `diff_id` from the input signal to get the raw difference data.
        2. Pass the results of the report into `evaluate_metrics` to compare baseline and shadow ranking quality.
        3. Analyze the outputs from the metrics evaluation to determine if the fix was successful.
        4. Make a final decision on whether to promote the fix to production or roll it back.

        Return the final output ONLY as a JSON string matching this exact schema:
        {
            "overall_status": "success | failed",
            "decision": "PROMOTE_TO_CANARY | ROLLBACK_FIX",
            "regression_risk": "low | medium | high",
            "summary": "A concise justification of your decision based on the metrics."
        }
        """

    # The run_agent method is inherited from BaseAgent and does not need to be redefined.

# =========================
# MAIN
# =========================
async def main():
    print("\n🚀 Running Eval Agent (Diffy API Evaluator)...\n")
    agent = GoogleEvalAgent()
    
    # In a real pipeline, this would receive the Diffy report ID from a CI/CD job
    # This mock ID will trigger the mock response in the DiffyApiTool
    input_signal = {
        "diff_id": "c28b-4b1e-b3f9-7153d3e690f3", 
        "context": "Catalog coverage gap patched for Trailhead XT footwear."
    }

    result = await agent.run_agent(input_signal)
    
    print("\n📦 FINAL EVALUATION REPORT:\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())