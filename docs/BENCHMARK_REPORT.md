# Benchmark Report

## What Was Run

The benchmark pipeline exported CASMI2022 and PFAS candidate-ranking outputs for FragAnnotor, CFM-ID, SIRIUS, and MS2DeepScore. Native baseline execution was required by the final command with `--allow-fallback false`; unavailable native tools are recorded as unavailable rather than replaced with fallback scores.

## Native vs Fallback Tool Status

| model | native_available | executable_or_package | version | blocker |
| --- | --- | --- | --- | --- |
| CFM-ID | False | /home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin/cfm-id | native_binary_smoke_passed_runtime_blocked | CFM-ID 4.x-compatible native binary was found and smoke-tested. A resumable full-run manifest is prepared for 170 supported `[M+H]+`/`[M-H]-` CASMI queries and 1062950 candidate rows. The precomputed route requires 936483 unique candidate spectra; current full-run cache progress is 346 candidate spectra and 2 completed supported query rankings. No full native CASMI CFM-ID metrics are reported until every required shard completes; unsupported adduct counts: {'[M+Na]+': 59}. |
| SIRIUS | True |  | SIRIUS 4.9.15 native formula result file |  |
| MS2DeepScore | False | /home/zhome/ec_structure/external_ms_models/envs/ms2deepscore_casmi/bin/python | MS2DeepScore 2.7.2 / MatchMS 0.33.1 / Torch 2.4.1+cpu verified | Do not report full-CASMI native MS2DeepScore Top-k metrics yet. MS2DeepScore scores spectrum pairs; the pretrained model and CPU environment are externally available/verified, and a CFM-ID-generated complete-query hybrid subset is available when cached candidate spectra exist. The full CASMI structure-candidate benchmark still lacks a complete per-candidate measured or predicted spectrum library. CFM-ID predicted spectra must be labeled as a CFM-ID plus MS2DeepScore hybrid baseline rather than native MS2DeepScore. Complete-query CFM-ID + MS2DeepScore hybrid subset is available for 2 selected queries with MRR=0.10704225352112677; it is not native MS2DeepScore. |

PFAS CFM-ID and SIRIUS entries use real precomputed external expert scores from the companion PFAS workflow. SIRIUS is used as a scalar formula plausibility feature, not as a synthetic spectrum generator.

## Dataset Sizes

- `CASMI2022`: status `available`, queries `229`, candidate rows `408249`
- `PFAS`: status `available`, queries `64`, candidate rows `29632`

## Main Results

| dataset | model | status | native_or_fallback | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank | mean_top1_tanimoto | molecular_formula_accuracy | median_true_rank | median_candidate_count | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CASMI2022 | FragAnnotor | completed | formal_fixed_component_score_mode | 229 | 0.6506550218340611 | 0.6593886462882096 | 0.6724890829694323 | 0.6585487281556323 | 0.6940283564485756 | 0.7991266375545851 | 1.0 | 2001.0 |  |
| CASMI2022 | CFM-ID | model_unavailable_native_required | native_runtime_blocked | 229 |  |  |  |  |  |  |  |  | CFM-ID native CASMI execution is runtime-blocked in this repository run: a compatible CFM-ID 4.x binary was found and smoke-tested, but 100 candidates did not finish within 15 minutes and no complete CASMI CFM-ID score table is available. |
| CASMI2022 | SIRIUS | completed | native_sirius | 229 | 0.6462882096069869 | 0.6550218340611353 | 0.6550218340611353 | 0.6499330162600465 | 0.7496250635336656 | 0.7947598253275109 | 1.0 | 2001.0 |  |
| CASMI2022 | MS2DeepScore | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | MS2DeepScore native CASMI candidate-ranking workflow is unavailable: the package/model may be installable, but this structure-candidate benchmark lacks a complete candidate spectrum library or configured pretrained MS2DeepScore embedding workflow. |
| PFAS | FragAnnotor | completed | precomputed_external_real_scores | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 | 0.46169711913564426 | 0.34375 | 2.0 | 463.0 |  |
| PFAS | CFM-ID | completed | precomputed_external_cfmid4_scores | 64 | 0.328125 | 0.65625 | 0.75 | 0.46612686869088077 | 0.4478419101480884 | 0.34375 | 3.0 | 463.0 |  |
| PFAS | SIRIUS | completed | precomputed_external_sirius_scores | 64 | 0.0 | 0.0 | 0.0 | 0.019027157243743736 | 0.11678068775266423 | 0.0 | 71.0 | 463.0 |  |
| PFAS | MS2DeepScore | model_unavailable_native_required | native_unavailable | 64 |  |  |  |  |  |  |  |  | MS2DeepScore package/model unavailable and fallback disabled. |

