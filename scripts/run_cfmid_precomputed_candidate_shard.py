#!/usr/bin/env python3
"""Generate cached CFM-ID candidate spectra for one full-CASMI shard."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd

from run_cfmid_precomputed_smoke import parse_all_smiles, parse_msp, write_plain_spectrum


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
DEFAULT_CFM_DIR = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin")
DEFAULT_MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
DEFAULT_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"


def run_command(cmd: list[str], stdout_path: Path, stderr_path: Path, timeout_seconds: int) -> dict[str, Any]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        try:
            proc = subprocess.run(cmd, stdout=stdout, stderr=stderr, text=True, timeout=timeout_seconds, check=False)
            status = "completed" if proc.returncode == 0 else "failed"
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            status = "timeout"
            returncode = None
    return {
        "command": " ".join(cmd),
        "status": status,
        "returncode": returncode,
        "elapsed_seconds": time.time() - started,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def adduct_slug(adduct: str) -> str:
    return adduct.replace("[", "").replace("]", "").replace("+", "plus").replace("-", "minus")


def get_unique_candidate_ids(casmi_dir: Path, model_root: Path, adduct: str) -> list[int]:
    spec = pd.read_pickle(casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(casmi_dir / "cand_df.pkl")
    model_adducts = {p.name for p in model_root.iterdir() if p.is_dir()}
    supported = spec[spec["prec_type"].astype(str).isin(model_adducts)].copy()
    adduct_spec = supported[supported["prec_type"].astype(str).eq(adduct)].copy()
    grouped = {int(k): v["candidate_mol_id"].astype(int).tolist() for k, v in cand.groupby("query_mol_id", sort=False)}
    unique_ids: set[int] = set()
    for mol_id in adduct_spec["mol_id"].astype(int):
        unique_ids.update(grouped.get(int(mol_id), []))
    return sorted(unique_ids)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--casmi-dir", type=Path, default=CASMI_DIR)
    parser.add_argument("--cfm-bin-dir", type=Path, default=DEFAULT_CFM_DIR)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--adduct", required=True)
    parser.add_argument("--candidate-start", type=int, default=0)
    parser.add_argument("--candidate-limit", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=int, default=86400)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    slug = adduct_slug(args.adduct)
    cache_dir = args.outdir / "candidate_spectra_cache" / slug
    shard_dir = args.outdir / "candidate_spectrum_shards" / slug / f"shard_{args.candidate_start}_{args.candidate_limit}"
    shard_dir.mkdir(parents=True, exist_ok=True)

    all_candidate_ids = get_unique_candidate_ids(args.casmi_dir, args.model_root, args.adduct)
    selected_ids = all_candidate_ids[args.candidate_start : args.candidate_start + max(0, args.candidate_limit)]
    id_to_smiles = parse_all_smiles(args.casmi_dir / "all_smiles.txt", set(selected_ids))

    pending_ids = []
    status_rows = []
    for mol_id in selected_ids:
        plain_path = cache_dir / f"{mol_id}.txt"
        if args.resume and plain_path.exists() and plain_path.stat().st_size > 0:
            status_rows.append(
                {
                    "candidate_mol_id": mol_id,
                    "status": "completed_cached",
                    "spectrum_file": str(plain_path),
                    "reason": "",
                }
            )
        else:
            pending_ids.append(mol_id)

    candidate_smiles = shard_dir / "candidate_smiles.txt"
    with candidate_smiles.open("w", encoding="utf-8") as handle:
        for mol_id in pending_ids:
            smiles = id_to_smiles.get(mol_id)
            if smiles:
                handle.write(f"{mol_id} {smiles}\n")
            else:
                status_rows.append(
                    {
                        "candidate_mol_id": mol_id,
                        "status": "failed",
                        "spectrum_file": "",
                        "reason": "missing_smiles",
                    }
                )

    predicted_msp = shard_dir / "candidate_spectra.msp"
    predict_run: dict[str, Any] | None = None
    if candidate_smiles.exists() and candidate_smiles.stat().st_size > 0:
        model_dir = args.model_root / args.adduct
        cmd = [
            str(args.cfm_bin_dir / "cfm-predict"),
            str(candidate_smiles),
            "0.001",
            str(model_dir / "param_output.log"),
            str(model_dir / "param_config.txt"),
            "0",
            str(predicted_msp),
            "1",
            "1",
        ]
        predict_run = run_command(cmd, shard_dir / "logs" / "cfm_predict.stdout.log", shard_dir / "logs" / "cfm_predict.stderr.log", args.timeout_seconds)
        spectra = parse_msp(predicted_msp) if predicted_msp.exists() else {}
        for mol_id in pending_ids:
            mol_text = str(mol_id)
            plain_path = cache_dir / f"{mol_id}.txt"
            if mol_text in spectra and any(spectra[mol_text].values()):
                write_plain_spectrum(plain_path, spectra[mol_text])
                status_rows.append(
                    {
                        "candidate_mol_id": mol_id,
                        "status": "completed",
                        "spectrum_file": str(plain_path),
                        "reason": "",
                    }
                )
            elif id_to_smiles.get(mol_id):
                status_rows.append(
                    {
                        "candidate_mol_id": mol_id,
                        "status": "failed",
                        "spectrum_file": "",
                        "reason": "missing_predicted_spectrum_in_msp",
                    }
                )
    else:
        predict_run = {
            "command": "",
            "status": "skipped_no_pending_candidates",
            "returncode": 0,
            "elapsed_seconds": 0.0,
            "stdout": "",
            "stderr": "",
        }

    status_path = shard_dir / "candidate_spectrum_status.csv"
    with status_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_mol_id", "status", "spectrum_file", "reason"])
        writer.writeheader()
        writer.writerows(status_rows)

    complete = sum(1 for row in status_rows if str(row["status"]).startswith("completed"))
    failed = sum(1 for row in status_rows if row["status"] == "failed")
    audit = {
        "stage": "cfmid_precomputed_candidate_spectrum_shard",
        "status": "completed" if complete == len(selected_ids) and len(selected_ids) > 0 else "partial_or_failed",
        "adduct": args.adduct,
        "candidate_start": args.candidate_start,
        "candidate_limit": args.candidate_limit,
        "selected_candidates": len(selected_ids),
        "completed_candidates": complete,
        "failed_candidates": failed,
        "cache_dir": str(cache_dir),
        "status_csv": str(status_path),
        "cfm_predict": predict_run,
    }
    (shard_dir / "audit_summary.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
