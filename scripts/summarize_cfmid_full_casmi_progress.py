#!/usr/bin/env python3
"""Summarize progress for the full native CFM-ID CASMI run."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "results" / "cfmid_full_casmi_run_manifest_v1"
FULL_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_full_supported_v1"


def parse_output(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split(maxsplit=3)
            if len(parts) < 4:
                continue
            try:
                rows.append({"rank": int(parts[0]), "score": float(parts[1]), "candidate_mol_id": int(parts[2]), "smiles": parts[3]})
            except ValueError:
                continue
    return rows


def json_safe(value):
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def main() -> None:
    manifest = pd.read_csv(MANIFEST_DIR / "cfmid_full_supported_query_manifest.csv")
    progress_rows = []
    pred_rows = []
    query_rows = []
    for _, row in manifest.iterrows():
        path = Path(row["full_output_file"])
        parsed = parse_output(path)
        expected = int(row["candidate_count"])
        true_mol_id = int(row["query_mol_id"])
        complete = len(parsed) == expected and expected > 0
        true_rank = np.nan
        for item in parsed:
            is_correct = item["candidate_mol_id"] == true_mol_id
            if is_correct:
                true_rank = float(item["rank"])
            pred_rows.append(
                {
                    "dataset": "CASMI2022",
                    "model": "CFM-ID",
                    "status": "completed" if complete else "partial_or_missing",
                    "native_or_fallback": "native_cfmid_full_supported_queries",
                    "query_id": str(row["spec_id"]),
                    "spectrum_id": str(row["spec_id"]),
                    "true_candidate_id": f"CASMI_MOL_{true_mol_id}",
                    "candidate_id": f"CASMI_MOL_{item['candidate_mol_id']}",
                    "candidate_mol_id": item["candidate_mol_id"],
                    "score": item["score"],
                    "rank": item["rank"],
                    "is_correct": is_correct,
                    "adduct": row["adduct"],
                    "candidate_count": expected,
                }
            )
        finite = not pd.isna(true_rank)
        query_rows.append(
            {
                "dataset": "CASMI2022",
                "model": "CFM-ID",
                "status": "completed" if complete else "partial_or_missing",
                "native_or_fallback": "native_cfmid_full_supported_queries",
                "query_id": str(row["spec_id"]),
                "spectrum_id": str(row["spec_id"]),
                "true_candidate_id": f"CASMI_MOL_{true_mol_id}",
                "adduct": row["adduct"],
                "candidate_count": expected,
                "observed_rows": len(parsed),
                "true_rank": true_rank,
                "top1_correct": bool(finite and true_rank == 1),
                "top5_correct": bool(finite and true_rank <= 5),
                "top10_correct": bool(finite and true_rank <= 10),
                "reciprocal_rank": 0.0 if not finite else 1.0 / true_rank,
            }
        )
        progress_rows.append(
            {
                "spec_id": str(row["spec_id"]),
                "query_mol_id": true_mol_id,
                "adduct": row["adduct"],
                "expected_candidate_rows": expected,
                "observed_rows": len(parsed),
                "complete": complete,
                "output_file": str(path),
            }
        )
    progress = pd.DataFrame(progress_rows)
    qdf = pd.DataFrame(query_rows)
    pred = pd.DataFrame(pred_rows)
    FULL_OUTDIR.mkdir(parents=True, exist_ok=True)
    progress.to_csv(FULL_OUTDIR / "cfmid_full_progress.csv", index=False)
    qdf.to_csv(FULL_OUTDIR / "casmi2022_cfmid_native_full_supported_query_results.csv", index=False)
    if not pred.empty:
        pred.to_csv(FULL_OUTDIR / "casmi2022_cfmid_native_full_supported_predictions.csv", index=False)
    completed = qdf[qdf["status"].eq("completed")].copy()
    all_complete = len(completed) == len(qdf) and len(qdf) > 0
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID",
        "status": "completed_full_supported" if all_complete else "incomplete_full_supported",
        "native_or_fallback": "native_cfmid_full_supported_queries",
        "n_supported_queries": int(len(qdf)),
        "n_completed_queries": int(len(completed)),
        "completion_fraction": float(len(completed) / len(qdf)) if len(qdf) else 0.0,
        "top1_accuracy": float(completed["top1_correct"].mean()) if all_complete else np.nan,
        "top5_accuracy": float(completed["top5_correct"].mean()) if all_complete else np.nan,
        "top10_accuracy": float(completed["top10_correct"].mean()) if all_complete else np.nan,
        "mean_reciprocal_rank": float(completed["reciprocal_rank"].mean()) if all_complete else np.nan,
        "claim_guardrail": "Do not report full native CFM-ID metrics until status is completed_full_supported; [M+Na]+ CASMI queries remain unsupported by the local cfmid4 model directory.",
    }
    pd.DataFrame([summary]).to_csv(FULL_OUTDIR / "casmi2022_cfmid_native_full_supported_summary.csv", index=False)
    (FULL_OUTDIR / "audit_summary.json").write_text(json.dumps(json_safe(summary), indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
