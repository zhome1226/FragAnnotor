# Section 3.1 CASMI2022 FragAnnotator-Only Performance

This report uses the frozen fixed evidence-fusion FragAnnotator definition from `configs/fragannotator_manuscript_final.yaml`.

No SIRIUS, CFM-ID, ICEBERG, MassFormer, NEIMS, or MS2DeepScore comparison metric is reported in this Section 3.1 package.

## Summary

|   n_queries |   top1_accuracy |   top5_accuracy |   top10_accuracy |   mean_reciprocal_rank |   median_true_rank |   mean_top1_tanimoto |   median_top1_tanimoto |   molecular_formula_accuracy |
|------------:|----------------:|----------------:|-----------------:|-----------------------:|-------------------:|---------------------:|-----------------------:|-----------------------------:|
|         229 |        0.650655 |        0.659389 |         0.672489 |               0.658549 |                  1 |             0.694028 |                      1 |                     0.799127 |

## Bootstrap 95% Confidence Intervals

| metric                     |   estimate |   ci95_low |   ci95_high |   n_bootstrap |   seed |
|:---------------------------|-----------:|-----------:|------------:|--------------:|-------:|
| top1_accuracy              |   0.650655 |   0.58952  |    0.716157 |          2000 |      0 |
| top5_accuracy              |   0.659389 |   0.593886 |    0.720524 |          2000 |      0 |
| top10_accuracy             |   0.672489 |   0.611354 |    0.729367 |          2000 |      0 |
| mean_reciprocal_rank       |   0.658549 |   0.59857  |    0.718365 |          2000 |      0 |
| median_true_rank           |   1        |   1        |    1        |          2000 |      0 |
| mean_top1_tanimoto         |   0.694028 |   0.639605 |    0.746553 |          2000 |      0 |
| median_top1_tanimoto       |   1        |   1        |    1        |          2000 |      0 |
| molecular_formula_accuracy |   0.799127 |   0.750983 |    0.851528 |          2000 |      0 |

## Stratification Notes

- Candidate set size, precursor mass, adduct, formula-correct versus formula-incorrect, spectrum peak count, and top-1 structural similarity proxy strata are included in `stratified_results.csv`.
- Collision energy is not available in the current processed CASMI2022 table, so the collision-energy stratum is explicitly marked unavailable.

## Figure Outputs

- `results/manuscript_3_1_casmi_overall/figures/figure_3_1_overall_topk_mrr.png`
- `results/manuscript_3_1_casmi_overall/figures/figure_3_1_true_rank_distribution.png`
- `results/manuscript_3_1_casmi_overall/figures/figure_3_1_candidate_set_size.png`
- `results/manuscript_3_1_casmi_overall/figures/figure_3_1_similarity_difficulty.png`

## Rebuild

`python scripts/generate_manuscript_3_1_casmi_overall.py`
