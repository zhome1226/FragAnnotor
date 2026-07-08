#!/usr/bin/env python3
"""Merge harmonized SOTA query-shard outputs for ICEBERG/MassFormer."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = ROOT / "results" / "harmonized_sota_candidate_reruns_v1"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


def read_csvs(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if not path.exists():
            continue
        try:
            frames.append(pd.read_csv(path))
        except pd.errors.EmptyDataError:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["iceberg", "massformer"], required=True)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--expected-queries", type=int, default=0)
    parser.add_argument("--candidate-limit", type=int, default=0)
    parser.add_argument("--top-predictions", type=int, default=100)
    parser.add_argument("--score-name", default="binned_cosine_1Da")
    args = parser.parse_args()

    model_outdir = args.outdir / args.model
    model_outdir.mkdir(parents=True, exist_ok=True)
    query_paths = sorted(model_outdir.glob("shard_*/casmi2022_*_harmonized_query_results.csv"))
    top_paths = sorted(model_outdir.glob("shard_*/casmi2022_*_harmonized_top_predictions.csv"))
    direct_query = model_outdir / f"casmi2022_{args.model}_harmonized_query_results.csv"
    direct_top = model_outdir / f"casmi2022_{args.model}_harmonized_top_predictions.csv"
    if direct_query.exists():
        query_paths.append(direct_query)
    if direct_top.exists():
        top_paths.append(direct_top)

    qdf = read_csvs(query_paths)
    top_df = read_csvs(top_paths)
    if not qdf.empty:
        qdf["_query_sort"] = pd.to_numeric(qdf["query_id"], errors="coerce")
        qdf["_status_priority"] = qdf["status"].astype(str).eq("completed").astype(int)
        qdf = (
            qdf.sort_values(["_query_sort", "_status_priority"])
            .drop_duplicates(subset=["query_id"], keep="last")
            .drop(columns=["_query_sort", "_status_priority"], errors="ignore")
        )
        qdf.to_csv(direct_query, index=False)
    if not top_df.empty:
        top_df["_query_sort"] = pd.to_numeric(top_df["query_id"], errors="coerce")
        top_df = top_df.sort_values(["_query_sort", "rank"]).drop(columns=["_query_sort"], errors="ignore")
        top_df.to_csv(direct_top, index=False)

    completed = qdf[qdf["status"].astype(str).eq("completed")].copy() if not qdf.empty else pd.DataFrame()
    rank_valid = completed[pd.to_numeric(completed.get("true_rank", pd.Series(dtype=float)), errors="coerce").notna()].copy() if not completed.empty else pd.DataFrame()
    expected_queries = int(args.expected_queries)
    if expected_queries <= 0 and not qdf.empty:
        expected_queries = int(qdf["query_id"].nunique())
    candidate_limit = int(args.candidate_limit) if args.candidate_limit > 0 else -1
    full_complete = candidate_limit == -1 and expected_queries > 0 and len(rank_valid) >= expected_queries
    status = "completed_harmonized_candidate_rerun" if full_complete else "partial_harmonized_candidate_rerun"
    summary = {
        "dataset": "CASMI2022",
        "model": args.model,
        "status": status,
        "n_expected_queries": expected_queries,
        "n_queries_completed": int(len(completed)),
        "n_rank_valid_queries": int(len(rank_valid)),
        "candidate_limit": candidate_limit,
        "candidate_pool_policy": "full_query_candidate_set" if candidate_limit == -1 else "debug_candidate_limited",
        "score_name": args.score_name,
        "top1_accuracy": float(rank_valid["top1_correct"].mean()) if not rank_valid.empty else np.nan,
        "top5_accuracy": float(rank_valid["top5_correct"].mean()) if not rank_valid.empty else np.nan,
        "top10_accuracy": float(rank_valid["top10_correct"].mean()) if not rank_valid.empty else np.nan,
        "mean_reciprocal_rank": float(rank_valid["reciprocal_rank"].mean()) if not rank_valid.empty else np.nan,
        "mean_top1_tanimoto": float(pd.to_numeric(rank_valid.get("top1_tanimoto", pd.Series(dtype=float)), errors="coerce").mean()) if not rank_valid.empty else np.nan,
        "formula_accuracy": float(rank_valid["formula_accuracy"].astype(bool).mean()) if "formula_accuracy" in rank_valid and not rank_valid.empty else np.nan,
        "total_candidate_rows_scored": int(pd.to_numeric(rank_valid.get("predicted_spectrum_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not rank_valid.empty else 0,
        "total_failed_predictions": int(pd.to_numeric(qdf.get("failed_prediction_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not qdf.empty else 0,
        "top_predictions_per_query_stored": int(args.top_predictions),
        "claim_guardrail": "This is a harmonized direct rerun only when candidate_limit == -1 and status == completed_harmonized_candidate_rerun.",
    }
    pd.DataFrame([summary]).to_csv(model_outdir / f"casmi2022_{args.model}_harmonized_summary.csv", index=False)
    audit = {
        "stage": "harmonized_sota_candidate_reruns_v1",
        "model": args.model,
        "query_results": direct_query.name,
        "top_predictions": direct_top.name,
        "shard_query_files": [str(path) for path in query_paths],
        "shard_top_prediction_files": [str(path) for path in top_paths],
        **summary,
    }
    write_json(model_outdir / "audit_summary.json", audit)
    report = [
        f"# CASMI2022 {args.model} Harmonized Candidate-Set Rerun",
        "",
        summary["claim_guardrail"],
        "",
        "## Summary",
        "",
        "\n".join(f"- `{key}`: `{value}`" for key, value in summary.items()),
        "",
    ]
    (model_outdir / f"casmi2022_{args.model}_harmonized_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
