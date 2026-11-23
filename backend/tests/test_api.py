from pathlib import Path

import pytest

from app.config import get_settings
from app.db import SessionLocal
from app.models import Fingerprint


def _upload(path: Path, mime: str = "video/mp4"):
    return {"file": (path.name, path.read_bytes(), mime)}


@pytest.fixture(scope="module")
def registered(client, videos):
    resp = client.post(
        "/api/fingerprints",
        files=_upload(videos["original"]),
        data={"claim_reference": "CLM-2026-0001", "vehicle_plate": "ab-123-cd"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_register_returns_signed_fingerprint(registered):
    assert registered["claim_reference"] == "CLM-2026-0001"
    assert registered["vehicle_plate"] == "AB-123-CD"
    assert registered["signature_valid"] is True
    assert len(registered["frame_hashes"]) == 16
    assert len(registered["signature"]) == 64


def test_list_and_search(client, registered):
    page = client.get("/api/fingerprints", params={"q": "clm-2026"}).json()
    assert page["total"] >= 1
    assert any(item["id"] == registered["id"] for item in page["items"])
    assert client.get("/api/fingerprints", params={"q": "nothing-like-this"}).json()["total"] == 0


def test_get_detail_and_404(client, registered):
    assert (
        client.get(f"/api/fingerprints/{registered['id']}").json()["sha256"] == registered["sha256"]
    )
    assert client.get("/api/fingerprints/does-not-exist").status_code == 404


@pytest.mark.parametrize(
    ("name", "verdict"),
    [
        ("original", "AUTHENTIC_EXACT"),
        ("reencoded", "AUTHENTIC_REENCODED"),
        ("tampered", "TAMPERED"),
    ],
)
def test_verify_against_fingerprint(client, videos, registered, name, verdict):
    mime = "video/x-msvideo" if name == "reencoded" else "video/mp4"
    resp = client.post(
        "/api/verify",
        files=_upload(videos[name], mime),
        data={"fingerprint_id": registered["id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verdict"] == verdict
    assert body["matched_fingerprint"]["id"] == registered["id"]
    assert body["record_signature_valid"] is True


def test_verify_by_claim_reference(client, videos, registered):
    resp = client.post(
        "/api/verify",
        files=_upload(videos["tampered"]),
        data={"claim_reference": "CLM-2026-0001"},
    )
    body = resp.json()
    assert body["verdict"] == "TAMPERED"
    assert any(s["kind"] == "altered" for s in body["comparison"]["segments"])


def test_identify_without_reference(client, videos, registered):
    found = client.post("/api/verify", files=_upload(videos["reencoded"], "video/x-msvideo"))
    assert found.json()["verdict"] == "AUTHENTIC_REENCODED"
    assert found.json()["matched_fingerprint"]["id"] == registered["id"]

    unknown = client.post("/api/verify", files=_upload(videos["unrelated"])).json()
    assert unknown["verdict"] == "NO_MATCH"
    assert unknown["matched_fingerprint"] is None


def test_database_tampering_is_detected(client, videos, registered):
    with SessionLocal() as db:
        row = db.get(Fingerprint, registered["id"])
        original_claim = row.claim_reference
        row.claim_reference = "CLM-FORGED"
        db.commit()
    try:
        detail = client.get(f"/api/fingerprints/{registered['id']}").json()
        assert detail["signature_valid"] is False
        body = client.post(
            "/api/verify",
            files=_upload(videos["original"]),
            data={"fingerprint_id": registered["id"]},
        ).json()
        assert body["record_signature_valid"] is False
        assert "signature is invalid" in body["message"]
    finally:
        with SessionLocal() as db:
            db.get(Fingerprint, registered["id"]).claim_reference = original_claim
            db.commit()


def test_rejects_unsupported_and_invalid_files(client, tmp_path):
    txt = tmp_path / "claim.txt"
    txt.write_text("hello")
    r = client.post(
        "/api/fingerprints", files=_upload(txt, "text/plain"), data={"claim_reference": "X"}
    )
    assert r.status_code == 415

    fake = tmp_path / "fake.mp4"
    fake.write_bytes(b"\x00" * 2048)
    r = client.post("/api/fingerprints", files=_upload(fake), data={"claim_reference": "X"})
    assert r.status_code == 422


def test_verification_log_and_stats(client, registered):
    log = client.get("/api/verifications").json()
    assert len(log) >= 1
    stats = client.get("/api/stats").json()
    assert stats["fingerprints"] >= 1
    assert stats["verifications"] == sum(stats["verdicts"].values())


def test_api_key_enforced_when_configured(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "api_key", "s3cret")
    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/stats", headers={"X-API-Key": "s3cret"}).status_code == 200
    assert client.get("/api/health").status_code == 200  # health stays public


def test_delete(client, videos):
    created = client.post(
        "/api/fingerprints", files=_upload(videos["unrelated"]), data={"claim_reference": "TMP"}
    ).json()
    assert client.delete(f"/api/fingerprints/{created['id']}").status_code == 204
    assert client.get(f"/api/fingerprints/{created['id']}").status_code == 404
