# Native CFM-ID CASMI Runtime Audit

Status: `runtime_blocked_full_casmi_not_reported`

A CFM-ID 4.x-compatible native binary was identified at `/home/zhome/ec_structure/external_ms_models/vendor/cfm-id-code/cfm/build_local_py36/bin/cfm-id` and passed a 3-candidate smoke run with the cfmid4 `[M+H]+` model. The previously audited conda binary remains incompatible with the cfmid4 feature config (`NLRootMatrixFPN10`).

Full CASMI candidate ranking is not reported because timing probes did not complete within 15 minutes for either a 1241-candidate query or a 100-candidate subset. Partial/generated MGF files are readiness artifacts only and are not used as benchmark scores.

Decision: keep CFM-ID as runtime-blocked in the main CASMI benchmark until a complete native score table exists.
