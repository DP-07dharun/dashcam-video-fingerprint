"""HMAC signatures over fingerprint records.

The signature binds the claim metadata to the fingerprint. If anyone edits a row directly in
the database (e.g. swaps the hashes of a claim), the signature no longer verifies and the
verification response reports ``record_signature_valid = false``.
"""

import hashlib
import hmac
import json
from typing import Any

SIGNED_FIELDS = (
    "id",
    "claim_reference",
    "policy_number",
    "vehicle_plate",
    "sha256",
    "perceptual_digest",
    "duration_s",
    "frame_count",
    "sample_interval_s",
    "frame_hashes",
)


def canonical_payload(record: Any) -> bytes:
    data = {name: getattr(record, name) for name in SIGNED_FIELDS}
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def sign_record(record: Any, secret: str) -> str:
    return hmac.new(secret.encode(), canonical_payload(record), hashlib.sha256).hexdigest()


def verify_record(record: Any, secret: str) -> bool:
    return hmac.compare_digest(sign_record(record, secret), record.signature or "")
