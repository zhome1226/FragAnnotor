#!/usr/bin/env python3
"""Generate Section 3.1 CASMI2022 FragAnnotator-only manuscript outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_QUERY_RESULTS = ROOT / "results/casmi2022_fragannotor_formal_components/casmi2022_fragannotor_formal_query_results.csv"
INPUT_SPEC_DF = ROOT / "data/proc/casmi_2022/spec_df.pkl"
FINAL_CONFIG_AUDIT = ROOT / "outputs/manuscript_completion_v1/final_config_audit.json"
OUTDIR = ROOT / "results/manuscript_3_1_casmi_overall"
FIGDIR = OUTDIR / "figures"


METRIC_COLUMNS = [
    "top1_accuracy",
    "top5_accuracy",
    "top10_accuracy",
    "mean_reciprocal_rank",
    "median_true_rank",
    "mean_top1_tanimoto",
    "median_top1_tanimoto",
    "molecular_formula_accuracy",
]


def load_inputs() -> pd.DataFrame:
    if not INPUT_QUERY_RESULTS.exists():
        raise FileNotFoundError(INPUT_QUERY_RESULTS)
    if not FINAL_CONFIG_AUDIT.exists():
        raise FileNotFoundError(FINAL_CONFIG_AUDIT)
    df = pd.read_csv(INPUT_QUERY_RESULTS)
    if INPUT_SPEC_DF.exists():
        spec = pd.read_pickle(INPUT_SPEC_DF)
        peak_counts = spec[["spec_id", "peaks"]].copy()
        peak_counts["query_id"] = peak_counts["spec_id"].astype(str)
        peak_counts["spectrum_peak_count"] = peak_counts["peaks"].map(lambda x: len(x) if isinstance(x, list) else 0)
        df["query_id"] = df["query_id"].astype(str)
        df = df.merge(peak_counts[["query_id", "spectrum_peak_count"]], on="query_id", how="left")
    else:
        df["spectrum_peak_count"] = np.nan
    df["difficulty_proxy"] = df["top1_tanimoto"]
    df["difficulty_proxy_label"] = "top1_candidate_tanimoto_to_truth"
    return df


def summarize(df: pd.DataFrame) -> dict[str, float | int | str]:
    valid = df[df["status"].astype(str).eq("completed")].copy()
    return {
        "section": "3.1",
        "model": "FragAnnotator",
        "method_family": "fixed_evidence_fusion_candidate_ranking",
        "n_queries": int(len(valid)),
        "rank_valid_queries": int(valid["true_rank"].notna().sum()),
        "top1_accuracy": float(valid["top1_correct"].mean()),
        "top5_accuracy": float(valid["top5_correct"].mean()),
        "top10_accuracy": float(valid["top10_correct"].mean()),
        "mean_reciprocal_rank": float(valid["reciprocal_rank"].mean()),
        "median_true_rank": float(valid["true_rank"].median()),
        "mean_top1_tanimoto": float(valid["top1_tanimoto"].mean()),
        "median_top1_tanimoto": float(valid["top1_tanimoto"].median()),
        "molecular_formula_accuracy": float(valid["formula_correct"].mean()),
        "mean_candidate_count": float(valid["candidate_count"].mean()),
        "median_candidate_count": float(valid["candidate_count"].median()),
    }


def bootstrap_ci(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    n = len(df)
    indices = np.arange(n)
    for metric, column, reducer in [
        ("top1_accuracy", "top1_correct", np.mean),
        ("top5_accuracy", "top5_correct", np.mean),
        ("top10_accuracy", "top10_correct", np.mean),
        ("mean_reciprocal_rank", "reciprocal_rank", np.mean),
        ("median_true_rank", "true_rank", np.median),
        ("mean_top1_tanimoto", "top1_tanimoto", np.nanmean),
        ("median_top1_tanimoto", "top1_tanimoto", np.nanmedian),
        ("molecular_formula_accuracy", "formula_correct", np.mean),
    ]:
        values = df[column].to_numpy()
        boots = []
        for _ in range(n_boot):
            sample = values[rng.choice(indices, size=n, replace=True)]
            boots.append(float(reducer(sample)))
        rows.append({
            "metric": metric,
            "estimate": float(reducer(values)),
            "ci95_low": float(np.nanpercentile(boots, 2.5)),
            "ci95_high": float(np.nanpercentile(boots, 97.5)),
            "n_bootstrap": n_boot,
            "seed": seed,
        })
    return pd.DataFrame(rows)


def bin_series(series: pd.Series, labels: list[str]) -> pd.Series:
    unique = series.dropna().nunique()
    if unique < 2:
        return pd.Series(["all"] * len(series), index=series.index)
    bins = pd.qcut(series, q=min(len(labels), unique), duplicates="drop")
    categories = bins.cat.categories
    rename = {cat: labels[i] if i < len(labels) else str(cat) for i, cat in enumerate(categories)}
    return bins.map(rename).astype("object")


def stratified_results(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["candidate_set_size_bin"] = bin_series(work["candidate_count"], ["small", "medium", "large", "very_large"])
    work["precursor_mz_bin"] = bin_series(work["precursor_mz"], ["low", "mid", "high", "very_high"])
    work["spectrum_peak_count_bin"] = bin_series(work["spectrum_peak_count"], ["few", "moderate", "many", "very_many"])
    work["candidate_similarity_difficulty_bin"] = bin_series(work["difficulty_proxy"], ["low_similarity", "mixed", "high_similarity", "near_identity"])
    work["formula_correct_bin"] = work["formula_correct"].map({True: "top1_formula_correct", False: "top1_formula_incorrect"})
    strata = [
        ("candidate_set_size", "candidate_set_size_bin"),
        ("precursor_mass", "precursor_mz_bin"),
        ("adduct", "adduct"),
        ("formula_correct_vs_incorrect", "formula_correct_bin"),
        ("spectrum_peak_count", "spectrum_peak_count_bin"),
        ("candidate_structural_similarity_difficulty", "candidate_similarity_difficulty_bin"),
    ]
    rows = []
    for stratum, column in strata:
        for level, group in work.groupby(column, dropna=False, observed=False):
            if len(group) == 0:
                continue
            summary = summarize(group)
            rows.append({
                "stratum": stratum,
                "level": "missing" if pd.isna(level) else str(level),
                **{k: summary[k] for k in METRIC_COLUMNS if k in summary},
                "n_queries": int(summary["n_queries"]),
                "mean_candidate_count": summary["mean_candidate_count"],
            })
    rows.append({
        "stratum": "collision_energy",
        "level": "unavailable_in_current_casmi_processed_table",
        "n_queries": int(len(work)),
        **{k: np.nan for k in METRIC_COLUMNS},
        "mean_candidate_count": float(work["candidate_count"].mean()),
    })
    return pd.DataFrame(rows)


def write_figures(summary: dict[str, float | int | str], query_df: pd.DataFrame, strat_df: pd.DataFrame) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGDIR.mkdir(parents=True, exist_ok=True)
    figure_paths = []

    metrics = [
        ("Top-1", summary["top1_accuracy"]),
        ("Top-5", summary["top5_accuracy"]),
        ("Top-10", summary["top10_accuracy"]),
        ("MRR", summary["mean_reciprocal_rank"]),
    ]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.bar([m[0] for m in metrics], [float(m[1]) for m in metrics], color=["#376d6a", "#649a7f", "#b7a767", "#6b6f8d"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title("CASMI2022 FragAnnotator performance")
    for i, (_, value) in enumerate(metrics):
        ax.text(i, float(value) + 0.02, f"{float(value):.3f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    path = FIGDIR / "figure_3_1_overall_topk_mrr.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    figure_paths.append(str(path.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ranks = pd.to_numeric(query_df["true_rank"], errors="coerce").dropna()
    bins = [1, 2, 6, 11, 51, 101, 501, np.inf]
    labels = ["1", "2-5", "6-10", "11-50", "51-100", "101-500", ">500"]
    rank_bins = pd.cut(ranks, bins=bins, labels=labels, right=False)
    counts = rank_bins.value_counts(sort=False)
    ax.bar(counts.index.astype(str), counts.values, color="#4e7c9b")
    ax.set_ylabel("Queries")
    ax.set_xlabel("True candidate rank")
    ax.set_title("True-rank distribution")
    fig.tight_layout()
    path = FIGDIR / "figure_3_1_true_rank_distribution.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    figure_paths.append(str(path.relative_to(ROOT)))

    cand = strat_df[strat_df["stratum"].eq("candidate_set_size")].copy()
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.plot(cand["level"], cand["top1_accuracy"], marker="o", label="Top-1", color="#376d6a")
    ax.plot(cand["level"], cand["mean_reciprocal_rank"], marker="s", label="MRR", color="#6b6f8d")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_xlabel("Candidate set size bin")
    ax.set_title("Performance versus candidate-set size")
    ax.legend(frameon=False)
    fig.tight_layout()
    path = FIGDIR / "figure_3_1_candidate_set_size.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    figure_paths.append(str(path.relative_to(ROOT)))

    diff = strat_df[strat_df["stratum"].eq("candidate_structural_similarity_difficulty")].copy()
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.bar(diff["level"], diff["top1_accuracy"], color="#8a6f3d")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Top-1 accuracy")
    ax.set_xlabel("Top-1 structural similarity bin")
    ax.set_title("Performance by structural difficulty proxy")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    path = FIGDIR / "figure_3_1_similarity_difficulty.png"
    fig.savefig(path, dpi=300)
    plt.close(fig)
    figure_paths.append(str(path.relative_to(ROOT)))
    return figure_paths


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    df = load_inputs()
    completed = df[df["status"].astype(str).eq("completed")].copy()
    if len(completed) != 229:
        raise ValueError(f"Expected 229 completed CASMI2022 queries, found {len(completed)}")
    if completed["query_id"].duplicated().any():
        raise ValueError("Duplicate query_id rows found in Section 3.1 query results")

    summary = summarize(completed)
    config_audit = json.loads(FINAL_CONFIG_AUDIT.read_text(encoding="utf-8"))
    summary.update({
        "source_query_results": str(INPUT_QUERY_RESULTS.relative_to(ROOT)),
        "frozen_config_audit": str(FINAL_CONFIG_AUDIT.relative_to(ROOT)),
        "final_config_sha256": config_audit["config_sha256"],
        "definition_bundle_sha256": config_audit["definition_bundle_sha256"],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "claim_guardrail": "Section 3.1 reports FragAnnotator only; external model comparisons belong in Section 3.2.",
    })

    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(OUTDIR / "summary.csv", index=False)
    completed.to_csv(OUTDIR / "query_results.csv", index=False)
    ci_df = bootstrap_ci(completed)
    ci_df.to_csv(OUTDIR / "bootstrap_ci.csv", index=False)
    strat_df = stratified_results(completed)
    strat_df.to_csv(OUTDIR / "stratified_results.csv", index=False)
    figure_paths = write_figures(summary, completed, strat_df)

    report_lines = [
        "# Section 3.1 CASMI2022 FragAnnotator-Only Performance",
        "",
        "This report uses the frozen fixed evidence-fusion FragAnnotator definition from `configs/fragannotator_manuscript_final.yaml`.",
        "",
        "No SIRIUS, CFM-ID, ICEBERG, MassFormer, NEIMS, or MS2DeepScore comparison metric is reported in this Section 3.1 package.",
        "",
        "## Summary",
        "",
        summary_df[[
            "n_queries",
            "top1_accuracy",
            "top5_accuracy",
            "top10_accuracy",
            "mean_reciprocal_rank",
            "median_true_rank",
            "mean_top1_tanimoto",
            "median_top1_tanimoto",
            "molecular_formula_accuracy",
        ]].to_markdown(index=False),
        "",
        "## Bootstrap 95% Confidence Intervals",
        "",
        ci_df.to_markdown(index=False),
        "",
        "## Stratification Notes",
        "",
        "- Candidate set size, precursor mass, adduct, formula-correct versus formula-incorrect, spectrum peak count, and top-1 structural similarity proxy strata are included in `stratified_results.csv`.",
        "- Collision energy is not available in the current processed CASMI2022 table, so the collision-energy stratum is explicitly marked unavailable.",
        "",
        "## Figure Outputs",
        "",
        *[f"- `{path}`" for path in figure_paths],
        "",
        "## Rebuild",
        "",
        "`python scripts/generate_manuscript_3_1_casmi_overall.py`",
        "",
    ]
    (OUTDIR / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
    audit = {
        "stage": "manuscript_3_1_casmi_overall",
        "status": "completed",
        "n_queries": int(summary["n_queries"]),
        "outputs": [
            str((OUTDIR / name).relative_to(ROOT))
            for name in ["summary.csv", "query_results.csv", "bootstrap_ci.csv", "stratified_results.csv", "report.md"]
        ] + figure_paths,
        "config_sha256": config_audit["config_sha256"],
        "definition_bundle_sha256": config_audit["definition_bundle_sha256"],
    }
    (OUTDIR / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
