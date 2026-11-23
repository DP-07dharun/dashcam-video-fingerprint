"""Video fingerprint extraction.

A fingerprint has two layers:

1. **Cryptographic** - SHA-256 of the exact bytes. Proves a file is bit-for-bit identical,
   but any re-encode (e.g. the dashcam app exporting, WhatsApp compressing) changes it.
2. **Perceptual** - a 64-bit DCT perceptual hash (pHash) of one frame every
   ``sample_interval_s`` seconds. pHash survives re-encoding, resizing and mild compression,
   but changes when the *content* of a frame changes. Comparing the two hash sequences tells
   an insurer whether footage is the same, re-encoded, or edited - and where.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

HASH_SIZE = 8  # 8x8 low-frequency DCT block -> 64-bit hash
_DCT_SIZE = 32


class VideoReadError(ValueError):
    """Raised when a file cannot be decoded as a video."""


@dataclass(slots=True)
class VideoFingerprint:
    sha256: str
    duration_s: float
    fps: float
    width: int
    height: int
    frame_count: int
    sample_interval_s: float
    frame_hashes: list[str] = field(default_factory=list)

    @property
    def perceptual_digest(self) -> str:
        """One SHA-256 over the whole perceptual hash sequence - a compact content ID."""
        return hashlib.sha256("".join(self.frame_hashes).encode()).hexdigest()


def phash(frame: np.ndarray) -> str:
    """64-bit DCT perceptual hash of a BGR or grayscale frame, as 16 hex chars."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    small = cv2.resize(gray, (_DCT_SIZE, _DCT_SIZE), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(small))
    low = dct[:HASH_SIZE, :HASH_SIZE].flatten()
    # Ignore the DC term (overall brightness) when picking the threshold.
    median = np.median(low[1:])
    bits = low > median
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_video(
    path: str | Path, sample_interval_s: float = 0.5, sha256: str | None = None
) -> VideoFingerprint:
    """Decode ``path`` and build its fingerprint.

    Frames are read sequentially (``grab`` skips decoding to RGB for unsampled frames), which
    is far more reliable than seeking across codecs and containers.
    """
    if sample_interval_s <= 0:
        raise ValueError("sample_interval_s must be positive")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise VideoReadError("File could not be opened as a video")

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if not np.isfinite(fps) or fps <= 0:
            fps = 30.0  # some containers omit it; timestamps then fall back to this rate
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        hashes: list[str] = []
        next_sample_t = 0.0
        index = 0
        while cap.grab():
            t = index / fps
            if t + 1e-9 >= next_sample_t:
                ok, frame = cap.retrieve()
                if ok and frame is not None:
                    hashes.append(phash(frame))
                next_sample_t += sample_interval_s
            index += 1
    finally:
        cap.release()

    if index == 0 or not hashes:
        raise VideoReadError("No decodable frames found in the video")

    return VideoFingerprint(
        sha256=sha256 or sha256_file(path),
        duration_s=round(index / fps, 3),
        fps=round(fps, 3),
        width=width,
        height=height,
        frame_count=index,
        sample_interval_s=sample_interval_s,
        frame_hashes=hashes,
    )
