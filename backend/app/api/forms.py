import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_user
from app.database import get_db
from app.models import ConnectedForm, User
from app.schemas import FormConnectRequest, MappingRequest, ProcessingToggle
from app.services.google_forms_service import GoogleFormsService, extract_form_id
from app.services.oauth_service import user_credentials

router = APIRouter(prefix="/forms", tags=["forms"])
logger = logging.getLogger(__name__)


def _owned_form(db: Session, user: User, form_id: str) -> ConnectedForm:
    form = db.scalar(select(ConnectedForm).where(
        ConnectedForm.id == form_id, ConnectedForm.user_id == user.id
    ))
    if form is None:
        raise HTTPException(status_code=404, detail="Connected form not found.")
    return form


def _serialize(form: ConnectedForm, total_responses: int = 0):
    return {
        "id": form.id,
        "google_form_id": form.google_form_id,
        "form_name": form.form_name,
        "field_mappings": form.field_mappings,
        "parent_drive_folder_id": form.parent_drive_folder_id,
        "automatic_processing_enabled": form.automatic_processing_enabled,
        "total_responses": total_responses,
    }


@router.post("/connect")
def connect_form(
    payload: FormConnectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    try:
        google_form_id = extract_form_id(payload.form_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        api = GoogleFormsService(user_credentials(user))
        form_info = api.get_form(google_form_id)
        responses = api.list_responses(google_form_id)
    except HttpError as exc:
        logger.info("Google Forms API rejected form access (%s)", exc.resp.status)
        raise HTTPException(
            status_code=403 if exc.resp.status in (403, 404) else 502,
            detail="Cannot access this form. Confirm that this Google account has editor access and Forms API is enabled.",
        ) from exc
    except Exception as exc:
        logger.exception("Unable to connect Google Form")
        raise HTTPException(status_code=502, detail="Unable to connect to Google Forms. Check Google credentials and try again.") from exc

    form = db.scalar(select(ConnectedForm).where(
        ConnectedForm.user_id == user.id, ConnectedForm.google_form_id == google_form_id
    ))
    if form is None:
        form = ConnectedForm(user_id=user.id, google_form_id=google_form_id, form_name=form_info.get("info", {}).get("title", "Google Form"))
        db.add(form)
    else:
        form.form_name = form_info.get("info", {}).get("title", "Google Form")
    db.commit()
    return {
        **_serialize(form, len(responses)),
        "questions": api.get_questions(google_form_id),
    }


@router.get("")
def list_forms(db: Session = Depends(get_db), user: User = Depends(require_user)):
    forms = db.scalars(select(ConnectedForm).where(ConnectedForm.user_id == user.id).order_by(ConnectedForm.created_at.desc())).all()
    return [_serialize(form) for form in forms]


@router.get("/{form_id}/questions")
def get_questions(
    form_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    form = _owned_form(db, user, form_id)
    try:
        api = GoogleFormsService(user_credentials(user))
        return {"questions": api.get_questions(form.google_form_id)}
    except HttpError as exc:
        raise HTTPException(status_code=403, detail="Google no longer permits access to this form.") from exc


@router.post("/{form_id}/mapping")
def save_mapping(
    form_id: str,
    payload: MappingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    form = _owned_form(db, user, form_id)
    allowed = {"candidate_name", "mobile_number", "date_of_birth", "birth_time", "birth_place", "height", "blood_group", "education", "address", "photograph", "receipt"}
    invalid = {
        key for key in payload.field_mappings
        if key not in allowed and not re.fullmatch(r"custom_[a-z0-9_]{1,60}", key)
    }
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unsupported mapping keys: {', '.join(sorted(invalid))}")
    if not payload.field_mappings.get("candidate_name") or not payload.field_mappings.get("photograph"):
        raise HTTPException(status_code=422, detail="Candidate name and photograph mappings are required.")
    form.field_mappings = payload.field_mappings
    form.parent_drive_folder_id = payload.parent_drive_folder_id or None
    db.commit()
    return _serialize(form)


@router.post("/{form_id}/start-processing")
def start_processing(
    form_id: str,
    payload: ProcessingToggle,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    form = _owned_form(db, user, form_id)
    if payload.enabled and (not form.field_mappings.get("candidate_name") or not form.field_mappings.get("photograph")):
        raise HTTPException(status_code=409, detail="Save candidate-name and photograph mappings before starting processing.")
    form.automatic_processing_enabled = payload.enabled
    db.commit()
    return {"form_id": form.id, "automatic_processing_enabled": form.automatic_processing_enabled}
