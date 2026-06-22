import os
import json
import time
import logging
import datetime
from typing import Dict, Any, Optional

from ..config import MOCK_MODE, CANARY_TIERS, CANARY_SOAK_TIME_SECONDS, CANARY_MAX_HOLDS
from ..db import OCSDatabase
from ..main import run_feedback_pipeline
from .traffic_router import set_traffic_weight
from .rollback import execute_rollback

logger = logging.getLogger("feedback_agent.canary.controller")


class CanaryReleaseController:
    """
    Orchestrates a progressive canary release through traffic tiers.

    State machine:
        PENDING → IN_PROGRESS → (per tier: PROMOTE/HOLD/ROLLBACK) → COMPLETED | ROLLED_BACK | HELD
    """

    def __init__(self, input_path: str, output_dir: str):
        """
        Args:
            input_path: Path to the input.json from FixPlanAgent.
            output_dir: Directory to write per-tier feedback results and final canary result.
        """
        self.input_path = input_path
        self.output_dir = output_dir
        self.db = OCSDatabase()
        self.tiers = CANARY_TIERS  # [5, 25, 50, 100]
        self.soak_time = CANARY_SOAK_TIME_SECONDS
        self.max_holds = CANARY_MAX_HOLDS

        # Load input to extract query and incident_id
        with open(input_path, 'r') as f:
            self.input_data = json.load(f)

        self.query = self.input_data.get("query") or self.input_data.get("result", {}).get("query", "")
        self.incident_id = self._extract_incident_id()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def _extract_incident_id(self) -> str:
        """Extracts incident ID from input data, matching AuditTrailAgent logic."""
        artifact_dir = self.input_data.get("result", {}).get("applyResult", {}).get("artifactDir", "")
        if artifact_dir and "sequential-" in artifact_dir:
            try:
                parts = artifact_dir.split("sequential-")
                if len(parts) > 1:
                    time_part = parts[1].split("/")[0]
                    date_str = time_part.split("_")[0]
                    return f"INC-{date_str}-001"
            except Exception:
                pass
        return f"INC-{datetime.datetime.now().strftime('%Y%m%d')}-001"

    def run(self) -> Dict[str, Any]:
        """
        Executes the full canary release lifecycle.

        Returns:
            Dict containing the final canary release result.
        """
        logger.info(f"Starting canary release for incident {self.incident_id}, query '{self.query}'")
        logger.info(f"Tiers: {self.tiers}, Soak time: {self.soak_time}s, Max holds: {self.max_holds}")

        # Initialize DB record
        self._create_db_record()

        tier_results = []
        hold_count = 0
        final_status = "COMPLETED"

        for tier_index, tier_percent in enumerate(self.tiers):
            logger.info(f"--- Canary Tier {tier_index + 1}/{len(self.tiers)}: {tier_percent}% ---")

            # Step 1: Set traffic weight
            weight_ok = set_traffic_weight(tier_percent, self.query)
            if not weight_ok:
                logger.error(f"Failed to set traffic weight to {tier_percent}%. Triggering rollback.")
                rollback_result = execute_rollback(self.query, self.incident_id, self.db, "Traffic routing failure")
                final_status = "ROLLED_BACK"
                tier_results.append({
                    "tier_percent": tier_percent,
                    "decision": "ROLLBACK",
                    "reason": "Failed to set traffic weight",
                    "rollback": rollback_result
                })
                break

            # Step 2: Soak — wait for telemetry to accumulate
            if self.soak_time > 0 and tier_percent < 100:
                logger.info(f"Soaking for {self.soak_time}s to collect telemetry at {tier_percent}%...")
                time.sleep(self.soak_time)

            # Step 3: Run the Feedback Agent pipeline for this tier
            tier_output_path = os.path.join(
                self.output_dir, f"feedback_tier_{tier_percent}.json"
            )
            logger.info(f"Running Feedback Agent pipeline → {tier_output_path}")
            run_feedback_pipeline(self.input_path, tier_output_path)

            # Step 4: Read the feedback result and extract the decision
            feedback_result = self._read_feedback_result(tier_output_path)
            decision = feedback_result.get("decision", {})
            action = decision.get("action", "HOLD")
            confidence = decision.get("confidence", 0.0)
            reason = decision.get("reason", "")

            tier_result = {
                "tier_percent": tier_percent,
                "decision": action,
                "confidence": confidence,
                "reason": reason,
                "metrics": feedback_result.get("metrics", {}),
                "timestamp": datetime.datetime.now().astimezone().isoformat(timespec='seconds')
            }
            tier_results.append(tier_result)

            # Step 5: Act on the decision
            if action == "PROMOTE":
                hold_count = 0  # Reset hold counter on a successful promotion
                self._update_db_tier(tier_percent, "PROMOTE", json.dumps([t["tier_percent"] for t in tier_results if t["decision"] == "PROMOTE"]))
                logger.info(f"✅ PROMOTED at {tier_percent}%.")

                if tier_percent == 100:
                    final_status = "COMPLETED"
                    logger.info("🎉 Canary release completed — 100% traffic on candidate.")
                # else: loop continues to next tier

            elif action == "ROLLBACK":
                logger.warning(f"🔴 ROLLBACK triggered at {tier_percent}%: {reason}")
                rollback_result = execute_rollback(self.query, self.incident_id, self.db, reason)
                tier_result["rollback"] = rollback_result
                final_status = "ROLLED_BACK"
                break

            elif action == "HOLD":
                hold_count += 1
                logger.warning(f"🟡 HOLD at {tier_percent}% (hold #{hold_count}/{self.max_holds}): {reason}")

                if hold_count >= self.max_holds:
                    logger.error(f"Max hold count ({self.max_holds}) reached. Escalating to HELD state.")
                    final_status = "HELD"
                    self._update_db_status("HELD")
                    break
                else:
                    # Stay at the same tier — re-run feedback after another soak
                    logger.info(f"Re-soaking at {tier_percent}% before retry...")
                    # We do NOT advance the tier. The `for` loop will move to the next tier,
                    # but we want to retry. So we need to handle this differently.
                    # For simplicity: on HOLD, we DO NOT advance. We break and report HELD.
                    final_status = "HELD"
                    self._update_db_status("HELD")
                    break

        # Build final canary release result
        canary_result = {
            "agent": "CanaryReleaseController",
            "incident_id": self.incident_id,
            "query": self.query,
            "status": final_status,
            "tiers_evaluated": len(tier_results),
            "tiers_promoted": len([t for t in tier_results if t["decision"] == "PROMOTE"]),
            "tier_results": tier_results,
            "final_traffic_percent": tier_results[-1]["tier_percent"] if tier_results else 0,
            "timestamp": datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        }

        # Write final result
        final_path = os.path.join(self.output_dir, "canary_release_result.json")
        with open(final_path, 'w') as f:
            json.dump(canary_result, f, indent=2)
        logger.info(f"Canary release result saved to {final_path}")

        # Update DB final state
        self._finalize_db(final_status)
        self.db.close()

        return canary_result

    def _read_feedback_result(self, path: str) -> Dict[str, Any]:
        """Reads a feedback_result JSON file."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read feedback result from {path}: {e}")
            return {}

    def _create_db_record(self):
        """Inserts the initial canary release record."""
        try:
            self.db.execute_query(
                """
                INSERT INTO canary_releases (incident_id, query, current_tier, status)
                VALUES (?, ?, 0, 'IN_PROGRESS')
                """,
                (self.incident_id, self.query)
            )
        except Exception as e:
            logger.error(f"Failed to create canary DB record: {e}")

    def _update_db_tier(self, tier: int, decision: str, tiers_completed_json: str):
        """Updates the current tier and completed tiers in the DB."""
        try:
            self.db.execute_query(
                """
                UPDATE canary_releases
                SET current_tier = ?, tiers_completed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE incident_id = ? AND query = ?
                """,
                (tier, tiers_completed_json, self.incident_id, self.query)
            )
        except Exception as e:
            logger.error(f"Failed to update canary tier in DB: {e}")

    def _update_db_status(self, status: str):
        """Updates the canary release status."""
        try:
            self.db.execute_query(
                """
                UPDATE canary_releases
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE incident_id = ? AND query = ?
                """,
                (status, self.incident_id, self.query)
            )
        except Exception as e:
            logger.error(f"Failed to update canary status in DB: {e}")

    def _finalize_db(self, final_status: str):
        """Marks the canary release as complete in the DB."""
        try:
            self.db.execute_query(
                """
                UPDATE canary_releases
                SET status = ?, final_decision = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE incident_id = ? AND query = ?
                """,
                (final_status, final_status, self.incident_id, self.query)
            )
        except Exception as e:
            logger.error(f"Failed to finalize canary DB record: {e}")
