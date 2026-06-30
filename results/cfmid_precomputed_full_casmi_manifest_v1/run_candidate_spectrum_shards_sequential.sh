#!/usr/bin/env bash
set -euo pipefail

OUTDIR='/home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1'
SHARDS='/home/zhome/ec_structure/github_export/FragAnnotor/results/cfmid_precomputed_full_casmi_manifest_v1/cfmid_precomputed_candidate_spectrum_shards.csv'
tail -n +2 "$SHARDS" | while IFS=, read -r shard_id adduct candidate_start candidate_limit candidate_count command status; do
  echo "Starting CFM-ID candidate-spectrum shard ${shard_id}: ${adduct} ${candidate_start}+${candidate_limit}"
  python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir "$OUTDIR" --adduct "$adduct" --candidate-start "$candidate_start" --candidate-limit "$candidate_limit" --resume
done
