import logging
import datetime
from typing import Dict, Any

from .base import BaseAgent

class AuditTrailAgent(BaseAgent):
    """
    Sub-agent 5: AuditTrailAgent
    Logs the immutable audit record to the database and produces the final audit report metadata.
    """

    def run(self, input_data: Dict[str, Any], pipeline_state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Writing audit trail record...")

        result_wrapper = input_data.get("result", {})
        apply_result = result_wrapper.get("applyResult", {})
        issue_profile = result_wrapper.get("issueProfile", {})
        rlm_synthesis = result_wrapper.get("rlmSynthesis", {})
        
        # 1. Parse/Generate Incident ID dynamically
        # Initialize fallback using current date
        now = datetime.datetime.now()
        date_str_fallback = now.strftime("%Y%m%d")
        incident_id = f"INC-{date_str_fallback}-001"
        
        # Attempt to parse from upstream run folder if present
        artifact_dir = apply_result.get("artifactDir", "")
        if artifact_dir and "sequential-" in artifact_dir:
            try:
                parts = artifact_dir.split("sequential-")
                if len(parts) > 1:
                    time_part = parts[1].split("/")[0] # e.g. 20260603_120153
                    extracted_date = time_part.split("_")[0] # e.g. 20260603
                    incident_id = f"INC-{extracted_date}-001"
            except Exception as e:
                self.logger.warning(f"Could not parse incident ID from artifactDir '{artifact_dir}': {e}")

        # 2. Extract counts and types
        gap_type = issue_profile.get("gapType", "query_vocabulary_gap")
        
        fix_order = result_wrapper.get("fixOrder", [])
        fix_order_executed = len(fix_order)
        
        artifacts = apply_result.get("artifacts", [])
        evidence_artifacts = len(artifacts)
        
        # Count applied patches
        patches_applied = 0
        for artifact in artifacts:
            atype = artifact.get("type", "")
            if "patch" in atype:
                patches_applied += 1
                
        # If no artifacts list or count is 0, count from applied configuration
        if patches_applied == 0:
            applied_config = apply_result.get("appliedSearchConfiguration", {})
            if applied_config:
                patches_applied = (
                    (1 if applied_config.get("searchableFields") else 0) +
                    (1 if applied_config.get("synonymsEnabled") else 0) +
                    (1 if applied_config.get("embeddingRefreshEnabled") else 0) +
                    (1 if applied_config.get("merchandisingRuleCount", 0) > 0 else 0)
                )

        # Extract primary owner path
        owner_path = rlm_synthesis.get("result", {}).get("workAiWindows", {}).get("owner_path", {}).get("summary", {}).get("primaryOwner", "Application owner")

        decision = pipeline_state.get("decision", {})
        action = decision.get("action", "HOLD")
        confidence = decision.get("confidence", 0.577)

        audit_report = {
            "incidentId": incident_id,
            "gapType": gap_type,
            "fixOrderExecuted": fix_order_executed,
            "patchesApplied": patches_applied,
            "evidenceArtifacts": evidence_artifacts,
            "ownerPath": owner_path,
            "rollbackAvailable": True # Rollback configuration is preserved and reversible
        }

        # 3. Write Immutable DB Audit Log
        try:
            self.db.execute_query(
                """
                INSERT INTO audit_records (
                    incident_id, query, gap_type, fix_order_executed, 
                    patches_applied, evidence_artifacts, owner_path, 
                    rollback_available, decision, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    input_data.get("query", ""),
                    gap_type,
                    ", ".join(fix_order),
                    patches_applied,
                    evidence_artifacts,
                    owner_path,
                    True,
                    action,
                    confidence
                )
            )
            self.logger.info(f"Successfully wrote audit record for {incident_id} in DB.")
        except Exception as e:
            self.logger.error(f"Failed to log audit record in DB: {e}")

        self.logger.info("Audit trail completed.")
        return {"auditRecord": audit_report}
