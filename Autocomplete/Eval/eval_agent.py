import asyncio
import json
import sys
import logging
from dataclasses import asdict
from typing import Any, Dict, List

import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from base_agent import BaseAgent

from .Tools.evaluate_autocomplete_ctr_tool import EvaluateAutocompleteCtrTool
from .Tools.fetch_autocomplete_diffy_report_tool import FetchAutocompleteDiffyReportTool

logger = logging.getLogger(__name__)

class AutocompleteEvalAgent(BaseAgent):
    """
    Evaluates the success of an autocomplete fix.
    """
    def __init__(self):
        super().__init__()
        
        self.ctr_tool = EvaluateAutocompleteCtrTool()
        self.diffy_tool = FetchAutocompleteDiffyReportTool()

        self.register_tool(
            name="evaluate_autocomplete_ctr",
            func=self.ctr_tool.run,
            description="Evaluates autocomplete CTR for the modified prefixes."
        )
        self.register_tool(
            name="fetch_autocomplete_diffy_report",
            func=self.diffy_tool.run,
            description="Checks for regressions in autocomplete results."
        )

    async def fast_rlm(self, fix_data: dict) -> list[str]:
        tools = []
        if any(
            key in fix_data
            for key in ("shadow_evaluation", "ctr_metrics", "baseline_ctr", "shadow_ctr")
        ):
            tools.append("evaluate_autocomplete_ctr")
        if any(key in fix_data for key in ("diffy_report", "diff_id", "regression_report")):
            tools.append("fetch_autocomplete_diffy_report")
        return tools

    @staticmethod
    def _normalize_result(result: Any) -> Dict[str, Any]:
        if hasattr(result, "__dataclass_fields__"):
            return asdict(result)
        if isinstance(result, dict):
            return result
        return {"status": "failed", "message": str(result)}

    async def run(self, fix_data: dict):
        """Runs the evaluation agent."""
        tools_to_run = await self.fast_rlm(fix_data)
        logger.info(f"Fast-RLM selected evaluation tools: {tools_to_run}")

        if isinstance(fix_data.get("shadow_evaluation"), dict) and "evaluate_autocomplete_ctr" not in tools_to_run:
            tools_to_run.append("evaluate_autocomplete_ctr")
        if (
            isinstance(fix_data.get("diffy_report"), dict)
            or fix_data.get("diff_id")
        ) and "fetch_autocomplete_diffy_report" not in tools_to_run:
            tools_to_run.append("fetch_autocomplete_diffy_report")

        metrics_status = "failed"
        diffy_status = "failed"
        regressions_found = None
        detailed_evidence: List[str] = []

        if "evaluate_autocomplete_ctr" in tools_to_run:
            metrics_raw = await self.execute_tool("evaluate_autocomplete_ctr", fix_data)
            metrics_result = self._normalize_result(metrics_raw)
            metrics_status = metrics_result.get("status", "failed")
            detailed_evidence.append(metrics_result.get("summary", "Autocomplete CTR evaluated."))
            
        if "fetch_autocomplete_diffy_report" in tools_to_run:
            diffy_raw = await self.execute_tool("fetch_autocomplete_diffy_report", fix_data)
            diffy_result = self._normalize_result(diffy_raw)
            diffy_status = diffy_result.get("status", "failed")
            regressions_found = diffy_result.get("regressions_found")
            detailed_evidence.append(diffy_result.get("summary", "Autocomplete diff report fetched."))

        if metrics_status == "failed" and diffy_status == "failed":
            return {
                "overall_status": "failed",
                "decision": "ROLLBACK_FIX",
                "summary": "No real autocomplete shadow data was provided for evaluation.",
                "detailed_evidence": [
                    "Provide shadow CTR metrics or a real diffy_report/diff_id."
                ],
            }

        decision = "PROMOTE_TO_CANARY"
        summary = "Real autocomplete shadow evaluation passed."

        if (
            metrics_status != "success"
            or diffy_status != "success"
            or (regressions_found or 0) > 0
        ):
            decision = "ROLLBACK_FIX"
            summary = "Real autocomplete shadow evaluation failed or reported regressions."
            
        return {
            "overall_status": "success" if decision == "PROMOTE_TO_CANARY" else "failed",
            "decision": decision,
            "summary": summary,
            "detailed_evidence": detailed_evidence,
        }

async def main():
    agent = AutocompleteEvalAgent()
    fix_input = {"actions_taken": ["update_typo_dictionary"]}
    result = await agent.run(fix_input)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
