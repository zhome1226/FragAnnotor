#!/usr/bin/env python3
"""Prepare a resumable full native CFM-ID CASMI run manifest.

This does not execute the long CFM-ID job. It creates shard commands that use
`run_native_cfmid_casmi_subset.py` with `candidate_limit=-1`, which means the
full candidate pool for each supported query.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
OUTDIR = ROOT / "results" / "cfmid_full_casmi_run_manifest_v1"
FULL_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_full_supported_v1"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(CASMI_DIR / "spec_df.pkl")
    cand = pd.read_pickle(CASMI_DIR / "cand_df.pkl")
    model_adducts = {p.name for p in MODEL_ROOT.iterdir() if p.is_dir()}
    supported = spec[spec["prec_type"].astype(str).isin(model_adducts)].reset_index(drop=True).copy()
    unsupported = spec[~spec["prec_type"].astype(str).isin(model_adducts)].copy()
    counts = cand.groupby("query_mol_id")["candidate_mol_id"].size()
    rows = []
    for supported_index, row in supported.iterrows():
        mol_id = int(row["mol_id"])
        count = int(counts.get(mol_id, 0))
        rows.append(
            {
                "supported_index": int(supported_index),
                "spec_id": str(row["spec_id"]),
                "query_mol_id": mol_id,
                "adduct": str(row["prec_type"]),
                "precursor_mz": float(row["prec_mz"]),
                "candidate_count": count,
                "full_output_file": str(FULL_OUTDIR / "work" / f"query_{row['spec_id']}" / f"cfmid_ranked_{row['spec_id']}.txt"),
                "status": "pending",
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(OUTDIR / "cfmid_full_supported_query_manifest.csv", index=False)

    shard_size = 5
    shard_rows = []
    commands = []
    for shard_id, start in enumerate(range(0, len(manifest), shard_size)):
        stop = min(start + shard_size, len(manifest))
        cmd = (
            "python3 scripts/run_native_cfmid_casmi_subset.py "
            f"--outdir {FULL_OUTDIR} "
            f"--query-start {start} --query-limit {stop - start} "
            "--candidate-limit -1 --candidate-pool-policy first_n_plus_true "
            "--max-workers 1 --timeout-seconds 86400 --resume"
        )
        shard_rows.append(
            {
                "shard_id": shard_id,
                "query_start": start,
                "query_limit": stop - start,
                "candidate_rows": int(manifest.iloc[start:stop]["candidate_count"].sum()),
                "command": cmd,
            }
        )
        commands.append(f"echo 'Starting CFM-ID full shard {shard_id}'\n{cmd}\n")
    pd.DataFrame(shard_rows).to_csv(OUTDIR / "cfmid_full_supported_shards.csv", index=False)
    (OUTDIR / "run_all_shards_sequential.sh").write_text("#!/usr/bin/env bash\nset -euo pipefail\n\n" + "\n".join(commands), encoding="utf-8")

    extrap = pd.read_csv(ROOT / "results" / "cfmid_full_runtime_extrapolation_v1" / "cfmid_full_runtime_extrapolation.csv")
    audit = {
        "stage": "cfmid_full_casmi_run_manifest_v1",
        "status": "prepared_not_executed",
        "total_casmi_queries": int(len(spec)),
        "supported_queries": int(len(supported)),
        "unsupported_queries": int(len(unsupported)),
        "unsupported_adduct_counts": unsupported["prec_type"].value_counts().to_dict(),
        "total_supported_candidate_rows": int(manifest["candidate_count"].sum()),
        "shard_size": shard_size,
        "n_shards": int(math.ceil(len(manifest) / shard_size)),
        "full_outdir": str(FULL_OUTDIR),
        "runner": "scripts/run_native_cfmid_casmi_subset.py --candidate-limit -1",
        "runtime_extrapolation": extrap.to_dict(orient="records"),
        "completion_gate": "Full native CFM-ID CASMI metrics may be reported only after every supported query has a completed full_output_file with candidate_count scored rows; [M+Na]+ remains unsupported unless an appropriate CFM-ID model is added.",
    }
    (OUTDIR / "audit_summary.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# Full Native CFM-ID CASMI Run Manifest",
        "",
        "This package prepares, but does not execute, the long-running full native CFM-ID CASMI job.",
        "",
        f"- Supported queries: `{len(supported)}`",
        f"- Unsupported queries: `{len(unsupported)}`; counts: `{unsupported['prec_type'].value_counts().to_dict()}`",
        f"- Total supported candidate rows: `{int(manifest['candidate_count'].sum())}`",
        f"- Shards: `{audit['n_shards']}` of `{shard_size}` supported queries each",
        f"- Full output directory: `{FULL_OUTDIR}`",
        "",
        "Run `bash results/cfmid_full_casmi_run_manifest_v1/run_all_shards_sequential.sh` for a resumable sequential run, or dispatch rows from `cfmid_full_supported_shards.csv` manually on a scheduler.",
        "",
        audit["completion_gate"],
        "",
    ]
    (OUTDIR / "cfmid_full_casmi_run_manifest_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
