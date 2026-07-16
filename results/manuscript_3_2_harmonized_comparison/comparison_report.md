# Section 3.2 Harmonized CASMI2022 Comparison

All rows in the main comparison are filtered to `manuscript_3_2_matched_170_v1` and use the same 170 [M+H]+ CASMI2022 queries and candidate sets.

## Main Model Summary

| model                                                     |   n_queries |   top1_accuracy |   top5_accuracy |   top10_accuracy |   mean_reciprocal_rank |   median_true_rank |   mean_top1_tanimoto |   formula_accuracy |   failed_candidate_predictions | result_status                                |
|:----------------------------------------------------------|------------:|----------------:|----------------:|-----------------:|-----------------------:|-------------------:|---------------------:|-------------------:|-------------------------------:|:---------------------------------------------|
| FragAnnotator                                             |         170 |      0.629412   |       0.635294  |        0.641176  |              0.63377   |                  1 |           nan        |         nan        |                              0 | completed                                    |
| SIRIUS formula-only                                       |         170 |      0.694118   |       0.7       |        0.705882  |              0.697199  |                  1 |           nan        |         nan        |                              0 | completed                                    |
| CFM-ID                                                    |         170 |      0.0529412  |       0.135294  |        0.176471  |              0.0943919 |                169 |           nan        |         nan        |                              0 | completed                                    |
| CFM-ID-generated spectra + MS2DeepScore similarity hybrid |         170 |      0          |       0.0294118 |        0.0411765 |              0.0194014 |                456 |           nan        |         nan        |                              0 | completed                                    |
| ICEBERG                                                   |         170 |      0.00588235 |       0.147059  |        0.182353  |              0.0649482 |                117 |             0.280744 |           0.776471 |                            376 | completed_with_candidate_prediction_failures |
| MassFormer                                                |         170 |      0.00588235 |       0.0117647 |        0.0117647 |              0.0133596 |                826 |             0.134447 |           0.582353 |                           1481 | completed_with_candidate_prediction_failures |

## Paired FragAnnotator Comparisons

| baseline_model_id         | baseline_model                                            |   n_queries |   fragannotator_better_query_count |   fragannotator_worse_query_count |   tie_count |   mean_rank_difference_fragannotator_minus_baseline |   median_rank_difference_fragannotator_minus_baseline |   mean_mrr_difference_fragannotator_minus_baseline |   mean_top10_difference_fragannotator_minus_baseline | interpretation                                                                |
|:--------------------------|:----------------------------------------------------------|------------:|-----------------------------------:|----------------------------------:|------------:|----------------------------------------------------:|------------------------------------------------------:|---------------------------------------------------:|-----------------------------------------------------:|:------------------------------------------------------------------------------|
| sirius_formula_only       | SIRIUS formula-only                                       |         170 |                                  7 |                                18 |         145 |                                            5.98235  |                                                   0   |                                         -0.0634283 |                                           -0.0647059 | negative rank difference means FragAnnotator ranked the true candidate better |
| cfmid_native              | CFM-ID                                                    |         170 |                                119 |                                47 |           4 |                                           -0.817647 |                                                 -83.5 |                                          0.539378  |                                            0.464706  | negative rank difference means FragAnnotator ranked the true candidate better |
| cfmid_ms2deepscore_hybrid | CFM-ID-generated spectra + MS2DeepScore similarity hybrid |         170 |                                128 |                                41 |           1 |                                         -328.165    |                                                -221   |                                          0.614369  |                                            0.6       | negative rank difference means FragAnnotator ranked the true candidate better |
| iceberg                   | ICEBERG                                                   |         170 |                                119 |                                50 |           1 |                                          139.759    |                                                 -34.5 |                                          0.568822  |                                            0.458824  | negative rank difference means FragAnnotator ranked the true candidate better |
| massformer                | MassFormer                                                |         170 |                                141 |                                29 |           0 |                                         -865.712    |                                                -528.5 |                                          0.620411  |                                            0.629412  | negative rank difference means FragAnnotator ranked the true candidate better |

## Reporting Guardrails

- FragAnnotator here is the frozen fixed evidence-fusion candidate-ranking framework, not a validated trained neural model.
- CFM-ID-generated spectra + MS2DeepScore similarity hybrid must not be described as native MS2DeepScore.
- ICEBERG and MassFormer are included as harmonized reruns with candidate-level prediction failures audited.
- NEIMS is excluded from the main table because no reliable checkpoint/wrapper was available.
- Do not compare these 170-query metrics directly against 229-query Section 3.1 metrics without labeling the query-set difference.

## Output Files

- `harmonized_model_summary.csv`
- `harmonized_query_results.csv`
- `harmonized_query_rank_wide.csv`
- `pairwise_rank_comparison.csv`
- `paired_bootstrap_differences.csv`
- `massformer_matched_query_results.csv`
