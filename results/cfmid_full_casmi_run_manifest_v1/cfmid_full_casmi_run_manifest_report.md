# Full Native CFM-ID CASMI Run Manifest

This package prepares, but does not execute, the long-running full native CFM-ID CASMI job.

- Supported queries: `170`
- Unsupported queries: `59`; counts: `{'[M+Na]+': 59}`
- Total supported candidate rows: `1062950`
- Shards: `34` of `5` supported queries each
- Full output directory: `/home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_full_supported_v1`

Run `bash results/cfmid_full_casmi_run_manifest_v1/run_all_shards_sequential.sh` for a resumable sequential run, or dispatch rows from `cfmid_full_supported_shards.csv` manually on a scheduler.

Full native CFM-ID CASMI metrics may be reported only after every supported query has a completed full_output_file with candidate_count scored rows; [M+Na]+ remains unsupported unless an appropriate CFM-ID model is added.
