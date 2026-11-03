from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_user
from app.database import get_db
from app.models import Candidate, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), user: User = Depends(require_user)):
    counts = dict(db.execute(
        select(Candidate.processing_status, func.count(Candidate.id))
        .where(Candidate.user_id == user.id)
        .group_by(Candidate.processing_status)
    ).all())
    return {
        "total_candidates": sum(counts.values()),
        "completed": counts.get("completed", 0),
        "pending": counts.get("pending", 0) + counts.get("processing", 0),
        "failed": counts.get("failed", 0),
    }
