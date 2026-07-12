# FragAnnotor Research State

Last updated: `2026-07-12T01:05:32.731801+00:00`
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

Last snapshot UTC: 2026-07-12T01:05:32.731801+00:00

| Model | Valid supported queries | Query rows | Failed candidate predictions | Status |
|---|---:|---:|---:|---|
| MassFormer | 170/170 | 170 | 1481 | all matched query rows complete; candidate-level prediction failures retained and audited |
| ICEBERG | 60/170 | 60 | 71 | running resumable shards `shard_061_065` and `shard_066_070` remotely |

MassFormer now has all 170 frozen matched CASMI [M+H]+ query rows available in `results/harmonized_sota_candidate_reruns_v1/massformer/`, but its merged summary remains guarded because 1,481 candidate spectra failed prediction across otherwise rank-valid query rows. ICEBERG remains partial and cannot enter the Section 3.2 main comparison table until it reaches the frozen 170-query set or has a completed unrecoverable-failure audit.

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

