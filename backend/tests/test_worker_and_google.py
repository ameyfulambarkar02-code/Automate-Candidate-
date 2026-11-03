from datetime import datetime, timezone
from unittest.mock import Mock

from fastapi import HTTPException
import requests
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Candidate, ConnectedForm, User
from app.services import google_drive_service, processing_service
from app.services.google_forms_service import GoogleFormsService
from app.api.candidates import _owned_candidate


def test_one_shot_worker_runs_single_poll_cycle(monkeypatch):
    from app.workers import scheduler

    poll = Mock(return_value=2)
    monkeypatch.setattr(scheduler, "process_pending_forms", poll)
    scheduler.run_once()
    poll.assert_called_once_with()


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_form_response_values_extracts_file_uploads():
    service = object.__new__(GoogleFormsService)
    service.get_questions = lambda _form_id: [
        {"item_id": "name_question", "title": "Candidate name"},
        {"item_id": "photo_question", "title": "Candidate photo"},
    ]
    response = {
        "answers": {
            "name_question": {"textAnswers": {"answers": [{"value": "Rahul Patil"}]}},
            "photo_question": {"fileUploadAnswers": {"answers": [{"fileId": "drive-photo-id"}]}},
        }
    }
    assert service.response_values("form-id", response) == {
        "Candidate name": "Rahul Patil",
        "Candidate photo": ["drive-photo-id"],
        "_answers_by_id": {
            "name_question": "Rahul Patil",
            "photo_question": ["drive-photo-id"],
        },
    }


def test_polling_is_idempotent_for_a_response(monkeypatch):
    db = make_session()
    user = User(google_id="google-1", email="owner@example.com", encrypted_refresh_token="encrypted")
    db.add(user)
    db.flush()
    form = ConnectedForm(
        user_id=user.id,
        google_form_id="form-id",
        form_name="Registration",
        field_mappings={"candidate_name": "name-question-id", "photograph": "photo-question-id"},
        automatic_processing_enabled=True,
    )
    db.add(form)
    db.commit()

    class FakeForms:
        def __init__(self, _credentials):
            pass

        def list_responses(self, _form_id):
            return [{"responseId": "response-123", "lastSubmittedTime": "2026-01-01T10:00:00Z"}]

        def response_values(self, _form_id, _response):
            return {
                "Name": "Rahul Patil",
                "Photo": ["file-id"],
                "_answers_by_id": {"name-question-id": "Rahul Patil", "photo-question-id": ["file-id"]},
            }

    def complete_without_google(_db, candidate, regenerate=False):
        candidate.processing_status = "completed"
        candidate.completion_timestamp = datetime.now(timezone.utc)
        _db.commit()

    monkeypatch.setattr(processing_service, "GoogleFormsService", FakeForms)
    monkeypatch.setattr(processing_service, "user_credentials", lambda _user: object())
    monkeypatch.setattr(processing_service, "process_candidate", complete_without_google)
    assert processing_service.poll_forms(db) == 1
    assert processing_service.poll_forms(db) == 0
    assert db.scalar(select(func.count(Candidate.id))) == 1
    db.close()


def test_retry_is_queued_without_blocking_for_google(monkeypatch):
    db = make_session()
    user = User(google_id="google-2", email="owner2@example.com", encrypted_refresh_token="encrypted")
    db.add(user)
    db.flush()
    form = ConnectedForm(user_id=user.id, google_form_id="f", form_name="F")
    db.add(form)
    db.flush()
    candidate = Candidate(
        user_id=user.id,
        connected_form_id=form.id,
        response_id="r",
        registration_id="REG-1",
        candidate_name="Test",
        original_data={},
        translated_data={},
        processing_status="failed",
    )
    db.add(candidate)
    db.commit()
    processing_service.retry_candidate(db, candidate)
    db.refresh(candidate)
    assert candidate.processing_status == "pending"
    assert candidate.retry_count == 1
    assert candidate.regenerate_requested is False
    db.close()


def test_drive_folder_creation_uses_requested_parent(monkeypatch):
    request = Mock()
    request.execute.return_value = {"id": "new-folder", "name": "Rahul_REG1"}
    list_request = Mock()
    list_request.execute.return_value = {"files": []}
    files = Mock()
    files.list.return_value = list_request
    files.create.return_value = request
    api = Mock()
    api.files.return_value = files
    monkeypatch.setattr(google_drive_service, "build", lambda *_args, **_kwargs: api)
    drive = google_drive_service.GoogleDriveService(credentials=object())
    folder = drive.create_candidate_folder("parent-folder", "Rahul_REG1")
    assert folder["id"] == "new-folder"
    assert files.create.call_args.kwargs["body"]["parents"] == ["parent-folder"]


def test_drive_upload_reuses_same_named_file_in_candidate_folder(monkeypatch):
    list_request = Mock()
    list_request.execute.return_value = {"files": [{"id": "already-uploaded"}]}
    files = Mock()
    files.list.return_value = list_request
    api = Mock()
    api.files.return_value = files
    monkeypatch.setattr(google_drive_service, "build", lambda *_args, **_kwargs: api)
    drive = google_drive_service.GoogleDriveService(credentials=object())
    assert drive.upload("candidate-folder", "candidate.docx", b"docx", "application/docx") == "already-uploaded"
    files.create.assert_not_called()


