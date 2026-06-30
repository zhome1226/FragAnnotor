# CASMI2022 Native CFM-ID Subset Benchmark

Status: `completed_subset`

This is a native CFM-ID subset/candidate-limited benchmark. It is not a complete CASMI2022 CFM-ID result and must not be used as full-SOTA evidence.

## Configuration

- CFM-ID binary: `/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin/cfm-id`
- Supported native adducts in model directory: `[M+H]+, [M-H]-`
- Unsupported CASMI queries: `59`; counts: `{'[M+Na]+': 59}`
- Candidate limit: `10`
- Candidate-pool policy: `first_n_plus_true`
- Selected queries: `10`
- Completed queries: `10`

## Subset Metrics

| dataset   | model   | status           | native_or_fallback                    |   n_queries_selected |   n_queries_completed |   n_rank_valid_queries |   candidate_limit | candidate_pool_policy   |   top1_accuracy |   top5_accuracy |   top10_accuracy |   mean_reciprocal_rank |   median_true_rank |   mean_elapsed_seconds_completed |   total_elapsed_seconds_completed | claim_guardrail                                                                                                                                      |
|:----------|:--------|:-----------------|:--------------------------------------|---------------------:|----------------------:|-----------------------:|------------------:|:------------------------|----------------:|----------------:|-----------------:|-----------------------:|-------------------:|---------------------------------:|----------------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------|
| CASMI2022 | CFM-ID  | completed_subset | native_cfmid_subset_candidate_limited |                   10 |                    10 |                     10 |                10 | first_n_plus_true       |             0.7 |             0.9 |                1 |               0.765833 |                  1 |                          92.8157 |                           928.157 | This is a native CFM-ID subset/candidate-limited benchmark. It is not a complete CASMI2022 CFM-ID result and must not be used as full-SOTA evidence. |

## Interpretation

These metrics are useful for runtime and integration validation only. Because the candidate pool is limited and injects the true structure when it is outside the first N CASMI candidates, the table is not comparable to full-candidate CASMI rankings.
