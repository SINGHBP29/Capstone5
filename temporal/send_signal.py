import asyncio
import argparse
from temporalio.client import Client

async def main():
    parser = argparse.ArgumentParser(description="Send a signal to the SearchOpsWorkflow.")
    parser.add_argument("decision", choices=["approve", "reject"], help="The decision to send to the workflow.")
    args = parser.parse_args()

    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle("search-ops-workflow")
    await handle.signal("approve_or_reject", args.decision)
    print(f"Signal '{args.decision}' sent to workflow 'search-ops-workflow'.")

if __name__ == "__main__":
    asyncio.run(main())