#!/usr/bin/env python3
"""Audit readiness for harmonized ICEBERG/MassFormer/NEIMS CASMI reruns.

This script records what can be verified locally without fabricating a direct
candidate-set rerun. A model is not marked complete unless candidate-level and
query-level outputs exist for the same CASMI candidate set used by FragAnnotor.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
EXTERNAL_ROOT = Path("/home/zhome/ec_structure/external_ms_models")
OUTDIR = ROOT / "results" / "harmonized_sota_rerun_audit_v1"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if pd.isna(value) if not isinstance(value, (list, dict, tuple)) else False:
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


def run_json(cmd: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception as exc:
        return {
            "command": cmd,
            "returncode": None,
            "stdout": "",
            "stderr": repr(exc),
            "parsed_json": {},
        }
    parsed: dict[str, Any] = {}
    stdout = completed.stdout.strip()
    if stdout:
        for line in reversed(stdout.splitlines()):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    return {
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip()[-4000:],
        "stderr": completed.stderr.strip()[-4000:],
        "parsed_json": parsed,
    }


def casmi_manifest() -> dict[str, Any]:
    spec = pd.read_pickle(CASMI_DIR / "spec_df.pkl")
    cand = pd.read_pickle(CASMI_DIR / "cand_df.pkl")
    smoke_row = spec[spec["prec_type"].astype(str).eq("[M+H]+")].iloc[0]
    return {
        "spec_path": str(CASMI_DIR / "spec_df.pkl"),
        "candidate_path": str(CASMI_DIR / "cand_df.pkl"),
        "all_smiles_path": str(CASMI_DIR / "all_smiles.txt"),
        "n_queries": int(len(spec)),
        "n_supported_mh_queries": int(spec["prec_type"].astype(str).eq("[M+H]+").sum()),
        "n_candidate_rows": int(len(cand)),
        "n_unique_candidate_mol_ids": int(cand["candidate_mol_id"].nunique()),
        "smoke_query_casmi_id": int(smoke_row["casmi_id"]),
        "smoke_query_smiles": str(smoke_row["smiles"]),
        "smoke_query_precursor_mz": float(smoke_row["prec_mz"]),
        "smoke_query_adduct": str(smoke_row["prec_type"]),
    }


def peak_count(result: dict[str, Any]) -> int:
    parsed = result.get("parsed_json") or {}
    peaks = parsed.get("predicted_peaks_json") or []
    return len(peaks) if isinstance(peaks, list) else 0


def smoke_status(result: dict[str, Any]) -> str:
    parsed = result.get("parsed_json") or {}
    return str(parsed.get("prediction_status") or ("command_failed" if result.get("returncode") else "unknown"))


def smoke_error(result: dict[str, Any]) -> str:
    parsed = result.get("parsed_json") or {}
    return str(parsed.get("error_message") or result.get("stderr") or "")


def build_rows(manifest: dict[str, Any], smoke: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    iceberg_wrapper = EXTERNAL_ROOT / "wrappers" / "ms_pred_iceberg_wrapper.py"
    massformer_wrapper = EXTERNAL_ROOT / "wrappers" / "massformer_wrapper.py"
    neims_source = EXTERNAL_ROOT / "vendor" / "ms-pred"
    neims_predict = neims_source / "run_scripts" / "ffn_model" / "02_predict_ffn.py"
    neims_configs = sorted(str(path) for path in (neims_source / "configs" / "neims_ffn").glob("*.yaml"))
    neims_checkpoints = sorted(str(path) for path in neims_source.glob("**/*ffn*.ckpt"))

    rows = []
    iceberg_result = smoke.get("ICEBERG", {})
    iceberg_ok = smoke_status(iceberg_result) == "predicted_spectrum" and peak_count(iceberg_result) > 0
    rows.append(
        {
            "model": "ICEBERG",
            "local_resource": str(EXTERNAL_ROOT / "vendor" / "ms-pred-iceberg-2024"),
            "local_resource_exists": (EXTERNAL_ROOT / "vendor" / "ms-pred-iceberg-2024").exists(),
            "env": str(EXTERNAL_ROOT / "envs" / "ms_pred_iceberg_sys"),
            "env_exists": (EXTERNAL_ROOT / "envs" / "ms_pred_iceberg_sys" / "bin" / "python").exists(),
            "wrapper": str(iceberg_wrapper),
            "wrapper_exists": iceberg_wrapper.exists(),
            "smoke_status": smoke_status(iceberg_result),
            "smoke_predicted_peak_count": peak_count(iceberg_result),
            "smoke_error_message": smoke_error(iceberg_result),
            "harmonized_candidate_set": "data/proc/casmi_2022/spec_df.pkl + cand_df.pkl + all_smiles.txt",
            **manifest,
            "current_status": "wrapper_smoke_passed_full_candidate_rerun_not_started" if iceberg_ok else "wrapper_smoke_failed",
            "claim_status": "blocked_until_harmonized_rerun_completes",
            "required_outputs": "candidate-level predictions plus query-level Top-1/Top-5/Top-10/MRR/Tanimoto/formula metrics on the same CASMI candidate set",
            "required_next_step": "Implement and run a resumable batch/shard ICEBERG candidate-set predictor; do not use per-candidate smoke output as ranking evidence.",
            "harmonized_rerun_complete": False,
        }
    )

    massformer_result = smoke.get("MassFormer", {})
    massformer_ok = smoke_status(massformer_result) == "predicted_spectrum" and peak_count(massformer_result) > 0
    rows.append(
        {
            "model": "MassFormer",
            "local_resource": str(EXTERNAL_ROOT / "vendor" / "massformer"),
            "local_resource_exists": (EXTERNAL_ROOT / "vendor" / "massformer").exists(),
            "env": str(EXTERNAL_ROOT / "envs" / "massformer_sys"),
            "env_exists": (EXTERNAL_ROOT / "envs" / "massformer_sys" / "bin" / "python").exists(),
            "wrapper": str(massformer_wrapper),
            "wrapper_exists": massformer_wrapper.exists(),
            "smoke_status": smoke_status(massformer_result),
            "smoke_predicted_peak_count": peak_count(massformer_result),
            "smoke_error_message": smoke_error(massformer_result),
            "harmonized_candidate_set": "data/proc/casmi_2022/spec_df.pkl + cand_df.pkl + all_smiles.txt",
            **manifest,
            "current_status": "wrapper_smoke_passed_full_candidate_rerun_not_started" if massformer_ok else "wrapper_runs_but_no_positive_intensity_peaks",
            "claim_status": "blocked_until_harmonized_rerun_completes",
            "required_outputs": "candidate-level predictions plus query-level Top-1/Top-5/Top-10/MRR/Tanimoto/formula metrics on the same CASMI candidate set",
            "required_next_step": (
                "Implement and run a resumable batch/shard MassFormer candidate-set predictor; do not use smoke output as ranking evidence."
                if massformer_ok
                else "Locate a validated MassFormer checkpoint/config that emits positive-intensity spectra before any harmonized ranking run."
            ),
            "harmonized_rerun_complete": False,
        }
    )

    rows.append(
        {
            "model": "NEIMS",
            "local_resource": str(neims_source),
            "local_resource_exists": neims_source.exists(),
            "env": str(EXTERNAL_ROOT / "envs" / "ms_pred_iceberg_sys"),
            "env_exists": (EXTERNAL_ROOT / "envs" / "ms_pred_iceberg_sys" / "bin" / "python").exists(),
            "wrapper": "",
            "wrapper_exists": False,
            "smoke_status": "not_run_no_validated_wrapper",
            "smoke_predicted_peak_count": 0,
            "smoke_error_message": "NEIMS/FFN source and configs exist, but no validated FragAnnotor-compatible NEIMS wrapper/checkpoint was found.",
            "neims_predict_script": str(neims_predict),
            "neims_predict_script_exists": neims_predict.exists(),
            "neims_config_count": len(neims_configs),
            "neims_checkpoint_count": len(neims_checkpoints),
            "harmonized_candidate_set": "data/proc/casmi_2022/spec_df.pkl + cand_df.pkl + all_smiles.txt",
            **manifest,
            "current_status": "no_validated_wrapper_or_checkpoint",
            "claim_status": "blocked_until_harmonized_rerun_completes",
            "required_outputs": "candidate-level predictions plus query-level Top-1/Top-5/Top-10/MRR/Tanimoto/formula metrics on the same CASMI candidate set",
            "required_next_step": "Add or locate a NEIMS-compatible inference wrapper and checkpoint, then run the same candidate-set ranking protocol.",
            "harmonized_rerun_complete": False,
        }
    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=OUTDIR)
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--smoke-timeout-seconds", type=int, default=420)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    manifest = casmi_manifest()
    smoke_root = EXTERNAL_ROOT / "outputs" / "harmonized_sota_rerun_smoke"
    smoke: dict[str, dict[str, Any]] = {}
    if not args.skip_smoke:
        smoke_smiles = str(manifest["smoke_query_smiles"])
        smoke_precursor_mz = str(manifest["smoke_query_precursor_mz"])
        smoke_label = f"CASMI_{manifest['smoke_query_casmi_id']}"
        smoke["ICEBERG"] = run_json(
            [
                sys.executable,
                str(EXTERNAL_ROOT / "wrappers" / "ms_pred_iceberg_wrapper.py"),
                "--smiles",
                smoke_smiles,
                "--inchikey",
                f"{smoke_label}_ICEBERG",
                "--precursor-mz",
                smoke_precursor_mz,
                "--adduct",
                "[M+H]+",
                "--polarity",
                "positive",
                "--collision-energy-bin",
                "medium",
                "--output-dir",
                str(smoke_root / "iceberg"),
            ],
            args.smoke_timeout_seconds,
        )
        smoke["MassFormer"] = run_json(
            [
                sys.executable,
                str(EXTERNAL_ROOT / "wrappers" / "massformer_wrapper.py"),
                "--smiles",
                smoke_smiles,
                "--inchikey",
                f"{smoke_label}_MASSFORMER",
                "--precursor-mz",
                smoke_precursor_mz,
                "--adduct",
                "[M+H]+",
                "--polarity",
                "positive",
                "--collision-energy-bin",
                "medium",
                "--output-dir",
                str(smoke_root / "massformer"),
            ],
            args.smoke_timeout_seconds,
        )

    rows = build_rows(manifest, smoke)
    df = pd.DataFrame(rows)
    df.to_csv(args.outdir / "harmonized_sota_rerun_readiness.csv", index=False)
    write_json(args.outdir / "wrapper_smoke_results.json", smoke)
    audit = {
        "stage": "harmonized_sota_rerun_audit_v1",
        "harmonized_reruns_complete": False,
        "direct_sota_claim_allowed": False,
        "models": rows,
        "environment": {"python": sys.version, "platform": platform.platform()},
    }
    write_json(args.outdir / "audit_summary.json", audit)
    report = [
        "# Harmonized SOTA Rerun Readiness",
        "",
        "No ICEBERG/MassFormer/NEIMS direct harmonized CASMI rerun is marked complete by this audit.",
        "",
        "## Current Status",
        "",
    ]
    for row in rows:
        report.extend(
            [
                f"### {row['model']}",
                "",
                f"- `current_status`: `{row['current_status']}`",
                f"- `smoke_status`: `{row['smoke_status']}`",
                f"- `smoke_predicted_peak_count`: `{row['smoke_predicted_peak_count']}`",
                f"- `required_next_step`: {row['required_next_step']}",
                "",
            ]
        )
    (args.outdir / "harmonized_sota_rerun_readiness.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(json_safe(audit), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
