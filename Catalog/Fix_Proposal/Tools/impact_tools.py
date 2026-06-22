"""Impact scoring tools for capability triage."""


CAPABILITY_BY_SIGNAL = {
    "catalog_delta": "catalog_completeness",
    "catalog_index_gap": "catalog",
    "catalog_freshness_breach": "catalog",
    "failed_query": "search_relevance",
    "low_ctr": "search_performance",
    "stale_suggestion": "autocomplete_freshness",
    "autocomplete_miss": "autocomplete_coverage",
    "autocomplete_fail": "autocomplete",
    "autocomplete_zero_suggestions": "autocomplete",
    "autocomplete_latency_spike": "autocomplete",
    "autocomplete_relevance_regression": "autocomplete",
    "merchandising_rule_conflict": "merchandising_governance",
    "zero_result_cluster": "semantic_search",
    "missing_products_cluster": "catalog",
    "semantic_index_gap": "semantic_index",
    "semantic_index_stale": "semantic_index",
    "stale_embedding": "semantic_index",
    "semantic_recall_drop": "semantic_index",
    "vector_search_latency_spike": "semantic_index",
    "personalization_fallback_spike": "personalization",
    "feature_service_degraded": "personalization",
    "personalization_uplift_drop": "personalization",
    "rule_diff": "merchandising_controls",
    "rule_conflict": "merchandising_controls",
    "policy_violation": "merchandising_controls",
    "pinning_failure": "merchandising_controls",
    "exclusion_policy_violation": "merchandising_controls",
    "merch_rule_conflict": "merchandising_controls",
    "campaign_result_miss": "merchandising_controls",
    "latency_spike": "search_api",
}

SEVERITY_SCORE = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 5,
}


def get_metric(signal, name, default=0):
    metrics = signal.get("metrics", {})
    value = metrics.get(name, default)
    return value if isinstance(value, (int, float)) else default


def signal_to_capability(signal):
    explicit_capability = signal.get("capability")
    if explicit_capability:
        return str(explicit_capability)
    signal_type = signal.get("type")
    return CAPABILITY_BY_SIGNAL.get(signal_type, "unknown")


def score_signal(signal):
    signal_type = signal.get("type")
    severity = SEVERITY_SCORE.get(signal.get("severity", "medium"), 2)

    if signal_type in {"failed_query", "low_ctr"}:
        impressions = get_metric(signal, "impressions")
        exits = get_metric(signal, "exits")
        return severity * (impressions + exits * 2)

    if signal_type == "autocomplete_miss":
        return severity * get_metric(signal, "missedPrefixCount") * 100

    if signal_type == "catalog_delta":
        return severity * get_metric(signal, "affectedDocumentCount") * 250

    if signal_type == "merchandising_rule_conflict":
        return severity * max(get_metric(signal, "conflictCount"), 1) * 1000

    if signal_type == "stale_suggestion":
        return severity * get_metric(signal, "staleSuggestionCount") * 100

    return severity


def higher_severity(first, second):
    first_score = SEVERITY_SCORE.get(first, 1)
    second_score = SEVERITY_SCORE.get(second, 1)
    return second if second_score > first_score else first
