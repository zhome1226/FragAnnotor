#!/usr/bin/env python3
"""Prepare a resumable full native CFM-ID CASMI run using precomputed spectra.

This manifest separates the expensive candidate spectrum prediction step from
the fast `cfm-id-precomputed` query-ranking step. It does not execute the full
job.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASMI_DIR = ROOT / "data" / "proc" / "casmi_2022"
MODEL_ROOT = Path("/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm-pretrained-models/cfmid4")
OUTDIR = ROOT / "results" / "cfmid_precomputed_full_casmi_manifest_v1"
RUN_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    spec = pd.read_pickle(CASMI_DIR / "spec_df.pkl")
    cand = pd.read_pickle(CASMI_DIR / "cand_df.pkl")
    model_adducts = sorted(p.name for p in MODEL_ROOT.iterdir() if p.is_dir())
    supported = spec[spec["prec_type"].astype(str).isin(model_adducts)].reset_index(drop=True).copy()
    unsupported = spec[~spec["prec_type"].astype(str).isin(model_adducts)].copy()

    counts = cand.groupby("query_mol_id")["candidate_mol_id"].size()
    query_rows = []
    for supported_index, row in supported.iterrows():
        query_mol_id = int(row["mol_id"])
        query_rows.append(
            {
                "supported_index": int(supported_index),
                "spec_id": str(row["spec_id"]),
                "query_mol_id": query_mol_id,
                "adduct": str(row["prec_type"]),
                "precursor_mz": float(row["prec_mz"]),
                "candidate_count": int(counts.get(query_mol_id, 0)),
                "rank_output_file": str(RUN_OUTDIR / "work" / f"query_{row['spec_id']}" / f"cfmid_precomputed_ranked_{row['spec_id']}.txt"),
                "status": "pending_candidate_spectra",
            }
        )
    query_manifest = pd.DataFrame(query_rows)
    query_manifest.to_csv(OUTDIR / "cfmid_precomputed_supported_query_manifest.csv", index=False)
    supported_candidate_row_count = int(query_manifest["candidate_count"].sum()) if not query_manifest.empty else 0

    unique_rows = []
    for adduct, adduct_spec in supported.groupby("prec_type"):
        adduct_query_ids = set(adduct_spec["mol_id"].astype(int))
        adduct_candidate_rows = int(sum(int(counts.get(int(mol_id), 0)) for mol_id in adduct_spec["mol_id"].astype(int)))
        adduct_candidate_ids = (
            cand[cand["query_mol_id"].astype(int).isin(adduct_query_ids)]["candidate_mol_id"]
            .astype(int)
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        unique_rows.append(
            {
                "adduct": adduct,
                "supported_queries": int(len(adduct_spec)),
                "candidate_rows": adduct_candidate_rows,
                "unique_candidate_mol_ids": int(len(adduct_candidate_ids)),
                "candidate_reuse_factor": float(
                    adduct_candidate_rows / len(adduct_candidate_ids)
                )
                if adduct_candidate_ids
                else 0.0,
            }
        )
    unique_summary = pd.DataFrame(unique_rows)
    unique_summary.to_csv(OUTDIR / "cfmid_precomputed_unique_candidate_summary.csv", index=False)

    candidate_shard_size = 100
    candidate_shards = []
    shard_id = 0
    for adduct, adduct_spec in supported.groupby("prec_type"):
        adduct_query_ids = set(adduct_spec["mol_id"].astype(int))
        unique_count = int(
            cand[cand["query_mol_id"].astype(int).isin(adduct_query_ids)]["candidate_mol_id"].astype(int).nunique()
        )
        for start in range(0, unique_count, candidate_shard_size):
            limit = min(candidate_shard_size, unique_count - start)
            cmd = (
                "python3 scripts/run_cfmid_precomputed_candidate_shard.py "
                f"--outdir {RUN_OUTDIR} --adduct '{adduct}' "
                f"--candidate-start {start} --candidate-limit {limit} --resume"
            )
            candidate_shards.append(
                {
                    "shard_id": shard_id,
                    "adduct": adduct,
                    "candidate_start": start,
                    "candidate_limit": limit,
                    "candidate_count": limit,
                    "command": cmd,
                    "status": "pending",
                }
            )
            shard_id += 1
    pd.DataFrame(candidate_shards).to_csv(OUTDIR / "cfmid_precomputed_candidate_spectrum_shards.csv", index=False)

    query_shard_size = 5
    query_shards = []
    commands = []
    for q_shard_id, start in enumerate(range(0, len(query_manifest), query_shard_size)):
        stop = min(start + query_shard_size, len(query_manifest))
        cmd = (
            "python3 scripts/run_cfmid_precomputed_query_shard.py "
            f"--outdir {RUN_OUTDIR} --query-start {start} --query-limit {stop - start} --resume"
        )
        query_shards.append(
            {
                "shard_id": q_shard_id,
                "query_start": start,
                "query_limit": stop - start,
                "candidate_rows": int(query_manifest.iloc[start:stop]["candidate_count"].sum()),
                "command": cmd,
                "status": "pending_candidate_spectra",
            }
        )
        commands.append(f"echo 'Starting CFM-ID precomputed query shard {q_shard_id}'\n{cmd}\n")
    pd.DataFrame(query_shards).to_csv(OUTDIR / "cfmid_precomputed_query_ranking_shards.csv", index=False)

    (OUTDIR / "run_candidate_spectrum_shards_sequential.sh").write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                f"OUTDIR='{RUN_OUTDIR}'",
                f"SHARDS='{OUTDIR / 'cfmid_precomputed_candidate_spectrum_shards.csv'}'",
                "tail -n +2 \"$SHARDS\" | while IFS=, read -r shard_id adduct candidate_start candidate_limit candidate_count command status; do",
                "  echo \"Starting CFM-ID candidate-spectrum shard ${shard_id}: ${adduct} ${candidate_start}+${candidate_limit}\"",
                "  python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir \"$OUTDIR\" --adduct \"$adduct\" --candidate-start \"$candidate_start\" --candidate-limit \"$candidate_limit\" --resume",
                "done",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (OUTDIR / "run_query_ranking_shards_after_spectra.sh").write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                f"OUTDIR='{RUN_OUTDIR}'",
                f"SHARDS='{OUTDIR / 'cfmid_precomputed_query_ranking_shards.csv'}'",
                "tail -n +2 \"$SHARDS\" | while IFS=, read -r shard_id query_start query_limit candidate_rows command status; do",
                "  echo \"Starting CFM-ID precomputed query shard ${shard_id}: ${query_start}+${query_limit}\"",
                "  python3 scripts/run_cfmid_precomputed_query_shard.py --outdir \"$OUTDIR\" --query-start \"$query_start\" --query-limit \"$query_limit\" --resume",
                "done",
                "",
            ]
        ),
        encoding="utf-8",
    )

    audit = {
        "stage": "cfmid_precomputed_full_casmi_manifest_v1",
        "status": "prepared_not_executed",
        "total_casmi_queries": int(len(spec)),
        "supported_queries": int(len(supported)),
        "unsupported_queries": int(len(unsupported)),
        "unsupported_adduct_counts": unsupported["prec_type"].value_counts().to_dict(),
        "supported_candidate_rows": supported_candidate_row_count,
        "unique_candidate_mol_ids_total_by_adduct": unique_summary.to_dict(orient="records"),
        "candidate_shard_size": candidate_shard_size,
        "candidate_spectrum_shards": int(len(candidate_shards)),
        "query_shard_size": query_shard_size,
        "query_ranking_shards": int(math.ceil(len(query_manifest) / query_shard_size)),
        "run_outdir": str(RUN_OUTDIR),
        "completion_gate": "Report full native CFM-ID CASMI metrics only after every candidate spectrum shard and every supported query-ranking shard completes; [M+Na]+ remains unsupported unless a compatible CFM-ID model is added.",
    }
    (OUTDIR / "audit_summary.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# CFM-ID Precomputed Full CASMI Manifest",
        "",
        "This package prepares a faster native CFM-ID CASMI path by caching candidate spectra before ranking.",
        "",
        f"- Supported queries: `{len(supported)}`",
        f"- Unsupported queries: `{len(unsupported)}`; counts: `{unsupported['prec_type'].value_counts().to_dict()}`",
        f"- Supported candidate rows: `{supported_candidate_row_count}`",
        f"- Candidate-spectrum shards: `{len(candidate_shards)}` of `{candidate_shard_size}` unique candidates each",
        f"- Query-ranking shards: `{audit['query_ranking_shards']}` of `{query_shard_size}` supported queries each",
        f"- Run output directory: `{RUN_OUTDIR}`",
        "",
        "Run candidate-spectrum shards first, then query-ranking shards, then `scripts/summarize_cfmid_precomputed_full_progress.py`.",
        "",
        audit["completion_gate"],
        "",
    ]
    (OUTDIR / "cfmid_precomputed_full_casmi_manifest_report.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
