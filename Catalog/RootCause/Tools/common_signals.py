sample_signal={
  "timestamp": "2026-06-16T11:00:00Z",
  "source": "magellan_search_monitor",
  "tenant": "outdoor_gear_co",

  "signal_id": "magellan-prod-relevance-005",
  "signal_type": "search_relevance_degradation",
  "diff_id": "magellan-diff-s24-001", # ID of the shadow test to evaluate (if applicable)
  "severity": "critical",

  "catalog_entity": {
    "product_id": "TH-GT-007",
    "category": "Gloves",
    "brand": "Trailhead Gear"
  },

  "signal": {
    "summary": "Product 'TH-GT-007' (Waterproof Winter Gloves) experiencing 40% drop in search impressions due to data corruption and missing attributes.",
    "detected_at": "2026-06-16T10:45:00Z",
    "recommended_action": "Deep dive into product data integrity and re-index affected SKUs."
  },

  "metrics": {
    "search_impressions_drop_percent": 40,
    "missing_attributes_count": 1,
    "corrupted_data_fields": ["description"]
  },

  "evidence": [
    {
      "field": "description",
      "issue": "malformed_encoding",
      "value_sample": "Winter gloves for extreme ☃️ conditions. Built with durable fabrics.",
      "expected_format": "UTF-8 plaintext"
    },
    {
      "field": "material",
      "issue": "missing_attribute",
      "value": None,
      "expected_values": ["Gore-Tex", "Polyester", "Wool"]
    },
    {
      "field": "availability_status",
      "issue": "incorrect_value",
      "value": "out_of_stock",
      "expected_value": "in_stock"
    }
  ],

  "impact": {
    "search_relevance_risk": "critical",
    "semantic_embedding_impact": True,
    "filtering_impact": True,
    "affected_capabilities": [
      "semantic_search",
      "attribute_filtering",
      "product_discoverability",
      "inventory_sync"
    ]
  },

  "remediation": {
    "action_type": "data_integrity_fix",
    "generate_patch": True,
    "trigger_reembedding": True,
    "reindex_search_catalog": True,
    "update_inventory_status": True,
    "priority": "highest"
  },

  "error": None,
  "raw_data_sample": {
    "product_id": "TH-GT-007",
    "name": "Waterproof Winter Gloves",
    "description": "Winter gloves for extreme \ud83d\ude04 conditions. Built with durable fabrics.",
    "category": "Gloves",
    "brand": "Trailhead Gear",
    "price": 129.99,
    "currency": "USD",
    "material": None,
    "waterproof_flag": True,
    "season": "winter",
    "availability_status": "out_of_stock",
    "last_updated": "2026-06-16T09:00:00Z"
  }
}

# This signal is designed to simulate a real-world issue that the Magellan AI Search Ops Harness
# would detect and route through the autonomous agent pipeline for diagnosis and remediation.
# It includes rich, structured data that the agents can analyze and act upon.
# In a production system, this would come from a real-time event bus
# like Kafka, sourced from an observability or merchandising tool.