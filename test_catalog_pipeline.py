import asyncio
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from Catalog.RootCause.google_agent import GoogleRootCauseAgent
from Catalog.Fix_Proposal.fix_agent import GoogleFixProposalAgent
from Catalog.Eval.eval_agent import CatalogEvalAgent

async def main():
    print("=" * 60)
    print("🚀 Testing Full Catalog Pipeline...")
    print("=" * 60)

    # 1. Load Input
    with open("Catalog/search_events.jsonl", "r") as f:
        signal_data = [json.loads(line) for line in f]

    print(f"\n[Test Script] Loaded {len(signal_data)} events from search_events.jsonl\n")

    # 2. Run Root Cause Analysis
    print("\n" + "=" * 20 + " Running Root Cause Analysis " + "=" * 20)
    rca_agent = CatalogRootCauseAgent()
    rca_result = await rca_agent.run(signal_data)
    with open("rca_output.json", "w") as f:
        json.dump(rca_result, f, indent=2)
    print(f"✅ RCA Complete. Output saved to rca_output.json")

    # 3. Run Fix Proposal
    print("\n" + "=" * 20 + " Running Fix Proposal " + "=" * 20)
    fix_agent = GoogleFixProposalAgent()
    fix_result = await fix_agent.run_agent(rca_result)
    with open("fix_output.json", "w") as f:
        json.dump(fix_result, f, indent=2)
    print(f"✅ Fix Proposal Complete. Output saved to fix_output.json")

    # 4. Run Evaluation
    print("\n" + "=" * 20 + " Running Evaluation " + "=" * 20)
    eval_agent = CatalogEvalAgent()
    eval_result = await eval_agent.run_agent(fix_result)
    with open("eval_output.json", "w") as f:
        json.dump(eval_result, f, indent=2)
    print(f"✅ Evaluation Complete. Output saved to eval_output.json")


if __name__ == "__main__":
    asyncio.run(main())