## Native CASMI2022 Results

| dataset | model | status | native_or_fallback | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank | mean_top1_tanimoto | molecular_formula_accuracy | median_true_rank | median_candidate_count | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CASMI2022 | FragAnnotor | completed | formal_fixed_component_score_mode | 229 | 0.6506550218340611 | 0.6593886462882096 | 0.6724890829694323 | 0.6585487281556323 | 0.6940283564485756 | 0.7991266375545851 | 1.0 | 2001.0 |  |
| CASMI2022 | CFM-ID | model_unavailable_native_required | native_runtime_blocked | 229 |  |  |  |  |  |  |  |  | CFM-ID native CASMI execution is runtime-blocked in this repository run: a compatible CFM-ID 4.x binary was found and smoke-tested, but 100 candidates did not finish within 15 minutes and no complete CASMI CFM-ID score table is available. |
| CASMI2022 | SIRIUS | completed | native_sirius | 229 | 0.6462882096069869 | 0.6550218340611353 | 0.6550218340611353 | 0.6499330162600465 | 0.7496250635336656 | 0.7947598253275109 | 1.0 | 2001.0 |  |
| CASMI2022 | MS2DeepScore | model_unavailable_native_required | native_unavailable | 229 |  |  |  |  |  |  |  |  | MS2DeepScore native CASMI candidate-ranking workflow is unavailable: the package/model may be installable, but this structure-candidate benchmark lacks a complete candidate spectrum library or configured pretrained MS2DeepScore embedding workflow. |

CASMI2022 includes one completed native baseline in this run: SIRIUS 4.9.15 formula-only ranking. FragAnnotor is reported separately as a formal fixed formula/fragment component-score CASMI mode using real experimental peaks, candidate formulas, precursor/adduct mass consistency, common fragment/neutral-loss plausibility, and native SIRIUS formula scores. A separate trained neural checkpoint report is included when available. CFM-ID and MS2DeepScore remain unavailable as completed full native CASMI candidate-ranking baselines under `--allow-fallback false`.

## Preliminary Fallback CASMI Results

Earlier deterministic fallback CASMI exports are preserved under `results/preliminary/` and are not used as native benchmark claims.

## PFAS Locked-Test Results

| dataset | model | status | native_or_fallback | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank | mean_top1_tanimoto | molecular_formula_accuracy | median_true_rank | median_candidate_count | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PFAS | FragAnnotor | completed | precomputed_external_real_scores | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 | 0.46169711913564426 | 0.34375 | 2.0 | 463.0 |  |
| PFAS | CFM-ID | completed | precomputed_external_cfmid4_scores | 64 | 0.328125 | 0.65625 | 0.75 | 0.46612686869088077 | 0.4478419101480884 | 0.34375 | 3.0 | 463.0 |  |
| PFAS | SIRIUS | completed | precomputed_external_sirius_scores | 64 | 0.0 | 0.0 | 0.0 | 0.019027157243743736 | 0.11678068775266423 | 0.0 | 71.0 | 463.0 |  |
| PFAS | MS2DeepScore | model_unavailable_native_required | native_unavailable | 64 |  |  |  |  |  |  |  |  | MS2DeepScore package/model unavailable and fallback disabled. |

## PFAS Ablation Results

