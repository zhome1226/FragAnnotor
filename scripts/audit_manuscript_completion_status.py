#!/usr/bin/env python3
"""Audit manuscript completion state from current FragAnnotor artifacts."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "outputs" / "manuscript_completion_v1"
MEMORY_PATH = ROOT / "outputs" / "agent_memory" / "research_state.json"
RESEARCH_STATE_PATH = ROOT / "docs" / "RESEARCH_STATE.md"


def run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if pd.isna(value) if not isinstance(value, (dict, list, tuple)) else False:
        return None
    return value


def metric_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {}
    rank = pd.to_numeric(df.get("true_rank"), errors="coerce")
    out: dict[str, Any] = {
        "n_queries": int(len(df)),
        "rank_valid_queries": int(rank.notna().sum()),
    }
    for col, name in [
        ("top1_correct", "top1_accuracy"),
        ("top5_correct", "top5_accuracy"),
        ("top10_correct", "top10_accuracy"),
        ("formula_correct", "formula_accuracy"),
        ("formula_accuracy", "formula_accuracy"),
    ]:
        if col in df.columns:
            out[name] = float(df[col].astype(bool).mean())
    if "reciprocal_rank" in df.columns:
        out["mean_reciprocal_rank"] = float(pd.to_numeric(df["reciprocal_rank"], errors="coerce").mean())
    if "top1_tanimoto" in df.columns:
        out["mean_top1_tanimoto"] = float(pd.to_numeric(df["top1_tanimoto"], errors="coerce").mean())
    if rank.notna().any():
        out["median_true_rank"] = float(rank.median())
    return out


def result_status(path: Path, expected: int | None, complete_statuses: set[str] | None = None) -> tuple[int, str]:
    df = read_csv(path)
    if df.empty:
        return 0, "missing"
    if complete_statuses and "status" in df.columns:
        completed = int(df["status"].astype(str).isin(complete_statuses).sum())
    else:
        completed = int(len(df))
    if expected is not None and completed >= expected:
        return completed, "completed"
    return completed, "partial"


def cfmid_full_supported_status(query_path: Path, gate_path: Path) -> tuple[int, str, str]:
    gate = read_csv(gate_path)
    if not gate.empty and {"requirement", "status"}.issubset(gate.columns):
        mask = gate["requirement"].astype(str).str.contains("CFM-ID complete all 170 supported CASMI queries", regex=False)
        rows = gate[mask]
        if not rows.empty and rows.iloc[0]["status"] == "completed_full_supported":
            return 170, "completed", "completion gate reports completed_full_supported"
    completed, status = result_status(query_path, 170, {"completed"})
    return completed, status, "query result file status count"


def harmonized_count(model: str) -> tuple[int, int, int]:
    root = ROOT / "results" / "harmonized_sota_candidate_reruns_v1" / model
    rows = []
    for path in sorted(root.glob("shard_*/casmi2022_*_harmonized_query_results.csv")):
        df = read_csv(path)
        if not df.empty:
            rows.append(df)
    if not rows:
        aggregate = read_csv(root / f"casmi2022_{model}_harmonized_query_results.csv")
        rows = [aggregate] if not aggregate.empty else []
    if not rows:
        return 0, 0, 0
    all_df = pd.concat(rows, ignore_index=True)
    valid = all_df[all_df.get("status", pd.Series(dtype=str)).astype(str).isin({"completed", "partial_prediction_failures"})]
    failed = int(pd.to_numeric(all_df.get("failed_prediction_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum())
    return int(valid["query_id"].astype(str).nunique()), int(len(all_df)), failed


def row(
    section: str,
    task: str,
    dataset: str,
    variant: str,
    expected: int | str,
    completed: int | str,
    status: str,
    outputs: list[str],
    blocker: str,
    next_action: str,
    usable: str,
    guardrail: str,
    latest_commit: str,
) -> dict[str, Any]:
    return {
        "manuscript_section": section,
        "task": task,
        "dataset": dataset,
        "model_or_variant": variant,
        "expected_queries": expected,
        "completed_queries": completed,
        "result_status": status,
        "output_paths": ";".join(outputs),
        "latest_commit": latest_commit,
        "blocker": blocker,
        "required_next_action": next_action,
        "can_be_used_in_main_text": usable,
        "claim_guardrail": guardrail,
    }


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESEARCH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    commit = run_git(["rev-parse", "HEAD"])
    branch = run_git(["branch", "--show-current"])
    dirty = run_git(["status", "--short"])
    now = datetime.now(timezone.utc).isoformat()

    formal_path = ROOT / "results" / "casmi2022_fragannotor_formal_components" / "casmi2022_fragannotor_formal_query_results.csv"
    formal_df = read_csv(formal_path)
    formal_metrics = metric_summary(formal_df)

    neural_path = ROOT / "results" / "casmi2022_fragannotor_trained_neural_v1" / "casmi2022_fragannotor_trained_neural_summary.csv"
    neural_df = read_csv(neural_path)

    cfmid_path = ROOT / "results" / "casmi2022_cfmid_native_full_supported_v1" / "casmi2022_cfmid_native_full_supported_query_results.csv"
    hybrid_path = ROOT / "results" / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_v1" / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_query_results.csv"
    cfm_gate_path = ROOT / "results" / "casmi_full_completion_audit_v1" / "full_completion_status.csv"

    cfmid_completed, cfmid_status, cfmid_evidence = cfmid_full_supported_status(cfmid_path, cfm_gate_path)
    hybrid_completed, hybrid_status = result_status(hybrid_path, 170, {"completed"})
    massformer_completed, massformer_rows, massformer_failed = harmonized_count("massformer")
    iceberg_completed, iceberg_rows, iceberg_failed = harmonized_count("iceberg")

    neims_files = list(ROOT.glob("**/*NEIMS*")) + list(ROOT.glob("**/*neims*"))
    neims_ready = any(path.is_file() and path.suffix in {".pt", ".pkl", ".ckpt", ".h5"} for path in neims_files)

    ablation_path = ROOT / "results" / "ablation" / "fragannotor_ablation_summary.csv"
    casmi_ablation_path = ROOT / "results" / "manuscript_3_3_casmi_ablation" / "summary.csv"
    case_paths = list((ROOT / "results").glob("**/*case*"))
    external_gap = ROOT / "results" / "external_validation_data_gap_summary.csv"

    matrix = [
        row("Stage 0", "Repository and result-state audit", "FragAnnotor repo", "all current artifacts", "n/a", "n/a", "completed",
            ["outputs/manuscript_completion_v1/status_matrix.csv", "outputs/manuscript_completion_v1/status_report.md"],
            "", "Use this audit as starting point for Stage 1 freeze.", "yes", "Audit records current files only; it does not validate manuscript claims by itself.", commit),
        row("Stage 1", "Freeze final FragAnnotator definition", "CASMI2022", "fixed evidence fusion", 1, 0, "missing_required_freeze",
            ["configs/fragannotator_manuscript_final.yaml", "docs/FRAGANNOTATOR_FINAL_MODEL_DEFINITION.md", "outputs/manuscript_completion_v1/final_config_audit.json"],
            "final manuscript config not yet frozen", "Create frozen config and model-definition audit before new main analyses.", "no",
            "Main method should remain fixed evidence-fusion unless a leakage-safe trained model beats it on matched data.", commit),
        row("3.1", "CASMI2022 FragAnnotor-only performance", "CASMI2022", "fixed component-score evidence fusion", 229, len(formal_df),
            "completed_query_results_available" if len(formal_df) == 229 else "partial_or_missing",
            [str(formal_path.relative_to(ROOT))], "", "Regenerate manuscript 3.1 package with CIs/strata from frozen config.", "not_yet_manuscript_ready",
            "Do not include SIRIUS/CFM-ID baselines in 3.1.", commit),
        row("3.1 audit", "Old trained neural checkpoint", "CASMI2022", "trained neural checkpoint", 229, int(neural_df.get("n_queries", pd.Series([0])).iloc[0]) if not neural_df.empty else 0,
            "negative_or_audit_result", [str(neural_path.relative_to(ROOT))], "", "Keep as audit/negative result unless strict rerun proves superiority.", "no",
            "Do not claim trained neural FragAnnotator outperforms SOTA from this checkpoint.", commit),
        row("3.2", "Native CFM-ID supported benchmark", "CASMI2022 matched [M+H]+", "native CFM-ID", 170, cfmid_completed, cfmid_status,
            [str(cfmid_path.relative_to(ROOT)), str(cfm_gate_path.relative_to(ROOT))], "", f"Refresh query summary from completion gate evidence: {cfmid_evidence}.", "yes_after_matched_manifest",
            "Use only 170 supported queries; do not mix with 229-query metrics.", commit),
        row("3.2", "CFM-ID spectra plus MS2DeepScore hybrid", "CASMI2022 matched [M+H]+", "CFM-ID-generated spectra + MS2DeepScore similarity hybrid", 170, hybrid_completed, hybrid_status,
            [str(hybrid_path.relative_to(ROOT))], "", "Recompute/confirm summary on matched manifest before main table.", "yes_after_matched_manifest",
            "Never call this a native MS2DeepScore benchmark.", commit),
        row("3.2", "MassFormer harmonized rerun", "CASMI2022 matched [M+H]+", "MassFormer", 170, massformer_completed, "running_or_partial",
            ["results/harmonized_sota_candidate_reruns_v1/massformer"], f"{massformer_failed} candidate prediction failures recorded so far",
            "Continue resumable shards to 170/170 or document irrecoverable failures.", "no_partial_main_table",
            "Partial MassFormer metrics cannot enter the main comparison table.", commit),
        row("3.2", "ICEBERG harmonized rerun", "CASMI2022 matched [M+H]+", "ICEBERG", 170, iceberg_completed, "partial",
            ["results/harmonized_sota_candidate_reruns_v1/iceberg"], f"{iceberg_failed} candidate prediction failures recorded so far",
            "Continue CPU shards to 170/170 or document irrecoverable failures.", "no_partial_main_table",
            "Partial ICEBERG metrics cannot enter the main comparison table.", commit),
        row("3.2", "NEIMS readiness", "CASMI2022 matched [M+H]+", "NEIMS", 170, 0, "blocked_or_unavailable" if not neims_ready else "resources_detected_needs_validation",
            [], "no validated checkpoint/wrapper confirmed" if not neims_ready else "detected files require validation",
            "Create NEIMS_UNAVAILABLE_AUDIT.md unless checkpoint and wrapper are validated.", "no",
            "Do not fabricate NEIMS results or include placeholders in the main table.", commit),
        row("3.3", "CASMI component ablation", "CASMI2022", "formal components", 229, 0 if not casmi_ablation_path.exists() else len(read_csv(casmi_ablation_path)),
            "missing_required_casmi_ablation" if not casmi_ablation_path.exists() else "available_needs_validation",
            [str(ablation_path.relative_to(ROOT))] if ablation_path.exists() else [], "existing ablation appears not to be the required CASMI manuscript package",
            "Run CASMI ablation and sensitivity using frozen config.", "no",
            "PFAS ablation cannot substitute for CASMI2022 main-task ablation.", commit),
        row("3.4", "Fragmentation mechanism cases", "CASMI2022 preferred", "case studies", "3-5", len(case_paths), "not_manuscript_ready",
            [str(p.relative_to(ROOT)) for p in case_paths[:8]], "case-study package not validated for required provenance and mass-balance checks",
            "Select CASMI cases and generate machine-readable evidence/figures.", "no",
            "Do not describe SIRIUS-derived annotations as FragAnnotator-generated.", commit),
        row("3.5", "Independent validation audit", "external/PFAS/public", "frozen evidence fusion", "unknown", 0, "blocked_pending_independence_audit",
            [str(external_gap.relative_to(ROOT))] if external_gap.exists() else [], "independent data not yet proven unused in model development",
            "Audit data independence before using PFAS or any external set.", "no",
            "Do not call PFAS locked-test independent unless audit proves no development use.", commit),
        row("Stage 7", "Manuscript-ready tables and claims", "all sections", "final result package", "all stages", 0, "not_ready",
            ["outputs/manuscript_completion_v1"], "depends on Stage 1-6 completion",
            "Assemble after frozen analyses are complete.", "no",
            "Claims must cite query-level outputs and matched query counts.", commit),
    ]

    status_df = pd.DataFrame(matrix)
    status_df.to_csv(OUTDIR / "status_matrix.csv", index=False)
    (OUTDIR / "status_matrix.json").write_text(json.dumps(json_safe(matrix), indent=2, sort_keys=True), encoding="utf-8")

    audit = {
        "stage": "manuscript_completion_v1_status_audit",
        "timestamp_utc": now,
        "branch": branch,
        "latest_commit": commit,
        "dirty_status": dirty,
        "formal_fragannotor_metrics": formal_metrics,
        "cfmid_completed_queries": cfmid_completed,
        "hybrid_completed_queries": hybrid_completed,
        "massformer_completed_queries": massformer_completed,
        "iceberg_completed_queries": iceberg_completed,
        "neims_ready": neims_ready,
    }
    (OUTDIR / "status_audit.json").write_text(json.dumps(json_safe(audit), indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Manuscript Completion Status Audit",
        "",
        f"- Timestamp UTC: `{now}`",
        f"- Branch: `{branch}`",
        f"- Latest commit: `{commit}`",
        f"- Dirty worktree entries: `{len(dirty.splitlines()) if dirty else 0}`",
        "",
        "## Key Findings",
        "",
        f"- FragAnnotor fixed evidence-fusion CASMI query-level results: `{len(formal_df)}/229`.",
        f"- CFM-ID native supported benchmark: `{cfmid_completed}/170` rows with completed status.",
        f"- CFM-ID-generated spectra + MS2DeepScore hybrid: `{hybrid_completed}/170` rows with completed status.",
        f"- MassFormer harmonized rerun: `{massformer_completed}/170` valid query rows found across shard outputs.",
        f"- ICEBERG harmonized rerun: `{iceberg_completed}/170` valid query rows found across shard outputs.",
        f"- NEIMS validated availability: `{neims_ready}`.",
        "",
        "## Required Next Action",
        "",
        "Freeze the final evidence-fusion configuration in Stage 1 before generating manuscript-ready Section 3.1-3.5 packages.",
        "",
        "## Status Matrix",
        "",
        status_df.to_markdown(index=False),
        "",
    ]
    (OUTDIR / "status_report.md").write_text("\n".join(lines), encoding="utf-8")

    research_lines = [
        "# FragAnnotor Research State",
        "",
        f"Last updated: `{now}`",
        f"Current audited commit: `{commit}`",
        "",
        "## Current Priority",
        "",
        "Stage 1: freeze the final fixed evidence-fusion FragAnnotator definition before regenerating manuscript result packages.",
        "",
        "## Current Evidence State",
        "",
        f"- Stage 0 status audit generated under `outputs/manuscript_completion_v1/`.",
        f"- Fixed evidence-fusion CASMI results available for `{len(formal_df)}` queries.",
        f"- Harmonized MassFormer currently has `{massformer_completed}` valid query rows; ICEBERG has `{iceberg_completed}` valid query rows.",
        "- Partial harmonized SOTA outputs are not manuscript-ready main-table evidence.",
        "- NEIMS remains unavailable unless a validated checkpoint and wrapper are confirmed.",
        "",
    ]
    RESEARCH_STATE_PATH.write_text("\n".join(research_lines), encoding="utf-8")
    MEMORY_PATH.write_text(json.dumps(json_safe(audit), indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
