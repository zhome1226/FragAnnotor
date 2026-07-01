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
|        199 | [M+H]+   |             19900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 19900 --candidate-limit 100 --resume |
|        220 | [M+H]+   |             22000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22000 --candidate-limit 100 --resume |
|        221 | [M+H]+   |             22100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22100 --candidate-limit 100 --resume |
|        222 | [M+H]+   |             22200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22200 --candidate-limit 100 --resume |
|        223 | [M+H]+   |             22300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22300 --candidate-limit 100 --resume |
|        224 | [M+H]+   |             22400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22400 --candidate-limit 100 --resume |
|        225 | [M+H]+   |             22500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22500 --candidate-limit 100 --resume |
|        226 | [M+H]+   |             22600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22600 --candidate-limit 100 --resume |
|        227 | [M+H]+   |             22700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22700 --candidate-limit 100 --resume |
|        228 | [M+H]+   |             22800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22800 --candidate-limit 100 --resume |
|        229 | [M+H]+   |             22900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 22900 --candidate-limit 100 --resume |
|        230 | [M+H]+   |             23000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23000 --candidate-limit 100 --resume |
|        231 | [M+H]+   |             23100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23100 --candidate-limit 100 --resume |
|        232 | [M+H]+   |             23200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23200 --candidate-limit 100 --resume |
|        233 | [M+H]+   |             23300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23300 --candidate-limit 100 --resume |
|        234 | [M+H]+   |             23400 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23400 --candidate-limit 100 --resume |
|        235 | [M+H]+   |             23500 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23500 --candidate-limit 100 --resume |
|        236 | [M+H]+   |             23600 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23600 --candidate-limit 100 --resume |
|        237 | [M+H]+   |             23700 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23700 --candidate-limit 100 --resume |
|        238 | [M+H]+   |             23800 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23800 --candidate-limit 100 --resume |
|        239 | [M+H]+   |             23900 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 23900 --candidate-limit 100 --resume |
|        240 | [M+H]+   |             24000 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 24000 --candidate-limit 100 --resume |
|        241 | [M+H]+   |             24100 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 24100 --candidate-limit 100 --resume |
|        242 | [M+H]+   |             24200 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 24200 --candidate-limit 100 --resume |
|        243 | [M+H]+   |             24300 |               100 | not_started | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 24300 --candidate-limit 100 --resume |

## [M+Na]+ Queries

Primary policy: report the 59 `[M+Na]+` CASMI queries as an unsupported adduct stratum for native CFM-ID. Do not convert them to `[M+H]+` for native CFM-ID metrics unless a validated conversion protocol and sodium-adduct model are added.

## MS2DeepScore

Full native MS2DeepScore ready: `False`.
Full CFM-ID + MS2DeepScore hybrid ready: `False`.
The hybrid can run only after the full CFM-ID candidate spectrum library and all supported-query coverage are complete.

## Harmonized ICEBERG/MassFormer/NEIMS

Use the same CASMI candidate set (`spec_df.pkl`, `cand_df.pkl`, `all_smiles.txt`) and the same Top-k/MRR/Tanimoto/formula metrics. Public notebook numbers remain external context only until these reruns complete.
