# Section 3.2 Matched CASMI Comparison Inputs

This package freezes the current 170-query matched CASMI2022 `[M+H]+` manifest for harmonized model comparison.

Current matched outputs are available for FragAnnotator, SIRIUS formula-only, native CFM-ID, and CFM-ID-generated candidate spectra + MS2DeepScore similarity hybrid.

ICEBERG and MassFormer are still running/partial. NEIMS is not included until a reliable checkpoint and inference wrapper are validated.

## Current Available Summary

| model                                                     | result_status   |   n_queries |   completed_queries |   top1_accuracy |   top5_accuracy |   top10_accuracy |   mean_reciprocal_rank |   median_true_rank |   mean_top1_tanimoto |   formula_accuracy |
|:----------------------------------------------------------|:----------------|------------:|--------------------:|----------------:|----------------:|-----------------:|-----------------------:|-------------------:|---------------------:|-------------------:|
| FragAnnotator                                             | completed       |         170 |                 170 |       0.629412  |       0.635294  |        0.641176  |              0.63377   |                  1 |                  nan |                nan |
| SIRIUS formula-only                                       | completed       |         170 |                 170 |       0.694118  |       0.7       |        0.705882  |              0.697199  |                  1 |                  nan |                nan |
| CFM-ID                                                    | completed       |         170 |                 170 |       0.0529412 |       0.135294  |        0.176471  |              0.0943919 |                169 |                  nan |                nan |
| CFM-ID-generated spectra + MS2DeepScore similarity hybrid | completed       |         170 |                 170 |       0         |       0.0294118 |        0.0411765 |              0.0194014 |                456 |                  nan |                nan |

## Guardrail

This is not the final Section 3.2 main table while ICEBERG/MassFormer are partial. Do not compare 229-query Section 3.1 metrics to this matched 170-query table without explicit labeling.
