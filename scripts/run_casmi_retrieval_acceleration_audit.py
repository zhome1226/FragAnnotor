#!/usr/bin/env python3
"""Audit low-cost CASMI candidate gates before expensive spectrum reranking.

This script does not train weights and does not replace full native CFM-ID
metrics.  It estimates whether existing FragAnnotor/formula components can be
used as a first-stage retrieval gate to reduce expensive CFM-ID/MS2DeepScore
candidate scoring while preserving the true candidate in top-K.
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from msms_metrics import peak_count_summary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPONENT_MATRIX = (
    ROOT
    / "results"
    / "casmi2022_fragannotor_formal_components"
    / "casmi2022_fragannotor_formal_component_matrix.csv.gz"
)
DEFAULT_QUERY_RESULTS = (
    ROOT
    / "results"
    / "casmi2022_fragannotor_formal_components"
    / "casmi2022_fragannotor_formal_query_results.csv"
)
DEFAULT_MANIFEST_DIR = ROOT / "results" / "cfmid_precomputed_full_casmi_manifest_v1"
DEFAULT_OUTDIR = ROOT / "results" / "casmi_retrieval_acceleration_audit_v1"
CASMI_DIR_CANDIDATES = [
    ROOT / "data" / "proc" / "casmi_2022",
    ROOT.parent / "FragAnnotor" / "data" / "proc" / "casmi_2022",
    Path("/home/zhome/ec_structure/github_export/FragAnnotor/data/proc/casmi_2022"),
]


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def resolve_casmi_dir(path_arg: str | None) -> Path:
    candidates = [Path(path_arg)] if path_arg else []
    candidates.extend(CASMI_DIR_CANDIDATES)
    for path in candidates:
        if path and (path / "spec_df.pkl").exists():
            return path
    raise FileNotFoundError("Could not find CASMI spec_df.pkl; pass --casmi-dir explicitly.")


def true_candidate_table(casmi_dir: Path) -> pd.DataFrame:
    spec = pd.read_pickle(casmi_dir / "spec_df.pkl")
    rows = spec[["spec_id", "mol_id", "prec_type", "prec_mz", "ion_mode", "peaks"]].copy()
    rows["query_id"] = rows["spec_id"].astype(int)
    rows["true_candidate_id"] = "CASMI_MOL_" + rows["mol_id"].astype(int).astype(str)
    rows = rows.rename(columns={"prec_type": "adduct", "prec_mz": "precursor_mz"})
    return rows


def load_component_matrix(path: Path, truth: pd.DataFrame) -> pd.DataFrame:
    usecols = [
        "spectrum_id",
        "query_id",
        "candidate_id",
        "candidate_formula",
        "fragannotor_formal_component_score",
        "sirius_formula_plausibility_score",
        "precursor_mass_consistency_score",
        "fragment_formula_plausibility_score",
    ]
    matrix = pd.read_csv(path, usecols=usecols)
    matrix["query_id"] = matrix["query_id"].astype(int)
    merged = matrix.merge(
        truth[["query_id", "true_candidate_id", "adduct", "precursor_mz"]],
        on="query_id",
        how="left",
        validate="many_to_one",
    )
    merged["is_true_candidate"] = merged["candidate_id"].astype(str).eq(merged["true_candidate_id"].astype(str))
    for col in [
        "fragannotor_formal_component_score",
        "sirius_formula_plausibility_score",
        "precursor_mass_consistency_score",
        "fragment_formula_plausibility_score",
    ]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
    return merged


def score_policy_metrics(matrix: pd.DataFrame, policies: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame]:
    query_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    query_count = int(matrix["query_id"].nunique())

    for policy_name, scores in policies.items():
        scored = matrix[["query_id", "candidate_id", "is_true_candidate"]].copy()
        scored["score"] = pd.to_numeric(scores, errors="coerce").fillna(-np.inf)
        scored = scored.sort_values(["query_id", "score", "candidate_id"], ascending=[True, False, True])
        scored["rank"] = scored.groupby("query_id").cumcount() + 1
        true_rows = scored[scored["is_true_candidate"]].copy()
        candidate_counts = scored.groupby("query_id").size().rename("candidate_count")
        true_rows = true_rows.merge(candidate_counts, on="query_id", how="left")
        true_rows["top1_correct"] = true_rows["rank"].le(1)
        true_rows["top5_correct"] = true_rows["rank"].le(5)
        true_rows["top10_correct"] = true_rows["rank"].le(10)
        true_rows["reciprocal_rank"] = 1.0 / true_rows["rank"].astype(float)
        true_rows["score_policy"] = policy_name
        query_rows.extend(true_rows.to_dict(orient="records"))
        summary_rows.append(
            {
                "score_policy": policy_name,
                "n_queries": query_count,
                "queries_with_true_candidate": int(len(true_rows)),
                "top1_accuracy": float(true_rows["top1_correct"].mean()),
                "top5_accuracy": float(true_rows["top5_correct"].mean()),
                "top10_accuracy": float(true_rows["top10_correct"].mean()),
                "mean_reciprocal_rank": float(true_rows["reciprocal_rank"].mean()),
                "median_true_rank": float(true_rows["rank"].median()),
                "mean_candidate_count": float(true_rows["candidate_count"].mean()),
            }
        )

    return pd.DataFrame(summary_rows), pd.DataFrame(query_rows)


def gate_retention_table(query_ranks: pd.DataFrame, topk_values: list[int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for policy_name, group in query_ranks.groupby("score_policy"):
        for topk in topk_values:
            retained = group["rank"].le(topk)
            gated_counts = np.minimum(group["candidate_count"].astype(int), int(topk))
            rows.append(
                {
                    "gate_policy": policy_name,
                    "top_k_gate": int(topk),
                    "n_queries": int(len(group)),
                    "true_candidate_retention": float(retained.mean()),
                    "queries_losing_true_candidate": int((~retained).sum()),
                    "mean_gated_candidate_count": float(gated_counts.mean()),
                    "median_gated_candidate_count": float(np.median(gated_counts)),
                    "mean_original_candidate_count": float(group["candidate_count"].mean()),
                    "candidate_row_reduction_fraction": float(1.0 - gated_counts.sum() / group["candidate_count"].sum()),
                }
            )
    return pd.DataFrame(rows)


def union_gate_retention_table(
    matrix: pd.DataFrame,
    policies: dict[str, pd.Series],
    *,
    gate_sets: dict[str, list[str]],
    topk_values: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate union gates that keep top-K candidates from multiple cheap policies."""

    base = matrix[["query_id", "candidate_id", "is_true_candidate"]].copy()
    ranked_by_policy: dict[str, pd.DataFrame] = {}
    for policy_name, scores in policies.items():
        scored = base.copy()
        scored["score"] = pd.to_numeric(scores, errors="coerce").fillna(-np.inf)
        scored = scored.sort_values(["query_id", "score", "candidate_id"], ascending=[True, False, True])
        scored["policy_rank"] = scored.groupby("query_id").cumcount() + 1
        ranked_by_policy[policy_name] = scored[["query_id", "candidate_id", "policy_rank"]]

    original_counts = base.groupby("query_id").size().rename("original_candidate_count")
    truth = base[base["is_true_candidate"]][["query_id", "candidate_id"]].rename(columns={"candidate_id": "true_candidate_id"})
    summary_rows: list[dict[str, Any]] = []
    query_rows: list[dict[str, Any]] = []

    for gate_name, policy_names in gate_sets.items():
        missing = [name for name in policy_names if name not in ranked_by_policy]
        if missing:
            continue
        for topk in topk_values:
            kept_parts = []
            for policy_name in policy_names:
                kept = ranked_by_policy[policy_name][ranked_by_policy[policy_name]["policy_rank"].le(topk)]
                kept_parts.append(kept[["query_id", "candidate_id"]])
            kept_union = pd.concat(kept_parts, ignore_index=True).drop_duplicates(["query_id", "candidate_id"])
            kept_counts = kept_union.groupby("query_id").size().rename("gated_candidate_count")
            retained = truth.merge(
                kept_union.assign(retained=True),
                left_on=["query_id", "true_candidate_id"],
                right_on=["query_id", "candidate_id"],
                how="left",
            )
            retained["retained"] = retained["retained"].fillna(False).astype(bool)
            retained = retained.merge(original_counts, on="query_id", how="left")
            retained = retained.merge(kept_counts, on="query_id", how="left")
            retained["gated_candidate_count"] = retained["gated_candidate_count"].fillna(0).astype(int)
            retained["union_gate"] = gate_name
            retained["per_policy_top_k"] = int(topk)
            query_rows.extend(retained.to_dict(orient="records"))
            summary_rows.append(
                {
                    "union_gate": gate_name,
                    "policies": "+".join(policy_names),
                    "per_policy_top_k": int(topk),
                    "n_queries": int(len(retained)),
                    "true_candidate_retention": float(retained["retained"].mean()),
                    "queries_losing_true_candidate": int((~retained["retained"]).sum()),
                    "mean_gated_candidate_count": float(retained["gated_candidate_count"].mean()),
                    "median_gated_candidate_count": float(retained["gated_candidate_count"].median()),
                    "mean_original_candidate_count": float(retained["original_candidate_count"].mean()),
                    "candidate_row_reduction_fraction": float(
                        1.0 - retained["gated_candidate_count"].sum() / retained["original_candidate_count"].sum()
                    ),
                }
            )

    return pd.DataFrame(summary_rows), pd.DataFrame(query_rows)


