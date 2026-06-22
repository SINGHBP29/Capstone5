import json
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

import fast_rlm
from fast_rlm import RLMConfig

# Load environment variables (ensure OPENAI_API_KEY or relevant key is set)
load_dotenv()

# We must define tools as completely standalone functions because fast-rlm
# extracts their source code and runs them in a sandboxed Pyodide environment.
# They cannot rely on external file reads (like mock_catalog_db.db) or complex class structures.

def tool_catalog_coverage(signal_json: str) -> str:
    """
    Analyzes catalog coverage for a brand/category slice.
    Args:
        signal_json: A JSON string containing the input signal data.
    """
    import json
    # Mocking the logic that would normally read the DB
    return json.dumps({
        "status": "degraded",
        "coverage_score": 66.67,
        "missing_attributes": ["waterproof_flag", "terrain_type"],
        "root_cause_candidate": "catalog_coverage_gap",
        "evidence": ["128 products missing required attributes."]
    })

def tool_schema_validation(signal_json: str) -> str:
    """
    Validates catalog records against the expected schema.
    Args:
        signal_json: A JSON string containing the input signal data.
    """
    import json
    return json.dumps({
        "status": "healthy",
        "missing_fields": [],
        "type_mismatches": [],
        "root_cause_candidate": "none",
        "evidence": ["All products passed schema validation."]
    })

def tool_freshness_check(signal_json: str) -> str:
    """
    Determines whether catalog data is stale.
    Args:
        signal_json: A JSON string containing the input signal data.
    """
    import json
    return json.dumps({
        "status": "stale",
        "age_hours": 174.5,
        "is_stale": True,
        "root_cause_candidate": "stale_catalog_data",
        "evidence": ["Catalog age is 174.5 hours, exceeding the 24h threshold."]
    })

def tool_historical_intent(signal_json: str) -> str:
    """
    Analyzes historical search queries for a given catalog entity.
    Args:
        signal_json: A JSON string containing the input signal data.
    """
    import json
    return json.dumps({
        "status": "healthy",
        "top_keywords": ["trail", "shoes", "hiking"],
        "root_cause_candidate": "none"
    })

def tool_search_quality(signal_json: str) -> str:
    """
    Evaluates search quality based on product data and a search query.
    Args:
        signal_json: A JSON string containing the input signal data.
    """
    import json
    return json.dumps({
        "status": "degraded",
        "quality_score": 0.0,
        "root_cause_candidate": "low_search_relevance",
        "evidence": ["No relevant products found for query 'trail waterproof'."]
    })

def tool_capability_mapping(coverage_res: str, schema_res: str, freshness_res: str) -> str:
    """
    Maps catalog data issues to affected search capabilities based on previous tool results.
    Args:
        coverage_res: JSON string result from catalog_coverage tool.
        schema_res: JSON string result from schema_validation tool.
        freshness_res: JSON string result from freshness_check tool.
    """
    import json
    affected = []
    root_cause = "none"
    
    try:
        cov = json.loads(coverage_res)
        if cov.get("status") == "degraded":
            affected.extend(["semantic_search", "attribute_filtering"])
            root_cause = cov.get("root_cause_candidate", "catalog_coverage_gap")
            
        fresh = json.loads(freshness_res)
        if fresh.get("is_stale"):
            affected.extend(["recommendations_freshness", "search_results_freshness"])
            root_cause = fresh.get("root_cause_candidate", "stale_catalog_data")
            
    except Exception as e:
        return f"Error parsing inputs: {e}"

    return json.dumps({
        "status": "degraded" if affected else "healthy",
        "affected_capabilities": list(set(affected)),
        "root_cause_candidate": root_cause
    })


# Define the output schema we expect from fast-rlm
class RCAOutputSchema:
    overall_status: str
    root_cause: str
    affected_capabilities: list[str]
    summary: str


def main():
    # fast-rlm expects OpenAI-compatible endpoints.
    # If you are using Gemini, you need to set OPENAI_BASE_URL to a proxy
    # or ensure fast-rlm is configured to use the Gemini provider if it supports it natively.
    # By default, fast-rlm uses standard OpenAI models.
    
    # We must ensure an API key is set. fast-rlm typically looks for OPENAI_API_KEY.
    if "OPENAI_API_KEY" not in os.environ and "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" not in os.environ:
        print("WARNING: You may need to set an API key environment variable (e.g., OPENAI_API_KEY).")

    # Define the list of tools to pass to the agent
    tools_list = [
        tool_catalog_coverage,
        tool_schema_validation,
        tool_freshness_check,
        tool_historical_intent,
        tool_search_quality,
        tool_capability_mapping
    ]

    sample_signal = {
        "signal_id": "ops-catalog-relevance-delta-01",
        "signal_type": "catalog_gap",
        "catalog_entity": {
            "category": "Footwear",
            "brand": "Trailhead XT"
        },
        "signal": {
            "summary": "New seasonal trail shoes ship with missing waterproof and terrain attributes."
        }
    }

    # Configure fast-rlm. We use a generic OpenAI model name; if you have a specific setup, adjust this.
    config = RLMConfig(
        primary_agent="gpt-4o-mini", # or whatever model you have configured for fast-rlm
        max_depth=3,
        enable_tools=True,
        enable_structured_io=True
    )

    prompt = f"""
You are a Root Cause Analysis Agent. 
Analyze the following signal by calling the necessary diagnostic tools.

Input Signal:
{json.dumps(sample_signal, indent=2)}

Guidelines:
1. Run `tool_catalog_coverage` and `tool_schema_validation` first.
2. Run `tool_freshness_check`.
3. Pass the results of those three tools into `tool_capability_mapping` to determine the final impact.
4. Set the final variable `FINAL` to a dictionary matching the requested output schema containing your conclusions.
    """

    print("🚀 Running fast-rlm Agent...")
    try:
        # Run the agent
        result = fast_rlm.run(
            query=prompt,
            config=config,
            tools=tools_list,
            # output_schema=RCAOutputSchema # Output schema validation currently disabled due to potential pydantic mismatch in Pyodide
        )
        
        print("\n📦 FINAL OUTPUT\n")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error running fast-rlm: {e}")
        print("Ensure you have Deno installed and a valid API key set (usually OPENAI_API_KEY for fast-rlm).")

if __name__ == "__main__":
    main()
