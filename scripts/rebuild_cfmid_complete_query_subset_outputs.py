#!/usr/bin/env python3
"""Rebuild native CFM-ID complete-query subset outputs from local work dirs.

Single-query CFM-ID runs overwrite the subset CSVs by design. This script scans
the ignored runtime work directories and rebuilds the reportable subset from
queries where the full candidate set has been ranked. Partial queries are kept
in the audit but excluded from Top-k/MRR.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from run_cfmid_precomputed_complete_query_subset import build_supported_query_table
from run_cfmid_precomputed_smoke import parse_ranked


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
DEFAULT_MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
DEFAULT_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_complete_query_subset_v1"


def read_candidate_smiles(path: Path) -> dict[int, str]:
    rows: dict[int, str] = {}
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            mol_id_text, _, smiles = text.partition(" ")
            try:
                mol_id = int(mol_id_text)
            except ValueError:
                continue
            if smiles:
                rows[mol_id] = smiles
    return rows


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="ignore") as handle:
        return sum(1 for line in handle if line.strip())


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--casmi-dir", type=Path, default=CASMI_DIR)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    query_table = build_supported_query_table(args.casmi_dir, args.model_root)
    query_meta = {str(row["spec_id"]): row.to_dict() for _, row in query_table.iterrows()}

    query_rows: list[dict[str, Any]] = []
    pred_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    partial_rows: list[dict[str, Any]] = []

    for work_dir in sorted((args.outdir / "work").glob("query_*"), key=lambda p: int(p.name.split("_", 1)[1])):
        query_id = work_dir.name.split("_", 1)[1]
        meta = query_meta.get(query_id)
        if not meta:
            continue
        candidate_smiles = read_candidate_smiles(work_dir / "candidate_smiles.txt")
        ranked_path = work_dir / f"cfmid_precomputed_ranked_{query_id}.txt"
        ranked = parse_ranked(ranked_path)
        candidate_count = len(candidate_smiles)
        triples_count = count_lines(work_dir / "candidate_triples_plain.txt")
        query_mol_id = int(meta["query_mol_id"])
        true_rank = np.nan
        for item in ranked:
            if int(item["candidate_mol_id"]) == query_mol_id:
                true_rank = float(item["rank"])
                break
        status = "completed_cached" if candidate_count and len(ranked) == candidate_count and not pd.isna(true_rank) else "partial_or_unranked"
        base_query = {
            "dataset": "CASMI2022",
            "model": "CFM-ID",
            "status": status,
            "native_or_fallback": "native_cfmid_precomputed_complete_query_subset",
            "query_id": query_id,
            "spectrum_id": query_id,
            "true_candidate_id": f"CASMI_MOL_{query_mol_id}",
            "query_mol_id": query_mol_id,
            "adduct": str(meta["adduct"]),
            "candidate_count": candidate_count,
            "ranked_rows": len(ranked),
            "predicted_spectrum_ids": triples_count,
            "missing_smiles": 0,
            "missing_candidate_spectra": max(0, candidate_count - triples_count),
            "true_rank": true_rank,
            "top1_correct": bool(not pd.isna(true_rank) and true_rank == 1),
            "top5_correct": bool(not pd.isna(true_rank) and true_rank <= 5),
            "top10_correct": bool(not pd.isna(true_rank) and true_rank <= 10),
            "reciprocal_rank": 0.0 if pd.isna(true_rank) else 1.0 / float(true_rank),
            "cfm_predict_seconds": np.nan,
            "cfm_id_precomputed_seconds": np.nan,
            "rank_output_file": str(ranked_path),
        }
        if status == "completed_cached":
            query_rows.append(base_query)
            selected_rows.append(
                {
                    "supported_index": int(meta["supported_index"]),
                    "spec_row_index": int(meta["spec_row_index"]),
                    "spec_id": query_id,
                    "query_mol_id": query_mol_id,
                    "adduct": str(meta["adduct"]),
                    "precursor_mz": float(meta["precursor_mz"]),
                    "candidate_count": candidate_count,
                }
            )
            for item in ranked:
                candidate_mol_id = int(item["candidate_mol_id"])
                is_correct = candidate_mol_id == query_mol_id
                pred_rows.append(
                    {
                        "dataset": "CASMI2022",
                        "model": "CFM-ID",
                        "status": status,
                        "native_or_fallback": "native_cfmid_precomputed_complete_query_subset",
                        "query_id": query_id,
                        "spectrum_id": query_id,
                        "true_candidate_id": f"CASMI_MOL_{query_mol_id}",
                        "candidate_id": f"CASMI_MOL_{candidate_mol_id}",
                        "candidate_mol_id": candidate_mol_id,
                        "score": item["score"],
                        "rank": item["rank"],
                        "is_correct": is_correct,
                        "adduct": str(meta["adduct"]),
                        "candidate_count": candidate_count,
                    }
                )
        elif candidate_count:
            partial_rows.append(base_query)

    query_rows = sorted(query_rows, key=lambda row: int(row["query_id"]))
    pred_rows = sorted(pred_rows, key=lambda row: (int(row["query_id"]), int(row["rank"])))
    selected_rows = sorted(selected_rows, key=lambda row: int(row["candidate_count"]))
    partial_rows = sorted(partial_rows, key=lambda row: int(row["query_id"]))

    query_df = pd.DataFrame(query_rows)
    pred_df = pd.DataFrame(pred_rows)
    query_df.to_csv(args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_query_results.csv", index=False)
    pred_df.to_csv(args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_predictions.csv", index=False)
    mirror_dir = ROOT / "results" / "predictions"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    pred_df.to_csv(mirror_dir / "casmi2022_cfmid_native_precomputed_complete_query_subset_predictions.csv", index=False)
    pd.DataFrame(selected_rows).to_csv(args.outdir / "selected_complete_query_manifest.csv", index=False)
    pd.DataFrame(partial_rows).to_csv(args.outdir / "partial_complete_query_attempts.csv", index=False)

    completed = query_df.copy()
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID complete-query subset",
        "status": "completed_subset" if not completed.empty else "missing_completed_subset",
        "native_or_fallback": "native_cfmid_precomputed_complete_query_subset",
        "n_queries": int(len(completed)),
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
    command_rows = [
        {
            "query_id": row["query_id"],
            "phase": "rebuild_outputs",
            "status": "completed_from_existing_ranked_work_dir",
            "command": "python3 scripts/rebuild_cfmid_complete_query_subset_outputs.py",
            "rank_output_file": row["rank_output_file"],
        }
        for row in query_rows
    ]
    write_csv(
        args.outdir / "cfmid_precomputed_complete_query_subset_commands.csv",
        command_rows,
        ["query_id", "phase", "status", "command", "rank_output_file"],
    )
    audit = {
        "stage": "casmi2022_cfmid_native_precomputed_complete_query_subset_v1",
        "status": summary["status"],
        "summary": summary,
        "selected_queries": query_rows,
        "partial_queries_excluded_from_metrics": partial_rows,
        "claim_guardrail": summary["claim_guardrail"],
    }
    (args.outdir / "audit_summary.json").write_text(json.dumps(json_safe(audit), indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# CASMI2022 Native CFM-ID Precomputed Complete-Query Subset",
        "",
        summary["claim_guardrail"],
        "",
        "## Summary",
        "",
        pd.DataFrame([summary]).to_markdown(index=False),
        "",
        "## Query Results Included In Metrics",
        "",
        query_df.to_markdown(index=False),
        "",
    ]
    if partial_rows:
        report.extend(
            [
                "## Partial Attempts Excluded From Metrics",
                "",
                pd.DataFrame(partial_rows).to_markdown(index=False),
                "",
            ]
        )
    (args.outdir / "casmi2022_cfmid_native_precomputed_complete_query_subset_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
