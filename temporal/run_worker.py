import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# To ensure the parent directory is in the Python path for module resolution
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporal.workflows import UnifiedSearchAiRepairWorkflow
from temporal.activities import root_cause_activity, fix_proposal_activity, eval_activity
from temporal.activities import autocomplete_root_cause_activity, autocomplete_fix_proposal_activity, autocomplete_eval_activity
from temporal.activities import release_activity
from temporal.activities import semantic_root_cause_activity, semantic_fix_proposal_activity, semantic_eval_activity

# Add detailed logging
logging.basicConfig(level=logging.INFO)

async def main():
    try:
        # Connect to the local Temporal server.
        logging.info("Attempting to connect to Temporal server at localhost:7233...")
        client = await Client.connect("localhost:7233")
        logging.info("Successfully connected to Temporal server.")

        # Create a worker that polls for tasks on the 'search-ai-task-queue'
        worker = Worker(
            client,
            task_queue="search-ai-task-queue",
            workflows=[UnifiedSearchAiRepairWorkflow],
            activities=[
                root_cause_activity, fix_proposal_activity, eval_activity,
                autocomplete_root_cause_activity, autocomplete_fix_proposal_activity, autocomplete_eval_activity,
                semantic_root_cause_activity, semantic_fix_proposal_activity, semantic_eval_activity,
                release_activity
            ],
        )
        
        logging.info("Starting Temporal worker...")
        await worker.run()
        logging.info("Worker stopped.")

    except Exception as e:
        logging.error(f"Failed to start or run Temporal worker: {e}", exc_info=True)
        # Re-raise the exception to ensure the process exits with an error code
        raise

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nWorker shut down.")
    except Exception as e:
        print(f"Critical error in main: {e}")
    finally:
        loop.close()
