import asyncio
import time
import json
import sys
from temporalio.client import Client
from temporal.workflows import UnifiedSearchAiRepairWorkflow

async def main():
    client = await Client.connect("localhost:7233")

    # Determine the workflow type from the command-line argument, defaulting to 'catalog'
    valid_types = ["catalog", "autocomplete", "semantic"]
    signal_type = "catalog" # Default
    if len(sys.argv) > 1 and sys.argv[1] in valid_types:
        signal_type = sys.argv[1]

    print(f"Preparing to run a '{signal_type}' workflow.")

    # Create a relevant signal based on the type
    if signal_type == "catalog":
        try:
            with open("Catalog/search_events.jsonl", "r") as f:
                first_line = f.readline()
                initial_signal = json.loads(first_line)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading search_events.jsonl: {e}. Using a fallback signal.")
            initial_signal = {"description": "Fallback signal for catalog."}
    elif signal_type == "autocomplete":
        initial_signal = {
            "description": "Users are reporting irrelevant search suggestions for the query 'shirt'."
        }
    elif signal_type == "semantic":
        initial_signal = {
            "description": "Users are reporting low relevance for the query 'red running shoes'."
        }
    
    initial_signal["type"] = signal_type

    workflow_id = f"unified-search-repair-workflow-{int(time.time())}"

    print(f"Executing Unified Search AI Repair Workflow with ID: {workflow_id}")
    print(f"Signal Type: {initial_signal['type']}")
    
    result = await client.execute_workflow(
        UnifiedSearchAiRepairWorkflow.run,
        initial_signal,
        id=workflow_id,
        task_queue="search-ai-task-queue",
    )

    print("\nWorkflow completed. Final Release Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
