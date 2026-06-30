#!/usr/bin/env python3
"""Audit native CFM-ID readiness for CASMI2022 candidate ranking.

The script never converts partial CFM-ID outputs into benchmark scores. It
records whether a cfmid4-compatible binary can run a smoke case and, optionally,
whether timing probes can complete for larger CASMI candidate sets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFMID = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin/cfm-id")
DEFAULT_MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def make_spectrum_file(path: Path, peaks: list[tuple[float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for label in ["low", "med", "high"]:
            handle.write(label + "\n")
            for mz, intensity in peaks:
                handle.write(f"{float(mz):.6f} {float(intensity):.6f}\n")


def load_casmi_inputs(casmi_dir: Path, query_index: int, candidate_count: int) -> tuple[pd.Series, list[tuple[int, str]], Path]:
    spec = pd.read_pickle(casmi_dir / "spec_df.pkl")
    cand = pd.read_pickle(casmi_dir / "cand_df.pkl")
    eligible = spec[spec["prec_type"].isin(["[M+H]+", "[M-H]-"])].reset_index(drop=True)
    row = eligible.iloc[int(query_index)]
    query_mol_id = int(row["mol_id"])
    ids = cand[cand["query_mol_id"].eq(query_mol_id)]["candidate_mol_id"].astype(int).tolist()
    if candidate_count > 0:
        ids = ids[:candidate_count]
    if query_mol_id not in ids:
        ids = [query_mol_id] + ids
    needed = set(ids)
    id_to_smiles: dict[int, str] = {}
    smiles_path = casmi_dir / "all_smiles.txt"
    with smiles_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not needed:
                break
            line = line.strip()
            if not line:
                continue
            mol_id_text, _, smiles = line.partition(" ")
            try:
                mol_id = int(mol_id_text)
            except ValueError:
                continue
            if mol_id in needed:
                id_to_smiles[mol_id] = smiles.strip()
                needed.remove(mol_id)
    candidates = [(mol_id, id_to_smiles[mol_id]) for mol_id in ids if mol_id in id_to_smiles]
    return row, candidates, smiles_path


def write_candidate_file(path: Path, candidates: list[tuple[int, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for mol_id, smiles in candidates:
            handle.write(f"{mol_id} {smiles}\n")


def run_cfmid(
    executable: Path,
    model_root: Path,
    spectrum_file: Path,
    candidate_file: Path,
    adduct: str,
    out_txt: Path,
    out_mgf: Path | None,
    timeout: int,
) -> dict[str, Any]:
    model_dir = model_root / adduct
    cmd = [
        str(executable),
        str(spectrum_file),
        "casmi_probe",
        str(candidate_file),
        "-1",
        "10",
        "0.01",
        "0.001",
        str(model_dir / "param_output.log"),
        str(model_dir / "param_config.txt"),
        "DotProduct",
        "1",
        str(out_txt),
    ]
    if out_mgf is not None:
        cmd.append(str(out_mgf))
    started = time.time()
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        elapsed = time.time() - started
        return {
            "command": " ".join(cmd),
            "completed": completed.returncode == 0,
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
            "output_txt_exists": out_txt.exists(),
            "output_txt_rows": sum(1 for _ in out_txt.open()) if out_txt.exists() else 0,
            "output_mgf_exists": bool(out_mgf and out_mgf.exists()),
            "output_mgf_size_bytes": out_mgf.stat().st_size if out_mgf and out_mgf.exists() else 0,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - started
        return {
            "command": " ".join(cmd),
            "completed": False,
            "returncode": None,
            "elapsed_seconds": elapsed,
            "timeout_seconds": timeout,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "output_txt_exists": out_txt.exists(),
            "output_txt_rows": sum(1 for _ in out_txt.open()) if out_txt.exists() else 0,
            "output_mgf_exists": bool(out_mgf and out_mgf.exists()),
            "output_mgf_size_bytes": out_mgf.stat().st_size if out_mgf and out_mgf.exists() else 0,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit native CFM-ID CASMI readiness.")
    parser.add_argument("--casmi-dir", type=Path, default=ROOT / "data" / "proc" / "casmi_2022")
    parser.add_argument("--cfmid", type=Path, default=DEFAULT_CFMID)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "native_cfmid_casmi")
    parser.add_argument("--query-index", type=int, default=0)
    parser.add_argument("--smoke-candidates", type=int, default=3)
    parser.add_argument("--timing-candidates", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--run-timing", action="store_true", help="Run the long timing probe; otherwise only smoke-test.")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    work = ROOT / "results" / "logs" / "native_smoke" / "cfmid_repair"
    work.mkdir(parents=True, exist_ok=True)

    row, smoke_candidates, _ = load_casmi_inputs(args.casmi_dir, args.query_index, args.smoke_candidates)
    adduct = str(row["prec_type"])
    spectrum_file = work / "audit_spectrum.txt"
    smoke_candidate_file = work / "audit_smoke_candidates.txt"
    make_spectrum_file(spectrum_file, [(float(mz), float(i)) for mz, i in row["peaks"]])
    write_candidate_file(smoke_candidate_file, smoke_candidates)
    smoke_result = run_cfmid(
        args.cfmid,
        args.model_root,
        spectrum_file,
        smoke_candidate_file,
        adduct,
        work / "audit_smoke_output.txt",
        work / "audit_smoke_output.mgf",
        args.timeout_seconds,
    )

    timing_result: dict[str, Any] | None = None
    if args.run_timing:
        _, timing_candidates, _ = load_casmi_inputs(args.casmi_dir, args.query_index, args.timing_candidates)
        timing_candidate_file = work / f"audit_timing_candidates_{len(timing_candidates)}.txt"
        write_candidate_file(timing_candidate_file, timing_candidates)
        timing_result = run_cfmid(
            args.cfmid,
            args.model_root,
            spectrum_file,
            timing_candidate_file,
            adduct,
            work / f"audit_timing_output_{len(timing_candidates)}.txt",
            None,
            args.timeout_seconds,
        )

    runtime_blocked = bool(timing_result and not timing_result.get("completed"))
    status = "runtime_blocked_full_casmi_not_reported" if runtime_blocked else ("smoke_passed_timing_not_run" if smoke_result.get("completed") else "smoke_failed")
    audit = {
        "stage": "native_cfmid_casmi_runtime_audit_v1",
        "status": status,
        "native_binary": str(args.cfmid),
        "native_binary_exists": args.cfmid.exists(),
        "native_binary_smoke_status": "passed" if smoke_result.get("completed") else "failed",
        "cfmid_model_root": str(args.model_root),
        "smoke_result": smoke_result,
        "timing_result": timing_result,
        "benchmark_decision": "Do not report native CFM-ID CASMI Top-k metrics until a complete per-query candidate score table is generated. Smoke/partial outputs are readiness evidence only, not benchmark results.",
        "environment": {"python": sys.version, "platform": platform.platform()},
    }
    write_json(args.outdir / "native_cfmid_runtime_audit.json", audit)
    pd.DataFrame(
        [
            {
                "stage": audit["stage"],
                "status": audit["status"],
                "native_binary": audit["native_binary"],
                "native_binary_smoke_status": audit["native_binary_smoke_status"],
                "timing_completed": None if timing_result is None else timing_result.get("completed"),
                "benchmark_decision": audit["benchmark_decision"],
            }
        ]
    ).to_csv(args.outdir / "native_cfmid_runtime_audit.csv", index=False)
    (args.outdir / "native_cfmid_runtime_audit.md").write_text(
        "# Native CFM-ID CASMI Runtime Audit\n\n"
        f"Status: `{audit['status']}`\n\n"
        f"Native binary: `{args.cfmid}`\n\n"
        f"Smoke status: `{audit['native_binary_smoke_status']}`\n\n"
        f"{audit['benchmark_decision']}\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
