#!/usr/bin/env python3
"""Validate a CFM-ID precomputed-spectrum ranking path on a small CASMI subset.

This is a smoke test for the faster native CFM-ID workflow:

1. predict candidate spectra once with `cfm-predict`;
2. split/normalize the predicted MSP into per-candidate plain spectrum files;
3. rank a query with `cfm-id-precomputed`.

The output is intentionally labelled as a smoke test, not as a CASMI benchmark.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFM_DIR = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin")
DEFAULT_MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
DEFAULT_CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
DEFAULT_OUTDIR = ROOT / "results" / "cfmid_precomputed_smoke_v1"


def run_command(cmd: list[str], stdout_path: Path, stderr_path: Path, timeout_seconds: int) -> dict[str, Any]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        try:
            proc = subprocess.run(cmd, stdout=stdout, stderr=stderr, text=True, timeout=timeout_seconds, check=False)
            status = "completed" if proc.returncode == 0 else "failed"
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            status = "timeout"
            returncode = None
    return {
        "command": " ".join(cmd),
        "status": status,
        "returncode": returncode,
        "elapsed_seconds": time.time() - started,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def parse_all_smiles(path: Path, needed: set[int]) -> dict[int, str]:
    remaining = set(needed)
    out: dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not remaining:
                break
            text = line.strip()
            if not text:
                continue
            mol_id_text, _, smiles = text.partition(" ")
            try:
                mol_id = int(mol_id_text)
            except ValueError:
                continue
            if mol_id in remaining:
                out[mol_id] = smiles.strip()
                remaining.remove(mol_id)
    return out


def write_query_spectrum(path: Path, peaks: list[tuple[float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for label in ["low", "med", "high"]:
            handle.write(label + "\n")
            for mz, intensity in sorted(peaks):
                handle.write(f"{float(mz):.6f} {float(intensity):.6f}\n")


def parse_msp(path: Path) -> dict[str, dict[int, list[tuple[float, float]]]]:
    spectra: dict[str, dict[int, list[tuple[float, float]]]] = {}
    current_id: str | None = None
    current_energy: int | None = None
    peaks_remaining = 0
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                current_energy = None
                peaks_remaining = 0
                continue
            if line.startswith("ID:"):
                current_id = line.split(":", 1)[1].strip()
                spectra.setdefault(current_id, {})
                continue
            if line.startswith("Comment: Energy"):
                current_energy = int(line.split("Energy", 1)[1].strip())
                if current_id is not None:
                    spectra.setdefault(current_id, {}).setdefault(current_energy, [])
                continue
            if line.upper().startswith("NUM PEAKS:"):
                peaks_remaining = int(line.split(":", 1)[1].strip())
                continue
            if peaks_remaining and current_id is not None and current_energy is not None:
                parts = line.split()
                if len(parts) >= 2:
                    spectra[current_id][current_energy].append((float(parts[0]), float(parts[1])))
                peaks_remaining -= 1
    return spectra


def write_plain_spectrum(path: Path, energies: dict[int, list[tuple[float, float]]]) -> None:
    labels = {0: "low", 1: "med", 2: "high"}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for energy in [0, 1, 2]:
            handle.write(labels[energy] + "\n")
            for mz, intensity in sorted(energies.get(energy, [])):
                handle.write(f"{mz:.6f} {intensity:.6f}\n")


def parse_ranked(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("ID:") or line.startswith("$"):
                continue
            parts = line.split(maxsplit=3)
            if len(parts) < 4:
                continue
            try:
                rows.append(
                    {
                        "rank": int(parts[0]),
                        "score": float(parts[1]),
                        "candidate_mol_id": int(parts[2]),
                        "smiles": parts[3],
                    }
                )
            except ValueError:
                continue
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--casmi-dir", type=Path, default=DEFAULT_CASMI_DIR)
    parser.add_argument("--cfm-bin-dir", type=Path, default=DEFAULT_CFM_DIR)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--candidate-limit", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--score-type", default="DotProduct")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(args.casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(args.casmi_dir / "cand_df.pkl")
    query = spec[spec["prec_type"].astype(str).eq("[M+H]+")].iloc[0]
    query_mol_id = int(query["mol_id"])
    query_id = str(query["spec_id"])
    candidate_ids = cand[cand["query_mol_id"].eq(query_mol_id)]["candidate_mol_id"].astype(int).tolist()
    candidate_ids = candidate_ids[: max(0, args.candidate_limit)]
    if query_mol_id not in candidate_ids:
        candidate_ids = [query_mol_id] + candidate_ids

    id_to_smiles = parse_all_smiles(args.casmi_dir / "all_smiles.txt", set(candidate_ids) | {query_mol_id})
    candidate_smiles = args.outdir / "candidate_smiles.txt"
    with candidate_smiles.open("w", encoding="utf-8") as handle:
        for mol_id in candidate_ids:
            smiles = id_to_smiles.get(mol_id)
            if smiles:
                handle.write(f"{mol_id} {smiles}\n")

    query_spectrum = args.outdir / "query_spectrum.txt"
    write_query_spectrum(query_spectrum, [(float(mz), float(intensity)) for mz, intensity in query["peaks"]])

    adduct = str(query["prec_type"])
    model_dir = args.model_root / adduct
    predicted_msp = args.outdir / "candidate_spectra.msp"
    predict_cmd = [
        str(args.cfm_bin_dir / "cfm-predict"),
        str(candidate_smiles),
        "0.001",
        str(model_dir / "param_output.log"),
        str(model_dir / "param_config.txt"),
        "0",
        str(predicted_msp),
        "1",
        "1",
    ]
    predict_run = run_command(
        predict_cmd,
        args.outdir / "logs" / "cfm_predict.stdout.log",
        args.outdir / "logs" / "cfm_predict.stderr.log",
        args.timeout_seconds,
    )

    spectra = parse_msp(predicted_msp) if predicted_msp.exists() else {}
    plain_dir = args.outdir / "plain_candidate_spectra"
    triples = args.outdir / "candidate_triples_plain.txt"
    with triples.open("w", encoding="utf-8") as handle:
        for mol_id in candidate_ids:
            mol_text = str(mol_id)
            smiles = id_to_smiles.get(mol_id)
            if not smiles or mol_text not in spectra:
                continue
            spectrum_path = plain_dir / f"{mol_text}.txt"
            write_plain_spectrum(spectrum_path, spectra[mol_text])
            handle.write(f"{mol_id} {smiles} {spectrum_path}\n")

    ranked = args.outdir / "ranked_precomputed.txt"
    precomputed_cmd = [
        str(args.cfm_bin_dir / "cfm-id-precomputed"),
        str(query_spectrum),
        query_id,
        str(triples),
        "-1",
        "10",
        "0.01",
        args.score_type,
        str(ranked),
        "0",
        "0",
    ]
    precomputed_run = run_command(
        precomputed_cmd,
        args.outdir / "logs" / "cfm_id_precomputed.stdout.log",
        args.outdir / "logs" / "cfm_id_precomputed.stderr.log",
        args.timeout_seconds,
    )
    ranked_rows = parse_ranked(ranked)
    true_rank = next((row["rank"] for row in ranked_rows if row["candidate_mol_id"] == query_mol_id), None)
    with (args.outdir / "ranked_precomputed.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["rank", "score", "candidate_mol_id", "smiles"])
        writer.writeheader()
        writer.writerows(ranked_rows)

    audit = {
        "stage": "cfmid_precomputed_smoke_v1",
        "status": "completed" if predict_run["status"] == "completed" and precomputed_run["status"] == "completed" and ranked_rows else "failed",
        "query_id": query_id,
        "query_mol_id": query_mol_id,
        "adduct": adduct,
        "candidate_limit": args.candidate_limit,
        "candidate_rows": len(candidate_ids),
        "predicted_spectra_ids": len(spectra),
        "ranked_rows": len(ranked_rows),
        "true_rank": true_rank,
        "cfm_predict": predict_run,
        "cfm_id_precomputed": precomputed_run,
        "claim_guardrail": "Smoke test only. This validates the precomputed CFM-ID ranking path and must not be reported as a CASMI benchmark.",
    }
    (args.outdir / "audit_summary.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# CFM-ID Precomputed Smoke Test",
        "",
        audit["claim_guardrail"],
        "",
        f"- Status: `{audit['status']}`",
        f"- Query: `{query_id}` / molecule `{query_mol_id}`",
        f"- Candidate rows: `{audit['candidate_rows']}`",
        f"- Predicted spectrum IDs parsed: `{audit['predicted_spectra_ids']}`",
        f"- Ranked rows: `{audit['ranked_rows']}`",
        f"- True rank in smoke set: `{audit['true_rank']}`",
        f"- cfm-predict seconds: `{predict_run['elapsed_seconds']:.3f}`",
        f"- cfm-id-precomputed seconds: `{precomputed_run['elapsed_seconds']:.3f}`",
        "",
    ]
    (args.outdir / "cfmid_precomputed_smoke_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
