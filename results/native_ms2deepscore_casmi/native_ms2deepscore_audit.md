# Native MS2DeepScore CASMI Audit

Status: `blocked_full_casmi_no_candidate_spectrum_library`

MS2DeepScore is a spectrum-to-spectrum similarity model. The current CASMI2022 benchmark is a structure-candidate ranking task. The pretrained environment is verified, and a CFM-ID-generated complete-query hybrid subset is available, but no complete full-CASMI per-candidate spectrum library is present.

Do not report full-CASMI native MS2DeepScore Top-k metrics yet. MS2DeepScore scores spectrum pairs; the pretrained model and CPU environment are externally available/verified, and a CFM-ID-generated complete-query hybrid subset is available when cached candidate spectra exist. The full CASMI structure-candidate benchmark still lacks a complete per-candidate measured or predicted spectrum library. CFM-ID predicted spectra must be labeled as a CFM-ID plus MS2DeepScore hybrid baseline rather than native MS2DeepScore.

## Hybrid Baseline Protocol

- Generate candidate spectra for every CASMI candidate with a clearly named generator such as CFM-ID or ICEBERG.
- Load a documented pretrained MS2DeepScore model and convert both query and candidate spectra to matchms Spectrum objects.
- Score query spectrum versus every generated candidate spectrum with MS2DeepScore.
- Rank candidates by MS2DeepScore similarity and label the model as '<generator> + MS2DeepScore hybrid', not native MS2DeepScore.
- Report generator coverage, failed candidates, adduct/ion-mode assumptions, and candidate_limit if any.
