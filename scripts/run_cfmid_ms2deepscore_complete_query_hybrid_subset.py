#!/usr/bin/env python3
"""Rank a complete CFM-ID query subset with MS2DeepScore.

This is a generator + MS2DeepScore hybrid benchmark. Candidate spectra are
native CFM-ID predictions cached by
``run_cfmid_precomputed_complete_query_subset.py``; MS2DeepScore only scores
query/candidate spectrum similarity. The output is therefore not native
MS2DeepScore and not a full CASMI benchmark.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from matchms import Spectrum
from ms2deepscore import MS2DeepScore
from ms2deepscore.models import load_model


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBSET_DIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_complete_query_subset_v1"
DEFAULT_OUTDIR = ROOT / "results" / "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_v1"
DEFAULT_MS2DEEPSCORE_MODEL = Path("/home/zhome/ec_structure/external_ms_models/ms2deepscore/ms2deepscore_model.pt")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def parse_sectioned_spectrum(path: Path, metadata: dict[str, Any]) -> Spectrum:
    """Parse CFM-ID low/med/high text spectra, merging energies by max peak."""
    peaks: dict[float, float] = {}
    active = False
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            if text.lower() in {"low", "med", "high"} or text.lower().startswith("energy"):
                active = True
                continue
            if not active:
                continue
            parts = text.split()
            if len(parts) < 2:
                continue
            try:
                mz = round(float(parts[0]), 4)
                intensity = float(parts[1])
            except ValueError:
                continue
            if intensity > peaks.get(mz, 0.0):
                peaks[mz] = intensity
    return make_spectrum(list(peaks.keys()), list(peaks.values()), metadata)


def make_spectrum(mzs: list[float], intensities: list[float], metadata: dict[str, Any]) -> Spectrum:
    mz = np.asarray(mzs if mzs else [0.0], dtype=np.float64)
    inten = np.asarray(intensities if intensities else [0.0], dtype=np.float64)
    order = np.argsort(mz)
    mz = mz[order]
    inten = inten[order]
    max_intensity = float(np.max(inten)) if len(inten) else 0.0
    if max_intensity > 0:
        inten = inten / max_intensity
    return Spectrum(mz=mz, intensities=inten, metadata=metadata)


def read_candidate_triples(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            parts = text.split(maxsplit=2)
            if len(parts) != 3:
                continue
            rows.append({"candidate_mol_id": int(parts[0]), "smiles": parts[1], "spectrum_file": parts[2]})
    return rows


def ionmode_from_adduct(adduct: str) -> str:
    return "negative" if "-" in str(adduct) else "positive"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset-dir", type=Path, default=DEFAULT_SUBSET_DIR)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--ms2deepscore-model", type=Path, default=DEFAULT_MS2DEEPSCORE_MODEL)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    query_df = pd.read_csv(args.subset_dir / "casmi2022_cfmid_native_precomputed_complete_query_subset_query_results.csv")
    query_df = query_df[query_df["status"].astype(str).isin(["completed", "completed_cached"])].copy()
    selected_manifest = pd.read_csv(args.subset_dir / "selected_complete_query_manifest.csv")
    manifest_by_spec = {
        str(row["spec_id"]): row.to_dict()
        for _, row in selected_manifest.iterrows()
    }

    model = load_model(args.ms2deepscore_model)
    similarity = MS2DeepScore(model, progress_bar=False)

    pred_rows: list[dict[str, Any]] = []
    query_rows: list[dict[str, Any]] = []
    for _, query in query_df.iterrows():
        query_id = str(query["query_id"])
        manifest_row = manifest_by_spec.get(query_id, {})
        work_dir = args.subset_dir / "work" / f"query_{query_id}"
        triples_path = work_dir / "candidate_triples_plain.txt"
        query_spectrum_path = work_dir / f"query_spectrum_{query_id}.txt"
        adduct = str(query.get("adduct") or manifest_row.get("adduct") or "")
        ionmode = ionmode_from_adduct(adduct)
        precursor_mz = float(query.get("precursor_mz", np.nan))
        if not np.isfinite(precursor_mz):
            precursor_mz = float(manifest_row.get("precursor_mz", np.nan))
        true_mol_id = int(str(query["true_candidate_id"]).replace("CASMI_MOL_", ""))

        if not triples_path.exists() or not query_spectrum_path.exists():
            query_rows.append(
                {
                    "dataset": "CASMI2022",
                    "model": "CFM-ID + MS2DeepScore complete-query hybrid subset",
                    "query_id": query_id,
                    "spectrum_id": query_id,
                    "status": "missing_cached_cfmid_spectra",
                    "true_rank": np.nan,
                }
            )
            continue

        triples = read_candidate_triples(triples_path)
        query_spec = parse_sectioned_spectrum(
            query_spectrum_path,
            {
                "id": f"query_{query_id}",
                "spectrum_id": query_id,
                "precursor_mz": precursor_mz,
                "ionmode": ionmode,
            },
        )
        candidate_specs = []
        candidate_rows = []
        missing = 0
        for triple in triples:
            spectrum_file = Path(str(triple["spectrum_file"]))
            if not spectrum_file.exists():
                missing += 1
                continue
            candidate_specs.append(
                parse_sectioned_spectrum(
                    spectrum_file,
                    {
                        "id": f"candidate_{triple['candidate_mol_id']}",
                        "candidate_mol_id": int(triple["candidate_mol_id"]),
                        "precursor_mz": precursor_mz,
                        "ionmode": ionmode,
                    },
                )
            )
            candidate_rows.append(triple)

        score_values: list[float] = []
        score_failures = 0
        for candidate_spec in candidate_specs:
            try:
                score = float(similarity.pair(candidate_spec, query_spec))
            except Exception:
                score = float("nan")
            if not np.isfinite(score):
                score_failures += 1
            score_values.append(score)
        ranked = []
        for triple, score in zip(candidate_rows, score_values):
            cid = int(triple["candidate_mol_id"])
            ranked.append(
                {
                    "candidate_mol_id": cid,
                    "candidate_id": f"CASMI_MOL_{cid}",
                    "candidate_smiles": triple["smiles"],
                    "score": float(score),
                    "is_correct": cid == true_mol_id,
                }
            )
        ranked.sort(
            key=lambda row: (
                not np.isfinite(float(row["score"])),
                -float(row["score"]) if np.isfinite(float(row["score"])) else 0.0,
                row["candidate_mol_id"],
            )
        )
        true_rank = np.nan
        for rank, row in enumerate(ranked, start=1):
            if row["is_correct"]:
                true_rank = float(rank)
            pred_rows.append(
                {
                    "dataset": "CASMI2022",
                    "model": "CFM-ID + MS2DeepScore complete-query hybrid subset",
                    "status": "completed",
                    "native_or_fallback": "cfmid_generated_spectra_ms2deepscore_similarity_complete_query_hybrid",
                    "query_id": query_id,
                    "spectrum_id": query_id,
                    "true_candidate_id": query["true_candidate_id"],
                    "candidate_id": row["candidate_id"],
                    "candidate_mol_id": row["candidate_mol_id"],
                    "candidate_smiles": row["candidate_smiles"],
                    "score": row["score"],
                    "score_status": "finite" if np.isfinite(float(row["score"])) else "failed_nan_score",
                    "rank": rank,
                    "is_correct": row["is_correct"],
                    "candidate_pool_policy": "full_candidate_set_for_each_selected_query",
                    "candidate_count": len(ranked),
                }
            )
        finite = not pd.isna(true_rank)
        query_rows.append(
            {
                "dataset": "CASMI2022",
                "model": "CFM-ID + MS2DeepScore complete-query hybrid subset",
                "status": "completed" if missing == 0 and score_failures == 0 else "partial_score_or_spectrum_failures",
                "native_or_fallback": "cfmid_generated_spectra_ms2deepscore_similarity_complete_query_hybrid",
                "query_id": query_id,
                "spectrum_id": query_id,
                "true_candidate_id": query["true_candidate_id"],
                "adduct": adduct,
                "precursor_mz": precursor_mz,
                "candidate_pool_policy": "full_candidate_set_for_each_selected_query",
                "candidate_count": len(ranked),
                "candidate_spectra_count": len(candidate_specs),
                "missing_candidate_spectra": missing,
                "nan_score_count": score_failures,
                "true_rank": true_rank,
                "top1_correct": bool(finite and true_rank == 1),
                "top5_correct": bool(finite and true_rank <= 5),
                "top10_correct": bool(finite and true_rank <= 10),
                "reciprocal_rank": 0.0 if not finite else 1.0 / true_rank,
            }
        )

    pred_df = pd.DataFrame(pred_rows)
    qdf = pd.DataFrame(query_rows)
    completed = qdf[qdf["status"].eq("completed")].copy()
    rank_valid = completed[pd.to_numeric(completed["true_rank"], errors="coerce").notna()].copy()
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID + MS2DeepScore complete-query hybrid subset",
        "status": "completed_subset" if len(rank_valid) == len(query_df) and len(query_df) else "partial_subset",
        "native_or_fallback": "cfmid_generated_spectra_ms2deepscore_similarity_complete_query_hybrid",
        "n_queries": int(len(query_df)),
        "n_queries_completed": int(len(completed)),
        "n_rank_valid_queries": int(len(rank_valid)),
        "candidate_limit": -1,
        "candidate_pool_policy": "full_candidate_set_for_each_selected_query",
        "top1_accuracy": float(rank_valid["top1_correct"].mean()) if not rank_valid.empty else np.nan,
        "top5_accuracy": float(rank_valid["top5_correct"].mean()) if not rank_valid.empty else np.nan,
        "top10_accuracy": float(rank_valid["top10_correct"].mean()) if not rank_valid.empty else np.nan,
        "mean_reciprocal_rank": float(rank_valid["reciprocal_rank"].mean()) if not rank_valid.empty else np.nan,
        "median_true_rank": float(pd.to_numeric(rank_valid["true_rank"], errors="coerce").median()) if not rank_valid.empty else np.nan,
        "median_candidate_count": float(pd.to_numeric(rank_valid["candidate_count"], errors="coerce").median()) if not rank_valid.empty else np.nan,
        "claim_guardrail": "Candidate spectra are generated by CFM-ID, so this is a complete-query CFM-ID + MS2DeepScore hybrid subset, not native MS2DeepScore and not a full CASMI benchmark.",
    }

    pred_df.to_csv(args.outdir / "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_predictions.csv", index=False)
    qdf.to_csv(args.outdir / "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_query_results.csv", index=False)
    pd.DataFrame([summary]).to_csv(args.outdir / "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_summary.csv", index=False)
    mirror = ROOT / "results" / "predictions" / "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_predictions.csv"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    pred_df.to_csv(mirror, index=False)
    audit = {
        "stage": "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_v1",
        "status": summary["status"],
        "subset_source": str(args.subset_dir),
        "ms2deepscore_model": str(args.ms2deepscore_model),
        **summary,
    }
    write_json(args.outdir / "audit_summary.json", audit)
    report = [
        "# CASMI2022 CFM-ID + MS2DeepScore Complete-Query Hybrid Subset",
        "",
        summary["claim_guardrail"],
        "",
        "## Summary",
        "",
        "\n".join(f"- `{key}`: `{value}`" for key, value in summary.items()),
        "",
    ]
    (args.outdir / "casmi2022_cfmid_ms2deepscore_complete_query_hybrid_subset_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
