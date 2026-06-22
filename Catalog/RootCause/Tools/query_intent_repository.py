from typing import List, Dict, Any

class QueryIntentRepository:
    async def get_query_history(self) -> List[Dict[str, Any]]:
        return [
            {"query": "trail waterproof", "search_count": 150, "ctr": 0.02},
            {"query": "hiking shoes", "search_count": 500, "ctr": 0.15}
        ]

    async def get_synonyms(self) -> Dict[str, List[str]]:
        return {"trail": ["hiking", "mountain"]}

    async def get_known_intents(self) -> List[str]:
        return ["hiking shoes", "waterproof boots"]
