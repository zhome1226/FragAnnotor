#!/usr/bin/env python3
"""Run incomplete CFM-ID candidate-spectrum shards in parallel.

This complements the sequential full runner. It skips shards that already have
complete cache coverage, optionally starts after a shard id, and writes a small
batch log under the full-completion audit directory. Runtime cache directories
remain ignored by Git.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "results" / "casmi_full_completion_audit_v1"
SHARD_STATUS = AUDIT_DIR / "cfmid_candidate_spectrum_shard_status.csv"
RUN_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"


def refresh_audit() -> None:
    subprocess.run(["python3", "scripts/summarize_cfmid_precomputed_full_progress.py"], cwd=ROOT, check=False)
    subprocess.run(["python3", "scripts/write_casmi_full_completion_audit.py"], cwd=ROOT, check=False)


def run_one(row: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    started = time.time()
    cmd = [
        "python3",
        "scripts/run_cfmid_precomputed_candidate_shard.py",
        "--outdir",
        str(RUN_OUTDIR),
        "--adduct",
        str(row["adduct"]),
        "--candidate-start",
        str(int(row["candidate_start"])),
        "--candidate-limit",
        str(int(row["candidate_limit"])),
        "--timeout-seconds",
        str(timeout_seconds),
        "--resume",
    ]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, check=False, timeout=timeout_seconds + 60)
        status = "completed" if proc.returncode == 0 else "failed"
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        status = "timeout"
        returncode = None
    return {
        "shard_id": int(row["shard_id"]),
        "adduct": str(row["adduct"]),
        "candidate_start": int(row["candidate_start"]),
        "candidate_limit": int(row["candidate_limit"]),
        "command": " ".join(cmd),
        "status": status,
        "returncode": returncode,
        "elapsed_seconds": time.time() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-shards", type=int, default=2)
    parser.add_argument("--start-after-shard", type=int, default=-1)
    parser.add_argument("--timeout-seconds", type=int, default=86400)
    parser.add_argument("--prefer-not-started", action="store_true")
    args = parser.parse_args()

    refresh_audit()
    status = pd.read_csv(SHARD_STATUS)
    todo = status[~status["status"].astype(str).eq("completed")].copy()
    todo = todo[todo["shard_id"].astype(int).gt(args.start_after_shard)].copy()
    if args.prefer_not_started:
        todo["status_priority"] = todo["status"].astype(str).map({"not_started": 0, "partial_cached": 1}).fillna(2)
        todo = todo.sort_values(["status_priority", "shard_id"]).drop(columns=["status_priority"])
    else:
        todo = todo.sort_values(["shard_id"])
    selected = todo.head(max(0, args.max_shards)).to_dict(orient="records")

    rows: list[dict[str, Any]] = []
    with futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_to_row = {pool.submit(run_one, row, args.timeout_seconds): row for row in selected}
        for future in futures.as_completed(future_to_row):
            rows.append(future.result())

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if rows:
        pd.DataFrame(sorted(rows, key=lambda r: r["shard_id"])).to_csv(
            AUDIT_DIR / "last_cfmid_candidate_parallel_batch_run.csv",
            index=False,
        )
    refresh_audit()


if __name__ == "__main__":
    main()
