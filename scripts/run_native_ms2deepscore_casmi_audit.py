#!/usr/bin/env python3
"""Audit native MS2DeepScore feasibility for CASMI2022 candidate ranking."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def package_version(package: str) -> str:
    try:
        import importlib.metadata as metadata

        return metadata.version(package)
    except Exception:
        return ""


def run(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": " ".join(cmd),
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip()[-2000:],
            "stderr": completed.stderr.strip()[-2000:],
        }
    except Exception as exc:
        return {"command": " ".join(cmd), "returncode": None, "stdout": "", "stderr": repr(exc)}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def find_candidate_spectrum_artifacts(root: Path) -> list[str]:
    patterns = ["*ms2deepscore*", "*matchms*", "*candidate*spectra*", "*predicted*spectra*"]
    found: set[str] = set()
    for pattern in patterns:
        for path in root.rglob(pattern):
            if path.is_file():
                found.add(str(path.relative_to(root)))
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit native MS2DeepScore CASMI feasibility.")
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "native_ms2deepscore_casmi")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    ms2_installed = importlib.util.find_spec("ms2deepscore") is not None
    matchms_installed = importlib.util.find_spec("matchms") is not None
    artifacts = find_candidate_spectrum_artifacts(ROOT)
    audit = {
        "stage": "native_ms2deepscore_casmi_audit_v1",
        "status": "blocked_no_candidate_spectrum_library",
        "package_installed": ms2_installed,
        "package_version": package_version("ms2deepscore"),
        "matchms_installed": matchms_installed,
        "matchms_version": package_version("matchms"),
        "pip_index_ms2deepscore": run([sys.executable, "-m", "pip", "index", "versions", "ms2deepscore"]),
        "pip_index_matchms": run([sys.executable, "-m", "pip", "index", "versions", "matchms"]),
        "candidate_spectrum_library_artifacts_found_in_repo": artifacts[:200],
        "candidate_spectrum_library_artifact_count": len(artifacts),
        "benchmark_decision": "Do not report MS2DeepScore CASMI Top-k metrics. MS2DeepScore scores spectrum pairs; the CASMI structure-candidate benchmark lacks a complete per-candidate measured or predicted spectrum library and no configured pretrained MS2DeepScore model file is present. CFM-ID predicted spectra were not substituted, because that would be a hybrid CFM-ID plus MS2DeepScore baseline rather than native MS2DeepScore.",
        "environment": {"python": sys.version, "platform": platform.platform()},
    }
    write_json(args.outdir / "native_ms2deepscore_audit.json", audit)
    pd.DataFrame(
        [
            {
                "stage": audit["stage"],
                "status": audit["status"],
                "package_installed": ms2_installed,
                "package_version": audit["package_version"],
                "matchms_installed": matchms_installed,
                "matchms_version": audit["matchms_version"],
                "candidate_spectrum_library_artifact_count": len(artifacts),
                "benchmark_decision": audit["benchmark_decision"],
            }
        ]
    ).to_csv(args.outdir / "native_ms2deepscore_audit.csv", index=False)
    (args.outdir / "native_ms2deepscore_audit.md").write_text(
        "# Native MS2DeepScore CASMI Audit\n\n"
        f"Status: `{audit['status']}`\n\n"
        "MS2DeepScore is a spectrum-to-spectrum similarity model. The current CASMI2022 benchmark is a structure-candidate ranking task, and no complete per-candidate spectrum library or configured pretrained model is present.\n\n"
        f"{audit['benchmark_decision']}\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
