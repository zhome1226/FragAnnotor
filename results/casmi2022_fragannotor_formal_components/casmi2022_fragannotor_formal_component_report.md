# CASMI2022 FragAnnotor Formal Component-Score Package

This package reports an audited fixed component-score mode for CASMI2022. It uses real CASMI experimental peaks, candidate formulas, native SIRIUS formula scores, precursor/adduct mass consistency, and fixed common fragment/neutral-loss plausibility components.

## Main Result

- Queries: 229
- Candidate rows: 408249
- Top-1: 0.650655
- Top-5: 0.659389
- Top-10: 0.672489
- MRR: 0.658549

## Guardrail

This is not claimed as a CASMI-trained native neural FragAnnotor model. No CASMI labels were used for training or weight search. The fixed score formula is `0.65 * native SIRIUS formula plausibility + 0.20 * precursor mass consistency + 0.15 * common fragment/neutral-loss formula plausibility`.
