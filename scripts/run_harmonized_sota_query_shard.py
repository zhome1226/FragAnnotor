#!/usr/bin/env python3
"""Run harmonized CASMI candidate-set reranking for external SOTA predictors.

The runner predicts spectra for the exact CASMI query candidate set and ranks
candidates by a shared binned cosine score against the experimental query
spectrum. It is intentionally resumable and stores query-level rows plus top
predictions only; raw per-candidate prediction files stay in temporary folders
unless ``--keep-raw`` is requested.

Supported models here are ICEBERG and MassFormer. NEIMS is not included because
no validated wrapper/checkpoint is currently available in the external resource
tree.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
EXTERNAL_ROOT = Path("/home/zhome/ec_structure/external_ms_models")
ICEBERG_LEGACY_DIR = EXTERNAL_ROOT / "vendor" / "ms-pred-iceberg-2024"
ICEBERG_MAIN_DIR = EXTERNAL_ROOT / "vendor" / "ms-pred"
ICEBERG_GEN_CKPT = ICEBERG_MAIN_DIR / "checkpoints" / "canopus_iceberg_generate.ckpt"
ICEBERG_INTEN_CKPT = ICEBERG_MAIN_DIR / "checkpoints" / "canopus_iceberg_score.ckpt"
ICEBERG_PYTHON = EXTERNAL_ROOT / "envs" / "ms_pred_iceberg_sys" / "bin" / "python"
MASSFORMER_DIR = EXTERNAL_ROOT / "vendor" / "massformer"
MASSFORMER_PYTHON = EXTERNAL_ROOT / "envs" / "massformer_sys" / "bin" / "python"
MASSFORMER_CONFIG = MASSFORMER_DIR / "config" / "demo" / "demo_eval_noworkers.yml"
MASSFORMER_CHECKPOINT = MASSFORMER_DIR / "checkpoints" / "demo.pkl"
DEFAULT_OUTDIR = ROOT / "results" / "harmonized_sota_candidate_reruns_v1"

ICEBERG_SUPPORTED_ADDUCTS = {"[M+H]+", "[M+Na]+", "[M+K]+", "[M]+", "[M-H2O+H]+", "[M+H-H2O]+", "[M+NH4]+", "[M+H3N+H]+"}
MASSFORMER_SUPPORTED_ADDUCTS = {"[M+H]+", "[M+Na]+"}


@dataclass
class CandidatePrediction:
    candidate_mol_id: int
    candidate_smiles: str
    peaks: list[list[float]]
    status: str
    error_message: str = ""


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")


def normalize(value: Any) -> str:
    return " ".join(str(value or "").split())


def safe_query_id(row: pd.Series) -> str:
    return str(int(row["spec_id"]))


def ce_for_model(row: pd.Series, model: str) -> str:
    nce = row.get("nce")
    if pd.notna(nce):
        try:
            return str(float(nce))
        except (TypeError, ValueError):
            pass
    ace = row.get("ace")
    if pd.notna(ace):
        try:
            return str(float(ace))
        except (TypeError, ValueError):
            pass
    # These match the existing validated single-spectrum wrappers.
    return "30" if model == "iceberg" else "40"


def query_peaks(row: pd.Series) -> list[list[float]]:
    peaks: list[list[float]] = []
    for item in row.get("peaks", []):
        if not isinstance(item, (tuple, list)) or len(item) < 2:
            continue
        try:
            mz = float(item[0])
            intensity = float(item[1])
        except (TypeError, ValueError):
            continue
        if mz > 0 and intensity > 0:
            peaks.append([mz, intensity])
    return peaks


def binned_unit_vector(peaks: list[list[float]], bin_width: float, intensity_power: float) -> dict[int, float]:
    bins: dict[int, float] = defaultdict(float)
    for mz, intensity in peaks:
        try:
            mz_f = float(mz)
            intensity_f = float(intensity)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(mz_f) or not np.isfinite(intensity_f) or mz_f <= 0 or intensity_f <= 0:
            continue
        bin_id = int(round(mz_f / bin_width))
        bins[bin_id] += float(intensity_f) ** intensity_power
    norm = math.sqrt(sum(value * value for value in bins.values()))
    if norm <= 0:
        return {}
    return {key: value / norm for key, value in bins.items()}


def cosine_score(query_vec: dict[int, float], pred_peaks: list[list[float]], bin_width: float, intensity_power: float) -> float:
    pred_vec = binned_unit_vector(pred_peaks, bin_width, intensity_power)
    if not query_vec or not pred_vec:
        return float("nan")
    if len(query_vec) < len(pred_vec):
        score = sum(value * pred_vec.get(key, 0.0) for key, value in query_vec.items())
    else:
        score = sum(query_vec.get(key, 0.0) * value for key, value in pred_vec.items())
    return float(score)


def parse_iceberg_tree_json(path: Path, max_peaks: int) -> list[list[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    merged: dict[float, float] = defaultdict(float)
    for frag in data.get("frags", {}).values():
        mzs = frag.get("mz_charge") or frag.get("mz_no_charge") or []
        intens = frag.get("intens") or []
        for mz, inten in zip(mzs, intens):
            try:
                mz_f = round(float(mz), 4)
                inten_f = float(inten)
            except (TypeError, ValueError):
                continue
            if mz_f > 0 and inten_f > 0:
                merged[mz_f] += inten_f
    if not merged:
        return []
    max_intensity = max(merged.values())
    peaks = [[mz, 100.0 * intensity / max_intensity] for mz, intensity in merged.items() if intensity > 0]
    peaks.sort(key=lambda item: item[1], reverse=True)
    return sorted(peaks[:max_peaks], key=lambda item: item[0])


def parse_massformer_peaks(value: Any, max_peaks: int) -> list[list[float]]:
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except Exception:
            return []
    else:
        parsed = value
    merged: dict[float, float] = defaultdict(float)
    for item in parsed or []:
        if not isinstance(item, (tuple, list)) or len(item) < 2:
            continue
        try:
            mz = round(float(item[0]), 4)
            intensity = float(item[1])
        except (TypeError, ValueError):
            continue
        if mz > 0 and intensity > 0:
            merged[mz] += intensity
    if not merged:
        return []
    max_intensity = max(merged.values())
    peaks = [[mz, 100.0 * intensity / max_intensity] for mz, intensity in merged.items()]
    peaks.sort(key=lambda item: item[1], reverse=True)
    return sorted(peaks[:max_peaks], key=lambda item: item[0])


def massformer_prepare_molecule(smiles: str) -> tuple[str | None, str]:
    """Return a MassFormer-safe canonical SMILES string, or a rejection reason."""
    try:
        from rdkit import Chem
        from rdkit.Chem import inchi as rd_inchi
    except Exception:
        return normalize(smiles), ""
    try:
        smiles_text = normalize(smiles)
        if smiles_text.startswith("InChI="):
            mol = rd_inchi.MolFromInchi(smiles_text)
        else:
            mol = Chem.MolFromSmiles(smiles_text)
        if mol is None:
            return None, "RDKit returned no molecule before MassFormer inference"
        if mol.GetNumAtoms() <= 0:
            return None, "RDKit molecule has no atoms before MassFormer inference"
        for atom in mol.GetAtoms():
            if atom.GetAtomicNum() <= 0:
                return None, "MassFormer graph featurization does not support dummy atoms"
        canonical = Chem.MolToSmiles(mol)
        if not canonical or Chem.MolFromSmiles(canonical) is None:
            return None, "RDKit canonical SMILES cannot be reparsed before MassFormer inference"
        return canonical, ""
    except Exception as exc:
        return None, f"RDKit failed to canonicalize molecule before MassFormer inference: {exc!r}"


def run_command(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int, log_path: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps(
            {
                "args": cmd,
                "cwd": str(cwd),
                "returncode": completed.returncode,
                "stdout": completed.stdout[-8000:],
                "stderr": completed.stderr[-8000:],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return completed


def massformer_command_failure_category(completed: subprocess.CompletedProcess[str] | None) -> str:
    if completed is None:
        return "exception"
    stderr = completed.stderr or ""
    if "AssertionError" in stderr and "smiles2graph" in stderr:
        return "graph_featurization_assertion"
    return "other"


def iceberg_predict_chunk(
    candidates: list[tuple[int, str]],
    query_row: pd.Series,
    args: argparse.Namespace,
    work_dir: Path,
    depth: int = 0,
) -> list[CandidatePrediction]:
    if not candidates:
        return []
    work_dir.mkdir(parents=True, exist_ok=True)
    labels = work_dir / "labels.tsv"
    save_dir = work_dir / "pred"
    ce = ce_for_model(query_row, "iceberg")
    adduct = normalize(query_row["prec_type"])
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["spec", "smiles", "ionization", "precursor", "instrument", "collision_energies"], delimiter="\t")
        writer.writeheader()
        for candidate_id, smiles in candidates:
            writer.writerow(
                {
                    "spec": f"q{int(query_row['spec_id'])}_m{candidate_id}",
                    "smiles": smiles,
                    "ionization": adduct,
                    "precursor": normalize(query_row["prec_mz"]),
                    "instrument": "Orbitrap",
                    "collision_energies": f"[{ce}]",
                }
            )
    env = os.environ.copy()
    shim_dir = EXTERNAL_ROOT / "shims" / "no_deepspeed"
    env["PYTHONPATH"] = os.pathsep.join([str(shim_dir), str(ICEBERG_LEGACY_DIR / "src")])
    env["DGLBACKEND"] = "pytorch"
    env["MPLCONFIGDIR"] = str(EXTERNAL_ROOT / "outputs" / "matplotlib_cache")
    cmd = [
        str(args.iceberg_python),
        str(ICEBERG_LEGACY_DIR / "src" / "ms_pred" / "dag_pred" / "predict_smis.py"),
        "--sparse-out",
        "--sparse-k",
        str(args.max_predicted_peaks),
        "--save-dir",
        str(save_dir),
        "--gen-checkpoint",
        str(args.iceberg_gen_checkpoint),
        "--inten-checkpoint",
        str(args.iceberg_inten_checkpoint),
        "--dataset-labels",
        str(labels),
        "--batch-size",
        str(args.model_batch_size),
        "--num-workers",
        "0",
        "--threshold",
        "0.0",
        "--max-nodes",
        "100",
        "--upper-limit",
        "1500",
        "--num-bins",
        "15000",
    ]
    log_path = work_dir / "iceberg_command.json"
    try:
        completed = run_command(cmd, ICEBERG_LEGACY_DIR, env, args.command_timeout_seconds, log_path)
    except Exception as exc:
        completed = None
        (work_dir / "iceberg_exception.txt").write_text(repr(exc), encoding="utf-8")
    if completed is None or completed.returncode != 0:
        if args.retry_failed_singletons and len(candidates) > 1 and depth < args.max_retry_depth:
            mid = len(candidates) // 2
            left = iceberg_predict_chunk(candidates[:mid], query_row, args, work_dir / "retry_left", depth + 1)
            right = iceberg_predict_chunk(candidates[mid:], query_row, args, work_dir / "retry_right", depth + 1)
            return left + right
        reason = "ICEBERG command failed" if completed is not None else "ICEBERG command raised an exception"
        return [CandidatePrediction(candidate_id, smiles, [], "prediction_failed", reason) for candidate_id, smiles in candidates]

    out: list[CandidatePrediction] = []
    tree_dir = save_dir / "tree_preds_inten"
    for candidate_id, smiles in candidates:
        pred_path = tree_dir / f"pred_q{int(query_row['spec_id'])}_m{candidate_id}.json"
        if not pred_path.exists():
            out.append(CandidatePrediction(candidate_id, smiles, [], "missing_prediction_file", "ICEBERG did not emit prediction JSON"))
            continue
        peaks = parse_iceberg_tree_json(pred_path, args.max_predicted_peaks)
        status = "predicted_spectrum" if peaks else "empty_prediction"
        out.append(CandidatePrediction(candidate_id, smiles, peaks, status, "" if peaks else "ICEBERG emitted no positive-intensity peaks"))
    return out


def massformer_predict_chunk(
    candidates: list[tuple[int, str]],
    query_row: pd.Series,
    args: argparse.Namespace,
    work_dir: Path,
    depth: int = 0,
) -> list[CandidatePrediction]:
    if not candidates:
        return []
    valid_candidates: list[tuple[int, str, str]] = []
    invalid_predictions: list[CandidatePrediction] = []
    for candidate_id, smiles in candidates:
        canonical_smiles, reason = massformer_prepare_molecule(smiles)
        if canonical_smiles:
            valid_candidates.append((candidate_id, smiles, canonical_smiles))
        else:
            invalid_predictions.append(CandidatePrediction(candidate_id, smiles, [], "unsupported_molecule", reason))
    if not valid_candidates:
        return invalid_predictions
    input_csv = work_dir / "smiles.csv"
    output_csv = work_dir / "predictions.csv"
    input_csv.parent.mkdir(parents=True, exist_ok=True)
    with input_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mol_id", "smiles"])
        writer.writeheader()
        for candidate_id, _, canonical_smiles in valid_candidates:
            writer.writerow({"mol_id": candidate_id, "smiles": canonical_smiles})
    env = os.environ.copy()
    env["DGLBACKEND"] = "pytorch"
    env["TORCH_HOME"] = str(MASSFORMER_DIR / "checkpoints" / "torch_cache")
    env["MPLCONFIGDIR"] = str(EXTERNAL_ROOT / "outputs" / "matplotlib_cache")
    env["PYTHONPATH"] = str(MASSFORMER_DIR / "src")
    cmd = [
        str(args.massformer_python),
        "scripts/run_inference.py",
        "-d",
        str(args.massformer_device_id),
        "-c",
        str(args.massformer_config.relative_to(MASSFORMER_DIR) if args.massformer_config.is_relative_to(MASSFORMER_DIR) else args.massformer_config),
        "-s",
        str(input_csv),
        "--nces",
        ce_for_model(query_row, "massformer"),
        "--prec_types",
        normalize(query_row["prec_type"]),
        "-o",
        str(output_csv),
    ]
    log_path = work_dir / "massformer_command.json"
    try:
        completed = run_command(cmd, MASSFORMER_DIR, env, args.command_timeout_seconds, log_path)
    except Exception as exc:
        completed = None
        (work_dir / "massformer_exception.txt").write_text(repr(exc), encoding="utf-8")
    if completed is None or completed.returncode != 0:
        failure_category = massformer_command_failure_category(completed)
        if failure_category == "graph_featurization_assertion" and not args.fail_graph_assertion_batches:
            if len(valid_candidates) > args.graph_assertion_fail_batch_size and depth < args.max_retry_depth:
                mid = len(valid_candidates) // 2
                retry_candidates = [(candidate_id, smiles) for candidate_id, smiles, _ in valid_candidates]
                left = massformer_predict_chunk(retry_candidates[:mid], query_row, args, work_dir / "retry_left", depth + 1)
                right = massformer_predict_chunk(retry_candidates[mid:], query_row, args, work_dir / "retry_right", depth + 1)
                return invalid_predictions + left + right
            reason = (
                "MassFormer graph featurization failed for this small molecule batch; "
                "batch was recorded as failed to avoid unbounded recursive retries"
            )
            return invalid_predictions + [
                CandidatePrediction(candidate_id, smiles, [], "prediction_failed", reason)
                for candidate_id, smiles, _ in valid_candidates
            ]
        if args.retry_failed_singletons and len(valid_candidates) > 1 and depth < args.max_retry_depth:
            mid = len(valid_candidates) // 2
            retry_candidates = [(candidate_id, smiles) for candidate_id, smiles, _ in valid_candidates]
            left = massformer_predict_chunk(retry_candidates[:mid], query_row, args, work_dir / "retry_left", depth + 1)
            right = massformer_predict_chunk(retry_candidates[mid:], query_row, args, work_dir / "retry_right", depth + 1)
            return invalid_predictions + left + right
        reason = "MassFormer command failed" if completed is not None else "MassFormer command raised an exception"
        return invalid_predictions + [CandidatePrediction(candidate_id, smiles, [], "prediction_failed", reason) for candidate_id, smiles, _ in valid_candidates]
    if not output_csv.exists():
        return invalid_predictions + [CandidatePrediction(candidate_id, smiles, [], "missing_prediction_file", "MassFormer did not emit predictions.csv") for candidate_id, smiles, _ in valid_candidates]
    try:
        pred_df = pd.read_csv(output_csv)
    except Exception as exc:
        return invalid_predictions + [CandidatePrediction(candidate_id, smiles, [], "prediction_parse_failed", repr(exc)) for candidate_id, smiles, _ in valid_candidates]
    peaks_by_id: dict[int, list[list[float]]] = {}
    for _, row in pred_df.iterrows():
        try:
            mol_id = int(row["mol_id"])
        except (TypeError, ValueError):
            continue
        peaks_by_id[mol_id] = parse_massformer_peaks(row.get("peaks", ""), args.max_predicted_peaks)
    out = list(invalid_predictions)
    for candidate_id, smiles, _ in valid_candidates:
        peaks = peaks_by_id.get(candidate_id, [])
        status = "predicted_spectrum" if peaks else "empty_prediction"
        out.append(CandidatePrediction(candidate_id, smiles, peaks, status, "" if peaks else "MassFormer emitted no positive-intensity peaks"))
    return out


def optional_tanimoto(true_smiles: str, candidate_smiles: str) -> float:
    try:
        from rdkit import Chem, DataStructs
        from rdkit.Chem import AllChem
    except Exception:
        return float("nan")
    true_mol = Chem.MolFromSmiles(true_smiles)
    cand_mol = Chem.MolFromSmiles(candidate_smiles)
    if true_mol is None or cand_mol is None:
        return float("nan")
    true_fp = AllChem.GetMorganFingerprintAsBitVect(true_mol, 2, nBits=2048)
    cand_fp = AllChem.GetMorganFingerprintAsBitVect(cand_mol, 2, nBits=2048)
    return float(DataStructs.TanimotoSimilarity(true_fp, cand_fp))


def optional_formula(smiles: str) -> str:
    try:
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors
    except Exception:
        return ""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ""
    return str(rdMolDescriptors.CalcMolFormula(mol))


def predict_candidates(
    model: str,
    candidates: list[tuple[int, str]],
    query_row: pd.Series,
    args: argparse.Namespace,
    query_work_dir: Path,
) -> list[CandidatePrediction]:
    predictions: list[CandidatePrediction] = []
    for chunk_index, start in enumerate(range(0, len(candidates), args.candidate_chunk_size)):
        chunk = candidates[start : start + args.candidate_chunk_size]
        chunk_dir = query_work_dir / f"chunk_{chunk_index:05d}"
        if model == "iceberg":
            chunk_predictions = iceberg_predict_chunk(chunk, query_row, args, chunk_dir)
        elif model == "massformer":
            chunk_predictions = massformer_predict_chunk(chunk, query_row, args, chunk_dir)
        else:
            raise ValueError(f"Unsupported model: {model}")
        predictions.extend(chunk_predictions)
        if not args.keep_raw:
            shutil.rmtree(chunk_dir, ignore_errors=True)
    return predictions


def score_query(
    model: str,
    query_row: pd.Series,
    candidates: list[tuple[int, str]],
    args: argparse.Namespace,
    work_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    start_time = time.time()
    query_id = safe_query_id(query_row)
    true_mol_id = int(query_row["mol_id"])
    true_smiles = normalize(query_row["smiles"])
    query_vec = binned_unit_vector(query_peaks(query_row), args.bin_width, args.intensity_power)
    query_work_dir = work_root / f"query_{query_id}"
    query_work_dir.mkdir(parents=True, exist_ok=True)
    predictions = predict_candidates(model, candidates, query_row, args, query_work_dir)
    if not args.keep_raw:
        shutil.rmtree(query_work_dir, ignore_errors=True)

    ranked_rows = []
    status_counts: dict[str, int] = defaultdict(int)
    nan_scores = 0
    for pred in predictions:
        status_counts[pred.status] += 1
        score = cosine_score(query_vec, pred.peaks, args.bin_width, args.intensity_power) if pred.peaks else float("nan")
        if not np.isfinite(score):
            nan_scores += 1
        ranked_rows.append(
            {
                "candidate_mol_id": pred.candidate_mol_id,
                "candidate_id": f"CASMI_MOL_{pred.candidate_mol_id}",
                "candidate_smiles": pred.candidate_smiles,
                "score": score,
                "prediction_status": pred.status,
                "is_correct": pred.candidate_mol_id == true_mol_id,
            }
        )
    ranked_rows.sort(
        key=lambda row: (
            not np.isfinite(float(row["score"])),
            -float(row["score"]) if np.isfinite(float(row["score"])) else 0.0,
            int(row["candidate_mol_id"]),
        )
    )
    true_rank = float("nan")
    top_rows = []
    for rank, row in enumerate(ranked_rows, start=1):
        if row["is_correct"]:
            true_rank = float(rank)
        if rank <= args.top_predictions or row["is_correct"]:
            top_rows.append(
                {
                    "dataset": "CASMI2022",
                    "model": model,
                    "status": "completed",
                    "query_id": query_id,
                    "spectrum_id": query_id,
                    "casmi_id": int(query_row["casmi_id"]),
                    "true_candidate_id": f"CASMI_MOL_{true_mol_id}",
                    "candidate_id": row["candidate_id"],
                    "candidate_mol_id": row["candidate_mol_id"],
                    "candidate_smiles": row["candidate_smiles"],
                    "score": row["score"],
                    "score_name": f"binned_cosine_{args.bin_width:g}Da",
                    "rank": rank,
                    "is_correct": row["is_correct"],
                    "prediction_status": row["prediction_status"],
                    "candidate_count": len(candidates),
                }
            )

    rank_valid = np.isfinite(true_rank)
    top1_smiles = top_rows[0]["candidate_smiles"] if top_rows else ""
    top1_formula = optional_formula(top1_smiles) if top1_smiles else ""
    true_formula = optional_formula(true_smiles)
    query_result = {
        "dataset": "CASMI2022",
        "model": model,
        "status": "completed" if rank_valid and status_counts.get("predicted_spectrum", 0) == len(candidates) else "partial_prediction_failures",
        "query_id": query_id,
        "spectrum_id": query_id,
        "casmi_id": int(query_row["casmi_id"]),
        "adduct": normalize(query_row["prec_type"]),
        "precursor_mz": float(query_row["prec_mz"]),
        "collision_energy_used": ce_for_model(query_row, model),
        "true_candidate_id": f"CASMI_MOL_{true_mol_id}",
        "candidate_pool_policy": "full_query_candidate_set",
        "candidate_count": int(len(candidates)),
        "predicted_spectrum_count": int(status_counts.get("predicted_spectrum", 0)),
        "failed_prediction_count": int(len(candidates) - status_counts.get("predicted_spectrum", 0)),
        "nan_score_count": int(nan_scores),
        "true_rank": true_rank,
        "top1_correct": bool(rank_valid and true_rank == 1),
        "top5_correct": bool(rank_valid and true_rank <= 5),
        "top10_correct": bool(rank_valid and true_rank <= 10),
        "reciprocal_rank": 0.0 if not rank_valid else 1.0 / float(true_rank),
        "top1_candidate_smiles": top1_smiles,
        "top1_tanimoto": optional_tanimoto(true_smiles, top1_smiles) if top1_smiles else float("nan"),
        "formula_accuracy": bool(true_formula and top1_formula and true_formula == top1_formula),
        "score_name": f"binned_cosine_{args.bin_width:g}Da",
        "elapsed_seconds": float(time.time() - start_time),
    }
    return query_result, top_rows


def load_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def write_sorted_csv(rows: list[dict[str, Any]], path: Path, sort_columns: list[str]) -> None:
    df = pd.DataFrame(rows)
    if df.empty:
        df.to_csv(path, index=False)
        return
    sort_helpers: list[str] = []
    for column in sort_columns:
        if column not in df.columns:
            continue
        helper = f"__sort_{column}"
        if column in {"query_id", "spectrum_id"}:
            numeric = pd.to_numeric(df[column], errors="coerce")
            df[helper] = numeric.where(numeric.notna(), df[column].astype(str))
        else:
            df[helper] = df[column]
        sort_helpers.append(helper)
    if sort_helpers:
        df = df.sort_values(sort_helpers, kind="mergesort").drop(columns=sort_helpers)
    df.to_csv(path, index=False)


def parse_all_smiles(path: Path) -> dict[int, str]:
    mapping: dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line_index, line in enumerate(handle):
            text = line.strip()
            if not text:
                continue
            parts = text.split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                mapping[int(parts[0])] = parts[1].strip()
            else:
                mapping[line_index] = text
    return mapping


def validate_resources(model: str, args: argparse.Namespace) -> None:
    if model == "iceberg":
        required = [ICEBERG_LEGACY_DIR, args.iceberg_python, args.iceberg_gen_checkpoint, args.iceberg_inten_checkpoint]
    elif model == "massformer":
        required = [MASSFORMER_DIR, args.massformer_python, args.massformer_config, MASSFORMER_CHECKPOINT]
    else:
        raise ValueError(f"Unsupported model: {model}")
    missing = [str(path) for path in required if not Path(path).exists()]
    if missing:
        raise FileNotFoundError(f"Missing resources for {model}: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["iceberg", "massformer"], required=True)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--query-start", type=int, default=0)
    parser.add_argument("--query-limit", type=int, default=0)
    parser.add_argument("--candidate-limit", type=int, default=0, help="Debug limit per query; 0 means full candidate set.")
    parser.add_argument("--candidate-chunk-size", type=int, default=256)
    parser.add_argument("--model-batch-size", type=int, default=1)
    parser.add_argument("--top-predictions", type=int, default=100)
    parser.add_argument("--max-predicted-peaks", type=int, default=100)
    parser.add_argument("--bin-width", type=float, default=1.0)
    parser.add_argument("--intensity-power", type=float, default=0.5)
    parser.add_argument("--command-timeout-seconds", type=int, default=1800)
    parser.add_argument("--retry-failed-singletons", dest="retry_failed_singletons", action="store_true", default=True)
    parser.add_argument("--no-retry-failed-singletons", dest="retry_failed_singletons", action="store_false")
    parser.add_argument("--max-retry-depth", type=int, default=12)
    parser.add_argument("--keep-raw", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--supported-mh-only", action="store_true", help="Restrict to [M+H]+ queries.")
    parser.add_argument("--shard-name", default="", help="Optional shard subdirectory under the model output directory.")
    parser.add_argument("--iceberg-python", type=Path, default=ICEBERG_PYTHON)
    parser.add_argument("--iceberg-gen-checkpoint", type=Path, default=ICEBERG_GEN_CKPT)
    parser.add_argument("--iceberg-inten-checkpoint", type=Path, default=ICEBERG_INTEN_CKPT)
    parser.add_argument("--massformer-python", type=Path, default=MASSFORMER_PYTHON)
    parser.add_argument("--massformer-config", type=Path, default=MASSFORMER_CONFIG)
    parser.add_argument("--massformer-device-id", type=int, default=-1, help="MassFormer device id: -1 for CPU, 0 for cuda:0.")
    parser.add_argument(
        "--fail-graph-assertion-batches",
        action="store_true",
        help="Debug mode: keep recursively splitting MassFormer graph assertion failures instead of marking the batch failed.",
    )
    parser.add_argument(
        "--graph-assertion-fail-batch-size",
        type=int,
        default=16,
        help="Minimum MassFormer graph-assertion retry batch size before recording the batch as failed.",
    )
    args = parser.parse_args()

    if not args.outdir.is_absolute():
        args.outdir = ROOT / args.outdir

    validate_resources(args.model, args)
    model_outdir = args.outdir / args.model
    if args.shard_name:
        shard_name = Path(args.shard_name).name
        if shard_name != args.shard_name:
            raise ValueError(f"--shard-name must be a simple directory name, got {args.shard_name!r}")
        model_outdir = model_outdir / shard_name
    model_outdir.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(CASMI_DIR / "spec_df.pkl").sort_values("spec_id").copy()
    if args.supported_mh_only:
        spec = spec[spec["prec_type"].astype(str).eq("[M+H]+")].copy()
    if args.model == "iceberg":
        spec = spec[spec["prec_type"].astype(str).isin(ICEBERG_SUPPORTED_ADDUCTS)].copy()
    elif args.model == "massformer":
        spec = spec[spec["prec_type"].astype(str).isin(MASSFORMER_SUPPORTED_ADDUCTS)].copy()
    stop = None if args.query_limit <= 0 else args.query_start + args.query_limit
    selected = spec.iloc[max(0, args.query_start) : stop].copy()
    cand = pd.read_pickle(CASMI_DIR / "cand_df.pkl")
    grouped = {int(k): v["candidate_mol_id"].astype(int).tolist() for k, v in cand.groupby("query_mol_id", sort=False)}
    smiles_by_id = parse_all_smiles(CASMI_DIR / "all_smiles.txt")

    query_path = model_outdir / f"casmi2022_{args.model}_harmonized_query_results.csv"
    top_path = model_outdir / f"casmi2022_{args.model}_harmonized_top_predictions.csv"
    existing = load_existing(query_path)
    completed_query_ids: set[str] = set()
    if args.resume and not existing.empty:
        reusable_statuses = {"completed", "partial_prediction_failures"}
        completed_query_ids = set(existing[existing["status"].astype(str).isin(reusable_statuses)]["query_id"].astype(str))
    query_rows = [] if existing.empty else existing.to_dict(orient="records")
    top_rows = [] if not args.resume else load_existing(top_path).to_dict(orient="records")
    temp_parent = model_outdir / "_raw" if args.keep_raw else Path(tempfile.mkdtemp(prefix=f"{args.model}_harmonized_"))
    temp_parent.mkdir(parents=True, exist_ok=True)

    try:
        for _, row in selected.iterrows():
            query_id = safe_query_id(row)
            if query_id in completed_query_ids:
                continue
            candidate_ids = grouped.get(int(row["mol_id"]), [])
            if int(row["mol_id"]) not in candidate_ids:
                candidate_ids = [int(row["mol_id"])] + candidate_ids
            if args.candidate_limit > 0:
                keep = candidate_ids[: args.candidate_limit]
                if int(row["mol_id"]) not in keep:
                    keep = [int(row["mol_id"])] + keep
                candidate_ids = keep
            candidates = [(candidate_id, smiles_by_id.get(candidate_id, "")) for candidate_id in candidate_ids]
            candidates = [(candidate_id, smiles) for candidate_id, smiles in candidates if smiles]
            query_result, query_top_rows = score_query(args.model, row, candidates, args, temp_parent)
            query_rows = [existing_row for existing_row in query_rows if str(existing_row.get("query_id")) != query_id]
            top_rows = [existing_row for existing_row in top_rows if str(existing_row.get("query_id")) != query_id]
            query_rows.append(query_result)
            top_rows.extend(query_top_rows)
            write_sorted_csv(query_rows, query_path, ["query_id"])
            write_sorted_csv(top_rows, top_path, ["query_id", "rank"])
            print(json.dumps(json_safe(query_result), sort_keys=True), flush=True)
    finally:
        if not args.keep_raw:
            shutil.rmtree(temp_parent, ignore_errors=True)

    qdf = pd.DataFrame(query_rows)
    completed = qdf[qdf["status"].astype(str).eq("completed")].copy() if not qdf.empty else pd.DataFrame()
    rank_valid = completed[pd.to_numeric(completed["true_rank"], errors="coerce").notna()].copy() if not completed.empty else pd.DataFrame()
    expected_queries = int(len(spec))
    status = "completed_harmonized_candidate_rerun" if len(rank_valid) == expected_queries and expected_queries else "partial_harmonized_candidate_rerun"
    summary = {
        "dataset": "CASMI2022",
        "model": args.model,
        "status": status,
        "n_expected_queries": expected_queries,
        "n_queries_completed": int(len(completed)),
        "n_rank_valid_queries": int(len(rank_valid)),
        "candidate_limit": int(args.candidate_limit) if args.candidate_limit > 0 else -1,
        "candidate_pool_policy": "full_query_candidate_set" if args.candidate_limit <= 0 else "debug_candidate_limited",
        "score_name": f"binned_cosine_{args.bin_width:g}Da",
        "top1_accuracy": float(rank_valid["top1_correct"].mean()) if not rank_valid.empty else np.nan,
        "top5_accuracy": float(rank_valid["top5_correct"].mean()) if not rank_valid.empty else np.nan,
        "top10_accuracy": float(rank_valid["top10_correct"].mean()) if not rank_valid.empty else np.nan,
        "mean_reciprocal_rank": float(rank_valid["reciprocal_rank"].mean()) if not rank_valid.empty else np.nan,
        "mean_top1_tanimoto": float(pd.to_numeric(rank_valid["top1_tanimoto"], errors="coerce").mean()) if not rank_valid.empty else np.nan,
        "formula_accuracy": float(rank_valid["formula_accuracy"].astype(bool).mean()) if not rank_valid.empty else np.nan,
        "total_candidate_rows_scored": int(pd.to_numeric(rank_valid.get("predicted_spectrum_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not rank_valid.empty else 0,
        "total_failed_predictions": int(pd.to_numeric(qdf.get("failed_prediction_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not qdf.empty else 0,
        "top_predictions_per_query_stored": int(args.top_predictions),
        "claim_guardrail": "This is a harmonized direct rerun only when candidate_limit == -1 and status == completed_harmonized_candidate_rerun.",
    }
    pd.DataFrame([summary]).to_csv(model_outdir / f"casmi2022_{args.model}_harmonized_summary.csv", index=False)
    write_json(
        model_outdir / "audit_summary.json",
        {
            "stage": "harmonized_sota_candidate_reruns_v1",
            "model": args.model,
            "query_results": query_path.name,
            "top_predictions": top_path.name,
            **summary,
        },
    )
    report = [
        f"# CASMI2022 {args.model} Harmonized Candidate-Set Rerun",
        "",
        summary["claim_guardrail"],
        "",
        "## Summary",
        "",
        "\n".join(f"- `{key}`: `{value}`" for key, value in summary.items()),
        "",
    ]
    (model_outdir / f"casmi2022_{args.model}_harmonized_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
