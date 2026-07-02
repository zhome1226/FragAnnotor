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

|   shard_id | adduct   |   candidate_start |   candidate_limit | status         | command                                                                                                                                                                                                                                           |
|-----------:|:---------|------------------:|------------------:|:---------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|        589 | [M+H]+   |             58900 |               100 | partial_cached | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 58900 --candidate-limit 100 --resume  |
|        590 | [M+H]+   |             59000 |               100 | partial_cached | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 59000 --candidate-limit 100 --resume  |
|       1372 | [M+H]+   |            137200 |               100 | partial_cached | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 137200 --candidate-limit 100 --resume |
|       1379 | [M+H]+   |            137900 |               100 | partial_cached | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 137900 --candidate-limit 100 --resume |
|       1563 | [M+H]+   |            156300 |               100 | partial_cached | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 156300 --candidate-limit 100 --resume |
|       1572 | [M+H]+   |            157200 |               100 | partial_cached | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 157200 --candidate-limit 100 --resume |
|       1648 | [M+H]+   |            164800 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 164800 --candidate-limit 100 --resume |
|       1649 | [M+H]+   |            164900 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 164900 --candidate-limit 100 --resume |
|       1650 | [M+H]+   |            165000 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165000 --candidate-limit 100 --resume |
|       1651 | [M+H]+   |            165100 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165100 --candidate-limit 100 --resume |
|       1652 | [M+H]+   |            165200 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165200 --candidate-limit 100 --resume |
|       1653 | [M+H]+   |            165300 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165300 --candidate-limit 100 --resume |
|       1654 | [M+H]+   |            165400 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165400 --candidate-limit 100 --resume |
|       1655 | [M+H]+   |            165500 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165500 --candidate-limit 100 --resume |
|       1656 | [M+H]+   |            165600 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165600 --candidate-limit 100 --resume |
|       1657 | [M+H]+   |            165700 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165700 --candidate-limit 100 --resume |
|       1658 | [M+H]+   |            165800 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165800 --candidate-limit 100 --resume |
|       1659 | [M+H]+   |            165900 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 165900 --candidate-limit 100 --resume |
|       1660 | [M+H]+   |            166000 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 166000 --candidate-limit 100 --resume |
|       1661 | [M+H]+   |            166100 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 166100 --candidate-limit 100 --resume |
|       1662 | [M+H]+   |            166200 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 166200 --candidate-limit 100 --resume |
|       1663 | [M+H]+   |            166300 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 166300 --candidate-limit 100 --resume |
|       1664 | [M+H]+   |            166400 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 166400 --candidate-limit 100 --resume |
|       1665 | [M+H]+   |            166500 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 166500 --candidate-limit 100 --resume |
|       1666 | [M+H]+   |            166600 |               100 | not_started    | python3 scripts/run_cfmid_precomputed_candidate_shard.py --outdir /home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1 --adduct '[M+H]+' --candidate-start 166600 --candidate-limit 100 --resume |

## [M+Na]+ Queries

Primary policy: report the 59 `[M+Na]+` CASMI queries as an unsupported adduct stratum for native CFM-ID. Do not convert them to `[M+H]+` for native CFM-ID metrics unless a validated conversion protocol and sodium-adduct model are added.

## MS2DeepScore

Full native MS2DeepScore ready: `False`.
Full CFM-ID + MS2DeepScore hybrid ready: `False`.
The hybrid can run only after the full CFM-ID candidate spectrum library and all supported-query coverage are complete.

## Harmonized ICEBERG/MassFormer/NEIMS

Use the same CASMI candidate set (`spec_df.pkl`, `cand_df.pkl`, `all_smiles.txt`) and the same Top-k/MRR/Tanimoto/formula metrics. Public notebook numbers remain external context only until these reruns complete.
