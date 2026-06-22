"""Compatibility wrapper for the Diffy-style shadow compare implementation."""

from __future__ import annotations

from typing import Any

from .diffy_shadow import build_diffy_shadow_report


def build_shadow_report(
    *,
    query: str | None = None,
    payload: Any = None,
    baseline: Any = None,
    candidate: Any = None,
    primary: Any = None,
    secondary: Any = None,
) -> dict[str, Any]:
    """Compare V-current and V-next payloads and return a Diffy-style report."""

    return build_diffy_shadow_report(
        query=query,
        payload=payload,
        baseline=baseline,
        candidate=candidate,
        primary=primary,
        secondary=secondary,
    )
