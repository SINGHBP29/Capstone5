import asyncio
import time
from temporalio.client import Client
from temporal.workflows import AutocompleteAiRepairWorkflow

async def main():
    client = await Client.connect("localhost:7233")

    initial_signal = {
        "description": "Users are reporting irrelevant search suggestions for the query 'shirt'."
    }

    # Use a unique ID for each workflow run to avoid conflicts
    workflow_id = f"autocomplete-ai-repair-workflow-{int(time.time())}"

    print(f"Executing Autocomplete AI Repair Workflow with ID: {workflow_id}")
    result = await client.execute_workflow(
        AutocompleteAiRepairWorkflow.run,
        initial_signal,
        id=workflow_id,
        task_queue="search-ai-task-queue",
    )

    print("\nWorkflow completed. Final Evaluation Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
