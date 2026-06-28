"""Unified annotator interface used by the benchmark pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class SpectrumRecord:
    """A benchmark query spectrum and candidate set."""

    dataset: str
    spectrum_id: str
    true_inchikey: str
    true_smiles: str | None = None
    true_formula: str | None = None
    peaks: list[tuple[float, float]] = field(default_factory=list)
    precursor_mz: float | None = None
    adduct: str | None = None
    ion_mode: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CandidatePrediction:
    """A ranked candidate returned by an annotator."""

    candidate_id: str
    inchikey: str
    smiles: str | None = None
    formula: str | None = None
    score: float = 0.0
    rank: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAnnotator(Protocol):
    """All benchmark models expose this interface."""

    name: str

    def predict(self, spectrum: SpectrumRecord) -> list[CandidatePrediction]:
        """Return ranked candidate structures for one query spectrum."""
        ...


def prediction_from_candidate(
    candidate: Mapping[str, Any],
    score: float,
    *,
    rank: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> CandidatePrediction:
    """Build a normalized prediction from a candidate dictionary."""

    return CandidatePrediction(
        candidate_id=str(
            candidate.get("candidate_id")
            or candidate.get("candidate_row_id")
            or candidate.get("row_id")
            or candidate.get("inchikey")
            or candidate.get("candidate_inchikey")
            or ""
        ),
        inchikey=str(candidate.get("inchikey") or candidate.get("candidate_inchikey") or ""),
        smiles=candidate.get("smiles") or candidate.get("canonical_smiles"),
        formula=candidate.get("formula") or candidate.get("candidate_formula"),
        score=float(score),
        rank=rank,
        metadata=metadata or {},
    )


class WeightedScoreAnnotator:
    """Deterministic annotator over precomputed candidate-level score columns."""

    def __init__(self, name: str, weights: Mapping[str, float], score_status: str) -> None:
        self.name = name
        self.weights = dict(weights)
        self.score_status = score_status

    def score_candidate(self, candidate: Mapping[str, Any]) -> float:
        total = 0.0
        for field, weight in self.weights.items():
            value = candidate.get(field, 0.0)
            try:
                total += float(value) * float(weight)
            except (TypeError, ValueError):
                total += 0.0
        return total

    def predict(self, spectrum: SpectrumRecord) -> list[CandidatePrediction]:
        best_by_structure: dict[str, CandidatePrediction] = {}
        for candidate in spectrum.candidates:
            score = self.score_candidate(candidate)
            pred = prediction_from_candidate(
                candidate,
                score,
                metadata={
                    "score_status": self.score_status,
                    "weights": self.weights,
                    "source": candidate.get("score_source") or candidate.get("source"),
                },
            )
            key = pred.inchikey or pred.candidate_id
            old = best_by_structure.get(key)
            if old is None or pred.score > old.score:
                best_by_structure[key] = pred
        scored = sorted(best_by_structure.values(), key=lambda pred: (-pred.score, pred.inchikey, pred.candidate_id))
        return [
            CandidatePrediction(
                candidate_id=pred.candidate_id,
                inchikey=pred.inchikey,
                smiles=pred.smiles,
                formula=pred.formula,
                score=pred.score,
                rank=i + 1,
                metadata={
                    **pred.metadata,
                    "structure_level_ranking": True,
                    "input_candidate_rows": len(spectrum.candidates),
                    "unique_structures_ranked": len(scored),
                },
            )
            for i, pred in enumerate(scored)
        ]
