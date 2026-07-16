# FragAnnotor Research State

Last updated: `2026-07-12T01:15:02.098800+00:00`
Current audited commit: `65f3d562ccc7b699a2f050df7f93b85bbf330b83`

## Current Priority

Continue MassFormer and ICEBERG remote shards until the matched 170-query Section 3.2 comparison is complete or has a completed failure audit.

## Frozen Manuscript Method

- Final config: `configs/fragannotator_manuscript_final.yaml`
- Model definition: `docs/FRAGANNOTATOR_FINAL_MODEL_DEFINITION.md`
- Final config audit: `outputs/manuscript_completion_v1/final_config_audit.json`
- Config SHA-256: `edf42951a62f169488ad53c4d8189cebef6ceaf8735ad6c6368081e9f3eeb63d`
- Main method: fixed evidence-fusion candidate-ranking framework.
- Not main method: existing trained neural checkpoint; retain only as audit or negative-control evidence unless strict matched evidence proves superiority.

## Section 3.1 CASMI2022 FragAnnotator-Only Package

- Status: manuscript-ready package completed and pushed.
- Output directory: `results/manuscript_3_1_casmi_overall/`
- Queries: `229`
- Top-1: `0.650655`
- Top-5: `0.659389`
- Top-10: `0.672489`
- MRR: `0.658549`

## Section 3.2 Matched Comparison Inputs

- Status: matched 170-query manifest frozen; final main comparison still pending ICEBERG/MassFormer completion and NEIMS audit.
- Output directory: `results/manuscript_3_2_harmonized_comparison/`
- Matched queries: `170`
- Matched FragAnnotator Top-1/MRR: `0.629412` / `0.633770`
- Matched SIRIUS formula-only Top-1/MRR: `0.694118` / `0.697199`
- Matched CFM-ID Top-1/MRR: `0.052941` / `0.094392`
- Matched CFM-ID-generated spectra + MS2DeepScore hybrid Top-1/MRR: `0.000000` / `0.019401`

## Current Evidence State

- Stage 0 status audit generated under `outputs/manuscript_completion_v1/`.
- Stage 1 final FragAnnotator definition is frozen.
- Stage 2 / Section 3.1 FragAnnotator-only package is complete.
- Stage 3.2 matched input manifest is frozen with available matched outputs for FragAnnotator, SIRIUS formula-only, native CFM-ID, and CFM-ID-generated candidate spectra + MS2DeepScore similarity hybrid.
- Harmonized MassFormer and ICEBERG remain partial/running remotely; partial outputs are not manuscript-ready main-table evidence.
- NEIMS was audited and remains unavailable: NEIMS config templates exist in the remote `ms-pred` vendor trees, but no traceable pretrained NEIMS checkpoint or validated candidate-level inference wrapper was found. It must be excluded from the Section 3.2 main table unless a checkpoint/wrapper is later supplied and audited.

## Latest Harmonized SOTA Progress

- Harmonized SOTA progress snapshot `2026-07-11T08:48:11.039563+00:00`: MassFormer `109/170`, ICEBERG `50/170`. Partial outputs are not manuscript-ready main-table evidence.

<!-- manuscript_completion_harmonized_sota_progress -->

### Harmonized SOTA candidate rerun progress

Last snapshot UTC: 2026-07-12T02:38:53+00:00

| Model | Valid supported queries | Query rows | Failed candidate predictions | Status |
|---|---:|---:|---:|---|
| MassFormer | 170/170 | 170 | 1481 | all matched query rows complete; candidate-level prediction failures retained and audited |
| ICEBERG | 65/170 | 65 | 80 | running 21 resumable ICEBERG controllers remotely |

MassFormer now has all 170 frozen matched CASMI [M+H]+ query rows available in `results/harmonized_sota_candidate_reruns_v1/massformer/`, but its merged summary remains guarded because 1,481 candidate spectra failed prediction across otherwise rank-valid query rows. ICEBERG remains partial and cannot enter the Section 3.2 main comparison table until it reaches the frozen 170-query set or has a completed unrecoverable-failure audit.

## ICEBERG GPU Acceleration Audit

- Status: GPU mode is not usable with the currently installed `ms-pred-iceberg-2024` vendor script.
- Evidence: running `predict_smis.py --gpu` reaches `assert not kwargs["gpu"]` in the vendor code and exits with `AssertionError`.
- Action taken: stopped the failed GPU-resume attempt and restarted `shard_061_065` and `shard_066_070` in CPU resumable mode.
- Guardrail: do not restart ICEBERG with `--gpu` unless the vendor inference code is patched and validated with a smoke test that emits prediction JSON.

## NEIMS Availability Audit

- Status: unavailable for Section 3.2 main comparison.
- Audit file: `results/manuscript_3_2_harmonized_comparison/NEIMS_UNAVAILABLE_AUDIT.md`
- Reason: NEIMS-related config templates exist, but no validated pretrained checkpoint or compatible harmonized inference wrapper was found locally or on the remote server.
- Guardrail: do not fabricate NEIMS results and do not substitute a metadata/fallback/surrogate model as NEIMS.

## 2026-07-11 Harmonized SOTA Rerun Progress Snapshot

