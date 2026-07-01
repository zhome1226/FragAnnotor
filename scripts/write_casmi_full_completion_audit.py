#!/usr/bin/env python3
"""Write full-CASMI completion audit and execution gates.

This report is intentionally conservative. It tracks the concrete work needed
before claiming:

- complete native CFM-ID ranking for all 170 supported CASMI queries;
- complete CFM-ID candidate-spectrum cache for 936,483 unique candidates;
- a documented policy for 59 unsupported [M+Na]+ CASMI queries;
- a full CASMI MS2DeepScore candidate-ranking library;
- harmonized ICEBERG/MassFormer/NEIMS reruns on the same candidate set.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
MANIFEST_DIR = ROOT / "results" / "cfmid_precomputed_full_casmi_manifest_v1"
CFMID_RUN_DIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"
MS2_AUDIT = ROOT / "results" / "native_ms2deepscore_casmi" / "native_ms2deepscore_audit.json"
OUTDIR = ROOT / "results" / "casmi_full_completion_audit_v1"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


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


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def adduct_slug(adduct: Any) -> str:
    return str(adduct).replace("[", "").replace("]", "").replace("+", "plus").replace("-", "minus")


def candidate_shard_audit_path(row: pd.Series) -> Path:
    slug = adduct_slug(row["adduct"])
    return (
        CFMID_RUN_DIR
        / "candidate_spectrum_shards"
        / slug
        / f"shard_{int(row['candidate_start'])}_{int(row['candidate_limit'])}"
        / "audit_summary.json"
    )


def unique_candidate_ids_by_adduct() -> dict[str, list[int]]:
    spec = pd.read_pickle(CASMI_DIR / "spec_df.pkl")
    cand = pd.read_pickle(CASMI_DIR / "cand_df.pkl")
    model_root = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
    model_adducts = {p.name for p in model_root.iterdir() if p.is_dir()} if model_root.exists() else set()
    supported = spec[spec["prec_type"].astype(str).isin(model_adducts)].copy()
    out: dict[str, list[int]] = {}
    for adduct, adduct_spec in supported.groupby("prec_type"):
        adduct_query_ids = set(adduct_spec["mol_id"].astype(int))
        ids = (
            cand[cand["query_mol_id"].astype(int).isin(adduct_query_ids)]["candidate_mol_id"]
            .astype(int)
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        out[str(adduct)] = ids
    return out


def cached_candidate_ids_by_slug() -> dict[str, set[int]]:
    cache_root = CFMID_RUN_DIR / "candidate_spectra_cache"
    out: dict[str, set[int]] = {}
    if not cache_root.exists():
        return out
    for slug_dir in cache_root.iterdir():
        if not slug_dir.is_dir():
            continue
        ids: set[int] = set()
        for path in slug_dir.glob("*.txt"):
            if path.stat().st_size <= 0:
                continue
            try:
                ids.add(int(path.stem))
            except ValueError:
                continue
        out[slug_dir.name] = ids
    return out


def candidate_shard_status() -> pd.DataFrame:
    manifest = read_csv(MANIFEST_DIR / "cfmid_precomputed_candidate_spectrum_shards.csv")
    if manifest.empty:
        return manifest
    unique_ids = unique_candidate_ids_by_adduct()
    cached_ids = cached_candidate_ids_by_slug()
    rows: list[dict[str, Any]] = []
    for _, row in manifest.iterrows():
        audit_path = candidate_shard_audit_path(row)
        audit = read_json(audit_path)
        selected_ids = unique_ids.get(str(row["adduct"]), [])[
            int(row["candidate_start"]) : int(row["candidate_start"]) + int(row["candidate_limit"])
        ]
        slug = adduct_slug(row["adduct"])
        cached = sum(1 for mol_id in selected_ids if mol_id in cached_ids.get(slug, set()))
        completed = max(int(audit.get("completed_candidates", 0) or 0), cached)
        failed = int(audit.get("failed_candidates", 0) or 0)
        selected = int(audit.get("selected_candidates", row.get("candidate_count", 0)) or 0)
        status = str(audit.get("status", "not_started"))
        if not audit:
            status = "not_started"
        if completed == int(row["candidate_count"]) and failed == 0:
            status = "completed"
        elif completed > 0 and status == "not_started":
            status = "partial_cached"
        rows.append(
            {
                "shard_id": int(row["shard_id"]),
                "adduct": str(row["adduct"]),
                "candidate_start": int(row["candidate_start"]),
                "candidate_limit": int(row["candidate_limit"]),
                "candidate_count": int(row["candidate_count"]),
                "status": status,
                "completed_candidates": completed,
                "cached_candidates": cached,
                "failed_candidates": failed,
                "selected_candidates": selected,
                "audit_file": str(audit_path) if audit_path.exists() else "",
                "command": row.get("command", ""),
            }
        )
    return pd.DataFrame(rows)


def query_completion_status() -> pd.DataFrame:
    manifest = read_csv(MANIFEST_DIR / "cfmid_precomputed_supported_query_manifest.csv")
    results = read_csv(CFMID_RUN_DIR / "casmi2022_cfmid_native_precomputed_full_query_results.csv")
    if manifest.empty:
        return manifest
    result_by_query: dict[str, dict[str, Any]] = {}
    if not results.empty and "query_id" in results.columns:
        for _, row in results.iterrows():
            result_by_query[str(row["query_id"])] = row.to_dict()
    rows: list[dict[str, Any]] = []
    for _, row in manifest.iterrows():
        qid = str(row["spec_id"])
        result = result_by_query.get(qid, {})
        status = str(result.get("status", "pending_candidate_spectra"))
        completed = status in {"completed", "completed_cached"}
        missing_spectra = result.get("missing_candidate_spectra", np.nan)
        rows.append(
            {
                "supported_index": int(row["supported_index"]),
                "query_id": qid,
                "query_mol_id": int(row["query_mol_id"]),
                "adduct": str(row["adduct"]),
                "precursor_mz": float(row["precursor_mz"]),
                "candidate_count": int(row["candidate_count"]),
                "status": status,
                "completed": bool(completed),
                "ranked_rows": result.get("ranked_rows", np.nan),
                "missing_candidate_spectra": missing_spectra,
                "true_rank": result.get("true_rank", np.nan),
                "rank_output_file": row.get("rank_output_file", ""),
            }
        )
    return pd.DataFrame(rows)


def unsupported_adduct_strategy() -> pd.DataFrame:
    spec = pd.read_pickle(CASMI_DIR / "spec_df.pkl")
    cand = pd.read_pickle(CASMI_DIR / "cand_df.pkl")
    model_root = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
    model_adducts = {p.name for p in model_root.iterdir() if p.is_dir()} if model_root.exists() else set()
    counts = cand.groupby("query_mol_id")["candidate_mol_id"].size()
    unsupported = spec[~spec["prec_type"].astype(str).isin(model_adducts)].copy()
    rows: list[dict[str, Any]] = []
    for _, row in unsupported.iterrows():
        mol_id = int(row["mol_id"])
        rows.append(
            {
                "query_id": str(row["spec_id"]),
                "query_mol_id": mol_id,
                "adduct": str(row["prec_type"]),
                "precursor_mz": float(row["prec_mz"]),
                "candidate_count": int(counts.get(mol_id, 0)),
                "cfmid4_supported": False,
                "primary_strategy": "report_as_unsupported_adduct_stratum",
                "include_in_native_cfmid_supported_metric": False,
                "convert_to_other_adduct": False,
                "strategy_reason": (
                    "The local cfmid4 model directory has no [M+Na]+ model. "
                    "Converting [M+Na]+ spectra to [M+H]+ would change ion/adduct "
                    "fragmentation assumptions and is not a native CFM-ID evaluation."
                ),
                "future_options": (
                    "Add a validated [M+Na]+ CFM-ID model, run a separate sodium-adduct "
                    "external model, or report [M+Na]+ as an unsupported CASMI stratum."
                ),
            }
        )
    return pd.DataFrame(rows)


def ms2deepscore_readiness(
    cfmid_summary: dict[str, Any],
    shard_df: pd.DataFrame,
    query_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    audit = read_json(MS2_AUDIT)
    env = audit.get("external_ms2deepscore_environment", {})
    model_cache = audit.get("external_pretrained_model_cache", {})
    candidate_total = int(cfmid_summary.get("expected_unique_candidate_spectra", 0) or 0)
    candidate_done = int(cfmid_summary.get("completed_candidate_spectra", 0) or 0)
    supported_queries = int(cfmid_summary.get("n_supported_queries", 0) or 0)
    completed_queries = int(cfmid_summary.get("n_completed_queries", 0) or 0)
    full_cfmid_library_ready = candidate_total > 0 and candidate_done == candidate_total
    full_query_cache_ready = supported_queries > 0 and completed_queries == supported_queries
    rows = [
        {
            "gate": "MS2DeepScore package and pretrained model",
            "ready": bool(env.get("status") == "verified" and model_cache.get("all_required_files_present")),
            "evidence": (
                f"env_status={env.get('status')}; ms2deepscore={env.get('ms2deepscore_version')}; "
                f"matchms={env.get('matchms_version')}; model_files_present={model_cache.get('all_required_files_present')}"
            ),
            "required_next_step": "none for environment; keep model cache outside Git",
        },
        {
            "gate": "full CFM-ID-generated candidate spectrum library for hybrid MS2DeepScore",
            "ready": full_cfmid_library_ready,
            "evidence": f"{candidate_done}/{candidate_total} candidate spectra available",
            "required_next_step": "complete remaining CFM-ID candidate-spectrum shards before full hybrid scoring",
        },
        {
            "gate": "full supported-query CFM-ID cache/ranking for hybrid input coverage",
            "ready": full_query_cache_ready,
            "evidence": f"{completed_queries}/{supported_queries} supported CFM-ID query rankings complete",
            "required_next_step": "rank all 170 supported queries after candidate spectra are complete",
        },
        {
            "gate": "native MS2DeepScore measured/predicted candidate spectrum library independent of CFM-ID",
            "ready": False,
            "evidence": "No complete independent CASMI candidate spectrum library is present in the repository.",
            "required_next_step": (
                "Provide measured spectra or a non-CFM-ID generator for every CASMI candidate; "
                "otherwise label the benchmark as CFM-ID + MS2DeepScore hybrid."
            ),
        },
    ]
    readiness = {
        "full_casmi_native_ms2deepscore_ready": False,
        "full_casmi_cfmid_ms2deepscore_hybrid_ready": bool(
            env.get("status") == "verified"
            and model_cache.get("all_required_files_present")
            and full_cfmid_library_ready
            and full_query_cache_ready
        ),
        "completed_candidate_spectra": candidate_done,
        "expected_candidate_spectra": candidate_total,
        "remaining_candidate_spectrum_shards": int((~shard_df["status"].eq("completed")).sum()) if not shard_df.empty else 0,
        "remaining_supported_query_rankings": int((~query_df["completed"]).sum()) if not query_df.empty else 0,
    }
    return pd.DataFrame(rows), readiness


def harmonized_sota_rerun_manifest() -> pd.DataFrame:
    external_root = Path("/home/zhome/ec_structure/external_ms_models")
    models = [
        {
            "model": "ICEBERG",
            "local_resource": external_root / "vendor" / "ms-pred-iceberg-2024",
            "env": external_root / "envs" / "ms_pred_iceberg_sys",
            "current_status": "resource_detected_not_harmonized",
            "required_wrapper": "CASMI candidate-set inference wrapper for all 229 queries and all candidate structures",
        },
        {
            "model": "MassFormer",
            "local_resource": external_root / "vendor" / "massformer",
            "env": external_root / "envs" / "massformer",
            "current_status": "resource_detected_not_harmonized",
            "required_wrapper": "CASMI candidate-set inference wrapper for all 229 queries and all candidate structures",
        },
        {
            "model": "NEIMS",
            "local_resource": external_root / "vendor" / "ms-pred",
            "env": external_root / "envs" / "ms_pred_iceberg_sys",
            "current_status": "no_harmonized_neims_wrapper_present",
            "required_wrapper": "NEIMS-compatible CASMI candidate-set inference wrapper or documented unavailable status",
        },
    ]
    rows: list[dict[str, Any]] = []
    for item in models:
        rows.append(
            {
                "model": item["model"],
                "local_resource": str(item["local_resource"]),
                "local_resource_exists": item["local_resource"].exists(),
                "env": str(item["env"]),
                "env_exists": item["env"].exists(),
                "harmonized_candidate_set": "data/proc/casmi_2022/spec_df.pkl + cand_df.pkl + all_smiles.txt",
                "required_outputs": (
                    "candidate-level predictions, query-level Top-1/Top-5/Top-10/MRR, "
                    "Tanimoto and formula accuracy on the same CASMI candidate set"
                ),
                "current_status": item["current_status"],
                "claim_status": "blocked_until_harmonized_rerun_completes",
                "required_wrapper": item["required_wrapper"],
            }
        )
    return pd.DataFrame(rows)


def write_runbook(
    shard_df: pd.DataFrame,
    query_df: pd.DataFrame,
    ms2_ready: dict[str, Any],
) -> None:
    remaining_shards = shard_df[~shard_df["status"].eq("completed")].copy() if not shard_df.empty else pd.DataFrame()
    next_shards = remaining_shards.head(25)
    lines = [
        "# CASMI Full Completion Runbook",
        "",
        "This runbook does not fabricate missing scores. It lists the exact gates still needed before full CASMI claims.",
        "",
        "## CFM-ID Full Supported CASMI",
        "",
        "For interactive or unstable sessions, run small resumable micro-batches:",
        "",
        "```bash",
        "python3 scripts/run_cfmid_precomputed_candidate_micro_batch.py --max-candidates 20 --max-range-len 20 --timeout-seconds 3600",
        "```",
        "",
        "For long server sessions, use the full shard runner:",
        "",
        "Run all remaining candidate-spectrum shards first:",
        "",
        "```bash",
        "bash results/cfmid_precomputed_full_casmi_manifest_v1/run_candidate_spectrum_shards_sequential.sh",
        "python3 scripts/summarize_cfmid_precomputed_full_progress.py",
        "```",
        "",
        "Then run query ranking shards:",
        "",
        "```bash",
        "bash results/cfmid_precomputed_full_casmi_manifest_v1/run_query_ranking_shards_after_spectra.sh",
        "python3 scripts/summarize_cfmid_precomputed_full_progress.py",
        "```",
        "",
        "Report full native CFM-ID metrics only when `status == completed_full_supported`.",
        "",
        "Next not-completed candidate-spectrum shards:",
        "",
        next_shards[["shard_id", "adduct", "candidate_start", "candidate_limit", "status", "command"]].to_markdown(index=False)
        if not next_shards.empty
        else "No remaining candidate-spectrum shards.",
        "",
        "## [M+Na]+ Queries",
        "",
        "Primary policy: report the 59 `[M+Na]+` CASMI queries as an unsupported adduct stratum for native CFM-ID. Do not convert them to `[M+H]+` for native CFM-ID metrics unless a validated conversion protocol and sodium-adduct model are added.",
        "",
        "## MS2DeepScore",
        "",
        f"Full native MS2DeepScore ready: `{ms2_ready['full_casmi_native_ms2deepscore_ready']}`.",
        f"Full CFM-ID + MS2DeepScore hybrid ready: `{ms2_ready['full_casmi_cfmid_ms2deepscore_hybrid_ready']}`.",
        "The hybrid can run only after the full CFM-ID candidate spectrum library and all supported-query coverage are complete.",
        "",
        "## Harmonized ICEBERG/MassFormer/NEIMS",
        "",
        "Use the same CASMI candidate set (`spec_df.pkl`, `cand_df.pkl`, `all_smiles.txt`) and the same Top-k/MRR/Tanimoto/formula metrics. Public notebook numbers remain external context only until these reruns complete.",
        "",
    ]
    (OUTDIR / "casmi_full_completion_runbook.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    manifest_audit = read_json(MANIFEST_DIR / "audit_summary.json")
    cfmid_summary = read_json(CFMID_RUN_DIR / "audit_summary.json")

    shard_df = candidate_shard_status()
    query_df = query_completion_status()
    unsupported_df = unsupported_adduct_strategy()
    ms2_gate_df, ms2_ready = ms2deepscore_readiness(cfmid_summary, shard_df, query_df)
    sota_df = harmonized_sota_rerun_manifest()

    remaining_shards = shard_df[~shard_df["status"].eq("completed")].copy() if not shard_df.empty else pd.DataFrame()
    remaining_queries = query_df[~query_df["completed"]].copy() if not query_df.empty else pd.DataFrame()
    full_status_rows = [
        {
            "requirement": "CFM-ID complete all 170 supported CASMI queries",
            "status": "incomplete",
            "current_evidence": f"{cfmid_summary.get('n_completed_queries', 0)}/{cfmid_summary.get('n_supported_queries', 0)} supported queries complete",
            "completion_gate": "all 170 supported query rows completed after full candidate spectra exist",
            "next_action": "run remaining CFM-ID candidate-spectrum shards, then query-ranking shards",
        },
        {
            "requirement": "Generate 936,483 CFM-ID candidate spectra or faster precomputed method",
            "status": "incomplete_precomputed_method_prepared",
            "current_evidence": (
                f"{cfmid_summary.get('completed_candidate_spectra', 0)}/"
                f"{cfmid_summary.get('expected_unique_candidate_spectra', manifest_audit.get('candidate_spectrum_shards', 0))} "
                "unique candidate spectra complete; precomputed shard method exists"
            ),
            "completion_gate": "candidate_spectrum_completion_fraction == 1.0",
            "next_action": "run remaining candidate-spectrum shards with resume enabled",
        },
        {
            "requirement": "Strategy for 59 unsupported [M+Na]+ CASMI queries",
            "status": "strategy_defined_report_separate_unsupported_stratum",
            "current_evidence": f"{len(unsupported_df)} unsupported [M+Na]+ rows exported",
            "completion_gate": "strategy table and report state no adduct conversion for native CFM-ID metrics",
            "next_action": "add a validated [M+Na]+ model only if sodium-adduct native metrics are required",
        },
        {
            "requirement": "MS2DeepScore full CASMI candidate spectrum library",
            "status": "blocked_until_candidate_library_complete",
            "current_evidence": (
                f"MS2DeepScore env verified, but hybrid library coverage is "
                f"{ms2_ready['completed_candidate_spectra']}/{ms2_ready['expected_candidate_spectra']}"
            ),
            "completion_gate": "complete independent native library, or complete CFM-ID library and label as hybrid",
            "next_action": "complete CFM-ID spectra for hybrid MS2DeepScore; provide independent spectra for native MS2DeepScore",
        },
        {
            "requirement": "ICEBERG/MassFormer/NEIMS harmonized candidate-set reruns",
            "status": "blocked_until_wrappers_run",
            "current_evidence": "local resources detected for ICEBERG/MassFormer; no harmonized FragAnnotor candidate-set rerun outputs exist",
            "completion_gate": "candidate-level and query-level outputs on the same CASMI candidate set for all three models",
            "next_action": "build/run harmonized inference wrappers using data/proc/casmi_2022 inputs",
        },
    ]
    full_status_df = pd.DataFrame(full_status_rows)

    shard_df.to_csv(OUTDIR / "cfmid_candidate_spectrum_shard_status.csv", index=False)
    remaining_shards.head(200).to_csv(OUTDIR / "cfmid_next_candidate_spectrum_shards.csv", index=False)
    query_df.to_csv(OUTDIR / "cfmid_supported_query_status.csv", index=False)
    remaining_queries.to_csv(OUTDIR / "cfmid_remaining_supported_queries.csv", index=False)
    unsupported_df.to_csv(OUTDIR / "unsupported_mna_query_strategy.csv", index=False)
    ms2_gate_df.to_csv(OUTDIR / "ms2deepscore_full_library_readiness.csv", index=False)
    sota_df.to_csv(OUTDIR / "harmonized_sota_rerun_manifest.csv", index=False)
    full_status_df.to_csv(OUTDIR / "full_completion_status.csv", index=False)

    write_runbook(shard_df, query_df, ms2_ready)
    audit = {
        "stage": "casmi_full_completion_audit_v1",
        "full_objective_complete": False,
        "cfmid_supported_queries_complete": False,
        "cfmid_candidate_spectra_complete": False,
        "mna_strategy_defined": True,
        "ms2deepscore_full_native_ready": ms2_ready["full_casmi_native_ms2deepscore_ready"],
        "ms2deepscore_full_hybrid_ready": ms2_ready["full_casmi_cfmid_ms2deepscore_hybrid_ready"],
        "harmonized_sota_reruns_complete": False,
        "cfmid_completed_queries": cfmid_summary.get("n_completed_queries", 0),
        "cfmid_supported_queries": cfmid_summary.get("n_supported_queries", 0),
        "cfmid_completed_candidate_spectra": cfmid_summary.get("completed_candidate_spectra", 0),
        "cfmid_expected_candidate_spectra": cfmid_summary.get("expected_unique_candidate_spectra", 0),
        "remaining_candidate_spectrum_shards": int(len(remaining_shards)),
        "remaining_supported_queries": int(len(remaining_queries)),
        "unsupported_mna_queries": int(len(unsupported_df)),
        "outputs": [
            "full_completion_status.csv",
            "cfmid_candidate_spectrum_shard_status.csv",
            "cfmid_next_candidate_spectrum_shards.csv",
            "cfmid_supported_query_status.csv",
            "cfmid_remaining_supported_queries.csv",
            "unsupported_mna_query_strategy.csv",
            "ms2deepscore_full_library_readiness.csv",
            "harmonized_sota_rerun_manifest.csv",
            "casmi_full_completion_runbook.md",
        ],
    }
    write_json(OUTDIR / "audit_summary.json", audit)
    print(json.dumps(json_safe(audit), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
