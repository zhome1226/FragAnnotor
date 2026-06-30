# CASMI2022 CFM-ID Complete-Query Expansion Record

This directory records native CFM-ID complete-query expansion attempts. Reportable
Top-k/MRR values are now rebuilt from completed ranked work directories under:

`results/casmi2022_cfmid_native_precomputed_complete_query_subset_v1/`

## Current Reportable Subset

The formal complete-query subset currently contains five completed full-candidate
CASMI queries: `16`, `34`, `35`, `78`, and `145`. Each query uses its full
candidate set, but this is still a selected complete-query subset and must not be
reported as a full CASMI CFM-ID baseline.

Current native CFM-ID complete-query subset metrics:

- Top-1: `0.0`
- Top-5: `0.2`
- Top-10: `0.2`
- MRR: `0.05426704980726227`

## Partial Attempts

Query `177` remains a partial attempt and is excluded from the reportable subset:
`117/336` candidate spectra are available and `219` candidate spectra remain
missing. It should not contribute to Top-k/MRR until all candidate spectra are
generated and the full candidate set is ranked.

## Guardrail

Use this directory as runtime provenance only. The authoritative reportable
subset files are the rebuilt CSV/JSON/Markdown artifacts in
`results/casmi2022_cfmid_native_precomputed_complete_query_subset_v1/`.
