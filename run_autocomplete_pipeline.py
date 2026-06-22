import asyncio
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from Autocomplete.RootCause.main_agent import AutocompleteRootCauseAgent
from Autocomplete.Fix_Proposal.fix_agent import AutocompleteFixAgent
from Autocomplete.Eval.eval_agent import AutocompleteEvalAgent
from Autocomplete.Release.release_agent import AutocompleteReleaseAgent

# Sample signal: a user typed "shos" and got no results — typo tolerance issue
sample_signal = {
    "search_input": "shos",
    "issue": "Autocomplete returns no results for a common misspelling of 'shoes'",
    "drop_in_ctr": True,
    "affected_prefix": "shos"
}

async def main():
    print("=" * 55)
    print("🔍 AUTOCOMPLETE PIPELINE — PHASE 1: ROOT CAUSE ANALYSIS")
    print("=" * 55)

    rca_agent = AutocompleteRootCauseAgent()
    print("\n🚀 Running Autocomplete Root Cause Agent on incoming signal...")
    rca_result_dict = await rca_agent.run(sample_signal)

    print("\n✅ RCA Completed. Diagnosis:")
    print(json.dumps(rca_result_dict, indent=2))

    print("\n\n" + "=" * 55)
    print("🛠️  PHASE 2: FIX PROPOSAL & EXECUTION")
    print("=" * 55)

    fix_agent = AutocompleteFixAgent()
    print(f"\n🚀 Routing to Fix Agent to remediate '{rca_result_dict.get('root_cause')}'...")
    fix_result = await fix_agent.run_agent(rca_result_dict, sample_signal)

    print("\n✅ Fix Proposal Completed:")
    print(json.dumps(fix_result, indent=2))

    print("\n\n" + "=" * 55)
    print("📊 PHASE 3: EVALUATION")
    print("=" * 55)

    eval_agent = AutocompleteEvalAgent()
    print("\n🚀 Running Evaluation Agent to verify fix quality...")
    eval_input = {
        "fix_result": fix_result,
        "rca_result": rca_result_dict,
        "original_signal": sample_signal,
    }
    eval_result = await eval_agent.run(eval_input)

    print("\n✅ Evaluation Completed:")
    print(json.dumps(eval_result, indent=2))

    print("\n\n" + "=" * 55)
    print("🚀 PHASE 4: RELEASE")
    print("=" * 55)

    release_agent = AutocompleteReleaseAgent()
    print(f"\n🚀 Running Release Agent with decision: {eval_result.get('decision')}...")
    release_result = await release_agent.run(eval_result)

    print("\n✅ Release Completed:")
    print(json.dumps(release_result, indent=2))

    print("\n\n" + "=" * 55)
    print("🎉 AUTOCOMPLETE PIPELINE COMPLETE")
    print("=" * 55)
    print(f"\n📌 Summary:")
    print(f"  Root Cause  : {rca_result_dict.get('root_cause')}")
    print(f"  Fix Applied : {fix_result.get('actions_taken', [])}")
    print(f"  Eval Result : {eval_result.get('decision')}")
    print(f"  Release     : {release_result.get('action_taken', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())
