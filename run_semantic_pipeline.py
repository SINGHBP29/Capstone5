import asyncio
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from Semantic.RootCause.main_agent import MainSemanticAgent
from Semantic.Fix_Proposal.fix_agent import SemanticFixAgent
from Semantic.Eval.eval_agent import SemanticEvalAgent
from Semantic.Release.release_agent import SemanticReleaseAgent

# Sample signal: low search relevance for outdoor/trail query due to zero/stale embeddings
sample_signal = {
    "search_query": "waterproof trail shoe",
    "issue": "Semantic search quality is degraded, zero results or low relevance score for Trailhead items.",
    "affected_skus": ["TH-XT-002", "TH-XT-004"],
    "index_coverage_gap": True
}

async def main():
    print("=" * 60)
    print("🔍 SEMANTIC PIPELINE — PHASE 1: ROOT CAUSE ANALYSIS")
    print("=" * 60)

    rca_agent = MainSemanticAgent()
    print("\n🚀 Running Main Semantic RCA Agent on incoming signal...")
    rca_result = await rca_agent.run(sample_signal)

    rca_result_text = rca_result.get("response_text", "{}")
    if rca_result_text.startswith("```json"):
        rca_result_text = rca_result_text[7:]
    if rca_result_text.endswith("```"):
        rca_result_text = rca_result_text[:-3]
    rca_result_dict = json.loads(rca_result_text)

    print("\n✅ RCA Completed. Diagnosis:")
    print(json.dumps(rca_result_dict, indent=2))

    print("\n\n" + "=" * 60)
    print("🛠️  PHASE 2: FIX PROPOSAL & EXECUTION")
    print("=" * 60)

    fix_agent = SemanticFixAgent()
    print(f"\n🚀 Routing to Fix Agent to remediate '{rca_result_dict.get('root_cause')}'...")
    fix_result = await fix_agent.run_agent(rca_result_dict)

    print("\n✅ Fix Proposal Completed:")
    print(json.dumps(fix_result, indent=2))

    print("\n\n" + "=" * 60)
    print("📊 PHASE 3: EVALUATION (SHADOW TESTING)")
    print("=" * 60)

    eval_agent = SemanticEvalAgent()
    # Pass fix execution results / diff ID context for shadow test evaluation
    eval_input = {
        "diff_id": "c28b-4b1e-b3f9-7153d3e690f3",
        "context": "Waterproof trail shoe embeddings updated and refreshed.",
        "actions_taken": fix_result.get("actions_taken", [])
    }
    
    print("\n🚀 Running Evaluation Agent to verify fix quality...")
    eval_result = await eval_agent.run(eval_input)

    print("\n✅ Evaluation Completed:")
    print(json.dumps(eval_result, indent=2))

    print("\n\n" + "=" * 60)
    print("🚀 PHASE 4: RELEASE")
    print("=" * 60)

    release_agent = SemanticReleaseAgent()
    print(f"\n🚀 Running Release Agent with decision: {eval_result.get('decision')}...")
    release_result = await release_agent.run(eval_result)

    print("\n✅ Release Completed:")
    print(json.dumps(release_result, indent=2))

    print("\n\n" + "=" * 60)
    print("🎉 SEMANTIC PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\n📌 Summary:")
    print(f"  Root Cause  : {rca_result_dict.get('root_cause')}")
    print(f"  Fix Applied : {fix_result.get('actions_taken', [])}")
    print(f"  Eval Result : {eval_result.get('decision')}")
    print(f"  Release     : {release_result.get('action_taken', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