| variant | n_queries | top1_accuracy | top5_accuracy | top10_accuracy | mean_reciprocal_rank |
| --- | --- | --- | --- | --- | --- |
| full_current_primary_no_sirius | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 |
| full_five_component_validation_selected | 64 | 0.3125 | 0.703125 | 0.78125 | 0.4676917976757649 |
| only_our_spectrum_score | 64 | 0.03125 | 0.328125 | 0.453125 | 0.1668739143762869 |
| only_cfmid_spectrum_score | 64 | 0.328125 | 0.65625 | 0.75 | 0.4661268686908807 |
| only_fragment_formula_score | 64 | 0.0625 | 0.21875 | 0.28125 | 0.1485011086449021 |
| only_sirius_formula_score | 64 | 0.0 | 0.0 | 0.0 | 0.0190271572437437 |
| only_reaction_prior_score | 64 | 0.0 | 0.0 | 0.0 | 0.0232429240635042 |
| without_our_spectrum_score | 64 | 0.34375 | 0.609375 | 0.65625 | 0.4494693331939122 |
| without_cfmid_spectrum_score | 64 | 0.015625 | 0.375 | 0.40625 | 0.1589713183110093 |
| without_fragment_formula_score | 64 | 0.3125 | 0.6875 | 0.734375 | 0.4650339795022493 |
| without_sirius_formula_score | 64 | 0.328125 | 0.71875 | 0.828125 | 0.502844039959644 |
| without_reaction_prior_score | 64 | 0.3125 | 0.703125 | 0.78125 | 0.4676917976757649 |

## PFAS Case-Study Results

Selected PFAS case studies: 5 rows in `results/case_studies/pfas_selected_cases.csv`.
Peak-level annotations available: True; source: Existing PFAS SIRIUS/project-derived peak annotations preserved from scripts/export_pfas_peak_annotations.py.

## Formal CASMI FragAnnotor Component Package

Formal fixed component-score mode is available at `results/casmi2022_fragannotor_formal_components/` with Top-1 `0.6506550218340611`, Top-5 `0.6593886462882096`, Top-10 `0.6724890829694323`, and MRR `0.6585487281556323`.
This is a formal fixed component-score mode using real CASMI spectra and native SIRIUS formula scores, not a trained FragAnnotor neural spectrum model and not a replacement for missing CFM-ID/MS2DeepScore native baselines.

## CASMI Trained Neural FragAnnotor Checkpoint

Frozen trained neural CASMI inference is available at `results/casmi2022_fragannotor_trained_neural_v1/` with Top-1 `0.0087336244541484`, Top-5 `0.0131004366812227`, Top-10 `0.0262008733624454`, and MRR `0.0172596075877486`.
Training-pair canonical SMILES overlap with CASMI test structures: `False`.
This is report-only inference from a frozen checkpoint, not CASMI training, weight search, or checkpoint selection.

## Native CFM-ID CASMI Runtime Audit

CFM-ID native binary status: `passed`; full CASMI status: `runtime_blocked_full_casmi_not_reported`.
Do not report native CFM-ID CASMI Top-k metrics until a complete per-query candidate score table is generated. Smoke/partial outputs are readiness evidence only, not benchmark results.

## Native CFM-ID Complete-Query Subset

Complete-query native CFM-ID precomputed subset evidence is available at `results/casmi2022_cfmid_native_precomputed_complete_query_subset_v1/`: `2` selected supported `[M+H]+` CASMI queries, full candidate sets for each selected query, Top-1 `0.0`, Top-5 `0.5`, Top-10 `0.5`, and MRR `0.1161290322580645`.
Query 35 expansion status: `completed_ranked`, candidate spectra `233/233`, ranked rows `233`, true rank `31`.
This is full-candidate-set evidence for selected low-candidate queries only; it is not a full CASMI CFM-ID baseline.

## Native MS2DeepScore CASMI Audit

MS2DeepScore CASMI status: `blocked_full_casmi_no_candidate_spectrum_library`.
Do not report full-CASMI native MS2DeepScore Top-k metrics yet. MS2DeepScore scores spectrum pairs; the pretrained model and CPU environment are externally available/verified, and a CFM-ID-generated complete-query hybrid subset is available when cached candidate spectra exist. The full CASMI structure-candidate benchmark still lacks a complete per-candidate measured or predicted spectrum library. CFM-ID predicted spectra must be labeled as a CFM-ID plus MS2DeepScore hybrid baseline rather than native MS2DeepScore.

## CFM-ID + MS2DeepScore Complete-Query Hybrid Subset

