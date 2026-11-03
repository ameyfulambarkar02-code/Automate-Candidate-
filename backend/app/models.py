from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    profile_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    forms: Mapped[list["ConnectedForm"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ConnectedForm(Base):
    __tablename__ = "connected_forms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    google_form_id: Mapped[str] = mapped_column(String(255))
    form_name: Mapped[str] = mapped_column(String(500))
    field_mappings: Mapped[dict] = mapped_column(JSON, default=dict)
    parent_drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    automatic_processing_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="forms")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="connected_form", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "google_form_id", name="uq_user_connected_form"),)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    connected_form_id: Mapped[str] = mapped_column(ForeignKey("connected_forms.id", ondelete="CASCADE"), index=True)
    response_id: Mapped[str] = mapped_column(String(255))
    registration_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    candidate_name: Mapped[str] = mapped_column(String(500), default="Candidate")
    mobile_number: Mapped[str] = mapped_column(String(100), default="")
    original_data: Mapped[dict] = mapped_column(JSON, default=dict)
    translated_data: Mapped[dict] = mapped_column(JSON, default=dict)
    photograph_drive_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_drive_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_drive_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    regenerate_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    submission_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    completion_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="candidates")
    connected_form: Mapped[ConnectedForm] = relationship(back_populates="candidates")

    __table_args__ = (
        UniqueConstraint("connected_form_id", "response_id", name="uq_form_response"),
        Index("ix_candidates_user_status", "user_id", "processing_status"),
    )
