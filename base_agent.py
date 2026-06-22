import os
import json
import asyncio
import logging
import inspect
from typing import Any, Callable, Optional, List
import subprocess

from dotenv import load_dotenv
import fast_rlm
from fast_rlm import RLMConfig

# -------------------------
# SETUP
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
load_dotenv()

# -------------------------
# AUTH HELPER
# -------------------------
def _get_vertex_access_token() -> str:
    """Fetches a short-lived ADC access token via gcloud."""
    result = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()

# -------------------------
# BASE AGENT
# -------------------------
class BaseAgent:
    """
    A foundational agent class built exclusively for the fast-rlm engine.
    Handles tool registration, engine configuration, and the core execution loop.
    Subclasses should override `get_system_prompt` and optionally `format_user_message`.
    """
    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        enable_deep_rca: bool = False,
    ):
        self.model_name = model_name
        self.enable_deep_rca = enable_deep_rca
        self.current_signal_data: Optional[dict[str, Any]] = None
        self._tool_functions: dict[str, Callable] = {}
        
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        # --- fast-rlm Configuration ---
        self.rlm_config = RLMConfig()
        self.rlm_config.primary_agent = f"google/{model_name}"
        self.rlm_config.sub_agent = f"google/{model_name}"
        self.rlm_config.max_depth = 2
        self.rlm_config.max_calls_per_subagent = 10
        self.rlm_config.truncate_len = 1000
        self.rlm_config.max_completion_tokens = 8000
        self.rlm_config.max_money_spent = 0.5
        self.rlm_config.enable_tools = True
        self.rlm_config.enable_structured_io = True

        self._rlm_vertex_base_url = (
            f"https://{location}-aiplatform.googleapis.com/v1/"
            f"projects/{project}/locations/{location}/endpoints/openapi"
        )

        if self.enable_deep_rca:
            self.register_tool(
                name="run_deep_rca_investigation",
                func=self._run_deep_rca_investigation_tool,
                description=(
                    "Deeply analyzes unknown or complex issues by writing Python "
                    "scripts and spawning recursive sub-agents to explore raw data."
                ),
            )

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
    ):
        """Registers a Python callable as a tool for the fast-rlm agent."""

        # Capture signature and argument requirements during registration
        func_sig = inspect.signature(func)
        needs_signal = "signal" in func_sig.parameters
        needs_signal_data = "signal_data" in func_sig.parameters

        async def wrapper(*args, **kwargs):
            import inspect # Ensure inspect is available within the wrapper's scope
            # Auto-inject signal data if the tool function expects it
            if (needs_signal and "signal" not in kwargs) or \
               (needs_signal_data and "signal_data" not in kwargs):
                if self.current_signal_data is None:
                    raise ValueError(f"Tool '{name}' needs signal data but it is not set.")
                # Provide both for convenience, as some tools might use one or the other
                kwargs["signal"] = self.current_signal_data
                kwargs["signal_data"] = self.current_signal_data

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return await asyncio.to_thread(func, *args, **kwargs)

        wrapper.__name__ = name
        wrapper.__doc__ = func.__doc__ or description
        self._tool_functions[name] = wrapper
        logger.info(f"Registered tool: {name}")

    def get_system_prompt(self) -> str:
        """Subclasses MUST override this to provide their specific instructions."""
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    def format_user_message(self, signal_data: dict) -> str:
        """Subclasses can override this to format the user message differently."""
        return f"Signal data: {json.dumps(signal_data)}"

    async def run_agent(self, signal_data: dict[str, Any]) -> dict[str, Any]:
        """
        Runs the agent using the fast-rlm engine. This is the primary
        execution method for all subclasses.
        """
        logger.info("Starting fast-rlm agent run.")
        self.current_signal_data = signal_data

        system_prompt = self.get_system_prompt()
        user_message = self.format_user_message(signal_data)
        query_prompt = f"{system_prompt}\n{user_message}"

        try:
            access_token = await asyncio.to_thread(_get_vertex_access_token)
        except Exception as e:
            logger.error(f"Failed to get Vertex AI access token: {e}")
            return {"status": "ERROR", "error": f"Could not obtain Vertex AI access token: {e}"}

        os.environ["RLM_MODEL_BASE_URL"] = self._rlm_vertex_base_url
        os.environ["RLM_MODEL_API_KEY"] = access_token
        logger.info(f"Fast-RLM routing to Vertex AI: {self._rlm_vertex_base_url}")

        try:
            response = await asyncio.to_thread(
                fast_rlm.run,
                query_prompt,
                config=self.rlm_config,
                tools=list(self._tool_functions.values()),
                verbose=True,
            )

            rlm_results = response.get("results", "")
            if isinstance(rlm_results, dict):
                return rlm_results
            try:
                return json.loads(rlm_results)
            except (json.JSONDecodeError, TypeError):
                logger.warning("fast-rlm result is not a valid JSON. Returning as text.")
                return {"response_text": str(rlm_results)}

        except Exception as e:
            logger.error(f"fast-rlm run failed: {str(e)}")
            return {"status": "ERROR", "error": f"fast-rlm run failed: {str(e)}"}

    async def _run_deep_rca_investigation_tool(self, signal: dict[str, 'Any']) -> dict[str, 'Any']:
        """
        Spawns a specialist sub-agent to analyze complex data issues by writing
        and executing its own Python code.
        """
        logger.info("Fast-RLM: Starting deep investigation sub-agent...")
        
        try:
            access_token = await asyncio.to_thread(_get_vertex_access_token)
        except Exception as e:
            logger.error(f"Failed to get Vertex AI access token for sub-agent: {e}")
            return {
                "status": "ERROR", "root_cause_finding": "Authentication Error",
                "summary_finding": "Failed to authenticate for sub-agent execution.",
                "evidence_finding": [str(e)],
            }

        os.environ["RLM_MODEL_BASE_URL"] = self._rlm_vertex_base_url
        os.environ["RLM_MODEL_API_KEY"]  = access_token

        output_schema = """
        {
          "status": "string", "root_cause_finding": "string",
          "summary_finding": "string", "evidence_finding": ["string"]
        }
        """
        query_prompt = (
            f"You are a specialist Root Cause Analysis sub-agent. Your only capability is to write and execute Python code in a REPL environment to analyze the provided data signal. "
            f"Signal: {json.dumps(signal)}\n\n"
            f"Your goal is to find the root cause of the issue described in the signal. "
            f"When you have finished your investigation, you MUST call the FINAL tool with a JSON object that strictly adheres to the following schema:\n"
            f"{output_schema}"
        )

        try:
            # The sub-agent is given no tools. This is intentional to force it
            # to rely on its code-writing capabilities and prevent context conflicts.
            response = await asyncio.to_thread(
                fast_rlm.run, query_prompt, config=self.rlm_config, tools=[], verbose=True
            )

            rlm_results = response.get("results", "")
            rlm_usage   = response.get("usage", {})

            if isinstance(rlm_results, dict):
                return rlm_results
            return {
                "status": "SUCCESS", "root_cause_finding": "Deep investigation performed by sub-agent.",
                "summary_finding": "Sub-agent completed. See evidence for raw output.",
                "evidence_finding": [str(rlm_results)], "usage": rlm_usage,
            }
        except Exception as e:
            logger.error(f"Sub-agent execution failed: {e}")
            return {
                "status": "ERROR", "root_cause_finding": "Sub-agent Execution Failed",
                "summary_finding": "The deep investigation sub-agent threw an exception.",
                "evidence_finding": [str(e)],
            }
