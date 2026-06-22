import math
from typing import Any, Optional, List, Dict
import logging
import numpy as np # Using numpy for percentile calculation

try:
    import ranx
except Exception:  # pragma: no cover - optional dependency path
    ranx = None

logger = logging.getLogger(__name__)

class MetricsEvaluatorTool:
    """Calculates relevance and performance metrics from a Diffy report."""

    async def run(self, signal: dict[str, Any]) -> dict[str, Any]:
        logger.info("MetricsEvaluatorTool: Received signal to evaluate metrics.")
        diffy_report = signal.get("report", {})
        execution_results = diffy_report.get("execution_results", [])
        latency_results = diffy_report.get("latency_results", {})
        
        if not execution_results:
            logger.warning("MetricsEvaluatorTool: No execution results found in the report.")
            return {"status": "failed", "message": "No execution results found in the Diffy report."}

        logger.info("MetricsEvaluatorTool: Calculating metrics from Diffy report...")

        relevance_metrics = self._calculate_relevance(execution_results)
        performance_metrics = self._calculate_performance(latency_results)

        # Combine the results and make a final decision
        # (This logic can be expanded based on business rules)
        ndcg_improvement = relevance_metrics.get("absolute_ndcg_improvement", 0.0)
        latency_increase = performance_metrics.get("p995_latency_increase_ms", 0.0)
        
        decision = "PROMOTE_TO_CANARY"
        if ndcg_improvement < 0 or latency_increase > 50: # Example rule: rollback if NDCG drops or latency increases by >50ms
            decision = "ROLLBACK_FIX"

        return {
            "tool_name": "MetricsEvaluatorTool",
            "status": "success",
            "metrics": {
                "relevance": relevance_metrics,
                "performance": performance_metrics
            },
            "decision": decision,
            "summary": f"Evaluation complete. NDCG change: {ndcg_improvement:+.2f}%. P995 latency change: {latency_increase:+.2f}ms. Decision: {decision}"
        }

    def _calculate_relevance(self, execution_results: list) -> dict:
        if ranx is not None:
            # Using ranx is more efficient and scalable
            return self._evaluate_relevance_with_ranx(execution_results)
        else:
            # Fallback for environments where ranx is not installed
            return self._evaluate_relevance_with_fallback(execution_results)

    def _calculate_performance(self, latency_results: dict) -> dict:
        baseline_latencies = latency_results.get("baseline_ms", [])
        shadow_latencies = latency_results.get("shadow_ms", [])

        if not baseline_latencies or not shadow_latencies:
            return {
                "p995_baseline_ms": 0,
                "p995_shadow_ms": 0,
                "p995_latency_increase_ms": 0
            }

        p995_baseline = np.percentile(baseline_latencies, 99.5)
        p995_shadow = np.percentile(shadow_latencies, 99.5)

        return {
            "p995_baseline_ms": round(p995_baseline, 2),
            "p995_shadow_ms": round(p995_shadow, 2),
            "p995_latency_increase_ms": round(p995_shadow - p995_baseline, 2)
        }

    def _evaluate_relevance_with_ranx(self, execution_results: list[dict[str, Any]]) -> dict[str, Any]:
        qrels = {}
        baseline_run = {}
        shadow_run = {}

        for i, res in enumerate(execution_results):
            query_id = f"q_{i+1}"
            expected_skus = res.get("expected_skus", [])
            baseline_top_k = res.get("baseline_top_k", [])
            shadow_top_k = res.get("shadow_top_k", [])

            qrels[query_id] = {sku: 1 for sku in expected_skus}
            baseline_run[query_id] = {sku: 1 / (rank + 1) for rank, sku in enumerate(baseline_top_k)}
            shadow_run[query_id] = {sku: 1 / (rank + 1) for rank, sku in enumerate(shadow_top_k)}

        metrics = ["mrr@10", "recall@5", "ndcg@10"]
        baseline_report = ranx.evaluate(ranx.Qrels(qrels), ranx.Run(baseline_run), metrics)
        shadow_report = ranx.evaluate(ranx.Qrels(qrels), ranx.Run(shadow_run), metrics)
        improvement = (shadow_report["ndcg@10"] - baseline_report["ndcg@10"]) * 100

        return {
            "baseline": baseline_report,
            "shadow": shadow_report,
            "absolute_ndcg_improvement": round(improvement, 2)
        }

    def _evaluate_relevance_with_fallback(self, execution_results: list[dict[str, Any]]) -> dict[str, Any]:
        baseline_report = self._aggregate_metrics(execution_results, "baseline_top_k")
        shadow_report = self._aggregate_metrics(execution_results, "shadow_top_k")
        improvement = (shadow_report["ndcg@10"] - baseline_report["ndcg@10"]) * 100

        return {
            "baseline": baseline_report,
            "shadow": shadow_report,
            "absolute_ndcg_improvement": round(improvement, 2)
        }

    def _aggregate_metrics(
        self,
        execution_results: List[Dict[str, Any]],
        ranking_key: str,
    ) -> Dict[str, float]:
        query_metrics = []
        for res in execution_results:
            expected_skus = res.get("expected_skus", [])
            ranked_skus = res.get(ranking_key, [])
            query_metrics.append({
                "mrr@10": self._mrr_at_k(ranked_skus, expected_skus, 10),
                "recall@5": self._recall_at_k(ranked_skus, expected_skus, 5),
                "ndcg@10": self._ndcg_at_k(ranked_skus, expected_skus, 10),
            })

        if not query_metrics:
            return {"mrr@10": 0.0, "recall@5": 0.0, "ndcg@10": 0.0}

        count = float(len(query_metrics))
        return {
            "mrr@10": round(sum(m["mrr@10"] for m in query_metrics) / count, 4),
            "recall@5": round(sum(m["recall@5"] for m in query_metrics) / count, 4),
            "ndcg@10": round(sum(m["ndcg@10"] for m in query_metrics) / count, 4),
        }

    @staticmethod
    def _mrr_at_k(ranked_skus: list[str], expected_skus: list[str], k: int) -> float:
        expected = set(expected_skus)
        for rank, sku in enumerate(ranked_skus[:k], start=1):
            if sku in expected:
                return round(1.0 / rank, 4)
        return 0.0

    @staticmethod
    def _recall_at_k(ranked_skus: list[str], expected_skus: list[str], k: int) -> float:
        expected = set(expected_skus)
        if not expected:
            return 0.0
        retrieved = sum(1 for sku in ranked_skus[:k] if sku in expected)
        return round(retrieved / len(expected), 4)

    @classmethod
    def _ndcg_at_k(cls, ranked_skus: list[str], expected_skus: list[str], k: int) -> float:
        expected = set(expected_skus)
        if not expected:
            return 0.0

        def dcg(items: list[str]) -> float:
            score = 0.0
            for idx, sku in enumerate(items[:k], start=1):
                rel = 1.0 if sku in expected else 0.0
                if rel > 0:
                    score += rel / math.log2(idx + 1)
            return score

        actual_dcg = dcg(ranked_skus)
        ideal_dcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(expected), k)))
        if ideal_dcg == 0:
            return 0.0
        return round(actual_dcg / ideal_dcg, 4)
