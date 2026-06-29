# Benchmark Report

## What Was Run

The benchmark pipeline exported CASMI2022 and PFAS candidate-ranking outputs for FragAnnotor, CFM-ID, SIRIUS, and MS2DeepScore. Native baseline execution was required by the final command with `--allow-fallback false`; unavailable native tools are recorded as unavailable rather than replaced with fallback scores.

## Native vs Fallback Tool Status

| model | native_available | executable_or_package | version | blocker |
| --- | --- | --- | --- | --- |
| CFM-ID | False | /data/zhome/ec_structure_external_ms_models/envs/cfm_py36/bin/cfm-id | executable_present_but_smoke_failed | CFM-ID executable exists, but smoke tests against available pretrained model/configs abort with Invalid Feature Configuration; no valid native CASMI CFM-ID benchmark scores are reported. |
| SIRIUS | True | /home/zhome/opt/sirius-4.9.15-headless/bin/sirius | SIRIUS 4.9.15 |  |
| MS2DeepScore | False |  | unavailable | ms2deepscore Python package/model not available; no native MS2DeepScore inference was run. |

PFAS CFM-ID and SIRIUS entries use real precomputed external expert scores from the companion PFAS workflow. SIRIUS is used as a scalar formula plausibility feature, not as a synthetic spectrum generator.

## Dataset Sizes

- `CASMI2022`: status `available`, queries `229`, candidate rows `408249`
- `PFAS`: status `available`, queries `64`, candidate rows `29632`

## Main Results

| dataset | model | status | native_or_fallback | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank | mean_top1_tanimoto | molecular_formula_accuracy | median_true_rank | median_candidate_count | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CASMI2022 | FragAnnotor | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | FragAnnotor native CASMI component scores are unavailable; fallback disabled. |
| CASMI2022 | CFM-ID | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | CFM-ID native CASMI execution/export parser is unavailable in this repository run; fallback disabled. |
| CASMI2022 | SIRIUS | completed | native_sirius | 229 | 0.6462882096069869 | 0.6550218340611353 | 0.6550218340611353 | 0.6499330162600465 | 0.7496250635336656 | 0.7947598253275109 | 1.0 | 2001.0 |  |
| CASMI2022 | MS2DeepScore | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | MS2DeepScore native CASMI model/embedding workflow is unavailable in this repository run; fallback disabled. |
| PFAS | FragAnnotor | completed | precomputed_external_real_scores | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 | 0.46169711913564426 | 0.34375 | 2.0 | 463.0 |  |
| PFAS | CFM-ID | completed | precomputed_external_cfmid4_scores | 64 | 0.328125 | 0.65625 | 0.75 | 0.46612686869088077 | 0.4478419101480884 | 0.34375 | 3.0 | 463.0 |  |
| PFAS | SIRIUS | completed | precomputed_external_sirius_scores | 64 | 0.0 | 0.015625 | 0.0625 | 0.02480186933879968 | 0.21353452806451576 | 0.0 | 96.0 | 463.0 |  |
| PFAS | MS2DeepScore | model_unavailable_native_required | native_unavailable | 64 |  |  |  |  |  |  |  |  | MS2DeepScore package/model unavailable and fallback disabled. |

## Native CASMI2022 Results

| dataset | model | status | native_or_fallback | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank | mean_top1_tanimoto | molecular_formula_accuracy | median_true_rank | median_candidate_count | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CASMI2022 | FragAnnotor | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | FragAnnotor native CASMI component scores are unavailable; fallback disabled. |
| CASMI2022 | CFM-ID | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | CFM-ID native CASMI execution/export parser is unavailable in this repository run; fallback disabled. |
| CASMI2022 | SIRIUS | completed | native_sirius | 229 | 0.6462882096069869 | 0.6550218340611353 | 0.6550218340611353 | 0.6499330162600465 | 0.7496250635336656 | 0.7947598253275109 | 1.0 | 2001.0 |  |
| CASMI2022 | MS2DeepScore | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | MS2DeepScore native CASMI model/embedding workflow is unavailable in this repository run; fallback disabled. |

CASMI2022 includes one completed native baseline in this run: SIRIUS 4.9.15 formula-only ranking. CASMI FragAnnotor component scores, CFM-ID, and MS2DeepScore remain unavailable under `--allow-fallback false`.

## Preliminary Fallback CASMI Results

Earlier deterministic fallback CASMI exports are preserved under `results/preliminary/` and are not used as native benchmark claims.

## PFAS Locked-Test Results

