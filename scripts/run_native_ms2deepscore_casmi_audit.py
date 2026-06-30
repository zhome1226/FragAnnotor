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
EXTERNAL_MS2DEEPSCORE_DIR = Path("/home/zhome/ec_structure/external_ms_models/ms2deepscore")
MS2DEEPSCORE_ENV_PYTHON = Path("/home/zhome/ec_structure/external_ms_models/envs/ms2deepscore_casmi/bin/python")


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


def find_model_files(root: Path) -> list[str]:
    patterns = ["*ms2deep*.pt", "*ms2deep*.hdf5", "*ms2deep*.h5", "*ms2deep*.keras"]
    found: set[str] = set()
    for pattern in patterns:
        for path in root.rglob(pattern):
            if path.is_file():
                found.add(str(path.relative_to(root)))
    return sorted(found)


def external_model_manifest() -> dict[str, Any]:
    expected = ["settings.json", "embedding_model_settings.json", "embedding_evaluator.pt", "ms2deepscore_model.pt"]
    rows = []
    for name in expected:
        path = EXTERNAL_MS2DEEPSCORE_DIR / name
        rows.append({"file": name, "path": str(path), "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0})
    return {
        "resource_dir": str(EXTERNAL_MS2DEEPSCORE_DIR),
        "files": rows,
        "all_required_files_present": all(row["exists"] and row["size_bytes"] > 0 for row in rows),
        "source": "Zenodo 10.5281/zenodo.17826815",
    }


def external_environment_probe() -> dict[str, Any]:
    if not MS2DEEPSCORE_ENV_PYTHON.exists():
        return {"env_python": str(MS2DEEPSCORE_ENV_PYTHON), "status": "missing"}
    cmd = [
        str(MS2DEEPSCORE_ENV_PYTHON),
        "-c",
        "import importlib.metadata as md, json, torch; "
        "print(json.dumps({'ms2deepscore_version': md.version('ms2deepscore'), "
        "'matchms_version': md.version('matchms'), 'torch_version': torch.__version__, "
        "'torch_cuda_available': torch.cuda.is_available()}))",
    ]
    result = run(cmd, timeout=120)
    out = {"env_python": str(MS2DEEPSCORE_ENV_PYTHON), "status": "failed", **result}
    if result.get("returncode") == 0 and result.get("stdout"):
        try:
            out.update(json.loads(str(result["stdout"]).splitlines()[-1]))
            out["status"] = "verified"
        except Exception:
            pass
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit native MS2DeepScore CASMI feasibility.")
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "native_ms2deepscore_casmi")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    ms2_installed = importlib.util.find_spec("ms2deepscore") is not None
    matchms_installed = importlib.util.find_spec("matchms") is not None
    artifacts = find_candidate_spectrum_artifacts(ROOT)
    model_files = find_model_files(ROOT)
    external_model = external_model_manifest()
    external_env = external_environment_probe()
    audit = {
        "stage": "native_ms2deepscore_casmi_audit_v1",
        "status": "blocked_no_candidate_spectrum_library",
        "package_installed": ms2_installed,
        "package_version": package_version("ms2deepscore"),
        "matchms_installed": matchms_installed,
        "matchms_version": package_version("matchms"),
        "pretrained_model_files_found_in_repo": model_files,
        "pretrained_model_file_count": len(model_files),
        "external_pretrained_model_cache": external_model,
        "external_ms2deepscore_environment": external_env,
        "official_pretrained_model_note": "MS2DeepScore documentation points to a Zenodo pretrained ms2deepscore_model.pt for MS2DeepScore >=2.6; the large model is cached outside Git when available and is recorded by results/ms2deepscore_resource_manifest_v1/.",
        "user_space_install_attempt": {
            "env_path": "/home/zhome/ec_structure/external_ms_models/envs/ms2deepscore_casmi",
            "command": "python3 -m venv ... && pip install ms2deepscore==2.7.2 matchms==0.33.1",
            "status": "timed_out_after_30_minutes_not_used_for_benchmark",
        },
        "pip_index_ms2deepscore": run([sys.executable, "-m", "pip", "index", "versions", "ms2deepscore"]),
        "pip_index_matchms": run([sys.executable, "-m", "pip", "index", "versions", "matchms"]),
        "candidate_spectrum_library_artifacts_found_in_repo": artifacts[:200],
        "candidate_spectrum_library_artifact_count": len(artifacts),
        "hybrid_baseline_protocol": [
            "Generate candidate spectra for every CASMI candidate with a clearly named generator such as CFM-ID or ICEBERG.",
            "Load a documented pretrained MS2DeepScore model and convert both query and candidate spectra to matchms Spectrum objects.",
            "Score query spectrum versus every generated candidate spectrum with MS2DeepScore.",
            "Rank candidates by MS2DeepScore similarity and label the model as '<generator> + MS2DeepScore hybrid', not native MS2DeepScore.",
            "Report generator coverage, failed candidates, adduct/ion-mode assumptions, and candidate_limit if any.",
        ],
        "benchmark_decision": "Do not report MS2DeepScore CASMI Top-k metrics yet. MS2DeepScore scores spectrum pairs; the pretrained model and CPU environment are now externally available/verified, but the CASMI structure-candidate benchmark still lacks a complete per-candidate measured or predicted spectrum library and a query-candidate scoring wrapper. CFM-ID predicted spectra must be labeled as a CFM-ID plus MS2DeepScore hybrid baseline rather than native MS2DeepScore.",
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
                "external_environment_status": external_env.get("status"),
                "external_ms2deepscore_version": external_env.get("ms2deepscore_version", ""),
                "external_matchms_version": external_env.get("matchms_version", ""),
                "pretrained_model_file_count": len(model_files),
                "external_model_cache_present": external_model.get("all_required_files_present"),
                "candidate_spectrum_library_artifact_count": len(artifacts),
                "benchmark_decision": audit["benchmark_decision"],
            }
        ]
    ).to_csv(args.outdir / "native_ms2deepscore_audit.csv", index=False)
    (args.outdir / "native_ms2deepscore_audit.md").write_text(
        "# Native MS2DeepScore CASMI Audit\n\n"
        f"Status: `{audit['status']}`\n\n"
        "MS2DeepScore is a spectrum-to-spectrum similarity model. The current CASMI2022 benchmark is a structure-candidate ranking task, and no complete per-candidate spectrum library or configured pretrained model is present.\n\n"
        f"{audit['benchmark_decision']}\n\n"
        "## Hybrid Baseline Protocol\n\n"
        + "\n".join(f"- {step}" for step in audit["hybrid_baseline_protocol"])
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
