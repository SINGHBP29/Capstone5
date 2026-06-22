import asyncio
import time
from temporalio.client import Client
from temporal.workflows import SemanticAiRepairWorkflow

async def main():
    client = await Client.connect("localhost:7233")

    initial_signal = {
        "description": "Users are reporting low relevance for the query 'red running shoes'."
    }

    workflow_id = f"semantic-ai-repair-workflow-{int(time.time())}"

    print(f"Executing Semantic AI Repair Workflow with ID: {workflow_id}")
    result = await client.execute_workflow(
        SemanticAiRepairWorkflow.run,
        initial_signal,
        id=workflow_id,
        task_queue="search-ai-task-queue",
    )

    print("\nWorkflow completed. Final Evaluation Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
