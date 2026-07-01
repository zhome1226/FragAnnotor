#!/usr/bin/env python3
"""Summarize progress for the precomputed full native CFM-ID CASMI run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "results" / "cfmid_precomputed_full_casmi_manifest_v1"
RUN_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def read_csvs(pattern: str) -> pd.DataFrame:
    frames = []
    for path in sorted(RUN_OUTDIR.glob(pattern)):
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        df["source_file"] = str(path)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def adduct_slug(adduct: Any) -> str:
    return str(adduct).replace("[", "").replace("]", "").replace("+", "plus").replace("-", "minus")


def infer_status_slug(row: pd.Series) -> str:
    if "adduct" in row and not pd.isna(row.get("adduct")) and str(row.get("adduct")):
        return adduct_slug(row.get("adduct"))
    for col in ["spectrum_file", "target_file", "source_file"]:
        text = str(row.get(col, ""))
        match = re.search(r"candidate_spectra_cache/([^/]+)/", text)
        if match:
            return match.group(1)
        match = re.search(r"candidate_spectrum_shards/([^/]+)/", text)
        if match:
            return match.group(1)
    return "unknown"


def completed_candidate_count(candidate_status: pd.DataFrame) -> tuple[int, int]:
    if candidate_status.empty:
        return 0, 0
    status = candidate_status.copy()
    if "candidate_mol_id" not in status.columns:
        return 0, 0
    status["candidate_key"] = status.apply(
        lambda row: f"{infer_status_slug(row)}:{str(row['candidate_mol_id'])}",
        axis=1,
    )
    completed = status[status["status"].astype(str).str.startswith(("completed", "imported"))].copy()
    failed = status[status["status"].astype(str).eq("failed")].copy()
    return int(completed["candidate_key"].nunique()), int(failed["candidate_key"].nunique())


def cached_candidate_count() -> int:
    """Count real cached CFM-ID candidate spectra.

    Some cache files are produced by long-running shard jobs whose status CSVs
    are intentionally ignored by Git. Counting the cache directory keeps the
    progress summary aligned with the actual resumable execution state.
    """

    cache_root = RUN_OUTDIR / "candidate_spectra_cache"
    if not cache_root.exists():
        return 0
    keys: set[str] = set()
    for slug_dir in cache_root.iterdir():
        if not slug_dir.is_dir():
            continue
        for path in slug_dir.glob("*.txt"):
            if path.stat().st_size <= 0:
                continue
            keys.add(f"{slug_dir.name}:{path.stem}")
    return len(keys)


def main() -> None:
    RUN_OUTDIR.mkdir(parents=True, exist_ok=True)
    query_manifest = pd.read_csv(MANIFEST_DIR / "cfmid_precomputed_supported_query_manifest.csv")
    candidate_shards = pd.read_csv(MANIFEST_DIR / "cfmid_precomputed_candidate_spectrum_shards.csv")
    query_shards = pd.read_csv(MANIFEST_DIR / "cfmid_precomputed_query_ranking_shards.csv")

    candidate_status = pd.concat(
        [
            read_csvs("candidate_spectrum_shards/*/shard_*_*/candidate_spectrum_status.csv"),
            read_csvs("complete_query_subset_cache_import_v1/complete_query_subset_cache_import.csv"),
        ],
        ignore_index=True,
    )
    query_results = read_csvs("query_shard_*_results.csv")
    predictions = read_csvs("query_shard_*_predictions.csv")

    candidate_completed_from_status, candidate_failed = completed_candidate_count(candidate_status)
    candidate_completed = max(candidate_completed_from_status, cached_candidate_count())
    query_completed = 0
    if not query_results.empty:
        query_completed = int(query_results["status"].astype(str).isin(["completed", "completed_cached"]).sum())

    expected_candidate_count = int(candidate_shards["candidate_count"].sum())
    expected_query_count = int(len(query_manifest))
    all_candidates_done = candidate_completed == expected_candidate_count and expected_candidate_count > 0
    all_queries_done = query_completed == expected_query_count and expected_query_count > 0
    all_complete = all_candidates_done and all_queries_done

    if not query_results.empty:
        query_results.to_csv(RUN_OUTDIR / "casmi2022_cfmid_native_precomputed_full_query_results.csv", index=False)
    else:
        pd.DataFrame(
            columns=[
                "dataset",
                "model",
                "status",
                "native_or_fallback",
                "query_id",
                "true_rank",
                "top1_correct",
                "top5_correct",
                "top10_correct",
                "reciprocal_rank",
            ]
        ).to_csv(RUN_OUTDIR / "casmi2022_cfmid_native_precomputed_full_query_results.csv", index=False)
    if not predictions.empty:
        predictions.to_csv(RUN_OUTDIR / "casmi2022_cfmid_native_precomputed_full_predictions.csv", index=False)

    completed = query_results[query_results["status"].astype(str).isin(["completed", "completed_cached"])].copy() if not query_results.empty else pd.DataFrame()
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID",
        "status": "completed_full_supported" if all_complete else "incomplete_full_supported",
        "native_or_fallback": "native_cfmid_precomputed_full_supported_queries",
        "n_supported_queries": expected_query_count,
        "n_completed_queries": query_completed,
        "query_completion_fraction": float(query_completed / expected_query_count) if expected_query_count else 0.0,
        "expected_unique_candidate_spectra": expected_candidate_count,
        "completed_candidate_spectra": candidate_completed,
        "failed_candidate_spectra": candidate_failed,
        "candidate_spectrum_completion_fraction": float(candidate_completed / expected_candidate_count) if expected_candidate_count else 0.0,
        "top1_accuracy": float(completed["top1_correct"].mean()) if all_complete else np.nan,
        "top5_accuracy": float(completed["top5_correct"].mean()) if all_complete else np.nan,
        "top10_accuracy": float(completed["top10_correct"].mean()) if all_complete else np.nan,
        "mean_reciprocal_rank": float(completed["reciprocal_rank"].mean()) if all_complete else np.nan,
        "claim_guardrail": "Do not report full native CFM-ID CASMI metrics until status is completed_full_supported; [M+Na]+ CASMI queries remain unsupported by the local cfmid4 model directory.",
    }
    pd.DataFrame([summary]).to_csv(RUN_OUTDIR / "casmi2022_cfmid_native_precomputed_full_summary.csv", index=False)
    (RUN_OUTDIR / "audit_summary.json").write_text(json.dumps(json_safe(summary), indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# CFM-ID Precomputed Full CASMI Progress",
        "",
        summary["claim_guardrail"],
        "",
        f"- Status: `{summary['status']}`",
        f"- Candidate spectra: `{candidate_completed}/{expected_candidate_count}` completed",
        f"- Supported query rankings: `{query_completed}/{expected_query_count}` completed",
        f"- Query-ranking shard count: `{len(query_shards)}`",
        f"- Candidate-spectrum shard count: `{len(candidate_shards)}`",
        "",
    ]
    (RUN_OUTDIR / "cfmid_precomputed_full_progress_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
