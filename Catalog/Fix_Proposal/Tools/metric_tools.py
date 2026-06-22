import asyncio
import json
from typing import Dict, Any, List, Set
import logging

from google import genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class VocabularyDriftTool:
    """
    Hybrid tool that uses a deterministic algorithm (Jaccard Similarity) to calculate drift,
    and an LLM to semantically analyze the drifting terms.
    """
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_dotenv()
        self.client = genai.Client()
        self.model_name = model_name

    def _calculate_jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        Algorithmic Component: Calculates Jaccard Similarity between two sets of words.
        0.0 = completely different, 1.0 = identical.
        """
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union != 0 else 1.0

    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Fetch data (mocked for this example)
        historical_queries = ["trail running shoes", "waterproof boots", "hiking gear"]
        current_queries = ["trail running shoes", "kicks", "waterproof boots", "gorpcore"]

        logger.info("VocabularyDriftTool: Running algorithmic drift calculation...")

        # 2. Algorithmic Processing
        hist_vocab = set(" ".join(historical_queries).lower().split())
        curr_vocab = set(" ".join(current_queries).lower().split())

        similarity_score = self._calculate_jaccard_similarity(hist_vocab, curr_vocab)
        drift_percentage = (1.0 - similarity_score) * 100

        logger.info(f"Calculated Jaccard Similarity: {similarity_score:.2f} (Drift: {drift_percentage:.2f}%)")

        new_terms = list(curr_vocab - hist_vocab)

        # 3. Hybrid Logic Threshold
        llm_analysis = {}
        if drift_percentage > 20.0 and new_terms:
            logger.info(f"Significant drift detected. Calling LLM to analyze new terms: {new_terms}")
            
            # Using concatenation to avoid f-string escaping issues with JSON braces in the prompt
            prompt = (
                f"Search vocabulary has drifted by {drift_percentage:.1f}%. "
                f"New terms: {new_terms}. "
                "Analyze these terms in the context of outdoor retail. Identify if it is: "
                "1. A synonym for an existing product. 2. A new trend. 3. Noise. "
                "Return the analysis as a strict JSON dictionary: {\"term\": {\"type\": \"...\", \"reason\": \"...\"}}"
            )

            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                
                text = (response.text or "").strip()
                if text.startswith("```json"): text = text[7:]
                if text.startswith("```"): text = text[3:]
                if text.endswith("```"): text = text[:-3]
                llm_analysis = json.loads(text.strip())

            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
                llm_analysis = {"error": "Failed to parse LLM analysis."}
        else:
            llm_analysis = {"status": "Drift is within acceptable mathematical bounds."}

        return {
            "tool_name": "VocabularyDriftTool",
            "status": "degraded" if drift_percentage > 20.0 else "healthy",
            "metrics": {
                "jaccard_similarity": round(similarity_score, 3),
                "drift_percentage": round(drift_percentage, 1),
                "new_terms_identified": len(new_terms)
            },
            "llm_semantic_analysis": llm_analysis
        }

if __name__ == "__main__":
    async def main():
        tool = VocabularyDriftTool()
        result = await tool.run({})
        print(json.dumps(result, indent=2))

    asyncio.run(main())

