import asyncio
import sys
import contextlib
from temporalio import activity

# To ensure the parent directory is in the Python path for module resolution
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporal.shared import HeartbeatingStream
from Catalog.RootCause.google_agent import GoogleRootCauseAgent
from Catalog.Fix_Proposal.fix_agent import GoogleFixProposalAgent
from Catalog.Eval.eval_agent import GoogleEvalAgent
from Autocomplete.RootCause.main_agent import AutocompleteRootCauseAgent
from Autocomplete.Fix_Proposal.fix_agent import AutocompleteFixProposalAgent
from Autocomplete.Eval.eval_agent import AutocompleteEvalAgent
from Release.release_agent import ReleaseAgent
from Semantic.RootCause.main_agent import SemanticRootCauseAgent
from Semantic.Fix_Proposal.fix_agent import SemanticFixProposalAgent
from Semantic.Eval.eval_agent import SemanticEvalAgent
from Catalog.Eval.Tools.diffy_client import DiffyApiClient # Ensure correct DiffyApiClient is imported
from Catalog.Eval.Tools.diffy_client import DiffyApiClient # Ensure correct DiffyApiClient is imported

import httpx # Import httpx for making async HTTP requests

FEEDBACK_AGENT_URL = os.getenv("FEEDBACK_AGENT_URL", "http://feedback-agent:8000")

@activity.defn
async def run_feedback_activity(input_data: dict) -> dict:
    """Temporal activity to send data to the Feedback Agent and get its response."""
    activity.logger.info(f"Sending feedback data to Feedback Agent at {FEEDBACK_AGENT_URL}/run_feedback...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{FEEDBACK_AGENT_URL}/run_feedback", json=input_data)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            feedback_result = response.json()
            activity.logger.info("Feedback Agent responded successfully.")
            return feedback_result
        except httpx.HTTPStatusError as e:
            activity.logger.error(f"HTTP error communicating with Feedback Agent: {e}")
            raise
        except httpx.RequestError as e:
            activity.logger.error(f"Network error communicating with Feedback Agent: {e}")
            raise

@activity.defn
async def root_cause_activity(signal: dict) -> dict:
    """Temporal activity to run the Root Cause Analysis agent."""
    activity.logger.info("Executing Root Cause Analysis activity...")
    agent = GoogleRootCauseAgent()
    
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            result = await agent.run_agent(signal)
            activity.logger.info("Root Cause Analysis completed.")
            return result

@activity.defn
async def fix_proposal_activity(rca_output: dict) -> dict:
    """
    Runs the Fix Proposal agent, ensures a project exists in Diffy,
    and then creates a new diff in the live Diffy service.
    """
    activity.logger.info("Executing Fix Proposal activity...")
    agent = GoogleFixProposalAgent()
    # Note: The 'apiKey' is the default required by the open-source Diffy project.
    diffy_client = DiffyApiClient(base_url="http://localhost:8888", api_key="apiKey")
    project_slug = "my-ai-project"

    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            fix_result = await agent.run_agent(rca_output)
            activity.logger.info("Fix Proposal completed.")

            # Step 1: Ensure the project exists in Diffy.
            await diffy_client.create_project_if_not_exists(slug=project_slug, name="My AI-Managed Project")

            # Step 2: Create a diff with simulated production and shadow HTTP requests.
            baseline_request = (
                "GET /search?q=shoes HTTP/1.1\n"
                "Host: production.example.com\n"
                "User-Agent: Diffy-Client\n\n"
            )
            shadow_request = (
                "GET /search?q=shoes HTTP/1.1\n"
                "Host: shadow.example.com\n"
                "User-Agent: Diffy-Client\n\n"
            )
            
            activity.logger.info(f"Creating a new diff in project '{project_slug}' on the live Diffy server...")
            diff_creation_result = await diffy_client.create_diff(
                baseline=baseline_request, 
                shadow=shadow_request,
                project=project_slug
            )
            
            return {
                "fix_proposal_summary": fix_result.get("summary", "N/A"),
                "diff_id": diff_creation_result.get("id")
            }


@activity.defn
async def eval_activity(fix_output: dict) -> dict:
    """
    Temporal activity to run the Evaluation agent.
    It receives the output from the fix_proposal_activity, including the
    dynamic 'diff_id', and uses it to run the evaluation.
    """
    activity.logger.info("Executing Evaluation activity...")
    agent = GoogleEvalAgent()

    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            # The signal for the eval agent is now dynamically constructed
            # from the output of the previous activity.
            eval_signal = {
                "diff_id": fix_output.get("diff_id"),
                "context": fix_output.get("fix_proposal_summary")
            }
            result = await agent.run_agent(eval_signal)
            activity.logger.info("Evaluation completed.")
            return result

@activity.defn
async def autocomplete_root_cause_activity(signal: dict) -> dict:
    """Temporal activity to run the Autocomplete Root Cause Analysis agent."""
    activity.logger.info("Executing Autocomplete Root Cause Analysis activity...")
    agent = AutocompleteRootCauseAgent()
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            return await agent.run_agent(signal)

