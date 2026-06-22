#!/usr/bin/env python3
"""ShadowTestAgent: compare V-current and V-next payloads before rollout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableLambda

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from environment.AgentsRLM.models import AgentInput, AgentOutput
from shadow_testing.shadow_compare import build_shadow_report


class ShadowTestAgent:
    """Class wrapper for Diffy-style shadow comparison."""

    @staticmethod
    def _resolve_side(data: dict[str, Any], name: str, shadow_test: dict[str, Any]) -> Any:
        return data.get(name) or shadow_test.get(name)

    def run(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = AgentInput.model_validate(data)
        shadow_test = data.get("shadowTest", {}) if isinstance(data.get("shadowTest"), dict) else {}
        primary = self._resolve_side(data, "primary", shadow_test) or shadow_test.get("baseline") or data.get("baseline")
        secondary = self._resolve_side(data, "secondary", shadow_test)
        candidate = self._resolve_side(data, "candidate", shadow_test)
        report = build_shadow_report(
            query=payload.query or data.get("query") or "",
            payload=data,
            primary=primary,
            secondary=secondary,
            candidate=candidate,
        )
        status = "ok" if report.get("assessment", {}).get("state") != "blocked" else "failed"
        output = AgentOutput(
            agent="ShadowTestAgent",
            status=status,
            query=payload.query,
            result=report,
        )
        return output.model_dump()


DEFAULT_SHADOW_TEST_AGENT = ShadowTestAgent()


def run_shadow_test(data: dict[str, Any]) -> dict[str, Any]:
    return DEFAULT_SHADOW_TEST_AGENT.run(data)


def run_agent(data: dict[str, Any]) -> dict[str, Any]:
    return RunnableLambda(run_shadow_test).invoke(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = run_agent(data)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
