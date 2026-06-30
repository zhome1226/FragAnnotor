# CASMI Native Baseline And Neural Completion Report

## Summary

This update resolves the CASMI trained FragAnnotor neural checkpoint request and narrows the two remaining native baseline gaps without fabricating unavailable results.

| item | status | benchmark decision |
| --- | --- | --- |
| Native CFM-ID | runtime-blocked | A cfmid4-compatible native binary was found and smoke-tested, but full CASMI candidate ranking is not reported because timing probes did not complete within 15 minutes. |
| Native MS2DeepScore | blocked | MS2DeepScore requires spectrum-to-spectrum inputs; the CASMI structure-candidate benchmark lacks a complete per-candidate spectrum library and configured pretrained MS2DeepScore model. |
| Trained FragAnnotor neural model on CASMI | completed | Frozen checkpoint inference was run report-only on all 229 CASMI queries with no CASMI training or weight tuning. |

## Trained Neural CASMI Result

Source package: `results/casmi2022_fragannotor_trained_neural_v1/`

| metric | value |
| --- | ---: |
| Top-1 | 0.008733624454148471 |
| Top-5 | 0.013100436681222707 |
| Top-10 | 0.026200873362445413 |
| MRR | 0.017259607587748645 |
| Mean Top-1 Tanimoto | 0.11306586455794747 |
| Molecular formula accuracy | 0.462882096069869 |

Training-pair canonical SMILES overlap with CASMI test structures was false in the generated audit. This result is substantially weaker than the fixed component-score CASMI mode, so it should be reported as a frozen checkpoint audit, not as evidence that the trained neural model is the primary CASMI ranking policy.

## CFM-ID Native Status

Source package: `results/native_cfmid_casmi/`

The previous incompatible binary failed with `Invalid Feature Configuration` / `NLRootMatrixFPN10`. A compatible binary was identified at:

`/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin/cfm-id`

It passed a 3-candidate cfmid4 smoke run. Full CASMI scoring remains blocked because a 1241-candidate query and a 100-candidate no-MGF timing run both exceeded 15 minutes. Partial CFM-ID outputs are readiness evidence only and are not included as benchmark scores.

## MS2DeepScore Native Status

Source package: `results/native_ms2deepscore_casmi/`

MS2DeepScore is not a structure-to-spectrum generator. It scores spectrum pairs, so a fair CASMI structure-candidate ranking requires a measured or predicted spectrum for every candidate plus a configured pretrained MS2DeepScore model. Those resources are not present in the repository. CFM-ID predicted spectra were not substituted because that would be a hybrid CFM-ID plus MS2DeepScore baseline rather than native MS2DeepScore.

## Claim Guardrail

Do not claim completed native CFM-ID or native MS2DeepScore CASMI Top-k metrics from this update. Do claim that the CFM-ID native runtime path was repaired enough to pass smoke testing, that the full CFM-ID CASMI run is runtime-blocked, and that the trained FragAnnotor neural checkpoint CASMI report is now complete.
