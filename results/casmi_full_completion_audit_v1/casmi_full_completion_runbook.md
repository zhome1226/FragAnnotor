# CASMI Full Completion Runbook

This runbook does not fabricate missing scores. It lists the exact gates still needed before full CASMI claims.

## CFM-ID Full Supported CASMI

For interactive or unstable sessions, run small resumable micro-batches:

```bash
python3 scripts/run_cfmid_precomputed_candidate_micro_batch.py --max-candidates 20 --max-range-len 20 --timeout-seconds 3600
```

For long server sessions, use the full shard runner:

Run all remaining candidate-spectrum shards first:

```bash
bash results/cfmid_precomputed_full_casmi_manifest_v1/run_candidate_spectrum_shards_sequential.sh
python3 scripts/summarize_cfmid_precomputed_full_progress.py
```

Then run query ranking shards:

```bash
bash results/cfmid_precomputed_full_casmi_manifest_v1/run_query_ranking_shards_after_spectra.sh
python3 scripts/summarize_cfmid_precomputed_full_progress.py
```

Report full native CFM-ID metrics only when `status == completed_full_supported`.

Next not-completed candidate-spectrum shards:

|   shard_id | adduct   |   candidate_start |   candidate_limit | status      | command                                                                                                                                                                                                                                          |
|-----------:|:---------|------------------:|------------------:|:------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|        150 | [M+H]+   |             15000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15000 --candidate-limit 100 --resume |
|        151 | [M+H]+   |             15100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15100 --candidate-limit 100 --resume |
|        152 | [M+H]+   |             15200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15200 --candidate-limit 100 --resume |
|        153 | [M+H]+   |             15300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15300 --candidate-limit 100 --resume |
|        154 | [M+H]+   |             15400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15400 --candidate-limit 100 --resume |
|        155 | [M+H]+   |             15500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15500 --candidate-limit 100 --resume |
|        156 | [M+H]+   |             15600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15600 --candidate-limit 100 --resume |
|        157 | [M+H]+   |             15700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15700 --candidate-limit 100 --resume |
|        158 | [M+H]+   |             15800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15800 --candidate-limit 100 --resume |
|        159 | [M+H]+   |             15900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 15900 --candidate-limit 100 --resume |
|        160 | [M+H]+   |             16000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16000 --candidate-limit 100 --resume |
|        161 | [M+H]+   |             16100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16100 --candidate-limit 100 --resume |
|        162 | [M+H]+   |             16200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16200 --candidate-limit 100 --resume |
|        163 | [M+H]+   |             16300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16300 --candidate-limit 100 --resume |
|        164 | [M+H]+   |             16400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16400 --candidate-limit 100 --resume |
|        165 | [M+H]+   |             16500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16500 --candidate-limit 100 --resume |
|        166 | [M+H]+   |             16600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16600 --candidate-limit 100 --resume |
|        167 | [M+H]+   |             16700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16700 --candidate-limit 100 --resume |
|        168 | [M+H]+   |             16800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16800 --candidate-limit 100 --resume |
|        169 | [M+H]+   |             16900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 16900 --candidate-limit 100 --resume |
|        170 | [M+H]+   |             17000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 17000 --candidate-limit 100 --resume |
|        171 | [M+H]+   |             17100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 17100 --candidate-limit 100 --resume |
|        172 | [M+H]+   |             17200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 17200 --candidate-limit 100 --resume |
|        173 | [M+H]+   |             17300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 17300 --candidate-limit 100 --resume |
|        174 | [M+H]+   |             17400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 17400 --candidate-limit 100 --resume |

## [M+Na]+ Queries

Primary policy: report the 59 `[M+Na]+` CASMI queries as an unsupported adduct stratum for native CFM-ID. Do not convert them to `[M+H]+` for native CFM-ID metrics unless a validated conversion protocol and sodium-adduct model are added.

## MS2DeepScore

Full native MS2DeepScore ready: `False`.
Full CFM-ID + MS2DeepScore hybrid ready: `False`.
The hybrid can run only after the full CFM-ID candidate spectrum library and all supported-query coverage are complete.

## Harmonized ICEBERG/MassFormer/NEIMS

Use the same CASMI candidate set (`spec_df.pkl`, `cand_df.pkl`, `all_smiles.txt`) and the same Top-k/MRR/Tanimoto/formula metrics. Public notebook numbers remain external context only until these reruns complete.
