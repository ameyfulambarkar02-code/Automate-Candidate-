import argparse
import logging
import time

from app.config import get_settings
from app.workers.processor import process_pending_forms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_once() -> None:
    processed = process_pending_forms()
    logger.info("Worker cycle complete; processed %s new candidates", processed)


def main() -> None:
    interval = max(30, get_settings().polling_interval_seconds)
    logger.info("Starting candidate form worker; polling interval=%s seconds", interval)
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("Worker cycle failed")
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Poll connected Google Forms.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one polling cycle and exit instead of polling continuously.",
    )
    arguments = parser.parse_args()
    if arguments.once:
        run_once()
    else:
        main()
