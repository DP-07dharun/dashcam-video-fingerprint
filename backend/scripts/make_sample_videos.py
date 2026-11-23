"""Generate synthetic dashcam-style clips for demos and tests.

    python scripts/make_sample_videos.py [output_dir]

Produces:
  original.mp4    - 12 s "drive" (the footage registered at the time of the incident)
  reencoded.avi   - same footage, re-encoded with another codec at a lower resolution
  tampered.mp4    - same footage with seconds 5-7 replaced by different footage
  trimmed.mp4     - same footage with the first 2 seconds cut
  unrelated.mp4   - a different drive
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

W, H, FPS = 640, 360, 24


def _scene_texture(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    coarse = rng.integers(0, 255, size=(9, 16, 3), dtype=np.uint8)
    return cv2.resize(coarse, (W, H), interpolation=cv2.INTER_CUBIC)


def render_frame(t: float, seed_base: int = 0) -> np.ndarray:
    """A frame of a fake drive: a textured 'scene' that changes every second, a moving
    'car', a road and an on-screen timestamp like a real dashcam overlay."""
    scene = int(t)  # new scene each second
    frame = _scene_texture(seed_base * 1000 + scene).copy()
    # Road
    cv2.fillPoly(
        frame,
        [np.array([[W // 2 - 40, H // 2], [W // 2 + 40, H // 2], [W - 40, H], [40, H]])],
        (60, 60, 60),
    )
    # Lane markings move toward the camera
    for k in range(6):
        y = int(H // 2 + ((t * 120 + k * 40) % (H // 2)))
        cv2.line(frame, (W // 2, y), (W // 2, min(H, y + 15)), (240, 240, 240), 3)
    # A vehicle ahead drifting across lanes
    cx = int(W / 2 + 120 * np.sin(t * 0.8 + seed_base))
    cv2.rectangle(frame, (cx - 45, H // 2 + 20), (cx + 45, H // 2 + 70), (30, 30, 200), -1)
    cv2.putText(
        frame,
        f"CAM1  2026-11-23 08:{14 + int(t) // 60:02d}:{int(t) % 60:02d}",
        (12, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )
    return frame


def write_video(
    path: Path,
    frames,
    fourcc: str = "mp4v",
    size: tuple[int, int] = (W, H),
    fps: float = FPS,
) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*fourcc), fps, size)
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer for {path} ({fourcc})")
    for frame in frames:
        if (frame.shape[1], frame.shape[0]) != size:
            frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        writer.write(frame)
    writer.release()
    return path


def drive(seconds: float, seed_base: int = 0, start: float = 0.0):
    n = int(round(seconds * FPS))
    for i in range(n):
        yield render_frame(start + i / FPS, seed_base)


def tampered_drive(seconds: float, cut_from: float, cut_to: float):
    for i in range(int(round(seconds * FPS))):
        t = i / FPS
        yield render_frame(t, seed_base=7 if cut_from <= t < cut_to else 0)


def make_all(out_dir: Path, seconds: float = 12.0) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "original": write_video(out_dir / "original.mp4", drive(seconds)),
        "reencoded": write_video(
            out_dir / "reencoded.avi", drive(seconds), fourcc="MJPG", size=(426, 240)
        ),
        "tampered": write_video(out_dir / "tampered.mp4", tampered_drive(seconds, 5.0, 7.0)),
        "trimmed": write_video(out_dir / "trimmed.mp4", drive(seconds - 2.0, start=2.0)),
        "unrelated": write_video(out_dir / "unrelated.mp4", drive(seconds, seed_base=42)),
    }


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sample_videos")
    for name, p in make_all(target).items():
        print(f"{name:10s} -> {p} ({p.stat().st_size / 1024:.0f} KB)")
