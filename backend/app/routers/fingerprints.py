import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..fingerprint import VideoReadError, fingerprint_video
from ..models import Fingerprint
from ..schemas import FingerprintDetail, FingerprintPage, FingerprintSummary
from ..signing import sign_record, verify_record
from ..uploads import stored_upload

router = APIRouter(prefix="/fingerprints", tags=["fingerprints"])


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def to_detail(record: Fingerprint, settings: Settings) -> FingerprintDetail:
    return FingerprintDetail.model_validate(
        {
            **FingerprintSummary.model_validate(record).model_dump(),
            "notes": record.notes,
            "frame_hashes": record.frame_hashes,
            "signature_valid": verify_record(record, settings.signing_secret),
        }
    )


@router.post("", response_model=FingerprintDetail, status_code=status.HTTP_201_CREATED)
def register_video(
    file: UploadFile = File(..., description="Original dashcam video"),
    claim_reference: str = Form(..., min_length=1, max_length=64),
    policy_number: str | None = Form(default=None, max_length=64),
    vehicle_plate: str | None = Form(default=None, max_length=32),
    notes: str | None = Form(default=None, max_length=2000),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Fingerprint an original video and store a signed record for a claim."""
    with stored_upload(file, settings.max_upload_mb) as upload:
        try:
            fp = fingerprint_video(upload.path, settings.sample_interval_s, sha256=upload.sha256)
        except VideoReadError as exc:
            raise HTTPException(422, str(exc)) from exc

    record = Fingerprint(
        id=str(uuid.uuid4()),
        claim_reference=claim_reference.strip(),
        policy_number=_clean(policy_number),
        vehicle_plate=_clean(vehicle_plate.upper() if vehicle_plate else None),
        notes=_clean(notes),
        original_filename=upload.filename,
        file_size_bytes=upload.size,
        sha256=fp.sha256,
        perceptual_digest=fp.perceptual_digest,
        duration_s=fp.duration_s,
        fps=fp.fps,
        width=fp.width,
        height=fp.height,
        frame_count=fp.frame_count,
        sample_interval_s=fp.sample_interval_s,
        frame_hashes=fp.frame_hashes,
    )
    record.signature = sign_record(record, settings.signing_secret)
    db.add(record)
    db.commit()
    db.refresh(record)
    return to_detail(record, settings)


@router.get("", response_model=FingerprintPage)
def list_fingerprints(
    q: str | None = Query(default=None, description="Search claim, policy, plate or filename"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Fingerprint)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Fingerprint.claim_reference).like(like),
                func.lower(Fingerprint.policy_number).like(like),
                func.lower(Fingerprint.vehicle_plate).like(like),
                func.lower(Fingerprint.original_filename).like(like),
                Fingerprint.sha256.like(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Fingerprint.created_at.desc()).limit(limit).offset(offset))
    return FingerprintPage(
        items=[FingerprintSummary.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{fingerprint_id}", response_model=FingerprintDetail)
def get_fingerprint(
    fingerprint_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    record = db.get(Fingerprint, fingerprint_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fingerprint not found")
    return to_detail(record, settings)


@router.delete("/{fingerprint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fingerprint(fingerprint_id: str, db: Session = Depends(get_db)):
    record = db.get(Fingerprint, fingerprint_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fingerprint not found")
    db.delete(record)
    db.commit()
