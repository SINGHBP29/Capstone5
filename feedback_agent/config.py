import os

# Mode Selection
# If MOCK_MODE is True, we simulate API responses using data parsed from input.json
MOCK_MODE = os.environ.get("OCS_MOCK_MODE", "True").lower() in ("true", "1", "yes")

# OCS Component API URLs
OCS_SEARCH_URL = os.environ.get("OCS_SEARCH_URL", "http://localhost:8534")
OCS_INDEXER_URL = os.environ.get("OCS_INDEXER_URL", "http://localhost:8535")
OCS_CONFIG_URL = os.environ.get("OCS_CONFIG_URL", "http://localhost:8536")
OCS_SUGGEST_URL = os.environ.get("OCS_SUGGEST_URL", "http://localhost:8536/suggest") # Or suggest service specific port

# Elasticsearch Base URL
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")

# Database Connection (Postgres)
# Using a local mock/sqlite fallback or postgres if configured
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING", "postgresql://postgres:postgres@localhost:5432/ocs_audit")

# --- Canary Release Settings ---

# Ordered list of traffic tiers (percentages). The controller advances through these.
CANARY_TIERS = [5, 25, 50, 100]

# How long (in seconds) to wait between tiers to collect telemetry.
# In mock mode, set to 0 for instant progression.
CANARY_SOAK_TIME_SECONDS = int(os.environ.get("CANARY_SOAK_TIME", "0" if MOCK_MODE else "300"))

# Maximum number of consecutive HOLD decisions before auto-escalating to human review.
CANARY_MAX_HOLDS = int(os.environ.get("CANARY_MAX_HOLDS", "3"))

# OCS traffic routing header name used to split canary vs baseline traffic.
CANARY_ROUTING_HEADER = os.environ.get("CANARY_ROUTING_HEADER", "X-OCS-Canary-Weight")

