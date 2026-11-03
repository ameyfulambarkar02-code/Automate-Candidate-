from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    profile_image: str | None
    model_config = ConfigDict(from_attributes=True)


class FormConnectRequest(BaseModel):
    form_url: str = Field(min_length=10, max_length=2000)


class MappingRequest(BaseModel):
    field_mappings: dict[str, str]
    parent_drive_folder_id: str | None = None


class ProcessingToggle(BaseModel):
    enabled: bool


class CandidateOut(BaseModel):
    id: str
    registration_id: str
    candidate_name: str
    mobile_number: str
    original_data: dict[str, Any]
    translated_data: dict[str, Any]
    photograph_drive_id: str | None
    receipt_drive_id: str | None
    document_drive_id: str | None
    candidate_folder_id: str | None
    processing_status: str
    error_message: str | None
    submission_timestamp: datetime
    completion_timestamp: datetime | None
    model_config = ConfigDict(from_attributes=True)


class TranslationUpdate(BaseModel):
    translated_data: dict[str, str]


class DashboardStats(BaseModel):
    total_candidates: int
    completed: int
    pending: int
    failed: int
