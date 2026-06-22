"""Diffy-style shadow testing helpers.

This module models the classic Diffy topology:

* candidate: V-next, the new implementation under test
* primary: V-current, the trusted baseline
* secondary: a second copy of the trusted baseline used to measure noise

The compare step multicasts the same request to each side, compares candidate
vs primary, and uses primary vs secondary as the non-deterministic noise
baseline.
"""

from __future__ import annotations

import copy
from typing import Any

from tools.data_gap_tools import classify_data_gap, data_gap_actions
from tools.index_analysis_tools import diff_index_settings
from tools.shadow_diff_tools import diff_shadow_responses, summarize_shadow_diffs


def _normalize_side(side: Any) -> dict[str, Any]:
    if isinstance(side, dict):
        return copy.deepcopy(side)
    return {}


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_str_list(values: Any) -> list[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for item in values:
        if isinstance(item, str):
            normalized = item.strip()
            if normalized:
                result.append(normalized)
    return result


def _extract_shadow_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("shadowTest"), dict):
        return dict(payload.get("shadowTest") or {})
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _extract_query(payload: Any, fallback: str = "") -> str:
    if isinstance(payload, dict):
        query = payload.get("query")
        if isinstance(query, str) and query.strip():
            return query.strip()
    return fallback


def _latency_ms(side: dict[str, Any]) -> float:
    metrics = side.get("metrics", {}) if isinstance(side.get("metrics"), dict) else {}
    for key in ("latencyMs", "latency_ms"):
        if key in side:
            return _coerce_float(side.get(key))
        if key in metrics:
            return _coerce_float(metrics.get(key))
    return 0.0


def _searchable_attributes(side: dict[str, Any]) -> list[str]:
    settings = side.get("settings", {}) if isinstance(side.get("settings"), dict) else {}
    return _coerce_str_list(settings.get("searchableAttributes"))


def _extract_response_body(side: dict[str, Any]) -> Any:
    for key in ("response", "body", "payload", "result", "output"):
        if key in side and side.get(key) is not None:
            return side.get(key)

    if not side:
        return {}

    fallback = copy.deepcopy(side)
    fallback.pop("name", None)
    return fallback


def _response_shape(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "object",
            "keys": list(value.keys())[:8],
            "keyCount": len(value),
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "itemCount": len(value),
        }
    return {
        "type": type(value).__name__,
    }


def _side_summary(name: str, side: dict[str, Any]) -> dict[str, Any]:
    settings = side.get("settings", {}) if isinstance(side.get("settings"), dict) else {}
    response = _extract_response_body(side)
    return {
        "name": side.get("name", name),
        "docs": _coerce_int(side.get("docs", side.get("documents", 0))),
        "results": _coerce_int(side.get("results", side.get("results_count", 0))),
        "status": str(side.get("status", "unknown")),
        "latencyMs": _latency_ms(side),
        "searchableAttributes": _searchable_attributes(side),
        "settings": settings,
        "responseShape": _response_shape(response),
    }


def _collect_ignore_paths(shadow_payload: dict[str, Any]) -> list[str]:
    ignore_paths: list[str] = []

    for section_key in ("transformations", "noiseCancellation"):
        section = shadow_payload.get(section_key)
        if not isinstance(section, dict):
            continue
        for key in ("ignorePaths", "ignoredPaths"):
            ignore_paths.extend(_coerce_str_list(section.get(key)))

    if "ignorePaths" in shadow_payload:
        ignore_paths.extend(_coerce_str_list(shadow_payload.get("ignorePaths")))

    deduped: list[str] = []
    seen: set[str] = set()
    for path in ignore_paths:
        normalized = path.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def _normalize_path(path: str) -> str:
    normalized = path.strip()
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized.startswith("$"):
        normalized = normalized[1:]
    if normalized.startswith("."):
        normalized = normalized[1:]
    return normalized


def _path_matches_ignore(path: str, ignore_path: str) -> bool:
    normalized_path = _normalize_path(path or "$")
    normalized_ignore = _normalize_path(ignore_path)
    if not normalized_ignore:
        return False
    if normalized_path == normalized_ignore:
        return True
    return normalized_path.startswith(f"{normalized_ignore}.") or normalized_path.startswith(f"{normalized_ignore}[")


def _filter_diffs(diffs: list[dict[str, Any]], ignore_paths: list[str]) -> list[dict[str, Any]]:
    if not ignore_paths:
        return diffs
    filtered: list[dict[str, Any]] = []
    for diff in diffs:
        path = str(diff.get("path", "$"))
        if any(_path_matches_ignore(path, ignore_path) for ignore_path in ignore_paths):
            continue
        filtered.append(diff)
    return filtered


def _candidate_ready_state(
    *,
    primary_available: bool,
    candidate_available: bool,
    candidate_diff_count: int,
    settings_changed: bool,
) -> str:
    if not primary_available or not candidate_available:
        return "blocked"

    if candidate_diff_count == 0 and not settings_changed:
        return "pass"

    return "warn"


