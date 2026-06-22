import asyncio
import json
from base4_agent import BaseAgent

async def main():
    print("=" * 60)
    print("🚀 Testing Fast-RLM integration in new ADK-based BaseAgent...")
    print("=" * 60)

    # Instantiate the agent with deep RCA enabled
    agent = BaseAgent(enable_deep_rca=True)

    # A complex signal to trigger the deep investigation
    signal = {
        "signal_id": "direct-fast-rlm-test",
        "description": "This is a direct test of the fast-rlm deep investigation tool using the new ADK-based BaseAgent."
    }

    print(f"\n[Test Script] Calling _run_deep_rca_investigation_tool with signal:\n{json.dumps(signal, indent=2)}\n")
    
    # Directly call the internal method that uses fast-rlm
    result_dict = await agent._run_deep_rca_investigation_tool(signal)
    
    print("\n\n" + "=" * 60)
    print("✅ Fast-RLM execution complete.")
    print("=" * 60)
    
    # Pretty-print the dictionary result from the tool
    print("\n[Test Script] Parsed Result from Fast-RLM:")
    print(json.dumps(result_dict, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
