import asyncio
import json
from typing import Dict, Any, List
import logging
import sys
import os

from google import genai
from google.genai import types

# Ensure we can import from the Catalog root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from Catalog.RootCause.Tools.catalog_repository import CatalogRepository

logger = logging.getLogger(__name__)

class SemanticIntentMappingTool:
    """
    Analyzes queries with zero/low lexical matches but high conceptual relevance
    (e.g., "pandemic mask" vs "n95 surgical mask") and generates a semantic 
    query expansion mapping for the search engine.
    """
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.client = genai.Client()
        self.model_name = model_name
        self.repository = CatalogRepository()

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Extract the query from the input arguments. 
        # If not provided, fail gracefully rather than hardcoding.
        user_query = args.get("query")
        if not user_query:
             return {
                "tool_name": "SemanticIntentMappingTool",
                "status": "failed",
                "error": "No 'query' provided in arguments."
            }
        
        # In a real scenario, you'd likely fetch products based on vector similarity 
        # to the user_query to find conceptually related items that missed lexical matching.
        # For this demonstration, we'll fetch products for a relevant category.
        # In a fully integrated system, the previous tool (like a zero-results monitor) 
        # would provide context on what category the user was likely searching in.
        
        # We'll use a mocked category fetch for demonstration, but it relies on the repo.
        category = args.get("category", "Apparel") # Defaulting to Apparel for our mock DB
        brand = args.get("brand", "Alpine Line")
        
        products = await self.repository.get_products(brand=brand, category=category)
        
        if not products:
             catalog_samples = ["No products found in DB for context."]
        else:
             # Extract titles/descriptions from the actual DB records
             catalog_samples = [f"SKU: {p.sku}, Category: {p.category}" for p in products[:5]]

        logger.info(f"SemanticIntentTool: Analyzing conceptual gap for query '{user_query}'...")

        prompt = f"""
        A user searched for "{user_query}" on an e-commerce site. 
        Lexical search engines fail to return good results because the exact words don't match our catalog.

        Our catalog contains these relevant items:
        {json.dumps(catalog_samples, indent=2)}

        Analyze the semantic gap.
        1. Explain WHY the lexical match fails (the conceptual link).
        2. Generate a "Query Expansion Rule" that we can inject into our search engine (like Solr/Elasticsearch or an LLM pre-processor).
        This rule should map the user's intent to the actual terminology used in our catalog.

        Return ONLY a JSON dictionary with the following schema:
        {{
            "conceptual_link": "string explaining the semantic relationship",
            "expansion_terms": ["list of catalog-specific terms to inject into the query behind the scenes"],
            "suggested_action": "string describing how ops should apply this"
        }}
        """

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            
            text = (response.text or "").strip()
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            mapping_result = json.loads(text.strip())

        except Exception as e:
            logger.error(f"Semantic analysis failed: {e}")
            mapping_result = {"error": "Failed to parse semantic mapping."}

        return {
            "tool_name": "SemanticIntentMappingTool",
            "status": "success",
            "original_query": user_query,
            "semantic_mapping": mapping_result
        }

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    if "GOOGLE_API_KEY" in os.environ:
         os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

    async def main():
        tool = SemanticIntentMappingTool()
        # Simulating an agent passing arguments derived from previous steps or signals
        test_args = {
            "query": "heavy winter jacket",
            "category": "Apparel",
            "brand": "Alpine Line"
        }
        result = await tool.run(test_args)
        print(json.dumps(result, indent=2))

    asyncio.run(main())
