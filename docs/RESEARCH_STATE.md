# FragAnnotor Research State

Last updated: `2026-07-11T08:03:00.552631+00:00`
Current audited commit: `65f3d562ccc7b699a2f050df7f93b85bbf330b83`

## Current Priority

Stage 2: generate the Section 3.1 CASMI2022 FragAnnotator-only manuscript package from the frozen fixed evidence-fusion definition.

## Frozen Manuscript Method

- Final config: `configs/fragannotator_manuscript_final.yaml`
- Model definition: `docs/FRAGANNOTATOR_FINAL_MODEL_DEFINITION.md`
- Final config audit: `outputs/manuscript_completion_v1/final_config_audit.json`
- Config SHA-256: `edf42951a62f169488ad53c4d8189cebef6ceaf8735ad6c6368081e9f3eeb63d`
- Definition bundle SHA-256: `7208d4740b5d8b8a0dded1b2d044f809b583685d7e03c33185ed56cfd8b2b0eb`
- Main method: fixed evidence-fusion candidate-ranking framework.
- Not main method: existing trained neural checkpoint; retain only as audit or negative-control evidence unless strict matched evidence proves superiority.

## Current Evidence State

- Stage 0 status audit generated under `outputs/manuscript_completion_v1/`.
- Stage 1 final FragAnnotator definition is frozen.
- Fixed evidence-fusion CASMI results available for `229` queries.
- Harmonized MassFormer last locally synced valid query rows: `102`; ICEBERG: `40`. Remote background runs must be rechecked before any 3.2 claim.
- Partial harmonized SOTA outputs are not manuscript-ready main-table evidence.
- NEIMS remains unavailable unless a validated checkpoint and wrapper are confirmed.
