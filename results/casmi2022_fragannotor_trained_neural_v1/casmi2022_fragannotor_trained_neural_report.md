# CASMI2022 FragAnnotor Trained Neural Checkpoint Report

Frozen checkpoint: `/home/zhome/ec_structure/pollutant_transform_pretraining/outputs/calibration_aware_model_v1/model_runs/calibration_weighted_model/checkpoints/best_model.pt`

This report ranks CASMI2022 candidates by cosine similarity between the measured CASMI MS/MS vector and the spectrum vector predicted by a trained FragAnnotor neural checkpoint. The script does not train, tune weights, or select checkpoints on CASMI.

## Result

- Queries: 229
- Candidate rows: 408249
- Top-1: 0.008734
- Top-5: 0.013100
- Top-10: 0.026201
- MRR: 0.017260
- Mean Top-1 Tanimoto: 0.113066
- Molecular formula accuracy: 0.462882

## Leakage Guardrail

Training-pair overlap with CASMI canonical SMILES: `False`.

## Scope

This is the formal trained neural CASMI report for the frozen checkpoint above. It is separate from the previous fixed component-score CASMI mode and should not be described as trained or tuned on CASMI.
