"""Tool to evaluate semantic shadow-test metrics after a fix."""
from __future__ import annotations

import logging
import math
from typing import Dict, Any, List

try:
    import ranx
except Exception:  # pragma: no cover - optional dependency path
    ranx = None

logger = logging.getLogger(__name__)


class SemanticMetricsEvaluatorTool:
    """
    Computes ranking quality from real shadow-test execution results.

    The tool expects execution results shaped like the Diffy payload used
    throughout the catalog pipeline:

        {
            "query_id": "q_1",
            "expected_skus": ["SKU-1", "SKU-2"],
            "baseline_top_k": ["SKU-9", "SKU-2", ...],
            "shadow_top_k": ["SKU-1", "SKU-2", ...]
        }

    If the caller does not provide real execution results, the tool fails
    instead of inventing a synthetic score.
    """

    async def run(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        execution_results = signal_data.get("execution_results", [])
        if not execution_results and isinstance(signal_data.get("diffy_report"), dict):
            execution_results = signal_data["diffy_report"].get("execution_results", [])

        if not execution_results:
            return {
                "tool_name": "SemanticMetricsEvaluatorTool",
                "status": "failed",
                "summary": (
                    "No real shadow execution_results were provided for semantic evaluation."
                ),
                "message": (
                    "Pass the real diffy report or execution_results from the shadow run."
                ),
            }

        logger.info("Calculating semantic shadow metrics...")

        if ranx is not None:
            return self._evaluate_with_ranx(execution_results)

        return self._evaluate_with_fallback(execution_results)

    def _evaluate_with_ranx(self, execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        qrels = {}
        baseline_run = {}
        shadow_run = {}

        for i, res in enumerate(execution_results):
            query_id = res.get("query_id") or f"q_{i+1}"
            expected_skus = res.get("expected_skus", [])
            baseline_top_k = res.get("baseline_top_k", [])
            shadow_top_k = res.get("shadow_top_k", [])

            qrels[query_id] = {sku: 1 for sku in expected_skus}
            baseline_run[query_id] = {
                sku: 1 / (rank + 1) for rank, sku in enumerate(baseline_top_k)
            }
            shadow_run[query_id] = {
                sku: 1 / (rank + 1) for rank, sku in enumerate(shadow_top_k)
            }

        metrics = ["mrr@10", "recall@5", "ndcg@10"]
        baseline_report = ranx.evaluate(ranx.Qrels(qrels), ranx.Run(baseline_run), metrics)
        shadow_report = ranx.evaluate(ranx.Qrels(qrels), ranx.Run(shadow_run), metrics)
        improvement = (shadow_report["ndcg@10"] - baseline_report["ndcg@10"]) * 100

        return self._build_response(
            baseline_report=baseline_report,
            shadow_report=shadow_report,
            improvement=improvement,
            source="ranx",
            execution_results=execution_results,
        )

    def _evaluate_with_fallback(self, execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        baseline_report = self._aggregate_metrics(execution_results, "baseline_top_k")
        shadow_report = self._aggregate_metrics(execution_results, "shadow_top_k")
        improvement = (shadow_report["ndcg@10"] - baseline_report["ndcg@10"]) * 100

        return self._build_response(
            baseline_report=baseline_report,
            shadow_report=shadow_report,
            improvement=improvement,
            source="fallback",
            execution_results=execution_results,
        )

    def _aggregate_metrics(
        self,
        execution_results: List[Dict[str, Any]],
        ranking_key: str,
    ) -> Dict[str, float]:
        query_metrics = []

        for res in execution_results:
            expected_skus = res.get("expected_skus", [])
            ranked_skus = res.get(ranking_key, [])
            query_metrics.append(
                {
                    "mrr@10": self._mrr_at_k(ranked_skus, expected_skus, 10),
                    "recall@5": self._recall_at_k(ranked_skus, expected_skus, 5),
                    "ndcg@10": self._ndcg_at_k(ranked_skus, expected_skus, 10),
                }
            )

        if not query_metrics:
            return {"mrr@10": 0.0, "recall@5": 0.0, "ndcg@10": 0.0}

        count = float(len(query_metrics))
        return {
            "mrr@10": round(sum(m["mrr@10"] for m in query_metrics) / count, 4),
            "recall@5": round(sum(m["recall@5"] for m in query_metrics) / count, 4),
            "ndcg@10": round(sum(m["ndcg@10"] for m in query_metrics) / count, 4),
        }

    @staticmethod
    def _mrr_at_k(ranked_skus: List[str], expected_skus: List[str], k: int) -> float:
        expected = set(expected_skus)
        for rank, sku in enumerate(ranked_skus[:k], start=1):
            if sku in expected:
                return round(1.0 / rank, 4)
        return 0.0

    @staticmethod
    def _recall_at_k(ranked_skus: List[str], expected_skus: List[str], k: int) -> float:
        expected = set(expected_skus)
        if not expected:
            return 0.0
        retrieved = sum(1 for sku in ranked_skus[:k] if sku in expected)
        return round(retrieved / len(expected), 4)

    @classmethod
    def _ndcg_at_k(cls, ranked_skus: List[str], expected_skus: List[str], k: int) -> float:
        expected = set(expected_skus)
        if not expected:
            return 0.0

        def dcg(items: List[str]) -> float:
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

    def _build_response(
        self,
        *,
        baseline_report: Dict[str, float],
        shadow_report: Dict[str, float],
        improvement: float,
        source: str,
        execution_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        decision = "PROMOTE_TO_CANARY" if improvement > 0 else "ROLLBACK_FIX"

        return {
            "tool_name": "SemanticMetricsEvaluatorTool",
            "status": "success",
            "source": source,
            "metrics": {
                "baseline": baseline_report,
                "shadow": shadow_report,
                "absolute_ndcg_improvement": round(improvement, 2),
            },
            "decision": decision,
            "execution_results": execution_results,
            "summary": (
                f"Semantic shadow evaluation complete via {source}. "
                f"Shadow index showed a {improvement:+.2f}% change in NDCG@10."
            ),
        }
