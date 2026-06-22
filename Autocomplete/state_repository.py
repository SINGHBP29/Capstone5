from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class AutocompleteStateRepository:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / "autocomplete_state.json"

    @staticmethod
    def _default_state() -> Dict[str, Any]:
        return {
            "catalog_terms": [
                {"term": "shoes", "clicks": 1240, "ctr": 0.23},
                {"term": "sneakers", "clicks": 980, "ctr": 0.19},
                {"term": "sandals", "clicks": 610, "ctr": 0.11},
                {"term": "boots", "clicks": 530, "ctr": 0.12},
            ],
            "prefix_index": {
                "last_refresh_at": "2026-06-10T02:00:00Z",
                "coverage": {"sh": 0.97, "sho": 0.18, "sne": 0.91, "boo": 0.88},
                "stale_prefixes": ["sho"],
                "suggestions": {
                    "sh": ["shoes", "shirts", "shorts"],
                    "sho": ["shop", "shorts"],
                    "sne": ["sneakers", "sneaker"],
                },
            },
            "popularity": {
                "entity_clicks": {"shoes": 1240, "sneakers": 980, "sandals": 610, "boots": 530},
                "boosts": {"shoes": 1.0, "sneakers": 1.0, "sandals": 0.9, "boots": 0.95},
                "ranking_by_query": {
                    "sh": ["sneakers", "shoes", "sandals"],
                    "sho": ["shop", "shorts", "shoes"],
                },
            },
            "typo_dictionary": {
                "snikers": ["sneakers"],
                "sandels": ["sandals"],
                "bootz": ["boots"],
            },
            "query_performance": {
                "shos": {"baseline_ctr": 0.05, "shadow_ctr": 0.18},
                "sh": {"baseline_ctr": 0.16, "shadow_ctr": 0.2},
            },
        }

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = AutocompleteStateRepository._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def load_state(self) -> Dict[str, Any]:
        if not self.path.exists():
            state = self._default_state()
            self.save_state(state)
            return state

        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("Autocomplete state file must contain a JSON object.")
        return self._deep_merge(self._default_state(), raw)

    def save_state(self, state: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    def catalog_terms(self) -> List[str]:
        state = self.load_state()
        terms: List[str] = []
        for item in state.get("catalog_terms", []):
            if isinstance(item, dict) and item.get("term"):
                terms.append(str(item["term"]))
            elif isinstance(item, str):
                terms.append(item)
        return terms
