#!/usr/bin/env python3
"""Create manuscript-ready benchmark summary tables."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "results" / "manuscript_ready_benchmark_tables_v1"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def keep_existing(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return df[[c for c in columns if c in df.columns]].copy()


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    summary = read_csv(ROOT / "results" / "sota_comparison_summary.csv")
    ablation = read_csv(ROOT / "results" / "ablation" / "fragannotor_ablation_summary.csv")
    native_audit = read_csv(ROOT / "results" / "native_baseline_audit.csv")
    guardrail = read_csv(ROOT / "results" / "casmi_remaining_gap_and_sota_guardrail_v1" / "claim_guardrail_status.csv")
    gap = read_csv(ROOT / "results" / "casmi_remaining_gap_and_sota_guardrail_v1" / "remaining_gap_status.csv")
    cfmid_subset = read_csv(ROOT / "results" / "casmi2022_cfmid_native_subset_v1" / "casmi2022_cfmid_native_subset_summary.csv")
    cfmid_full = read_csv(ROOT / "results" / "casmi2022_cfmid_native_full_supported_v1" / "casmi2022_cfmid_native_full_supported_summary.csv")
    cfmid_full_manifest = read_json(ROOT / "results" / "cfmid_full_casmi_run_manifest_v1" / "audit_summary.json")
    cfmid_precomputed = read_csv(ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1" / "casmi2022_cfmid_native_precomputed_full_summary.csv")
    cfmid_precomputed_manifest = read_json(ROOT / "results" / "cfmid_precomputed_full_casmi_manifest_v1" / "audit_summary.json")
    cfmid_precomputed_progress = read_json(ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1" / "audit_summary.json")
    hybrid_subset = read_csv(ROOT / "results" / "casmi2022_cfmid_ms2deepscore_hybrid_subset_v1" / "casmi2022_cfmid_ms2deepscore_hybrid_subset_summary.csv")
    neural = read_csv(ROOT / "results" / "casmi2022_fragannotor_trained_neural_v1" / "casmi2022_fragannotor_trained_neural_summary.csv")
    ms2_audit = read_json(ROOT / "results" / "native_ms2deepscore_casmi" / "native_ms2deepscore_audit.json")
    ms2_env = ms2_audit.get("external_ms2deepscore_environment", {})
    ms2_resource = ms2_audit.get("external_pretrained_model_cache", {})
    cfmid_audit = read_json(ROOT / "results" / "native_cfmid_casmi" / "native_cfmid_runtime_audit.json")

    metric_cols = [
        "dataset",
        "model",
        "status",
        "native_or_fallback",
        "n_queries",
        "top1_accuracy",
        "top5_accuracy",
        "top10_accuracy",
        "mean_reciprocal_rank",
        "mean_top1_tanimoto",
        "molecular_formula_accuracy",
        "median_true_rank",
        "median_candidate_count",
        "notes",
    ]
    casmi = keep_existing(summary[summary["dataset"].eq("CASMI2022")] if not summary.empty else summary, metric_cols)
    if not cfmid_full.empty:
        full = cfmid_full.rename(columns={"n_supported_queries": "n_queries", "claim_guardrail": "notes"})
        full["dataset"] = "CASMI2022"
        full["model"] = "CFM-ID full supported manifest"
        casmi = pd.concat([casmi, keep_existing(full, metric_cols)], ignore_index=True)
    if not cfmid_precomputed.empty:
        precomputed = cfmid_precomputed.rename(columns={"n_supported_queries": "n_queries", "claim_guardrail": "notes"})
        precomputed["dataset"] = "CASMI2022"
        precomputed["model"] = "CFM-ID precomputed full progress"
        casmi = pd.concat([casmi, keep_existing(precomputed, metric_cols)], ignore_index=True)
    if not cfmid_subset.empty:
        subset = cfmid_subset.rename(
            columns={
                "n_queries_selected": "n_queries",
                "claim_guardrail": "notes",
            }
        )
        subset["dataset"] = "CASMI2022"
        subset["model"] = "CFM-ID subset"
        casmi = pd.concat([casmi, keep_existing(subset, metric_cols)], ignore_index=True)
    if not neural.empty:
        neural_row = neural.copy()
        neural_row["model"] = "FragAnnotor trained neural checkpoint"
        casmi = pd.concat([casmi, keep_existing(neural_row, metric_cols)], ignore_index=True)
    if not hybrid_subset.empty:
        hybrid = hybrid_subset.rename(
            columns={
                "n_queries_selected": "n_queries",
                "claim_guardrail": "notes",
            }
        )
        hybrid["dataset"] = "CASMI2022"
        hybrid["model"] = "CFM-ID + MS2DeepScore hybrid subset"
        casmi = pd.concat([casmi, keep_existing(hybrid, metric_cols)], ignore_index=True)
    casmi.to_csv(OUTDIR / "table1_casmi2022_benchmark.csv", index=False)

    pfas = keep_existing(summary[summary["dataset"].eq("PFAS")] if not summary.empty else summary, metric_cols)
    pfas.to_csv(OUTDIR / "table2_pfas_locked_test_benchmark.csv", index=False)

    ablation_cols = ["variant", "n_queries", "top1_accuracy", "top5_accuracy", "top10_accuracy", "mean_reciprocal_rank"]
    keep_existing(ablation, ablation_cols).to_csv(OUTDIR / "table3_pfas_ablation.csv", index=False)

    blocker_rows = []
    if not native_audit.empty:
        blocker_rows.extend(native_audit.to_dict(orient="records"))
    blocker_rows.extend(
        [
            {
                "model": "CFM-ID",
                "native_available": False,
                "executable_or_package": cfmid_audit.get("native_binary", ""),
                "version": cfmid_audit.get("native_binary_smoke_status", ""),
                "blocker": cfmid_audit.get("benchmark_decision", ""),
                "subset_status": "completed_candidate_limited_subset" if not cfmid_subset.empty else "",
                "full_run_manifest": (
                    f"{cfmid_full_manifest.get('supported_queries', 'unknown')} supported queries; "
                    f"{cfmid_full_manifest.get('total_supported_candidate_rows', 'unknown')} candidate rows; "
                    f"{cfmid_full_manifest.get('n_shards', 'unknown')} shards; status={cfmid_full_manifest.get('status', 'missing')}"
                ),
                "precomputed_full_manifest": (
                    f"{cfmid_precomputed_manifest.get('supported_queries', 'unknown')} supported queries; "
                    f"{cfmid_precomputed_manifest.get('supported_candidate_rows', 'unknown')} candidate rows; "
                    f"{cfmid_precomputed_progress.get('expected_unique_candidate_spectra', 'unknown')} unique candidate spectra; "
                    f"cached={cfmid_precomputed_progress.get('completed_candidate_spectra', 0)}; "
                    f"ranked_queries={cfmid_precomputed_progress.get('n_completed_queries', 0)}"
                ),
            },
            {
                "model": "MS2DeepScore",
                "native_available": False,
                "executable_or_package": ms2_env.get("env_python", "ms2deepscore/matchms user-space venv"),
                "version": (
                    f"MS2DeepScore {ms2_env.get('ms2deepscore_version', '')}; "
                    f"MatchMS {ms2_env.get('matchms_version', '')}; Torch {ms2_env.get('torch_version', '')}"
                ),
                "blocker": ms2_audit.get("benchmark_decision", ""),
                "subset_status": "pretrained_model_and_cpu_env_verified; complete_candidate_spectrum_library_missing",
                "pretrained_files_present": ms2_resource.get("all_required_files_present", False),
            },
        ]
    )
    pd.DataFrame(blocker_rows).drop_duplicates().to_csv(OUTDIR / "supplementary_native_tool_audit_and_blockers.csv", index=False)

    if not gap.empty:
        gap.to_csv(OUTDIR / "supplementary_remaining_gap_status.csv", index=False)
    if not guardrail.empty:
        guardrail.to_csv(OUTDIR / "supplementary_sota_guardrails.csv", index=False)

    report = [
        "# Manuscript-Ready Benchmark Tables",
        "",
        "This package collects clean tables for manuscript drafting without changing model weights or rerunning benchmark selection.",
        "",
        "## Included Tables",
        "",
        "- `table1_casmi2022_benchmark.csv`: CASMI2022 main rows plus explicitly labeled CFM-ID direct full-run manifest, CFM-ID precomputed full-progress, CFM-ID subset, trained neural checkpoint audit, and CFM-ID + MS2DeepScore hybrid subset rows.",
        "- `table2_pfas_locked_test_benchmark.csv`: PFAS locked-test benchmark rows.",
        "- `table3_pfas_ablation.csv`: PFAS no-SIRIUS/full-fusion ablations where available.",
        "- `supplementary_native_tool_audit_and_blockers.csv`: native tool status and blockers.",
        "- `supplementary_remaining_gap_status.csv`: remaining gap audit.",
        "- `supplementary_sota_guardrails.csv`: allowed/disallowed claims.",
        "",
        "## Reporting Guardrails",
        "",
        "- The CFM-ID subset row is candidate-limited (`first_n_plus_true`) and is not a full CASMI CFM-ID result.",
        "- The CFM-ID full-run manifest row is a completion gate, not a completed benchmark metric row; report full CFM-ID metrics only after all supported query outputs are complete.",
        "- The CFM-ID precomputed full-progress row is also a completion gate; it validates candidate-spectrum caching and fast `cfm-id-precomputed` ranking but is not a full metric row until all candidate spectra and supported queries complete.",
        "- The CFM-ID + MS2DeepScore row is a generated-spectrum hybrid subset, not native MS2DeepScore and not a full CASMI benchmark.",
        "- MS2DeepScore has a verified pretrained model cache and CPU environment, but remains blocked for full candidate ranking because no complete CASMI per-candidate spectrum library is available.",
        "- The trained neural checkpoint row is report-only and weak; do not use it as primary CASMI evidence.",
        "- Strong SOTA claims remain blocked until all methods are rerun on the same candidate set, preprocessing, adduct assumptions, and metrics.",
        "",
    ]
    (OUTDIR / "manuscript_ready_tables_report.md").write_text("\n".join(report), encoding="utf-8")
    write_json(
        OUTDIR / "audit_summary.json",
        {
            "stage": "manuscript_ready_benchmark_tables_v1",
            "tables": [
                "table1_casmi2022_benchmark.csv",
                "table2_pfas_locked_test_benchmark.csv",
                "table3_pfas_ablation.csv",
                "supplementary_native_tool_audit_and_blockers.csv",
                "supplementary_remaining_gap_status.csv",
                "supplementary_sota_guardrails.csv",
            ],
            "cfmid_subset_included_as_full_result": False,
            "cfmid_full_manifest_available": bool(cfmid_full_manifest),
            "cfmid_precomputed_manifest_available": bool(cfmid_precomputed_manifest),
            "cfmid_precomputed_candidate_spectrum_completion_fraction": cfmid_precomputed_progress.get("candidate_spectrum_completion_fraction"),
            "ms2deepscore_full_candidate_ranking_available": False,
            "ms2deepscore_environment_verified": ms2_env.get("status") == "verified",
            "strong_sota_claim_supported": False,
        },
    )


if __name__ == "__main__":
    main()
