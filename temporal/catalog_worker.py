import asyncio
import logging
from dotenv import load_dotenv
from temporalio.client import Client

from temporalio.worker import Worker
from temporalio.contrib.google_adk_agents import GoogleAdkPlugin

load_dotenv()

from temporal.catalog_workflows import AdkSearchOpsWorkflow
from temporal import catalog_activities as activities

async def main():
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="search-ops-task-queue",
        workflows=[AdkSearchOpsWorkflow],
        activities=[
            activities.catalog_coverage,
            activities.schema_validation,
            activities.apply_patch,
            activities.vector_refresh,
            activities.fetch_diffy_report,
            activities.evaluate_metrics,
            activities.initiate_canary_release,
            activities.execute_rollback,
        ],
        plugins=[GoogleAdkPlugin()],
    )
    
    logging.info("🚀 Temporal Worker with ADK Plugin started...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())