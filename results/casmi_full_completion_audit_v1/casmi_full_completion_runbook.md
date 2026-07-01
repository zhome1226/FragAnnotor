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
|        545 | [M+H]+   |             54500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 54500 --candidate-limit 100 --resume |
|        546 | [M+H]+   |             54600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 54600 --candidate-limit 100 --resume |
|        550 | [M+H]+   |             55000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55000 --candidate-limit 100 --resume |
|        551 | [M+H]+   |             55100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55100 --candidate-limit 100 --resume |
|        552 | [M+H]+   |             55200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55200 --candidate-limit 100 --resume |
|        553 | [M+H]+   |             55300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55300 --candidate-limit 100 --resume |
|        554 | [M+H]+   |             55400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55400 --candidate-limit 100 --resume |
|        555 | [M+H]+   |             55500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55500 --candidate-limit 100 --resume |
|        556 | [M+H]+   |             55600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55600 --candidate-limit 100 --resume |
|        557 | [M+H]+   |             55700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55700 --candidate-limit 100 --resume |
|        558 | [M+H]+   |             55800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55800 --candidate-limit 100 --resume |
|        559 | [M+H]+   |             55900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 55900 --candidate-limit 100 --resume |
|        560 | [M+H]+   |             56000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56000 --candidate-limit 100 --resume |
|        561 | [M+H]+   |             56100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56100 --candidate-limit 100 --resume |
|        562 | [M+H]+   |             56200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56200 --candidate-limit 100 --resume |
|        563 | [M+H]+   |             56300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56300 --candidate-limit 100 --resume |
|        564 | [M+H]+   |             56400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56400 --candidate-limit 100 --resume |
|        565 | [M+H]+   |             56500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56500 --candidate-limit 100 --resume |
|        566 | [M+H]+   |             56600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56600 --candidate-limit 100 --resume |
|        567 | [M+H]+   |             56700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56700 --candidate-limit 100 --resume |
|        568 | [M+H]+   |             56800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56800 --candidate-limit 100 --resume |
|        569 | [M+H]+   |             56900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 56900 --candidate-limit 100 --resume |
|        570 | [M+H]+   |             57000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 57000 --candidate-limit 100 --resume |
|        571 | [M+H]+   |             57100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 57100 --candidate-limit 100 --resume |
|        572 | [M+H]+   |             57200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 57200 --candidate-limit 100 --resume |

## [M+Na]+ Queries

Primary policy: report the 59 `[M+Na]+` CASMI queries as an unsupported adduct stratum for native CFM-ID. Do not convert them to `[M+H]+` for native CFM-ID metrics unless a validated conversion protocol and sodium-adduct model are added.

## MS2DeepScore

Full native MS2DeepScore ready: `False`.
Full CFM-ID + MS2DeepScore hybrid ready: `False`.
The hybrid can run only after the full CFM-ID candidate spectrum library and all supported-query coverage are complete.

## Harmonized ICEBERG/MassFormer/NEIMS

Use the same CASMI candidate set (`spec_df.pkl`, `cand_df.pkl`, `all_smiles.txt`) and the same Top-k/MRR/Tanimoto/formula metrics. Public notebook numbers remain external context only until these reruns complete.