Complete-query CFM-ID + MS2DeepScore hybrid subset evidence is available for `2` selected queries with full candidate sets: Top-1 `0.0`, Top-5 `0.5`, Top-10 `0.5`, and MRR `0.1070422535211267`.
Candidate spectra are generated by CFM-ID, so this is a complete-query CFM-ID + MS2DeepScore hybrid subset, not native MS2DeepScore and not a full CASMI benchmark.

## External Public Benchmark Context

ICEBERG CASMI22 public retrieval context is available at `results/external_public_benchmarks/iceberg_casmi22_retrieval/`, covering Random, CFM-ID, NEIMS, FixedVocab, MassFormer, and ICEBERG from the local vendor notebook outputs.
These public CASMI22 retrieval results are external context. They should not be described as a direct apples-to-apples head-to-head against FragAnnotor unless the same candidate sets, preprocessing, and splits are harmonized.

## External Public Model Audit

- FIORA status: `smoke_failed`.
- FIORA main-table inclusion: `False`.
- Reason: FIORA smoke command returned 1; no candidate-ranking benchmark was generated.

## Interpretation

- PFAS locked-test ranking supports the selected primary FragAnnotor policy within the frozen PFAS benchmark.
- CASMI2022 native SIRIUS formula-only ranking completed; CASMI FragAnnotor is available as an audited fixed formula/fragment component-score mode and as a separate frozen trained-neural checkpoint report.
- The trained neural checkpoint CASMI result is substantially weaker than the fixed component-score mode, so it should be reported as a checkpoint audit result rather than the primary CASMI ranking policy.
- CFM-ID native binary compatibility was repaired, but full CASMI candidate ranking remains runtime-blocked and is not replaced with fallback scores.
- No result with `native_or_fallback=native_unavailable` should be described as a completed native baseline.
- MS2DeepScore native comparison is blocked until a complete full-CASMI per-candidate spectrum library is available; current MS2DeepScore evidence is a CFM-ID-generated hybrid subset.
- Pairwise rank-delta statistics exclude unavailable baselines and non-finite true-rank pairs; missing true ranks are counted separately and are not replaced with sentinel ranks.
- SIRIUS is used here as molecular formula plausibility evidence, not as a synthetic spectrum generator or CSI:FingerID structure predictor.

## Manuscript Readiness

- PFAS locked-test expert-fusion benchmark: ready as an internal frozen benchmark, with conservative claims.
- PFAS ablation and case-study package: ready for manuscript drafting, subject to the external-validation limitation.
- CASMI benchmark: partially ready; SIRIUS formula-only native baseline and FragAnnotor formal fixed component-score mode completed, while native CFM-ID and MS2DeepScore remain blocked.
- SOTA comparison: partially ready; public ICEBERG/MassFormer/NEIMS CASMI22 retrieval context is included with provenance, but do not claim direct head-to-head superiority until candidate sets and preprocessing are harmonized.

## Remaining Blockers

- Native CFM-ID full CASMI scoring is prepared via direct and precomputed manifests, but full supported-query metrics remain blocked until all candidate-spectrum shards and query-ranking shards complete.
- Native MS2DeepScore is blocked because the benchmark lacks a complete full-CASMI candidate spectrum library; current CFM-ID-generated hybrid subsets must not be called native MS2DeepScore.
- The CASMI trained neural checkpoint result is complete, but it underperforms the fixed component-score mode and should not be used to claim neural superiority.
- A strong SOTA claim is blocked until FragAnnotor, CFM-ID, SIRIUS/CSI, ICEBERG, MassFormer, NEIMS, and MS2DeepScore are compared on a harmonized CASMI candidate set with the same preprocessing and metrics.
- PFAS results remain an internal frozen locked-test benchmark and are not independent external validation.

## Exact Reproduction Command

```bash
python scripts/run_benchmark.py --dataset both --native-baselines --allow-fallback false --run-ablation --export-query-level --select-case-studies --output-dir results --seed 20260628
```

## Known Limitations

- CASMI native benchmark execution is incomplete: SIRIUS formula-only scores, FragAnnotor fixed component scores, and a frozen trained neural checkpoint report are available, but CFM-ID full candidate ranking is runtime-blocked and MS2DeepScore has no complete full-CASMI candidate spectrum library.
- PFAS results depend on the frozen candidate matrix generated in the transformation-product workflow.
- The benchmark does not establish deployment-ready thresholds or universal LC-MS/MS prediction performance.
