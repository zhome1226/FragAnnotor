# Benchmark Report

## What Was Run

The benchmark pipeline exported CASMI2022 and PFAS candidate-ranking outputs for FragAnnotor, CFM-ID, SIRIUS, and MS2DeepScore. Native baseline execution was required by the final command with `--allow-fallback false`; unavailable native tools are recorded as unavailable rather than replaced with fallback scores.

## Native vs Fallback Tool Status

| model        | native_available   | executable_or_package   | version   | blocker                                                                                    |
|:-------------|:-------------------|:------------------------|:----------|:-------------------------------------------------------------------------------------------|
| CFM-ID       | False              |                         |           | CFM-ID executable not found in PATH; no native CASMI CFM-ID inference was run.             |
| SIRIUS       | False              |                         |           | SIRIUS executable not found in PATH; no native CASMI SIRIUS inference was run.             |
| MS2DeepScore | False              |                         |           | ms2deepscore Python package/model not available; no native MS2DeepScore inference was run. |

PFAS CFM-ID and SIRIUS entries use real precomputed external expert scores from the companion PFAS workflow. SIRIUS is used as a scalar formula plausibility feature, not as a synthetic spectrum generator.

## Dataset Sizes

- `CASMI2022`: status `available`, queries `229`, candidate rows `408249`
- `PFAS`: status `available`, queries `64`, candidate rows `29632`

## Main Results

| dataset   | model        | status                            | native_or_fallback                 |   n_queries |   top1_accuracy |   top5_accuracy |   top10_accuracy |   mean_reciprocal_rank |   mean_top1_tanimoto |   molecular_formula_accuracy |   median_true_rank |   median_candidate_count | notes                                                                                                        |
|:----------|:-------------|:----------------------------------|:-----------------------------------|------------:|----------------:|----------------:|-----------------:|-----------------------:|---------------------:|-----------------------------:|-------------------:|-------------------------:|:-------------------------------------------------------------------------------------------------------------|
| CASMI2022 | FragAnnotor  | model_unavailable_native_required | native_unavailable                 |         229 |      nan        |       nan       |       nan        |            nan         |           nan        |                    nan       |                nan |                      nan | FragAnnotor native CASMI component scores are unavailable; fallback disabled.                                |
| CASMI2022 | CFM-ID       | model_unavailable_native_required | native_unavailable                 |         229 |      nan        |       nan       |       nan        |            nan         |           nan        |                    nan       |                nan |                      nan | CFM-ID native CASMI execution/export parser is unavailable in this repository run; fallback disabled.        |
| CASMI2022 | SIRIUS       | model_unavailable_native_required | native_unavailable                 |         229 |      nan        |       nan       |       nan        |            nan         |           nan        |                    nan       |                nan |                      nan | SIRIUS native CASMI execution/export parser is unavailable in this repository run; fallback disabled.        |
| CASMI2022 | MS2DeepScore | model_unavailable_native_required | native_unavailable                 |         229 |      nan        |       nan       |       nan        |            nan         |           nan        |                    nan       |                nan |                      nan | MS2DeepScore native CASMI model/embedding workflow is unavailable in this repository run; fallback disabled. |
| PFAS      | FragAnnotor  | completed                         | precomputed_external_real_scores   |          64 |        0.328125 |         0.71875 |         0.828125 |              0.502844  |             0.461697 |                      0.34375 |                  2 |                      463 |                                                                                                              |
| PFAS      | CFM-ID       | completed                         | precomputed_external_cfmid4_scores |          64 |        0.328125 |         0.65625 |         0.75     |              0.466127  |             0.447842 |                      0.34375 |                  3 |                      463 |                                                                                                              |
| PFAS      | SIRIUS       | completed                         | precomputed_external_sirius_scores |          64 |        0        |         0       |         0        |              0.0190272 |             0.116781 |                      0       |                 71 |                      463 |                                                                                                              |
| PFAS      | MS2DeepScore | model_unavailable_native_required | native_unavailable                 |          64 |      nan        |       nan       |       nan        |            nan         |           nan        |                    nan       |                nan |                      nan | MS2DeepScore package/model unavailable and fallback disabled.                                                |

## Interpretation

- PFAS locked-test ranking supports the selected primary FragAnnotor policy within the frozen PFAS benchmark.
- CASMI2022 native CFM-ID/SIRIUS/MS2DeepScore results are unavailable in this environment; preserved fallback CASMI results are preliminary only.
- No result with `native_or_fallback=native_unavailable` should be described as a completed native baseline.
- MS2DeepScore native comparison is blocked until the package and an appropriate pretrained model/embedding workflow are available.

## Exact Reproduction Command

```bash
python scripts/run_benchmark.py --dataset both --native-baselines --allow-fallback false --run-ablation --export-query-level --select-case-studies --output-dir results --seed 20260628
```

## Known Limitations

- CASMI native baseline execution was not completed because required native tools were not installed.
- PFAS results depend on the frozen candidate matrix generated in the transformation-product workflow.
- The benchmark does not establish deployment-ready thresholds or universal LC-MS/MS prediction performance.
