#!/usr/bin/env python3
"""Run native CFM-ID precomputed ranking for complete small CASMI queries.

This script is a middle ground between the 10-candidate smoke test and the full
936k-candidate-spectrum CASMI run. It selects the supported CASMI query or
queries with the fewest candidates and runs each selected query against its full
candidate set. Results are explicitly labelled as a complete-query subset, not
as a full CASMI baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from run_cfmid_precomputed_smoke import parse_all_smiles, parse_msp, parse_ranked, write_plain_spectrum, write_query_spectrum


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
DEFAULT_CFM_DIR = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin")
DEFAULT_MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
DEFAULT_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_complete_query_subset_v1"


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


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_supported_query_table(casmi_dir: Path, model_root: Path) -> pd.DataFrame:
    spec = pd.read_pickle(casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(casmi_dir / "cand_df.pkl")
    model_adducts = {p.name for p in model_root.iterdir() if p.is_dir()}
    supported = spec[spec["prec_type"].astype(str).isin(model_adducts)].copy()
    counts = cand.groupby("query_mol_id")["candidate_mol_id"].size()
    rows = []
    for supported_order, (spec_row_index, row) in enumerate(supported.iterrows()):
        query_mol_id = int(row["mol_id"])
        rows.append(
            {
                "supported_index": int(supported_order),
                "spec_row_index": int(spec_row_index),
                "spec_id": str(row["spec_id"]),
                "query_mol_id": query_mol_id,
                "adduct": str(row["prec_type"]),
                "precursor_mz": float(row["prec_mz"]),
                "candidate_count": int(counts.get(query_mol_id, 0)),
            }
        )
    return pd.DataFrame(rows).sort_values(["candidate_count", "supported_index"]).reset_index(drop=True)


def write_candidate_smiles(path: Path, candidate_ids: list[int], id_to_smiles: dict[int, str]) -> list[int]:
    missing_smiles = []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for candidate_id in candidate_ids:
            smiles = id_to_smiles.get(int(candidate_id))
            if smiles:
                handle.write(f"{int(candidate_id)} {smiles}\n")
            else:
                missing_smiles.append(int(candidate_id))
    return missing_smiles


def append_msp(target: Path, source: Path) -> None:
    if not source.exists() or source.stat().st_size == 0:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("ab") as out, source.open("rb") as inp:
        if target.stat().st_size > 0:
            out.write(b"\n")
        shutil.copyfileobj(inp, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--casmi-dir", type=Path, default=CASMI_DIR)
    parser.add_argument("--cfm-bin-dir", type=Path, default=DEFAULT_CFM_DIR)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--max-queries", type=int, default=1)
    parser.add_argument("--max-candidates", type=int, default=250)
    parser.add_argument("--query-spec-id", default="")
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    parser.add_argument("--score-type", default="DotProduct")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(args.casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(args.casmi_dir / "cand_df.pkl")
    grouped = {int(k): v["candidate_mol_id"].astype(int).tolist() for k, v in cand.groupby("query_mol_id", sort=False)}
    query_table = build_supported_query_table(args.casmi_dir, args.model_root)
    if args.query_spec_id:
        selected = query_table[query_table["spec_id"].astype(str).eq(str(args.query_spec_id))].copy()
    else:
        selected = query_table[query_table["candidate_count"].le(args.max_candidates)].head(max(1, args.max_queries)).copy()
    if selected.empty:
        raise SystemExit("No supported query matched the selection criteria.")
    selected.to_csv(args.outdir / "selected_complete_query_manifest.csv", index=False)
    previous_results_path = args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_query_results.csv"
    previous_by_query: dict[str, dict[str, Any]] = {}
    if previous_results_path.exists():
        previous_df = pd.read_csv(previous_results_path)
        for _, prev in previous_df.iterrows():
            previous_by_query[str(prev["query_id"])] = prev.to_dict()

    needed: set[int] = set()
    for _, row in selected.iterrows():
        needed.add(int(row["query_mol_id"]))
        needed.update(grouped.get(int(row["query_mol_id"]), []))
    id_to_smiles = parse_all_smiles(args.casmi_dir / "all_smiles.txt", needed)

    pred_rows: list[dict[str, Any]] = []
    query_rows: list[dict[str, Any]] = []
    command_rows: list[dict[str, Any]] = []

    spec_by_id = {str(row["spec_id"]): row for _, row in spec.iterrows()}
    for _, query_info in selected.iterrows():
        spec_id = str(query_info["spec_id"])
        query_mol_id = int(query_info["query_mol_id"])
        adduct = str(query_info["adduct"])
        candidate_ids = grouped.get(query_mol_id, [])
        work_dir = args.outdir / "work" / f"query_{spec_id}"
        plain_dir = work_dir / "plain_candidate_spectra"
        work_dir.mkdir(parents=True, exist_ok=True)

        candidate_smiles = work_dir / "candidate_smiles.txt"
        missing_smiles = write_candidate_smiles(candidate_smiles, candidate_ids, id_to_smiles)

        predicted_msp = work_dir / "candidate_spectra.msp"
        model_dir = args.model_root / adduct
        predict_run: dict[str, Any]
        existing_spectra = parse_msp(predicted_msp) if predicted_msp.exists() and predicted_msp.stat().st_size > 0 else {}
        missing_for_prediction = [
            int(candidate_id)
            for candidate_id in candidate_ids
            if str(int(candidate_id)) not in existing_spectra and id_to_smiles.get(int(candidate_id))
        ]
        if args.resume and predicted_msp.exists() and predicted_msp.stat().st_size > 0 and not missing_for_prediction:
            prev_elapsed = float(previous_by_query.get(spec_id, {}).get("cfm_predict_seconds", 0.0) or 0.0)
            predict_run = {
                "command": "",
                "status": "completed_cached",
                "returncode": 0,
                "elapsed_seconds": prev_elapsed,
                "stdout": "",
                "stderr": "",
            }
        else:
            predict_input = candidate_smiles
            predict_output = predicted_msp
            if args.resume and existing_spectra and missing_for_prediction:
                predict_input = work_dir / "candidate_smiles_missing.txt"
                missing_input_smiles = write_candidate_smiles(predict_input, missing_for_prediction, id_to_smiles)
                missing_smiles.extend(missing_input_smiles)
                predict_output = work_dir / "candidate_spectra_missing.msp"
            predict_cmd = [
                str(args.cfm_bin_dir / "cfm-predict"),
                str(predict_input),
                "0.001",
                str(model_dir / "param_output.log"),
                str(model_dir / "param_config.txt"),
                "0",
                str(predict_output),
                "1",
                "1",
            ]
            predict_run = run_command(
                predict_cmd,
                work_dir / "logs" / "cfm_predict.stdout.log",
                work_dir / "logs" / "cfm_predict.stderr.log",
                args.timeout_seconds,
            )
            if predict_output != predicted_msp and predict_output.exists() and predict_output.stat().st_size > 0:
                append_msp(predicted_msp, predict_output)
        command_rows.append({"query_id": spec_id, "phase": "cfm_predict", **predict_run})

        spectra = parse_msp(predicted_msp) if predicted_msp.exists() else {}
        triples = work_dir / "candidate_triples_plain.txt"
        missing_spectra = []
        with triples.open("w", encoding="utf-8") as handle:
            for candidate_id in candidate_ids:
                candidate_text = str(int(candidate_id))
                smiles = id_to_smiles.get(int(candidate_id))
                if candidate_text in spectra and smiles:
                    spectrum_path = plain_dir / f"{candidate_text}.txt"
                    write_plain_spectrum(spectrum_path, spectra[candidate_text])
                    handle.write(f"{candidate_text} {smiles} {spectrum_path}\n")
                else:
                    missing_spectra.append(int(candidate_id))

        ranked_path = work_dir / f"cfmid_precomputed_ranked_{spec_id}.txt"
        query_spectrum = work_dir / f"query_spectrum_{spec_id}.txt"
        ranked: list[dict[str, Any]] = []
        if missing_smiles or missing_spectra or len(spectra) != len(candidate_ids):
            status = "partial_missing_candidate_spectra"
            rank_run = {
                "command": "",
                "status": status,
                "returncode": None,
                "elapsed_seconds": 0.0,
                "stdout": "",
                "stderr": "",
            }
        elif args.resume and ranked_path.exists() and ranked_path.stat().st_size > 0:
            prev_elapsed = float(previous_by_query.get(spec_id, {}).get("cfm_id_precomputed_seconds", 0.0) or 0.0)
            status = "completed_cached"
            ranked = parse_ranked(ranked_path)
            rank_run = {
                "command": "",
                "status": status,
                "returncode": 0,
                "elapsed_seconds": prev_elapsed,
                "stdout": "",
                "stderr": "",
            }
        else:
            source_spec = spec_by_id[spec_id]
            write_query_spectrum(query_spectrum, [(float(mz), float(intensity)) for mz, intensity in source_spec["peaks"]])
            rank_cmd = [
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
            rank_run = run_command(
                rank_cmd,
                work_dir / "logs" / "cfm_id_precomputed.stdout.log",
                work_dir / "logs" / "cfm_id_precomputed.stderr.log",
                args.timeout_seconds,
            )
            ranked = parse_ranked(ranked_path) if rank_run["status"] == "completed" else []
            status = "completed" if len(ranked) == len(candidate_ids) else "partial_ranked_rows"
        command_rows.append({"query_id": spec_id, "phase": "cfm_id_precomputed", **rank_run})

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
                    "native_or_fallback": "native_cfmid_precomputed_complete_query_subset",
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
                "native_or_fallback": "native_cfmid_precomputed_complete_query_subset",
                "query_id": spec_id,
                "spectrum_id": spec_id,
                "true_candidate_id": f"CASMI_MOL_{query_mol_id}",
                "query_mol_id": query_mol_id,
                "adduct": adduct,
                "candidate_count": len(candidate_ids),
                "ranked_rows": len(ranked),
                "predicted_spectrum_ids": len(spectra),
                "missing_smiles": len(missing_smiles),
                "missing_candidate_spectra": len(missing_spectra),
                "true_rank": true_rank,
                "top1_correct": bool(finite and true_rank == 1),
                "top5_correct": bool(finite and true_rank <= 5),
                "top10_correct": bool(finite and true_rank <= 10),
                "reciprocal_rank": 0.0 if not finite else 1.0 / true_rank,
                "cfm_predict_seconds": predict_run["elapsed_seconds"],
                "cfm_id_precomputed_seconds": rank_run["elapsed_seconds"],
                "rank_output_file": str(ranked_path),
            }
        )

    query_df = pd.DataFrame(query_rows)
    pred_df = pd.DataFrame(pred_rows)
    query_df.to_csv(args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_query_results.csv", index=False)
    pred_df.to_csv(args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_predictions.csv", index=False)
    mirror_dir = ROOT / "results" / "predictions"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    pred_df.to_csv(mirror_dir / "casmi2022_cfmid_native_precomputed_complete_query_subset_predictions.csv", index=False)
    write_csv(args.outdir / "cfmid_precomputed_complete_query_subset_commands.csv", command_rows, sorted({key for row in command_rows for key in row}))

    completed = query_df[query_df["status"].astype(str).isin(["completed", "completed_cached"])].copy()
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID complete-query subset",
        "status": "completed_subset" if len(completed) == len(query_df) and len(query_df) else "partial_subset",
        "native_or_fallback": "native_cfmid_precomputed_complete_query_subset",
        "n_queries": int(len(query_df)),
        "n_queries_completed": int(len(completed)),
        "candidate_pool_policy": "full_candidate_set_for_each_selected_query",
        "candidate_limit": -1,
        "top1_accuracy": float(completed["top1_correct"].mean()) if not completed.empty else np.nan,
        "top5_accuracy": float(completed["top5_correct"].mean()) if not completed.empty else np.nan,
        "top10_accuracy": float(completed["top10_correct"].mean()) if not completed.empty else np.nan,
        "mean_reciprocal_rank": float(completed["reciprocal_rank"].mean()) if not completed.empty else np.nan,
        "median_true_rank": float(pd.to_numeric(completed["true_rank"], errors="coerce").median()) if not completed.empty else np.nan,
        "median_candidate_count": float(completed["candidate_count"].median()) if not completed.empty else np.nan,
        "claim_guardrail": "Complete-query CFM-ID subset only. Each selected query uses its full candidate set, but this is not a full CASMI CFM-ID baseline.",
    }
    pd.DataFrame([summary]).to_csv(args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_summary.csv", index=False)
    audit = {
        "stage": "casmi2022_cfmid_native_precomputed_complete_query_subset_v1",
        "status": summary["status"],
        "selection": {
            "max_queries": args.max_queries,
            "max_candidates": args.max_candidates,
            "query_spec_id": args.query_spec_id,
        },
        "summary": summary,
        "selected_queries": query_df.to_dict(orient="records"),
    }
    (args.outdir / "audit_summary.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# CASMI2022 Native CFM-ID Precomputed Complete-Query Subset",
        "",
        summary["claim_guardrail"],
        "",
        "## Summary",
        "",
        pd.DataFrame([summary]).to_markdown(index=False),
        "",
        "## Query Results",
        "",
        query_df.to_markdown(index=False),
        "",
    ]
    (args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
