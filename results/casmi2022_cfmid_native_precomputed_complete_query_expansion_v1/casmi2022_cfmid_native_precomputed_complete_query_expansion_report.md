# CASMI2022 CFM-ID Complete-Query Expansion Attempt

Do not report query 35 as completed CFM-ID ranking until all 233 candidate spectra are predicted and cfm-id-precomputed ranks the full candidate set.

## Current Query 35 Status

|   query_id |   candidate_count |   predicted_spectrum_ids |   missing_candidate_spectra |   ranked_rows |   true_rank | status                            |
|-----------:|------------------:|-------------------------:|----------------------------:|--------------:|------------:|:----------------------------------|
|         35 |               233 |                       88 |                         145 |             0 |         nan | partial_missing_candidate_spectra |

## Runtime Interpretation

Initial 30-minute expansion reached 64/233 predicted spectra. Chunked resume then advanced query 35 to 88/233 predicted spectra; 145 remain missing. Ranking is still skipped until all candidate spectra are available.

## Next Resume Command

```bash
python3 scripts/run_cfmid_complete_query_chunked_resume.py --query-id 35 --chunk-size 3 --max-chunks 5 --timeout-seconds 120
```
