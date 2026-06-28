# Benchmark Report

This report compares FragAnnotor against CFM-ID, SIRIUS, and MS2DeepScore through the unified `BaseAnnotator.predict()` interface.

## Dataset Status

- `CASMI2022`: `available`
  - Queries: 229
- `PFAS`: `available`
  - Queries: 64

## Results

| dataset   | model        | status    |   n_queries |   top1_accuracy |   top5_accuracy |   top10_accuracy |   mean_reciprocal_rank |   mean_top1_tanimoto |   molecular_formula_accuracy | notes   |
|:----------|:-------------|:----------|------------:|----------------:|----------------:|-----------------:|-----------------------:|---------------------:|-----------------------------:|:--------|
| CASMI2022 | FragAnnotor  | completed |         229 |      0          |      0.00436681 |       0.0131004  |             0.00482266 |            0.0913518 |                    0.0873362 |         |
| CASMI2022 | CFM-ID       | completed |         229 |      0.00436681 |      0.0174672  |       0.0218341  |             0.0108374  |            0.0945282 |                    0.0917031 |         |
| CASMI2022 | SIRIUS       | completed |         229 |      0          |      0          |       0.00873362 |             0.0034754  |            0.0922272 |                    0.126638  |         |
| CASMI2022 | MS2DeepScore | completed |         229 |      0          |      0          |       0.00436681 |             0.00332422 |            0.0967545 |                    0.296943  |         |
| PFAS      | FragAnnotor  | completed |          64 |      0.328125   |      0.71875    |       0.828125   |             0.502844   |            0.461697  |                    0.34375   |         |
| PFAS      | CFM-ID       | completed |          64 |      0.328125   |      0.65625    |       0.75       |             0.466127   |            0.447842  |                    0.34375   |         |
| PFAS      | SIRIUS       | completed |          64 |      0          |      0.015625   |       0.0625     |             0.0248019  |            0.213535  |                    0         |         |
| PFAS      | MS2DeepScore | completed |          64 |      0.265625   |      0.671875   |       0.765625   |             0.432832   |            0.431796  |                    0.28125   |         |

## PFAS Case Study Summary

On the frozen PFAS locked-test benchmark, FragAnnotor reached Top-1 0.328125, Top-5 0.718750, Top-10 0.828125, and MRR 0.502844. The best non-FragAnnotor Top-10 baseline reached 0.765625, and the best non-FragAnnotor MRR reached 0.466127.

## CASMI 2022 Summary

CASMI 2022 standard test spectra were loaded from the MassFormer processed package. Native CFM-ID, SIRIUS, and MS2DeepScore executables/models were not available in this local environment, so CASMI model scores use deterministic lightweight fallback wrappers. These CASMI numbers verify pipeline execution and should be replaced with native baseline outputs before making SOTA claims.

## Model Execution Notes

- `FragAnnotor`: `{'class': 'FragAnnotorAnnotator', 'weights': {'our_spectrum_score': 0.35, 'cfmid_spectrum_score': 0.5, 'fragment_formula_score': 0.15, 'sirius_formula_score': 0.0, 'reaction_prior_score': 0.0}, 'executable': None, 'package_available': None}`
- `CFM-ID`: `{'class': 'CFMIDAnnotator', 'weights': {'cfmid_spectrum_score': 1.0}, 'executable': None, 'package_available': None}`
- `SIRIUS`: `{'class': 'SiriusAnnotator', 'weights': {'sirius_formula_score': 1.0}, 'executable': None, 'package_available': None}`
- `MS2DeepScore`: `{'class': 'MS2DeepScoreAnnotator', 'weights': {'ms2deepscore_score': 1.0}, 'executable': None, 'package_available': False}`

## Interpretation Guardrails

- Do not claim CASMI 2022 performance unless the CASMI standard test split is loaded and marked completed.
- Do not describe deterministic fallback wrappers as native CFM-ID/SIRIUS/MS2DeepScore inference.
- Clear FragAnnotor improvement is supported for the PFAS locked-test run in this artifact; CASMI uses fallback scores.
- PFAS results use the frozen locked-test candidate matrix and do not tune on locked test.
