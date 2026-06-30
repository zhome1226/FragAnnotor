# CASMI Gap Resolution Update

This update records the state after adding the selected complete-query CFM-ID + MS2DeepScore hybrid subset. It does not change model weights, tune on CASMI, or claim full native baseline completion.

## Current Status

| Gap | Current state | Evidence | Claim guardrail |
| --- | --- | --- | --- |
| CFM-ID complete CASMI native ranking | Still blocked for full CASMI | Full precomputed manifest exists for 170 supported `[M+H]+`/`[M-H]-` queries and 936,483 unique candidate spectra. A selected complete-query native CFM-ID subset is completed for query `16` with 103 candidates, Top-5 `1.0`, MRR `0.2`. | Report the complete-query result only as selected subset evidence, not as full CASMI CFM-ID. |
| MS2DeepScore reasonable candidate-ranking benchmark | Partially improved, still blocked for full CASMI/native | MS2DeepScore 2.7.2 CPU environment and pretrained model cache are verified. A selected complete-query CFM-ID + MS2DeepScore hybrid subset is completed for query `16` with 103 CFM-ID-generated candidate spectra, Top-5 `1.0`, MRR `0.2`. | Label as CFM-ID-generated hybrid, not native MS2DeepScore and not full CASMI. |
| Trained neural FragAnnotor on CASMI | Completed but weak report-only result | Frozen checkpoint CASMI report: Top-1 `0.008733624454148471`, Top-10 `0.026200873362445413`, MRR `0.017259607587748645`; training overlap audit found no CASMI canonical SMILES overlap. | Do not use as primary CASMI evidence or claim effective neural CASMI performance. |
| CASMI pairwise rank delta anomaly | Fixed | Pairwise deltas now require completed models and finite true-rank pairs. Current max absolute reported rank delta is `69.28125`; sentinel-scale delta detected: `False`. | Keep missing ranks as missing; do not replace unavailable baselines with sentinel ranks. |
| Strong SOTA claim | Still blocked | ICEBERG/MassFormer/NEIMS remain imported public context rather than direct harmonized reruns on the same candidate set, preprocessing, adduct assumptions, and metrics. | Do not claim SOTA until harmonized direct comparison is complete. |

## Bottom Line

The current repository has stronger subset evidence for both native CFM-ID and CFM-ID + MS2DeepScore, plus a fixed pairwise rank-delta audit and a formal trained-neural CASMI report. The remaining blockers are full native CFM-ID execution, a complete full-CASMI candidate spectrum library for MS2DeepScore/hybrid scoring, and harmonized direct comparisons before any strong SOTA claim.
