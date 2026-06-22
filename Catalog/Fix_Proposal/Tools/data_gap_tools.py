"""Data-gap classification tools for shadow and catalog analysis."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


def looks_synthetic_query(query: str) -> bool:
    normalized = str(query or "").strip().lower()
    if not normalized:
        return False
    markers = (
        "definitelymissing",
        "zzzz",
        "synthetic",
        "dummy",
        "fake",
        "test",
        "nonexistent-control",
    )
    return any(marker in normalized for marker in markers)


def incident_comparison(comparisons: Iterable[Dict[str, Any]], incident_query: str) -> Dict[str, Any]:
    for comparison in comparisons:
        if str(comparison.get("query")) == incident_query:
            return comparison
    return {
        "query": incident_query,
        "baseline": {"results_count": 0},
        "shadow": {"results_count": 0},
        "delta": {"outcome": "unknown"},
    }


def classify_data_gap(
    *,
    incident_query: str,
    baseline_docs: int,
    candidate_docs: int,
    baseline_results: int,
    candidate_results: int,
    shadow_status: str,
    setting_diff: Dict[str, Any],
) -> tuple[str, str, str]:
    if looks_synthetic_query(incident_query):
        return (
            "synthetic_test_query",
            f"The incident query '{incident_query}' looks synthetic, so the zero-result cluster is likely expected test traffic.",
            "high",
        )
    if shadow_status == "candidate-index-missing":
        return (
            "candidate-index-missing",
            "The candidate index is missing, so shadow replay cannot prove the fix path yet.",
            "high",
        )
    if baseline_docs == 0:
        return (
            "baseline_index_empty",
            "The baseline index has no documents, so the failure is caused by an empty or unseeded catalog.",
            "high",
        )
    if baseline_results == 0 and candidate_results == 0 and baseline_docs > 0:
        return (
            "query_vocabulary_gap",
            "Both baseline and candidate stay at zero hits even though the catalog has documents, which points to vocabulary, synonym, or coverage gaps.",
            "high",
        )
    if candidate_docs < baseline_docs:
        return (
            "candidate_catalog_delta",
            "The candidate index contains fewer documents than baseline, so the candidate catalog is incomplete.",
            "medium",
        )
    if setting_diff:
        return (
            "rule_configuration_diff",
            "Ranking, synonym, or searchable-attribute settings differ between baseline and candidate indexes.",
            "medium",
        )
    return (
        "no_material_catalog_gap_detected",
        "No major catalog or rule diff stands out from the current replay and index comparison.",
        "medium",
    )


def data_gap_actions(*, gap_type: str, incident_query: str) -> List[str]:
    if gap_type == "insufficient_shadow_evidence":
        return [
            "Pass the baseline/candidate shadow payloads or the full shadowTest section so the agent can compare both sides.",
            "Run the DataGap stage from the sequential pipeline if you want it to reuse the upstream shadow-test output automatically.",
        ]
    if gap_type == "synthetic_test_query":
        return [
            "Mark the signal as expected test traffic or suppress it in the detector.",
            "Keep the query out of customer-impact dashboards and promotion gates.",
        ]
    if gap_type == "candidate-index-missing":
        return [
            "Sync or create the candidate index before any canary decision.",
            "Re-run the shadow eval dataset after the candidate index is seeded.",
        ]
    if gap_type == "baseline_index_empty":
        return [
            "Backfill the baseline index from the source catalog immediately.",
            "Verify indexing jobs and ingestion credentials before reopening traffic.",
        ]
    if gap_type == "query_vocabulary_gap":
        return [
            f"Check whether expected documents for '{incident_query}' exist in the source catalog and index.",
            "Add synonyms, aliases, stemming, or query normalization if the documents exist but do not match.",
        ]
    if gap_type == "candidate_catalog_delta":
        return [
            "Backfill missing candidate documents before evaluating relevance changes.",
            "Compare ingestion jobs and recent catalog patches between baseline and candidate indexes.",
        ]
    if gap_type == "rule_configuration_diff":
        return [
            "Review the changed ranking, synonym, and searchable-attribute settings.",
            "Promote only after the rule diff is intentional and shadow replay stays stable.",
        ]
    return [
        "Expand the eval dataset with more real customer queries before changing production traffic.",
        "Keep collecting evidence until a stronger catalog or rule gap appears.",
    ]
