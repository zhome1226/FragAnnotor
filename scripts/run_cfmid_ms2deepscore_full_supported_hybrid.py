#!/usr/bin/env python3
"""Rank full supported CASMI CFM-ID spectra with MS2DeepScore.

This is a generated-spectrum hybrid benchmark. Candidate spectra are CFM-ID
predictions; MS2DeepScore only scores query/candidate spectrum similarity.
Do not label this output as native MS2DeepScore.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from matchms import Spectrum
from ms2deepscore import MS2DeepScore
from ms2deepscore.models import load_model


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFMID_DIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"
DEFAULT_OUTDIR = ROOT / "results" / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_v1"
DEFAULT_MS2DEEPSCORE_MODEL = Path("/home/zhome/ec_structure/external_ms_models/ms2deepscore/ms2deepscore_model.pt")


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
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


def ionmode_from_adduct(adduct: str) -> str:
    return "negative" if "-" in str(adduct) else "positive"


def adduct_slug(adduct: Any) -> str:
    return str(adduct).replace("[", "").replace("]", "").replace("+", "plus").replace("-", "minus")


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


def parse_sectioned_spectrum(path: Path, metadata: dict[str, Any]) -> Spectrum:
    peaks: dict[float, float] = {}
    active = False
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            lower = text.lower()
            if lower in {"low", "med", "medium", "high"} or lower.startswith("energy"):
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
            if mz > 0 and intensity > peaks.get(mz, 0.0):
                peaks[mz] = intensity
    return make_spectrum(list(peaks.keys()), list(peaks.values()), metadata)


def query_spectrum_from_peaks(row: pd.Series) -> Spectrum:
    peaks = row.get("peaks", [])
    mzs: list[float] = []
    intensities: list[float] = []
    for item in peaks:
        if not isinstance(item, (tuple, list)) or len(item) < 2:
            continue
        try:
            mz = float(item[0])
            intensity = float(item[1])
        except (TypeError, ValueError):
            continue
        if mz > 0 and intensity > 0:
            mzs.append(mz)
            intensities.append(intensity)
    return make_spectrum(
        mzs,
        intensities,
        {
            "id": f"query_{int(row['spec_id'])}",
            "spectrum_id": str(int(row["spec_id"])),
            "precursor_mz": float(row["prec_mz"]),
            "ionmode": ionmode_from_adduct(str(row["prec_type"])),
        },
    )


def candidate_spectrum_path(cfmid_dir: Path, adduct: str, candidate_mol_id: int) -> Path:
    return cfmid_dir / "candidate_spectra_cache" / adduct_slug(adduct) / f"{candidate_mol_id}.txt"


def load_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def score_query(
    similarity: MS2DeepScore,
    cfmid_dir: Path,
    query_row: pd.Series,
    candidate_ids: list[int],
    smiles_by_id: dict[int, str],
    batch_size: int,
    top_predictions: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    start_time = time.time()
    query_id = str(int(query_row["spec_id"]))
    true_mol_id = int(query_row["mol_id"])
    adduct = str(query_row["prec_type"])
    precursor_mz = float(query_row["prec_mz"])
    query_spec = query_spectrum_from_peaks(query_row)
    ranked_rows: list[dict[str, Any]] = []
    missing = 0
    nan_scores = 0

    for start in range(0, len(candidate_ids), batch_size):
        batch_ids = candidate_ids[start : start + batch_size]
        batch_specs = []
        batch_meta = []
        for candidate_id in batch_ids:
            path = candidate_spectrum_path(cfmid_dir, adduct, candidate_id)
            if not path.exists() or path.stat().st_size <= 0:
                missing += 1
                continue
            try:
                spec = parse_sectioned_spectrum(
                    path,
                    {
                        "id": f"candidate_{candidate_id}",
                        "candidate_mol_id": candidate_id,
                        "precursor_mz": precursor_mz,
                        "ionmode": ionmode_from_adduct(adduct),
                    },
                )
            except Exception:
                missing += 1
                continue
            batch_specs.append(spec)
            batch_meta.append(candidate_id)
        if not batch_specs:
            continue
        try:
            scores = similarity.matrix(batch_specs, [query_spec])[:, 0]
        except Exception:
            scores = np.asarray([similarity.pair(spec, query_spec) for spec in batch_specs], dtype=float)
        for candidate_id, score_value in zip(batch_meta, scores):
            score = float(score_value)
            if not np.isfinite(score):
                nan_scores += 1
            ranked_rows.append(
                {
                    "candidate_mol_id": candidate_id,
                    "candidate_id": f"CASMI_MOL_{candidate_id}",
                    "candidate_smiles": smiles_by_id.get(candidate_id, ""),
                    "score": score,
                    "is_correct": candidate_id == true_mol_id,
                }
            )

    ranked_rows.sort(
        key=lambda row: (
            not np.isfinite(float(row["score"])),
            -float(row["score"]) if np.isfinite(float(row["score"])) else 0.0,
            int(row["candidate_mol_id"]),
        )
    )
    true_rank = np.nan
    top_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked_rows, start=1):
        if row["is_correct"]:
            true_rank = float(rank)
        if rank <= top_predictions or row["is_correct"]:
            top_rows.append(
                {
                    "dataset": "CASMI2022",
                    "model": "CFM-ID + MS2DeepScore full-supported hybrid",
                    "status": "completed",
                    "native_or_fallback": "cfmid_generated_spectra_ms2deepscore_similarity_full_supported_hybrid",
                    "query_id": query_id,
                    "spectrum_id": query_id,
                    "true_candidate_id": f"CASMI_MOL_{true_mol_id}",
                    "candidate_id": row["candidate_id"],
                    "candidate_mol_id": row["candidate_mol_id"],
                    "candidate_smiles": row["candidate_smiles"],
                    "score": row["score"],
                    "score_status": "finite" if np.isfinite(float(row["score"])) else "failed_nan_score",
                    "rank": rank,
                    "is_correct": row["is_correct"],
                    "candidate_pool_policy": "full_supported_query_candidate_set",
                    "candidate_count": len(ranked_rows),
                }
            )

    rank_valid = not pd.isna(true_rank)
    query_result = {
        "dataset": "CASMI2022",
        "model": "CFM-ID + MS2DeepScore full-supported hybrid",
        "status": "completed" if missing == 0 and nan_scores == 0 and rank_valid else "partial_score_or_spectrum_failures",
        "native_or_fallback": "cfmid_generated_spectra_ms2deepscore_similarity_full_supported_hybrid",
        "query_id": query_id,
        "spectrum_id": query_id,
        "true_candidate_id": f"CASMI_MOL_{true_mol_id}",
        "adduct": adduct,
        "precursor_mz": precursor_mz,
        "candidate_pool_policy": "full_supported_query_candidate_set",
        "candidate_count": int(len(candidate_ids)),
        "candidate_spectra_count": int(len(ranked_rows)),
        "missing_candidate_spectra": int(missing),
        "nan_score_count": int(nan_scores),
        "true_rank": true_rank,
        "top1_correct": bool(rank_valid and true_rank == 1),
        "top5_correct": bool(rank_valid and true_rank <= 5),
        "top10_correct": bool(rank_valid and true_rank <= 10),
        "reciprocal_rank": 0.0 if not rank_valid else 1.0 / float(true_rank),
        "elapsed_seconds": float(time.time() - start_time),
    }
    return query_result, top_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cfmid-dir", type=Path, default=DEFAULT_CFMID_DIR)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--ms2deepscore-model", type=Path, default=DEFAULT_MS2DEEPSCORE_MODEL)
    parser.add_argument("--query-start", type=int, default=0)
    parser.add_argument("--query-limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--top-predictions", type=int, default=100)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(ROOT / "data" / "proc" / "casmi_2022" / "spec_df.pkl")
    cand = pd.read_pickle(ROOT / "data" / "proc" / "casmi_2022" / "cand_df.pkl")
    smiles = (ROOT / "data" / "proc" / "casmi_2022" / "all_smiles.txt").read_text(encoding="utf-8").splitlines()
    smiles_by_id = {idx: value.strip() for idx, value in enumerate(smiles)}
    supported = spec[spec["prec_type"].astype(str).eq("[M+H]+")].sort_values("spec_id").copy()
    stop = None if args.query_limit <= 0 else args.query_start + args.query_limit
    selected = supported.iloc[max(0, args.query_start) : stop].copy()
    grouped = {int(k): v["candidate_mol_id"].astype(int).tolist() for k, v in cand.groupby("query_mol_id", sort=False)}

    query_path = args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_query_results.csv"
    top_path = args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_top_predictions.csv"
    existing = load_existing(query_path)
    completed_query_ids = set()
    if args.resume and not existing.empty and "status" in existing.columns:
        completed_query_ids = set(existing[existing["status"].astype(str).eq("completed")]["query_id"].astype(str))

    model = load_model(args.ms2deepscore_model)
    similarity = MS2DeepScore(model, progress_bar=False)

    query_rows = [] if existing.empty else existing.to_dict(orient="records")
    top_rows = [] if not args.resume else load_existing(top_path).to_dict(orient="records")
    for _, row in selected.iterrows():
        query_id = str(int(row["spec_id"]))
        if query_id in completed_query_ids:
            continue
        candidate_ids = grouped.get(int(row["mol_id"]), [])
        query_result, query_top_rows = score_query(
            similarity,
            args.cfmid_dir,
            row,
            candidate_ids,
            smiles_by_id,
            args.batch_size,
            args.top_predictions,
        )
        query_rows = [existing_row for existing_row in query_rows if str(existing_row.get("query_id")) != query_id]
        top_rows = [existing_row for existing_row in top_rows if str(existing_row.get("query_id")) != query_id]
        query_rows.append(query_result)
        top_rows.extend(query_top_rows)
        pd.DataFrame(query_rows).sort_values("query_id").to_csv(query_path, index=False)
        pd.DataFrame(top_rows).sort_values(["query_id", "rank"]).to_csv(top_path, index=False)
        print(json.dumps(json_safe(query_result), sort_keys=True), flush=True)

    qdf = pd.DataFrame(query_rows)
    completed = qdf[qdf["status"].astype(str).eq("completed")].copy() if not qdf.empty else pd.DataFrame()
    rank_valid = completed[pd.to_numeric(completed["true_rank"], errors="coerce").notna()].copy() if not completed.empty else pd.DataFrame()
    summary = {
        "dataset": "CASMI2022",
        "model": "CFM-ID + MS2DeepScore full-supported hybrid",
        "status": "completed_full_supported_hybrid" if len(rank_valid) == len(supported) and len(supported) else "partial_full_supported_hybrid",
        "native_or_fallback": "cfmid_generated_spectra_ms2deepscore_similarity_full_supported_hybrid",
        "n_supported_queries": int(len(supported)),
        "n_queries_completed": int(len(completed)),
        "n_rank_valid_queries": int(len(rank_valid)),
        "candidate_limit": -1,
        "candidate_pool_policy": "full_supported_query_candidate_set",
        "top1_accuracy": float(rank_valid["top1_correct"].mean()) if not rank_valid.empty else np.nan,
        "top5_accuracy": float(rank_valid["top5_correct"].mean()) if not rank_valid.empty else np.nan,
        "top10_accuracy": float(rank_valid["top10_correct"].mean()) if not rank_valid.empty else np.nan,
        "mean_reciprocal_rank": float(rank_valid["reciprocal_rank"].mean()) if not rank_valid.empty else np.nan,
        "median_true_rank": float(pd.to_numeric(rank_valid["true_rank"], errors="coerce").median()) if not rank_valid.empty else np.nan,
        "median_candidate_count": float(pd.to_numeric(rank_valid["candidate_count"], errors="coerce").median()) if not rank_valid.empty else np.nan,
        "top_predictions_per_query_stored": int(args.top_predictions),
        "claim_guardrail": "Candidate spectra are generated by CFM-ID, so this is a full-supported CFM-ID + MS2DeepScore hybrid benchmark, not native MS2DeepScore.",
    }
    pd.DataFrame([summary]).to_csv(args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_summary.csv", index=False)
    audit = {
        "stage": "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_v1",
        "status": summary["status"],
        "cfmid_dir": str(args.cfmid_dir),
        "ms2deepscore_model": str(args.ms2deepscore_model),
        "query_results": query_path.name,
        "top_predictions": top_path.name,
        **summary,
    }
    write_json(args.outdir / "audit_summary.json", audit)
    report = [
        "# CASMI2022 CFM-ID + MS2DeepScore Full-Supported Hybrid",
        "",
        summary["claim_guardrail"],
        "",
        "## Summary",
        "",
        "\n".join(f"- `{key}`: `{value}`" for key, value in summary.items()),
        "",
    ]
    (args.outdir / "casmi2022_cfmid_ms2deepscore_full_supported_hybrid_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
