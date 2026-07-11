#!/usr/bin/env python3
"""Freeze Section 3.2 matched CASMI comparison inputs and current matched outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "results/manuscript_3_2_harmonized_comparison"
SUPPORTED = ROOT / "results/casmi_full_completion_audit_v1/cfmid_supported_query_status.csv"
FRAG_QUERY = ROOT / "results/casmi2022_fragannotor_formal_components/casmi2022_fragannotor_formal_query_results.csv"
COMPONENT_MATRIX = ROOT / "results/casmi2022_fragannotor_formal_components/casmi2022_fragannotor_formal_component_matrix.csv.gz"
CFMID_QUERY = ROOT / "results/casmi2022_cfmid_native_precomputed_full_v1/casmi2022_cfmid_native_precomputed_full_query_results.csv"
HYBRID_QUERY = ROOT / "results/casmi2022_cfmid_ms2deepscore_full_supported_hybrid_v1/casmi2022_cfmid_ms2deepscore_full_supported_hybrid_query_results.csv"
FINAL_CONFIG_AUDIT = ROOT / "outputs/manuscript_completion_v1/final_config_audit.json"
CASMI_DIR = ROOT / "data/proc/casmi_2022"

import sys
sys.path.insert(0, str(ROOT))
from run_benchmark import (  # noqa: E402
    casmi_fragannotor_adapter_components,
    formula_from_smiles,
    load_native_sirius_casmi_scores,
    parse_all_smiles,
    safe_float,
    safe_str,
)


def metric_summary(df: pd.DataFrame, model: str, status: str = "completed") -> dict[str, object]:
    work = df.copy()
    return {
        "model": model,
        "result_status": status,
        "n_queries": int(len(work)),
        "completed_queries": int(work["true_rank"].notna().sum()),
        "top1_accuracy": float(work["top1_correct"].mean()),
        "top5_accuracy": float(work["top5_correct"].mean()),
        "top10_accuracy": float(work["top10_correct"].mean()),
        "mean_reciprocal_rank": float(work["reciprocal_rank"].mean()),
        "median_true_rank": float(pd.to_numeric(work["true_rank"], errors="coerce").median()),
        "mean_top1_tanimoto": float(pd.to_numeric(work.get("top1_tanimoto", pd.Series([np.nan] * len(work))), errors="coerce").mean()),
        "formula_accuracy": float(work["formula_correct"].mean()) if "formula_correct" in work.columns else np.nan,
    }


def evaluate_component_variant(components: pd.DataFrame, score_col: str, model: str, native_or_fallback: str) -> tuple[pd.DataFrame, dict[str, object]]:
    rows = []
    for query_id, group in components.groupby("query_id", sort=True):
        ranked = (
            group.assign(score=pd.to_numeric(group[score_col], errors="coerce").fillna(0.0))
            .sort_values(["score", "candidate_id"], ascending=[False, True])
            .reset_index(drop=True)
        )
        correct = np.where(ranked["is_true_candidate"].astype(bool).to_numpy())[0]
        true_rank = np.nan if len(correct) == 0 else float(correct[0] + 1)
        top = ranked.iloc[0]
        rows.append({
            "dataset": "CASMI2022",
            "model": model,
            "status": "completed",
            "native_or_fallback": native_or_fallback,
            "query_id": int(query_id),
            "candidate_count": int(len(ranked)),
            "true_rank": true_rank,
            "top1_correct": bool(not pd.isna(true_rank) and true_rank == 1),
            "top5_correct": bool(not pd.isna(true_rank) and true_rank <= 5),
            "top10_correct": bool(not pd.isna(true_rank) and true_rank <= 10),
            "reciprocal_rank": 0.0 if pd.isna(true_rank) else 1.0 / true_rank,
            "top1_candidate_id": str(top["candidate_id"]),
            "top1_score": float(top["score"]),
        })
    qdf = pd.DataFrame(rows)
    return qdf, metric_summary(qdf, model)


def build_full_supported_component_matrix(supported: pd.DataFrame) -> pd.DataFrame:
    spec_df = pd.read_pickle(CASMI_DIR / "spec_df.pkl")
    cand_df = pd.read_pickle(CASMI_DIR / "cand_df.pkl")
    supported_query_mol_ids = set(supported["query_mol_id"].astype(int))
    spec = spec_df[spec_df["mol_id"].astype(int).isin(supported_query_mol_ids)].copy()
    cand = cand_df[cand_df["query_mol_id"].astype(int).isin(supported_query_mol_ids)].copy()

    selected_by_query = {
        int(k): v["candidate_mol_id"].astype(int).tolist()
        for k, v in cand.groupby("query_mol_id", sort=False)
    }
    needed_ids: set[int] = set()
    for query_mol_id, candidate_ids in selected_by_query.items():
        if query_mol_id not in candidate_ids:
            candidate_ids = [query_mol_id] + candidate_ids
            selected_by_query[query_mol_id] = candidate_ids
        needed_ids.update(candidate_ids)
        needed_ids.add(query_mol_id)
    id_to_smiles = parse_all_smiles(CASMI_DIR / "all_smiles.txt", set(needed_ids))
    formula_cache = {mol_id: formula_from_smiles(smiles) for mol_id, smiles in id_to_smiles.items()}
    native_sirius_scores = load_native_sirius_casmi_scores()
    supported_index_by_query_id = dict(zip(supported["query_id"].astype(int), supported["supported_index"].astype(int)))

    rows: list[dict[str, object]] = []
    for _, spec_row in spec.sort_values("spec_id").iterrows():
        query_id = int(spec_row["spec_id"])
        query_mol_id = int(spec_row["mol_id"])
        peaks = [(float(mz), float(intensity)) for mz, intensity in spec_row.get("peaks", [])]
        precursor_mz = safe_float(spec_row.get("prec_mz"), default=np.nan)
        adduct = safe_str(spec_row.get("prec_type"))
        ion_mode = safe_str(spec_row.get("ion_mode"))
        sirius_meta = native_sirius_scores.get(str(query_id), {})
        component_cache: dict[tuple[str, float], dict[str, float]] = {}
        for candidate_mol_id in selected_by_query.get(query_mol_id, []):
            smiles = id_to_smiles.get(int(candidate_mol_id), "")
            if not smiles:
                continue
            formula = formula_cache.get(int(candidate_mol_id), "") or formula_from_smiles(smiles)
            native_formula_score = sirius_meta.get("formula_scores", {}).get(formula, {})
            native_score = safe_float(native_formula_score.get("score"), default=np.nan) if native_formula_score else np.nan
            cache_key = (formula, -1.0 if pd.isna(native_score) else float(native_score))
            components = component_cache.get(cache_key)
            if components is None:
                components = casmi_fragannotor_adapter_components(formula, peaks, precursor_mz, adduct, ion_mode, native_score)
                component_cache[cache_key] = components
            rows.append({
                "supported_index": supported_index_by_query_id[query_id],
                "query_id": query_id,
                "query_mol_id": query_mol_id,
                "candidate_id": f"CASMI_MOL_{candidate_mol_id}",
                "candidate_formula": formula,
                "fragannotor_full_candidate_score": components["fragannotor_casmi_adapter_score"],
                "sirius_formula_plausibility_score": 0.0 if pd.isna(native_score) else float(native_score),
                "precursor_mass_consistency_score": components["casmi_mass_consistency_score"],
                "fragment_formula_plausibility_score": components["casmi_fragment_formula_score"],
                "is_true_candidate": int(candidate_mol_id == query_mol_id),
            })
    matrix = pd.DataFrame(rows)
    if matrix["query_id"].nunique() != 170:
        raise ValueError(f"Full supported component matrix covers {matrix['query_id'].nunique()} queries, expected 170")
    return matrix


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for path in [SUPPORTED, CFMID_QUERY, HYBRID_QUERY, FINAL_CONFIG_AUDIT, CASMI_DIR / "spec_df.pkl", CASMI_DIR / "cand_df.pkl", CASMI_DIR / "all_smiles.txt"]:
        if not path.exists():
            raise FileNotFoundError(path)

    supported = pd.read_csv(SUPPORTED).sort_values("supported_index").copy()
    if len(supported) != 170 or supported["query_id"].nunique() != 170:
        raise ValueError("Expected exactly 170 unique supported CFM-ID queries")
    supported_ids = set(supported["query_id"].astype(int))

    cfmid = pd.read_csv(CFMID_QUERY)
    cfmid_m = cfmid[cfmid["query_id"].astype(int).isin(supported_ids)].copy().sort_values("query_id")
    if len(cfmid_m) != 170:
        raise ValueError(f"Expected 170 matched CFM-ID rows, found {len(cfmid_m)}")

    hybrid = pd.read_csv(HYBRID_QUERY)
    hybrid_m = hybrid[hybrid["query_id"].astype(int).isin(supported_ids)].copy().sort_values("query_id")
    if len(hybrid_m) != 170:
        raise ValueError(f"Expected 170 matched hybrid rows, found {len(hybrid_m)}")

    comp_m = build_full_supported_component_matrix(supported)
    frag_m, frag_summary = evaluate_component_variant(
        comp_m,
        "fragannotor_full_candidate_score",
        "FragAnnotator",
        "formal_fixed_component_score_mode_full_supported_candidate_set",
    )
    sirius_q, sirius_summary = evaluate_component_variant(
        comp_m,
        "sirius_formula_plausibility_score",
        "SIRIUS formula-only",
        "native_sirius_formula_only_full_supported_candidate_set",
    )

    manifest = supported[[
        "supported_index",
        "query_id",
        "query_mol_id",
        "adduct",
        "precursor_mz",
        "candidate_count",
        "status",
        "completed",
    ]].copy()
    manifest["matched_manifest_version"] = "manuscript_3_2_matched_170_v1"
    manifest["in_fragannotator"] = manifest["query_id"].astype(int).isin(set(frag_m["query_id"].astype(int)))
    manifest["in_cfmid"] = manifest["query_id"].astype(int).isin(set(cfmid_m["query_id"].astype(int)))
    manifest["in_cfmid_ms2deepscore_hybrid"] = manifest["query_id"].astype(int).isin(set(hybrid_m["query_id"].astype(int)))
    manifest["in_sirius_formula_only"] = manifest["query_id"].astype(int).isin(set(sirius_q["query_id"].astype(int)))
    manifest.to_csv(OUTDIR / "matched_query_manifest.csv", index=False)

    candidate_audit = comp_m.groupby("query_id", as_index=False).agg(
        candidate_rows=("candidate_id", "count"),
        unique_candidate_ids=("candidate_id", "nunique"),
        true_candidate_rows=("is_true_candidate", "sum"),
        sirius_rows_with_score=("sirius_formula_plausibility_score", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
    )
    candidate_audit = candidate_audit.merge(supported[["query_id", "candidate_count"]], on="query_id", how="left")
    candidate_audit["candidate_count_matches_supported_audit"] = candidate_audit["candidate_rows"].astype(int).eq(candidate_audit["candidate_count"].astype(int))
    candidate_audit.to_csv(OUTDIR / "candidate_set_audit.csv", index=False)

    frag_m.to_csv(OUTDIR / "fragannotator_matched_query_results.csv", index=False)
    sirius_q.to_csv(OUTDIR / "sirius_formula_only_matched_query_results.csv", index=False)
    cfmid_m.to_csv(OUTDIR / "cfmid_native_matched_query_results.csv", index=False)
    hybrid_m.to_csv(OUTDIR / "cfmid_ms2deepscore_hybrid_matched_query_results.csv", index=False)

    summaries = [
        frag_summary,
        sirius_summary,
        metric_summary(cfmid_m, "CFM-ID"),
        metric_summary(hybrid_m, "CFM-ID-generated spectra + MS2DeepScore similarity hybrid"),
    ]
    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(OUTDIR / "available_model_summary.csv", index=False)

    config_audit = json.loads(FINAL_CONFIG_AUDIT.read_text(encoding="utf-8"))
    audit = {
        "stage": "manuscript_3_2_matched_inputs",
        "status": "matched_manifest_frozen_partial_models_available",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "matched_queries": int(len(manifest)),
        "models_with_matched_outputs_now": summary_df["model"].tolist(),
        "models_pending_completion": ["ICEBERG", "MassFormer", "NEIMS readiness audit"],
        "config_sha256": config_audit["config_sha256"],
        "claim_guardrail": "Do not use as final Section 3.2 main table until ICEBERG/MassFormer finish or are explicitly excluded by completed failure audits; NEIMS requires checkpoint/wrapper audit.",
    }
    (OUTDIR / "matched_input_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# Section 3.2 Matched CASMI Comparison Inputs",
        "",
        "This package freezes the current 170-query matched CASMI2022 `[M+H]+` manifest for harmonized model comparison.",
        "",
        "Current matched outputs are available for FragAnnotator, SIRIUS formula-only, native CFM-ID, and CFM-ID-generated candidate spectra + MS2DeepScore similarity hybrid.",
        "",
        "ICEBERG and MassFormer are still running/partial. NEIMS is not included until a reliable checkpoint and inference wrapper are validated.",
        "",
        "## Current Available Summary",
        "",
        summary_df.to_markdown(index=False),
        "",
        "## Guardrail",
        "",
        "This is not the final Section 3.2 main table while ICEBERG/MassFormer are partial. Do not compare 229-query Section 3.1 metrics to this matched 170-query table without explicit labeling.",
        "",
    ]
    (OUTDIR / "matched_input_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
