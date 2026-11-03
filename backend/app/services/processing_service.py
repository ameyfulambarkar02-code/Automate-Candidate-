import logging
import mimetypes
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from googleapiclient.errors import HttpError
import requests

from app.config import get_settings
from app.models import Candidate, ConnectedForm, User
from app.services.document_generator import generate_document
from app.services.google_drive_service import GoogleDriveService
from app.services.google_forms_service import GoogleFormsService
from app.services.image_processor import validate_photo
from app.services.oauth_service import user_credentials
from app.services.translator import translate_fields

logger = logging.getLogger(__name__)
FIELD_KEYS = {
    "candidate_name": "candidate_name",
    "mobile_number": "mobile_number",
    "date_of_birth": "dob",
    "birth_time": "time",
    "birth_place": "birth_place",
    "height": "height",
    "blood_group": "blood_group",
    "education": "education",
    "address": "address",
}


def _safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", value).strip(" .") or "Candidate"


def process_candidate(db: Session, candidate: Candidate, regenerate: bool = False) -> None:
    candidate.processing_status = "processing"
    candidate.error_message = None
    db.commit()
    try:
        form = db.get(ConnectedForm, candidate.connected_form_id)
        user = db.get(User, candidate.user_id)
        if not form or not user:
            raise RuntimeError("Candidate form or owning account no longer exists.")
        credentials = user_credentials(user)
        drive = GoogleDriveService(credentials)
        original = dict(candidate.original_data)
        answers_by_id = original.get("_answers_by_id", {})

        def mapped_answer(question_id: str | None):
            if not question_id:
                return None
            return answers_by_id.get(question_id, original.get(question_id))

        mappings = form.field_mappings
        photo_ids = mapped_answer(mappings.get("photograph")) or []
        receipt_ids = mapped_answer(mappings.get("receipt")) or []
        photo_ids = [photo_ids] if isinstance(photo_ids, str) else photo_ids
        receipt_ids = [receipt_ids] if isinstance(receipt_ids, str) else receipt_ids
        photo = None
        if photo_ids:
            photo, photo_meta = drive.download(photo_ids[0])
            validate_photo(photo, get_settings().max_upload_bytes)
        else:
            raise ValueError("Required candidate photograph is missing from this response.")

        if not candidate.candidate_folder_id:
            folder_name = f"{_safe_name(candidate.candidate_name)}_{candidate.registration_id}"
            candidate.candidate_folder_id = drive.create_candidate_folder(
                form.parent_drive_folder_id, folder_name
            )["id"]
            db.commit()
        folder_id = candidate.candidate_folder_id

        if not candidate.photograph_drive_id:
            candidate.photograph_drive_id = drive.upload(
                folder_id,
                photo_meta.get("name", f"{candidate.candidate_name}.jpg"),
                photo,
                photo_meta.get("mimeType", "image/jpeg"),
            )
            db.commit()
        if receipt_ids and not candidate.receipt_drive_id:
            receipt, receipt_meta = drive.download(receipt_ids[0])
            if len(receipt) > get_settings().max_upload_bytes:
                raise ValueError("Payment receipt exceeds the configured file-size limit.")
            receipt_mime = receipt_meta.get("mimeType") or mimetypes.guess_type(receipt_meta.get("name", ""))[0] or "application/octet-stream"
            candidate.receipt_drive_id = drive.upload(
                folder_id, receipt_meta.get("name", f"{candidate.candidate_name}_Receipt"), receipt, receipt_mime
            )
            db.commit()

        raw_fields: dict[str, str] = {}
        for role, question_title in mappings.items():
            if role in {"photograph", "receipt"} or not question_title:
                continue
            value = mapped_answer(question_title) or ""
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            raw_fields[FIELD_KEYS.get(role, role)] = str(value)
        if not candidate.translated_data:
            candidate.translated_data = {**candidate.translated_data, **translate_fields(raw_fields)}

        document_values = {**raw_fields, **candidate.translated_data}
        if regenerate or not candidate.document_drive_id:
            with tempfile.TemporaryDirectory() as temp_dir:
                safe_name = _safe_name(candidate.candidate_name)
                revision = f"_v{candidate.retry_count}" if regenerate and candidate.document_drive_id else ""
                filename = f"{safe_name}_{candidate.registration_id}{revision}.docx"
                path = Path(temp_dir) / filename
                generate_document(get_settings().template_path, path, document_values, photo)
                candidate.document_drive_id = drive.upload(
                    folder_id, filename, path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
        candidate.processing_status = "completed"
        candidate.completion_timestamp = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        candidate = db.get(Candidate, candidate.id)
        candidate.retry_count += 1
        retryable = isinstance(exc, requests.RequestException) or (
            isinstance(exc, HttpError) and (exc.resp.status == 429 or exc.resp.status >= 500)
        )
        candidate.processing_status = "pending" if retryable and candidate.retry_count <= 3 else "failed"
        candidate.error_message = str(exc)[:4000]
        db.commit()
        logger.exception("Candidate processing failed: %s", candidate.registration_id)


def poll_forms(db: Session) -> int:
    processed = 0
    pending = db.scalars(select(Candidate).where(Candidate.processing_status == "pending")).all()
    for candidate in pending:
        regenerate = candidate.regenerate_requested
        candidate.regenerate_requested = False
        db.commit()
        process_candidate(db, candidate, regenerate=regenerate)
        processed += 1
    forms = db.scalars(select(ConnectedForm).where(ConnectedForm.automatic_processing_enabled.is_(True))).all()
    for form in forms:
        try:
            user = db.get(User, form.user_id)
            forms_api = GoogleFormsService(user_credentials(user))
            responses = forms_api.list_responses(form.google_form_id)
            for response in responses:
                response_id = response.get("responseId")
                if not response_id:
                    continue
                exists = db.scalar(select(Candidate.id).where(
                    Candidate.connected_form_id == form.id, Candidate.response_id == response_id
                ))
                if exists:
                    continue
                values = forms_api.response_values(form.google_form_id, response)
                name_question = form.field_mappings.get("candidate_name")
                mobile_question = form.field_mappings.get("mobile_number")
                answers_by_id = values.get("_answers_by_id", {})
                name = str(answers_by_id.get(name_question, values.get(name_question, "Candidate"))) if name_question else "Candidate"
                candidate = Candidate(
                    user_id=form.user_id,
                    connected_form_id=form.id,
                    response_id=response_id,
                    registration_id=uuid4().hex[:12].upper(),
                    candidate_name=name,
                    mobile_number=str(answers_by_id.get(mobile_question, values.get(mobile_question, ""))) if mobile_question else "",
                    original_data=values,
                )
                db.add(candidate)
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    continue
                process_candidate(db, candidate)
                processed += 1
            form.last_processed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Polling failed for connected form %s", form.google_form_id)
    return processed


def retry_candidate(db: Session, candidate: Candidate, regenerate: bool = False) -> None:
    candidate.retry_count += 1
    candidate.processing_status = "pending"
    candidate.regenerate_requested = regenerate
    db.commit()
