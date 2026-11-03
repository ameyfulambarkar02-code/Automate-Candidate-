import logging

from app.database import SessionLocal
from app.services.processing_service import poll_forms

logger = logging.getLogger(__name__)


def process_pending_forms() -> int:
    db = SessionLocal()
    try:
        return poll_forms(db)
    finally:
        db.close()
