"""Index setting diff tools.

The original version depended on app.ai_search. This local version accepts
stats/settings dictionaries directly, so agents can use JSON pipeline inputs.
"""

from __future__ import annotations

from typing import Any, Dict


INDEX_SETTING_KEYS = (
    "searchableAttributes",
    "filterableAttributes",
    "sortableAttributes",
    "rankingRules",
    "synonyms",
    "stopWords",
    "typoTolerance",
)


def build_index_analysis(
    baseline_stats: Dict[str, Any],
    candidate_stats: Dict[str, Any],
    baseline_settings: Dict[str, Any],
    candidate_settings: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "baselineStats": baseline_stats,
        "candidateStats": candidate_stats,
        "baselineSettings": baseline_settings,
        "candidateSettings": candidate_settings,
        "settingDiff": diff_index_settings(baseline_settings, candidate_settings),
    }


def diff_index_settings(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    diff: Dict[str, Any] = {}
    for key in INDEX_SETTING_KEYS:
        if baseline.get(key) != candidate.get(key):
            diff[key] = {
                "baseline": compact_value(baseline.get(key)),
                "candidate": compact_value(candidate.get(key)),
            }
    return diff


def compact_value(value: Any) -> Any:
    if isinstance(value, list):
        if len(value) <= 8:
            return value
        return value[:8] + [f"... +{len(value) - 8} more"]
    if isinstance(value, dict):
        compact: Dict[str, Any] = {}
        for index, (key, item) in enumerate(sorted(value.items())):
            if index >= 6:
                compact["..."] = f"+{len(value) - 6} more"
                break
            compact[key] = item
        return compact
    return value

