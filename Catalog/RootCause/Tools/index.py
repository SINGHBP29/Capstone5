from dataclasses import dataclass
from dataclasses import asdict

from typing import List
from typing import Dict
from typing import Any

from datetime import datetime

from .search_index_repository import (
    SearchIndexRepository
)


@dataclass
class SearchIndexCoverageResult:

    tool_name: str

    status: str

    catalog_count: int

    indexed_count: int

    missing_documents: int

    stale_documents: int

    failed_index_jobs: int

    root_cause_candidate: str

    evidence: List[str]


class SearchIndexCoverageTool:

    def __init__(
        self,
        repository: SearchIndexRepository
    ):
        self.repository = repository

    async def run(
        self,
        signal_data: Dict[str, Any]
    ) -> SearchIndexCoverageResult:

        catalog_products = (
            await self.repository.get_catalog_products()
        )

        indexed_products = (
            await self.repository.get_search_index()
        )

        latest_job = (
            await self.repository.get_latest_index_job()
        )

        evidence = []

        catalog_count = len(catalog_products)

        indexed_count = len(indexed_products)

        catalog_map = {
            p["sku"]: p
            for p in catalog_products
        }

        index_map = {
            p["sku"]: p
            for p in indexed_products
        }

        # ------------------------------------
        # Missing Indexed Documents
        # ------------------------------------

        missing_docs = (
            set(catalog_map.keys())
            -
            set(index_map.keys())
        )

        missing_documents = len(missing_docs)

        if missing_documents:

            evidence.append(
                f"{missing_documents} products "
                f"missing from search index."
            )

            evidence.append(
                f"Missing SKUs: {list(missing_docs)}"
            )

        # ------------------------------------
        # Stale Indexed Documents
        # ------------------------------------

        stale_documents = 0

        for sku in index_map:

            if sku not in catalog_map:
                continue

            catalog_time = datetime.fromisoformat(
                catalog_map[sku]["updated_at"]
                .replace("Z", "+00:00")
            )

            index_time = datetime.fromisoformat(
                index_map[sku]["indexed_at"]
                .replace("Z", "+00:00")
            )

            if index_time < catalog_time:

                stale_documents += 1

        if stale_documents:

            evidence.append(
                f"{stale_documents} stale index "
                f"documents detected."
            )

        # ------------------------------------
        # Failed Index Jobs
        # ------------------------------------

        failed_jobs = 0

        if latest_job["status"] != "SUCCESS":

            failed_jobs = 1

            evidence.append(
                f"Latest index job status: "
                f"{latest_job['status']}"
            )

        # ------------------------------------
        # Root Cause
        # ------------------------------------

        if (
            missing_documents
            or stale_documents
            or failed_jobs
        ):

            status = "degraded"

            root_cause = (
                "search_index_failure"
            )

        else:

            status = "healthy"

            root_cause = "none"

            evidence.append(
                "Search index coverage healthy."
            )

        return SearchIndexCoverageResult(
            tool_name="SearchIndexCoverageTool",
            status=status,
            catalog_count=catalog_count,
            indexed_count=indexed_count,
            missing_documents=missing_documents,
            stale_documents=stale_documents,
            failed_index_jobs=failed_jobs,
            root_cause_candidate=root_cause,
            evidence=evidence
        )