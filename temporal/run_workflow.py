import asyncio
from temporalio.client import Client

from temporal.workflows import SearchAiRepairWorkflow

async def main():
    client = await Client.connect("localhost:7233")

    # This is the initial signal that will kick off the entire agent pipeline.
    # We'll use the one designed to trigger a deep RCA run.
    initial_signal = {
        "signal_id": "data-corruption-789",
        "description": "System logs show random, unstructured errors related to data formats.",
        "raw_data_sample": "{\"product_id\":\"ABC-123\", \"description\":\"A comfortable......\\u0000\\u001f......mouse.\"}"
    }

    print("Executing Search AI Repair Workflow...")
    result = await client.execute_workflow(
        SearchAiRepairWorkflow.run,
        initial_signal,
        id="search-ai-repair-workflow",
        task_queue="search-ai-task-queue",
    )

    print("\nWorkflow completed. Final Evaluation Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
