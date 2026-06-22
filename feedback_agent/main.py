import os
import json
import logging
import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import MOCK_MODE
from .db import OCSDatabase
from .agents.fix_verification import FixVerificationAgent
from .agents.metric_comparison import MetricComparisonAgent
from .agents.canary_evaluation import CanaryEvaluationAgent
from .agents.threshold_update import ThresholdUpdateAgent
from .agents.audit_trail import AuditTrailAgent
from .models import FeedbackResult, VerificationReport, MetricsReport, DecisionReport, ThresholdUpdatesReport, AuditRecord # Import your models

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('feedback_agent.log', mode='w')
    ]
)
logger = logging.getLogger("feedback_agent.orchestrator")

app = FastAPI()

class FeedbackInput(BaseModel):
    # Define the structure of your input payload here
    # This should match what your agents expect
    query: str
    result: Dict[str, Any] = {}
    signal: Dict[str, Any] = {}
    # Add other fields as necessary based on your agent's input requirements

async def run_feedback_pipeline_internal(input_data: Dict[str, Any]) -> FeedbackResult:
    logger.info("Initializing OCS Feedback Agent Pipeline...")
    logger.info(f"Execution Mode: {'MOCK/SIMULATED' if MOCK_MODE else 'LIVE'}")

    # Initialize Database connection
    db = OCSDatabase()

    # Instantiate Sub-Agents
    agents = [
        ("verification", FixVerificationAgent(db)),
        ("metrics", MetricComparisonAgent(db)),
        ("decision", CanaryEvaluationAgent(db)),
        ("threshold_updates", ThresholdUpdateAgent(db)),
        ("audit_record", AuditTrailAgent(db))
    ]

    pipeline_state: Dict[str, Any] = {}

    # Sequentially run sub-agents
    for name, agent in agents:
        logger.info(f"Executing sub-agent: {agent.__class__.__name__}")
        try:
            agent_output = await agent.run(input_data, pipeline_state) # Assuming agent.run can be async
            pipeline_state.update(agent_output)
        except Exception as e:
            logger.exception(f"Error during execution of sub-agent {agent.__class__.__name__}:")
            pipeline_state[name] = {"error": str(e), "passed": False}

    # Build final feedback_result matching the target schema
    feedback_result = FeedbackResult(
        query=input_data.get("query") or input_data.get("result", {}).get("query", ""),
        timestamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        verification=pipeline_state.get("verification"),
        metrics=pipeline_state.get("metrics"),
        decision=pipeline_state.get("decision"),
        threshold_updates=pipeline_state.get("thresholdUpdates"),
        audit_record=pipeline_state.get("auditRecord")
    )

    # Determine overall status
    if feedback_result.verification and feedback_result.verification.get("allPassed", False):
        feedback_result.status = "ok"
    else:
        feedback_result.status = "degraded"

    # Close Database connection
    db.close()

    logger.info("Feedback pipeline completed successfully.")
    return feedback_result

@app.post("/run_feedback", response_model=FeedbackResult)
async def run_feedback(input_data: FeedbackInput):
    try:
        # Convert pydantic model to dict for internal pipeline
        result = await run_feedback_pipeline_internal(input_data.dict())
        return result
    except Exception as e:
        logger.exception("Error running feedback pipeline via API:")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "agent": "FeedbackAgent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
