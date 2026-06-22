import asyncio
import json
import os
import re
from typing import Any

# Import agents
from Catalog.RootCause.google_agent import GoogleRootCauseAgent
from Catalog.Fix_Proposal.fix_agent import GoogleFixProposalAgent
from Catalog.Eval.eval_agent import GoogleEvalAgent
from Catalog.Release.release_agent import ReleaseAgent
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

async def process_signal(current_signal: dict):
    print("==================================================")
    print(f"🔍 PHASE 1: ROOT CAUSE ANALYSIS for Request ID: {current_signal.get('request_id', 'N/A')}")
    print("==================================================")
    
    # Initialize the Root Cause Agent
    rca_agent = GoogleRootCauseAgent()
    os.environ["MODEL_NAME"] = "gemini-2.5-flash"
    os.environ["GOOGLE_CLOUD_MODEL"] = "gemini-2.5-flash"
    
    # Enriche the signal with a description and raw_data_sample for the RCA agent
    problem_description = "General search event with no explicit error."
    raw_data_sample_for_rca = {}

    if current_signal.get("error"):
        problem_description = f"Search error detected: {current_signal['error']}"
        raw_data_sample_for_rca = {"error_details": current_signal["error"]}
    elif current_signal.get("response", {}).get("status_code") != 200:
        problem_description = (
            f"Search returned non-200 status code: "
            f"{current_signal['response']['status_code']} for query: "
            f"{current_signal['query']['text']}"
        )
        raw_data_sample_for_rca = {
            "query": current_signal["query"]["text"],
            "status_code": current_signal["response"]["status_code"],
            "response_details": current_signal["response"]
        }
    elif not current_signal.get("response", {}).get("results"):
        problem_description = (
            f"Search query '{current_signal['query']['text']}' "
            f"returned no results."
        )
        raw_data_sample_for_rca = {
            "query": current_signal["query"]["text"],
            "response_results": current_signal["response"].get("results", [])
        }
    else:
        # For successful searches, we can still provide a generic description
        # or focus on specific aspects if a problem is to be simulated later.
        problem_description = (
            f"Successful search for '{current_signal['query']['text']}' "
            f"with {current_signal['response'].get('result_count', 0)} results."
        )
        # Keep raw_data_sample minimal for successful cases to avoid token limits
        raw_data_sample_for_rca = {
            "query": current_signal["query"]["text"],
            "result_count": current_signal['response'].get('result_count', 0)
        }

    # Create a concise input for the RCA agent
    rca_input_signal = {
        "description": problem_description,
        "raw_data_sample": raw_data_sample_for_rca
    }
    
    print(f"\n🚀 Running Chief Investigator on incoming signal: {problem_description}...")
    rca_result = await rca_agent.run_agent(rca_input_signal)
    rca_result_dict = parse_agent_response(rca_result)

    if "error" in rca_result_dict:
        print(f"\n❌ RCA Agent Error: {rca_result_dict['error']}")
        print(f"Raw response that caused error: {rca_result_dict.get('raw_text', 'N/A')}")
        return

    print("\n✅ RCA Completed. Diagnosis:")
    print(json.dumps(rca_result_dict, indent=2))

    print("\n\n==================================================")
    print("🛠️  PHASE 2: FIX PROPOSAL & EXECUTION")
    print("==================================================")

    if rca_result_dict.get("overall_status") == "healthy":
        print("\n✅ System is healthy. No fixes required.")
        return

    print(f"\n🚀 Routing to Fix Proposal Agent to remediate '{rca_result_dict.get('root_cause', 'None')}'...")
    
    # Initialize the Fix Proposal Agent
    fix_agent = GoogleFixProposalAgent()
    
    # Pass the actual RCA result and original signal to the Fix Agent
    fix_input = {
        "root_cause": rca_result_dict.get("root_cause", ""),
        "summary": rca_result_dict.get("summary", ""),
        "affected_skus": rca_result_dict.get("affected_skus", [current_signal["catalog_entity"]["product_id"]] if "product_id" in current_signal.get("catalog_entity", {}) else []), # Dynamically extract product_id or default
        "original_signal": current_signal # Pass the full original signal for context
    }
    
    fix_result = await fix_agent.run_agent(fix_input)
    fix_result_dict = parse_agent_response(fix_result)

    if "error" in fix_result_dict:
        print(f"\n❌ Fix Proposal Agent Error: {fix_result_dict['error']}")
        print(f"Raw response that caused error: {fix_result_dict.get('raw_text', 'N/A')}")
        return

    print("\n✅ Remediation Completed. Final Report:")
    print(json.dumps(fix_result_dict, indent=2))

    print("\n\n==================================================")
    print("📊 PHASE 3: EVALUATION (SHADOW TESTING)")
    print("==================================================")
    
    eval_agent = GoogleEvalAgent()
    eval_input = {
        "diff_id": current_signal.get("diff_id", ""), # Use diff_id from original signal
        "context": fix_result_dict.get("summary", "") # Pass summary from fix as context
    }
    
    print("\n🚀 Running Evaluation Agent on shadow search traffic...")
    eval_result = await eval_agent.run_agent(eval_input)
    eval_result_dict = parse_agent_response(eval_result)

    if "error" in eval_result_dict:
        print(f"\n❌ Evaluation Agent Error: {eval_result_dict['error']}")
        print(f"Raw response that caused error: {eval_result_dict.get('raw_text', 'N/A')}")
        return

    print("\n✅ Evaluation Completed. Results:")
    print(json.dumps(eval_result_dict, indent=2))

    print("\n\n==================================================")
    print("🚀 PHASE 4: RELEASE MANAGEMENT")
    print("==================================================")
    
    release_agent = ReleaseAgent()
    
    # Map decision value to expected inputs for ReleaseAgent
    decision = eval_result_dict.get("decision", "").upper() if eval_result_dict.get("decision") else ""
    
    release_input = {
        "decision": decision, # Pass the actual decision
        "summary": eval_result_dict.get("summary", "") # Pass summary from eval as context
    }
    
    print(f"\n🚀 Routing decision '{decision}' to Release Agent...")
    release_result = await release_agent.run_agent(release_input)
    release_result_dict = parse_agent_response(release_result)

    if "error" in release_result_dict:
        print(f"\n❌ Release Agent Error: {release_result_dict['error']}")
        print(f"Raw response that caused error: {release_result_dict.get('raw_text', 'N/A')}")
        return
    
    print("\n✅ Release Orchestration Completed:")
    print(json.dumps(release_result_dict, indent=2))

    print("\n\n==================================================")
    print("🔍 PHASE 5: VERIFICATION (LANCEDB)")
    print("==================================================")
    
    from Catalog.RootCause.Tools.catalog_repository import CatalogRepository
    repo = CatalogRepository()
    mock_search_query_vector = [0.0, 0.0, 1.0, 0.5] 
    
    try:
        search_results = await repo.search_vectors(mock_search_query_vector, limit=3)
        print(f"\nTop Semantic Search Results from LanceDB:")
        for res in search_results:
            print(f" - SKU: {res['sku']}, Distance: {res['_distance']:.4f}, Vector: {res['vector']}")
    except Exception as e:
        print(f"Failed to query LanceDB: {e}")

async def main():
    script_dir = os.path.dirname(__file__)
    jsonl_file_path = os.path.join(script_dir, "search_events.jsonl")

    try:
        with open(jsonl_file_path, 'r') as f:
            for i, line in enumerate(f):
                print(f"\nProcessing signal {i+1}...")
                try:
                    current_signal = json.loads(line.strip())
                    await process_signal(current_signal)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from line {i+1}: {e}")
                print(f"\nFinished processing signal {i+1}.\n")
                print("="*80) # Separator for clarity
    except FileNotFoundError:
        print(f"Error: The file {jsonl_file_path} was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())