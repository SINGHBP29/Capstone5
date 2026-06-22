import asyncio
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from Semantic.RootCause.main_agent import RootCauseAgent
from Semantic.common_signals import sample_semantic_index_signal

async def main():
    print("=" * 60)
    print("🚀 Testing Semantic RootCause Agent...")
    print("=" * 60)

    # Instantiate the agent
    agent = RootCauseAgent()

    # Use the sample signal from the common signals file
    signal = sample_semantic_index_signal

    print(f"\n[Test Script] Calling agent with signal:\n{json.dumps(signal, indent=2)}\n")
    
    # Run the agent
    result_dict = await agent.run_to_completion(signal)
    
    print("\n\n" + "=" * 60)
    print("✅ Agent execution complete.")
    print("=" * 60)
    
    # Pretty-print the dictionary result from the agent
    print("\n[Test Script] Parsed Result from Agent:")
    print(json.dumps(result_dict, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
