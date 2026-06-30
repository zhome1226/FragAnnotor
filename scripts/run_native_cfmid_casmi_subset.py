#!/usr/bin/env python3
"""Run a clearly labeled native CFM-ID CASMI subset benchmark.

Full CASMI CFM-ID candidate ranking is very slow in this environment because
cfm-id predicts spectra for every candidate on the fly. This script produces a
bounded, resumable subset benchmark with explicit coverage and candidate-pool
metadata. It must not be reported as the full CASMI CFM-ID result.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFMID = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin/cfm-id")
DEFAULT_MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
DEFAULT_CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_float(value: Any, default: float = np.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def parse_all_smiles(path: Path, needed: set[int]) -> dict[int, str]:
    remaining = set(needed)
    out: dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not remaining:
                break
            text = line.strip()
            if not text:
                continue
            mol_id_text, _, smiles = text.partition(" ")
            try:
                mol_id = int(mol_id_text)
            except ValueError:
                continue
            if mol_id in remaining:
                out[mol_id] = smiles.strip()
                remaining.remove(mol_id)
    return out


def write_spectrum_file(path: Path, peaks: list[tuple[float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for label in ["low", "med", "high"]:
            handle.write(label + "\n")
            for mz, intensity in peaks:
                handle.write(f"{float(mz):.6f} {float(intensity):.6f}\n")


def write_candidate_file(path: Path, candidates: list[tuple[int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for mol_id, smiles in candidates:
            handle.write(f"{int(mol_id)} {smiles}\n")


def parse_cfmid_output(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            parts = text.split(maxsplit=3)
            if len(parts) < 4:
                continue
            rank_text, score_text, mol_id_text, smiles = parts
            try:
                rank = int(rank_text)
                mol_id = int(mol_id_text)
            except ValueError:
                continue
            rows.append({"rank": rank, "score": safe_float(score_text), "candidate_mol_id": mol_id, "smiles": smiles})
    return rows


def run_query(task: dict[str, Any]) -> dict[str, Any]:
    query_id = str(task["spec_id"])
    work_dir = Path(task["work_dir"])
    work_dir.mkdir(parents=True, exist_ok=True)
    spectrum_file = work_dir / f"spectrum_{query_id}.txt"
    candidate_file = work_dir / f"candidates_{query_id}.txt"
    output_file = work_dir / f"cfmid_ranked_{query_id}.txt"
    stdout_file = work_dir / f"cfmid_{query_id}.stdout.log"
    stderr_file = work_dir / f"cfmid_{query_id}.stderr.log"

    if task.get("resume") and output_file.exists():
        parsed = parse_cfmid_output(output_file)
        if parsed:
            return {
                "query": task,
                "status": "completed_cached",
                "elapsed_seconds": 0.0,
                "returncode": 0,
                "output_file": str(output_file),
                "stdout_file": str(stdout_file),
                "stderr_file": str(stderr_file),
                "parsed_rows": parsed,
                "command": "",
            }

    write_spectrum_file(spectrum_file, task["peaks"])
    write_candidate_file(candidate_file, task["candidates"])
    model_dir = Path(task["model_root"]) / task["adduct"]
    cmd = [
        str(task["cfmid"]),
        str(spectrum_file),
        query_id,
        str(candidate_file),
        "-1",
        str(task["ppm_mass_tol"]),
        str(task["abs_mass_tol"]),
        str(task["prob_thresh_for_prune"]),
        str(model_dir / "param_output.log"),
        str(model_dir / "param_config.txt"),
        task["score_type"],
        str(task["apply_postprocessing"]),
        str(output_file),
    ]

    started = time.time()
    with stdout_file.open("w", encoding="utf-8") as stdout, stderr_file.open("w", encoding="utf-8") as stderr:
        proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        try:
            returncode = proc.wait(timeout=int(task["timeout_seconds"]))
            status = "completed" if returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            status = "timeout"
            returncode = None
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    elapsed = time.time() - started
    parsed = parse_cfmid_output(output_file) if status == "completed" else []
    return {
        "query": task,
        "status": status,
        "elapsed_seconds": elapsed,
        "returncode": returncode,
        "output_file": str(output_file),
        "stdout_file": str(stdout_file),
        "stderr_file": str(stderr_file),
        "parsed_rows": parsed,
        "command": " ".join(cmd),
    }


def build_tasks(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = pd.read_pickle(args.casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(args.casmi_dir / "cand_df.pkl")
    smiles_path = args.casmi_dir / "all_smiles.txt"
    model_adducts = {p.name for p in args.model_root.iterdir() if p.is_dir()}
    supported = spec[spec["prec_type"].astype(str).isin(model_adducts)].reset_index(drop=True)
    unsupported = spec[~spec["prec_type"].astype(str).isin(model_adducts)].reset_index(drop=True)

    grouped = {int(k): v["candidate_mol_id"].astype(int).tolist() for k, v in cand.groupby("query_mol_id", sort=False)}
    start = max(0, int(args.query_start))
    stop = None if args.query_limit <= 0 else start + int(args.query_limit)
    selected = supported.iloc[start:stop].copy()

    selected_by_query: dict[int, list[int]] = {}
    original_positions: dict[int, int | None] = {}
    needed: set[int] = set()
    for _, row in selected.iterrows():
        query_mol_id = int(row["mol_id"])
        full_candidates = grouped.get(query_mol_id, [])
        try:
            original_positions[query_mol_id] = full_candidates.index(query_mol_id) + 1
        except ValueError:
            original_positions[query_mol_id] = None
        limited = full_candidates[: max(0, int(args.candidate_limit))]
        if args.candidate_pool_policy == "first_n_plus_true" and query_mol_id not in limited:
            limited = [query_mol_id] + limited
        selected_by_query[query_mol_id] = limited
        needed.update(limited)
        needed.add(query_mol_id)

    id_to_smiles = parse_all_smiles(smiles_path, needed)
    tasks: list[dict[str, Any]] = []
    missing_smiles = 0
    for _, row in selected.iterrows():
        query_mol_id = int(row["mol_id"])
        candidates: list[tuple[int, str]] = []
        for mol_id in selected_by_query.get(query_mol_id, []):
            smiles = id_to_smiles.get(int(mol_id))
            if not smiles:
                missing_smiles += 1
                continue
            candidates.append((int(mol_id), smiles))
        tasks.append(
            {
                "spec_id": str(row["spec_id"]),
                "query_mol_id": query_mol_id,
                "true_smiles": id_to_smiles.get(query_mol_id, str(row.get("smiles", ""))),
                "adduct": str(row["prec_type"]),
                "precursor_mz": safe_float(row.get("prec_mz")),
                "peaks": [(float(mz), float(intensity)) for mz, intensity in row.get("peaks", [])],
                "candidates": candidates,
                "candidate_count": len(candidates),
                "original_true_candidate_position": original_positions.get(query_mol_id),
                "cfmid": str(args.cfmid),
                "model_root": str(args.model_root),
                "work_dir": str(args.outdir / "work" / f"query_{row['spec_id']}"),
                "timeout_seconds": args.timeout_seconds,
                "ppm_mass_tol": args.ppm_mass_tol,
                "abs_mass_tol": args.abs_mass_tol,
                "prob_thresh_for_prune": args.prob_thresh_for_prune,
                "score_type": args.score_type,
                "apply_postprocessing": args.apply_postprocessing,
                "candidate_limit": args.candidate_limit,
                "candidate_pool_policy": args.candidate_pool_policy,
                "resume": args.resume,
            }
        )
    audit = {
        "stage": "casmi2022_cfmid_native_subset_v1",
        "status": "subset_runner_prepared",
        "casmi_dir": str(args.casmi_dir),
        "cfmid": str(args.cfmid),
        "model_root": str(args.model_root),
        "model_adducts": sorted(model_adducts),
        "total_casmi_queries": int(len(spec)),
        "native_supported_queries": int(len(supported)),
        "native_unsupported_queries": int(len(unsupported)),
        "native_unsupported_adduct_counts": unsupported["prec_type"].value_counts().to_dict(),
        "candidate_limit": int(args.candidate_limit),
        "candidate_pool_policy": args.candidate_pool_policy,
        "query_start": int(args.query_start),
        "query_limit": int(args.query_limit),
        "selected_query_count": int(len(tasks)),
        "missing_candidate_smiles": int(missing_smiles),
        "spec_df_sha256": sha256_file(args.casmi_dir / "spec_df.pkl"),
        "cand_df_sha256": sha256_file(args.casmi_dir / "cand_df.pkl"),
        "all_smiles_sha256": sha256_file(smiles_path),
        "claim_guardrail": "This is a native CFM-ID subset/candidate-limited benchmark. It is not a complete CASMI2022 CFM-ID result and must not be used as full-SOTA evidence.",
    }
    return tasks, audit


def summarize(results: list[dict[str, Any]], audit: dict[str, Any], outdir: Path) -> None:
    pred_rows: list[dict[str, Any]] = []
    query_rows: list[dict[str, Any]] = []
    command_rows: list[dict[str, Any]] = []
    for result in results:
        task = result["query"]
        true_id = int(task["query_mol_id"])
        status = result["status"]
        parsed = result.get("parsed_rows", [])
        true_rank = np.nan
        for row in parsed:
            is_correct = int(row["candidate_mol_id"]) == true_id
            if is_correct:
                true_rank = float(row["rank"])
            pred_rows.append(
                {
                    "dataset": "CASMI2022",
                    "model": "CFM-ID",
                    "status": status,
                    "native_or_fallback": "native_cfmid_subset_candidate_limited",
                    "spectrum_id": task["spec_id"],
                    "query_id": task["spec_id"],
                    "true_candidate_id": f"CASMI_MOL_{true_id}",
                    "candidate_id": f"CASMI_MOL_{row['candidate_mol_id']}",
                    "candidate_mol_id": row["candidate_mol_id"],
                    "candidate_smiles": row["smiles"],
                    "score": row["score"],
                    "rank": row["rank"],
                    "is_correct": is_correct,
                    "adduct": task["adduct"],
                    "precursor_mz": task["precursor_mz"],
                    "candidate_limit": task["candidate_limit"],
                    "candidate_pool_policy": task["candidate_pool_policy"],
                    "candidate_count": task["candidate_count"],
                    "original_true_candidate_position": task["original_true_candidate_position"],
                }
            )
        finite_rank = not pd.isna(true_rank)
        query_rows.append(
            {
                "dataset": "CASMI2022",
                "model": "CFM-ID",
                "status": status,
                "native_or_fallback": "native_cfmid_subset_candidate_limited",
                "spectrum_id": task["spec_id"],
                "query_id": task["spec_id"],
                "true_candidate_id": f"CASMI_MOL_{true_id}",
                "adduct": task["adduct"],
                "candidate_limit": task["candidate_limit"],
                "candidate_pool_policy": task["candidate_pool_policy"],
                "candidate_count": task["candidate_count"],
                "original_true_candidate_position": task["original_true_candidate_position"],
                "true_rank": true_rank,
                "top1_correct": bool(finite_rank and true_rank == 1),
                "top5_correct": bool(finite_rank and true_rank <= 5),
                "top10_correct": bool(finite_rank and true_rank <= 10),
                "reciprocal_rank": 0.0 if not finite_rank else 1.0 / true_rank,
                "elapsed_seconds": result["elapsed_seconds"],
                "returncode": result["returncode"],
                "output_file": result["output_file"],
                "stdout_file": result["stdout_file"],
                "stderr_file": result["stderr_file"],
            }
        )
        command_rows.append({"query_id": task["spec_id"], "status": status, "command": result.get("command", "")})

    pred_df = pd.DataFrame(pred_rows)
    query_df = pd.DataFrame(query_rows)
    completed = query_df[query_df["status"].isin(["completed", "completed_cached"])].copy()
    rank_valid = completed[pd.to_numeric(completed["true_rank"], errors="coerce").notna()].copy()
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID",
        "status": "completed_subset" if len(completed) == len(query_df) and len(query_df) else "partial_subset",
        "native_or_fallback": "native_cfmid_subset_candidate_limited",
        "n_queries_selected": int(len(query_df)),
        "n_queries_completed": int(len(completed)),
        "n_rank_valid_queries": int(len(rank_valid)),
        "candidate_limit": audit["candidate_limit"],
        "candidate_pool_policy": audit["candidate_pool_policy"],
        "top1_accuracy": float(rank_valid["top1_correct"].mean()) if not rank_valid.empty else np.nan,
        "top5_accuracy": float(rank_valid["top5_correct"].mean()) if not rank_valid.empty else np.nan,
        "top10_accuracy": float(rank_valid["top10_correct"].mean()) if not rank_valid.empty else np.nan,
        "mean_reciprocal_rank": float(rank_valid["reciprocal_rank"].mean()) if not rank_valid.empty else np.nan,
        "median_true_rank": float(pd.to_numeric(rank_valid["true_rank"], errors="coerce").median()) if not rank_valid.empty else np.nan,
        "mean_elapsed_seconds_completed": float(completed["elapsed_seconds"].mean()) if not completed.empty else np.nan,
        "total_elapsed_seconds_completed": float(completed["elapsed_seconds"].sum()) if not completed.empty else np.nan,
        "claim_guardrail": audit["claim_guardrail"],
    }
    audit.update(
        {
            "status": summary["status"],
            "n_queries_completed": summary["n_queries_completed"],
            "n_rank_valid_queries": summary["n_rank_valid_queries"],
            "top1_accuracy": summary["top1_accuracy"],
            "top5_accuracy": summary["top5_accuracy"],
            "top10_accuracy": summary["top10_accuracy"],
            "mean_reciprocal_rank": summary["mean_reciprocal_rank"],
        }
    )

    outdir.mkdir(parents=True, exist_ok=True)
    pred_df.to_csv(outdir / "casmi2022_cfmid_native_subset_predictions.csv", index=False)
    query_df.to_csv(outdir / "casmi2022_cfmid_native_subset_query_results.csv", index=False)
    pd.DataFrame([summary]).to_csv(outdir / "casmi2022_cfmid_native_subset_summary.csv", index=False)
    pd.DataFrame(command_rows).to_csv(outdir / "cfmid_commands.csv", index=False)
    write_json(outdir / "audit_summary.json", audit)

    mirror = ROOT / "results" / "predictions" / "casmi2022_cfmid_native_subset_predictions.csv"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    pred_df.to_csv(mirror, index=False)

    report = [
        "# CASMI2022 Native CFM-ID Subset Benchmark",
        "",
        f"Status: `{summary['status']}`",
        "",
        audit["claim_guardrail"],
        "",
        "## Configuration",
        "",
        f"- CFM-ID binary: `{audit['cfmid']}`",
        f"- Supported native adducts in model directory: `{', '.join(audit['model_adducts'])}`",
        f"- Unsupported CASMI queries: `{audit['native_unsupported_queries']}`; counts: `{audit['native_unsupported_adduct_counts']}`",
        f"- Candidate limit: `{audit['candidate_limit']}`",
        f"- Candidate-pool policy: `{audit['candidate_pool_policy']}`",
        f"- Selected queries: `{summary['n_queries_selected']}`",
        f"- Completed queries: `{summary['n_queries_completed']}`",
        "",
        "## Subset Metrics",
        "",
        pd.DataFrame([summary]).to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "These metrics are useful for runtime and integration validation only. Because the candidate pool is limited and injects the true structure when it is outside the first N CASMI candidates, the table is not comparable to full-candidate CASMI rankings.",
        "",
    ]
    (outdir / "casmi2022_cfmid_native_subset_report.md").write_text("\n".join(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--casmi-dir", type=Path, default=DEFAULT_CASMI_DIR)
    parser.add_argument("--cfmid", type=Path, default=DEFAULT_CFMID)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "casmi2022_cfmid_native_subset_v1")
    parser.add_argument("--query-start", type=int, default=0)
    parser.add_argument("--query-limit", type=int, default=5)
    parser.add_argument("--candidate-limit", type=int, default=10)
    parser.add_argument("--candidate-pool-policy", choices=["first_n_plus_true", "first_n_only"], default="first_n_plus_true")
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--ppm-mass-tol", type=float, default=10)
    parser.add_argument("--abs-mass-tol", type=float, default=0.01)
    parser.add_argument("--prob-thresh-for-prune", type=float, default=0.001)
    parser.add_argument("--score-type", default="DotProduct")
    parser.add_argument("--apply-postprocessing", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    tasks, audit = build_tasks(args)
    if not tasks:
        audit["status"] = "no_selected_queries"
        write_json(args.outdir / "audit_summary.json", audit)
        return
    results: list[dict[str, Any]] = []
    with futures.ThreadPoolExecutor(max_workers=max(1, int(args.max_workers))) as executor:
        future_map = {executor.submit(run_query, task): task for task in tasks}
        for future in futures.as_completed(future_map):
            result = future.result()
            results.append(result)
            task = result["query"]
            print(
                f"query={task['spec_id']} status={result['status']} "
                f"elapsed={result['elapsed_seconds']:.1f}s candidates={task['candidate_count']}",
                flush=True,
            )
    results.sort(key=lambda item: int(item["query"]["spec_id"]))
    summarize(results, audit, args.outdir)


if __name__ == "__main__":
    main()
