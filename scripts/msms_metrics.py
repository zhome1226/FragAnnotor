#!/usr/bin/env python3
"""Small shared MS/MS spectrum utilities for benchmark audits.

The functions in this module are deliberately dependency-light.  If matchms is
installed, downstream scripts can still use it directly; these helpers provide
the same preprocessing contract for environments where matchms is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import math

import numpy as np


Peak = tuple[float, float]


@dataclass(frozen=True)
class SpectrumSimilarity:
    score: float
    matched_peaks: int
    reference_peaks: int
    query_peaks: int


def normalize_peaks(
    peaks: Iterable[Sequence[float]],
    *,
    min_relative_intensity: float = 0.0,
    top_k: int | None = None,
    precursor_mz: float | None = None,
    remove_precursor_tolerance: float | None = None,
    l2_normalize: bool = True,
) -> list[Peak]:
    """Return sorted, filtered peaks with optional L2-normalized intensities."""

    parsed: list[Peak] = []
    for peak in peaks or []:
        if len(peak) < 2:
            continue
        try:
            mz = float(peak[0])
            intensity = float(peak[1])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(mz) or not math.isfinite(intensity) or intensity <= 0:
            continue
        if (
            precursor_mz is not None
            and remove_precursor_tolerance is not None
            and abs(mz - float(precursor_mz)) <= float(remove_precursor_tolerance)
        ):
            continue
        parsed.append((mz, intensity))

    if not parsed:
        return []

    max_intensity = max(intensity for _, intensity in parsed)
    if max_intensity <= 0:
        return []

    min_abs = max(0.0, float(min_relative_intensity)) * max_intensity
    filtered = [(mz, intensity / max_intensity) for mz, intensity in parsed if intensity >= min_abs]
    if top_k is not None and top_k > 0 and len(filtered) > top_k:
        filtered = sorted(filtered, key=lambda peak: (-peak[1], peak[0]))[:top_k]
    filtered = sorted(filtered, key=lambda peak: peak[0])

    if l2_normalize and filtered:
        norm = math.sqrt(sum(intensity * intensity for _, intensity in filtered))
        if norm > 0:
            filtered = [(mz, intensity / norm) for mz, intensity in filtered]
    return filtered


def greedy_cosine(reference: list[Peak], query: list[Peak], *, tolerance: float = 0.1) -> SpectrumSimilarity:
    """Greedy peak cosine with one-to-one matching within an m/z tolerance."""

    if not reference or not query:
        return SpectrumSimilarity(0.0, 0, len(reference), len(query))

    ref = sorted(reference)
    qry = sorted(query)
    candidates: list[tuple[float, int, int]] = []
    j0 = 0
    for i, (mz_ref, inten_ref) in enumerate(ref):
        while j0 < len(qry) and qry[j0][0] < mz_ref - tolerance:
            j0 += 1
        j = j0
        while j < len(qry) and qry[j][0] <= mz_ref + tolerance:
            candidates.append((inten_ref * qry[j][1], i, j))
            j += 1

    used_ref: set[int] = set()
    used_qry: set[int] = set()
    score = 0.0
    matched = 0
    for contribution, i, j in sorted(candidates, reverse=True):
        if i in used_ref or j in used_qry:
            continue
        used_ref.add(i)
        used_qry.add(j)
        score += contribution
        matched += 1

    return SpectrumSimilarity(float(max(0.0, min(1.0, score))), matched, len(ref), len(qry))


def modified_cosine(
    reference: list[Peak],
    query: list[Peak],
    *,
    reference_precursor_mz: float | None = None,
    query_precursor_mz: float | None = None,
    tolerance: float = 0.1,
) -> SpectrumSimilarity:
    """Approximate modified cosine by allowing a precursor-mass-shifted match."""

    direct = greedy_cosine(reference, query, tolerance=tolerance)
    if reference_precursor_mz is None or query_precursor_mz is None:
        return direct

    delta = float(query_precursor_mz) - float(reference_precursor_mz)
    shifted_query = [(mz - delta, intensity) for mz, intensity in query]
    shifted = greedy_cosine(reference, shifted_query, tolerance=tolerance)
    return shifted if shifted.score > direct.score else direct


def top_peak_recall(reference: list[Peak], query: list[Peak], *, top_n: int = 20, tolerance: float = 0.1) -> float:
    """Fraction of top-N reference peaks matched by the query spectrum."""

    if top_n <= 0 or not reference:
        return 0.0
    ref_top = sorted(reference, key=lambda peak: (-peak[1], peak[0]))[:top_n]
    qry_mz = np.array([mz for mz, _ in query], dtype=float)
    if qry_mz.size == 0:
        return 0.0
    hits = 0
    for mz, _ in ref_top:
        if np.any(np.abs(qry_mz - mz) <= tolerance):
            hits += 1
    return float(hits / len(ref_top))


def peak_count_summary(
    peaks: Iterable[Sequence[float]],
    *,
    precursor_mz: float | None = None,
) -> dict[str, int]:
    """Common peak-count variants used for benchmark preprocessing audits."""

    return {
        "raw_peak_count": len(normalize_peaks(peaks, l2_normalize=False)),
        "peak_count_ge_1pct": len(normalize_peaks(peaks, min_relative_intensity=0.01, l2_normalize=False)),
        "peak_count_ge_3pct": len(normalize_peaks(peaks, min_relative_intensity=0.03, l2_normalize=False)),
        "peak_count_ge_1pct_no_precursor": len(
            normalize_peaks(
                peaks,
                min_relative_intensity=0.01,
                precursor_mz=precursor_mz,
                remove_precursor_tolerance=1.5,
                l2_normalize=False,
            )
        ),
        "peak_count_top50": len(normalize_peaks(peaks, top_k=50, l2_normalize=False)),
        "peak_count_top20": len(normalize_peaks(peaks, top_k=20, l2_normalize=False)),
    }
