import logging
from ..config import MOCK_MODE, OCS_CONFIG_URL, CANARY_ROUTING_HEADER

logger = logging.getLogger("feedback_agent.canary.traffic_router")

def set_traffic_weight(tier_percent: int, query: str) -> bool:
    """
    Updates the OCS traffic routing weight for the canary configuration.

    Args:
        tier_percent: The percentage of traffic to route to the candidate config (0-100).
        query: The incident query (for logging/scoping).

    Returns:
        True if the weight was successfully applied, False otherwise.
    """
    logger.info(f"Setting canary traffic weight to {tier_percent}% for query '{query}'")

    if MOCK_MODE:
        logger.info(f"[MOCK] Traffic weight set to {tier_percent}%. No live API call made.")
        return True
    else:
        import requests
        try:
            # OCS Config Service endpoint to update traffic routing rules.
            # This assumes OCS exposes a config endpoint for canary weights.
            # Adjust the URL path and payload schema to match your OCS deployment.
            url = f"{OCS_CONFIG_URL}/config-service/v1/traffic-routing"
            payload = {
                "canaryWeight": tier_percent,
                "baselineWeight": 100 - tier_percent,
                "scope": query,
                "routingHeader": CANARY_ROUTING_HEADER
            }
            response = requests.put(url, json=payload, timeout=5)

            if response.status_code in (200, 204):
                logger.info(f"Traffic weight updated to {tier_percent}% via Config Service.")
                return True
            else:
                logger.error(f"Config Service returned status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to set traffic weight: {e}")
            return False


def reset_traffic_to_baseline(query: str) -> bool:
    """
    Resets all traffic to the baseline configuration (0% canary).
    Called during rollback.
    """
    logger.info(f"Resetting all traffic to baseline (0% canary) for query '{query}'")
    return set_traffic_weight(0, query)
