"""FragAnnotor benchmark wrapper."""

from __future__ import annotations

from .base import WeightedScoreAnnotator


class FragAnnotorAnnotator(WeightedScoreAnnotator):
    """Current FragAnnotor policy used for candidate annotation.

    The repository benchmark treats FragAnnotor as the frozen expert-fusion
    implementation when candidate-level component scores are available.
    """

    def __init__(self) -> None:
        super().__init__(
            name="FragAnnotor",
            weights={
                "our_spectrum_score": 0.35,
                "cfmid_spectrum_score": 0.50,
                "fragment_formula_score": 0.15,
                "sirius_formula_score": 0.0,
                "reaction_prior_score": 0.0,
            },
            score_status="precomputed_frozen_fragannotor_fusion",
        )
