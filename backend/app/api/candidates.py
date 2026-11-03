import logging
from io import BytesIO
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_user
from app.database import get_db
from app.models import Candidate, User
from app.schemas import CandidateOut, TranslationUpdate
from app.services.google_drive_service import GoogleDriveService
from app.services.oauth_service import user_credentials
from app.services.processing_service import retry_candidate

router = APIRouter(prefix="/candidates", tags=["candidates"])
logger = logging.getLogger(__name__)


def _owned_candidate(db: Session, user: User, candidate_id: str) -> Candidate:
    candidate = db.scalar(select(Candidate).where(Candidate.id == candidate_id, Candidate.user_id == user.id))
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    query = select(Candidate).where(Candidate.user_id == user.id)
    if status:
        query = query.where(Candidate.processing_status == status)
    if search:
        query = query.where(Candidate.candidate_name.ilike(f"%{search}%") | Candidate.mobile_number.ilike(f"%{search}%"))
    candidates = db.scalars(query.order_by(Candidate.submission_timestamp.desc()).offset(offset).limit(limit)).all()
    return candidates


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    return _owned_candidate(db, user, candidate_id)


@router.get("/{candidate_id}/document")
def download_document(
    candidate_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    candidate = _owned_candidate(db, user, candidate_id)
    if not candidate.document_drive_id:
        raise HTTPException(status_code=404, detail="Generated document is not available.")
    try:
        content, _ = GoogleDriveService(user_credentials(user)).download(candidate.document_drive_id)
    except HttpError as exc:
        raise HTTPException(status_code=502, detail="Could not retrieve the document from Google Drive.") from exc
    safe_name = re.sub(r'[<>:"/\\|?*\r\n]+', "_", candidate.candidate_name).strip(" .") or "Candidate"
    filename = f"{safe_name}_{candidate.registration_id}.docx"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _preview_file(candidate: Candidate, field: str, user: User):
    form = candidate.connected_form
    title = form.field_mappings.get(field)
    if not title:
        raise HTTPException(status_code=404, detail="No form question is mapped for this file.")
    answers_by_id = candidate.original_data.get("_answers_by_id", {})
    file_ids = answers_by_id.get(title, candidate.original_data.get(title, []))
    file_id = file_ids[0] if isinstance(file_ids, list) and file_ids else file_ids if isinstance(file_ids, str) else None
    if not file_id:
        raise HTTPException(status_code=404, detail="No uploaded file is available.")
    try:
        content, metadata = GoogleDriveService(user_credentials(user)).download(file_id)
    except HttpError as exc:
        raise HTTPException(status_code=502, detail="Could not retrieve the file from Google Drive.") from exc
    return StreamingResponse(
        BytesIO(content),
        media_type=metadata.get("mimeType", "application/octet-stream"),
        headers={"Content-Disposition": "inline"},
    )


@router.get("/{candidate_id}/photograph")
def preview_photograph(
    candidate_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    return _preview_file(_owned_candidate(db, user, candidate_id), "photograph", user)


@router.get("/{candidate_id}/receipt")
def preview_receipt(
    candidate_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    return _preview_file(_owned_candidate(db, user, candidate_id), "receipt", user)


@router.get("/{candidate_id}/drive-folder")
def get_drive_folder(
    candidate_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    candidate = _owned_candidate(db, user, candidate_id)
    if not candidate.candidate_folder_id:
        raise HTTPException(status_code=404, detail="Candidate Drive folder is not available.")
    return {"url": f"https://drive.google.com/drive/folders/{candidate.candidate_folder_id}"}


@router.patch("/{candidate_id}/translation", response_model=CandidateOut)
def update_translation(
    candidate_id: str,
    payload: TranslationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    candidate = _owned_candidate(db, user, candidate_id)
    candidate.translated_data = payload.translated_data
    db.commit()
    return candidate


@router.post("/{candidate_id}/retry")
def retry_processing(
    candidate_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    candidate = _owned_candidate(db, user, candidate_id)
    if candidate.processing_status not in {"failed", "pending"}:
        raise HTTPException(status_code=409, detail="Only failed or pending candidates can be retried.")
    retry_candidate(db, candidate)
    return {"candidate_id": candidate.id, "processing_status": candidate.processing_status, "queued": True}


@router.post("/{candidate_id}/regenerate")
def regenerate_document(
    candidate_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    candidate = _owned_candidate(db, user, candidate_id)
    retry_candidate(db, candidate, regenerate=True)
    return {"candidate_id": candidate.id, "processing_status": candidate.processing_status, "queued": True}
