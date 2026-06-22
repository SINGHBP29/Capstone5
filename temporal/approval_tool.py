import asyncio
import sys
from temporalio.client import Client

async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m temporal.approval_tool <WORKFLOW_ID> [approve/reject]")
        return

    workflow_id = sys.argv[1]
    decision = sys.argv[2].lower() if len(sys.argv) > 2 else "approve"
    approved = (decision == "approve")

    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(workflow_id)
    
    print(f"Sending approval signal to workflow {workflow_id}: {approved}")
    await handle.signal("approve_deployment", approved)
    print("Signal sent successfully.")

if __name__ == "__main__":
    asyncio.run(main())
