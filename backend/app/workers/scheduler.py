import logging
import time

from app.config import get_settings
from app.workers.processor import process_pending_forms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    interval = max(30, get_settings().polling_interval_seconds)
    logger.info("Starting candidate form worker; polling interval=%s seconds", interval)
    while True:
        try:
            processed = process_pending_forms()
            logger.info("Worker cycle complete; processed %s new candidates", processed)
        except Exception:
            logger.exception("Worker cycle failed")
        time.sleep(interval)


if __name__ == "__main__":
    main()
