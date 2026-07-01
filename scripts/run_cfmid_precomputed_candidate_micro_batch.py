#!/usr/bin/env python3
"""Run a tiny resumable CFM-ID candidate-spectrum batch.

This is safer than the 100-candidate shard runner for interactive sessions. It
finds the next missing candidate spectra in the full CASMI CFM-ID cache, runs
the existing native CFM-ID shard wrapper on contiguous micro-ranges, and then
refreshes the full completion audit.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd

from run_cfmid_precomputed_candidate_shard import adduct_slug, get_unique_candidate_ids


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
RUN_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"
AUDIT_DIR = ROOT / "results" / "casmi_full_completion_audit_v1"


def cached_candidate_ids(slug: str) -> set[int]:
    cache_dir = RUN_OUTDIR / "candidate_spectra_cache" / slug
    if not cache_dir.exists():
        return set()
    ids: set[int] = set()
    for path in cache_dir.glob("*.txt"):
        if path.stat().st_size <= 0:
            continue
        try:
            ids.add(int(path.stem))
        except ValueError:
            continue
    return ids


def contiguous_ranges(indexes: list[int], max_range_len: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    if not indexes:
        return ranges
    start = prev = indexes[0]
    for idx in indexes[1:]:
        if idx == prev + 1 and idx - start + 1 <= max_range_len:
            prev = idx
            continue
        ranges.append((start, prev - start + 1))
        start = prev = idx
    ranges.append((start, prev - start + 1))
    return ranges


def run_command(cmd: list[str], timeout_seconds: int) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, check=False, timeout=timeout_seconds)
        return {
            "command": " ".join(cmd),
            "status": "completed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "elapsed_seconds": time.time() - started,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(cmd),
            "status": "timeout",
            "returncode": None,
            "elapsed_seconds": time.time() - started,
        }


def refresh() -> None:
    subprocess.run(["python3", "scripts/summarize_cfmid_precomputed_full_progress.py"], cwd=ROOT, check=False)
    subprocess.run(["python3", "scripts/write_casmi_full_completion_audit.py"], cwd=ROOT, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adduct", default="[M+H]+")
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--max-range-len", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--outdir", type=Path, default=RUN_OUTDIR)
    args = parser.parse_args()

    all_ids = get_unique_candidate_ids(CASMI_DIR, MODEL_ROOT, args.adduct)
    cached = cached_candidate_ids(adduct_slug(args.adduct))
    missing_positions = [idx for idx, mol_id in enumerate(all_ids) if mol_id not in cached]
    selected_positions = missing_positions[: max(0, args.max_candidates)]
    ranges = contiguous_ranges(selected_positions, max(1, args.max_range_len))

    rows: list[dict[str, Any]] = []
    for start, limit in ranges:
        before = len(cached_candidate_ids(adduct_slug(args.adduct)))
        cmd = [
            "python3",
            "scripts/run_cfmid_precomputed_candidate_shard.py",
            "--outdir",
            str(args.outdir),
            "--adduct",
            args.adduct,
            "--candidate-start",
            str(start),
            "--candidate-limit",
            str(limit),
            "--timeout-seconds",
            str(args.timeout_seconds),
            "--resume",
        ]
        result = run_command(cmd, args.timeout_seconds + 30)
        after = len(cached_candidate_ids(adduct_slug(args.adduct)))
        rows.append(
            {
                "adduct": args.adduct,
                "candidate_start": start,
                "candidate_limit": limit,
                "cache_count_before": before,
                "cache_count_after": after,
                "new_cached_candidates": after - before,
                **result,
            }
        )
        if result["status"] != "completed":
            break

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(AUDIT_DIR / "last_cfmid_candidate_micro_batch_run.csv", index=False)
    refresh()


if __name__ == "__main__":
    main()
