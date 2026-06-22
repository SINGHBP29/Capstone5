"""Common signal definitions for the Semantic Index Error detection pipeline.

Mirrors Catalog/common_signals.py with semantic-index-specific signals.
"""

sample_semantic_index_signal = {
  "timestamp": "2026-06-06T10:15:30Z",
  "source": "semantic_refresh_monitor",
  "tenant": "retail_tenant_001",

  "signal_id": "sem_refresh_001",
  "signal_type": "semantic_refresh_index",

  "index": {
    "index_id": "footwear_semantic_v3",
    "index_name": "Footwear Semantic Search Index",
    "index_version": "v3.2.1",
    "embedding_model": "text-embedding-3-large",
    "last_refresh_time": "2026-05-20T00:00:00Z",
    "last_successful_refresh": "2026-05-20T00:00:00Z"
  },

  "refresh_metrics": {
    "days_since_refresh": 17,
    "documents_added": 524,
    "documents_updated": 213,
    "documents_deleted": 41,
    "catalog_change_percentage": 12.7,
    "embedding_drift_score": 0.84,
    "relevance_score_delta": -0.18
  },

  "search_impact": {
    "query_samples": [
      {
        "query": "waterproof trail shoe",
        "previous_ctr": 0.21,
        "current_ctr": 0.14,
        "ctr_delta": -0.07
      },
      {
        "query": "running shoes",
        "previous_ctr": 0.31,
        "current_ctr": 0.25,
        "ctr_delta": -0.06
      }
    ],
    "affected_query_count": 347,
    "estimated_revenue_impact_usd": 4200
  },

  "refresh_recommendation": {
    "action": "FULL_REBUILD",
    "priority": "HIGH",
    "reason": [
      "Embedding drift exceeded threshold",
      "Catalog changes exceeded 10%",
      "Search relevance degradation detected"
    ]
  },

  "thresholds": {
    "max_days_without_refresh": 14,
    "max_embedding_drift": 0.75,
    "max_catalog_change_percentage": 10.0,
    "max_relevance_score_drop": -0.10
  },

  "status": {
    "state": "ACTION_REQUIRED",
    "confidence": 0.93
  },

  "context": {
    "domain": "retail",
    "category": "Footwear",
    "region": "global",
    "channel": "web"
  },

  "error": null
}
