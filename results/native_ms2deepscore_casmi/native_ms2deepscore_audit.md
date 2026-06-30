# Native MS2DeepScore CASMI Audit

Status: `blocked_no_candidate_spectrum_library`

MS2DeepScore is a spectrum-to-spectrum similarity model. The current CASMI2022 benchmark is a structure-candidate ranking task, and no complete per-candidate spectrum library or configured pretrained model is present.

Do not report MS2DeepScore CASMI Top-k metrics. MS2DeepScore scores spectrum pairs; the CASMI structure-candidate benchmark lacks a complete per-candidate measured or predicted spectrum library and no configured pretrained MS2DeepScore model file is present. CFM-ID predicted spectra were not substituted, because that would be a hybrid CFM-ID plus MS2DeepScore baseline rather than native MS2DeepScore.

## Hybrid Baseline Protocol

- Generate candidate spectra for every CASMI candidate with a clearly named generator such as CFM-ID or ICEBERG.
- Load a documented pretrained MS2DeepScore model and convert both query and candidate spectra to matchms Spectrum objects.
- Score query spectrum versus every generated candidate spectrum with MS2DeepScore.
- Rank candidates by MS2DeepScore similarity and label the model as '<generator> + MS2DeepScore hybrid', not native MS2DeepScore.
- Report generator coverage, failed candidates, adduct/ion-mode assumptions, and candidate_limit if any.
