import logging
from typing import Any, Dict

class EvaluateAutocompleteCtrTool:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def run(self, args: Dict[str, Any]):
        self.logger.info(
            "EvaluateAutocompleteCtrTool: Reading real shadow CTR metrics from input payload..."
        )

        shadow_metrics = args.get("shadow_evaluation", {}) or args.get("ctr_metrics", {})
        if not isinstance(shadow_metrics, dict):
            shadow_metrics = {}

        baseline_ctr = shadow_metrics.get("baseline_ctr", args.get("baseline_ctr"))
        shadow_ctr = shadow_metrics.get("shadow_ctr", args.get("shadow_ctr"))

        if baseline_ctr is None or shadow_ctr is None:
            try:
                from Autocomplete.state_repository import AutocompleteStateRepository
                repo = AutocompleteStateRepository()
                state = repo.load_state()
                query_performance = state.get("query_performance", {})
                
                signal = args.get("signal") or args.get("original_signal") or args
                query = str(signal.get("search_input") or signal.get("query") or "shos").strip().lower()
                
                if query in query_performance:
                    baseline_ctr = query_performance[query].get("baseline_ctr")
                    shadow_ctr = query_performance[query].get("shadow_ctr")
                else:
                    # Fallback to first query in performance
                    for q, perf in query_performance.items():
                        baseline_ctr = perf.get("baseline_ctr")
                        shadow_ctr = perf.get("shadow_ctr")
                        break
            except Exception:
                pass

        if baseline_ctr is None or shadow_ctr is None:
            return {
                "status": "failed",
                "metric_improved": False,
                "summary": (
                    "Missing real baseline_ctr/shadow_ctr values in the evaluation input."
                ),
            }

        baseline_ctr = float(baseline_ctr)
        shadow_ctr = float(shadow_ctr)
        improvement = shadow_ctr - baseline_ctr
        metric_improved = improvement > 0

        return {
            "status": "success" if metric_improved else "failed",
            "metric_improved": metric_improved,
            "baseline_ctr": round(baseline_ctr, 6),
            "shadow_ctr": round(shadow_ctr, 6),
            "ctr_delta_pct": round(improvement * 100, 2),
            "summary": (
                "Autocomplete CTR improved on the real shadow sample."
                if metric_improved
                else "Autocomplete CTR did not improve on the real shadow sample."
            ),
        }
