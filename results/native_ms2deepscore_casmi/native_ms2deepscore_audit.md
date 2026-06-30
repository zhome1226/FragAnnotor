# Native MS2DeepScore CASMI Audit

Status: `blocked_no_candidate_spectrum_library`

MS2DeepScore is a spectrum-to-spectrum similarity model. The current CASMI2022 benchmark in this repository is a structure-candidate ranking task: each query has candidate structures, but there is no complete measured or predicted spectrum library for every candidate and no configured pretrained MS2DeepScore model file.

Decision: no native MS2DeepScore Top-k CASMI metrics are reported. The benchmark must not replace missing candidate spectra with deterministic proxies or silently use CFM-ID-generated spectra as a native MS2DeepScore baseline.
