# CASMI Retrieval Acceleration Audit

This branch tests a first-stage candidate gate before expensive native spectrum reranking. It does not train weights, does not tune on CASMI, and does not replace the ongoing full native CFM-ID run.

## Key Findings

- Component matrix rows: `408249` across `229` queries.
- Mean candidate rows per query: `1782.7`.
- FragAnnotor top-100 gate retains the true candidate for `0.755` of queries while reducing candidate rows by `0.944`.
- FragAnnotor top-200 gate retains the true candidate for `0.777` of queries while reducing candidate rows by `0.888`.
- Best tested union gate `union_fragannotor_sirius_fragment` at per-policy top-1000 retains `0.952` of true candidates with mean gated candidate count `1206.3`.
- Practical union gate range (`FragAnnotor + SIRIUS + fragment-formula`): top-50: retention 0.812, mean candidates 82.3, reduction 0.954; top-100: retention 0.825, mean candidates 162.9, reduction 0.909; top-200: retention 0.843, mean candidates 315.1, reduction 0.823.

## Score Policy Summary

| score_policy | n_queries | queries_with_true_candidate | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank | median_true_rank | mean_candidate_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fragannotor_formal_component_score | 229 | 229 | 0.650655 | 0.659389 | 0.668122 | 0.658178 | 1 | 1782.75 |
| precursor_mass_consistency_score | 229 | 229 | 0.279476 | 0.384279 | 0.458515 | 0.339437 | 15 | 1782.75 |
| fragment_formula_plausibility_score | 229 | 229 | 0.563319 | 0.641921 | 0.659389 | 0.59771 | 1 | 1782.75 |
| sirius_formula_plausibility_score_nan0 | 229 | 229 | 0.724891 | 0.733624 | 0.737991 | 0.730114 | 1 | 1782.75 |
| no_sirius_precursor80_fragment20 | 229 | 229 | 0.305677 | 0.406114 | 0.475983 | 0.364414 | 13 | 1782.75 |
| no_sirius_precursor50_fragment50 | 229 | 229 | 0.31441 | 0.414847 | 0.480349 | 0.372637 | 13 | 1782.75 |

## Union Gate Summary

| union_gate | policies | per_policy_top_k | n_queries | true_candidate_retention | queries_losing_true_candidate | mean_gated_candidate_count | median_gated_candidate_count | mean_original_candidate_count | candidate_row_reduction_fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| union_fragannotor_sirius | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0 | 10 | 229 | 0.742358 | 59 | 10.8821 | 10 | 1782.75 | 0.993896 |
| union_fragannotor_sirius | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0 | 25 | 229 | 0.755459 | 56 | 27.2358 | 25 | 1782.75 | 0.984723 |
| union_fragannotor_sirius | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0 | 50 | 229 | 0.764192 | 54 | 54.3668 | 50 | 1782.75 | 0.969504 |
| union_fragannotor_sirius | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0 | 100 | 229 | 0.781659 | 50 | 108.031 | 100 | 1782.75 | 0.939402 |
| union_fragannotor_sirius | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0 | 200 | 229 | 0.799127 | 46 | 216.585 | 200 | 1782.75 | 0.87851 |
| union_fragannotor_sirius | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0 | 500 | 229 | 0.89083 | 25 | 542.402 | 500 | 1782.75 | 0.695749 |
| union_fragannotor_sirius | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0 | 1000 | 229 | 0.947598 | 12 | 1050.32 | 1000 | 1782.75 | 0.410842 |
| union_fragannotor_sirius_fragment | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score | 10 | 229 | 0.80786 | 44 | 16.655 | 18 | 1782.75 | 0.990658 |
| union_fragannotor_sirius_fragment | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score | 25 | 229 | 0.80786 | 44 | 41.3144 | 45 | 1782.75 | 0.976825 |
| union_fragannotor_sirius_fragment | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score | 50 | 229 | 0.812227 | 43 | 82.3275 | 88 | 1782.75 | 0.95382 |
| union_fragannotor_sirius_fragment | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score | 100 | 229 | 0.825328 | 40 | 162.904 | 175 | 1782.75 | 0.908622 |
| union_fragannotor_sirius_fragment | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score | 200 | 229 | 0.842795 | 36 | 315.057 | 338 | 1782.75 | 0.823275 |
| union_fragannotor_sirius_fragment | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score | 500 | 229 | 0.912664 | 20 | 701.459 | 713 | 1782.75 | 0.606529 |
| union_fragannotor_sirius_fragment | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score | 1000 | 229 | 0.951965 | 11 | 1206.34 | 1283 | 1782.75 | 0.323322 |
| union_all_low_cost | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score+precursor_mass_consistency_score | 10 | 229 | 0.812227 | 43 | 21 | 20 | 1782.75 | 0.98822 |
| union_all_low_cost | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score+precursor_mass_consistency_score | 25 | 229 | 0.812227 | 43 | 49.8734 | 49 | 1782.75 | 0.972024 |
| union_all_low_cost | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score+precursor_mass_consistency_score | 50 | 229 | 0.816594 | 42 | 96.048 | 95 | 1782.75 | 0.946124 |
| union_all_low_cost | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score+precursor_mass_consistency_score | 100 | 229 | 0.829694 | 39 | 184.332 | 185 | 1782.75 | 0.896602 |
| union_all_low_cost | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score+precursor_mass_consistency_score | 200 | 229 | 0.842795 | 36 | 346.362 | 353 | 1782.75 | 0.805714 |
| union_all_low_cost | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score+precursor_mass_consistency_score | 500 | 229 | 0.912664 | 20 | 736.646 | 728 | 1782.75 | 0.586791 |
| union_all_low_cost | fragannotor_formal_component_score+sirius_formula_plausibility_score_nan0+fragment_formula_plausibility_score+precursor_mass_consistency_score | 1000 | 229 | 0.951965 | 11 | 1228.82 | 1300 | 1782.75 | 0.310715 |

## Interpretation

- Acceleration potential is high if CFM-ID/MS2DeepScore are used as second-stage rerankers on a retained top-K set.
- The tested gates do not improve accuracy by themselves; they trade recall for runtime and need validation-only threshold/top-K selection before locked reporting.
- This is not a full native CFM-ID baseline because CFM-ID is not run over every supported candidate.
- A production path should use validation-only gate selection, then report locked-test behavior separately.
- The shared `scripts/msms_metrics.py` module provides a dependency-light spectrum cleaning and similarity layer; if matchms is installed, it should be used as the stricter reference implementation.
