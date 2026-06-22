import asyncio
import json
from dataclasses import dataclass, asdict
from typing import Any

from .catalog_repository import CatalogRepository
from .catalog_coverage_tool import CatalogCoverageTool, CatalogCoverageResult
from .schema_validation import CatalogSchemaValidationTool, CatalogSchemaValidationResult
from .freshness import CatalogFreshnessTool, CatalogFreshnessResult
from .common_signals import sample_signal


@dataclass
class CapabilityMappingResult:
    tool_name: str
    status: str
    affected_capabilities: list[str]
    root_cause_candidate: str
    evidence: list[str]


class CatalogCapabilityMappingTool:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository
        self.coverage_tool = CatalogCoverageTool(repository)
        self.schema_tool = CatalogSchemaValidationTool(repository)
        self.freshness_tool = CatalogFreshnessTool(repository)

    async def run(self, signal_data: dict[str, 'Any']) -> 'CapabilityMappingResult':
        affected_capabilities: list[str] = []
        evidence: list[str] = []
        root_cause_candidate = "none"

        # Run all relevant tools
        coverage_result = await self.coverage_tool.run(signal_data)
        schema_result = await self.schema_tool.run(signal_data)
        freshness_result = await self.freshness_tool.run(signal_data)

        # Analyze results from CatalogCoverageTool
        if coverage_result.status == "degraded":
            evidence.extend(coverage_result.evidence)
            if "catalog_coverage_gap" == coverage_result.root_cause_candidate:
                affected_capabilities.append("search_results_completeness")
                affected_capabilities.append("recommendations_accuracy")
                root_cause_candidate = "catalog_coverage_gap"
            if "catalog_attribute_gap" == coverage_result.root_cause_candidate:
                affected_capabilities.append("semantic_search_relevance")
                affected_capabilities.append("attribute_filtering")
                root_cause_candidate = "catalog_attribute_gap"
            if "stale_catalog_data" == coverage_result.root_cause_candidate:
                affected_capabilities.append("search_results_freshness")
                affected_capabilities.append("recommendations_freshness")
                root_cause_candidate = "stale_catalog_data"


        # Analyze results from CatalogSchemaValidationTool
        if schema_result.status == "failed":
            evidence.extend(schema_result.evidence)
            affected_capabilities.append("data_integrity")
            affected_capabilities.append("semantic_embedding_quality")
            if schema_result.root_cause_candidate != "none":
                root_cause_candidate = schema_result.root_cause_candidate

        # Analyze results from CatalogFreshnessTool
        if freshness_result.is_stale:
            evidence.extend(freshness_result.evidence)
            affected_capabilities.append("search_results_freshness")
            affected_capabilities.append("recommendations_freshness")
            if freshness_result.root_cause_candidate != "none":
                root_cause_candidate = freshness_result.root_cause_candidate


        status = "healthy" if not affected_capabilities else "degraded"

        # Remove duplicates and sort
        affected_capabilities = sorted(list(set(affected_capabilities)))

        if not evidence and status == "healthy":
            evidence.append("No immediate capability impacts detected.")

        return CapabilityMappingResult(
            tool_name="CatalogCapabilityMappingTool",
            status=status,
            affected_capabilities=affected_capabilities,
            root_cause_candidate=root_cause_candidate,
            evidence=evidence,
        )


if __name__ == "__main__":
    async def main():
        repo = CatalogRepository()
        tool = CatalogCapabilityMappingTool(repo)
        result = await tool.run(sample_signal)

        print("\n")
        print("=" * 70)
        print("CATALOG CAPABILITY MAPPING RESULT")
        print("=" * 70)

        print(json.dumps(asdict(result), indent=2))

    asyncio.run(main())
