from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..fingerprint import (
    ComparisonResult,
    Verdict,
    VideoFingerprint,
    VideoReadError,
    compare_fingerprints,
    fingerprint_video,
)
from ..models import Fingerprint, Verification
from ..schemas import (
    ComparisonOut,
    FingerprintSummary,
    Stats,
    VerificationLogItem,
    VerificationOut,
)
from ..signing import verify_record
from ..uploads import stored_upload

router = APIRouter(tags=["verification"])

SEARCH_LIMIT = 500  # records scanned when no claim/fingerprint is specified

MESSAGES = {
    Verdict.AUTHENTIC_EXACT: "Bit-for-bit identical to the registered original.",
    Verdict.AUTHENTIC_REENCODED: (
        "Same footage as the registered original; the file was re-encoded or resized, "
        "but no content was changed."
    ),
    Verdict.TAMPERED: (
        "Footage matches a registered original, but parts were altered, removed or added. "
        "See the flagged segments."
    ),
    Verdict.NO_MATCH: "No registered video matches this footage.",
}


def _as_fingerprint(record: Fingerprint) -> VideoFingerprint:
    return VideoFingerprint(
        sha256=record.sha256,
        duration_s=record.duration_s,
        fps=record.fps,
        width=record.width,
        height=record.height,
        frame_count=record.frame_count,
        sample_interval_s=record.sample_interval_s,
        frame_hashes=list(record.frame_hashes),
    )


_RANK = {
    Verdict.AUTHENTIC_EXACT: 3,
    Verdict.AUTHENTIC_REENCODED: 2,
    Verdict.TAMPERED: 1,
    Verdict.NO_MATCH: 0,
}


@router.post("/verify", response_model=VerificationOut)
def verify_video(
    file: UploadFile = File(..., description="Video submitted with a claim"),
    fingerprint_id: str | None = Form(default=None),
    claim_reference: str | None = Form(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Check a submitted video against registered fingerprints.

    * ``fingerprint_id`` - compare with one specific record;
    * ``claim_reference`` - compare with every record of that claim;
    * neither - identify the footage among all registered records.
    """
    fingerprint_id = (fingerprint_id or "").strip() or None
    claim_reference = (claim_reference or "").strip() or None

    if fingerprint_id:
        record = db.get(Fingerprint, fingerprint_id)
        if not record:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Fingerprint not found")
        references = [record]
    elif claim_reference:
        references = list(
            db.scalars(select(Fingerprint).where(Fingerprint.claim_reference == claim_reference))
        )
        if not references:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No fingerprints for that claim")
    else:
        references = []

    with stored_upload(file, settings.max_upload_mb) as upload:
        if not references:
            exact = db.scalars(
                select(Fingerprint)
                .where(Fingerprint.sha256 == upload.sha256)
                .order_by(Fingerprint.created_at)
            ).first()
            references = (
                [exact]
                if exact
                else list(
                    db.scalars(
                        select(Fingerprint)
                        .order_by(Fingerprint.created_at.desc())
                        .limit(SEARCH_LIMIT)
                    )
                )
            )

        # Fingerprint the candidate once per sampling interval used by the references.
        candidates: dict[float, VideoFingerprint] = {}
        try:
            for interval in {r.sample_interval_s for r in references} or {
                settings.sample_interval_s
            }:
                candidates[interval] = fingerprint_video(upload.path, interval, upload.sha256)
        except VideoReadError as exc:
            raise HTTPException(422, str(exc)) from exc

    best: tuple[Fingerprint, ComparisonResult] | None = None
    for ref in references:
        result = compare_fingerprints(
            _as_fingerprint(ref),
            candidates[ref.sample_interval_s],
            hamming_threshold=settings.hamming_threshold,
            authentic_similarity=settings.authentic_similarity,
            related_similarity=settings.related_similarity,
            max_offset_samples=settings.max_offset_samples,
        )
        if best is None or (_RANK[result.verdict], result.similarity) > (
            _RANK[best[1].verdict],
            best[1].similarity,
        ):
            best = (ref, result)

    targeted = bool(fingerprint_id or claim_reference)
    if best is None or (best[1].verdict == Verdict.NO_MATCH and not targeted):
        # In "identify" mode a weak best guess is not a match, so nothing is linked.
        matched, comparison = None, None
        verdict, similarity = Verdict.NO_MATCH, 0.0
    else:
        # A targeted check always reports the comparison, even when it is NO_MATCH.
        matched, comparison = best
        verdict, similarity = comparison.verdict, comparison.similarity

    signature_valid = verify_record(matched, settings.signing_secret) if matched else None
    message = MESSAGES[verdict]
    if signature_valid is False:
        message += " WARNING: the stored record's signature is invalid - it was modified."

    log = Verification(
        fingerprint_id=matched.id if matched else None,
        uploaded_filename=upload.filename,
        uploaded_sha256=upload.sha256,
        verdict=verdict.value,
        similarity=similarity,
        record_signature_valid=signature_valid,
        details=comparison.to_dict() if comparison else {},
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return VerificationOut(
        id=log.id,
        verdict=verdict.value,
        similarity=similarity,
        uploaded_filename=upload.filename,
        uploaded_sha256=upload.sha256,
        matched_fingerprint=FingerprintSummary.model_validate(matched) if matched else None,
        record_signature_valid=signature_valid,
        comparison=ComparisonOut.model_validate(comparison.to_dict()) if comparison else None,
        message=message,
        created_at=log.created_at,
    )


@router.get("/verifications", response_model=list[VerificationLogItem])
def list_verifications(
    fingerprint_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Verification).order_by(Verification.created_at.desc()).limit(limit)
    if fingerprint_id:
        stmt = stmt.where(Verification.fingerprint_id == fingerprint_id)
    return [VerificationLogItem.model_validate(v) for v in db.scalars(stmt)]


@router.get("/stats", response_model=Stats)
def stats(db: Session = Depends(get_db)):
    verdicts = dict(
        db.execute(select(Verification.verdict, func.count()).group_by(Verification.verdict)).all()
    )
    return Stats(
        fingerprints=db.scalar(select(func.count()).select_from(Fingerprint)) or 0,
        verifications=db.scalar(select(func.count()).select_from(Verification)) or 0,
        verdicts={v.value: int(verdicts.get(v.value, 0)) for v in Verdict},
        total_video_seconds=round(db.scalar(select(func.sum(Fingerprint.duration_s))) or 0.0, 1),
    )
