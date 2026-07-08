#!/usr/bin/env python3
"""Merge CFM-ID + MS2DeepScore full-supported hybrid shard outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = ROOT / "results" / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_v1"


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
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
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
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(ROOT / "data" / "proc" / "casmi_2022" / "spec_df.pkl")
    supported = spec[spec["prec_type"].astype(str).eq("[M+H]+")].copy()
    expected_queries = int(len(supported))

    query_paths = sorted(args.outdir.glob("shard_*/casmi2022_cfmid_ms2deepscore_full_supported_hybrid_query_results.csv"))
    top_paths = sorted(args.outdir.glob("shard_*/casmi2022_cfmid_ms2deepscore_full_supported_hybrid_top_predictions.csv"))
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
        qdf.to_csv(args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_query_results.csv", index=False)
    if not top_df.empty:
        top_df["_query_sort"] = pd.to_numeric(top_df["query_id"], errors="coerce")
        top_df = top_df.sort_values(["_query_sort", "rank"]).drop(columns=["_query_sort"], errors="ignore")
        top_df.to_csv(args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_top_predictions.csv", index=False)

    completed = qdf[qdf["status"].astype(str).eq("completed")].copy() if not qdf.empty else pd.DataFrame()
    rank_valid = completed[pd.to_numeric(completed["true_rank"], errors="coerce").notna()].copy() if not completed.empty else pd.DataFrame()
    status = "completed_full_supported_hybrid" if len(rank_valid) == expected_queries and expected_queries else "partial_full_supported_hybrid"
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID + MS2DeepScore full-supported hybrid",
        "status": status,
        "native_or_fallback": "cfmid_generated_spectra_ms2deepscore_similarity_full_supported_hybrid",
        "n_supported_queries": expected_queries,
        "n_queries_completed": int(len(completed)),
        "n_rank_valid_queries": int(len(rank_valid)),
        "candidate_limit": -1,
        "candidate_pool_policy": "full_supported_query_candidate_set",
        "top1_accuracy": float(rank_valid["top1_correct"].mean()) if not rank_valid.empty else np.nan,
        "top5_accuracy": float(rank_valid["top5_correct"].mean()) if not rank_valid.empty else np.nan,
        "top10_accuracy": float(rank_valid["top10_correct"].mean()) if not rank_valid.empty else np.nan,
        "mean_reciprocal_rank": float(rank_valid["reciprocal_rank"].mean()) if not rank_valid.empty else np.nan,
        "median_true_rank": float(pd.to_numeric(rank_valid["true_rank"], errors="coerce").median()) if not rank_valid.empty else np.nan,
        "median_candidate_count": float(pd.to_numeric(rank_valid["candidate_count"], errors="coerce").median()) if not rank_valid.empty else np.nan,
        "total_candidate_rows_scored": int(pd.to_numeric(rank_valid["candidate_spectra_count"], errors="coerce").sum()) if not rank_valid.empty else 0,
        "total_missing_candidate_spectra": int(pd.to_numeric(qdf.get("missing_candidate_spectra", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not qdf.empty else 0,
        "total_nan_scores": int(pd.to_numeric(qdf.get("nan_score_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not qdf.empty else 0,
        "top_predictions_per_query_stored": 100,
        "claim_guardrail": "Candidate spectra are generated by CFM-ID, so this is a full-supported CFM-ID + MS2DeepScore hybrid benchmark, not native MS2DeepScore.",
    }
    pd.DataFrame([summary]).to_csv(args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_summary.csv", index=False)
    audit = {
        "stage": "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_v1",
        "status": status,
        "shard_query_files": [str(path) for path in query_paths],
        "shard_top_prediction_files": [str(path) for path in top_paths],
        "query_results": "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_query_results.csv",
        "top_predictions": "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_top_predictions.csv",
        **summary,
    }
    write_json(args.outdir / "audit_summary.json", audit)
    report = [
        "# CASMI2022 CFM-ID + MS2DeepScore Full-Supported Hybrid",
        "",
        summary["claim_guardrail"],
        "",
        "## Summary",
        "",
        "\n".join(f"- `{key}`: `{value}`" for key, value in summary.items()),
        "",
    ]
    (args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
