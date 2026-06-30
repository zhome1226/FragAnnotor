# CFM-ID Precomputed Full CASMI Manifest

This package prepares a faster native CFM-ID CASMI path by caching candidate spectra before ranking.

- Supported queries: `170`
- Unsupported queries: `59`; counts: `{'[M+Na]+': 59}`
- Supported candidate rows: `1062950`
- Candidate-spectrum shards: `9365` of `100` unique candidates each
- Query-ranking shards: `34` of `5` supported queries each
- Run output directory: `/home/zhome/ec_structure/github_export/FragAnnotor/results/casmi2022_cfmid_native_precomputed_full_v1`

Run candidate-spectrum shards first, then query-ranking shards, then `scripts/summarize_cfmid_precomputed_full_progress.py`.

Report full native CFM-ID CASMI metrics only after every candidate spectrum shard and every supported query-ranking shard completes; [M+Na]+ remains unsupported unless a compatible CFM-ID model is added.
