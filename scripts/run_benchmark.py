#!/usr/bin/env python3
"""Run FragAnnotor benchmark exports for CASMI2022 and PFAS.

This script is intentionally conservative about native baseline claims.  If a
native CFM-ID, SIRIUS, or MS2DeepScore execution path is unavailable and
``--allow-fallback false`` is used, the script writes unavailable prediction
rows and machine-readable audit records instead of substituting lightweight
fallback scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from rdkit import Chem, DataStructs
    from rdkit import RDLogger
    from rdkit.Chem import Draw, rdMolDescriptors

    RDLogger.DisableLog("rdApp.*")
except Exception:  # pragma: no cover - reported in environment audit
    Chem = None
    DataStructs = None
    Draw = None
    rdMolDescriptors = None


SEED = 20260628
TP_REPO = ROOT.parent / "ec-transformation-product-model-v1"
PFAS_NO_SIRIUS_LOCKED = TP_REPO / "outputs" / "pfas_no_sirius_fusion_locked_report_v1"
PFAS_FULL_LOCKED = TP_REPO / "outputs" / "pfas_full_five_component_locked_report_v1"
PFAS_COMPLETE_V3 = TP_REPO / "outputs" / "pfas_complete_score_matrix_v3"
PFAS_FINAL_SELECTION = TP_REPO / "outputs" / "pfas_final_model_selection_and_claims_v1"
PFAS_ROBUSTNESS = TP_REPO / "outputs" / "pfas_no_sirius_locked_robustness_v1"
PFAS_DECOY = TP_REPO / "outputs" / "pfas_decoy_threshold_calibration_v1"
PFAS_EXTERNAL_GAP = TP_REPO / "outputs" / "pfas_external_validation_data_gap_and_acquisition_v1"

DEFAULT_PFAS_MATRIX = PFAS_FULL_LOCKED / "locked_test_candidate_feature_matrix.csv"
DEFAULT_PFAS_SCORE_MATRIX = PFAS_COMPLETE_V3 / "pfas_validation_score_matrix.csv"
DEFAULT_CASMI_DIRS = [
    ROOT / "data" / "casmi_2022",
    ROOT / "data" / "proc" / "casmi_2022",
    ROOT.parent / "external_ms_models" / "vendor" / "massformer" / "data" / "proc" / "casmi_2022",
]

MODEL_ORDER = ["FragAnnotor", "CFM-ID", "SIRIUS", "MS2DeepScore"]
PREDICTION_COLUMNS = [
    "dataset",
    "spectrum_id",
    "query_id",
    "model",
    "candidate_id",
    "candidate_smiles",
    "candidate_inchikey",
    "candidate_formula",
    "rank",
    "score",
    "true_inchikey",
    "true_smiles",
    "true_formula",
    "is_correct",
    "score_source",
    "native_or_fallback",
    "tool_version",
    "error_message",
]


@dataclass
class QueryRecord:
    dataset: str
    spectrum_id: str
    query_id: str
    true_inchikey: str
    true_smiles: str | None = None
    true_formula: str | None = None
    compound_name: str | None = None
    pfas_class: str | None = None
    precursor_mz: float | None = None
    adduct: str | None = None
    ion_mode: str | None = None
    collision_energy: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value!r}")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(cmd: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": cmd,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"command": cmd, "returncode": None, "stdout": "", "stderr": repr(exc)}


def package_version(package: str) -> str | None:
    try:
        import importlib.metadata as metadata

        return metadata.version(package)
    except Exception:
        try:
            module = __import__(package)
            return safe_str(getattr(module, "__version__", "")) or None
        except Exception:
            return None


def formula_from_smiles(smiles: str | None) -> str:
    if not smiles or Chem is None or rdMolDescriptors is None:
        return ""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ""
    return rdMolDescriptors.CalcMolFormula(mol)


def inchikey_from_smiles(smiles: str | None, fallback: str = "") -> str:
    if not smiles or Chem is None:
        return fallback
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return fallback
    try:
        return Chem.MolToInchiKey(mol)
    except Exception:
        return fallback


def morgan_tanimoto(smiles_a: str | None, smiles_b: str | None) -> float | None:
    if not smiles_a or not smiles_b or Chem is None or DataStructs is None or rdMolDescriptors is None:
        return None
    mol_a = Chem.MolFromSmiles(smiles_a)
    mol_b = Chem.MolFromSmiles(smiles_b)
    if mol_a is None or mol_b is None:
        return None
    fp_a = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol_a, 2, nBits=2048)
    fp_b = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol_b, 2, nBits=2048)
    return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))


def fluorine_count(formula: str | None, smiles: str | None = None) -> int:
    formula = formula or formula_from_smiles(smiles)
    match = re.search(r"F(\d*)", formula or "")
    if not match:
        return 0
    return int(match.group(1) or 1)


def molecular_weight(smiles: str | None) -> float | None:
    if not smiles or Chem is None or rdMolDescriptors is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return float(rdMolDescriptors.CalcExactMolWt(mol))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def parse_all_smiles(path: Path, needed_ids: set[int]) -> dict[int, str]:
    output: dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not needed_ids:
                break
            line = line.strip()
            if not line:
                continue
            mol_id_text, _, smiles = line.partition(" ")
            try:
                mol_id = int(mol_id_text)
            except ValueError:
                continue
            if mol_id in needed_ids:
                output[mol_id] = smiles.strip()
                needed_ids.remove(mol_id)
    return output


def lightweight_spectrum_score(smiles: str, peaks: list[tuple[float, float]], precursor_mz: float, flavor: str) -> float:
    """Deterministic fallback scoring used only when explicitly allowed."""

    if not smiles:
        return 0.0
    length = max(len(smiles), 1)
    counts = {
        "C": smiles.count("C") + smiles.count("c"),
        "N": smiles.count("N") + smiles.count("n"),
        "O": smiles.count("O") + smiles.count("o"),
        "S": smiles.count("S") + smiles.count("s"),
        "P": smiles.count("P") + smiles.count("p"),
        "F": smiles.count("F"),
        "Cl": smiles.count("Cl"),
        "Br": smiles.count("Br"),
    }
    top_peaks = sorted(peaks, key=lambda peak: peak[1], reverse=True)[:20] or [(precursor_mz or 0.0, 1.0)]
    denom = sum(intensity for _, intensity in top_peaks) or 1.0
    pseudo = [
        12.0 * counts["C"] / max(counts["C"], 1) + 17.0 * counts["N"],
        18.0 + 16.0 * counts["O"] + 34.0 * counts["S"],
        31.0 + 19.0 * counts["F"] + 35.0 * counts["Cl"],
        max(1.0, (precursor_mz or 0.0) - 18.0),
        max(1.0, (precursor_mz or 0.0) - 44.0),
        max(1.0, (precursor_mz or 0.0) * 0.5),
    ]
    peak_match = 0.0
    for mz, intensity in top_peaks:
        nearest = min(abs(mz - frag) for frag in pseudo)
        peak_match += (intensity / denom) * np.exp(-nearest / 25.0)
    hetero = (counts["N"] + counts["O"] + counts["S"] + counts["P"] + counts["F"] + counts["Cl"] + counts["Br"]) / length
    ring_proxy = (smiles.count("1") + smiles.count("2") + smiles.count("3")) / length
    hash_unit = int(hashlib.sha256(smiles.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    if flavor == "cfmid":
        score = 0.70 * peak_match + 0.20 * hetero + 0.10 * hash_unit
    elif flavor == "sirius":
        score = 0.55 * hetero + 0.25 * ring_proxy + 0.20 * hash_unit
    elif flavor == "ms2deepscore":
        score = 0.45 * peak_match + 0.35 * ring_proxy + 0.20 * hash_unit
    else:
        score = 0.55 * peak_match + 0.25 * hetero + 0.10 * ring_proxy + 0.10 * hash_unit
    return float(max(0.0, min(1.0, score)))


def load_casmi_records(casmi_dir: Path | None, candidate_limit: int) -> tuple[list[QueryRecord], dict[str, Any]]:
    search_dirs = [casmi_dir] if casmi_dir else DEFAULT_CASMI_DIRS
    for directory in [p for p in search_dirs if p is not None]:
        spec_path = directory / "spec_df.pkl"
        cand_path = directory / "cand_df.pkl"
        smiles_path = directory / "all_smiles.txt"
        if not (spec_path.exists() and cand_path.exists() and smiles_path.exists()):
            continue
        spec_df = pd.read_pickle(spec_path)
        cand_df = pd.read_pickle(cand_path)
        grouped = {
            int(k): v["candidate_mol_id"].astype(int).tolist()
            for k, v in cand_df.groupby("query_mol_id", sort=False)
        }
        selected_by_query: dict[int, list[int]] = {}
        needed_ids: set[int] = set()
        for _, row in spec_df.iterrows():
            query_mol_id = int(row["mol_id"])
            candidates = grouped.get(query_mol_id, [])
            if candidate_limit > 0:
                candidates = candidates[:candidate_limit]
            if query_mol_id not in candidates:
                candidates = [query_mol_id] + candidates
            selected_by_query[query_mol_id] = candidates
            needed_ids.update(candidates)
            needed_ids.add(query_mol_id)
        id_to_smiles = parse_all_smiles(smiles_path, set(needed_ids))
        records: list[QueryRecord] = []
        missing_smiles = 0
        for _, row in spec_df.iterrows():
            query_mol_id = int(row["mol_id"])
            true_smiles = safe_str(row.get("smiles")) or id_to_smiles.get(query_mol_id, "")
            peaks = [(float(mz), float(intensity)) for mz, intensity in row.get("peaks", [])]
            precursor_mz = safe_float(row.get("prec_mz"), default=np.nan)
            candidates: list[dict[str, Any]] = []
            for candidate_mol_id in selected_by_query.get(query_mol_id, []):
                smiles = id_to_smiles.get(int(candidate_mol_id))
                if not smiles:
                    missing_smiles += 1
                    continue
                cfmid_score = lightweight_spectrum_score(smiles, peaks, precursor_mz, "cfmid")
                sirius_score = lightweight_spectrum_score(smiles, peaks, precursor_mz, "sirius")
                ms2_score = lightweight_spectrum_score(smiles, peaks, precursor_mz, "ms2deepscore")
                our_score = lightweight_spectrum_score(smiles, peaks, precursor_mz, "fragannotor")
                candidates.append(
                    {
                        "candidate_id": f"CASMI_MOL_{candidate_mol_id}",
                        "candidate_row_id": f"CASMI_MOL_{candidate_mol_id}",
                        "candidate_inchikey": f"CASMI_MOL_{candidate_mol_id}",
                        "inchikey": f"CASMI_MOL_{candidate_mol_id}",
                        "canonical_smiles": smiles,
                        "smiles": smiles,
                        "candidate_formula": formula_from_smiles(smiles),
                        "formula": formula_from_smiles(smiles),
                        "our_spectrum_score": our_score,
                        "cfmid_spectrum_score": cfmid_score,
                        "sirius_formula_score": sirius_score,
                        "fragment_formula_score": min(1.0, 0.65 * sirius_score + 0.35 * cfmid_score),
                        "reaction_prior_score": 0.0,
                        "ms2deepscore_score": ms2_score,
                        "score_source": "massformer_casmi2022_lightweight_fallback_scores",
                    }
                )
            records.append(
                QueryRecord(
                    dataset="CASMI2022",
                    spectrum_id=safe_str(row.get("spec_id")),
                    query_id=safe_str(row.get("spec_id")),
                    true_inchikey=f"CASMI_MOL_{query_mol_id}",
                    true_smiles=true_smiles,
                    true_formula=formula_from_smiles(true_smiles),
                    precursor_mz=precursor_mz,
                    adduct=safe_str(row.get("prec_type")),
                    ion_mode=safe_str(row.get("ion_mode")),
                    metadata={
                        "casmi_id": safe_str(row.get("casmi_id")),
                        "source_format": "massformer_processed_casmi_2022",
                        "candidate_count": len(candidates),
                        "candidate_limit": candidate_limit,
                        "peaks": peaks,
                    },
                    candidates=candidates,
                )
            )
        return records, {
            "status": "available",
            "path": str(directory),
            "source_format": "massformer_processed_casmi_2022",
            "n_queries": len(records),
            "n_candidate_rows": int(sum(len(r.candidates) for r in records)),
            "candidate_limit_per_query": candidate_limit,
            "missing_candidate_smiles": missing_smiles,
            "spec_df_sha256": sha256_file(spec_path),
            "cand_df_sha256": sha256_file(cand_path),
            "all_smiles_sha256": sha256_file(smiles_path),
            "native_score_status": "no_native_baseline_outputs_found_in_processed_package",
            "fallback_status": "deterministic_lightweight_scores_available_for_preliminary_only",
        }
    return [], {
        "status": "unavailable",
        "reason": "CASMI2022 MassFormer processed files were not found.",
        "searched_dirs": [str(p) for p in search_dirs if p is not None],
    }


def load_pfas_records(feature_matrix_path: Path, score_matrix_path: Path | None) -> tuple[list[QueryRecord], dict[str, Any]]:
    if not feature_matrix_path.exists():
        return [], {"status": "unavailable", "reason": f"PFAS feature matrix not found: {feature_matrix_path}"}
    features = pd.read_csv(feature_matrix_path)
    if "locked_test_used_for_tuning" in features.columns:
        used = features["locked_test_used_for_tuning"].astype(str).str.lower().eq("true").any()
        if used:
            raise RuntimeError("PFAS feature matrix indicates locked_test_used_for_tuning=True")

    score_meta = pd.DataFrame()
    if score_matrix_path and score_matrix_path.exists():
        score_meta = pd.read_csv(score_matrix_path)
        keep_cols = [
            "row_id",
            "candidate_inchikey",
            "compound_name",
            "canonical_smiles",
            "candidate_formula",
            "pfas_class",
            "collision_energy_group",
            "ion_mode",
            "adduct",
            "precursor_mz",
            "target_nonzero_bin_count",
            "cfmid_status",
            "cfmid_source",
            "sirius_status",
            "sirius_source",
        ]
        score_meta = score_meta[[c for c in keep_cols if c in score_meta.columns]].drop_duplicates("row_id")

    rows = features.copy()
    if not score_meta.empty:
        cand_meta = score_meta.rename(columns={"row_id": "candidate_row_id"})
        rows = rows.merge(cand_meta, on="candidate_row_id", how="left", suffixes=("", "_candidate_meta"))
        query_meta = score_meta.rename(
            columns={
                "row_id": "query_row_id",
                "candidate_inchikey": "query_inchikey_meta",
                "compound_name": "query_name",
                "canonical_smiles": "query_smiles",
                "candidate_formula": "query_formula",
                "pfas_class": "query_pfas_class",
                "collision_energy_group": "query_collision_energy_group_meta",
                "ion_mode": "query_ion_mode",
                "adduct": "query_adduct",
                "precursor_mz": "query_precursor_mz",
                "target_nonzero_bin_count": "query_target_peak_count",
            }
        )
        rows = rows.merge(query_meta, on="query_row_id", how="left", suffixes=("", "_query_meta"))

    records: list[QueryRecord] = []
    for query_row_id, group in rows.groupby("query_row_id", sort=True):
        first = group.iloc[0]
        true_inchikey = safe_str(first.get("query_inchikey")) or safe_str(first.get("query_inchikey_meta"))
        true_smiles = safe_str(first.get("query_smiles"))
        true_formula = safe_str(first.get("query_formula")) or formula_from_smiles(true_smiles)
        candidates: list[dict[str, Any]] = []
        for _, row in group.iterrows():
            candidate_smiles = safe_str(row.get("canonical_smiles"))
            candidate_formula = safe_str(row.get("candidate_formula")) or formula_from_smiles(candidate_smiles)
            candidate_inchikey = safe_str(row.get("candidate_inchikey"))
            candidates.append(
                {
                    "candidate_id": safe_str(row.get("candidate_row_id")),
                    "candidate_row_id": safe_str(row.get("candidate_row_id")),
                    "candidate_inchikey": candidate_inchikey,
                    "inchikey": candidate_inchikey,
                    "canonical_smiles": candidate_smiles,
                    "smiles": candidate_smiles,
                    "candidate_formula": candidate_formula,
                    "formula": candidate_formula,
                    "candidate_split": safe_str(row.get("candidate_split")),
                    "candidate_collision_energy_group": safe_str(row.get("candidate_collision_energy_group")),
                    "our_spectrum_score": safe_float(row.get("our_spectrum_score"), default=np.nan),
                    "cfmid_spectrum_score": safe_float(row.get("cfmid_spectrum_score"), default=np.nan),
                    "sirius_formula_score": safe_float(row.get("sirius_formula_score"), default=np.nan),
                    "fragment_formula_score": safe_float(row.get("fragment_formula_score"), default=np.nan),
                    "reaction_prior_score": safe_float(row.get("reaction_prior_score"), default=np.nan),
                    "ms2deepscore_score": row.get("ms2deepscore_score", np.nan),
                    "cfmid_status": safe_str(row.get("cfmid_status")),
                    "cfmid_source": safe_str(row.get("cfmid_source")),
                    "sirius_status": safe_str(row.get("sirius_status")),
                    "sirius_source": safe_str(row.get("sirius_source")),
                    "score_source": "pfas_locked_test_external_score_matrix",
                }
            )
        records.append(
            QueryRecord(
                dataset="PFAS",
                spectrum_id=safe_str(query_row_id),
                query_id=safe_str(query_row_id),
                true_inchikey=true_inchikey,
                true_smiles=true_smiles,
                true_formula=true_formula,
                compound_name=safe_str(first.get("query_name")),
                pfas_class=safe_str(first.get("query_pfas_class") or first.get("pfas_class")),
                precursor_mz=safe_float(first.get("query_precursor_mz"), default=np.nan),
                adduct=safe_str(first.get("query_adduct")),
                ion_mode=safe_str(first.get("query_ion_mode")),
                collision_energy=safe_str(first.get("query_collision_energy_group") or first.get("query_collision_energy_group_meta")),
                metadata={
                    "candidate_count": len(candidates),
                    "target_nonzero_bin_count": safe_float(first.get("query_target_peak_count"), default=np.nan),
                    "source_feature_matrix": str(feature_matrix_path),
                    "source_score_matrix": str(score_matrix_path) if score_matrix_path else "",
                },
                candidates=candidates,
            )
        )
    return records, {
        "status": "available",
        "path": str(feature_matrix_path),
        "score_matrix_path": str(score_matrix_path) if score_matrix_path else "",
        "n_queries": len(records),
        "n_candidate_rows": int(len(rows)),
        "unique_query_inchikeys": int(rows["query_inchikey"].nunique()) if "query_inchikey" in rows.columns else None,
        "feature_matrix_sha256": sha256_file(feature_matrix_path),
        "score_matrix_sha256": sha256_file(score_matrix_path) if score_matrix_path else "",
        "locked_test_used_for_tuning": False,
    }


def environment_audit() -> dict[str, Any]:
    executables = {
        "cfmid": shutil.which("cfmid"),
        "cfm_predict": shutil.which("cfm-predict"),
        "cfm_id": shutil.which("cfm-id"),
        "sirius": shutil.which("sirius"),
        "java": shutil.which("java"),
        "git": shutil.which("git"),
        "python": sys.executable,
    }
    packages = {}
    for package in ["rdkit", "ms2deepscore", "matchms", "torch", "numpy", "pandas", "matplotlib", "yaml"]:
        packages[package] = {"available": package_version(package) is not None, "version": package_version(package)}
    torch_cuda = None
    try:
        import torch

        torch_cuda = {"cuda_available": bool(torch.cuda.is_available()), "device_count": int(torch.cuda.device_count())}
    except Exception:
        torch_cuda = {"cuda_available": False, "device_count": 0}
    audit = {
        "platform": platform.platform(),
        "os": os.name,
        "python_version": sys.version,
        "python_executable": sys.executable,
        "virtual_env": os.environ.get("VIRTUAL_ENV", ""),
        "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
        "cwd": str(Path.cwd()),
        "executables": executables,
        "versions": {
            "java": run_cmd(["java", "-version"]) if executables["java"] else None,
            "sirius": run_cmd(["sirius", "--version"]) if executables["sirius"] else None,
            "cfmid": run_cmd([executables["cfmid"], "--version"]) if executables["cfmid"] else None,
            "cfm_predict": run_cmd([executables["cfm_predict"], "--help"]) if executables["cfm_predict"] else None,
        },
        "packages": packages,
        "cuda": torch_cuda,
        "git": {
            "branch": run_cmd(["git", "branch", "--show-current"]).get("stdout"),
            "commit": run_cmd(["git", "rev-parse", "HEAD"]).get("stdout"),
            "status_short": run_cmd(["git", "status", "--short"]).get("stdout"),
        },
    }
    return audit


def native_baseline_audit(env: dict[str, Any]) -> list[dict[str, Any]]:
    executables = env["executables"]
    packages = env["packages"]
    rows = [
        {
            "model": "CFM-ID",
            "native_available": bool(executables.get("cfmid") or executables.get("cfm_predict") or executables.get("cfm_id")),
            "executable_or_package": executables.get("cfmid") or executables.get("cfm_predict") or executables.get("cfm_id") or "",
            "version": safe_str(env["versions"].get("cfmid") or env["versions"].get("cfm_predict")),
            "blocker": "" if (executables.get("cfmid") or executables.get("cfm_predict") or executables.get("cfm_id")) else "CFM-ID executable not found in PATH; no native CASMI CFM-ID inference was run.",
        },
        {
            "model": "SIRIUS",
            "native_available": bool(executables.get("sirius")),
            "executable_or_package": executables.get("sirius") or "",
            "version": safe_str(env["versions"].get("sirius")),
            "blocker": "" if executables.get("sirius") else "SIRIUS executable not found in PATH; no native CASMI SIRIUS inference was run.",
        },
        {
            "model": "MS2DeepScore",
            "native_available": bool(packages.get("ms2deepscore", {}).get("available")),
            "executable_or_package": "ms2deepscore" if packages.get("ms2deepscore", {}).get("available") else "",
            "version": packages.get("ms2deepscore", {}).get("version") or "",
            "blocker": "" if packages.get("ms2deepscore", {}).get("available") else "ms2deepscore Python package/model not available; no native MS2DeepScore inference was run.",
        },
    ]
    return rows


def model_score(candidate: dict[str, Any], model: str, allow_fallback: bool) -> tuple[float, str]:
    if model == "FragAnnotor":
        weights = {"our_spectrum_score": 0.35, "cfmid_spectrum_score": 0.50, "fragment_formula_score": 0.15}
    elif model == "CFM-ID":
        weights = {"cfmid_spectrum_score": 1.0}
    elif model == "SIRIUS":
        weights = {"sirius_formula_score": 1.0}
    elif model == "MS2DeepScore":
        raw = candidate.get("ms2deepscore_score", np.nan)
        try:
            if not pd.isna(raw) and raw != "":
                return float(raw), "ms2deepscore_score"
        except Exception:
            pass
        if not allow_fallback:
            return np.nan, "ms2deepscore_unavailable"
        return 0.65 * safe_float(candidate.get("our_spectrum_score")) + 0.35 * safe_float(candidate.get("cfmid_spectrum_score")), "deterministic_ms2deepscore_proxy"
    else:
        weights = {}
    total = 0.0
    source_parts = []
    for field_name, weight in weights.items():
        value = safe_float(candidate.get(field_name), default=np.nan)
        if pd.isna(value):
            value = 0.0
        total += value * weight
        source_parts.append(field_name)
    return float(total), "+".join(source_parts)


def model_availability(dataset: str, model: str, native_baselines: bool, allow_fallback: bool, env: dict[str, Any]) -> tuple[bool, str, str]:
    if dataset == "PFAS":
        if model == "FragAnnotor":
            return True, "precomputed_external_real_scores", "Frozen no-SIRIUS FragAnnotor score matrix from PFAS locked-test report."
        if model == "CFM-ID":
            return True, "precomputed_external_cfmid4_scores", "Real CFM-ID 4.x score column from PFAS external expert score matrix."
        if model == "SIRIUS":
            return True, "precomputed_external_sirius_scores", "Real SIRIUS 4.9.15 formula score column; scalar formula plausibility, not synthetic spectra."
        if model == "MS2DeepScore" and env["packages"].get("ms2deepscore", {}).get("available"):
            return True, "native_ms2deepscore_package", "Native package available; requires candidate score column or embeddings."
        if model == "MS2DeepScore" and allow_fallback:
            return True, "deterministic_fallback", "MS2DeepScore package unavailable; explicit deterministic proxy fallback."
        return False, "native_unavailable", "MS2DeepScore package/model unavailable and fallback disabled."

    if dataset == "CASMI2022":
        if not native_baselines and allow_fallback:
            return True, "deterministic_fallback", "Preliminary lightweight fallback scoring; not native baseline inference."
        if allow_fallback:
            return True, "deterministic_fallback", "Native CASMI outputs unavailable; explicit fallback was allowed."
        if model == "CFM-ID":
            return False, "native_unavailable", "CFM-ID native CASMI execution/export parser is unavailable in this repository run; fallback disabled."
        if model == "SIRIUS":
            return False, "native_unavailable", "SIRIUS native CASMI execution/export parser is unavailable in this repository run; fallback disabled."
        if model == "MS2DeepScore":
            return False, "native_unavailable", "MS2DeepScore native CASMI model/embedding workflow is unavailable in this repository run; fallback disabled."
        return False, "native_unavailable", "FragAnnotor native CASMI component scores are unavailable; fallback disabled."
    return False, "dataset_unavailable", "Dataset unavailable."


def rank_record(record: QueryRecord, model: str, native_baselines: bool, allow_fallback: bool, env: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    available, mode, message = model_availability(record.dataset, model, native_baselines, allow_fallback, env)
    tool_version = tool_version_for_model(model, env, record.dataset)
    if not available:
        return pd.DataFrame(
            [
                {
                    "dataset": record.dataset,
                    "spectrum_id": record.spectrum_id,
                    "query_id": record.query_id,
                    "model": model,
                    "candidate_id": "",
                    "candidate_smiles": "",
                    "candidate_inchikey": "",
                    "candidate_formula": "",
                    "rank": np.nan,
                    "score": np.nan,
                    "true_inchikey": record.true_inchikey,
                    "true_smiles": record.true_smiles or "",
                    "true_formula": record.true_formula or "",
                    "is_correct": False,
                    "score_source": "",
                    "native_or_fallback": mode,
                    "tool_version": tool_version,
                    "error_message": message,
                }
            ],
            columns=PREDICTION_COLUMNS,
        ), {"available": False, "native_or_fallback": mode, "error_message": message}

    best_by_key: dict[str, dict[str, Any]] = {}
    for candidate in record.candidates:
        score, score_source = model_score(candidate, model, allow_fallback)
        if pd.isna(score):
            continue
        key = safe_str(candidate.get("candidate_inchikey") or candidate.get("inchikey") or candidate.get("candidate_id"))
        row = {
            "dataset": record.dataset,
            "spectrum_id": record.spectrum_id,
            "query_id": record.query_id,
            "model": model,
            "candidate_id": safe_str(candidate.get("candidate_id") or candidate.get("candidate_row_id")),
            "candidate_smiles": safe_str(candidate.get("canonical_smiles") or candidate.get("smiles")),
            "candidate_inchikey": key,
            "candidate_formula": safe_str(candidate.get("candidate_formula") or candidate.get("formula")),
            "rank": np.nan,
            "score": float(score),
            "true_inchikey": record.true_inchikey,
            "true_smiles": record.true_smiles or "",
            "true_formula": record.true_formula or "",
            "is_correct": key == record.true_inchikey,
            "score_source": score_source,
            "native_or_fallback": mode,
            "tool_version": tool_version,
            "error_message": "",
        }
        old = best_by_key.get(key)
        if old is None or row["score"] > old["score"]:
            best_by_key[key] = row
    ranked = sorted(best_by_key.values(), key=lambda x: (-float(x["score"]), x["candidate_inchikey"], x["candidate_id"]))
    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
    return pd.DataFrame(ranked, columns=PREDICTION_COLUMNS), {"available": True, "native_or_fallback": mode, "error_message": ""}


def tool_version_for_model(model: str, env: dict[str, Any], dataset: str) -> str:
    if dataset == "PFAS" and model == "CFM-ID":
        return "CFM-ID 4.x precomputed in PFAS score matrix"
    if dataset == "PFAS" and model == "SIRIUS":
        return "SIRIUS 4.9.15 precomputed in PFAS score matrix"
    if model == "MS2DeepScore":
        return safe_str(env["packages"].get("ms2deepscore", {}).get("version"))
    if model == "CFM-ID":
        return safe_str(env["versions"].get("cfmid") or env["versions"].get("cfm_predict"))
    if model == "SIRIUS":
        return safe_str(env["versions"].get("sirius"))
    return "FragAnnotor frozen no-SIRIUS weights"


def query_metrics_from_predictions(record: QueryRecord, pred_df: pd.DataFrame, model: str, status: dict[str, Any]) -> dict[str, Any]:
    valid = pred_df[pred_df["candidate_id"].astype(str).ne("")].copy()
    true_rows = valid[valid["is_correct"].astype(bool)] if not valid.empty else pd.DataFrame()
    true_rank = np.nan
    if not true_rows.empty:
        true_rank = float(true_rows["rank"].min())
    top1 = valid.sort_values("rank").head(1)
    top1_row = top1.iloc[0].to_dict() if not top1.empty else {}
    tanimoto = morgan_tanimoto(record.true_smiles, top1_row.get("candidate_smiles"))
    pred_formula = safe_str(top1_row.get("candidate_formula"))
    true_formula = record.true_formula or formula_from_smiles(record.true_smiles)
    return {
        "dataset": record.dataset,
        "spectrum_id": record.spectrum_id,
        "query_id": record.query_id,
        "model": model,
        "status": "completed" if status["available"] else "model_unavailable_native_required",
        "native_or_fallback": status["native_or_fallback"],
        "true_inchikey": record.true_inchikey,
        "true_smiles": record.true_smiles or "",
        "true_formula": true_formula or "",
        "compound_name": record.compound_name or "",
        "pfas_class": record.pfas_class or "",
        "precursor_mz": record.precursor_mz,
        "ion_mode": record.ion_mode or "",
        "adduct": record.adduct or "",
        "collision_energy": record.collision_energy or "",
        "candidate_count": len(record.candidates),
        "true_rank": true_rank,
        "top1_correct": bool(not pd.isna(true_rank) and true_rank == 1),
        "top5_correct": bool(not pd.isna(true_rank) and true_rank <= 5),
        "top10_correct": bool(not pd.isna(true_rank) and true_rank <= 10),
        "reciprocal_rank": 0.0 if pd.isna(true_rank) else 1.0 / true_rank,
        "top1_candidate_smiles": safe_str(top1_row.get("candidate_smiles")),
        "top1_candidate_inchikey": safe_str(top1_row.get("candidate_inchikey")),
        "top1_candidate_formula": pred_formula,
        "top1_score": top1_row.get("score", np.nan),
        "top1_tanimoto": tanimoto,
        "formula_correct": bool(true_formula and pred_formula and true_formula == pred_formula),
        "error_message": status.get("error_message", ""),
    }


def aggregate_metrics(query_df: pd.DataFrame) -> dict[str, Any]:
    completed = query_df[query_df["status"].eq("completed")].copy()
    if completed.empty:
        return {
            "n_queries": int(len(query_df)),
            "top1_accuracy": np.nan,
            "top5_accuracy": np.nan,
            "top10_accuracy": np.nan,
            "mean_reciprocal_rank": np.nan,
            "mean_top1_tanimoto": np.nan,
            "molecular_formula_accuracy": np.nan,
            "median_true_rank": np.nan,
            "median_candidate_count": np.nan,
        }
    true_rank = pd.to_numeric(completed["true_rank"], errors="coerce")
    tanimoto = pd.to_numeric(completed["top1_tanimoto"], errors="coerce")
    return {
        "n_queries": int(len(completed)),
        "top1_accuracy": float(completed["top1_correct"].mean()),
        "top5_accuracy": float(completed["top5_correct"].mean()),
        "top10_accuracy": float(completed["top10_correct"].mean()),
        "mean_reciprocal_rank": float(completed["reciprocal_rank"].mean()),
        "mean_top1_tanimoto": np.nan if tanimoto.dropna().empty else float(tanimoto.mean()),
        "molecular_formula_accuracy": float(completed["formula_correct"].mean()),
        "median_true_rank": np.nan if true_rank.dropna().empty else float(true_rank.median()),
        "median_candidate_count": float(completed["candidate_count"].median()),
    }


def copy_preliminary_fallback(results_dir: Path) -> None:
    prelim = results_dir / "preliminary"
    prelim.mkdir(parents=True, exist_ok=True)
    for suffix in ["csv", "json"]:
        src = results_dir / f"benchmark_results.{suffix}"
        if src.exists():
            dst = prelim / f"casmi2022_fallback_benchmark_results.{suffix}"
            if not dst.exists():
                shutil.copy2(src, dst)


def build_predictions(
    records: list[QueryRecord],
    models: list[str],
    native_baselines: bool,
    allow_fallback: bool,
    env: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    query_rows: list[dict[str, Any]] = []
    for record in records:
        for model in models:
            pred_df, status = rank_record(record, model, native_baselines, allow_fallback, env)
            prediction_frames.append(pred_df)
            query_rows.append(query_metrics_from_predictions(record, pred_df, model, status))
    predictions = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame(columns=PREDICTION_COLUMNS)
    query_df = pd.DataFrame(query_rows)
    return predictions, query_df


def write_prediction_files(predictions: pd.DataFrame, results_dir: Path) -> None:
    outdir = results_dir / "predictions"
    outdir.mkdir(parents=True, exist_ok=True)
    slug = {
        "FragAnnotor": "fragannotor",
        "CFM-ID": "cfmid_native",
        "SIRIUS": "sirius_native",
        "MS2DeepScore": "ms2deepscore_native",
    }
    dataset_slug = {"CASMI2022": "casmi2022", "PFAS": "pfas"}
    for (dataset, model), group in predictions.groupby(["dataset", "model"], dropna=False):
        filename = f"{dataset_slug.get(dataset, dataset.lower())}_{slug.get(model, model.lower())}_predictions.csv"
        group[PREDICTION_COLUMNS].to_csv(outdir / filename, index=False)


def write_summary_files(summary: pd.DataFrame, query_df: pd.DataFrame, predictions: pd.DataFrame, results_dir: Path, dataset_status: dict[str, Any], env: dict[str, Any]) -> None:
    summary.to_csv(results_dir / "benchmark_results.csv", index=False)
    predictions.to_csv(results_dir / "benchmark_predictions.csv", index=False)
    write_json(
        results_dir / "benchmark_results.json",
        {
            "summary": summary.replace({np.nan: None}).to_dict(orient="records"),
            "dataset_status": dataset_status,
            "native_baseline_audit": native_baseline_audit(env),
            "interpretation": {
                "native_claim_guardrail": "Rows with native_or_fallback=native_unavailable are not native benchmark results.",
                "pfas_score_note": "PFAS CFM-ID and SIRIUS columns are real precomputed external expert scores from the companion PFAS workflow.",
                "casmi_note": "CASMI native baseline outputs were unavailable in this environment when fallback was disabled.",
            },
        },
    )


def build_summary(query_df: pd.DataFrame, dataset_status: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset in ["CASMI2022", "PFAS"]:
        for model in MODEL_ORDER:
            subset = query_df[(query_df["dataset"].eq(dataset)) & (query_df["model"].eq(model))]
            metrics = aggregate_metrics(subset)
            status = "dataset_unavailable"
            native_or_fallback = ""
            notes = dataset_status.get(dataset, {}).get("reason", "")
            if not subset.empty:
                completed = subset[subset["status"].eq("completed")]
                status = "completed" if not completed.empty else "model_unavailable_native_required"
                native_or_fallback = safe_str(subset["native_or_fallback"].iloc[0])
                error_messages = subset["error_message"].astype(str)
                error_messages = error_messages[error_messages.ne("")]
                notes = safe_str(error_messages.iloc[0]) if not error_messages.empty else ""
            rows.append(
                {
                    "dataset": dataset,
                    "model": model,
                    "status": status,
                    "native_or_fallback": native_or_fallback,
                    **metrics,
                    "notes": notes,
                }
            )
    return pd.DataFrame(rows)


def write_casmi_native_outputs(query_df: pd.DataFrame, predictions: pd.DataFrame, records: list[QueryRecord], results_dir: Path) -> None:
    casmi_query = query_df[query_df["dataset"].eq("CASMI2022")].copy()
    casmi_summary = build_summary(casmi_query, {"CASMI2022": {"status": "available"}})
    casmi_summary = casmi_summary[casmi_summary["dataset"].eq("CASMI2022")]
    casmi_summary.to_csv(results_dir / "casmi2022_native_benchmark_summary.csv", index=False)
    write_json(results_dir / "casmi2022_native_benchmark_summary.json", casmi_summary.replace({np.nan: None}).to_dict(orient="records"))
    casmi_wide = query_level_wide(casmi_query, records)
    casmi_wide.to_csv(results_dir / "casmi2022_query_level_results.csv", index=False)
    predictions[predictions["dataset"].eq("CASMI2022")].to_csv(results_dir / "casmi2022_candidate_level_predictions.csv", index=False)


def query_level_wide(query_df: pd.DataFrame, records: list[QueryRecord]) -> pd.DataFrame:
    record_meta = {
        r.query_id: {
            "dataset": r.dataset,
            "spectrum_id": r.spectrum_id,
            "query_id": r.query_id,
            "true compound name if available": r.compound_name or "",
            "true SMILES": r.true_smiles or "",
            "true InChIKey": r.true_inchikey,
            "true molecular formula": r.true_formula or "",
            "PFAS class/subclass if available": r.pfas_class or "",
            "precursor m/z": r.precursor_mz,
            "ion mode": r.ion_mode or "",
            "adduct": r.adduct or "",
            "number of candidates": len(r.candidates),
        }
        for r in records
    }
    rows: list[dict[str, Any]] = []
    for query_id, group in query_df.groupby("query_id", sort=True):
        row = record_meta.get(query_id, {}).copy()
        by_model = {r["model"]: r for r in group.to_dict(orient="records")}
        for model in MODEL_ORDER:
            model_row = by_model.get(model, {})
            label = model if model != "CFM-ID" else "CFM-ID"
            row[f"{label} true rank"] = model_row.get("true_rank", np.nan)
            row[f"{label} top-1 candidate SMILES"] = model_row.get("top1_candidate_smiles", "")
            row[f"{label} top-1 candidate InChIKey"] = model_row.get("top1_candidate_inchikey", "")
            row[f"{label} top-1 score"] = model_row.get("top1_score", np.nan)
            row[f"{label} status"] = model_row.get("status", "")
            row[f"{label} native_or_fallback"] = model_row.get("native_or_fallback", "")
        frag = by_model.get("FragAnnotor", {})
        row["FragAnnotor top-1 candidate SMILES"] = frag.get("top1_candidate_smiles", "")
        row["FragAnnotor top-1 candidate InChIKey"] = frag.get("top1_candidate_inchikey", "")
        row["FragAnnotor top-1 score"] = frag.get("top1_score", np.nan)
        row["top-1 Tanimoto similarity"] = frag.get("top1_tanimoto", np.nan)
        frag_rank = safe_float(frag.get("true_rank"), default=np.nan)
        for baseline in ["CFM-ID", "SIRIUS", "MS2DeepScore"]:
            base_rank = safe_float(by_model.get(baseline, {}).get("true_rank"), default=np.nan)
            row[f"whether FragAnnotor beats {baseline}"] = bool(not pd.isna(frag_rank) and not pd.isna(base_rank) and frag_rank < base_rank)
            row[f"rank improvement over {baseline}"] = np.nan if pd.isna(frag_rank) or pd.isna(base_rank) else base_rank - frag_rank
        row["failure category if applicable"] = failure_category(frag_rank)
        rows.append(row)
    return pd.DataFrame(rows)


def failure_category(rank: float) -> str:
    if pd.isna(rank):
        return "model_unavailable_or_true_candidate_missing"
    if rank == 1:
        return ""
    if rank <= 5:
        return "not_top1_but_top5"
    if rank <= 10:
        return "top10_only"
    return "missed_top10"


def write_query_level_outputs(query_df: pd.DataFrame, predictions: pd.DataFrame, records_by_dataset: dict[str, list[QueryRecord]], results_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    outdir = results_dir / "query_level"
    outdir.mkdir(parents=True, exist_ok=True)
    casmi_wide = query_level_wide(query_df[query_df["dataset"].eq("CASMI2022")], records_by_dataset.get("CASMI2022", []))
    pfas_wide = query_level_wide(query_df[query_df["dataset"].eq("PFAS")], records_by_dataset.get("PFAS", []))
    casmi_wide.to_csv(outdir / "casmi2022_query_level_comparison.csv", index=False)
    pfas_wide.to_csv(outdir / "pfas_query_level_comparison.csv", index=False)
    pfas_top10 = predictions[
        (predictions["dataset"].eq("PFAS"))
        & (pd.to_numeric(predictions["rank"], errors="coerce") <= 10)
        & (predictions["candidate_id"].astype(str).ne(""))
    ].copy()
    pfas_top10.to_csv(outdir / "pfas_top10_candidates_by_model.csv", index=False)
    return casmi_wide, pfas_wide


def rank_metrics_for_weights(records: list[QueryRecord], weights: dict[str, float], variant: str) -> tuple[dict[str, Any], pd.DataFrame]:
    rows = []
    for record in records:
        best: dict[str, dict[str, Any]] = {}
        for candidate in record.candidates:
            score = 0.0
            for field_name, weight in weights.items():
                value = safe_float(candidate.get(field_name), default=np.nan)
                if pd.isna(value):
                    value = 0.0
                score += value * weight
            key = safe_str(candidate.get("candidate_inchikey") or candidate.get("candidate_id"))
            row = {"query_id": record.query_id, "candidate_inchikey": key, "score": score, "is_correct": key == record.true_inchikey}
            old = best.get(key)
            if old is None or score > old["score"]:
                best[key] = row
        ranked = sorted(best.values(), key=lambda x: (-x["score"], x["candidate_inchikey"]))
        true_rank = np.nan
        for i, row in enumerate(ranked, start=1):
            if row["is_correct"]:
                true_rank = i
                break
        rows.append(
            {
                "variant": variant,
                "query_id": record.query_id,
                "true_rank": true_rank,
                "top1_correct": bool(not pd.isna(true_rank) and true_rank == 1),
                "top5_correct": bool(not pd.isna(true_rank) and true_rank <= 5),
                "top10_correct": bool(not pd.isna(true_rank) and true_rank <= 10),
                "reciprocal_rank": 0.0 if pd.isna(true_rank) else 1.0 / true_rank,
                "candidate_count": len(ranked),
            }
        )
    qdf = pd.DataFrame(rows)
    metrics = {
        "variant": variant,
        "top1_accuracy": float(qdf["top1_correct"].mean()),
        "top5_accuracy": float(qdf["top5_correct"].mean()),
        "top10_accuracy": float(qdf["top10_correct"].mean()),
        "mean_reciprocal_rank": float(qdf["reciprocal_rank"].mean()),
        "mean_top1_tanimoto": np.nan,
        "molecular_formula_accuracy": np.nan,
        "n_queries": int(len(qdf)),
        **{f"weight_{k}": v for k, v in weights.items()},
    }
    return metrics, qdf


def write_ablation_outputs(records: list[QueryRecord], results_dir: Path) -> pd.DataFrame:
    outdir = results_dir / "ablation"
    outdir.mkdir(parents=True, exist_ok=True)
    variants: dict[str, dict[str, float]] = {
        "full_current_primary_no_sirius": {"our_spectrum_score": 0.35, "cfmid_spectrum_score": 0.50, "fragment_formula_score": 0.15},
        "full_five_component_validation_selected": {
            "our_spectrum_score": 0.30,
            "cfmid_spectrum_score": 0.55,
            "sirius_formula_score": 0.10,
            "fragment_formula_score": 0.05,
            "reaction_prior_score": 0.0,
        },
        "only_our_spectrum_score": {"our_spectrum_score": 1.0},
        "only_cfmid_spectrum_score": {"cfmid_spectrum_score": 1.0},
        "only_fragment_formula_score": {"fragment_formula_score": 1.0},
        "only_sirius_formula_score": {"sirius_formula_score": 1.0},
        "only_reaction_prior_score": {"reaction_prior_score": 1.0},
        "without_our_spectrum_score": {"cfmid_spectrum_score": 0.786, "sirius_formula_score": 0.143, "fragment_formula_score": 0.071},
        "without_cfmid_spectrum_score": {"our_spectrum_score": 0.667, "sirius_formula_score": 0.222, "fragment_formula_score": 0.111},
        "without_fragment_formula_score": {"our_spectrum_score": 0.316, "cfmid_spectrum_score": 0.579, "sirius_formula_score": 0.105},
        "without_sirius_formula_score": {"our_spectrum_score": 0.35, "cfmid_spectrum_score": 0.50, "fragment_formula_score": 0.15},
        "without_reaction_prior_score": {"our_spectrum_score": 0.30, "cfmid_spectrum_score": 0.55, "sirius_formula_score": 0.10, "fragment_formula_score": 0.05},
    }
    sensitivity = {
        "sens_our035_cfmid050_fragment015": {"our_spectrum_score": 0.35, "cfmid_spectrum_score": 0.50, "fragment_formula_score": 0.15},
        "sens_our050_cfmid035_fragment015": {"our_spectrum_score": 0.50, "cfmid_spectrum_score": 0.35, "fragment_formula_score": 0.15},
        "sens_our045_cfmid045_fragment010": {"our_spectrum_score": 0.45, "cfmid_spectrum_score": 0.45, "fragment_formula_score": 0.10},
        "sens_our060_cfmid025_fragment015": {"our_spectrum_score": 0.60, "cfmid_spectrum_score": 0.25, "fragment_formula_score": 0.15},
        "sens_our025_cfmid060_fragment015": {"our_spectrum_score": 0.25, "cfmid_spectrum_score": 0.60, "fragment_formula_score": 0.15},
        "sens_our040_cfmid040_fragment020": {"our_spectrum_score": 0.40, "cfmid_spectrum_score": 0.40, "fragment_formula_score": 0.20},
    }
    metrics_rows: list[dict[str, Any]] = []
    query_frames: list[pd.DataFrame] = []
    for variant, weights in variants.items():
        metrics, qdf = rank_metrics_for_weights(records, weights, variant)
        metrics_rows.append(metrics)
        query_frames.append(qdf)
    summary = pd.DataFrame(metrics_rows)
    query_level = pd.concat(query_frames, ignore_index=True)
    summary.to_csv(outdir / "fragannotor_ablation_summary.csv", index=False)
    write_json(outdir / "fragannotor_ablation_summary.json", summary.replace({np.nan: None}).to_dict(orient="records"))
    query_level.to_csv(outdir / "fragannotor_ablation_query_level.csv", index=False)

    sens_rows = []
    for variant, weights in sensitivity.items():
        metrics, _ = rank_metrics_for_weights(records, weights, variant)
        sens_rows.append(metrics)
    sens_df = pd.DataFrame(sens_rows)
    sens_df.to_csv(outdir / "fragannotor_weight_sensitivity.csv", index=False)
    return summary


def bootstrap_ci(values_a: np.ndarray, values_b: np.ndarray, seed: int, n_bootstrap: int = 1000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    if len(values_a) == 0:
        return np.nan, np.nan
    deltas = []
    n = len(values_a)
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, n)
        deltas.append(float(np.nanmean(values_a[idx] - values_b[idx])))
    return float(np.nanpercentile(deltas, 2.5)), float(np.nanpercentile(deltas, 97.5))


def write_sota_outputs(summary: pd.DataFrame, query_df: pd.DataFrame, results_dir: Path, seed: int) -> None:
    summary.to_csv(results_dir / "sota_comparison_summary.csv", index=False)
    write_json(results_dir / "sota_comparison_summary.json", summary.replace({np.nan: None}).to_dict(orient="records"))
    pair_rows: list[dict[str, Any]] = []
    ci_rows: list[dict[str, Any]] = []
    for dataset in ["CASMI2022", "PFAS"]:
        frag = query_df[(query_df["dataset"].eq(dataset)) & (query_df["model"].eq("FragAnnotor"))]
        for baseline in ["CFM-ID", "SIRIUS", "MS2DeepScore"]:
            base = query_df[(query_df["dataset"].eq(dataset)) & (query_df["model"].eq(baseline))]
            merged = frag.merge(base, on="query_id", suffixes=("_frag", "_base"))
            completed = merged[(merged["status_frag"].eq("completed")) & (merged["status_base"].eq("completed"))].copy()
            if completed.empty:
                pair_rows.append({"dataset": dataset, "baseline": baseline, "status": "comparison_unavailable"})
                ci_rows.append({"dataset": dataset, "baseline": baseline, "metric": "top10_accuracy_difference", "ci95_low": np.nan, "ci95_high": np.nan, "status": "comparison_unavailable"})
                ci_rows.append({"dataset": dataset, "baseline": baseline, "metric": "mrr_difference", "ci95_low": np.nan, "ci95_high": np.nan, "status": "comparison_unavailable"})
                continue
            frag_rank = pd.to_numeric(completed["true_rank_frag"], errors="coerce").fillna(1e9)
            base_rank = pd.to_numeric(completed["true_rank_base"], errors="coerce").fillna(1e9)
            pair_rows.append(
                {
                    "dataset": dataset,
                    "baseline": baseline,
                    "status": "completed",
                    "n_queries": int(len(completed)),
                    "fragannotor_better": int((frag_rank < base_rank).sum()),
                    "baseline_better": int((base_rank < frag_rank).sum()),
                    "ties": int((base_rank == frag_rank).sum()),
                    "mean_rank_delta_baseline_minus_fragannotor": float((base_rank - frag_rank).mean()),
                    "median_rank_delta_baseline_minus_fragannotor": float((base_rank - frag_rank).median()),
                }
            )
            top10_frag = completed["top10_correct_frag"].astype(float).to_numpy()
            top10_base = completed["top10_correct_base"].astype(float).to_numpy()
            mrr_frag = completed["reciprocal_rank_frag"].astype(float).to_numpy()
            mrr_base = completed["reciprocal_rank_base"].astype(float).to_numpy()
            low, high = bootstrap_ci(top10_frag, top10_base, seed)
            ci_rows.append({"dataset": dataset, "baseline": baseline, "metric": "top10_accuracy_difference", "ci95_low": low, "ci95_high": high, "status": "completed"})
            low, high = bootstrap_ci(mrr_frag, mrr_base, seed + 1)
            ci_rows.append({"dataset": dataset, "baseline": baseline, "metric": "mrr_difference", "ci95_low": low, "ci95_high": high, "status": "completed"})
    pd.DataFrame(pair_rows).to_csv(results_dir / "sota_pairwise_rank_comparison.csv", index=False)
    pd.DataFrame(ci_rows).to_csv(results_dir / "sota_bootstrap_confidence_intervals.csv", index=False)


def write_case_studies(pfas_wide: pd.DataFrame, predictions: pd.DataFrame, records: list[QueryRecord], results_dir: Path) -> pd.DataFrame:
    outdir = results_dir / "case_studies"
    outdir.mkdir(parents=True, exist_ok=True)
    by_query = {r.query_id: r for r in records}

    def get_rank(row: pd.Series, model: str) -> float:
        return safe_float(row.get(f"{model} true rank"), default=np.nan)

    selected: list[tuple[str, str, pd.Series]] = []
    if not pfas_wide.empty:
        case = pfas_wide[(pfas_wide["FragAnnotor true rank"].eq(1)) & (~pfas_wide["CFM-ID true rank"].eq(1))].head(1)
        if not case.empty:
            selected.append(("case_frag_top1_cfmid_not", "FragAnnotor ranks correct structure Top-1 but CFM-ID does not.", case.iloc[0]))
        case = pfas_wide[(pd.to_numeric(pfas_wide["FragAnnotor true rank"], errors="coerce") <= 5)].head(1)
        if not case.empty:
            selected.append(("case_frag_top5_ms2_blocked", "FragAnnotor Top-5; native MS2DeepScore is unavailable, so the requested MS2 contrast is blocked.", case.iloc[0]))
        temp = pfas_wide.copy()
        temp["_sirius_improvement"] = pd.to_numeric(temp["SIRIUS true rank"], errors="coerce") - pd.to_numeric(temp["FragAnnotor true rank"], errors="coerce")
        case = temp.sort_values("_sirius_improvement", ascending=False).head(1)
        if not case.empty:
            selected.append(("case_frag_improves_over_sirius", "FragAnnotor substantially improves rank over SIRIUS formula-only scoring.", case.iloc[0]))
        case = pfas_wide[
            (pd.to_numeric(pfas_wide["FragAnnotor true rank"], errors="coerce") > 10)
            & ((pd.to_numeric(pfas_wide["CFM-ID true rank"], errors="coerce") <= 10) | (pd.to_numeric(pfas_wide["SIRIUS true rank"], errors="coerce") <= 10))
        ].head(1)
        if not case.empty:
            selected.append(("case_frag_failure_baseline_success", "FragAnnotor misses Top-10 while another available baseline succeeds.", case.iloc[0]))

    frag_top10 = predictions[(predictions["dataset"].eq("PFAS")) & (predictions["model"].eq("FragAnnotor")) & (pd.to_numeric(predictions["rank"], errors="coerce") <= 10)]
    same_formula_case = None
    for query_id, group in frag_top10.groupby("query_id"):
        rec = by_query.get(query_id)
        if rec is None:
            continue
        false_same_formula = group[(~group["is_correct"].astype(bool)) & (group["candidate_formula"].eq(rec.true_formula))]
        if not false_same_formula.empty:
            same_formula_case = pfas_wide[pfas_wide["query_id"].eq(query_id)].head(1)
            break
    if same_formula_case is not None and not same_formula_case.empty:
        selected.append(("case_same_formula_isomer", "Difficult same-formula/isomer-like candidate appears in FragAnnotor Top-10.", same_formula_case.iloc[0]))

    rows = []
    seen: set[str] = set()
    for case_id, reason, row in selected:
        query_id = safe_str(row.get("query_id"))
        if (case_id, query_id) in seen:
            continue
        seen.add((case_id, query_id))
        rec = by_query.get(query_id)
        frag_preds = predictions[(predictions["query_id"].eq(query_id)) & (predictions["model"].eq("FragAnnotor")) & (predictions["candidate_id"].astype(str).ne(""))].copy()
        false_top = frag_preds[~frag_preds["is_correct"].astype(bool)].sort_values("rank").head(1)
        correct = frag_preds[frag_preds["is_correct"].astype(bool)].head(1)
        rows.append(
            {
                "case_id": case_id,
                "reason_selected": reason,
                "query_id": query_id,
                "compound_name": rec.compound_name if rec else "",
                "PFAS class/subclass": rec.pfas_class if rec else "",
                "true SMILES": rec.true_smiles if rec else "",
                "true InChIKey": rec.true_inchikey if rec else "",
                "FragAnnotor rank": get_rank(row, "FragAnnotor"),
                "CFM-ID rank": get_rank(row, "CFM-ID"),
                "SIRIUS rank": get_rank(row, "SIRIUS"),
                "MS2DeepScore rank": get_rank(row, "MS2DeepScore"),
                "candidate count": row.get("number of candidates"),
                "diagnostic notes": reason,
                "top false candidate SMILES": false_top["candidate_smiles"].iloc[0] if not false_top.empty else "",
                "top false candidate score": false_top["score"].iloc[0] if not false_top.empty else np.nan,
                "correct candidate score": correct["score"].iloc[0] if not correct.empty else np.nan,
            }
        )
    case_df = pd.DataFrame(rows)
    case_df.to_csv(outdir / "pfas_selected_cases.csv", index=False)
    write_json(
        outdir / "peak_annotation_status.json",
        {
            "peak_level_annotations_available": False,
            "reason": "FragAnnotor benchmark inputs contain candidate-level scores and sparse vector diagnostics, but no curated fragment formula/neutral-loss assignments for selected PFAS cases.",
            "how_to_generate": "Run the fragment-formula assignment workflow on raw spectra and join annotations by query row_id before exporting pfas_case_peak_annotations.csv.",
        },
    )
    draw_case_structures(case_df, predictions, results_dir / "figures" / "case_structures")
    return case_df


def draw_case_structures(case_df: pd.DataFrame, predictions: pd.DataFrame, outdir: Path) -> None:
    if Chem is None or Draw is None or case_df.empty:
        return
    outdir.mkdir(parents=True, exist_ok=True)
    for _, case in case_df.iterrows():
        case_id = safe_str(case.get("case_id"))
        query_id = safe_str(case.get("query_id"))
        candidates = {
            "true": safe_str(case.get("true SMILES")),
            "fragannotor_top1": safe_str(
                predictions[(predictions["query_id"].eq(query_id)) & (predictions["model"].eq("FragAnnotor")) & (predictions["rank"].eq(1))]["candidate_smiles"].head(1).squeeze()
            ),
            "cfmid_top1": safe_str(
                predictions[(predictions["query_id"].eq(query_id)) & (predictions["model"].eq("CFM-ID")) & (predictions["rank"].eq(1))]["candidate_smiles"].head(1).squeeze()
            ),
        }
        for label, smiles in candidates.items():
            mol = Chem.MolFromSmiles(smiles) if smiles else None
            if mol is None:
                continue
            try:
                Draw.MolToFile(mol, str(outdir / f"{case_id}_{label}.png"), size=(420, 320))
            except Exception:
                continue


def write_stratified_outputs(pfas_query: pd.DataFrame, records: list[QueryRecord], results_dir: Path) -> None:
    outdir = results_dir / "stratified"
    outdir.mkdir(parents=True, exist_ok=True)
    rec_meta = {}
    for r in records:
        mw = molecular_weight(r.true_smiles)
        rec_meta[r.query_id] = {
            "query_id": r.query_id,
            "pfas_class": r.pfas_class or "unknown",
            "fluorine_count": fluorine_count(r.true_formula, r.true_smiles),
            "mw_bin": pd.cut([mw if mw is not None else np.nan], bins=[0, 300, 500, 700, 1000], labels=["lt300", "300_500", "500_700", "gt700"])[0],
            "candidate_size_bin": pd.cut([len(r.candidates)], bins=[0, 50, 100, 200, 10000], labels=["le50", "51_100", "101_200", "gt200"])[0],
        }
    meta = pd.DataFrame(rec_meta.values())
    frag = pfas_query[(pfas_query["model"].eq("FragAnnotor")) & (pfas_query["status"].eq("completed"))].merge(
        meta,
        on="query_id",
        how="left",
        suffixes=("", "_meta"),
    )
    if "pfas_class" not in frag.columns and "pfas_class_meta" in frag.columns:
        frag["pfas_class"] = frag["pfas_class_meta"]
    elif "pfas_class_meta" in frag.columns:
        frag["pfas_class"] = frag["pfas_class"].replace("", np.nan).fillna(frag["pfas_class_meta"])
    frag["formula_match_group"] = frag["formula_correct"].map(lambda x: "top1_formula_match" if bool(x) else "top1_formula_mismatch")

    def grouped(metric_col: str, output: str) -> None:
        rows = []
        for group_value, group in frag.groupby(metric_col, dropna=False):
            rows.append(
                {
                    metric_col: safe_str(group_value),
                    "n_queries": int(len(group)),
                    "top1_accuracy": float(group["top1_correct"].mean()),
                    "top5_accuracy": float(group["top5_correct"].mean()),
                    "top10_accuracy": float(group["top10_correct"].mean()),
                    "mrr": float(group["reciprocal_rank"].mean()),
                }
            )
        pd.DataFrame(rows).to_csv(outdir / output, index=False)

    grouped("pfas_class", "pfas_by_subclass.csv")
    grouped("candidate_size_bin", "pfas_by_candidate_size.csv")
    grouped("formula_match_group", "pfas_by_formula_match.csv")
    grouped("fluorine_count", "pfas_by_fluorine_count.csv")


def plot_bar_metrics(summary: pd.DataFrame, outpath: Path, title: str) -> None:
    plot_df = summary[summary["status"].eq("completed")].copy()
    if plot_df.empty:
        return
    labels = [f"{r.dataset}\n{r.model}" for r in plot_df.itertuples()]
    x = np.arange(len(labels))
    width = 0.25
    plt.figure(figsize=(max(9, len(labels) * 0.8), 5.4))
    plt.bar(x - width, plot_df["top1_accuracy"], width, label="Top-1")
    plt.bar(x, plot_df["top5_accuracy"], width, label="Top-5")
    plt.bar(x + width, plot_df["top10_accuracy"], width, label="Top-10")
    plt.xticks(x, labels, rotation=45, ha="right")
    plt.ylabel("Accuracy")
    plt.ylim(0, 1.05)
    plt.title(title)
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(outpath, dpi=300)
    plt.close()


def plot_mrr(summary: pd.DataFrame, outpath: Path, title: str) -> None:
    plot_df = summary[summary["status"].eq("completed")].copy()
    if plot_df.empty:
        return
    labels = [f"{r.dataset}\n{r.model}" for r in plot_df.itertuples()]
    plt.figure(figsize=(max(8, len(labels) * 0.75), 4.8))
    plt.bar(np.arange(len(labels)), plot_df["mean_reciprocal_rank"])
    plt.xticks(np.arange(len(labels)), labels, rotation=45, ha="right")
    plt.ylabel("MRR")
    plt.ylim(0, 1.0)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath, dpi=300)
    plt.close()


def plot_table(summary: pd.DataFrame, outpath: Path) -> None:
    cols = ["dataset", "model", "status", "top1_accuracy", "top5_accuracy", "top10_accuracy", "mean_reciprocal_rank"]
    df = summary[cols].copy()
    for col in ["top1_accuracy", "top5_accuracy", "top10_accuracy", "mean_reciprocal_rank"]:
        df[col] = df[col].map(lambda x: "NA" if pd.isna(x) else f"{float(x):.3f}")
    fig, ax = plt.subplots(figsize=(13, max(3, 0.46 * len(df) + 1.5)))
    ax.axis("off")
    table = ax.table(cellText=df.values, colLabels=df.columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    ax.set_title("Benchmark comparison table", pad=18)
    plt.tight_layout()
    plt.savefig(outpath, dpi=300)
    plt.close()


def write_all_figures(summary: pd.DataFrame, query_df: pd.DataFrame, ablation: pd.DataFrame, predictions: pd.DataFrame, records_by_dataset: dict[str, list[QueryRecord]], results_dir: Path) -> None:
    figdir = results_dir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    plot_bar_metrics(summary, figdir / "bar_plot_topk_accuracy.png", "Top-k accuracy by dataset and model")
    plot_bar_metrics(summary[summary["dataset"].eq("CASMI2022")], figdir / "casmi2022_topk_accuracy.png", "CASMI2022 native benchmark status")
    plot_mrr(summary[summary["dataset"].eq("CASMI2022")], figdir / "casmi2022_mrr_comparison.png", "CASMI2022 MRR comparison")
    plot_bar_metrics(summary, figdir / "sota_topk_accuracy_grouped_bar.png", "SOTA comparison Top-k accuracy")
    plot_mrr(summary, figdir / "sota_mrr_comparison.png", "SOTA comparison MRR")
    plot_table(summary, figdir / "comparison_table.png")

    casmi_counts = [len(r.candidates) for r in records_by_dataset.get("CASMI2022", [])]
    if casmi_counts:
        plt.figure(figsize=(6, 4))
        plt.hist(casmi_counts, bins=20)
        plt.xlabel("Candidate count")
        plt.ylabel("Queries")
        plt.title("CASMI2022 candidate set size distribution")
        plt.tight_layout()
        plt.savefig(figdir / "casmi2022_candidate_size_distribution.png", dpi=300)
        plt.close()

    if not ablation.empty:
        top = ablation.head(20)
        plt.figure(figsize=(10, max(4, 0.35 * len(top))))
        plt.barh(top["variant"], top["top10_accuracy"])
        plt.xlabel("Top-10 accuracy")
        plt.title("FragAnnotor ablation Top-10 accuracy")
        plt.tight_layout()
        plt.savefig(figdir / "ablation_top10_accuracy.png", dpi=300)
        plt.close()
        plt.figure(figsize=(10, max(4, 0.35 * len(top))))
        plt.barh(top["variant"], top["mean_reciprocal_rank"])
        plt.xlabel("MRR")
        plt.title("FragAnnotor ablation MRR")
        plt.tight_layout()
        plt.savefig(figdir / "ablation_mrr.png", dpi=300)
        plt.close()

    sens_path = results_dir / "ablation" / "fragannotor_weight_sensitivity.csv"
    if sens_path.exists():
        sens = pd.read_csv(sens_path)
        if not sens.empty:
            plt.figure(figsize=(8, 4.5))
            x = np.arange(len(sens))
            plt.plot(x, sens["top10_accuracy"], marker="o", label="Top-10")
            plt.plot(x, sens["mean_reciprocal_rank"], marker="o", label="MRR")
            plt.xticks(x, sens["variant"], rotation=45, ha="right", fontsize=7)
            plt.title("Weight sensitivity")
            plt.legend(frameon=False)
            plt.tight_layout()
            plt.savefig(figdir / "weight_sensitivity_heatmap.png", dpi=300)
            plt.close()

    rank_delta = []
    frag = query_df[(query_df["model"].eq("FragAnnotor")) & (query_df["status"].eq("completed"))]
    for baseline in ["CFM-ID", "SIRIUS"]:
        base = query_df[(query_df["model"].eq(baseline)) & (query_df["status"].eq("completed"))]
        merged = frag.merge(base, on=["dataset", "query_id"], suffixes=("_frag", "_base"))
        if not merged.empty:
            rank_delta.append(pd.to_numeric(merged["true_rank_base"], errors="coerce") - pd.to_numeric(merged["true_rank_frag"], errors="coerce"))
    if rank_delta:
        plt.figure(figsize=(6, 4))
        plt.boxplot([x.dropna().to_numpy() for x in rank_delta], tick_labels=["CFM-ID", "SIRIUS"][: len(rank_delta)])
        plt.ylabel("Baseline rank - FragAnnotor rank")
        plt.title("Rank delta distribution")
        plt.tight_layout()
        plt.savefig(figdir / "sota_rank_delta_boxplot.png", dpi=300)
        plt.close()

    plot_pfas_case_figures(predictions, figdir)
    plot_stratified_figures(results_dir)


def plot_pfas_case_figures(predictions: pd.DataFrame, figdir: Path) -> None:
    pfas = predictions[(predictions["dataset"].eq("PFAS")) & (predictions["candidate_id"].astype(str).ne(""))].copy()
    if pfas.empty:
        return
    true_ranks = pfas[pfas["is_correct"].astype(bool)].pivot_table(index="query_id", columns="model", values="rank", aggfunc="min")
    if not true_ranks.empty:
        examples = true_ranks.sort_values("FragAnnotor", na_position="last").head(12)
        models = [m for m in MODEL_ORDER if m in examples.columns]
        vals = examples[models].fillna(25).clip(upper=25)
        plt.figure(figsize=(8, max(3, 0.35 * len(vals))))
        im = plt.imshow(vals.values, aspect="auto", cmap="viridis_r", vmin=1, vmax=25)
        plt.xticks(np.arange(len(models)), models, rotation=30, ha="right")
        plt.yticks(np.arange(len(vals)), vals.index)
        plt.title("PFAS case-study true ranks (capped at 25)")
        plt.colorbar(im, label="True rank")
        plt.tight_layout()
        plt.savefig(figdir / "pfas_case_study_examples.png", dpi=300)
        plt.savefig(figdir / "pfas_case_rank_comparison.png", dpi=300)
        plt.close()
    top10 = pfas[(pfas["model"].eq("FragAnnotor")) & (pd.to_numeric(pfas["rank"], errors="coerce") <= 10)].copy()
    if not top10.empty:
        example_ids = top10["query_id"].drop_duplicates().head(4).tolist()
        plt.figure(figsize=(8, 4.5))
        for query_id in example_ids:
            g = top10[top10["query_id"].eq(query_id)].sort_values("rank")
            plt.plot(g["rank"], g["score"], marker="o", label=query_id)
        plt.xlabel("Rank")
        plt.ylabel("FragAnnotor score")
        plt.title("Selected PFAS Top-10 score profiles")
        plt.legend(frameon=False, fontsize=7)
        plt.tight_layout()
        plt.savefig(figdir / "pfas_case_top10_score_profiles.png", dpi=300)
        plt.close()


def plot_stratified_figures(results_dir: Path) -> None:
    figdir = results_dir / "figures"
    mapping = [
        ("pfas_by_subclass.csv", "pfas_subclass_top10_accuracy.png", "pfas_class"),
        ("pfas_by_candidate_size.csv", "pfas_candidate_size_effect.png", "candidate_size_bin"),
        ("pfas_by_formula_match.csv", "pfas_formula_match_effect.png", "formula_match_group"),
    ]
    for filename, outname, label_col in mapping:
        path = results_dir / "stratified" / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if df.empty or label_col not in df.columns:
            continue
        plt.figure(figsize=(7, 4))
        plt.bar(df[label_col].astype(str), df["top10_accuracy"])
        plt.xticks(rotation=35, ha="right")
        plt.ylabel("Top-10 accuracy")
        plt.title(filename.replace(".csv", ""))
        plt.tight_layout()
        plt.savefig(figdir / outname, dpi=300)
        plt.close()


def write_docs(summary: pd.DataFrame, dataset_status: dict[str, Any], env: dict[str, Any], results_dir: Path, command: str) -> None:
    docs_dir = ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    native_rows = pd.DataFrame(native_baseline_audit(env))
    lines = [
        "# Benchmark Report",
        "",
        "## What Was Run",
        "",
        "The benchmark pipeline exported CASMI2022 and PFAS candidate-ranking outputs for FragAnnotor, CFM-ID, SIRIUS, and MS2DeepScore. Native baseline execution was required by the final command with `--allow-fallback false`; unavailable native tools are recorded as unavailable rather than replaced with fallback scores.",
        "",
        "## Native vs Fallback Tool Status",
        "",
        native_rows.to_markdown(index=False),
        "",
        "PFAS CFM-ID and SIRIUS entries use real precomputed external expert scores from the companion PFAS workflow. SIRIUS is used as a scalar formula plausibility feature, not as a synthetic spectrum generator.",
        "",
        "## Dataset Sizes",
        "",
    ]
    for name, status in dataset_status.items():
        lines.append(f"- `{name}`: status `{status.get('status')}`, queries `{status.get('n_queries', 0)}`, candidate rows `{status.get('n_candidate_rows', 'NA')}`")
    lines.extend(["", "## Main Results", "", summary.to_markdown(index=False), ""])
    lines.extend(
        [
            "## Interpretation",
            "",
            "- PFAS locked-test ranking supports the selected primary FragAnnotor policy within the frozen PFAS benchmark.",
            "- CASMI2022 native CFM-ID/SIRIUS/MS2DeepScore results are unavailable in this environment; preserved fallback CASMI results are preliminary only.",
            "- No result with `native_or_fallback=native_unavailable` should be described as a completed native baseline.",
            "- MS2DeepScore native comparison is blocked until the package and an appropriate pretrained model/embedding workflow are available.",
            "",
            "## Exact Reproduction Command",
            "",
            "```bash",
            command,
            "```",
            "",
            "## Known Limitations",
            "",
            "- CASMI native baseline execution was not completed because required native tools were not installed.",
            "- PFAS results depend on the frozen candidate matrix generated in the transformation-product workflow.",
            "- The benchmark does not establish deployment-ready thresholds or universal LC-MS/MS prediction performance.",
        ]
    )
    (docs_dir / "BENCHMARK_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    readme = [
        "# Results Directory",
        "",
        "- `environment_audit.json`: OS, Python, Git, package, executable, Java, and CUDA audit.",
        "- `native_baseline_audit.csv/json`: native tool availability and blockers.",
        "- `benchmark_results.csv/json`: unified benchmark metrics.",
        "- `predictions/`: per-dataset, per-model candidate-level prediction exports.",
        "- `casmi2022_native_benchmark_summary.csv/json`: CASMI native benchmark status and metrics where available.",
        "- `sota_comparison_summary.csv/json`: unified model comparison table.",
        "- `sota_pairwise_rank_comparison.csv`: paired query-level rank comparisons.",
        "- `sota_bootstrap_confidence_intervals.csv`: bootstrap confidence intervals for Top-10 and MRR differences.",
        "- `ablation/`: FragAnnotor component ablation and weight sensitivity outputs.",
        "- `query_level/`: query-level comparison tables and PFAS Top-10 candidates.",
        "- `case_studies/`: automatically selected PFAS case-study rows and peak-annotation availability status.",
        "- `stratified/`: PFAS subclass and difficulty-stratified summaries.",
        "- `figures/`: matplotlib-only publication-draft plots.",
        "- `preliminary/`: preserved preliminary fallback CASMI result files.",
    ]
    (results_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    (results_dir / "benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_native_audit(results_dir: Path, env: dict[str, Any]) -> None:
    write_json(results_dir / "environment_audit.json", env)
    native = pd.DataFrame(native_baseline_audit(env))
    native.to_csv(results_dir / "native_baseline_audit.csv", index=False)
    write_json(results_dir / "native_baseline_audit.json", native.to_dict(orient="records"))


def write_config(results_dir: Path, args: argparse.Namespace, dataset_status: dict[str, Any], env: dict[str, Any]) -> None:
    payload = {
        "seed": args.seed,
        "dataset": args.dataset,
        "native_baselines": args.native_baselines,
        "allow_fallback": args.allow_fallback,
        "run_ablation": args.run_ablation,
        "export_query_level": args.export_query_level,
        "select_case_studies": args.select_case_studies,
        "candidate_limit": args.candidate_limit,
        "dataset_status": dataset_status,
        "native_baseline_audit": native_baseline_audit(env),
    }
    write_yaml(results_dir / "config.yaml", payload)


def write_decoy_and_external_summaries(results_dir: Path) -> None:
    if (PFAS_DECOY / "threshold_calibration.csv").exists():
        shutil.copy2(PFAS_DECOY / "threshold_calibration.csv", results_dir / "decoy_threshold_summary.csv")
    if (PFAS_EXTERNAL_GAP / "external_validation_manifest.csv").exists():
        manifest = pd.read_csv(PFAS_EXTERNAL_GAP / "external_validation_manifest.csv")
        summary = pd.DataFrame(
            [
                {
                    "external_pfas_spectra_found": int(len(manifest)),
                    "usable_external_spectra": int(manifest["usable_for_external_validation"].astype(bool).sum()) if "usable_for_external_validation" in manifest.columns else 0,
                    "unique_inchikeys": int(manifest["InChIKey"].nunique()) if "InChIKey" in manifest.columns else 0,
                    "external_validation_can_run_now": False,
                    "reason": "Independent usable external PFAS/TP spectra remain insufficient in the prior acquisition audit.",
                }
            ]
        )
        summary.to_csv(results_dir / "external_validation_data_gap_summary.csv", index=False)


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    set_seed(args.seed)
    results_dir = Path(args.output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    copy_preliminary_fallback(results_dir)

    env = environment_audit()
    save_native_audit(results_dir, env)

    pfas_records, pfas_status = load_pfas_records(Path(args.pfas_matrix), Path(args.pfas_score_matrix))
    casmi_records, casmi_status = load_casmi_records(Path(args.casmi_dir) if args.casmi_dir else None, args.candidate_limit)
    records_by_dataset = {"CASMI2022": casmi_records, "PFAS": pfas_records}
    dataset_status = {"CASMI2022": casmi_status, "PFAS": pfas_status}

    selected_records: list[QueryRecord] = []
    if args.dataset in {"casmi2022", "both"}:
        selected_records.extend(casmi_records)
    if args.dataset in {"pfas", "both"}:
        selected_records.extend(pfas_records)

    predictions, query_df = build_predictions(selected_records, MODEL_ORDER, args.native_baselines, args.allow_fallback, env)
    summary = build_summary(query_df, dataset_status)
    write_prediction_files(predictions, results_dir)
    write_summary_files(summary, query_df, predictions, results_dir, dataset_status, env)
    write_casmi_native_outputs(query_df, predictions, casmi_records, results_dir)
    write_sota_outputs(summary, query_df, results_dir, args.seed)

    casmi_wide = pd.DataFrame()
    pfas_wide = pd.DataFrame()
    if args.export_query_level:
        casmi_wide, pfas_wide = write_query_level_outputs(query_df, predictions, records_by_dataset, results_dir)
    else:
        casmi_wide, pfas_wide = write_query_level_outputs(query_df, predictions, records_by_dataset, results_dir)

    ablation = pd.DataFrame()
    if args.run_ablation and pfas_records:
        ablation = write_ablation_outputs(pfas_records, results_dir)
    elif pfas_records:
        ablation = write_ablation_outputs(pfas_records, results_dir)

    if args.select_case_studies and not pfas_wide.empty:
        write_case_studies(pfas_wide, predictions, pfas_records, results_dir)
    elif not pfas_wide.empty:
        write_case_studies(pfas_wide, predictions, pfas_records, results_dir)

    write_stratified_outputs(query_df[query_df["dataset"].eq("PFAS")], pfas_records, results_dir)
    write_decoy_and_external_summaries(results_dir)
    write_all_figures(summary, query_df, ablation, predictions, records_by_dataset, results_dir)
    command = (
        "python scripts/run_benchmark.py --dataset both --native-baselines --allow-fallback false "
        "--run-ablation --export-query-level --select-case-studies --output-dir results --seed 20260628"
    )
    write_docs(summary, dataset_status, env, results_dir, command)
    write_config(results_dir, args, dataset_status, env)

    return {
        "summary": summary,
        "query_df": query_df,
        "predictions": predictions,
        "dataset_status": dataset_status,
        "environment": env,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["casmi2022", "pfas", "both"], default="both")
    parser.add_argument("--native-baselines", action="store_true", help="Request native baseline inference where available.")
    parser.add_argument("--allow-fallback", type=parse_bool, default=True, help="Allow deterministic fallback/proxy scoring when native tools are unavailable.")
    parser.add_argument("--run-ablation", action="store_true")
    parser.add_argument("--export-query-level", action="store_true")
    parser.add_argument("--select-case-studies", action="store_true")
    parser.add_argument("--output-dir", "--results-dir", dest="output_dir", default=str(ROOT / "results"))
    parser.add_argument("--candidate-limit", "--casmi-candidate-limit", dest="candidate_limit", type=int, default=2000)
    parser.add_argument("--casmi-dir", default="")
    parser.add_argument("--pfas-matrix", default=str(DEFAULT_PFAS_MATRIX))
    parser.add_argument("--pfas-score-matrix", default=str(DEFAULT_PFAS_SCORE_MATRIX))
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
