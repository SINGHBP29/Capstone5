import logging
import datetime
from typing import Dict, Any
from .traffic_router import reset_traffic_to_baseline
from ..config import MOCK_MODE, OCS_CONFIG_URL
from ..db import OCSDatabase

logger = logging.getLogger("feedback_agent.canary.rollback")

def execute_rollback(query: str, incident_id: str, db: OCSDatabase, reason: str) -> Dict[str, Any]:
    """
    Performs a full rollback:
    1. Resets traffic weight to 0% (baseline only).
    2. Reverts OCS search configuration changes (synonyms, fields, rules).
    3. Logs the rollback event to the database.

    Args:
        query: The incident query string.
        incident_id: The incident identifier.
        db: Database connection instance.
        reason: Human-readable reason for the rollback.

    Returns:
        Dict with rollback status and details.
    """
    logger.warning(f"Executing rollback for incident {incident_id}, query '{query}'")

    rollback_report = {
        "status": "ROLLED_BACK",
        "incident_id": incident_id,
        "query": query,
        "reason": reason,
        "steps_executed": [],
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    }

    # Step 1: Reset traffic routing
    traffic_ok = reset_traffic_to_baseline(query)
    rollback_report["steps_executed"].append({
        "step": "reset_traffic_to_baseline",
        "success": traffic_ok
    })

    # Step 2: Revert OCS configurations
    config_ok = _revert_ocs_config(query)
    rollback_report["steps_executed"].append({
        "step": "revert_ocs_config",
        "success": config_ok
    })

    # Step 3: Update canary release record in DB
    try:
        db.execute_query(
            """
            UPDATE canary_releases
            SET status = 'ROLLED_BACK',
                final_decision = 'ROLLBACK',
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE incident_id = ? AND query = ?
            """,
            (incident_id, query)
        )
        rollback_report["steps_executed"].append({
            "step": "update_db_record",
            "success": True
        })
    except Exception as e:
        logger.error(f"Failed to update canary DB record during rollback: {e}")
        rollback_report["steps_executed"].append({
            "step": "update_db_record",
            "success": False,
            "error": str(e)
        })

    # Step 4: Update watchlist status to REGRESSED
    try:
        db.execute_query(
            """
            INSERT INTO watchlist (query, status, monitoring_window, regression_threshold)
            VALUES (?, 'REGRESSED', '0d', 'immediate_revert')
            ON CONFLICT(query) DO UPDATE SET status = 'REGRESSED'
            """,
            (query,)
        )
    except Exception as e:
        logger.error(f"Failed to update watchlist during rollback: {e}")

    rollback_report["all_success"] = all(
        step["success"] for step in rollback_report["steps_executed"]
    )

    logger.info(f"Rollback completed. All steps successful: {rollback_report['all_success']}")
    return rollback_report


def _revert_ocs_config(query: str) -> bool:
    """
    Reverts OCS Config Service to the pre-fix baseline.
    In mock mode, logs and returns True.
    In live mode, calls the Config Service revert endpoint.
    """
    if MOCK_MODE:
        logger.info(f"[MOCK] Reverted OCS config for query '{query}'.")
        return True
    else:
        import requests
        try:
            url = f"{OCS_CONFIG_URL}/config-service/v1/revert"
            response = requests.post(url, json={"scope": query}, timeout=5)
            if response.status_code in (200, 204):
                logger.info("OCS config reverted via Config Service.")
                return True
            else:
                logger.error(f"Config revert failed with status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to revert OCS config: {e}")
            return False