def test_processing_marks_missing_photo_as_failed(monkeypatch):
    db = make_session()
    user = User(google_id="google-3", email="owner3@example.com", encrypted_refresh_token="encrypted")
    db.add(user)
    db.flush()
    form = ConnectedForm(
        user_id=user.id,
        google_form_id="f",
        form_name="F",
        field_mappings={"photograph": "Photo"},
    )
    db.add(form)
    db.flush()
    candidate = Candidate(
        user_id=user.id,
        connected_form_id=form.id,
        response_id="r",
        registration_id="REG-2",
        candidate_name="No Photo",
        original_data={"Photo": []},
        translated_data={},
    )
    db.add(candidate)
    db.commit()
    monkeypatch.setattr(processing_service, "user_credentials", lambda _user: object())
    monkeypatch.setattr(processing_service, "GoogleDriveService", lambda _credentials: object())
    processing_service.process_candidate(db, candidate)
    db.refresh(candidate)
    assert candidate.processing_status == "failed"
    assert "photograph is missing" in candidate.error_message
    db.close()


def test_candidate_lookup_is_scoped_to_owning_user():
    db = make_session()
    owner = User(google_id="owner", email="owner@example.com", encrypted_refresh_token="token")
    other = User(google_id="other", email="other@example.com", encrypted_refresh_token="token")
    db.add_all([owner, other])
    db.flush()
    form = ConnectedForm(user_id=owner.id, google_form_id="f", form_name="F")
    db.add(form)
    db.flush()
    candidate = Candidate(
        user_id=owner.id,
        connected_form_id=form.id,
        response_id="r",
        registration_id="REG-3",
        candidate_name="Private candidate",
    )
    db.add(candidate)
    db.commit()
    try:
        _owned_candidate(db, other, candidate.id)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("A different user read another account's candidate")
    db.close()


def test_regeneration_keeps_manual_translation_and_creates_new_drive_file(monkeypatch, tmp_path):
    from io import BytesIO
    from types import SimpleNamespace
    from PIL import Image

    db = make_session()
    user = User(google_id="google-4", email="owner4@example.com", encrypted_refresh_token="encrypted")
    db.add(user)
    db.flush()
    form = ConnectedForm(
        user_id=user.id,
        google_form_id="f",
        form_name="F",
        field_mappings={"candidate_name": "Name", "photograph": "Photo"},
    )
    db.add(form)
    db.flush()
    candidate = Candidate(
        user_id=user.id,
        connected_form_id=form.id,
        response_id="r",
        registration_id="REG-4",
        candidate_name="Rahul",
        original_data={"Name": "Rahul", "Photo": ["source-photo"]},
        translated_data={"candidate_name": "दुरुस्त केलेले नाव"},
        candidate_folder_id="folder",
        photograph_drive_id="saved-photo",
        document_drive_id="previous-document",
        retry_count=1,
    )
    db.add(candidate)
    db.commit()

    photo_buffer = BytesIO()
    Image.new("RGB", (4, 8), "white").save(photo_buffer, format="PNG")

    class FakeDrive:
        def __init__(self, _credentials):
            self.upload_names = []

        def download(self, _file_id):
            return photo_buffer.getvalue(), {"name": "photo.png", "mimeType": "image/png", "size": "70"}

        def upload(self, _folder, name, _content, _mime):
            self.upload_names.append(name)
            return "new-document"

    drive = FakeDrive(None)
    monkeypatch.setattr(processing_service, "user_credentials", lambda _user: object())
    monkeypatch.setattr(processing_service, "GoogleDriveService", lambda _credentials: drive)
    monkeypatch.setattr(
        processing_service,
        "get_settings",
        lambda: SimpleNamespace(max_upload_bytes=1024, template_path=str(tmp_path / "template.docx")),
    )
    seen = {}

    def fake_generate(_template, output, values, _photo):
        seen.update(values)
        output.write_bytes(b"test-docx")
        return output

    monkeypatch.setattr(processing_service, "generate_document", fake_generate)
    processing_service.process_candidate(db, candidate, regenerate=True)
    db.refresh(candidate)
    assert candidate.processing_status == "completed"
    assert candidate.document_drive_id == "new-document"
    assert drive.upload_names == ["Rahul_REG-4_v1.docx"]
    assert seen["candidate_name"] == "दुरुस्त केलेले नाव"
    db.close()


def test_transient_google_failures_retry_and_eventually_fail(monkeypatch):
    db = make_session()
    user = User(google_id="google-5", email="owner5@example.com", encrypted_refresh_token="encrypted")
    db.add(user)
    db.flush()
    form = ConnectedForm(user_id=user.id, google_form_id="f", form_name="F")
    db.add(form)
    db.flush()
    candidate = Candidate(
        user_id=user.id,
        connected_form_id=form.id,
        response_id="r",
        registration_id="REG-5",
        candidate_name="Network error",
        original_data={},
    )
    db.add(candidate)
    db.commit()
    def fail_refresh(_user):
        raise requests.ConnectionError("temporary network outage")

    monkeypatch.setattr(processing_service, "user_credentials", fail_refresh)

    for attempt in range(1, 5):
        processing_service.process_candidate(db, candidate)
        db.refresh(candidate)
        expected = "pending" if attempt <= 3 else "failed"
        assert candidate.processing_status == expected
        assert candidate.retry_count == attempt
    db.close()