def build_diffy_shadow_report(
    *,
    query: str | None = None,
    payload: Any = None,
    baseline: Any = None,
    candidate: Any = None,
    primary: Any = None,
    secondary: Any = None,
) -> dict[str, Any]:
    """Compare V-current and V-next payloads using a Diffy-style 3-way compare."""

    shadow_payload = _extract_shadow_payload(payload)
    incident_query = _extract_query(payload, query or "")
    if not incident_query:
        incident_query = _extract_query(shadow_payload, "")

    primary_side = _normalize_side(
        primary
        or baseline
        or shadow_payload.get("primary")
        or shadow_payload.get("baseline")
    )
    candidate_side = _normalize_side(candidate or shadow_payload.get("candidate"))
    secondary_provided = isinstance(secondary, dict) or isinstance(shadow_payload.get("secondary"), dict)
    secondary_side = _normalize_side(secondary or shadow_payload.get("secondary"))
    if not secondary_side and primary_side:
        secondary_side = copy.deepcopy(primary_side)
    secondary_mode = "explicit" if secondary_provided else "inferred-from-primary"

    primary_summary = _side_summary("primary", primary_side)
    candidate_summary = _side_summary("candidate", candidate_side)
    secondary_summary = _side_summary("secondary", secondary_side)

    ignore_paths = _collect_ignore_paths(shadow_payload)
    primary_response = _extract_response_body(primary_side)
    candidate_response = _extract_response_body(candidate_side)
    secondary_response = _extract_response_body(secondary_side)

    raw_candidate_response_diffs = diff_shadow_responses(primary_response, candidate_response)
    noise_response_diffs = diff_shadow_responses(primary_response, secondary_response)
    noise_response_diff_summary = summarize_shadow_diffs(noise_response_diffs)
    noise_paths = [str(diff.get("path", "$")) for diff in noise_response_diffs]
    suppression_paths = list(ignore_paths)
    for path in noise_paths:
        if path not in suppression_paths:
            suppression_paths.append(path)
    candidate_response_diffs = _filter_diffs(raw_candidate_response_diffs, suppression_paths)
    candidate_response_diff_summary = summarize_shadow_diffs(candidate_response_diffs)
    filtered_candidate_raw_summary = summarize_shadow_diffs(raw_candidate_response_diffs)

    settings_diff = diff_index_settings(
        primary_summary["settings"],
        candidate_summary["settings"],
    )

    gap_type, reason, confidence = classify_data_gap(
        incident_query=incident_query,
        baseline_docs=primary_summary["docs"],
        candidate_docs=candidate_summary["docs"],
        baseline_results=primary_summary["results"],
        candidate_results=candidate_summary["results"],
        shadow_status=candidate_summary["status"],
        setting_diff=settings_diff,
    )

    docs_delta = candidate_summary["docs"] - primary_summary["docs"]
    results_delta = candidate_summary["results"] - primary_summary["results"]
    latency_delta = round(candidate_summary["latencyMs"] - primary_summary["latencyMs"], 2)
    searchable_delta = sorted(set(candidate_summary["searchableAttributes"]) - set(primary_summary["searchableAttributes"]))
    searchable_removed = sorted(set(primary_summary["searchableAttributes"]) - set(candidate_summary["searchableAttributes"]))

    candidate_diff_count = candidate_response_diff_summary["diffCount"]
    candidate_raw_diff_count = filtered_candidate_raw_summary["diffCount"]
    noise_diff_count = noise_response_diff_summary["diffCount"]
    state = _candidate_ready_state(
        primary_available=bool(primary_side),
        candidate_available=bool(candidate_side),
        candidate_diff_count=candidate_diff_count,
        settings_changed=bool(settings_diff),
    )

    signal_to_noise = round(candidate_raw_diff_count / max(noise_diff_count, 1), 2)
    actions = data_gap_actions(gap_type=gap_type, incident_query=incident_query)

    return {
        "shadowMode": "diffy-shadow",
        "shadowFramework": "Diffy",
        "incidentQuery": incident_query,
        "gapType": gap_type,
        "reason": reason,
        "confidence": confidence,
        "topology": {
            "primary": primary_summary,
            "secondary": secondary_summary,
            "candidate": candidate_summary,
            "secondaryMode": secondary_mode,
        },
        "primary": primary_summary,
        "secondary": secondary_summary,
        "candidate": candidate_summary,
        "baseline": primary_summary,
        "comparisonSummary": {
            "docsDelta": docs_delta,
            "resultsDelta": results_delta,
            "latencyDeltaMs": latency_delta,
            "settingsChanged": bool(settings_diff),
            "settingDiffCount": len(settings_diff),
            "searchableAttributesAdded": searchable_delta,
            "searchableAttributesRemoved": searchable_removed,
            "candidateRawResponseDiffCount": candidate_raw_diff_count,
            "candidateResponseDiffCount": candidate_diff_count,
            "noiseResponseDiffCount": noise_diff_count,
            "signalToNoiseRatio": signal_to_noise,
            "noiseBaselineEquivalent": noise_response_diff_summary["responseEquivalent"],
            "candidateResponseEquivalent": candidate_response_diff_summary["responseEquivalent"],
            "ignorePathCount": len(ignore_paths),
            "noiseSuppressedPaths": suppression_paths[len(ignore_paths):],
        },
        "settingDiff": settings_diff,
        "responseDiff": candidate_response_diffs,
        "responseDiffSummary": candidate_response_diff_summary,
        "noiseDiff": noise_response_diffs,
        "noiseDiffSummary": noise_response_diff_summary,
        "assessment": {
            "state": state,
            "candidateEquivalent": candidate_response_diff_summary["responseEquivalent"],
            "noiseEquivalent": noise_response_diff_summary["responseEquivalent"],
            "candidateReady": state == "pass",
            "secondaryAvailable": secondary_provided,
            "secondaryMode": secondary_mode,
            "summary": (
                "Candidate matches the primary once noisy fields are suppressed."
                if state == "pass"
                else "Candidate differs from the primary beyond the observed noise baseline."
                if state == "warn"
                else "Primary or candidate data is missing, so shadow testing is blocked."
            ),
        },
        "actions": actions,
        "recommendation": {
            "decision": "promote_candidate" if state == "pass" else "hold_and_review",
            "reason": reason,
        },
    }
