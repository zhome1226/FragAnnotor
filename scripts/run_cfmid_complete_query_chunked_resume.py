#!/usr/bin/env python3
"""Resume a native CFM-ID complete-query run in small candidate chunks.

This is designed for long CASMI CFM-ID queries where a single `cfm-predict`
call can run for hours or be interrupted. It reads an existing complete-query
work directory, predicts only missing candidate spectra in chunks, appends any
new MSP records to the cumulative MSP file, and ranks the query only after all
candidate spectra are present.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd

from run_cfmid_precomputed_smoke import parse_msp, parse_ranked, write_plain_spectrum, write_query_spectrum


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
DEFAULT_CFM_DIR = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin")
DEFAULT_MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
DEFAULT_WORK_DIR = (
    ROOT
    / "results"
    / "casmi2022_cfmid_native_precomputed_complete_query_subset_v1"
    / "work"
    / "query_35"
)
DEFAULT_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_complete_query_expansion_v1"


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


def read_candidate_smiles(path: Path) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            mol_id_text, _, smiles = text.partition(" ")
            if not smiles:
                continue
            rows.append((int(mol_id_text), smiles.strip()))
    return rows


def write_candidate_smiles(path: Path, rows: list[tuple[int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for mol_id, smiles in rows:
            handle.write(f"{mol_id} {smiles}\n")


def append_msp_record(target: Path, mol_id: int, energies: dict[int, list[tuple[float, float]]]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        if target.stat().st_size > 0:
            handle.write("\n")
        handle.write(f"ID: {int(mol_id)}\n")
        for energy in [0, 1, 2]:
            handle.write(f"Comment: Energy {energy}\n")
            peaks = energies.get(energy, [])
            handle.write(f"Num peaks: {len(peaks)}\n")
            for mz, intensity in sorted(peaks):
                handle.write(f"{float(mz):.6f} {float(intensity):.6f}\n")
            handle.write("\n")


def reuse_duplicate_smiles_spectra(
    predicted_msp: Path,
    candidate_rows: list[tuple[int, str]],
    spectra: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fill missing duplicate-SMILES candidate ids from existing CFM-ID spectra.

    CASMI candidate lists can contain different candidate ids with identical
    SMILES. CFM-ID spectra are deterministic for a given SMILES/adduct/model, so
    reusing an already generated spectrum for an identical SMILES avoids
    re-running the native predictor without fabricating non-CFM-ID evidence.
    """

    smiles_to_source: dict[str, tuple[int, dict[int, list[tuple[float, float]]]]] = {}
    for mol_id, smiles in candidate_rows:
        energies = spectra.get(str(int(mol_id)))
        if energies is not None and smiles not in smiles_to_source:
            smiles_to_source[smiles] = (int(mol_id), energies)

    cloned: list[dict[str, Any]] = []
    for mol_id, smiles in candidate_rows:
        mol_text = str(int(mol_id))
        if mol_text in spectra or smiles not in smiles_to_source:
            continue
        source_mol_id, energies = smiles_to_source[smiles]
        append_msp_record(predicted_msp, int(mol_id), energies)
        spectra[mol_text] = energies
        cloned.append(
            {
                "candidate_mol_id": int(mol_id),
                "source_candidate_mol_id": int(source_mol_id),
                "smiles": smiles,
                "reason": "identical_smiles_cfm_id_spectrum_reuse",
            }
        )
    return cloned


def append_file(target: Path, source: Path) -> None:
    if not source.exists() or source.stat().st_size == 0:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("ab") as out, source.open("rb") as inp:
        if target.stat().st_size > 0:
            out.write(b"\n")
        shutil.copyfileobj(inp, out)


def query_metadata(casmi_dir: Path, query_id: str) -> dict[str, Any]:
    spec = pd.read_pickle(casmi_dir / "spec_df.pkl")
    row = spec[spec["spec_id"].astype(str).eq(str(query_id))]
    if row.empty:
        raise SystemExit(f"Could not find CASMI query {query_id}")
    item = row.iloc[0]
    return {
        "query_id": str(item["spec_id"]),
        "query_mol_id": int(item["mol_id"]),
        "adduct": str(item["prec_type"]),
        "peaks": [(float(mz), float(intensity)) for mz, intensity in item["peaks"]],
    }


