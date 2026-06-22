"""Evidence-driven synonym proposal helpers for the fix-plan pipeline.

The proposer looks at the incident query, local catalog content, and query-log
evidence. It stays deterministic and explainable, but the candidates come from
observed data instead of a sample-specific seed table.
"""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Iterable


STOPWORDS = {
    "and",
    "for",
    "from",
    "into",
    "item",
    "items",
    "more",
    "of",
    "or",
    "product",
    "products",
    "the",
    "this",
    "that",
    "with",
}

FIELD_WEIGHTS = {
    "title": 3.0,
    "tags": 2.2,
    "category": 1.8,
    "description": 1.0,
    "data": 1.2,
    "query": 1.6,
    "prefix": 0.6,
}


def _normalize_catalog(catalog: Any) -> dict[str, Any]:
    if isinstance(catalog, dict):
        payload = dict(catalog)
        payload.setdefault("products", [])
        return payload
    if isinstance(catalog, list):
        return {"products": catalog}
    return {"products": []}


def _as_text_fragments(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _as_text_fragments(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from _as_text_fragments(item)
        return
    yield str(value)


def _tokenize(value: Any) -> list[str]:
    text = " ".join(_as_text_fragments(value))
    tokens = re.findall(r"[a-z0-9]+", text.lower().replace("-", " "))
    return [token for token in tokens if len(token) >= 3 and token not in STOPWORDS]


def _product_profile(product: dict[str, Any]) -> dict[str, Any]:
    data = product.get("data") if isinstance(product.get("data"), dict) else {}
    tags = product.get("tags") if isinstance(product.get("tags"), list) else []

    title_tokens = set(_tokenize(product.get("title", "")))
    description_tokens = set(_tokenize(product.get("description", "")))
    category_tokens = set(_tokenize(product.get("category", "")))
    tags_tokens = set(_tokenize(tags))
    data_tokens = set(_tokenize(data))

    return {
        "id": product.get("id"),
        "title": product.get("title", ""),
        "description": product.get("description", ""),
        "category": product.get("category", ""),
        "title_tokens": title_tokens,
        "description_tokens": description_tokens,
        "category_tokens": category_tokens,
        "tags_tokens": tags_tokens,
        "data_tokens": data_tokens,
        "all_tokens": title_tokens | description_tokens | category_tokens | tags_tokens | data_tokens,
    }


def _query_log_weight(log: dict[str, Any]) -> float:
    impressions = float(log.get("impressions", 0) or 0)
    clicks = float(log.get("clicks", 0) or 0)
    exits = float(log.get("exits", 0) or 0)
    revenue = float(log.get("revenue", 0) or 0)

    engagement = 1.0
    engagement += min(2.0, impressions / 2000.0)
    engagement += min(2.0, clicks / 10.0)
    engagement += min(1.0, revenue / 5000.0)
    engagement -= min(0.75, exits / 4000.0)
    return max(0.5, engagement)


def _query_log_profile(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": str(log.get("query", "")),
        "prefix": str(log.get("prefix", "")),
        "query_tokens": set(_tokenize(log.get("query", ""))),
        "prefix_tokens": set(_tokenize(log.get("prefix", ""))),
        "weight": _query_log_weight(log),
    }


def _shared_prefix_length(first: str, second: str) -> int:
    length = 0
    for left, right in zip(first, second):
        if left != right:
            break
        length += 1
    return length


def _subword_bonus(term: str, candidate: str) -> float:
    if term == candidate:
        return 0.0

    if term in candidate or candidate in term:
        shared = min(len(term), len(candidate))
        return 0.25 + min(0.3, shared * 0.02)

    shared_prefix = _shared_prefix_length(term, candidate)
    if shared_prefix >= 4:
        return min(0.25, shared_prefix * 0.04)

    return 0.0


def _candidate_confidence(
    *,
    term: str,
    selected: list[str],
    evidence_map: dict[str, list[dict[str, Any]]],
) -> float:
    observed = 0
    catalog_support = 0
    subword_support = 0

    for candidate in selected:
        sources = {entry.get("source") for entry in evidence_map.get(candidate, [])}
        if "catalog" in sources:
            observed += 1
            catalog_support += 1
        if "queryLog" in sources:
            observed += 1
        if "subword" in sources:
            subword_support += 1

    base = 0.52 + min(0.18, catalog_support * 0.06) + min(0.12, observed * 0.03) + min(0.08, len(selected) * 0.02)
    if subword_support and not catalog_support:
        base -= 0.05
    return round(max(0.35, min(0.99, base)), 2)


def propose_synonym_mappings(
    query: str | None,
    catalog: Any,
    query_logs: Any,
    *,
    max_synonyms_per_term: int = 4,
) -> list[dict[str, Any]]:
    """Propose synonym mappings using local catalog and query-log evidence."""

    catalog_payload = _normalize_catalog(catalog)
    products = [
        _product_profile(product)
        for product in catalog_payload.get("products", [])
        if isinstance(product, dict)
    ]
    logs = [
        _query_log_profile(log)
        for log in (query_logs if isinstance(query_logs, list) else [])
        if isinstance(log, dict)
    ]

    query_terms = _tokenize(query or "")
    if not query_terms:
        return []
    query_term_set = set(query_terms)

    mappings: list[dict[str, Any]] = []
    seen_terms: set[str] = set()

    for term in query_terms:
        if term in seen_terms:
            continue
        seen_terms.add(term)

        candidate_scores: dict[str, float] = defaultdict(float)
        evidence_map: dict[str, list[dict[str, Any]]] = defaultdict(list)

        supporting_products = [
            product
            for product in products
            if term in product["all_tokens"] or product["all_tokens"] & query_term_set
        ]
        if not supporting_products:
            supporting_products = list(products)

        for product in supporting_products:
            query_overlap = len(product["all_tokens"] & set(query_terms))
            relevance = 1.0 + min(2.0, query_overlap * 0.5)
            if term in product["title_tokens"]:
                relevance += 1.4
            if term in product["tags_tokens"]:
                relevance += 1.0
            if term in product["category_tokens"]:
                relevance += 0.8

            field_tokens = (
                ("title", product["title_tokens"]),
                ("tags", product["tags_tokens"]),
                ("category", product["category_tokens"]),
                ("description", product["description_tokens"]),
                ("data", product["data_tokens"]),
            )

            for field_name, tokens in field_tokens:
                for candidate in tokens:
                    if candidate == term or candidate in query_terms:
                        continue
                    weight = relevance * FIELD_WEIGHTS[field_name]
                    candidate_scores[candidate] += weight
                    if len(evidence_map[candidate]) < 4:
                        evidence_map[candidate].append(
                            {
                                "source": "catalog",
                                "productId": product.get("id"),
                                "field": field_name,
                                "productTitle": product.get("title", ""),
                                "reason": "co-occurs with the incident query inside a relevant catalog record",
                            }
                        )

        for log in logs:
            log_text_tokens = set(log["query_tokens"])
            if not (log_text_tokens & query_term_set or term in log_text_tokens):
                continue
            log_relevance = log["weight"]
            for candidate in log_text_tokens:
                if candidate == term or candidate in query_terms:
                    continue
                candidate_scores[candidate] += log_relevance * FIELD_WEIGHTS["query"]
                if len(evidence_map[candidate]) < 4:
                    evidence_map[candidate].append(
                        {
                            "source": "queryLog",
                            "query": log["query"],
                            "prefix": log["prefix"],
                            "reason": "observed in a high-engagement query log related to the incident",
                        }
                    )

        for candidate in list(candidate_scores):
            bonus = _subword_bonus(term, candidate)
            if bonus <= 0:
                continue
            candidate_scores[candidate] += bonus
            if len(evidence_map[candidate]) < 4:
                evidence_map[candidate].append(
                    {
                        "source": "subword",
                        "reason": "shares a lexical fragment with the incident term",
                    }
                )

        ranked_candidates = sorted(
            candidate_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
        selected = [candidate for candidate, _ in ranked_candidates[:max_synonyms_per_term]]
        if not selected:
            continue

        source_summary = {
            "catalog": sum(1 for candidate in selected if any(entry.get("source") == "catalog" for entry in evidence_map.get(candidate, []))),
            "queryLog": sum(1 for candidate in selected if any(entry.get("source") == "queryLog" for entry in evidence_map.get(candidate, []))),
            "subword": sum(1 for candidate in selected if any(entry.get("source") == "subword" for entry in evidence_map.get(candidate, []))),
        }

        evidence: list[dict[str, Any]] = []
        for candidate in selected:
            for entry in evidence_map.get(candidate, [])[:2]:
                evidence.append({"synonym": candidate, **entry})

        mappings.append(
            {
                "term": term,
                "synonyms": selected,
                "confidence": _candidate_confidence(term=term, selected=selected, evidence_map=evidence_map),
                "sourceSummary": source_summary,
                "evidence": evidence[:6],
            }
        )

    return mappings
