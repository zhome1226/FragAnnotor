# ICEBERG Matched 170-Query Cleaning Audit

The cleaned ICEBERG package filters remote shard outputs to `manuscript_3_2_matched_170_v1` and excludes off-manifest rows.

## Outputs
- Query results: `results/manuscript_3_2_harmonized_comparison/iceberg_matched_query_results.csv`
- Top predictions: `results/manuscript_3_2_harmonized_comparison/iceberg_matched_top_predictions.csv`
- Summary: `results/manuscript_3_2_harmonized_comparison/iceberg_matched_summary.csv`
- Audit JSON: `results/manuscript_3_2_harmonized_comparison/iceberg_matched_cleaning_audit.json`

## Summary
- `dataset`: `CASMI2022`
- `model`: `ICEBERG`
- `benchmark_label`: `ICEBERG harmonized candidate-set rerun`
- `matched_manifest_version`: `manuscript_3_2_matched_170_v1`
- `status`: `completed_harmonized_matched_170_with_candidate_prediction_failures`
- `n_expected_queries`: `170`
- `n_queries_completed`: `170`
- `n_rank_valid_queries`: `170`
- `candidate_pool_policy`: `full_query_candidate_set`
- `score_name`: `binned_cosine_1Da`
- `top1_accuracy`: `0.0058823529411764705`
- `top5_accuracy`: `0.14705882352941177`
- `top10_accuracy`: `0.18235294117647058`
- `mean_reciprocal_rank`: `0.06494820403068068`
- `median_true_rank`: `117.0`
- `mean_top1_tanimoto`: `0.2807435479638168`
- `formula_accuracy`: `0.7764705882352941`
- `total_candidate_rows_scored`: `1062574`
- `total_failed_predictions`: `376`
- `source_query_rows_before_manifest_filter`: `180`
- `source_valid_rows_before_manifest_filter`: `180`
- `extra_query_ids_excluded`: `91,92,167,168`
- `claim_guardrail`: `Use only the matched 170-query filtered files for Section 3.2. Extra off-manifest shard rows were excluded and must not enter the main comparison table.`

## Excluded off-manifest rows

```text
 query_id  source_shard                      status  failed_prediction_count  true_rank
       91 shard_091_095                   completed                        0     8444.0
       92 shard_091_095 partial_prediction_failures                      256        4.0
      167 shard_166_170                   completed                        0     4351.0
      168 shard_166_170                   completed                        0     4734.0
```
