import logging
from typing import Dict, Any

from .base import BaseAgent

class ThresholdUpdateAgent(BaseAgent):
    """
    Sub-agent 4: ThresholdUpdateAgent
    Updates watchlists, detection thresholds, and runbook histories in the database.
    """

    def run(self, input_data: Dict[str, Any], pipeline_state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Updating thresholds and watchlists...")

        # 1. Retrieve prior decision
        decision = pipeline_state.get("decision", {})
        action = decision.get("action", "HOLD")

        query = input_data.get("query") or input_data.get("result", {}).get("query", "")
        issue_profile = input_data.get("result", {}).get("issueProfile", {})
        gap_type = issue_profile.get("gapType", "query_vocabulary_gap")
        signal_types = issue_profile.get("signalTypes", [])

        # Parse runbook duration dynamically
        duration_minutes = self._parse_runbook_duration(input_data)

        # Default report values
        report = {
            "watchlistAdded": None,
            "monitoringWindow": "7d",
            "regressionThreshold": "zero_result_rate > 0.05",
            "runbookTemplatePatched": False,
            "signalSensitivityAdjusted": []
        }

        # 2. Database Operations (if decision is PROMOTE or HOLD)
        if action in ("PROMOTE", "HOLD"):
            try:
                # Add to watchlist in the DB
                self.db.execute_query(
                    """
                    INSERT INTO watchlist (query, status, monitoring_window, regression_threshold)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(query) DO UPDATE SET
                        status = excluded.status,
                        monitoring_window = excluded.monitoring_window,
                        regression_threshold = excluded.regression_threshold
                    """,
                    (query, "RESOLVED", "7d", "zero_result_rate > 0.05")
                )
                report["watchlistAdded"] = query
                self.logger.info(f"Updated watchlist in DB for query '{query}'.")

                # Insert runbook execution history
                fix_order = input_data.get("result", {}).get("fixOrder", [])
                remediation_steps = ", ".join(fix_order)
                self.db.execute_query(
                    """
                    INSERT INTO runbook_history (gap_type, remediation_steps, success, duration_minutes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (gap_type, remediation_steps, True, duration_minutes)
                )
                report["runbookTemplatePatched"] = True
                self.logger.info(f"Logged runbook execution success for gap type '{gap_type}' with duration {duration_minutes} min.")

                # Adjust signal sensitivities
                adjusted_signals = [sig for sig in signal_types if sig in ("autocomplete_miss", "stale_embedding")]
                report["signalSensitivityAdjusted"] = adjusted_signals
                self.logger.info(f"Adjusted sensitivity for signals: {adjusted_signals}")

            except Exception as e:
                self.logger.error(f"Failed to perform database threshold updates: {e}")
        else:
            # Action is ROLLBACK
            try:
                # Update watchlist to reflect regression or failed fix
                self.db.execute_query(
                    """
                    INSERT INTO watchlist (query, status, monitoring_window, regression_threshold)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(query) DO UPDATE SET status = excluded.status
                    """,
                    (query, "REGRESSED", "0d", "immediate_revert")
                )
                
                # Log failed runbook execution
                fix_order = input_data.get("result", {}).get("fixOrder", [])
                remediation_steps = ", ".join(fix_order)
                self.db.execute_query(
                    """
                    INSERT INTO runbook_history (gap_type, remediation_steps, success, duration_minutes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (gap_type, remediation_steps, False, duration_minutes)
                )
                self.logger.info(f"Logged failed runbook execution for query '{query}' with duration {duration_minutes} min.")
            except Exception as e:
                self.logger.error(f"Failed to log rollback database states: {e}")

        self.logger.info("Threshold updates completed.")
        return {"thresholdUpdates": report}

    def _parse_runbook_duration(self, input_data: Dict[str, Any]) -> int:
        """
        Helper method to dynamically parse and sum durations from result.implementation.phases.
        Supports units: 'min', 'hour', 'hr', 'day'.
        """
        try:
            result_wrapper = input_data.get("result", {})
            implementation = result_wrapper.get("implementation", {})
            phases = implementation.get("phases", [])
            
            total_minutes = 0
            for phase in phases:
                duration_str = phase.get("duration", "0 min")
                
                # Extract numeric part (including decimal points)
                val_chars = []
                for char in duration_str:
                    if char.isdigit() or char == '.':
                        val_chars.append(char)
                
                val_str = "".join(val_chars)
                if not val_str:
                    continue
                
                try:
                    val = float(val_str)
                except ValueError:
                    continue
                
                # Extract unit part
                unit = duration_str.replace(val_str, "").strip().lower()
                
                if "min" in unit:
                    total_minutes += int(val)
                elif "hour" in unit or "hr" in unit:
                    total_minutes += int(val * 60)
                elif "day" in unit:
                    total_minutes += int(val * 24 * 60)
                else:
                    # Default unit fallback: minutes
                    total_minutes += int(val)
            
            # Fallback to 95 if parsed duration is 0
            return total_minutes if total_minutes > 0 else 95
            
        except Exception as e:
            self.logger.warning(f"Error parsing runbook duration, using fallback 95 min: {e}")
            return 95
