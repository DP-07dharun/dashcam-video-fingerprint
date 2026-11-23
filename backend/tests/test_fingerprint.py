import cv2
import numpy as np
import pytest

from app.fingerprint import Verdict, VideoReadError, compare_fingerprints, fingerprint_video, phash
from app.fingerprint.engine import hamming


@pytest.fixture(scope="module")
def ref(videos):
    return fingerprint_video(videos["original"], 0.5)


def test_phash_is_deterministic_and_64_bit():
    frame = np.random.default_rng(1).integers(0, 255, (120, 160, 3), dtype=np.uint8)
    h = phash(frame)
    assert h == phash(frame)
    assert len(h) == 16
    int(h, 16)  # valid hex


def test_phash_survives_resize_and_compression_but_not_new_content():
    rng = np.random.default_rng(2)
    frame = cv2.resize(rng.integers(0, 255, (9, 16, 3), dtype=np.uint8), (640, 360))
    small = cv2.resize(frame, (320, 180))
    _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
    compressed = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
    other = cv2.resize(rng.integers(0, 255, (9, 16, 3), dtype=np.uint8), (640, 360))

    assert hamming(phash(frame), phash(small)) <= 4
    assert hamming(phash(frame), phash(compressed)) <= 6
    assert hamming(phash(frame), phash(other)) > 10


def test_fingerprint_metadata(ref):
    assert ref.fps == pytest.approx(24, abs=0.1)
    assert ref.duration_s == pytest.approx(8.0, abs=0.1)
    assert (ref.width, ref.height) == (640, 360)
    assert len(ref.frame_hashes) == 16  # 8 s / 0.5 s
    assert len(ref.sha256) == 64 and len(ref.perceptual_digest) == 64


def test_identical_file_is_exact(ref, videos):
    result = compare_fingerprints(ref, fingerprint_video(videos["original"]))
    assert result.verdict is Verdict.AUTHENTIC_EXACT
    assert result.similarity == 1.0 and result.segments == []


def test_reencoded_file_is_authentic(ref, videos):
    result = compare_fingerprints(ref, fingerprint_video(videos["reencoded"]))
    assert result.verdict is Verdict.AUTHENTIC_REENCODED
    assert not result.exact_match
    assert result.similarity >= 0.95


def test_tampered_segment_is_located(ref, videos):
    result = compare_fingerprints(ref, fingerprint_video(videos["tampered"]))
    assert result.verdict is Verdict.TAMPERED
    altered = [s for s in result.segments if s.kind == "altered"]
    assert len(altered) == 1
    assert altered[0].start_s == pytest.approx(5.0, abs=0.5)
    assert altered[0].end_s == pytest.approx(7.0, abs=0.5)


def test_trimmed_start_is_reported_as_missing(ref, videos):
    result = compare_fingerprints(ref, fingerprint_video(videos["trimmed"]))
    assert result.verdict is Verdict.TAMPERED
    assert result.offset_s == pytest.approx(-2.0)
    missing = [s for s in result.segments if s.kind == "missing"]
    assert missing and missing[0].start_s == 0.0 and missing[0].end_s == pytest.approx(2.0)


def test_unrelated_footage_does_not_match(ref, videos):
    result = compare_fingerprints(ref, fingerprint_video(videos["unrelated"]))
    assert result.verdict is Verdict.NO_MATCH
    assert result.similarity < 0.4


def test_non_video_file_is_rejected(tmp_path):
    bogus = tmp_path / "notes.mp4"
    bogus.write_bytes(b"this is not a video" * 100)
    with pytest.raises(VideoReadError):
        fingerprint_video(bogus)
