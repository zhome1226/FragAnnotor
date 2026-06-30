#!/usr/bin/env python3
"""Write CASMI gap and SOTA-claim guardrail artifacts.

This script is intentionally report-only. It reads the current benchmark
artifacts, summarizes the remaining native-baseline gaps, and records the
conditions required before stronger CASMI/SOTA claims can be made.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "results" / "casmi_remaining_gap_and_sota_guardrail_v1"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def scalar(df: pd.DataFrame, column: str, default: Any = None) -> Any:
    if df.empty or column not in df.columns:
        return default
    value = df.iloc[0][column]
    if pd.isna(value):
        return default
    return value


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    pairwise = read_csv(ROOT / "results" / "sota_pairwise_rank_comparison.csv")
    summary = read_csv(ROOT / "results" / "sota_comparison_summary.csv")
    neural = read_csv(ROOT / "results" / "casmi2022_fragannotor_trained_neural_v1" / "casmi2022_fragannotor_trained_neural_summary.csv")
    cfmid = read_json(ROOT / "results" / "native_cfmid_casmi" / "native_cfmid_runtime_audit.json")
    cfmid_full_manifest = read_json(ROOT / "results" / "cfmid_full_casmi_run_manifest_v1" / "audit_summary.json")
    cfmid_full_progress = read_json(ROOT / "results" / "casmi2022_cfmid_native_full_supported_v1" / "audit_summary.json")
    cfmid_precomputed_manifest = read_json(ROOT / "results" / "cfmid_precomputed_full_casmi_manifest_v1" / "audit_summary.json")
    cfmid_precomputed_progress = read_json(ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1" / "audit_summary.json")
    cfmid_complete_query_subset = read_json(
        ROOT
        / "results"
        / "casmi2022_cfmid_native_precomputed_complete_query_subset_v1"
        / "audit_summary.json"
    )
    cfmid_complete_query_expansion = read_json(
        ROOT
        / "results"
        / "casmi2022_cfmid_native_precomputed_complete_query_expansion_v1"
        / "audit_summary.json"
    )
    ms2_complete_query_hybrid = read_json(
        ROOT
        / "results"
        / "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_v1"
        / "audit_summary.json"
    )
    ms2 = read_json(ROOT / "results" / "native_ms2deepscore_casmi" / "native_ms2deepscore_audit.json")
    ms2_env = ms2.get("external_ms2deepscore_environment", {})
    ms2_resource = ms2.get("external_pretrained_model_cache", {})

    casmi_summary = summary[summary["dataset"].eq("CASMI2022")].copy() if not summary.empty else pd.DataFrame()
    frag = casmi_summary[casmi_summary["model"].eq("FragAnnotor")]
    sirius = casmi_summary[casmi_summary["model"].eq("SIRIUS")]
    rank_delta_cols = [
        "mean_rank_delta_baseline_minus_fragannotor",
        "median_rank_delta_baseline_minus_fragannotor",
    ]
    rank_delta_values = pd.Series(dtype=float)
    if not pairwise.empty:
        rank_delta_values = pd.concat(
            [pd.to_numeric(pairwise[col], errors="coerce") for col in rank_delta_cols if col in pairwise.columns],
            ignore_index=True,
        ).dropna()
    max_abs_rank_delta = float(rank_delta_values.abs().max()) if not rank_delta_values.empty else np.nan
    has_sentinel_scale_rank_delta = bool(not pd.isna(max_abs_rank_delta) and max_abs_rank_delta > 1_000_000)

    gap_rows = [
        {
            "gap": "CFM-ID complete CASMI native ranking",
            "status": cfmid_precomputed_progress.get("status", cfmid_full_progress.get("status", cfmid.get("status", "missing_audit"))),
            "resolved_now": False,
            "current_evidence": (
                "cfmid4-compatible native binary smoke passed; the original direct full-run manifest covers "
                f"{cfmid_full_manifest.get('supported_queries', 'unknown')} supported [M+H]+/[M-H]- CASMI queries, "
                f"{cfmid_full_manifest.get('total_supported_candidate_rows', 'unknown')} candidate rows, and "
                f"{cfmid_full_manifest.get('n_shards', 'unknown')} shards. A faster precomputed-spectrum pipeline is now "
                f"prepared for {cfmid_precomputed_manifest.get('supported_queries', 'unknown')} supported queries, "
                f"{cfmid_precomputed_manifest.get('supported_candidate_rows', 'unknown')} candidate rows, and "
                f"{cfmid_precomputed_progress.get('expected_unique_candidate_spectra', 'unknown')} unique candidate spectra; "
                f"currently cached spectra={cfmid_precomputed_progress.get('completed_candidate_spectra', 0)} and completed supported queries="
                f"{cfmid_precomputed_progress.get('n_completed_queries', 0)}. A separate complete-query subset is available with "
                f"{cfmid_complete_query_subset.get('summary', {}).get('n_queries_completed', 0)} selected query using its full candidate set; "
                f"subset MRR={cfmid_complete_query_subset.get('summary', {}).get('mean_reciprocal_rank', 'NA')}. "
                f"An attempted expansion query {cfmid_complete_query_expansion.get('query_id', 'NA')} reached "
                f"{cfmid_complete_query_expansion.get('predicted_spectrum_ids', 'NA')}/"
                f"{cfmid_complete_query_expansion.get('candidate_count', 'NA')} predicted spectra before timeout and is "
                f"not included in completed metrics. "
                f"Unsupported adduct counts: {cfmid_full_manifest.get('unsupported_adduct_counts', {})}."
            ),
            "required_to_close": "execute all CFM-ID precomputed candidate-spectrum shards, then all query-ranking shards, and obtain complete per-query CFM-ID candidate score tables for every supported query; add an [M+Na]+ model or report those CASMI rows as unsupported",
            "can_include_in_main_benchmark": False,
        },
        {
            "gap": "MS2DeepScore reasonable CASMI candidate-ranking benchmark",
            "status": "partial_complete_query_hybrid_subset_available_full_casmi_blocked",
            "resolved_now": False,
            "current_evidence": (
                "official dual-mode MS2DeepScore model cache recorded outside Git; CPU environment verified "
                f"with MS2DeepScore {ms2_env.get('ms2deepscore_version', 'unknown')}, MatchMS {ms2_env.get('matchms_version', 'unknown')}, "
                f"Torch {ms2_env.get('torch_version', 'unknown')}; required model files present="
                f"{ms2_resource.get('all_required_files_present', False)}. A candidate-limited CFM-ID + MS2DeepScore "
                "hybrid subset exists. A complete-query CFM-ID + MS2DeepScore hybrid subset is also available for the "
                f"selected low-candidate query with n_queries={ms2_complete_query_hybrid.get('n_queries', 'NA')}, "
                f"candidate policy={ms2_complete_query_hybrid.get('candidate_pool_policy', 'NA')}, "
                f"Top-5={ms2_complete_query_hybrid.get('top5_accuracy', 'NA')}, "
                f"MRR={ms2_complete_query_hybrid.get('mean_reciprocal_rank', 'NA')}. Full CASMI candidate ranking "
                "still lacks a complete per-candidate spectrum library."
            ),
            "required_to_close": "construct a complete CASMI per-candidate measured or generated spectrum library and run a documented MS2DeepScore query-candidate scoring wrapper; label generator+MS2DeepScore reranking as hybrid rather than native MS2DeepScore",
            "can_include_in_main_benchmark": False,
        },
        {
            "gap": "trained neural FragAnnotor CASMI effective result",
            "status": "completed_report_only_weak",
            "resolved_now": True,
            "current_evidence": f"frozen checkpoint Top-1={scalar(neural, 'top1_accuracy')}, Top-10={scalar(neural, 'top10_accuracy')}, MRR={scalar(neural, 'mean_reciprocal_rank')}",
            "required_to_close": "for an effective neural claim, train/select on non-CASMI data with explicit CASMI structure exclusion and improve beyond fixed component-score mode without CASMI tuning",
            "can_include_in_main_benchmark": False,
        },
        {
            "gap": "CASMI pairwise rank delta outliers",
            "status": "fixed",
            "resolved_now": True,
            "current_evidence": (
                "sota_pairwise_rank_comparison.csv now reports n_completed_queries, n_rank_valid_queries, "
                f"and n_missing_rank_pairs; max_abs_reported_rank_delta={max_abs_rank_delta}; "
                f"has_sentinel_scale_rank_delta={has_sentinel_scale_rank_delta}"
            ),
            "required_to_close": "none for the current artifact; continue excluding unavailable or non-finite rank pairs from paired deltas",
            "can_include_in_main_benchmark": True,
        },
        {
            "gap": "strong SOTA claim",
            "status": "blocked_pending_harmonized_direct_comparison",
            "resolved_now": False,
            "current_evidence": "ICEBERG/MassFormer/NEIMS are available only as imported public/vendor context, not harmonized candidate-level reruns",
            "required_to_close": "run FragAnnotor, CFM-ID, SIRIUS/CSI, ICEBERG, MassFormer, NEIMS, and MS2DeepScore on the same CASMI candidate set, preprocessing, split, adduct assumptions, and metrics",
            "can_include_in_main_benchmark": False,
        },
    ]
    gap_df = pd.DataFrame(gap_rows)
    gap_df.to_csv(OUTDIR / "remaining_gap_status.csv", index=False)

    claim_rows = [
        {
            "claim": "FragAnnotor fixed component-score mode has completed CASMI2022 report-only rankings",
            "allowed": True,
            "support": f"CASMI Top-1={scalar(frag, 'top1_accuracy')}, Top-10={scalar(frag, 'top10_accuracy')}, MRR={scalar(frag, 'mean_reciprocal_rank')}",
            "guardrail": "Describe as fixed formal component-score mode using real CASMI peaks and SIRIUS formula evidence, not as trained neural spectrum prediction.",
        },
        {
            "claim": "Native SIRIUS formula-only CASMI ranking completed",
            "allowed": True,
            "support": f"CASMI SIRIUS Top-1={scalar(sirius, 'top1_accuracy')}, Top-10={scalar(sirius, 'top10_accuracy')}",
            "guardrail": "SIRIUS is scalar molecular formula plausibility evidence here, not a synthetic spectrum generator.",
        },
        {
            "claim": "Complete native CFM-ID CASMI candidate-ranking metrics are available",
            "allowed": False,
            "support": (
                f"Direct full-run manifest prepared for {cfmid_full_manifest.get('supported_queries', 'unknown')} supported "
                f"queries and {cfmid_full_manifest.get('total_supported_candidate_rows', 'unknown')} candidate rows. "
                f"Precomputed full-run manifest prepared for {cfmid_precomputed_progress.get('expected_unique_candidate_spectra', 'unknown')} "
                f"unique candidate spectra; completion status is {cfmid_precomputed_progress.get('status', 'missing_progress')} with "
                f"{cfmid_precomputed_progress.get('completed_candidate_spectra', 0)} cached candidate spectra and "
                f"{cfmid_precomputed_progress.get('n_completed_queries', 0)} completed queries. "
                f"{cfmid.get('benchmark_decision', '')}"
            ),
            "guardrail": "Only report CFM-ID smoke/runtime audit until a full candidate score table exists.",
        },
        {
            "claim": "A native CFM-ID complete-query CASMI subset is available",
            "allowed": True,
            "support": (
                f"Selected-query subset status={cfmid_complete_query_subset.get('status', 'missing')}; "
                f"n_queries={cfmid_complete_query_subset.get('summary', {}).get('n_queries')}; "
                f"candidate policy={cfmid_complete_query_subset.get('summary', {}).get('candidate_pool_policy')}; "
                f"Top-5={cfmid_complete_query_subset.get('summary', {}).get('top5_accuracy')}; "
                f"MRR={cfmid_complete_query_subset.get('summary', {}).get('mean_reciprocal_rank')}."
            ),
            "guardrail": "Describe as a full-candidate-set subset for selected low-candidate query only; do not report it as full CASMI CFM-ID.",
        },
        {
            "claim": "A second native CFM-ID complete-query CASMI result is available",
            "allowed": False,
            "support": (
                f"Expansion status={cfmid_complete_query_expansion.get('status', 'missing')}; "
                f"query_id={cfmid_complete_query_expansion.get('query_id')}; "
                f"predicted spectra={cfmid_complete_query_expansion.get('predicted_spectrum_ids')}/"
                f"{cfmid_complete_query_expansion.get('candidate_count')}; "
                f"missing={cfmid_complete_query_expansion.get('missing_candidate_spectra')}."
            ),
            "guardrail": "Query 35 remains partial and must not be included in Top-k/MRR until all candidate spectra are available and the full candidate set is ranked.",
        },
        {
            "claim": "MS2DeepScore CASMI candidate-ranking benchmark is complete",
            "allowed": False,
            "support": (
                f"MS2DeepScore environment/model cache verified={ms2_env.get('status', 'unknown')}; "
                "full candidate ranking remains blocked because CASMI structure candidates lack a complete candidate spectrum library. "
                "A complete-query hybrid subset exists only for a selected low-candidate query and uses CFM-ID-generated candidate spectra. "
                f"{ms2.get('benchmark_decision', '')}"
            ),
            "guardrail": "Do not substitute CFM-ID-generated spectra and call it native MS2DeepScore.",
        },
        {
            "claim": "A CFM-ID + MS2DeepScore complete-query CASMI hybrid subset is available",
            "allowed": True,
            "support": (
                f"status={ms2_complete_query_hybrid.get('status', 'missing')}; "
                f"n_queries={ms2_complete_query_hybrid.get('n_queries')}; "
                f"candidate policy={ms2_complete_query_hybrid.get('candidate_pool_policy')}; "
                f"Top-5={ms2_complete_query_hybrid.get('top5_accuracy')}; "
                f"MRR={ms2_complete_query_hybrid.get('mean_reciprocal_rank')}."
            ),
            "guardrail": "Describe as a CFM-ID-generated spectrum hybrid complete-query subset only; not native MS2DeepScore and not full CASMI.",
        },
        {
            "claim": "FragAnnotor is SOTA over ICEBERG/MassFormer/NEIMS on CASMI",
            "allowed": False,
            "support": "current ICEBERG/MassFormer/NEIMS results are imported public context, not direct harmonized reruns",
            "guardrail": "Use as external context only until harmonized candidate-level direct comparison is run.",
        },
    ]
    pd.DataFrame(claim_rows).to_csv(OUTDIR / "claim_guardrail_status.csv", index=False)

    if not pairwise.empty:
        pairwise.to_csv(OUTDIR / "rank_delta_validity_audit.csv", index=False)

    report = [
        "# CASMI Remaining Gap And SOTA Guardrail Report",
        "",
        "This package records the current status of the remaining CASMI benchmark gaps without fabricating unavailable native baseline results.",
        "",
        "## Rank-Delta Fix",
        "",
        "The CASMI pairwise rank-delta outlier was caused by missing true ranks being replaced with a large sentinel value before computing deltas. The benchmark now computes paired rank deltas only when both models are completed and both true ranks are finite.",
        "",
        "Current paired comparison table:",
        "",
        pairwise.to_markdown(index=False) if not pairwise.empty else "No pairwise table found.",
        "",
        "## Remaining Gaps",
        "",
        gap_df.to_markdown(index=False),
        "",
        "## Claim Guardrails",
        "",
        pd.DataFrame(claim_rows).to_markdown(index=False),
        "",
        "## Bottom Line",
        "",
        "The pairwise rank-delta artifact is fixed, and a report-only trained neural FragAnnotor CASMI result is available but weak. Complete CASMI native CFM-ID ranking remains a long full-shard execution task. MS2DeepScore has a verified pretrained environment, a candidate-limited CFM-ID-generated hybrid subset, and a selected complete-query CFM-ID-generated hybrid subset, but not a complete full-CASMI candidate-ranking benchmark. A strong SOTA claim remains blocked until all compared models are rerun on a harmonized candidate set and evaluation protocol.",
        "",
    ]
    (OUTDIR / "casmi_remaining_gap_and_sota_guardrail_report.md").write_text("\n".join(report), encoding="utf-8")

    write_json(
        OUTDIR / "audit_summary.json",
        {
            "stage": "casmi_remaining_gap_and_sota_guardrail_v1",
            "rank_delta_outlier_fixed": True,
            "max_abs_reported_rank_delta": None if pd.isna(max_abs_rank_delta) else max_abs_rank_delta,
            "has_sentinel_scale_rank_delta": has_sentinel_scale_rank_delta,
            "complete_native_cfmid_casmi_available": False,
            "native_ms2deepscore_casmi_available": False,
            "ms2deepscore_complete_query_hybrid_subset_available": bool(ms2_complete_query_hybrid),
            "trained_neural_casmi_effective_primary": False,
            "strong_sota_claim_supported": False,
            "outputs": [
                "remaining_gap_status.csv",
                "claim_guardrail_status.csv",
                "rank_delta_validity_audit.csv",
                "casmi_remaining_gap_and_sota_guardrail_report.md",
            ],
            "cfmid_full_manifest_available": bool(cfmid_full_manifest),
            "cfmid_full_supported_completion_fraction": cfmid_full_progress.get("completion_fraction"),
            "cfmid_precomputed_manifest_available": bool(cfmid_precomputed_manifest),
            "cfmid_precomputed_candidate_spectrum_completion_fraction": cfmid_precomputed_progress.get("candidate_spectrum_completion_fraction"),
            "cfmid_precomputed_query_completion_fraction": cfmid_precomputed_progress.get("query_completion_fraction"),
            "cfmid_complete_query_subset_available": bool(cfmid_complete_query_subset),
            "cfmid_complete_query_expansion_partial_available": bool(cfmid_complete_query_expansion),
            "ms2deepscore_environment_verified": ms2_env.get("status") == "verified",
            "ms2deepscore_pretrained_files_present": bool(ms2_resource.get("all_required_files_present")),
        },
    )


if __name__ == "__main__":
    main()
