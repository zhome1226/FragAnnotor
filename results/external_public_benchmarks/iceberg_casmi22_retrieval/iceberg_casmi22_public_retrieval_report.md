# ICEBERG CASMI22 Public Retrieval Benchmark Context

This package imports the CASMI22 public retrieval comparison reported in the local `ms-pred-iceberg-2024` vendor notebook `notebooks/iceberg_casmi22.ipynb`. It provides external/public benchmark context beyond the internal PFAS locked-test.

## Imported Public Retrieval Table

| Method | Cosine sim. | Top-1 | Avg. Tanimoto Similarity |
| --- | ---: | ---: | ---: |
| Random | NA | 0.013 | 0.196 |
| CFM-ID | 0.248 | NA | NA |
| NEIMS (FFN) | 0.361 | 0.086 | 0.333 |
| FixedVocab | 0.409 | 0.073 | 0.324 |
| MassFormer | 0.415 | 0.076 | 0.317 |
| ICEBERG | 0.417 | 0.129 | 0.378 |

## Guardrail

These results are imported from an external vendor notebook with provenance and are not a direct head-to-head rerun inside FragAnnotor. A direct comparison requires harmonizing candidate sets, preprocessing, and splits.
