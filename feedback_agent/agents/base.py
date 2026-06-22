import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from ..db import OCSDatabase

class BaseAgent(ABC):
    """
    Abstract base class for all Feedback Loop sub-agents.
    """
    def __init__(self, db: OCSDatabase):
        self.db = db
        self.logger = logging.getLogger(f"feedback_agent.agents.{self.__class__.__name__}")

    @abstractmethod
    def run(self, input_data: Dict[str, Any], pipeline_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the sub-agent's primary logic.
        
        Args:
            input_data: The deserialized contents of input.json (upstream FixPlanAgent context).
            pipeline_state: Dict containing the running state accumulated from previous sub-agents.
            
        Returns:
            A dict containing updates/reports to merge into the pipeline state.
        """
        pass
