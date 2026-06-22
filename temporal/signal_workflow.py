import asyncio
import sys
from temporalio.client import Client

async def main():
    """
    Connects to a running workflow and sends a signal to it.
    """
    if len(sys.argv) < 2:
        print("Usage: python3 -m temporal.signal_workflow <workflow-id>")
        return

    workflow_id = sys.argv[1]
    client = await Client.connect("localhost:7233")

    try:
        handle = client.get_workflow_handle(workflow_id)
        
        print(f"Signaling workflow '{workflow_id}' to approve deployment...")
        await handle.signal("approve_deployment")
        print("Signal sent successfully.")

    except Exception as e:
        print(f"Error signaling workflow: {e}")
        print(f"Please ensure a workflow with ID '{workflow_id}' is running and waiting for a signal.")


if __name__ == "__main__":
    asyncio.run(main())
