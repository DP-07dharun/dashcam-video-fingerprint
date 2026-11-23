import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# JSONB on PostgreSQL (Supabase), plain JSON elsewhere (SQLite for local dev/tests).
JsonType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Fingerprint(Base):
    """A registered dashcam video. The video itself is never stored - only its fingerprint."""

    __tablename__ = "fingerprints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    claim_reference: Mapped[str] = mapped_column(String(64), index=True)
    policy_number: Mapped[str | None] = mapped_column(String(64))
    vehicle_plate: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)

    original_filename: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    perceptual_digest: Mapped[str] = mapped_column(String(64), index=True)

    duration_s: Mapped[float] = mapped_column(Float)
    fps: Mapped[float] = mapped_column(Float)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    frame_count: Mapped[int] = mapped_column(Integer)
    sample_interval_s: Mapped[float] = mapped_column(Float)
    frame_hashes: Mapped[list[str]] = mapped_column(JsonType)

    signature: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    verifications: Mapped[list["Verification"]] = relationship(back_populates="fingerprint")


class Verification(Base):
    """Audit log of every verification request."""

    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    fingerprint_id: Mapped[str | None] = mapped_column(
        ForeignKey("fingerprints.id", ondelete="SET NULL"), index=True
    )
    uploaded_filename: Mapped[str] = mapped_column(String(255))
    uploaded_sha256: Mapped[str] = mapped_column(String(64))
    verdict: Mapped[str] = mapped_column(String(32), index=True)
    similarity: Mapped[float] = mapped_column(Float)
    record_signature_valid: Mapped[bool | None] = mapped_column()
    details: Mapped[dict] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    fingerprint: Mapped[Fingerprint | None] = relationship(back_populates="verifications")
