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
|        432 | [M+H]+   |             43200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43200 --candidate-limit 100 --resume |
|        433 | [M+H]+   |             43300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43300 --candidate-limit 100 --resume |
|        434 | [M+H]+   |             43400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43400 --candidate-limit 100 --resume |
|        435 | [M+H]+   |             43500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43500 --candidate-limit 100 --resume |
|        436 | [M+H]+   |             43600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43600 --candidate-limit 100 --resume |
|        437 | [M+H]+   |             43700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43700 --candidate-limit 100 --resume |
|        438 | [M+H]+   |             43800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43800 --candidate-limit 100 --resume |
|        439 | [M+H]+   |             43900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 43900 --candidate-limit 100 --resume |
|        440 | [M+H]+   |             44000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44000 --candidate-limit 100 --resume |
|        441 | [M+H]+   |             44100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44100 --candidate-limit 100 --resume |
|        442 | [M+H]+   |             44200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44200 --candidate-limit 100 --resume |
|        443 | [M+H]+   |             44300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44300 --candidate-limit 100 --resume |
|        444 | [M+H]+   |             44400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44400 --candidate-limit 100 --resume |
|        445 | [M+H]+   |             44500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44500 --candidate-limit 100 --resume |
|        446 | [M+H]+   |             44600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44600 --candidate-limit 100 --resume |
|        447 | [M+H]+   |             44700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44700 --candidate-limit 100 --resume |
|        448 | [M+H]+   |             44800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44800 --candidate-limit 100 --resume |
|        449 | [M+H]+   |             44900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 44900 --candidate-limit 100 --resume |
|        450 | [M+H]+   |             45000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 45000 --candidate-limit 100 --resume |
|        451 | [M+H]+   |             45100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 45100 --candidate-limit 100 --resume |
|        452 | [M+H]+   |             45200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 45200 --candidate-limit 100 --resume |
|        453 | [M+H]+   |             45300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 45300 --candidate-limit 100 --resume |
|        454 | [M+H]+   |             45400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 45400 --candidate-limit 100 --resume |
|        455 | [M+H]+   |             45500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 45500 --candidate-limit 100 --resume |
|        456 | [M+H]+   |             45600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 45600 --candidate-limit 100 --resume |

## [M+Na]+ Queries

Primary policy: report the 59 `[M+Na]+` CASMI queries as an unsupported adduct stratum for native CFM-ID. Do not convert them to `[M+H]+` for native CFM-ID metrics unless a validated conversion protocol and sodium-adduct model are added.

## MS2DeepScore

Full native MS2DeepScore ready: `False`.
Full CFM-ID + MS2DeepScore hybrid ready: `False`.
The hybrid can run only after the full CFM-ID candidate spectrum library and all supported-query coverage are complete.

## Harmonized ICEBERG/MassFormer/NEIMS

Use the same CASMI candidate set (`spec_df.pkl`, `cand_df.pkl`, `all_smiles.txt`) and the same Top-k/MRR/Tanimoto/formula metrics. Public notebook numbers remain external context only until these reruns complete.
