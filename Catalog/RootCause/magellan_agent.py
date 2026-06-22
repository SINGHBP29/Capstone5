"""Fast-RLM Root Cause agent for the Catalog package."""

from __future__ import annotations

import asyncio
import ast
import json
import os
import re
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

try:
    from fast_rlm import FastRLM, RLMEnvironment, llm_query_tool
except ImportError:  # pragma: no cover - optional dependency path
    FastRLM = None
    RLMEnvironment = None

    def llm_query_tool(func):  # type: ignore[misc]
        return func


from .Tools.catalog_coverage_tool import CatalogCoverageTool
from .Tools.catalog_repository import CatalogRepository
from .Tools.capability_mapping_tools import CatalogCapabilityMappingTool
from .Tools.freshness import CatalogFreshnessTool
from .Tools.historical_intent import CatalogHistoricalIntentTool
from .Tools.schema_validation import CatalogSchemaValidationTool
from .Tools.search_Quality import CatalogSearchQualityTool
from .Tools.vector_sync import CatalogVectorSyncTool
from .Tools.common_signals import sample_signal


def _to_plain_object(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


def _safe_parse_structured_text(text: str) -> Any:
    cleaned = re.sub(r"```python|```json|```", "", text).strip()
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(cleaned)
        except Exception:
            continue
    return text


@llm_query_tool
async def rlm_sub_query(prompt: str, context_chunk: str) -> Any:
    """Leaf worker used by the FastRLM loop."""

    worker_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    template = ChatPromptTemplate.from_template(
        "You are a specialized SearchOps worker node checking a slice of catalog data.\n"
        "Instructions: {prompt}\n\n"
        "Data Scope Fragment:\n{context_chunk}\n\n"
        "Return your findings strictly as a valid Python literal or JSON object.\n"
        "Do not include markdown or conversational commentary."
    )
    chain = template | worker_llm | StrOutputParser()
    raw_response = await chain.ainvoke(
        {"prompt": prompt, "context_chunk": context_chunk}
    )
    return _safe_parse_structured_text(raw_response)


class MagellanFastRLMOpsAgent:
    """FastRLM-shaped SearchOps root cause agent."""

    def __init__(
        self,
        capability_role: str = "Catalog Root Cause",
        model_name: str = "gpt-4o",
        repository: Optional[CatalogRepository] = None,
    ) -> None:
        load_dotenv()
        self.root_llm: Optional[ChatOpenAI] = None
        self.model_name = model_name
        self.capability_role = capability_role
        self.repository = repository or CatalogRepository()
        self.max_turns = 5

        self.coverage_tool_instance = CatalogCoverageTool(self.repository)
        self.schema_tool_instance = CatalogSchemaValidationTool(self.repository)
        self.freshness_tool_instance = CatalogFreshnessTool(self.repository)
        self.historical_intent_tool_instance = CatalogHistoricalIntentTool(
            self.repository
        )
        self.search_quality_tool_instance = CatalogSearchQualityTool(self.repository)
        self.capability_mapping_tool_instance = CatalogCapabilityMappingTool(
            self.repository
        )
        self.vector_sync_tool_instance = CatalogVectorSyncTool(self.repository)

        self.tools: Dict[str, Any] = {
            "catalog_coverage_tool": self.coverage_tool_instance.run,
            "catalog_schema_validation_tool": self.schema_tool_instance.run,
            "catalog_freshness_tool": self.freshness_tool_instance.run,
            "catalog_historical_intent_tool": self.historical_intent_tool_instance.run,
            "catalog_search_quality_tool": self.search_quality_tool_instance.run,
            "catalog_capability_mapping_tool": self.capability_mapping_tool_instance.run,
            "catalog_vector_sync_tool": self.vector_sync_tool_instance.run,
        }

        self.system_prompt = (
            f"You are the Magellan {capability_role} driven natively by a fast-RLM library pipeline.\n"
            "Your master catalog payload is pinned safely inside the workspace as `master_data`.\n"
            "A parsed `signal_data` dictionary is also available for direct tool calls.\n\n"
            "LIBRARY EXECUTION CONSTRAINTS:\n"
            "1. DO NOT print or mirror the complete `master_data` variable.\n"
            "2. Use standard Python scripts to slice or batch-segment the data stream.\n"
            "3. You have access to an async leaf worker: `await rlm_sub_query(instructions, chunk)`.\n"
            "4. You have direct access to registered tools: `catalog_coverage_tool`, `catalog_schema_validation_tool`,\n"
            "   `catalog_freshness_tool`, `catalog_historical_intent_tool`, `catalog_search_quality_tool`,\n"
            "   `catalog_capability_mapping_tool`, and `catalog_vector_sync_tool`.\n"
            "5. HIGH-PERFORMANCE MANDATE: Bundle chunk tasks into a list and execute them concurrently using\n"
            "   `await asyncio.gather(*tasks)`.\n"
            "6. COMPOSITION BY REFERENCE: Save sub-call results directly into explicit variable definitions.\n"
            "7. HARD TERMINATION: When the analytical loop finishes, register the clean structured dictionary by\n"
            "   invoking `FINAL(your_variable_name)`.\n\n"
            "Output your code block inside a single ```repl ... ``` markdown envelope.\n"
            "Harness Query: {query}\n"
            "Workspace Execution Feedback (stdout): {stdout_feedback}"
        )

    def _build_root_llm(self) -> ChatOpenAI:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "OPENAI_API_KEY environment variable not set for FastRLM execution."
            )
        return ChatOpenAI(model=self.model_name, temperature=0)

    @staticmethod
    def _coerce_payload(data_payload: Any) -> Dict[str, Any]:
        if isinstance(data_payload, dict):
            return dict(data_payload)
        if isinstance(data_payload, str):
            loaded = json.loads(data_payload)
            if not isinstance(loaded, dict):
                raise TypeError("JSON payload must decode to a dictionary.")
            return loaded
        raise TypeError(
            "data_payload must be either a dictionary or a JSON string."
        )

    @staticmethod
    def _derive_query(signal_data: Dict[str, Any]) -> str:
        signal_section = signal_data.get("signal", {})
        if isinstance(signal_section, dict):
            summary = str(signal_section.get("summary", "")).strip()
            if summary:
                return summary

        signal_id = str(signal_data.get("signal_id", "")).strip()
        if signal_id:
            return f"Investigate root cause for signal {signal_id}"

        entity = signal_data.get("catalog_entity", {})
        if isinstance(entity, dict):
            brand = str(entity.get("brand", "")).strip()
            category = str(entity.get("category", "")).strip()
            if brand or category:
                return f"Investigate root cause for {brand} {category}".strip()

        return "Investigate the catalog root cause."

    @staticmethod
    def _register_value(env: Any, name: str, value: Any) -> None:
        if hasattr(env, "register_tool") and callable(value):
            try:
                env.register_tool(name, value)
                return
            except Exception:
                pass
        if hasattr(env, "register_variable"):
            env.register_variable(name, value)
            return
        raise AttributeError("FastRLM environment does not support registration.")

    @staticmethod
    def _register_module(env: Any, module_name: str, module: Any) -> None:
        if hasattr(env, "register_module"):
            env.register_module(module_name, module)
            return
        MagellanFastRLMOpsAgent._register_value(env, module_name, module)

    @staticmethod
    def _normalize_final_payload(payload: Any) -> Any:
        if isinstance(payload, str):
            parsed = _safe_parse_structured_text(payload)
            return parsed
        if is_dataclass(payload):
            return asdict(payload)
        return payload

    async def execute_runbook(self, query: str, data_payload: Any) -> Dict[str, Any]:
        """Execute the actual FastRLM loop."""

        if FastRLM is None or RLMEnvironment is None:
            raise ImportError(
                "fast_rlm is not installed. Install the fast_rlm package to run "
                "MagellanFastRLMOpsAgent.execute_runbook()."
            )

        if self.root_llm is None:
            self.root_llm = self._build_root_llm()

        signal_data = self._coerce_payload(data_payload)
        master_data = json.dumps(signal_data, indent=2, default=str)

        r_env = RLMEnvironment()
        self._register_value(r_env, "master_data", master_data)
        self._register_value(r_env, "signal_data", signal_data)
        self._register_value(r_env, "query", query)
        self._register_value(r_env, "rlm_sub_query", rlm_sub_query)

        for tool_name, tool in self.tools.items():
            self._register_value(r_env, tool_name, tool)

        self._register_module(r_env, "asyncio", asyncio)
        self._register_module(r_env, "json", json)
        self._register_module(r_env, "re", re)

        stdout_feedback = "Workspace Active - Pointers mapped."

        async with FastRLM(environment=r_env) as rlm_session:
            for turn in range(self.max_turns):
                prompt = ChatPromptTemplate.from_template(self.system_prompt)
                chain = prompt | self.root_llm | StrOutputParser()
                llm_response = await chain.ainvoke(
                    {"query": query, "stdout_feedback": stdout_feedback}
                )

                code_match = re.search(r"```repl(.*?)```", llm_response, re.DOTALL)
                if code_match:
                    code_to_execute = code_match.group(1).strip()
                    execution_result = await rlm_session.run_cell(code_to_execute)
                    stdout_feedback = getattr(execution_result, "stdout", "") or ""
                else:
                    stdout_feedback = (
                        f"Error: No formatted ```repl code block provided on Turn {turn}."
                    )

                if rlm_session.is_finalized():
                    final_payload = self._normalize_final_payload(
                        rlm_session.get_final_payload()
                    )
                    return {
                        "status": "SUCCESS",
                        "evidence_pack": final_payload,
                        "query": query,
                        "total_turns": turn + 1,
                    }

        return {
            "status": "ESCALATED",
            "evidence_pack": None,
            "error": "Fast-RLM execution window closed without resolving a FINAL payload.",
            "query": query,
        }

    async def run_agent(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience wrapper for package-local callers."""

        query = self._derive_query(signal_data)
        return await self.execute_runbook(query, signal_data)


# Backwards-compatible aliases for the names used elsewhere in the package.
MagellanRootCauseAgent = MagellanFastRLMOpsAgent
RootCauseAgent = MagellanFastRLMOpsAgent


async def main() -> None:
    agent = MagellanFastRLMOpsAgent()
    final_result = await agent.run_agent(sample_signal)
    print(json.dumps(final_result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