@activity.defn
async def autocomplete_fix_proposal_activity(rca_output: dict) -> dict:
    """Temporal activity to run the Autocomplete Fix Proposal agent."""
    activity.logger.info("Executing Autocomplete Fix Proposal activity...")
    agent = AutocompleteFixProposalAgent()
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            return await agent.run_agent(rca_output)

@activity.defn
async def autocomplete_eval_activity(fix_output: dict) -> dict:
    """Temporal activity to run the Autocomplete Evaluation agent."""
    activity.logger.info("Executing Autocomplete Evaluation activity...")
    agent = AutocompleteEvalAgent()
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            return await agent.run_agent(fix_output)

@activity.defn
async def release_activity(eval_output: dict) -> dict:
    """Temporal activity to run the final Release agent."""
    activity.logger.info("Executing Release activity...")
    agent = ReleaseAgent()
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            # The release agent just needs the final approval status
            return await agent.run_agent(eval_output)

@activity.defn
async def semantic_root_cause_activity(signal: dict) -> dict:
    """Temporal activity to run the Semantic Root Cause Analysis agent."""
    activity.logger.info("Executing Semantic Root Cause Analysis activity...")
    agent = SemanticRootCauseAgent()
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            return await agent.run_agent(signal)

@activity.defn
async def semantic_fix_proposal_activity(rca_output: dict) -> dict:
    """Temporal activity to run the Semantic Fix Proposal agent."""
    activity.logger.info("Executing Semantic Fix Proposal activity...")
    agent = SemanticFixProposalAgent()
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            return await agent.run_agent(rca_output)

@activity.defn
async def semantic_eval_activity(fix_output: dict) -> dict:
    """Temporal activity to run the Semantic Evaluation agent."""
    activity.logger.info("Executing Semantic Evaluation activity...")
    agent = SemanticEvalAgent()
    with HeartbeatingStream() as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            return await agent.run_agent(fix_output)

async def _run_kubectl_command(command: str) -> str:
    """
    Helper to run kubectl commands. For local Docker Compose development, this simulates
    the kubectl execution. For actual Kubernetes deployment, this function should be
    replaced with interactions using a Kubernetes client library (e.g., `kubernetes-client/python`)
    or by executing `kubectl` commands directly in a pod with appropriate RBAC.
    """
    activity.logger.info(f"Simulating kubectl command: {command}")
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error_message = stderr.decode().strip()
        activity.logger.error(f"kubectl command failed (simulated): {error_message}")
        # In a real scenario, you might want to raise a specific exception or handle this more gracefully
        raise RuntimeError(f"Simulated kubectl command failed: {error_message}")
    
    output = stdout.decode().strip()
    activity.logger.info(f"Simulated kubectl output: {output}")
    return output

@activity.defn
async def deploy_canary_activity(service_name: str, image: str, replicas: int) -> str:
    """
    Temporal activity to deploy a canary version of a service.
    This simulates applying a Kubernetes deployment manifest.
    """
    activity.logger.info(f"Deploying canary for {service_name} with image {image}, replicas {replicas}...")
    # In a real-world scenario, you'd generate/apply a K8s manifest
    # For this example, we'll use a placeholder command
    command = f"kubectl apply -f kubernetes/deployment-canary.yaml --record --force --wait --server-side --field-manager=kubectl-client-side-apply"
    # Note: This is a simplified representation. A real implementation would involve
    # dynamically generating or patching the deployment manifest.
    result = await _run_kubectl_command(command)
    activity.logger.info(f"Canary deployment initiated for {service_name}.")
    return result

@activity.defn
async def rollback_deployment_activity(service_name: str) -> str:
    """
    Temporal activity to roll back a service to its previous stable version.
    This simulates reverting a Kubernetes deployment.
    """
    activity.logger.info(f"Initiating rollback for {service_name}...")
    command = f"kubectl rollout undo deployment/{service_name}"
    result = await _run_kubectl_command(command)
    activity.logger.info(f"Rollback initiated for {service_name}.")
    return result

@activity.defn
async def promote_canary_activity(service_name: str) -> str:
    """
    Temporal activity to promote the canary deployment to primary.
    This would involve updating the primary deployment to use the canary image.
    """
    activity.logger.info(f"Promoting canary for {service_name}...")
    # This is a placeholder. Real promotion might involve updating the primary deployment
    # with the canary's image, or shifting traffic.
    command = f"kubectl set image deployment/{service_name}-primary {service_name}-primary={service_name}-canary-image" # Example command
    result = await _run_kubectl_command(command)
    activity.logger.info(f"Canary promoted for {service_name}.")
    return result

@activity.defn
async def get_deployment_status_activity(service_name: str) -> str:
    """
    Temporal activity to get the status of a Kubernetes deployment.
    """
    activity.logger.info(f"Getting deployment status for {service_name}...")
    command = f"kubectl rollout status deployment/{service_name}"
    result = await _run_kubectl_command(command)
    activity.logger.info(f"Deployment status for {service_name}: {result.strip()}")
    return result
