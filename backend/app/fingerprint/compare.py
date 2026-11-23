"""Compare a candidate video's fingerprint with a registered (reference) fingerprint."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum

from .engine import VideoFingerprint, hamming


class Verdict(StrEnum):
    AUTHENTIC_EXACT = "AUTHENTIC_EXACT"  # bit-for-bit identical file
    AUTHENTIC_REENCODED = "AUTHENTIC_REENCODED"  # same footage, different encoding/resolution
    TAMPERED = "TAMPERED"  # same footage, but segments were changed, cut or inserted
    NO_MATCH = "NO_MATCH"  # different footage


@dataclass(slots=True)
class Segment:
    start_s: float
    end_s: float
    kind: str  # "altered" | "missing" | "extra"


@dataclass(slots=True)
class ComparisonResult:
    verdict: Verdict
    similarity: float  # share of reference samples matched in the candidate (0..1)
    exact_match: bool
    offset_s: float  # candidate timeline shift that gave the best alignment
    matched_samples: int
    reference_samples: int
    candidate_samples: int
    mean_distance: float | None  # mean Hamming distance of matched samples (0..64)
    duration_delta_s: float
    segments: list[Segment] = field(default_factory=list)
    timeline: list[int | None] = field(default_factory=list)  # per reference sample distance

    def to_dict(self) -> dict:
        data = asdict(self)
        data["verdict"] = self.verdict.value
        return data


def _align(ref: list[str], cand: list[str], offset: int) -> list[int | None]:
    """Distance for every reference sample when candidate is shifted by ``offset`` samples."""
    out: list[int | None] = []
    for i, h in enumerate(ref):
        j = i + offset
        out.append(hamming(h, cand[j]) if 0 <= j < len(cand) else None)
    return out


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    """[start, end) index ranges where ``flags`` is True."""
    runs, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            runs.append((start, i))
            start = None
    return runs


def compare_fingerprints(
    reference: VideoFingerprint,
    candidate: VideoFingerprint,
    *,
    hamming_threshold: int = 10,
    authentic_similarity: float = 0.95,
    related_similarity: float = 0.40,
    max_offset_samples: int = 6,
) -> ComparisonResult:
    ref, cand = reference.frame_hashes, candidate.frame_hashes
    step = reference.sample_interval_s
    exact = reference.sha256 == candidate.sha256

    # Pick the shift (in samples) that maximises matching frames - this tolerates footage that
    # was trimmed at the start or re-exported with a slightly different first keyframe.
    best_offset, best_dists, best_score = 0, _align(ref, cand, 0), -1.0
    for offset in range(-max_offset_samples, max_offset_samples + 1):
        dists = _align(ref, cand, offset)
        matches = sum(1 for d in dists if d is not None and d <= hamming_threshold)
        score = matches - abs(offset) * 1e-3  # prefer the smallest shift on ties
        if score > best_score:
            best_offset, best_dists, best_score = offset, dists, score

    matched = [d for d in best_dists if d is not None and d <= hamming_threshold]
    similarity = len(matched) / len(ref) if ref else 0.0
    mean_distance = round(sum(matched) / len(matched), 2) if matched else None

    segments: list[Segment] = []
    for a, b in _runs([d is not None and d > hamming_threshold for d in best_dists]):
        segments.append(Segment(round(a * step, 2), round(b * step, 2), "altered"))
    for a, b in _runs([d is None for d in best_dists]):
        segments.append(Segment(round(a * step, 2), round(b * step, 2), "missing"))
    # Candidate content that falls outside the reference timeline (appended/prepended footage).
    extra_before = max(0, best_offset)
    extra_after = max(0, len(cand) - (len(ref) + best_offset))
    if extra_before:
        segments.append(Segment(round(-extra_before * step, 2), 0.0, "extra"))
    if extra_after:
        end = len(ref) * step
        segments.append(Segment(round(end, 2), round(end + extra_after * step, 2), "extra"))
    segments.sort(key=lambda s: s.start_s)

    duration_delta = round(candidate.duration_s - reference.duration_s, 3)
    # Allow ~one sample of rounding when a re-encode slightly changes frame count.
    duration_ok = abs(duration_delta) <= max(step * 2, 1.0)

    if exact:
        verdict = Verdict.AUTHENTIC_EXACT
        similarity = 1.0
        segments = []
    elif similarity >= authentic_similarity and duration_ok and not segments:
        verdict = Verdict.AUTHENTIC_REENCODED
    elif similarity >= authentic_similarity and duration_ok:
        # A stray noisy sample or two should not condemn a whole claim.
        significant = [s for s in segments if s.end_s - s.start_s > step * 2]
        verdict = Verdict.TAMPERED if significant else Verdict.AUTHENTIC_REENCODED
        if not significant:
            segments = []
    elif similarity >= related_similarity:
        verdict = Verdict.TAMPERED
    else:
        verdict = Verdict.NO_MATCH
        segments = []

    return ComparisonResult(
        verdict=verdict,
        similarity=round(similarity, 4),
        exact_match=exact,
        offset_s=round(best_offset * step, 2),
        matched_samples=len(matched),
        reference_samples=len(ref),
        candidate_samples=len(cand),
        mean_distance=mean_distance,
        duration_delta_s=duration_delta,
        segments=segments,
        timeline=best_dists,
    )
