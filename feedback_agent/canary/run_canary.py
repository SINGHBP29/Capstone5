import argparse
import logging
from ..main import setup_logging
from .controller import CanaryReleaseController

def main():
    setup_logging()
    logger = logging.getLogger("feedback_agent.canary.run_canary")

    parser = argparse.ArgumentParser(description="OCS Canary Release Controller")
    parser.add_argument("--input", default="input.json", help="Path to input.json from FixPlanAgent")
    parser.add_argument("--output-dir", default="canary_output", help="Directory to write per-tier results and final canary result")
    args = parser.parse_args()

    logger.info("Launching Canary Release Controller...")
    controller = CanaryReleaseController(
        input_path=args.input,
        output_dir=args.output_dir
    )
    result = controller.run()
    logger.info(f"Canary release finished with status: {result['status']}")

if __name__ == "__main__":
    main()
