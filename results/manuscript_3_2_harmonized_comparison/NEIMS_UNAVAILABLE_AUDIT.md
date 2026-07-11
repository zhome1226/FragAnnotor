# NEIMS Availability Audit for Harmonized CASMI2022 Comparison

Audit timestamp: 2026-07-11T08:55:00Z

## Decision

NEIMS is not included in the manuscript Section 3.2 harmonized main comparison table at this stage.

The current local and remote environments do not contain a validated NEIMS pretrained checkpoint plus an inference wrapper that can generate candidate-level spectra for the frozen CASMI2022 matched 170-query candidate set.

## Evidence Checked

- Local FragAnnotor repository search for NEIMS files, wrappers, checkpoints, and prior outputs.
- Remote FragAnnotor repository search under `/home/zhome/fragannotor_remote/FragAnnotor`.
- Remote external model tree search under `/home/zhome/ec_structure/external_ms_models`.
- `ms-pred` and `ms-pred-iceberg-2024` vendor trees for NEIMS-related configs and prediction scripts.

## Findings

The remote model tree contains NEIMS-related training configuration templates:

- `/home/zhome/ec_structure/external_ms_models/vendor/ms-pred/configs/neims_ffn/ffn_baseline_canopus.yaml`
- `/home/zhome/ec_structure/external_ms_models/vendor/ms-pred/configs/neims_ffn/ffn_baseline_nist.yaml`
- `/home/zhome/ec_structure/external_ms_models/vendor/ms-pred/configs/neims_gnn/gnn_baseline_canopus.yaml`
- `/home/zhome/ec_structure/external_ms_models/vendor/ms-pred/configs/neims_gnn/gnn_baseline_nist.yaml`
- Equivalent config files in `/home/zhome/ec_structure/external_ms_models/vendor/ms-pred-iceberg-2024/configs/`

The same vendor trees contain generic FFN/GNN prediction scripts, but the audit did not find a NEIMS-specific trained checkpoint directory, run artifact, or model weights corresponding to those NEIMS configurations.

The checkpoint search found ICEBERG, MassFormer, MS2DeepScore, and FIORA model artifacts, but no NEIMS checkpoint with traceable provenance:

- ICEBERG checkpoints: `canopus_iceberg_generate.ckpt`, `canopus_iceberg_score.ckpt`
- MassFormer checkpoint: `checkpoint_best_pcqm4mv2.pt`
- MS2DeepScore files: `embedding_evaluator.pt`, `ms2deepscore_model.pt`
- FIORA model files

No NEIMS output directory or previous harmonized candidate-level NEIMS query results were found.

## Manuscript Guardrail

Do not fabricate NEIMS results, do not enter placeholder values in the main table, and do not label another FFN/GNN surrogate as NEIMS unless a validated NEIMS checkpoint and compatible spectrum-prediction wrapper are added and audited.

NEIMS can be mentioned only in a reproducibility or availability audit as unavailable in the current environment.

## Recovery Requirements

NEIMS can be added later only if all of the following are available:

- A traceable pretrained NEIMS checkpoint.
- The corresponding model configuration.
- A compatible inference wrapper that accepts candidate SMILES or structures.
- Clear output semantics for predicted MS/MS spectra.
- A validation smoke test on a small frozen candidate subset.
- Harmonized scoring on the exact matched 170-query CASMI2022 candidate set.

Until then, Section 3.2 should exclude NEIMS from the harmonized main comparison table.
