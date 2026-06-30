#!/usr/bin/env python3
"""Run trained FragAnnotor neural spectrum scoring on CASMI2022 candidates.

This script is deliberately report-only: it loads a frozen checkpoint trained
outside the CASMI2022 benchmark, predicts a binned spectrum for each candidate
structure, ranks candidates by cosine similarity to the measured CASMI spectrum,
and writes an overlap/leakage audit. It does not train or tune on CASMI.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TP_ROOT = ROOT.parent.parent / "pollutant_transform_pretraining"
DEFAULT_CHECKPOINT = (
    DEFAULT_TP_ROOT
    / "outputs"
    / "calibration_aware_model_v1"
    / "model_runs"
    / "calibration_weighted_model"
    / "checkpoints"
    / "best_model.pt"
)
DEFAULT_TRAINING_PAIRS = DEFAULT_CHECKPOINT.parents[1] / "pairs.jsonl"

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors
    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")
except Exception as exc:  # pragma: no cover
    raise RuntimeError("RDKit is required for CASMI neural FragAnnotor inference") from exc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def canonical_smiles(smiles: str | None) -> str:
    if not smiles:
        return ""
    mol = Chem.MolFromSmiles(str(smiles))
    return Chem.MolToSmiles(mol, isomericSmiles=True) if mol is not None else ""


def formula_from_smiles(smiles: str | None) -> str:
    mol = Chem.MolFromSmiles(str(smiles)) if smiles else None
    return rdMolDescriptors.CalcMolFormula(mol) if mol is not None else ""


def exact_mass_from_smiles(smiles: str | None) -> float:
    mol = Chem.MolFromSmiles(str(smiles)) if smiles else None
    return float(Descriptors.ExactMolWt(mol)) if mol is not None else 0.0


def morgan_fp(smiles: str, n_bits: int, radius: int) -> np.ndarray:
    arr = np.zeros(n_bits, dtype=np.float32)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return arr
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr.astype(np.float32)


def one_hot(value: Any, vocab: list[str]) -> np.ndarray:
    out = np.zeros(len(vocab), dtype=np.float32)
    text = "" if value is None else str(value).strip()
    if text in vocab:
        out[vocab.index(text)] = 1.0
    return out


def ion_mode_text(value: Any) -> str:
    text = "" if value is None else str(value).strip().lower()
    if text in {"p", "pos", "positive", "+"}:
        return "positive"
    if text in {"n", "neg", "negative", "-"}:
        return "negative"
    return text


def collision_text(row: pd.Series) -> str:
    for key in ["collision_energy", "nce", "ace"]:
        value = row.get(key)
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            if text.endswith(".0"):
                text = text[:-2]
            return text
    return ""


def bin_spectrum(peaks: list[tuple[float, float]], mz_min: float, mz_max: float, bin_width: float) -> np.ndarray:
    n_bins = int(math.floor((mz_max - mz_min) / bin_width)) + 1
    vec = np.zeros(n_bins, dtype=np.float32)
    for mz, intensity in peaks:
        if mz < mz_min or mz > mz_max or intensity <= 0:
            continue
        idx = int(round((mz - mz_min) / bin_width))
        if 0 <= idx < len(vec):
            vec[idx] = max(vec[idx], float(intensity))
    max_i = float(vec.max())
    if max_i > 0:
        vec /= max_i
    return vec


class FingerprintMLP(torch.nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden_dim: int = 256, dropout: float = 0.15):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_dim, output_dim),
            torch.nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def load_all_smiles(path: Path, needed_ids: set[int]) -> dict[int, str]:
    out: dict[int, str] = {}
    remaining = set(needed_ids)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not remaining:
                break
            line = line.strip()
            if not line:
                continue
            mol_id_text, _, smiles = line.partition(" ")
            try:
                mol_id = int(mol_id_text)
            except ValueError:
                continue
            if mol_id in remaining:
                out[mol_id] = smiles.strip()
                remaining.remove(mol_id)
    return out


def load_casmi(casmi_dir: Path, candidate_limit: int) -> tuple[pd.DataFrame, dict[int, list[int]], dict[int, str]]:
    spec = pd.read_pickle(casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(casmi_dir / "cand_df.pkl")
    grouped = {
        int(k): v["candidate_mol_id"].astype(int).tolist()
        for k, v in cand.groupby("query_mol_id", sort=False)
    }
    selected: dict[int, list[int]] = {}
    needed: set[int] = set()
    for _, row in spec.iterrows():
        qid = int(row["mol_id"])
        ids = grouped.get(qid, [])
        if candidate_limit > 0:
            ids = ids[:candidate_limit]
        if qid not in ids:
            ids = [qid] + ids
        selected[qid] = ids
        needed.update(ids)
        needed.add(qid)
    smiles = load_all_smiles(casmi_dir / "all_smiles.txt", needed)
    return spec, selected, smiles


def build_features(
    smiles_batch: list[str],
    row: pd.Series,
    config: dict[str, Any],
    vocab: dict[str, list[str]],
    fp_cache: dict[str, np.ndarray],
    mass_cache: dict[str, float],
) -> np.ndarray:
    fp_bits = int(config.get("fingerprint_bits", 2048))
    radius = int(config.get("morgan_radius", 2))
    precursor = safe_float(row.get("prec_mz"), 0.0) / 1000.0
    mode = ion_mode_text(row.get("ion_mode"))
    adduct = str(row.get("prec_type") or "").strip()
    ce = collision_text(row)
    category = "unknown_or_other"
    categorical = np.concatenate(
        [
            one_hot(mode, vocab.get("ion_mode", [])),
            one_hot(adduct, vocab.get("adduct", [])),
            one_hot(ce, vocab.get("collision_energy", [])),
            one_hot(category, vocab.get("category", [])),
        ]
    ).astype(np.float32)
    rows = []
    for smiles in smiles_batch:
        if smiles not in fp_cache:
            fp_cache[smiles] = morgan_fp(smiles, fp_bits, radius)
        if smiles not in mass_cache:
            mass_cache[smiles] = exact_mass_from_smiles(smiles)
        numeric = np.array([mass_cache[smiles] / 1000.0, precursor], dtype=np.float32)
        rows.append(np.concatenate([fp_cache[smiles], numeric, categorical]).astype(np.float32))
    return np.stack(rows).astype(np.float32)


def cosine_scores(pred: np.ndarray, target: np.ndarray) -> np.ndarray:
    target_norm = np.linalg.norm(target)
    pred_norm = np.linalg.norm(pred, axis=1)
    denom = pred_norm * target_norm
    raw = pred @ target
    out = np.zeros(len(pred), dtype=np.float32)
    mask = denom > 0
    out[mask] = raw[mask] / denom[mask]
    return out


def morgan_tanimoto(smiles_a: str | None, smiles_b: str | None) -> float:
    mol_a = Chem.MolFromSmiles(str(smiles_a)) if smiles_a else None
    mol_b = Chem.MolFromSmiles(str(smiles_b)) if smiles_b else None
    if mol_a is None or mol_b is None:
        return float("nan")
    fp_a = AllChem.GetMorganFingerprintAsBitVect(mol_a, 2, nBits=2048)
    fp_b = AllChem.GetMorganFingerprintAsBitVect(mol_b, 2, nBits=2048)
    return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))


def audit_training_overlap(training_pairs: Path, casmi_smiles: set[str]) -> dict[str, Any]:
    split_counts: Counter[str] = Counter()
    overlap_counts: Counter[str] = Counter()
    examples: list[dict[str, str]] = []
    if not training_pairs.exists():
        return {"status": "training_pairs_missing", "path": str(training_pairs)}
    with training_pairs.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            obj = json.loads(line)
            split = str(obj.get("split") or "unknown")
            split_counts[split] += 1
            structure = obj.get("structure") or {}
            smiles = canonical_smiles(structure.get("canonical_smiles") or structure.get("smiles"))
            if smiles in casmi_smiles:
                overlap_counts[split] += 1
                if len(examples) < 20:
                    examples.append({"split": split, "canonical_smiles": smiles, "pair_id": str(obj.get("pair_id") or "")})
    return {
        "status": "checked",
        "path": str(training_pairs),
        "training_pair_count_by_split": dict(split_counts),
        "casmi_overlap_count_by_split": dict(overlap_counts),
        "has_casmi_structure_overlap": bool(sum(overlap_counts.values())),
        "overlap_examples": examples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run trained FragAnnotor neural CASMI2022 inference.")
    parser.add_argument("--casmi-dir", type=Path, default=ROOT / "data" / "proc" / "casmi_2022")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--training-pairs", type=Path, default=DEFAULT_TRAINING_PAIRS)
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "casmi2022_fragannotor_trained_neural_v1")
    parser.add_argument("--candidate-limit", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=20260628)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    args.outdir.mkdir(parents=True, exist_ok=True)
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    config = dict(checkpoint.get("config") or {})
    vocab = checkpoint.get("vocab") or config.get("metadata_vocab") or checkpoint.get("metadata_vocab") or {}
    input_dim = int(checkpoint.get("input_dim") or config.get("input_dim"))
    output_dim = int(checkpoint.get("output_dim") or config.get("output_dim"))
    model = FingerprintMLP(
        input_dim=input_dim,
        output_dim=output_dim,
        hidden_dim=int(config.get("hidden_dim", 256)),
        dropout=float(config.get("dropout", 0.15)),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    spec, selected, id_to_smiles = load_casmi(args.casmi_dir, args.candidate_limit)
    casmi_canonical = {canonical_smiles(s) for s in spec["smiles"].dropna().astype(str)}
    casmi_canonical.discard("")
    leakage = audit_training_overlap(args.training_pairs, casmi_canonical)

    fp_cache: dict[str, np.ndarray] = {}
    mass_cache: dict[str, float] = {}
    formula_cache: dict[str, str] = {}
    pred_rows: list[dict[str, Any]] = []
    query_rows: list[dict[str, Any]] = []
    unsupported_adducts: Counter[str] = Counter()
    unknown_ce = 0

    mz_min = float(config.get("mz_min", 0.0))
    mz_max = float(config.get("mz_max", 1000.0))
    bin_width = float(config.get("bin_width", 1.0))

    with torch.no_grad():
        for _, row in spec.iterrows():
            qid = int(row["mol_id"])
            query_id = str(row["spec_id"])
            true_smiles = str(row.get("smiles") or id_to_smiles.get(qid, ""))
            true_formula = formula_from_smiles(true_smiles)
            ids = [mol_id for mol_id in selected.get(qid, []) if id_to_smiles.get(mol_id)]
            smiles_list = [id_to_smiles[mol_id] for mol_id in ids]
            if str(row.get("prec_type") or "") not in vocab.get("adduct", []):
                unsupported_adducts[str(row.get("prec_type") or "")] += 1
            if not collision_text(row):
                unknown_ce += 1
            peaks = [(float(mz), float(intensity)) for mz, intensity in row.get("peaks", [])]
            target = bin_spectrum(peaks, mz_min, mz_max, bin_width)
            scores = []
            for start in range(0, len(smiles_list), args.batch_size):
                batch_smiles = smiles_list[start : start + args.batch_size]
                features = build_features(batch_smiles, row, config, vocab, fp_cache, mass_cache)
                if features.shape[1] != input_dim:
                    raise RuntimeError(f"Feature dimension {features.shape[1]} does not match checkpoint input_dim {input_dim}")
                pred = model(torch.from_numpy(features)).cpu().numpy()
                scores.extend(cosine_scores(pred, target).tolist())
            rows = []
            for mol_id, smiles, score in zip(ids, smiles_list, scores):
                if smiles not in formula_cache:
                    formula_cache[smiles] = formula_from_smiles(smiles)
                cand_key = f"CASMI_MOL_{mol_id}"
                rows.append(
                    {
                        "dataset": "CASMI2022",
                        "spectrum_id": query_id,
                        "query_id": query_id,
                        "model": "FragAnnotor-trained-neural",
                        "candidate_id": cand_key,
                        "candidate_smiles": smiles,
                        "candidate_inchikey": cand_key,
                        "candidate_formula": formula_cache[smiles],
                        "score": float(score),
                        "true_inchikey": f"CASMI_MOL_{qid}",
                        "true_smiles": true_smiles,
                        "true_formula": true_formula,
                        "is_correct": mol_id == qid,
                        "score_source": "trained_fragannotor_neural_predicted_spectrum_cosine",
                        "native_or_fallback": "trained_neural_checkpoint_report_only",
                        "tool_version": f"checkpoint:{args.checkpoint}",
                        "command": "python scripts/run_casmi_fragannotor_neural.py",
                        "error_message": "",
                    }
                )
            rows.sort(key=lambda item: (-item["score"], item["candidate_inchikey"], item["candidate_id"]))
            for rank, pred_row in enumerate(rows, start=1):
                pred_row["rank"] = rank
            pred_rows.extend(rows)
            true_rank = next((item["rank"] for item in rows if item["is_correct"]), float("nan"))
            top1 = rows[0] if rows else {}
            reciprocal = 0.0 if pd.isna(true_rank) else 1.0 / float(true_rank)
            query_rows.append(
                {
                    "dataset": "CASMI2022",
                    "spectrum_id": query_id,
                    "query_id": query_id,
                    "model": "FragAnnotor-trained-neural",
                    "status": "completed",
                    "native_or_fallback": "trained_neural_checkpoint_report_only",
                    "true_inchikey": f"CASMI_MOL_{qid}",
                    "true_smiles": true_smiles,
                    "true_formula": true_formula,
                    "precursor_mz": safe_float(row.get("prec_mz"), float("nan")),
                    "ion_mode": ion_mode_text(row.get("ion_mode")),
                    "adduct": str(row.get("prec_type") or ""),
                    "collision_energy": collision_text(row),
                    "candidate_count": len(rows),
                    "true_rank": true_rank,
                    "top1_correct": bool(true_rank == 1),
                    "top5_correct": bool(not pd.isna(true_rank) and true_rank <= 5),
                    "top10_correct": bool(not pd.isna(true_rank) and true_rank <= 10),
                    "reciprocal_rank": reciprocal,
                    "top1_candidate_smiles": top1.get("candidate_smiles", ""),
                    "top1_candidate_inchikey": top1.get("candidate_inchikey", ""),
                    "top1_score": top1.get("score", float("nan")),
                    "top1_tanimoto": morgan_tanimoto(true_smiles, top1.get("candidate_smiles")),
                    "formula_correct": bool(true_formula and top1.get("candidate_formula") == true_formula),
                    "error_message": "",
                }
            )

    predictions = pd.DataFrame(pred_rows)
    query = pd.DataFrame(query_rows)
    summary = pd.DataFrame(
        [
            {
                "dataset": "CASMI2022",
                "model": "FragAnnotor-trained-neural",
                "status": "completed",
                "native_or_fallback": "trained_neural_checkpoint_report_only",
                "n_queries": int(len(query)),
                "top1_accuracy": float(query["top1_correct"].mean()),
                "top5_accuracy": float(query["top5_correct"].mean()),
                "top10_accuracy": float(query["top10_correct"].mean()),
                "mean_reciprocal_rank": float(query["reciprocal_rank"].mean()),
                "mean_top1_tanimoto": float(query["top1_tanimoto"].mean()),
                "molecular_formula_accuracy": float(query["formula_correct"].mean()),
                "median_true_rank": float(query["true_rank"].median()),
                "median_candidate_count": float(query["candidate_count"].median()),
            }
        ]
    )

    pred_path = args.outdir / "casmi2022_fragannotor_trained_neural_predictions.csv.gz"
    predictions.to_csv(pred_path, index=False, compression="gzip")
    manifest = {
        "artifact": pred_path.name,
        "rows": int(len(predictions)),
        "sha256": sha256_file(pred_path),
        "note": "Large candidate-level prediction table is gzip-compressed.",
    }
    write_json(args.outdir / "casmi2022_fragannotor_trained_neural_predictions_manifest.json", manifest)
    query.to_csv(args.outdir / "casmi2022_fragannotor_trained_neural_query_results.csv", index=False)
    summary.to_csv(args.outdir / "casmi2022_fragannotor_trained_neural_summary.csv", index=False)

    audit = {
        "stage": "casmi2022_fragannotor_trained_neural_v1",
        "status": "completed",
        "claim_guardrail": "Report-only CASMI inference from a frozen trained neural spectrum checkpoint. No CASMI labels were used for training, weight search, or checkpoint selection in this script.",
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256_file(args.checkpoint),
        "training_pairs": str(args.training_pairs),
        "training_pairs_sha256": sha256_file(args.training_pairs) if args.training_pairs.exists() else "",
        "training_overlap_audit": leakage,
        "candidate_limit": args.candidate_limit,
        "input_dim": input_dim,
        "output_dim": output_dim,
        "config": config,
        "vocab_coverage": {
            "unsupported_adduct_query_counts": dict(unsupported_adducts),
            "queries_with_missing_collision_energy": int(unknown_ce),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "torch": torch.__version__,
        },
        "summary": summary.replace({np.nan: None}).to_dict(orient="records")[0],
    }
    write_json(args.outdir / "trained_neural_claim_audit.json", audit)

    report = f"""# CASMI2022 FragAnnotor Trained Neural Checkpoint Report

