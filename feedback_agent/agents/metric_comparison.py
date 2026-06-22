import logging
import time
from typing import Dict, Any, Union

from .base import BaseAgent
from ..config import MOCK_MODE, OCS_SEARCH_URL

class MetricComparisonAgent(BaseAgent):
    """
    Sub-agent 2: MetricComparisonAgent
    Compares baseline metrics against post-remediation metrics.
    Metrics evaluated:
      - zeroResultRate: Fraction of searches with zero hits (should go to 0).
      - Relevance score: Retrieval relevance indicator (should go up).
      - Latency p95: Latency metric (measured from gateway roundtrip and headers).
      - CTR (Click-Through Rate): Lift expectation (typically pending canary data).
    """

    def run(self, input_data: Dict[str, Any], pipeline_state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Starting metric comparison...")

        # If previous verification check failed, we don't have new metrics to measure
        verification = pipeline_state.get("verification", {})
        if not verification.get("allPassed", False):
            self.logger.warning("Verification failed. Skipping metric comparison; reporting pre-fix defaults.")
            return {
                "metrics": {
                    "zeroResultRate": {"before": 1.0, "after": 1.0, "delta": 0.0},
                    "ctr": {"before": 0.0, "after": 0.0, "delta": 0.0},
                    "latency_p95_ms": {"before": 45.0, "after": 45.0, "delta": 0.0},
                    "relevanceScore": {"before": 0.0, "after": 0.0, "delta": 0.0}
                }
            }

        # 1. Collect baseline metrics from input.json expectations
        baseline = {
            "zeroResultRate": 1.0,
            "ctr": 0.0,
            "latency_p95_ms": 45.0,
            "relevanceScore": 0.0
        }

        # 2. Retrieve live or mock metrics
        current = self._collect_current_metrics(input_data)

        # 3. Compute deltas
        metrics_report = {
            "zeroResultRate": {
                "before": baseline["zeroResultRate"],
                "after": current["zeroResultRate"],
                "delta": current["zeroResultRate"] - baseline["zeroResultRate"]
            },
            "ctr": {
                "before": baseline["ctr"],
                "after": current["ctr"],
                "delta": "n/a" if isinstance(current["ctr"], str) else current["ctr"] - baseline["ctr"]
            },
            "latency_p95_ms": {
                "before": baseline["latency_p95_ms"],
                "after": current["latency_p95_ms"],
                "delta": current["latency_p95_ms"] - baseline["latency_p95_ms"]
            },
            "relevanceScore": {
                "before": baseline["relevanceScore"],
                "after": current["relevanceScore"],
                "delta": current["relevanceScore"] - baseline["relevanceScore"]
            }
        }

        self.logger.info("Metric comparison completed.")
        return {"metrics": metrics_report}

    def _collect_current_metrics(self, input_data: Dict[str, Any]) -> Dict[str, Union[float, str]]:
        if MOCK_MODE:
            # Dynamically calculate mock relevance score from upstream pipeline confidence
            result_wrapper = input_data.get("result", {})
            rlm_synthesis = result_wrapper.get("rlmSynthesis", {})
            confidence = rlm_synthesis.get("result", {}).get("confidence", 0.577)
            # Standardize mock relevance dynamically: e.g. mapping confidence range to relevance
            relevance = float(round(0.70 + (confidence * 0.20), 2)) # e.g. 0.70 + 0.12 = 0.82

            # Simulate latency dynamically (base 45ms + small random delta or synonym overhead)
            # We add 7ms of overhead since 3 synonyms and 4 searchable fields are active
            latency_after = 45.0 + 7.0

            return {
                "zeroResultRate": 0.0,
                "ctr": "pending_canary",
                "latency_p95_ms": latency_after,
                "relevanceScore": relevance
            }
        else:
            # Live metric gathering via gateway response times
            current_metrics = {
                "zeroResultRate": 1.0,
                "ctr": "pending_canary",
                "latency_p95_ms": 45.0,
                "relevanceScore": 0.0
            }
            
            import requests
            query = input_data.get("query") or input_data.get("result", {}).get("query", "")
            
            try:
                url = f"{OCS_SEARCH_URL}/search-api/v1/search"
                
                # Measure round-trip time of search API request (gateway latency)
                start_time = time.perf_counter()
                response = requests.post(url, json={"q": query}, timeout=3)
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    result_count = len(results)
                    
                    # 1. Determine Latency: check for search headers first (e.g. X-Search-Time), fallback to round-trip
                    header_latency = response.headers.get("X-Search-Time") or response.headers.get("X-OCS-Latency")
                    if header_latency:
                        try:
                            current_metrics["latency_p95_ms"] = float(header_latency)
                        except ValueError:
                            current_metrics["latency_p95_ms"] = float(round(elapsed_ms, 1))
                    else:
                        current_metrics["latency_p95_ms"] = float(round(elapsed_ms, 1))
                    
                    # 2. Determine Zero-Result Rate
                    if result_count > 0:
                        current_metrics["zeroResultRate"] = 0.0
                        
                        # 3. Dynamic Relevance: check if affected product IDs exist in search results
                        affected_pids = input_data.get("result", {}).get("embeddingPatch", {}).get("affectedProductIds", [])
                        
                        # Calculate matching overlap
                        overlap_hits = 0
                        returned_pids = [r.get("id") or r.get("productId") for r in results if isinstance(r, dict)]
                        for pid in affected_pids:
                            if pid in returned_pids:
                                overlap_hits += 1
                        
                        # Dynamic relevance score calculation based on overlap and scores
                        base_relevance = 0.6
                        if affected_pids:
                            overlap_ratio = overlap_hits / len(affected_pids)
                            base_relevance += (overlap_ratio * 0.3) # Max 0.9 relevance
                        
                        # Check OCS relevance scores if present
                        max_score = max([r.get("score", 0) or r.get("_score", 0) for r in results if isinstance(r, dict)] or [0])
                        if max_score > 0:
                            # Normalize high match score to boost relevance
                            base_relevance = min(0.95, base_relevance + (max_score * 0.05))

                        current_metrics["relevanceScore"] = float(round(base_relevance, 2))
                    else:
                        current_metrics["zeroResultRate"] = 1.0
                        current_metrics["relevanceScore"] = 0.0
                else:
                    self.logger.warning(f"Search API returned code {response.status_code}")
                    current_metrics["latency_p95_ms"] = float(round(elapsed_ms, 1))
            except Exception as e:
                self.logger.warning(f"Could not contact Search API for live metrics: {e}")

            return current_metrics
