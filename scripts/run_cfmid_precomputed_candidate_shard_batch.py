#!/usr/bin/env python3
"""Run a small resumable batch of CFM-ID candidate-spectrum shards.

The full CASMI CFM-ID cache has 9,365 candidate-spectrum shards, so this helper
is intentionally budgeted. It reads the current completion audit, selects the
next incomplete shards, runs the existing native CFM-ID shard wrapper, and then
refreshes the audit. Use it repeatedly on a server until coverage reaches 100%.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "results" / "casmi_full_completion_audit_v1"
RUN_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"


def run(cmd: list[str], timeout_seconds: int) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(cmd, cwd=ROOT, text=True, check=False, timeout=timeout_seconds)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "status": "completed" if proc.returncode == 0 else "failed",
        "elapsed_seconds": time.time() - started,
    }


def refresh_audit() -> None:
    subprocess.run(
        ["python3", "scripts/summarize_cfmid_precomputed_full_progress.py"],
        cwd=ROOT,
        text=True,
        check=False,
    )
    subprocess.run(
        ["python3", "scripts/write_casmi_full_completion_audit.py"],
        cwd=ROOT,
        text=True,
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-shards", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=86400)
    parser.add_argument("--shard-status-csv", type=Path, default=AUDIT_DIR / "cfmid_candidate_spectrum_shard_status.csv")
    parser.add_argument("--prefer-not-started", action="store_true")
    args = parser.parse_args()

    if not args.shard_status_csv.exists():
        refresh_audit()
    shard_df = pd.read_csv(args.shard_status_csv)
    incomplete = shard_df[~shard_df["status"].astype(str).eq("completed")].copy()
    if args.prefer_not_started:
        incomplete["status_priority"] = incomplete["status"].astype(str).map({"not_started": 0, "partial_cached": 1}).fillna(2)
        incomplete = incomplete.sort_values(["status_priority", "shard_id"]).drop(columns=["status_priority"])
    else:
        incomplete = incomplete.sort_values(["shard_id"])
    selected = incomplete.head(max(0, args.max_shards)).copy()
    rows: list[dict[str, Any]] = []
    for _, shard in selected.iterrows():
        cmd = [
            "python3",
            "scripts/run_cfmid_precomputed_candidate_shard.py",
            "--outdir",
            str(RUN_OUTDIR),
            "--adduct",
            str(shard["adduct"]),
            "--candidate-start",
            str(int(shard["candidate_start"])),
            "--candidate-limit",
            str(int(shard["candidate_limit"])),
            "--timeout-seconds",
            str(args.timeout_seconds),
            "--resume",
        ]
        result = run(cmd, args.timeout_seconds + 60)
        rows.append(
            {
                "shard_id": int(shard["shard_id"]),
                "adduct": str(shard["adduct"]),
                "candidate_start": int(shard["candidate_start"]),
                "candidate_limit": int(shard["candidate_limit"]),
                **result,
            }
        )
        if result["returncode"] != 0:
            break

    if rows:
        out = AUDIT_DIR / "last_cfmid_candidate_shard_batch_run.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
    refresh_audit()


if __name__ == "__main__":
    main()