Frozen checkpoint: `{args.checkpoint}`

This report ranks CASMI2022 candidates by cosine similarity between the measured CASMI MS/MS vector and the spectrum vector predicted by a trained FragAnnotor neural checkpoint. The script does not train, tune weights, or select checkpoints on CASMI.

## Result

- Queries: {int(summary.loc[0, 'n_queries'])}
- Candidate rows: {len(predictions)}
- Top-1: {float(summary.loc[0, 'top1_accuracy']):.6f}
- Top-5: {float(summary.loc[0, 'top5_accuracy']):.6f}
- Top-10: {float(summary.loc[0, 'top10_accuracy']):.6f}
- MRR: {float(summary.loc[0, 'mean_reciprocal_rank']):.6f}
- Mean Top-1 Tanimoto: {float(summary.loc[0, 'mean_top1_tanimoto']):.6f}
- Molecular formula accuracy: {float(summary.loc[0, 'molecular_formula_accuracy']):.6f}

## Leakage Guardrail

Training-pair overlap with CASMI canonical SMILES: `{leakage.get('has_casmi_structure_overlap')}`.

## Scope

This is the formal trained neural CASMI report for the frozen checkpoint above. It is separate from the previous fixed component-score CASMI mode and should not be described as trained or tuned on CASMI.
"""
    (args.outdir / "casmi2022_fragannotor_trained_neural_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(audit["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
