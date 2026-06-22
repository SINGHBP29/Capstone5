"""Bridge helpers that connect an external Diffy capture to the agent pipeline."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from tools.io_tools import load_json


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return {}


def normalize_shadow_payload(payload: Any) -> dict[str, Any]:
    """Normalize a Diffy-style payload into the internal shadow-test contract.

    Accepted shapes:
    - already-normalized pipeline input with ``shadowTest``
    - raw Diffy export with ``primary``, ``secondary`` and ``candidate``
    - nested payloads with a ``diffy``/``shadow`` section
    """

    if not isinstance(payload, dict):
        return {}

    normalized = copy.deepcopy(payload)
    shadow_test = _as_dict(normalized.get("shadowTest"))
    if not shadow_test:
        for key in ("diffy", "shadow"):
            section = normalized.get(key)
            if isinstance(section, dict):
                shadow_test = _as_dict(section.get("shadowTest") or section)
                break
    if not shadow_test and isinstance(normalized.get("topology"), dict):
        topology = normalized.get("topology")
        for key in ("primary", "secondary", "candidate", "baseline"):
            value = topology.get(key)
            if isinstance(value, dict):
                shadow_test[key] = copy.deepcopy(value)

    for key in ("primary", "secondary", "candidate", "baseline"):
        if key in normalized and isinstance(normalized.get(key), dict):
            shadow_test[key] = copy.deepcopy(normalized[key])

    if shadow_test:
        if "baseline" not in shadow_test and isinstance(shadow_test.get("primary"), dict):
            shadow_test["baseline"] = copy.deepcopy(shadow_test["primary"])
        normalized["shadowTest"] = shadow_test

    if "query" not in normalized:
        query = shadow_test.get("query") if isinstance(shadow_test, dict) else None
        if isinstance(query, str) and query.strip():
            normalized["query"] = query.strip()

    if isinstance(shadow_test, dict):
        for key in ("primary", "secondary", "candidate", "baseline"):
            if key in shadow_test and isinstance(shadow_test.get(key), dict):
                normalized[key] = copy.deepcopy(shadow_test[key])

    return normalized


def merge_shadow_payload(base_input: dict[str, Any], shadow_payload: Any) -> dict[str, Any]:
    """Overlay a normalized Diffy payload on top of the main agent input."""

    merged = copy.deepcopy(base_input)
    normalized_shadow = normalize_shadow_payload(shadow_payload)
    if not normalized_shadow:
        return merged

    if "query" in normalized_shadow and not merged.get("query"):
        merged["query"] = normalized_shadow["query"]

    for key in ("shadowTest", "primary", "secondary", "candidate", "baseline"):
        if key in normalized_shadow:
            merged[key] = copy.deepcopy(normalized_shadow[key])

    for key in ("noiseCancellation", "transformations", "ignorePaths"):
        if key in normalized_shadow:
            merged[key] = copy.deepcopy(normalized_shadow[key])

    return merged


def load_shadow_payload(path: str | Path) -> dict[str, Any]:
    """Load a Diffy payload from disk and normalize it for the agents."""

    return normalize_shadow_payload(load_json(path))
