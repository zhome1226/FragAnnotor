"""CFM-ID benchmark wrapper."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import CandidatePrediction, SpectrumRecord, WeightedScoreAnnotator


class CFMIDAnnotator(WeightedScoreAnnotator):
    """Use CFM-ID scores when available, with an optional CLI probe.

    Full CFM-ID spectrum generation is installation-specific. The benchmark
    pipeline uses precomputed candidate-level CFM-ID scores when present and
    records whether a CFM-ID executable was available in the environment.
    """

    def __init__(self, executable: str | None = None) -> None:
        super().__init__(
            name="CFM-ID",
            weights={"cfmid_spectrum_score": 1.0},
            score_status="precomputed_cfmid_score",
        )
        self.executable = executable or shutil.which("cfm-id") or shutil.which("cfmid")

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
        status = "precomputed_cfmid_score"
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

    def write_reproducibility_note(self, path: Path) -> None:
        path.write_text(
            "CFM-ID wrapper\n"
            f"executable: {self.executable or 'not found'}\n"
            f"version_probe: {self.cli_version() or 'not available'}\n",
            encoding="utf-8",
        )
