import asyncio
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from Merchandising.RootCause.main_agent import MerchandisingRootCauseAgent
from Merchandising.Fix_Proposal.fix_agent import MerchandisingFixAgent
from Merchandising.Eval.eval_agent import MerchandisingEvalAgent
from Merchandising.Release.release_agent import MerchandisingReleaseAgent

# Sample signal: two rules fighting over the same query scope
sample_signal = {
    "query": "summer dresses",
    "issue": "Two merchandising rules are conflicting — rule_boost_brandA_summer boosts Brand A, but rule_bury_brandA_clearance buries it on the same category",
    "conflicting_rule_ids": ["rule_boost_brandA_summer", "rule_bury_brandA_clearance"],
    "affected_category": "Dresses > Summer"
}

async def main():
    print("=" * 60)
    print("🔍 MERCHANDISING PIPELINE — PHASE 1: ROOT CAUSE ANALYSIS")
    print("=" * 60)

    rca_agent = MerchandisingRootCauseAgent()
    print("\n🚀 Running Merchandising Root Cause Agent on incoming signal...")
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

    fix_agent = MerchandisingFixAgent()
    print(f"\n🚀 Routing to Fix Agent to remediate '{rca_result_dict.get('root_cause')}'...")
    fix_result = await fix_agent.run_agent(rca_result_dict)

    print("\n✅ Fix Proposal Completed:")
    print(json.dumps(fix_result, indent=2))

    print("\n\n" + "=" * 60)
    print("📊 PHASE 3: EVALUATION")
    print("=" * 60)

    eval_agent = MerchandisingEvalAgent()
    print("\n🚀 Running Evaluation Agent to verify fix quality...")
    eval_input = {
        "fix_result": fix_result,
        "rca_result": rca_result_dict,
        "original_signal": sample_signal,
    }
    eval_result = await eval_agent.run(eval_input)

    print("\n✅ Evaluation Completed:")
    print(json.dumps(eval_result, indent=2))

    print("\n\n" + "=" * 60)
    print("🚀 PHASE 4: RELEASE")
    print("=" * 60)

    release_agent = MerchandisingReleaseAgent()
    print(f"\n🚀 Running Release Agent with decision: {eval_result.get('decision')}...")
    release_result = await release_agent.run(eval_result)

    print("\n✅ Release Completed:")
    print(json.dumps(release_result, indent=2))

    print("\n\n" + "=" * 60)
    print("🎉 MERCHANDISING PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\n📌 Summary:")
    print(f"  Root Cause  : {rca_result_dict.get('root_cause')}")
    print(f"  Fix Applied : {fix_result.get('actions_taken', [])}")
    print(f"  Eval Result : {eval_result.get('decision')}")
    print(f"  Release     : {release_result.get('action_taken', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
