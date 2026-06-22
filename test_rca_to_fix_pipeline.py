import asyncio
import json
import sys
import os
from typing import Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from Catalog.RootCause.google_agent import GoogleRootCauseAgent
from Catalog.Fix_Proposal.fix_agent import GoogleFixProposalAgent

def parse_agent_response(context: Any) -> dict:
    """Parses the agent's response, handling various formats, including raw dicts and text with embedded JSON."""
    if isinstance(context, dict):
        return context

    if not context:
        print(f"\nERROR: Empty context received for parsing.\n")
        return {"error": "Empty context received for parsing"}

    json_start = context.find("{")
    json_end = context.rfind("}")

    if json_start == -1 or json_end == -1:
        print(f"\nERROR: No JSON found in context: {context}\n")
        return {"error": "No JSON found in context", "raw_text": context}

    json_string = context[json_start:json_end+1]

    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        print(f"\nWARNING: Initial JSON parsing failed: {e}. Attempting last resort cleanup.\n")
        # last resort cleanup
        cleaned = json_string.replace("\n", "").replace("\t", "")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as clean_e:
            print(f"\nERROR: Final JSON parsing failed after cleanup: {clean_e}\n")
            print(f"ERROR: Malformed JSON string: {cleaned}\n")
            return {"error": f"JSON parsing failed even after cleanup: {clean_e}", "cleaned_text": cleaned, "raw_text": context}

async def main():
    print("=" * 60)
    print("🚀 Testing RCA to Fix Proposal Pipeline...")
    print("=" * 60)

    # 1. Load Input
    with open("Catalog/search_events.jsonl", "r") as f:
        signal_data = [json.loads(line) for line in f]

    print(f"\n[Test Script] Loaded {len(signal_data)} events from search_events.jsonl\n")

    # 2. Run Root Cause Analysis
    print("\n" + "=" * 20 + " Running Root Cause Analysis " + "=" * 20)
    rca_agent = GoogleRootCauseAgent()
    rca_result = await rca_agent.run_agent(signal_data[0])
    rca_result_dict = parse_agent_response(rca_result)
    print(f"✅ RCA Complete. Output:")
    print(json.dumps(rca_result_dict, indent=2))

    # 3. Run Fix Proposal
    print("\n" + "=" * 20 + " Running Fix Proposal " + "=" * 20)
    fix_agent = GoogleFixProposalAgent()
    fix_result = await fix_agent.run_agent(rca_result_dict)
    fix_result_dict = parse_agent_response(fix_result)
    print(f"✅ Fix Proposal Complete. Output:")
    print(json.dumps(fix_result_dict, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