| dataset | model | status | native_or_fallback | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank | mean_top1_tanimoto | molecular_formula_accuracy | median_true_rank | median_candidate_count | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PFAS | FragAnnotor | completed | precomputed_external_real_scores | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 | 0.46169711913564426 | 0.34375 | 2.0 | 463.0 |  |
| PFAS | CFM-ID | completed | precomputed_external_cfmid4_scores | 64 | 0.328125 | 0.65625 | 0.75 | 0.46612686869088077 | 0.4478419101480884 | 0.34375 | 3.0 | 463.0 |  |
| PFAS | SIRIUS | completed | precomputed_external_sirius_scores | 64 | 0.0 | 0.015625 | 0.0625 | 0.02480186933879968 | 0.21353452806451576 | 0.0 | 96.0 | 463.0 |  |
| PFAS | MS2DeepScore | model_unavailable_native_required | native_unavailable | 64 |  |  |  |  |  |  |  |  | MS2DeepScore package/model unavailable and fallback disabled. |

## PFAS Ablation Results

| variant | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank |
| --- | --- | --- | --- | --- | --- |
| full_current_primary_no_sirius | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 |
| full_five_component_validation_selected | 64 | 0.328125 | 0.75 | 0.828125 | 0.5034280116505216 |
| only_our_spectrum_score | 64 | 0.03125 | 0.328125 | 0.453125 | 0.1668739143762869 |
| only_cfmid_spectrum_score | 64 | 0.328125 | 0.65625 | 0.75 | 0.4661268686908807 |
| only_fragment_formula_score | 64 | 0.0625 | 0.21875 | 0.28125 | 0.1485011086449021 |
| only_sirius_formula_score | 64 | 0.0 | 0.015625 | 0.0625 | 0.0248018693387996 |
| only_reaction_prior_score | 64 | 0.0 | 0.0 | 0.0 | 0.0232429240635042 |
| without_our_spectrum_score | 64 | 0.34375 | 0.65625 | 0.796875 | 0.4782487523267485 |
| without_cfmid_spectrum_score | 64 | 0.09375 | 0.4375 | 0.59375 | 0.2544062647984305 |
| without_fragment_formula_score | 64 | 0.3125 | 0.703125 | 0.75 | 0.4869929128515937 |
| without_sirius_formula_score | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 |
| without_reaction_prior_score | 64 | 0.328125 | 0.75 | 0.828125 | 0.5034280116505216 |

## PFAS Case-Study Results

Selected PFAS case studies: 5 rows in `results/case_studies/pfas_selected_cases.csv`.
Peak-level annotations available: True; source: Existing PFAS SIRIUS/project-derived peak annotations preserved from scripts/export_pfas_peak_annotations.py.

## Interpretation

- PFAS locked-test ranking supports the selected primary FragAnnotor policy within the frozen PFAS benchmark.
- CASMI2022 native SIRIUS formula-only ranking completed; CASMI FragAnnotor, CFM-ID, and MS2DeepScore native structure-ranking outputs remain blocked and are not replaced with fallback scores.
- No result with `native_or_fallback=native_unavailable` should be described as a completed native baseline.
- MS2DeepScore native comparison is blocked until the package and an appropriate pretrained model/embedding workflow are available.
- SIRIUS is used here as molecular formula plausibility evidence, not as a synthetic spectrum generator or CSI:FingerID structure predictor.

## Manuscript Readiness

- PFAS locked-test expert-fusion benchmark: ready as an internal frozen benchmark, with conservative claims.
- PFAS ablation and case-study package: ready for manuscript drafting, subject to the external-validation limitation.
- CASMI benchmark: partially ready; only SIRIUS formula-only native baseline completed, while native CFM-ID, MS2DeepScore, and CASMI FragAnnotor component scores are blocked.
- SOTA comparison: partially ready; do not claim full FragAnnotor superiority on CASMI until missing native baselines and FragAnnotor CASMI scores are available.

## Remaining Blockers

- Native CFM-ID CASMI scoring is blocked by `Invalid Feature Configuration` in available pretrained model/config smoke tests.
- Native MS2DeepScore is blocked because the package and a compatible pretrained model/embedding workflow are unavailable.
- CASMI FragAnnotor is blocked until real CASMI component scores are generated; fallback component scores are not reported as native results.
- PFAS results remain an internal frozen locked-test benchmark and are not independent external validation.

## Exact Reproduction Command

```bash
python scripts/run_benchmark.py --dataset both --native-baselines --allow-fallback false --run-ablation --export-query-level --select-case-studies --output-dir results --seed 20260628
```

## Known Limitations

- CASMI native benchmark execution is incomplete: SIRIUS formula-only scores are available, but CFM-ID smoke tests fail with model/config incompatibility and MS2DeepScore has no configured package/model.
- PFAS results depend on the frozen candidate matrix generated in the transformation-product workflow.
- The benchmark does not establish deployment-ready thresholds or universal LC-MS/MS prediction performance.
