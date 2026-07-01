#!/usr/bin/env python3
"""Run full supported CASMI CFM-ID work until the completion gate is met.

The native CFM-ID CASMI run is intentionally cache-backed. This controller
keeps launching bounded candidate-spectrum shard batches, refreshes progress,
and only starts query-ranking shards after all supported candidate spectra are
available. It does not fabricate missing scores.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "results" / "casmi_full_completion_audit_v1"
RUN_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"
SUMMARY_PATH = RUN_OUTDIR / "audit_summary.json"
FULL_STATUS_PATH = AUDIT_DIR / "full_completion_status.csv"
LOOP_LOG = AUDIT_DIR / "logs" / "cfmid_full_supported_continuous_loop.jsonl"


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, check=check)


def refresh() -> dict[str, Any]:
    run(["python3", "scripts/summarize_cfmid_precomputed_full_progress.py"], check=False)
    run(["python3", "scripts/write_casmi_full_completion_audit.py"], check=False)
    if SUMMARY_PATH.exists():
        return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    return {}


def adduct_slug(adduct: str) -> str:
    return adduct.replace("[", "").replace("]", "").replace("+", "plus").replace("-", "minus")


def active_shard_keys() -> set[tuple[str, int, int]]:
    proc = subprocess.run(
        ["pgrep", "-af", "run_cfmid_precomputed_candidate_shard.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    keys: set[tuple[str, int, int]] = set()
    for line in proc.stdout.splitlines():
        adduct = re.search(r"--adduct\s+(\S+)", line)
        start = re.search(r"--candidate-start\s+(\d+)", line)
        limit = re.search(r"--candidate-limit\s+(\d+)", line)
        if adduct and start and limit:
            keys.add((adduct.group(1), int(start.group(1)), int(limit.group(1))))
    return keys


def sync_active_locks() -> None:
    active = active_shard_keys()
    for adduct, start, limit in active:
        slug = adduct_slug(adduct)
        lock_dir = RUN_OUTDIR / "candidate_spectrum_shards" / slug / f"shard_{start}_{limit}.lock"
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "active_process.txt").write_text(
            f"created_by=run_cfmid_full_supported_continuous.py\n"
            f"adduct={adduct}\ncandidate_start={start}\ncandidate_limit={limit}\n"
            f"timestamp={datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )

    for lock_dir in RUN_OUTDIR.glob("candidate_spectrum_shards/*/shard_*_*.lock"):
        match = re.search(r"candidate_spectrum_shards/([^/]+)/shard_(\d+)_(\d+)\.lock$", str(lock_dir))
        if not match:
            continue
        slug, start_text, limit_text = match.groups()
        start = int(start_text)
        limit = int(limit_text)
        still_active = any(adduct_slug(adduct) == slug and s == start and l == limit for adduct, s, l in active)
        if still_active:
            continue
        # Drop stale controller-created locks. Locks from live parallel workers
        # are removed by the worker itself; this is only a recovery fallback.
        try:
            shutil.rmtree(lock_dir)
        except FileNotFoundError:
            pass


def append_loop_log(row: dict[str, Any]) -> None:
    LOOP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOOP_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def summary_status(summary: dict[str, Any]) -> str:
    return str(summary.get("status", "unknown"))


def run_candidate_batch(workers: int, max_shards: int, timeout_seconds: int) -> int:
    sync_active_locks()
    cmd = [
        "python3",
        "scripts/run_cfmid_candidate_shards_parallel.py",
        "--workers",
        str(workers),
        "--max-shards",
        str(max_shards),
        "--timeout-seconds",
        str(timeout_seconds),
        "--prefer-not-started",
    ]
    proc = run(cmd, check=False)
    return int(proc.returncode)


def run_query_ranking() -> int:
    proc = run(["bash", "results/cfmid_precomputed_full_casmi_manifest_v1/run_query_ranking_shards_after_spectra.sh"], check=False)
    return int(proc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-shards-per-batch", type=int, default=32)
    parser.add_argument("--timeout-seconds", type=int, default=86400)
    parser.add_argument("--sleep-seconds", type=int, default=30)
    parser.add_argument("--max-loops", type=int, default=0, help="0 means run until completion.")
    args = parser.parse_args()

    loops = 0
    while True:
        loops += 1
        sync_active_locks()
        summary = refresh()
        status = summary_status(summary)
        candidate_done = bool(summary.get("candidate_spectrum_completion_fraction") == 1.0)
        query_done = bool(summary.get("query_completion_fraction") == 1.0)
        append_loop_log(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "loop": loops,
                "status": status,
                "completed_candidate_spectra": summary.get("completed_candidate_spectra"),
                "expected_unique_candidate_spectra": summary.get("expected_unique_candidate_spectra"),
                "n_completed_queries": summary.get("n_completed_queries"),
                "n_supported_queries": summary.get("n_supported_queries"),
            }
        )
        if status == "completed_full_supported":
            break
        if args.max_loops and loops > args.max_loops:
            break
        if not candidate_done:
            run_candidate_batch(args.workers, args.max_shards_per_batch, args.timeout_seconds)
        elif not query_done:
            run_query_ranking()
        else:
            refresh()
        time.sleep(max(0, args.sleep_seconds))


if __name__ == "__main__":
    main()
