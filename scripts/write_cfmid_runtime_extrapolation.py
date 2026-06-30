#!/usr/bin/env python3
"""Estimate full CASMI CFM-ID runtime from observed subset timings."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "results" / "cfmid_full_runtime_extrapolation_v1"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    query = pd.read_csv(ROOT / "results" / "casmi2022_cfmid_native_subset_v1" / "casmi2022_cfmid_native_subset_query_results.csv")
    spec = pd.read_pickle(ROOT / "data" / "proc" / "casmi_2022" / "spec_df.pkl")
    cand = pd.read_pickle(ROOT / "data" / "proc" / "casmi_2022" / "cand_df.pkl")
    supported = spec[spec["prec_type"].isin(["[M+H]+", "[M-H]-"])].copy()
    counts = cand.groupby("query_mol_id")["candidate_mol_id"].size()
    supported_counts = [int(counts.get(int(mol_id), 0)) for mol_id in supported["mol_id"]]

    completed = query[query["status"].eq("completed")].copy()
    completed["seconds_per_candidate"] = completed["elapsed_seconds"] / completed["candidate_count"]
    mean_seconds_per_candidate = float(completed["seconds_per_candidate"].mean())
    median_seconds_per_candidate = float(completed["seconds_per_candidate"].median())
    total_supported_candidates = int(sum(supported_counts))
    estimates = pd.DataFrame(
        [
            {
                "basis": "mean_seconds_per_candidate_from_10_query_subset",
                "seconds_per_candidate": mean_seconds_per_candidate,
                "supported_queries": int(len(supported)),
                "unsupported_queries": int(len(spec) - len(supported)),
                "total_supported_candidate_rows": total_supported_candidates,
                "estimated_single_worker_seconds": mean_seconds_per_candidate * total_supported_candidates,
                "estimated_single_worker_hours": mean_seconds_per_candidate * total_supported_candidates / 3600,
                "estimated_16_worker_hours_ideal": mean_seconds_per_candidate * total_supported_candidates / 3600 / 16,
                "guardrail": "Back-of-envelope estimate only; CFM-ID runtime varies by molecule and this does not include [M+Na]+ unsupported queries.",
            },
            {
                "basis": "median_seconds_per_candidate_from_10_query_subset",
                "seconds_per_candidate": median_seconds_per_candidate,
                "supported_queries": int(len(supported)),
                "unsupported_queries": int(len(spec) - len(supported)),
                "total_supported_candidate_rows": total_supported_candidates,
                "estimated_single_worker_seconds": median_seconds_per_candidate * total_supported_candidates,
                "estimated_single_worker_hours": median_seconds_per_candidate * total_supported_candidates / 3600,
                "estimated_16_worker_hours_ideal": median_seconds_per_candidate * total_supported_candidates / 3600 / 16,
                "guardrail": "Back-of-envelope estimate only; CFM-ID runtime varies by molecule and this does not include [M+Na]+ unsupported queries.",
            },
        ]
    )
    estimates.to_csv(OUTDIR / "cfmid_full_runtime_extrapolation.csv", index=False)
    payload = {
        "stage": "cfmid_full_runtime_extrapolation_v1",
        "subset_queries": int(len(completed)),
        "subset_candidate_limit": int(completed["candidate_limit"].iloc[0]) if not completed.empty else None,
        "subset_pool_policy": str(completed["candidate_pool_policy"].iloc[0]) if not completed.empty else "",
        "mean_seconds_per_candidate": mean_seconds_per_candidate,
        "median_seconds_per_candidate": median_seconds_per_candidate,
        "supported_queries": int(len(supported)),
        "unsupported_queries": int(len(spec) - len(supported)),
        "total_supported_candidate_rows": total_supported_candidates,
        "full_native_cfmid_completed": False,
    }
    (OUTDIR / "audit_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# CFM-ID Full Runtime Extrapolation",
        "",
        "This estimate uses the observed 10-query native CFM-ID subset timings to explain why full CASMI candidate ranking remains a long-running job.",
        "",
        estimates.to_markdown(index=False),
        "",
        "The estimate is not a replacement for a full result. It supports the current reporting decision: full native CFM-ID CASMI Top-k metrics remain unavailable, while the candidate-limited subset demonstrates the native path.",
        "",
    ]
    (OUTDIR / "cfmid_full_runtime_extrapolation_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
