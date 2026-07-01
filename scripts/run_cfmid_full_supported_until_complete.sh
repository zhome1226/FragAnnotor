#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[cfmid-full] started at $(date -Is)"
echo "[cfmid-full] root: $ROOT"

echo "[cfmid-full] phase 1: candidate-spectrum shards"
bash results/cfmid_precomputed_full_casmi_manifest_v1/run_candidate_spectrum_shards_sequential.sh

echo "[cfmid-full] phase 2: summarize after candidate spectra"
python3 scripts/summarize_cfmid_precomputed_full_progress.py
python3 scripts/write_casmi_full_completion_audit.py

echo "[cfmid-full] phase 3: query-ranking shards"
bash results/cfmid_precomputed_full_casmi_manifest_v1/run_query_ranking_shards_after_spectra.sh

echo "[cfmid-full] phase 4: final summarize"
python3 scripts/summarize_cfmid_precomputed_full_progress.py
python3 scripts/write_casmi_full_completion_audit.py

echo "[cfmid-full] finished at $(date -Is)"
