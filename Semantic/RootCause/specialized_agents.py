"""Specialized agents for semantic root cause analysis."""
from base_agent import BaseAgent

class VectorDBHealthAgent(BaseAgent):
    """Agent to check vector database health."""
    def __init__(self):
        super().__init__(model_name="gemini-1.5-flash-latest")
        # Add tool registrations here if needed

    def get_system_prompt(self) -> str:
        return "You are an agent that analyzes the health of the vector database."

    async def run(self, signal_data: dict):
        """Runs the vector database health analysis."""
        return await self.run_agent(signal_data)

class EmbeddingDriftAgent(BaseAgent):
    """Agent to analyze embedding drift."""
    def __init__(self):
        super().__init__(model_name="gemini-1.5-flash-latest")
        # Add tool registrations here if needed

    def get_system_prompt(self) -> str:
        return "You are an agent that analyzes semantic drift in vector embeddings."

    async def run(self, signal_data: dict):
        """Runs the embedding drift analysis."""
        return await self.run_agent(signal_data)

class SemanticCoverageAgent(BaseAgent):
    """Agent to check semantic index coverage."""
    def __init__(self):
        super().__init__(model_name="gemini-1.5-flash-latest")
        # Add tool registrations here if needed

    def get_system_prompt(self) -> str:
        return "You are an agent that analyzes gaps in semantic index coverage."

    async def run(self, signal_data: dict):
        """Runs the semantic coverage analysis."""
        return await self.run_agent(signal_data)

class SemanticSearchQualityAgent(BaseAgent):
    """Agent to evaluate semantic search quality."""
    def __init__(self):
        super().__init__(model_name="gemini-1.5-flash-latest")
        # Add tool registrations here if needed

    def get_system_prompt(self) -> str:
        return "You are an agent that analyzes the relevance and quality of semantic search results."

    async def run(self, signal_data: dict):
        """Runs the semantic search quality analysis."""
        return await self.run_agent(signal_data)
