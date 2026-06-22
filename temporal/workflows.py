from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities import (
        root_cause_activity,
        fix_proposal_activity,
        eval_activity,
        release_activity,
        autocomplete_root_cause_activity,
        autocomplete_fix_proposal_activity,
        autocomplete_eval_activity,
        semantic_root_cause_activity,
        semantic_fix_proposal_activity,
        semantic_eval_activity,
        deploy_canary_activity,
        rollback_deployment_activity,
        promote_canary_activity,
        get_deployment_status_activity,
        run_feedback_activity # New feedback activity
    )

@workflow.defn
class UnifiedSearchAiRepairWorkflow:
    def __init__(self):
        self._is_approved = False

    @workflow.run
    async def run(self, signal: dict) -> dict:
        """
        Executes a unified pipeline that intelligently routes to the correct
        RCA and Fix agents based on the signal type, then uses a shared
        Eval and Release process with a human-in-the-loop approval step.
        """
        workflow.logger.info(f"Starting Unified Search AI Repair Workflow for signal type: {signal.get('type')}")

        signal_type = signal.get("type")
        if signal_type == "catalog":
            rca_activity = root_cause_activity
            fix_activity = fix_proposal_activity
            service_name = "catalog-service" # Example service name for catalog
        elif signal_type == "autocomplete":
            rca_activity = autocomplete_root_cause_activity
            fix_activity = autocomplete_fix_proposal_activity
            service_name = "autocomplete-service" # Example service name for autocomplete
        elif signal_type == "semantic":
            rca_activity = semantic_root_cause_activity
            fix_activity = semantic_fix_proposal_activity
            service_name = "semantic-service" # Example service name for semantic
        else:
            raise ValueError(f"Unknown signal type: {signal_type}")

        rca_result = await workflow.execute_activity(
            rca_activity, signal, start_to_close_timeout=timedelta(minutes=5)
        )
        fix_result = await workflow.execute_activity(
            fix_activity, rca_result, start_to_close_timeout=timedelta(minutes=5)
        )
        eval_result = await workflow.execute_activity(
            eval_activity, fix_result, start_to_close_timeout=timedelta(minutes=5)
        )

        # Shared Human-in-the-loop and Release logic
        ndcg_score = eval_result.get("metrics", {}).get("shadow", {}).get("ndcg@10", 1.0)
        threshold = 0.84

        if ndcg_score < threshold:
            workflow.logger.warning(
                f"NDCG score of {ndcg_score} is below the threshold of {threshold}. "
                f"Workflow is paused pending human approval. To approve, run 'python3 -m temporal.signal_workflow.py'"
            )
            await workflow.wait_for(lambda: self._is_approved)
            workflow.logger.info("Deployment has been manually approved. Proceeding.")
        else:
            workflow.logger.info(
                f"NDCG score of {ndcg_score} is above threshold. Proceeding automatically."
            )
        
        approval_status = {
            "status": "Deployment Approved",
            "evaluation_summary": eval_result.get("summary", "N/A"),
            "final_ndcg": ndcg_score
        }

        release_result = await workflow.execute_activity(
            release_activity, approval_status, start_to_close_timeout=timedelta(minutes=1)
        )

        # Act on the ReleaseAgent's decision
        release_decision = release_result.get("decision")

        if release_decision == "PROMOTE_CANARY":
            workflow.logger.info(f"Release Agent decided to PROMOTE_CANARY for {service_name}.")
            await workflow.execute_activity(
                deploy_canary_activity, service_name, "canary-image:latest", 1,
                start_to_close_timeout=timedelta(minutes=5)
            )
            await workflow.sleep(timedelta(seconds=10)) # Simulate monitoring
            await workflow.execute_activity(
                get_deployment_status_activity, service_name,
                start_to_close_timeout=timedelta(minutes=1)
            )
            await workflow.execute_activity(
                promote_canary_activity, service_name,
                start_to_close_timeout=timedelta(minutes=5)
            )
            final_action_summary = f"Canary for {service_name} deployed and promoted."
        elif release_decision == "ROLLBACK":
            workflow.logger.info(f"Release Agent decided to ROLLBACK for {service_name}.")
            await workflow.execute_activity(
                rollback_deployment_activity, service_name,
                start_to_close_timeout=timedelta(minutes=5)
            )
            final_action_summary = f"Rollback initiated for {service_name}.
The issue likely requires further investigation or a new fix."
        else: # NO_ACTION or any other unexpected decision
            workflow.logger.info("Release Agent decided NO_ACTION or an unknown action.")
            final_action_summary = "No automated release action taken based on the agent's decision."

        workflow.logger.info("Unified Search AI Repair Workflow completed successfully.")
        
        # Send final workflow outcome to feedback agent
        feedback_input = {
            "query": signal.get("query", "N/A"),
            "result": {
                "workflow_status": "Completed",
                "final_action": final_action_summary,
                "signal_type": signal_type,
                "ndcg_score": ndcg_score,
                "release_decision": release_decision
            },
            "signal": signal # Pass the original signal for context
        }
        feedback_output = await workflow.execute_activity(
            run_feedback_activity, feedback_input, start_to_close_timeout=timedelta(minutes=5)
        )
        workflow.logger.info(f"Feedback Agent Output: {feedback_output}")

        return {"workflow_status": "Completed", "final_action": final_action_summary, "feedback_result": feedback_output}

    @workflow.signal
    def approve_deployment(self):
        """Signal method to approve a deployment that is pending review."""
        self._is_approved = True

@workflow.defn
class SemanticAiRepairWorkflow:
    @workflow.run
    async def run(self, signal: dict) -> dict:
        """
        Executes the full Semantic Root Cause, Fix, and Evaluation pipeline.
        """
        workflow.logger.info("Starting Semantic AI Repair Workflow...")

        rca_result = await workflow.execute_activity(
            semantic_root_cause_activity, signal, start_to_close_timeout=timedelta(minutes=5)
        )
        fix_result = await workflow.execute_activity(
            semantic_fix_proposal_activity, rca_result, start_to_close_timeout=timedelta(minutes=5)
        )
        eval_result = await workflow.execute_activity(
            semantic_eval_activity, fix_result, start_to_close_timeout=timedelta(minutes=5)
        )
        
        workflow.logger.info("Semantic AI Repair Workflow completed successfully.")
        return eval_result