def update_triples(work_dir: Path, candidate_rows: list[tuple[int, str]], spectra: dict[str, Any]) -> tuple[Path, int]:
    plain_dir = work_dir / "plain_candidate_spectra"
    triples = work_dir / "candidate_triples_plain.txt"
    count = 0
    with triples.open("w", encoding="utf-8") as handle:
        for mol_id, smiles in candidate_rows:
            mol_text = str(int(mol_id))
            if mol_text not in spectra:
                continue
            spectrum_path = plain_dir / f"{mol_text}.txt"
            write_plain_spectrum(spectrum_path, spectra[mol_text])
            handle.write(f"{mol_text} {smiles} {spectrum_path}\n")
            count += 1
    return triples, count


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--casmi-dir", type=Path, default=CASMI_DIR)
    parser.add_argument("--cfm-bin-dir", type=Path, default=DEFAULT_CFM_DIR)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--query-id", default="35")
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--max-chunks", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--score-type", default="DotProduct")
    args = parser.parse_args()

    if args.work_dir == DEFAULT_WORK_DIR and str(args.query_id) != "35":
        args.work_dir = DEFAULT_WORK_DIR.parent / f"query_{args.query_id}"

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    candidate_smiles = args.work_dir / "candidate_smiles.txt"
    predicted_msp = args.work_dir / "candidate_spectra.msp"
    if not candidate_smiles.exists():
        raise SystemExit(f"Missing candidate SMILES file: {candidate_smiles}")

    meta = query_metadata(args.casmi_dir, args.query_id)
    adduct = meta["adduct"]
    model_dir = args.model_root / adduct
    candidate_rows = read_candidate_smiles(candidate_smiles)
    existing = parse_msp(predicted_msp) if predicted_msp.exists() and predicted_msp.stat().st_size > 0 else {}
    cloned_before = reuse_duplicate_smiles_spectra(predicted_msp, candidate_rows, existing)
    missing_rows = [(mol_id, smiles) for mol_id, smiles in candidate_rows if str(mol_id) not in existing]

    command_rows: list[dict[str, Any]] = []
    chunk_dir = args.work_dir / "chunked_resume"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunks_to_run = [
        missing_rows[start : start + max(1, args.chunk_size)]
        for start in range(0, len(missing_rows), max(1, args.chunk_size))
    ][: max(0, args.max_chunks)]

    for chunk_index, chunk in enumerate(chunks_to_run, start=1):
        chunk_input = chunk_dir / f"chunk_{chunk_index:04d}_candidate_smiles.txt"
        chunk_msp = chunk_dir / f"chunk_{chunk_index:04d}_candidate_spectra.msp"
        write_candidate_smiles(chunk_input, chunk)
        cmd = [
            str(args.cfm_bin_dir / "cfm-predict"),
            str(chunk_input),
            "0.001",
            str(model_dir / "param_output.log"),
            str(model_dir / "param_config.txt"),
            "0",
            str(chunk_msp),
            "1",
            "1",
        ]
        run = run_command(
            cmd,
            chunk_dir / f"chunk_{chunk_index:04d}.stdout.log",
            chunk_dir / f"chunk_{chunk_index:04d}.stderr.log",
            args.timeout_seconds,
        )
        append_file(predicted_msp, chunk_msp)
        chunk_spectra = parse_msp(chunk_msp) if chunk_msp.exists() and chunk_msp.stat().st_size > 0 else {}
        command_rows.append(
            {
                "query_id": args.query_id,
                "chunk_index": chunk_index,
                "requested_candidates": len(chunk),
                "predicted_spectra": len(chunk_spectra),
                **run,
            }
        )
        pd.DataFrame(command_rows).to_csv(args.outdir / f"query{args.query_id}_chunked_resume_commands.csv", index=False)

    spectra = parse_msp(predicted_msp) if predicted_msp.exists() and predicted_msp.stat().st_size > 0 else {}
    cloned_after = reuse_duplicate_smiles_spectra(predicted_msp, candidate_rows, spectra)
    cloned_rows = cloned_before + cloned_after
    triples, triple_count = update_triples(args.work_dir, candidate_rows, spectra)
    missing_after = [(mol_id, smiles) for mol_id, smiles in candidate_rows if str(mol_id) not in spectra]
    ranked_rows: list[dict[str, Any]] = []
    rank_run: dict[str, Any] = {
        "status": "skipped_missing_candidate_spectra",
        "elapsed_seconds": 0.0,
        "command": "",
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }
    ranked_path = args.work_dir / f"cfmid_precomputed_ranked_{args.query_id}.txt"
    if not missing_after:
        query_spectrum = args.work_dir / f"query_spectrum_{args.query_id}.txt"
        write_query_spectrum(query_spectrum, meta["peaks"])
        rank_cmd = [
            str(args.cfm_bin_dir / "cfm-id-precomputed"),
            str(query_spectrum),
            args.query_id,
            str(triples),
            "-1",
            "10",
            "0.01",
            args.score_type,
            str(ranked_path),
            "0",
            "0",
        ]
        rank_run = run_command(
            rank_cmd,
            args.work_dir / "logs" / "cfm_id_precomputed_chunked.stdout.log",
            args.work_dir / "logs" / "cfm_id_precomputed_chunked.stderr.log",
            args.timeout_seconds,
        )
        ranked_rows = parse_ranked(ranked_path) if rank_run["status"] == "completed" else []

    true_rank = next((row["rank"] for row in ranked_rows if int(row["candidate_mol_id"]) == int(meta["query_mol_id"])), None)
    audit = {
        "stage": "casmi2022_cfmid_native_precomputed_complete_query_chunked_resume_v1",
        "query_id": args.query_id,
        "query_mol_id": meta["query_mol_id"],
        "candidate_count": len(candidate_rows),
        "predicted_spectrum_ids": len(spectra),
        "missing_candidate_spectra": len(missing_after),
        "duplicate_smiles_spectra_reused": len(cloned_rows),
        "chunks_requested_this_run": len(chunks_to_run),
        "chunk_size": args.chunk_size,
        "ranked_rows": len(ranked_rows),
        "true_rank": true_rank,
        "status": "completed_ranked" if ranked_rows and true_rank is not None else ("partial_missing_candidate_spectra" if missing_after else "partial_unranked"),
        "rank_run": rank_run,
        "claim_guardrail": "Only report Top-k/MRR for this query if status is completed_ranked.",
    }
    write_json(args.outdir / f"query{args.query_id}_chunked_resume_audit.json", audit)
    if str(args.query_id) == "35":
        write_json(args.outdir / "chunked_resume_audit.json", audit)
    expansion_audit = {
        "stage": "casmi2022_cfmid_native_precomputed_complete_query_expansion_v1",
        "purpose": "Record expansion of the complete-query native CFM-ID CASMI subset beyond the initial completed query 16 result.",
        "query_id": audit["query_id"],
        "query_mol_id": audit["query_mol_id"],
        "candidate_pool_policy": "full_candidate_set_for_selected_query",
        "candidate_count": audit["candidate_count"],
        "predicted_spectrum_ids": audit["predicted_spectrum_ids"],
        "missing_candidate_spectra": audit["missing_candidate_spectra"],
        "ranked_rows": audit["ranked_rows"],
        "true_rank": audit["true_rank"],
        "status": audit["status"],
        "chunk_size_last_run": audit["chunk_size"],
        "chunks_requested_last_run": audit["chunks_requested_this_run"],
        "duplicate_smiles_spectra_reused_last_run": audit["duplicate_smiles_spectra_reused"],
        "rank_run": audit["rank_run"],
        "included_in_completed_subset_metrics": audit["status"] == "completed_ranked",
        "claim_guardrail": f"Query {args.query_id} may be reported only as complete-query subset evidence when completed; it is not a full CASMI CFM-ID baseline.",
    }
    write_json(args.outdir / f"query{args.query_id}_audit_summary.json", expansion_audit)
    if str(args.query_id) == "35":
        write_json(args.outdir / "audit_summary.json", expansion_audit)
    pd.DataFrame(cloned_rows).to_csv(args.outdir / f"query{args.query_id}_duplicate_smiles_reused.csv", index=False)
    pd.DataFrame(
        [
            {
                "query_id": args.query_id,
                "candidate_count": audit["candidate_count"],
                "predicted_spectrum_ids": audit["predicted_spectrum_ids"],
                "missing_candidate_spectra": audit["missing_candidate_spectra"],
                "ranked_rows": audit["ranked_rows"],
                "true_rank": audit["true_rank"],
                "status": audit["status"],
            }
        ]
    ).to_csv(args.outdir / f"query{args.query_id}_chunked_resume_status.csv", index=False)
    remaining_path = args.outdir / f"query{args.query_id}_remaining_candidate_smiles.txt"
    if missing_after:
        write_candidate_smiles(remaining_path, missing_after)
    elif remaining_path.exists():
        remaining_path.unlink()
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
