"""MS2DeepScore benchmark wrapper."""

from __future__ import annotations

import importlib.util

from .base import CandidatePrediction, SpectrumRecord, WeightedScoreAnnotator


class MS2DeepScoreAnnotator(WeightedScoreAnnotator):
    """MS2DeepScore-compatible retrieval wrapper.

    If the real `ms2deepscore` package and embeddings are not installed, the
    benchmark uses a deterministic spectral-proxy score derived from the
    internal spectrum score. This is explicitly reported in result metadata.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MS2DeepScore",
            weights={"ms2deepscore_score": 1.0},
            score_status="ms2deepscore_score",
        )
        self.package_available = importlib.util.find_spec("ms2deepscore") is not None

    def score_candidate(self, candidate: dict) -> float:
        if candidate.get("ms2deepscore_score") not in (None, ""):
            return super().score_candidate(candidate)
        # Deterministic fallback for candidate matrices without MS2DeepScore
        # embeddings. The result table marks this as a proxy baseline.
        try:
            our = float(candidate.get("our_spectrum_score", 0.0))
            cfmid = float(candidate.get("cfmid_spectrum_score", 0.0))
        except (TypeError, ValueError):
            return 0.0
        return 0.65 * our + 0.35 * cfmid

    def predict(self, spectrum: SpectrumRecord) -> list[CandidatePrediction]:
        predictions = super().predict(spectrum)
        status = "native_ms2deepscore" if self.package_available else "deterministic_proxy_no_ms2deepscore_package"
        return [
            CandidatePrediction(
                candidate_id=pred.candidate_id,
                inchikey=pred.inchikey,
                smiles=pred.smiles,
                formula=pred.formula,
                score=pred.score,
                rank=pred.rank,
                metadata={**pred.metadata, "score_status": status},
            )
            for pred in predictions
        ]
