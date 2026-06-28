"""SIRIUS/CSI:FingerID benchmark wrapper."""

from __future__ import annotations

import shutil
import subprocess

from .base import CandidatePrediction, SpectrumRecord, WeightedScoreAnnotator


class SiriusAnnotator(WeightedScoreAnnotator):
    """Use SIRIUS formula scores as scalar formula plausibility evidence."""

    def __init__(self, executable: str | None = None) -> None:
        super().__init__(
            name="SIRIUS",
            weights={"sirius_formula_score": 1.0},
            score_status="precomputed_sirius_formula_score",
        )
        self.executable = executable or shutil.which("sirius")

    def cli_version(self) -> str | None:
        if not self.executable:
            return None
        try:
            completed = subprocess.run(
                [self.executable, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception:
            return None
        text = (completed.stdout or completed.stderr).strip()
        return text or None

    def predict(self, spectrum: SpectrumRecord) -> list[CandidatePrediction]:
        predictions = super().predict(spectrum)
        status = "precomputed_sirius_formula_score"
        if self.executable:
            status += "_cli_available"
        else:
            status += "_cli_not_found"
        return [
            CandidatePrediction(
                candidate_id=pred.candidate_id,
                inchikey=pred.inchikey,
                smiles=pred.smiles,
                formula=pred.formula,
                score=pred.score,
                rank=pred.rank,
                metadata={**pred.metadata, "score_status": status, "executable": self.executable},
            )
            for pred in predictions
        ]
