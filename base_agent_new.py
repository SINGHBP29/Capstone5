import os
import json
import asyncio
import logging
import inspect
import subprocess
import functools
import functools
from functools import cached_property
from typing import List, Dict, Any, Callable, Optional, AsyncGenerator

from dotenv import load_dotenv

# ── Google ADK imports ────────────────────────────────────────────────────────
from google.adk.agents import BaseAgent as AdkBaseAgent, LlmAgent, InvocationContext
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import Client, types as genai_types
from google.adk.events import Event
from google.adk.models.llm import LlmRequest

# ── fast-rlm imports ──────────────────────────────────────────────────────────
import fast_rlm
from fast_rlm import RLMConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Vertex-AI-backed Gemini model for ADK
# Uses Application Default Credentials (ADC) — no API key needed
# ─────────────────────────────────────────────────────────────────────────────
class VertexGemini(Gemini):
    """Gemini model that always routes through Vertex AI (IAM auth)."""

    @cached_property
    def api_client(self) -> Client:
        return Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )


def _get_vertex_access_token() -> str:
    """
    Fetch a short-lived ADC access token via gcloud.
    This token is used as the Bearer token for Vertex AI's
    OpenAI-compatible endpoint, which fast-rlm's Deno engine calls directly.

    Requires:
        gcloud auth application-default login
    or GOOGLE_APPLICATION_CREDENTIALS set to a service-account key path.
    """
    result = subprocess.run(
        ["gcloud", "auth", "application-default", "print-access-token"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ─────────────────────────────────────────────────────────────────────────────
# BaseAgent — built on Google ADK, 100% Vertex AI
# ─────────────────────────────────────────────────────────────────────────────
class BaseAgent(AdkBaseAgent):
    """
    A foundational agent class built on Google ADK with Vertex AI only.

    Public API (same as original):
      - register_tool(name, func, description, parameters_schema)
      - get_system_prompt()   ← subclasses must override
      - run(signal_data) → Dict[str, Any]

    Auth: Application Default Credentials
        gcloud auth application-default login
    or GOOGLE_APPLICATION_CREDENTIALS pointing to a service-account key.

    Required env vars:
        GOOGLE_CLOUD_PROJECT   — GCP project ID
        GOOGLE_CLOUD_LOCATION  — GCP region (default: us-central1)
    """
    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        enable_deep_rca: bool = False,
    ):
        super().__init__(name="BaseAgentOrchestrator")
        load_dotenv()

        self.model_name = model_name
        self.enable_deep_rca = enable_deep_rca

        # Holds current signal so tool wrappers can inject it
        self.current_signal_data: Optional[Dict[str, Any]] = None

        # Internal registries
        self._tool_functions: Dict[str, Callable] = {}
        self._adk_tools: List[FunctionTool]  = []

        # Vertex-AI-backed ADK model (shared across run_agent calls)
        self._vertex_model = VertexGemini(model=self.model_name)

        # ── fast-rlm / deep-RCA setup ────────────────────────────────────────
        if self.enable_deep_rca:
            project  = os.getenv("GOOGLE_CLOUD_PROJECT", "")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

            self.rlm_config = RLMConfig()

            # Model name as used by Vertex AI's OpenAI-compatible endpoint.
            # The Deno engine sends this as the "model" field in the
            # chat.completions.create call to Vertex AI.
            self.rlm_config.primary_agent = f"google/{self.model_name}"
            self.rlm_config.sub_agent     = f"google/{self.model_name}"

            # Valid RLMConfig fields only (verified against dataclass definition)
            self.rlm_config.max_depth              = 2
            self.rlm_config.max_calls_per_subagent = 10
            self.rlm_config.truncate_len           = 1000
            self.rlm_config.max_completion_tokens  = 4000
            self.rlm_config.max_money_spent        = 0.5
            self.rlm_config.enable_tools           = True
            self.rlm_config.enable_structured_io   = True

            # ✅ Vertex AI OpenAI-compatible endpoint.
            # fast-rlm's Deno engine reads RLM_MODEL_BASE_URL and
            # RLM_MODEL_API_KEY as MODULE-LEVEL constants in call_llm.ts —
            # they MUST be set on the host process os.environ BEFORE
            # fast_rlm.run() is called. env_variables={} only injects into
            # the Pyodide REPL and is NOT visible to the Deno host.
            self._rlm_vertex_base_url = (
                f"https://{location}-aiplatform.googleapis.com/v1/"
                f"projects/{project}/locations/{location}/endpoints/openapi"
            )

            self.register_tool(
                name="run_deep_rca_investigation",
                func=self._run_deep_rca_investigation_tool,
                description=(
                    "Deeply analyzes unknown or complex issues by writing Python "
                    "scripts and spawning recursive sub-agents to explore raw data."
                ),
            )

    # ── Tool registration ────────────────────────────────────────────────────

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters_schema: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a Python callable as an ADK FunctionTool.
        ADK auto-derives the JSON schema from type annotations + docstring.
        Tools declaring a `signal` or `signal_data` parameter have the
        current run's signal_data injected automatically.
        """
        func_sig          = inspect.signature(func)
        needs_signal      = "signal"      in func_sig.parameters
        needs_signal_data = "signal_data" in func_sig.parameters

        async def wrapper(*args, **kwargs):
            if needs_signal and "signal" not in kwargs:
                if self.current_signal_data is None:
                    raise ValueError(f"Tool '{name}' needs signal but signal_data is not set.")
                kwargs["signal"] = self.current_signal_data
            if needs_signal_data and "signal_data" not in kwargs:
                if self.current_signal_data is None:
                    raise ValueError(f"Tool '{name}' needs signal_data but it is not set.")
                kwargs["signal_data"] = self.current_signal_data
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return await asyncio.to_thread(func, *args, **kwargs)

        wrapper.__name__ = name
        wrapper.__doc__  = func.__doc__ or description

        self._adk_tools.append(FunctionTool(func=wrapper))
        self._tool_functions[name] = func
        logger.info(f"Registered tool: {name}")

    # ── Subclass contract ────────────────────────────────────────────────────

    def get_system_prompt(self) -> str:
        """Subclasses MUST override this to provide their specific instructions."""
        raise NotImplementedError("Subclasses must implement get_system_prompt()")

    # ── Direct tool execution (bypass ADK loop when needed) ──────────────────

    async def execute_tool(self, name: str, args: dict) -> Any:
        """Execute a registered tool by name with the given args dict."""
        if name not in self._tool_functions:
            logger.error(f"Unknown tool requested: {name}")
            return {"error": f"Unknown tool: {name}"}
        logger.info(f"Executing tool: {name} with args: {args}")
        func = self._tool_functions[name]
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**args)
            else:
                result = await asyncio.to_thread(func, **args)
            logger.info(f"Tool {name} complete.")
            return result
        except Exception as e:
            logger.exception(f"Tool execution failed: {name}")
            return {"error": str(e)}

    # ── ADK agent execution ──────────────────────────────────────────────────
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Core asynchronous execution logic for the custom agent."""
        system_prompt = self.get_system_prompt()

        # Create a transient LlmAgent to execute the turn, configured at runtime
        # This preserves the pattern of configuring the agent just before the run.
        llm_sub_agent = LlmAgent(
            name="ExecutingAgent",
            model=self._vertex_model,
            instruction=system_prompt,
            tools=self._adk_tools,
            generate_content_config=genai_types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=4000,
            ),
        )

        # Delegate the execution to the sub-agent
        async for event in llm_sub_agent.run_async(ctx):
            yield event

    async def fast_rlm_route(self, prompt: str, valid_tools: List[str]) -> List[str]:
        """
        Uses the ADK agent to route to the correct tool based on the prompt.
        """
        response = self._vertex_model.generate_content_async(
            LlmRequest(prompt=prompt)
        )
        first_chunk = await response.__anext__()
        response_text = first_chunk.text
        async for chunk in response:
            response_text += chunk.text
        text = response_text.strip().replace("```json", "").replace("```", "").strip()
        try:
            tools_to_run = json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Fast-RLM: Failed to parse tool list from LLM response: {text}")
            tools_to_run = []
        
        valid_tools_to_run = [t for t in tools_to_run if t in valid_tools]
        logger.info(f"Fast-RLM selected remediation tools: {valid_tools_to_run}")
        return valid_tools_to_run

    async def llm_query(self, query: str) -> str:
        """
        Spawns a sub-agent to answer a query.
        """
        response = await self._vertex_model.generate_content_async(
            LlmRequest(prompt=query)
        )
        response_text = ""
        async for chunk in response:
            response_text += chunk.text
        return response_text

    # ── fast-rlm deep-RCA tool ───────────────────────────────────────────────

    async def _run_deep_rca_investigation_tool(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deeply analyzes unknown or complex issues by writing Python scripts
        and spawning recursive sub-agents to explore raw data.

        Args:
            signal: The signal data dict to investigate.

        Returns:
            Structured dict with status, root_cause_finding, summary_finding,
            and evidence_finding fields.
        """
        logger.info("Fast-RLM: Starting deep investigation...")

        # Load mock DB if present
        db_path = os.path.join(os.path.dirname(__file__), "..", "mock_catalog_db.db")
        db_content = "[]"
        try:
            with open(db_path, "r") as f:
                db_content = f.read()
        except FileNotFoundError:
            logger.warning(f"mock_catalog_db.db not found at {db_path}, using empty content.")

        # ── Fetch a fresh ADC access token ───────────────────────────────────
        try:
            access_token = await asyncio.to_thread(_get_vertex_access_token)
        except Exception as e:
            logger.error(f"Failed to get Vertex AI access token: {e}")
            return {
                "status": "ERROR",
                "error": f"Could not obtain Vertex AI access token: {e}",
            }

        # ✅ Set on the HOST process env — this is what Deno inherits
        os.environ["RLM_MODEL_BASE_URL"] = self._rlm_vertex_base_url
        os.environ["RLM_MODEL_API_KEY"]  = access_token

        logger.info(f"Fast-RLM routing to Vertex AI: {self._rlm_vertex_base_url}")

        query_prompt = f"Analyze this signal via REPL: {json.dumps(signal)}"

        try:
            response = await asyncio.to_thread(
                fast_rlm.run,
                query_prompt,       # ✅ positional arg — NOT a kwarg
                config=self.rlm_config,
                __tools__={
                    "llm_query": self.llm_query,
                },
                env_variables={
                    # These are only needed inside the Pyodide REPL for tool code
                    "MOCK_DB_DATA":          db_content,
                    "GOOGLE_CLOUD_PROJECT":  os.getenv("GOOGLE_CLOUD_PROJECT", ""),
                    "GOOGLE_CLOUD_LOCATION": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
                },
                verbose=True,
            )

            rlm_results = response.get("results", "")
            rlm_usage   = response.get("usage", {})
            logger.info(f"Fast-RLM usage: {rlm_usage}")

            return {
                "status":             "SUCCESS",
                "root_cause_finding": "Deep investigation performed by RLM subagent.",
                "summary_finding":    "RLM subagent completed; see evidence for details.",
                "evidence_finding":   [str(rlm_results)],  # Capture the raw string output
                "usage":              rlm_usage,
            }

        except Exception as e:
            logger.error(f"Deep investigation failed: {str(e)}")
            return {
                "status": "ERROR",
                "error":  f"Deep investigation failed: {str(e)}",
            }

    # ── JSON cleanup ─────────────────────────────────────────────────────────

    def _clean_json(self, text: str) -> str:
        text = text.strip()
        for fence in ("```json", "```"):
            if text.startswith(fence):
                text = text[len(fence):]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    # ── Main entry point ─────────────────────────────────────────────────────
async def run_agent(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the ADK agent with the provided signal data.
        """
        logger.info("Starting ADK agent run...")
        self.current_signal_data = signal_data
        
        # Pass the tools to the deep rca tool
        if "run_deep_rca_investigation" in self._tool_functions:
            self._tool_functions["run_deep_rca_investigation"] = functools.partial(
                self._run_deep_rca_investigation_tool,
                __tools__=self._tool_functions,
            )

        agent = self._create_adk_agent()
        runner = Runner(agent=agent, session_service=InMemorySessionService())
        
        user_input = json.dumps(signal_data, indent=2)
        response = await runner.run(user_input)
        
        return {
            "response_text": response.text,
            "response_parts": response.parts,
        }
        Runs the ADK agent with the provided signal data.
        """
        logger.info("Starting ADK agent run...")
        self.current_signal_data = signal_data
        
        # Pass the tools to the deep rca tool
        if "run_deep_rca_investigation" in self._tool_functions:
            self._tool_functions["run_deep_rca_investigation"] = functools.partial(
                self._run_deep_rca_investigation_tool,
                __tools__=self._tool_functions,
            )

        agent = self._create_adk_agent()
        runner = Runner(agent=agent, session_service=InMemorySessionService())
        
        user_input = json.dumps(signal_data, indent=2)
        response = await runner.run(user_input)
        
        return {
            "response_text": response.text,
            "response_parts": response.parts,
        }

    async def run_to_completion(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the ADK agent with the given signal data and returns the final result.
        """
        self.current_signal_data = signal_data

        user_message  = f"Signal data: {json.dumps(signal_data)}"

        session_service = InMemorySessionService()
        runner = Runner(
            agent=self,
            app_name="base_agent_app",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="base_agent_app",
            user_id="default_user",
        )

        logger.info("Starting ADK agent run...")

        collected_parts: List[str] = []

        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_message)],
            ),
        ):
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        collected_parts.append(part.text)

        final_text = self._clean_json("\n".join(collected_parts))

        if not final_text:
            logger.warning("Agent returned empty response.")
            return {"response_text": ""}

        try:
            return json.loads(final_text)
        except json.JSONDecodeError:
            return {"response_text": final_text}
