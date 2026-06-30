#!/usr/bin/env python3
"""Rank CASMI queries with cached CFM-ID candidate spectra."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from run_cfmid_precomputed_smoke import parse_all_smiles, parse_ranked, write_query_spectrum
from run_cfmid_precomputed_candidate_shard import adduct_slug


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--casmi-dir", type=Path, default=CASMI_DIR)
    parser.add_argument("--cfm-bin-dir", type=Path, default=DEFAULT_CFM_DIR)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--query-start", type=int, default=0)
    parser.add_argument("--query-limit", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--score-type", default="DotProduct")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(args.casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(args.casmi_dir / "cand_df.pkl")
    model_adducts = {p.name for p in args.model_root.iterdir() if p.is_dir()}
    supported = spec[spec["prec_type"].astype(str).isin(model_adducts)].reset_index(drop=True).copy()
    stop = None if args.query_limit <= 0 else args.query_start + args.query_limit
    selected = supported.iloc[max(0, args.query_start) : stop].copy()

    grouped = {int(k): v["candidate_mol_id"].astype(int).tolist() for k, v in cand.groupby("query_mol_id", sort=False)}
    needed: set[int] = set()
    for _, row in selected.iterrows():
        needed.update(grouped.get(int(row["mol_id"]), []))
        needed.add(int(row["mol_id"]))
    id_to_smiles = parse_all_smiles(args.casmi_dir / "all_smiles.txt", needed)

    query_rows = []
    pred_rows = []
    command_rows = []
    for _, row in selected.iterrows():
        spec_id = str(row["spec_id"])
        query_mol_id = int(row["mol_id"])
        adduct = str(row["prec_type"])
        slug = adduct_slug(adduct)
        work_dir = args.outdir / "work" / f"query_{spec_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        ranked_path = work_dir / f"cfmid_precomputed_ranked_{spec_id}.txt"
        query_spectrum = work_dir / f"query_spectrum_{spec_id}.txt"
        triples = work_dir / f"candidate_triples_{spec_id}.txt"

        candidate_ids = grouped.get(query_mol_id, [])
        missing = []
        with triples.open("w", encoding="utf-8") as handle:
            for candidate_id in candidate_ids:
                smiles = id_to_smiles.get(candidate_id)
                spectrum_file = args.outdir / "candidate_spectra_cache" / slug / f"{candidate_id}.txt"
                if smiles and spectrum_file.exists() and spectrum_file.stat().st_size > 0:
                    handle.write(f"{candidate_id} {smiles} {spectrum_file}\n")
                else:
                    missing.append(candidate_id)

        if missing:
            status = "blocked_missing_candidate_spectra"
            ranked = []
            run = {
                "command": "",
                "status": status,
                "returncode": None,
                "elapsed_seconds": 0.0,
                "stdout": "",
                "stderr": "",
            }
        elif args.resume and ranked_path.exists() and ranked_path.stat().st_size > 0:
            status = "completed_cached"
            ranked = parse_ranked(ranked_path)
            run = {
                "command": "",
                "status": status,
                "returncode": 0,
                "elapsed_seconds": 0.0,
                "stdout": "",
                "stderr": "",
            }
        else:
            write_query_spectrum(query_spectrum, [(float(mz), float(intensity)) for mz, intensity in row["peaks"]])
            cmd = [
                str(args.cfm_bin_dir / "cfm-id-precomputed"),
                str(query_spectrum),
                spec_id,
                str(triples),
                "-1",
                "10",
                "0.01",
                args.score_type,
                str(ranked_path),
                "0",
                "0",
            ]
            run = run_command(cmd, work_dir / "logs" / "cfm_id_precomputed.stdout.log", work_dir / "logs" / "cfm_id_precomputed.stderr.log", args.timeout_seconds)
            ranked = parse_ranked(ranked_path) if run["status"] == "completed" else []
            status = "completed" if ranked else run["status"]

        true_rank = np.nan
        for item in ranked:
            is_correct = int(item["candidate_mol_id"]) == query_mol_id
            if is_correct:
                true_rank = float(item["rank"])
            pred_rows.append(
                {
                    "dataset": "CASMI2022",
                    "model": "CFM-ID",
                    "status": status,
                    "native_or_fallback": "native_cfmid_precomputed_full_supported_queries",
                    "query_id": spec_id,
                    "spectrum_id": spec_id,
                    "true_candidate_id": f"CASMI_MOL_{query_mol_id}",
                    "candidate_id": f"CASMI_MOL_{item['candidate_mol_id']}",
                    "candidate_mol_id": item["candidate_mol_id"],
                    "score": item["score"],
                    "rank": item["rank"],
                    "is_correct": is_correct,
                    "adduct": adduct,
                    "candidate_count": len(candidate_ids),
                }
            )
        finite = not pd.isna(true_rank)
        query_rows.append(
            {
                "dataset": "CASMI2022",
                "model": "CFM-ID",
                "status": status,
                "native_or_fallback": "native_cfmid_precomputed_full_supported_queries",
                "query_id": spec_id,
                "spectrum_id": spec_id,
                "true_candidate_id": f"CASMI_MOL_{query_mol_id}",
                "adduct": adduct,
                "candidate_count": len(candidate_ids),
                "ranked_rows": len(ranked),
                "missing_candidate_spectra": len(missing),
                "true_rank": true_rank,
                "top1_correct": bool(finite and true_rank == 1),
                "top5_correct": bool(finite and true_rank <= 5),
                "top10_correct": bool(finite and true_rank <= 10),
                "reciprocal_rank": 0.0 if not finite else 1.0 / true_rank,
                "elapsed_seconds": run["elapsed_seconds"],
                "rank_output_file": str(ranked_path),
            }
        )
        command_rows.append({"query_id": spec_id, **run})

    pd.DataFrame(query_rows).to_csv(args.outdir / f"query_shard_{args.query_start}_{args.query_limit}_results.csv", index=False)
    if pred_rows:
        pd.DataFrame(pred_rows).to_csv(args.outdir / f"query_shard_{args.query_start}_{args.query_limit}_predictions.csv", index=False)
    with (args.outdir / f"query_shard_{args.query_start}_{args.query_limit}_commands.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({k for row in command_rows for k in row}))
        writer.writeheader()
        writer.writerows(command_rows)

    complete = sum(1 for row in query_rows if row["status"] in {"completed", "completed_cached"})
    audit = {
        "stage": "cfmid_precomputed_query_ranking_shard",
        "status": "completed" if complete == len(query_rows) and query_rows else "partial_or_blocked",
        "query_start": args.query_start,
        "query_limit": args.query_limit,
        "selected_queries": len(query_rows),
        "completed_queries": complete,
        "blocked_queries": sum(1 for row in query_rows if row["status"] == "blocked_missing_candidate_spectra"),
    }
    (args.outdir / f"query_shard_{args.query_start}_{args.query_limit}_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
