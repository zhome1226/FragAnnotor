#!/usr/bin/env python3
"""Import completed complete-query CFM-ID spectra into the full-run cache.

The full precomputed CASMI pipeline expects per-candidate plain spectrum files
under results/casmi2022_cfmid_native_precomputed_full_v1/candidate_spectra_cache.
Complete-query subset runs already generated native CFM-ID spectra for selected
queries. This script copies those spectra into the full cache and writes a
small provenance table; the bulky cache files remain ignored by Git.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from run_cfmid_precomputed_candidate_shard import adduct_slug


ROOT = Path(__file__).resolve().parents[1]
SUBSET_DIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_complete_query_subset_v1"
FULL_OUTDIR = ROOT / "results" / "casmi2022_cfmid_native_precomputed_full_v1"
IMPORT_OUTDIR = FULL_OUTDIR / "complete_query_subset_cache_import_v1"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    IMPORT_OUTDIR.mkdir(parents=True, exist_ok=True)
    query_results_path = SUBSET_DIR / "casmi2022_cfmid_native_precomputed_complete_query_subset_query_results.csv"
    if not query_results_path.exists():
        raise SystemExit(f"Missing complete-query subset query results: {query_results_path}")

    query_df = pd.read_csv(query_results_path)
    completed = query_df[query_df["status"].astype(str).isin(["completed", "completed_cached", "completed_ranked"])].copy()
    rows: list[dict[str, Any]] = []
    for _, query in completed.iterrows():
        query_id = str(query["query_id"])
        adduct = str(query["adduct"])
        slug = adduct_slug(adduct)
        work_dir = SUBSET_DIR / "work" / f"query_{query_id}"
        plain_dir = work_dir / "plain_candidate_spectra"
        if not plain_dir.exists():
            rows.append(
                {
                    "query_id": query_id,
                    "adduct": adduct,
                    "candidate_mol_id": "",
                    "status": "missing_plain_candidate_spectra_dir",
                    "source_file": str(plain_dir),
                    "target_file": "",
                }
            )
            continue
        for source in sorted(plain_dir.glob("*.txt")):
            candidate_mol_id = source.stem
            target = FULL_OUTDIR / "candidate_spectra_cache" / slug / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            status = "completed_cached" if target.exists() and target.stat().st_size > 0 else "imported"
            if status == "imported":
                shutil.copy2(source, target)
            rows.append(
                {
                    "query_id": query_id,
                    "adduct": adduct,
                    "candidate_mol_id": candidate_mol_id,
                    "status": status,
                    "source_file": str(source),
                    "target_file": str(target),
                }
            )

    import_df = pd.DataFrame(rows)
    import_df.to_csv(IMPORT_OUTDIR / "complete_query_subset_cache_import.csv", index=False)
    completed_rows = import_df[import_df["status"].astype(str).isin(["imported", "completed_cached"])]
    audit = {
        "stage": "cfmid_complete_query_subset_cache_import_v1",
        "status": "completed" if not completed_rows.empty else "no_completed_candidate_spectra_imported",
        "source_subset_dir": str(SUBSET_DIR),
        "target_full_outdir": str(FULL_OUTDIR),
        "source_queries": sorted(completed["query_id"].astype(str).tolist()),
        "candidate_spectrum_rows": int(len(import_df)),
        "imported_or_cached_candidate_spectra": int(len(completed_rows)),
        "unique_imported_or_cached_candidate_spectra": int(completed_rows["candidate_mol_id"].astype(str).nunique())
        if not completed_rows.empty
        else 0,
        "claim_guardrail": "This imports selected complete-query CFM-ID spectra into the full-run cache only; it does not complete full CASMI CFM-ID scoring.",
    }
    write_json(IMPORT_OUTDIR / "audit_summary.json", audit)
    report = [
        "# CFM-ID Complete-Query Subset Cache Import",
        "",
        audit["claim_guardrail"],
        "",
        f"- Source queries: `{audit['source_queries']}`",
        f"- Imported/cached candidate spectra rows: `{audit['imported_or_cached_candidate_spectra']}`",
        f"- Unique candidate spectra: `{audit['unique_imported_or_cached_candidate_spectra']}`",
        "",
    ]
    (IMPORT_OUTDIR / "complete_query_subset_cache_import_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
