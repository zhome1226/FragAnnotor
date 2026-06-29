"""MS2DeepScore benchmark wrapper."""

from __future__ import annotations

import importlib.util
import math

from .base import CandidatePrediction, SpectrumRecord, WeightedScoreAnnotator, prediction_from_candidate


class MS2DeepScoreAnnotator(WeightedScoreAnnotator):
    """MS2DeepScore-compatible retrieval wrapper.

    This wrapper only ranks candidates when real MS2DeepScore candidate scores
    are present. It does not synthesize proxy embeddings or fallback scores.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MS2DeepScore",
            weights={"ms2deepscore_score": 1.0},
            score_status="native_ms2deepscore_score",
        )
        self.package_available = importlib.util.find_spec("ms2deepscore") is not None

    def predict(self, spectrum: SpectrumRecord) -> list[CandidatePrediction]:
        if not self.package_available:
            return []
        scored: list[CandidatePrediction] = []
        for candidate in spectrum.candidates:
            raw_score = candidate.get("ms2deepscore_score")
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                continue
            if math.isnan(score):
                continue
            scored.append(
                prediction_from_candidate(
                    candidate,
                    score,
                    metadata={"score_status": "native_ms2deepscore_score"},
                )
            )
        ranked = sorted(scored, key=lambda pred: (-pred.score, pred.inchikey, pred.candidate_id))
        return [
            CandidatePrediction(
                candidate_id=pred.candidate_id,
                inchikey=pred.inchikey,
                smiles=pred.smiles,
                formula=pred.formula,
                score=pred.score,
                rank=i + 1,
                metadata={**pred.metadata, "structure_level_ranking": True},
            )
            for i, pred in enumerate(ranked)
        ]
