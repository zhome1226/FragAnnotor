# FragAnnotor Research State

Last updated: `2026-07-11T08:42:44.065070+00:00`
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
- NEIMS remains unavailable unless a validated checkpoint and wrapper are confirmed.
