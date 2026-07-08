# Native MS2DeepScore CASMI Audit

Status: `blocked_native_library_missing_full_cfmid_hybrid_complete`

MS2DeepScore is a spectrum-to-spectrum similarity model. The current CASMI2022 benchmark is a structure-candidate ranking task. The pretrained environment is verified, and CFM-ID-generated hybrid scoring is tracked separately, but no complete full-CASMI per-candidate spectrum library independent of CFM-ID is present.

Full-supported CFM-ID + MS2DeepScore hybrid status: `completed_full_supported_hybrid`.

Do not report full-CASMI native MS2DeepScore Top-k metrics. MS2DeepScore scores spectrum pairs; the pretrained model and CPU environment are externally available/verified, and CFM-ID-generated hybrid outputs are valid only when labeled as CFM-ID plus MS2DeepScore. The native CASMI structure-candidate benchmark still lacks a complete per-candidate measured or non-CFM-ID predicted spectrum library independent of CFM-ID.

## Hybrid Baseline Protocol

- Generate candidate spectra for every CASMI candidate with a clearly named generator such as CFM-ID or ICEBERG.
- Load a documented pretrained MS2DeepScore model and convert both query and candidate spectra to matchms Spectrum objects.
- Score query spectrum versus every generated candidate spectrum with MS2DeepScore.
- Rank candidates by MS2DeepScore similarity and label the model as '<generator> + MS2DeepScore hybrid', not native MS2DeepScore.
- Report generator coverage, failed candidates, adduct/ion-mode assumptions, and candidate_limit if any.