def spectrum_cleaning_audit(truth: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in truth.iterrows():
        counts = peak_count_summary(row.get("peaks", []), precursor_mz=row.get("precursor_mz"))
        rows.append(
            {
                "query_id": int(row["query_id"]),
                "adduct": row.get("adduct", ""),
                "precursor_mz": row.get("precursor_mz", np.nan),
                **counts,
            }
        )
    return pd.DataFrame(rows)


def cfmid_workload_projection(manifest_dir: Path, topk_values: list[int], supported_query_ids: set[int]) -> pd.DataFrame:
    manifest_path = manifest_dir / "cfmid_precomputed_supported_query_manifest.csv"
    if not manifest_path.exists():
        return pd.DataFrame()
    manifest = pd.read_csv(manifest_path)
    if "spec_id" in manifest.columns:
        manifest["query_id"] = manifest["spec_id"].astype(int)
    if supported_query_ids:
        manifest = manifest[manifest["query_id"].isin(supported_query_ids)].copy()
    rows = []
    total = int(manifest["candidate_count"].sum()) if not manifest.empty else 0
    for topk in topk_values:
        gated = np.minimum(manifest["candidate_count"].astype(int), int(topk))
        rows.append(
            {
                "top_k_gate": int(topk),
                "supported_queries": int(len(manifest)),
                "full_supported_candidate_rows": total,
                "projected_gated_candidate_rows": int(gated.sum()),
                "projected_candidate_row_reduction_fraction": float(1.0 - gated.sum() / total) if total else np.nan,
                "note": "Projection assumes the first-stage gate can be computed for the full supported candidate set; it is not a native CFM-ID metric.",
            }
        )
    return pd.DataFrame(rows)


def write_report(
    outdir: Path,
    audit: dict[str, Any],
    score_summary: pd.DataFrame,
    gate_summary: pd.DataFrame,
    union_summary: pd.DataFrame,
) -> None:
    best_100 = gate_summary[(gate_summary["gate_policy"].eq("fragannotor_formal_component_score")) & (gate_summary["top_k_gate"].eq(100))]
    best_200 = gate_summary[(gate_summary["gate_policy"].eq("fragannotor_formal_component_score")) & (gate_summary["top_k_gate"].eq(200))]
    union_best = union_summary.sort_values(
        ["true_candidate_retention", "candidate_row_reduction_fraction", "mean_gated_candidate_count"],
        ascending=[False, False, True],
    ).head(1)
    lines = [
        "# CASMI Retrieval Acceleration Audit",
        "",
        "This branch tests a first-stage candidate gate before expensive native spectrum reranking. It does not train weights, does not tune on CASMI, and does not replace the ongoing full native CFM-ID run.",
        "",
        "## Key Findings",
        "",
        f"- Component matrix rows: `{audit['component_matrix_rows']}` across `{audit['queries']}` queries.",
        f"- Mean candidate rows per query: `{audit['mean_candidate_count']:.1f}`.",
    ]
    if not best_100.empty:
        row = best_100.iloc[0]
        lines.append(
            f"- FragAnnotor top-100 gate retains the true candidate for `{row['true_candidate_retention']:.3f}` of queries while reducing candidate rows by `{row['candidate_row_reduction_fraction']:.3f}`."
        )
    if not best_200.empty:
        row = best_200.iloc[0]
        lines.append(
            f"- FragAnnotor top-200 gate retains the true candidate for `{row['true_candidate_retention']:.3f}` of queries while reducing candidate rows by `{row['candidate_row_reduction_fraction']:.3f}`."
        )
    if not union_best.empty:
        row = union_best.iloc[0]
        lines.append(
            f"- Best tested union gate `{row['union_gate']}` at per-policy top-{int(row['per_policy_top_k'])} retains `{row['true_candidate_retention']:.3f}` of true candidates with mean gated candidate count `{row['mean_gated_candidate_count']:.1f}`."
        )
    practical = union_summary[
        (union_summary["union_gate"].eq("union_fragannotor_sirius_fragment"))
        & (union_summary["per_policy_top_k"].isin([50, 100, 200]))
    ]
    if not practical.empty:
        parts = []
        for _, row in practical.iterrows():
            parts.append(
                f"top-{int(row['per_policy_top_k'])}: retention {row['true_candidate_retention']:.3f}, "
                f"mean candidates {row['mean_gated_candidate_count']:.1f}, reduction {row['candidate_row_reduction_fraction']:.3f}"
            )
        lines.append("- Practical union gate range (`FragAnnotor + SIRIUS + fragment-formula`): " + "; ".join(parts) + ".")
    def markdown_table(df: pd.DataFrame) -> str:
        cols = list(df.columns)
        rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for _, row in df.iterrows():
            values = []
            for col in cols:
                value = row[col]
                if isinstance(value, float):
                    values.append(f"{value:.6g}")
                else:
                    values.append(str(value))
            rows.append("| " + " | ".join(values) + " |")
        return "\n".join(rows)

    lines.extend(
        [
            "",
            "## Score Policy Summary",
            "",
            markdown_table(score_summary),
            "",
            "## Union Gate Summary",
            "",
            markdown_table(union_summary),
            "",
            "## Interpretation",
            "",
            "- Acceleration potential is high if CFM-ID/MS2DeepScore are used as second-stage rerankers on a retained top-K set.",
            "- The tested gates do not improve accuracy by themselves; they trade recall for runtime and need validation-only threshold/top-K selection before locked reporting.",
            "- This is not a full native CFM-ID baseline because CFM-ID is not run over every supported candidate.",
            "- A production path should use validation-only gate selection, then report locked-test behavior separately.",
            "- The shared `scripts/msms_metrics.py` module provides a dependency-light spectrum cleaning and similarity layer; if matchms is installed, it should be used as the stricter reference implementation.",
            "",
        ]
    )
    (outdir / "casmi_retrieval_acceleration_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component-matrix", type=Path, default=DEFAULT_COMPONENT_MATRIX)
    parser.add_argument("--query-results", type=Path, default=DEFAULT_QUERY_RESULTS)
    parser.add_argument("--casmi-dir", type=str, default=None)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--topk", type=str, default="10,25,50,100,200,500,1000")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    topk_values = [int(x) for x in args.topk.split(",") if x.strip()]
    casmi_dir = resolve_casmi_dir(args.casmi_dir)
    truth = true_candidate_table(casmi_dir)
    matrix = load_component_matrix(args.component_matrix, truth)

    policies = {
        "fragannotor_formal_component_score": matrix["fragannotor_formal_component_score"],
        "precursor_mass_consistency_score": matrix["precursor_mass_consistency_score"],
        "fragment_formula_plausibility_score": matrix["fragment_formula_plausibility_score"],
        "sirius_formula_plausibility_score_nan0": matrix["sirius_formula_plausibility_score"].fillna(0.0),
        "no_sirius_precursor80_fragment20": (
            0.8 * matrix["precursor_mass_consistency_score"].fillna(0.0)
            + 0.2 * matrix["fragment_formula_plausibility_score"].fillna(0.0)
        ),
        "no_sirius_precursor50_fragment50": (
            0.5 * matrix["precursor_mass_consistency_score"].fillna(0.0)
            + 0.5 * matrix["fragment_formula_plausibility_score"].fillna(0.0)
        ),
    }
    score_summary, query_ranks = score_policy_metrics(matrix, policies)
    gate_summary = gate_retention_table(query_ranks, topk_values)
    union_gate_sets = {
        "union_fragannotor_sirius": [
            "fragannotor_formal_component_score",
            "sirius_formula_plausibility_score_nan0",
        ],
        "union_fragannotor_sirius_fragment": [
            "fragannotor_formal_component_score",
            "sirius_formula_plausibility_score_nan0",
            "fragment_formula_plausibility_score",
        ],
        "union_all_low_cost": [
            "fragannotor_formal_component_score",
            "sirius_formula_plausibility_score_nan0",
            "fragment_formula_plausibility_score",
            "precursor_mass_consistency_score",
        ],
    }
    union_summary, union_query = union_gate_retention_table(
        matrix,
        policies,
        gate_sets=union_gate_sets,
        topk_values=topk_values,
    )
    cleaning = spectrum_cleaning_audit(truth)
    supported_query_ids = set(matrix["query_id"].astype(int).unique())
    cfmid_projection = cfmid_workload_projection(args.manifest_dir, topk_values, supported_query_ids)

    score_summary.to_csv(args.outdir / "score_policy_metrics.csv", index=False)
    query_ranks.to_csv(args.outdir / "query_level_gate_audit.csv", index=False)
    gate_summary.to_csv(args.outdir / "topk_gate_retention.csv", index=False)
    union_summary.to_csv(args.outdir / "union_gate_retention.csv", index=False)
    union_query.to_csv(args.outdir / "union_gate_query_level_audit.csv", index=False)
    cleaning.to_csv(args.outdir / "spectrum_cleaning_audit.csv", index=False)
    if not cfmid_projection.empty:
        cfmid_projection.to_csv(args.outdir / "cfmid_second_stage_workload_projection.csv", index=False)

    audit = {
        "stage": "casmi_retrieval_acceleration_audit_v1",
        "status": "completed",
        "branch_purpose": "Evaluate matchms-style preprocessing, leakage/metric consistency, and first-stage retrieval acceleration potential without changing model weights.",
        "component_matrix": str(args.component_matrix),
        "casmi_dir": str(casmi_dir),
        "component_matrix_rows": int(len(matrix)),
        "queries": int(matrix["query_id"].nunique()),
        "candidate_rows": int(len(matrix)),
        "unique_candidate_ids": int(matrix["candidate_id"].nunique()),
        "mean_candidate_count": float(matrix.groupby("query_id").size().mean()),
        "topk_values": topk_values,
        "rdkit_available": False,
        "matchms_required": False,
        "python": platform.python_version(),
        "outputs": [
            "score_policy_metrics.csv",
            "query_level_gate_audit.csv",
            "topk_gate_retention.csv",
            "union_gate_retention.csv",
            "union_gate_query_level_audit.csv",
            "spectrum_cleaning_audit.csv",
            "cfmid_second_stage_workload_projection.csv",
            "casmi_retrieval_acceleration_report.md",
        ],
        "guardrail": "Use this as a first-stage retrieval/gating audit only. Do not claim full native CFM-ID or MS2DeepScore results from gated reranking.",
    }
    (args.outdir / "audit_summary.json").write_text(json.dumps(json_safe(audit), indent=2, sort_keys=True), encoding="utf-8")
    write_report(args.outdir, audit, score_summary, gate_summary, union_summary)


if __name__ == "__main__":
    main()
