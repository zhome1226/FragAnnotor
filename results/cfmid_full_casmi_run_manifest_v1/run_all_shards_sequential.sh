#!/usr/bin/env bash
set -euo pipefail

echo 'Starting CFM-ID full shard 0'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 0 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 1'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 5 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 2'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 10 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 3'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 15 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 4'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 20 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 5'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 25 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 6'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 30 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 7'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 35 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 8'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 40 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 9'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 45 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 10'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 50 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 11'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 55 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 12'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 60 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 13'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 65 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 14'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 70 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 15'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 75 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 16'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 80 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 17'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 85 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 18'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 90 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 19'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 95 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 20'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 100 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 21'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 105 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 22'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 110 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 23'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 115 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 24'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 120 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 25'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 125 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 26'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 130 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 27'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 135 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 28'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 140 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 29'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 145 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 30'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 150 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 31'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 155 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 32'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 160 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume

echo 'Starting CFM-ID full shard 33'
python3 scripts/run_native_cfmid_casmi_subset.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1 --query-start 165 --query-limit 5 --candidate-limit -1 --candidate-pool-policy first_n_plus_true --max-workers 1 --timeout-seconds 86400 --resume
