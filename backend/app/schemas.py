from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FingerprintSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_reference: str
    policy_number: str | None
    vehicle_plate: str | None
    original_filename: str
    file_size_bytes: int
    sha256: str
    perceptual_digest: str
    duration_s: float
    fps: float
    width: int
    height: int
    frame_count: int
    sample_interval_s: float
    signature: str
    created_at: datetime


class FingerprintDetail(FingerprintSummary):
    notes: str | None
    frame_hashes: list[str]
    signature_valid: bool


class FingerprintPage(BaseModel):
    items: list[FingerprintSummary]
    total: int
    limit: int
    offset: int


class SegmentOut(BaseModel):
    start_s: float
    end_s: float
    kind: str


class ComparisonOut(BaseModel):
    verdict: str
    similarity: float
    exact_match: bool
    offset_s: float
    matched_samples: int
    reference_samples: int
    candidate_samples: int
    mean_distance: float | None
    duration_delta_s: float
    segments: list[SegmentOut]
    timeline: list[int | None]


class VerificationOut(BaseModel):
    id: str
    verdict: str
    similarity: float
    uploaded_filename: str
    uploaded_sha256: str
    matched_fingerprint: FingerprintSummary | None
    record_signature_valid: bool | None
    comparison: ComparisonOut | None
    message: str
    created_at: datetime


class VerificationLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fingerprint_id: str | None
    uploaded_filename: str
    verdict: str
    similarity: float
    record_signature_valid: bool | None
    created_at: datetime


class Stats(BaseModel):
    fingerprints: int
    verifications: int
    verdicts: dict[str, int]
    total_video_seconds: float