- MassFormer harmonized rerun: 129/170 supported CASMI queries completed; shard_126_135 is running remotely.
- ICEBERG harmonized rerun: 54/170 supported CASMI queries completed; remote shard_051_055 and shard_056_060 controllers are still running.
- Long-running orphaned `bash -c /usr/lib/openssh/sftp-server` processes were terminated on the remote server to release CPU/memory; active FragAnnotor controllers were not stopped.
- Section 3.2 remains not manuscript-ready until ICEBERG and MassFormer reach the frozen 170-query matched set or produce auditable unrecoverable failures.

<!-- manuscript_completion_status -->

## FragAnnotor Manuscript Completion Status

Last updated: 2026-07-11T18:22:29.216139+00:00

Current stage: Section 3.2 harmonized SOTA reruns in progress. The final FragAnnotator definition is frozen as fixed evidence fusion; NEIMS is audited unavailable unless a validated checkpoint/wrapper is later found.

- MassFormer: 166/170 supported queries completed or auditable partial-prediction failures; failed candidate predictions: 1481; latest synced query: 225 (partial_prediction_failures, shard_166_170). Active remote shard: shard_166_170.
- ICEBERG: 58/170 supported queries completed or auditable partial-prediction failures; failed candidate predictions: 69; latest synced query: 84 (completed, shard_056_060). Active remote shards: shard_051_055 and shard_056_060.
- Manuscript guardrail: partial ICEBERG/MassFormer metrics must not enter the final main comparison table; CFM-ID + MS2DeepScore must be labeled as CFM-ID-generated candidate spectra + MS2DeepScore similarity hybrid.
- 2026-07-12T01:50:46.221852+00:00: ICEBERG harmonized rerun advanced to 61/170 query rows on the matched CASMI set; failed candidate predictions currently 71. Newest synced shard counts: {'shard_001_005': 5, 'shard_006_010': 5, 'shard_011_015': 5, 'shard_016_020': 5, 'shard_021_025': 5, 'shard_026_030': 5, 'shard_031_035': 5, 'shard_036_040': 5, 'shard_041_045': 5, 'shard_046_050': 5, 'shard_051_055': 5, 'shard_056_060': 5, 'shard_106_110': 1}. Section 3.2 remains not manuscript-ready until ICEBERG reaches 170/170 or has an auditable unrecoverable failure list.
- 2026-07-12T02:38:53+00:00: ICEBERG harmonized rerun advanced to 65/170 query rows on the matched CASMI set; failed candidate predictions currently 80. Newly synced one-query shard outputs: `shard_066_070`, `shard_101_105`, `shard_111_115`, and `shard_156_160`. Remote ICEBERG controllers and vendor predictors remain running in CPU resumable mode; GPU remains unused because the current vendor ICEBERG script asserts out when `--gpu` is enabled.

<!-- manuscript_3_2_harmonized_comparison -->

## Section 3.2 Harmonized Comparison Frozen

Last updated: 2026-07-16T03:23:01+00:00

- Status: manuscript-ready Section 3.2 harmonized comparison package generated and verified on `manuscript_3_2_matched_170_v1`.
- Output directory: `results/manuscript_3_2_harmonized_comparison/`
- Matched queries: `170`
- Main summary: `harmonized_model_summary.csv`
- Query-level table: `harmonized_query_results.csv`
- Pairwise comparison: `pairwise_rank_comparison.csv`
- Paired bootstrap differences: `paired_bootstrap_differences.csv`
- Report: `comparison_report.md`

| Model | Top-1 | Top-5 | Top-10 | MRR | Median true rank | Failure audit |
|---|---:|---:|---:|---:|---:|---|
| FragAnnotator | `0.629412` | `0.635294` | `0.641176` | `0.633770` | `1.0` | `0` failed candidate predictions; status `completed` |
| SIRIUS formula-only | `0.694118` | `0.700000` | `0.705882` | `0.697199` | `1.0` | `0` failed candidate predictions; status `completed` |
| CFM-ID | `0.052941` | `0.135294` | `0.176471` | `0.094392` | `169.0` | `0` failed candidate predictions; status `completed` |
| CFM-ID-generated spectra + MS2DeepScore similarity hybrid | `0.000000` | `0.029412` | `0.041176` | `0.019401` | `456.0` | `0` failed candidate predictions; status `completed` |
| ICEBERG | `0.005882` | `0.147059` | `0.182353` | `0.064948` | `117.0` | `376` failed candidate predictions; status `completed_with_candidate_prediction_failures` |
| MassFormer | `0.005882` | `0.011765` | `0.011765` | `0.013360` | `826.0` | `1481` failed candidate predictions; status `completed_with_candidate_prediction_failures` |

Guardrails:

- FragAnnotator is the frozen fixed evidence-fusion candidate-ranking framework, not a validated trained neural model.
- CFM-ID-generated spectra + MS2DeepScore similarity hybrid is not a native MS2DeepScore benchmark.
- ICEBERG and MassFormer are included with candidate-level prediction-failure audits.
- NEIMS is excluded from the main comparison because no reliable checkpoint/wrapper was available.
- These 170-query metrics must not be mixed with Section 3.1 229-query metrics without explicit labeling.
