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
    ms2 = read_json(ROOT / "results" / "native_ms2deepscore_casmi" / "native_ms2deepscore_audit.json")

    casmi_summary = summary[summary["dataset"].eq("CASMI2022")].copy() if not summary.empty else pd.DataFrame()
    frag = casmi_summary[casmi_summary["model"].eq("FragAnnotor")]
    sirius = casmi_summary[casmi_summary["model"].eq("SIRIUS")]

    gap_rows = [
        {
            "gap": "CFM-ID complete CASMI native ranking",
            "status": cfmid.get("status", "missing_audit"),
            "resolved_now": False,
            "current_evidence": "cfmid4-compatible native binary smoke passed; full 1241-candidate query and 100-candidate timing probe exceeded 15 minutes",
            "required_to_close": "complete per-query CFM-ID candidate score table for all 229 CASMI queries, preferably through precomputed candidate spectra plus cfm-id-precomputed or a successful full native batch run",
            "can_include_in_main_benchmark": False,
        },
        {
            "gap": "MS2DeepScore reasonable CASMI candidate-ranking benchmark",
            "status": ms2.get("status", "missing_audit"),
            "resolved_now": False,
            "current_evidence": "no configured MS2DeepScore pretrained model and no complete per-candidate measured/predicted spectrum library in repository",
            "required_to_close": "install/configure a pretrained MS2DeepScore model and construct a complete candidate spectrum library; label any generator+MS2DeepScore reranker as hybrid rather than native MS2DeepScore",
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
            "current_evidence": "sota_pairwise_rank_comparison.csv now reports n_completed_queries, n_rank_valid_queries, and n_missing_rank_pairs; no 1e9 missing-rank sentinel participates in deltas",
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
            "support": cfmid.get("benchmark_decision", ""),
            "guardrail": "Only report CFM-ID smoke/runtime audit until a full candidate score table exists.",
        },
        {
            "claim": "MS2DeepScore CASMI candidate-ranking benchmark is complete",
            "allowed": False,
            "support": ms2.get("benchmark_decision", ""),
            "guardrail": "Do not substitute CFM-ID-generated spectra and call it native MS2DeepScore.",
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
        "The pairwise rank-delta artifact is fixed. Complete CASMI native CFM-ID ranking, native or defensible hybrid MS2DeepScore candidate ranking, and an effective trained neural FragAnnotor CASMI result remain unavailable. A strong SOTA claim remains blocked until all compared models are rerun on a harmonized candidate set and evaluation protocol.",
        "",
    ]
    (OUTDIR / "casmi_remaining_gap_and_sota_guardrail_report.md").write_text("\n".join(report), encoding="utf-8")

    write_json(
        OUTDIR / "audit_summary.json",
        {
            "stage": "casmi_remaining_gap_and_sota_guardrail_v1",
            "rank_delta_outlier_fixed": True,
            "complete_native_cfmid_casmi_available": False,
            "native_ms2deepscore_casmi_available": False,
            "trained_neural_casmi_effective_primary": False,
            "strong_sota_claim_supported": False,
            "outputs": [
                "remaining_gap_status.csv",
                "claim_guardrail_status.csv",
                "rank_delta_validity_audit.csv",
                "casmi_remaining_gap_and_sota_guardrail_report.md",
            ],
        },
    )


if __name__ == "__main__":
    main()
