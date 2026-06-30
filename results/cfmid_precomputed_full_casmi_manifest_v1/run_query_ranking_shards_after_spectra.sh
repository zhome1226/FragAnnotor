#!/usr/bin/env bash
set -euo pipefail

OUTDIR='/home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1'
SHARDS='/home/zhome/ec_structure/github_export/FragAnnotor/results/cfmid_precomputed_full_casmi_manifest_v1/cfmid_precomputed_query_ranking_shards.csv'
tail -n +2 "$SHARDS" | while IFS=, read -r shard_id query_start query_limit candidate_rows command status; do
  echo "Starting CFM-ID precomputed query shard ${shard_id}: ${query_start}+${query_limit}"
  python3 scripts/run_cfmid_precomputed_query_shard.py --outdir "$OUTDIR" --query-start "$query_start" --query-limit "$query_limit" --resume
done
