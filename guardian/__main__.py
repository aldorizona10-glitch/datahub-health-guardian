"""
DataHub Health Guardian — CLI Entry Point

Usage:
    python -m guardian              # Start API server (demo mode)
    python -m guardian --scan       # Run single scan
    python -m guardian --live       # Start with live DataHub
"""
import argparse
import logging
import sys

import uvicorn

from .config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("guardian")


def main():
    parser = argparse.ArgumentParser(description="DataHub Health Guardian Agent")
    parser.add_argument("--scan", action="store_true", help="Run a single health scan and exit")
    parser.add_argument("--live", action="store_true", help="Connect to live DataHub (default: demo mode)")
    parser.add_argument("--host", default="0.0.0.0", help="API server host")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    args = parser.parse_args()

    if args.scan:
        config = Config()
        issues = config.validate()
        if issues:
            logger.error(f"Config issues: {', '.join(issues)}")
            logger.info("Set DATAHUB_TOKEN and GOOGLE_API_KEY in .env")
            sys.exit(1)

        from .agent import HealthGuardianAgent
        agent = HealthGuardianAgent(config)
        try:
            result = agent.run_health_check()
            print(result["report"])
        finally:
            agent.close()
    else:
        logger.info("🏥 DataHub Health Guardian — Starting API server")
        logger.info(f"   Dashboard: http://localhost:{args.port}")
        logger.info(f"   API Docs:  http://localhost:{args.port}/docs")
        logger.info(f"   Mode:      {'live' if args.live else 'demo'}")
        uvicorn.run("guardian.server:app", host=args.host, port=args.port, reload=True)


if __name__ == "__main__":
    main()
