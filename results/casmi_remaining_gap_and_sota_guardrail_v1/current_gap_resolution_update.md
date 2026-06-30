# CASMI Gap Resolution Update

This update records the state after extending the selected complete-query native CFM-ID subset and the CFM-ID + MS2DeepScore hybrid subset to nine full-candidate-set CASMI queries. It does not change model weights, tune on CASMI, or claim full native baseline completion.

## Current Status

| Gap | Current state | Evidence | Claim guardrail |
| --- | --- | --- | --- |
| CFM-ID complete CASMI native ranking | Still blocked for full CASMI | Full precomputed manifest exists for 170 supported `[M+H]+`/`[M-H]-` queries and 936,483 unique candidate spectra. A selected complete-query native CFM-ID subset is completed for nine full-candidate-set queries (`16`, `34`, `35`, `39`, `46`, `53`, `68`, `78`, `145`) with Top-5 `0.2222222222222222`, Top-10 `0.2222222222222222`, and MRR `0.08671697767958597`. | Report the complete-query result only as selected subset evidence, not as full CASMI CFM-ID. |
| MS2DeepScore reasonable candidate-ranking benchmark | Partially improved, still blocked for full CASMI/native | MS2DeepScore 2.7.2 CPU environment and pretrained model cache are verified. A selected complete-query CFM-ID + MS2DeepScore hybrid subset is completed for the same nine full-candidate-set queries using CFM-ID-generated candidate spectra, with Top-5 `0.2222222222222222`, Top-10 `0.3333333333333333`, and MRR `0.08139700702143969`. | Label as CFM-ID-generated hybrid, not native MS2DeepScore and not full CASMI. |
| Trained neural FragAnnotor on CASMI | Completed but weak report-only result | Frozen checkpoint CASMI report: Top-1 `0.008733624454148471`, Top-10 `0.026200873362445413`, MRR `0.017259607587748645`; training overlap audit found no CASMI canonical SMILES overlap. | Do not use as primary CASMI evidence or claim effective neural CASMI performance. |
| CASMI pairwise rank delta anomaly | Fixed | Pairwise deltas now require completed models and finite true-rank pairs. Current max absolute reported rank delta is `69.28125`; sentinel-scale delta detected: `False`. | Keep missing ranks as missing; do not replace unavailable baselines with sentinel ranks. |
| Strong SOTA claim | Still blocked | ICEBERG/MassFormer/NEIMS remain imported public context rather than direct harmonized reruns on the same candidate set, preprocessing, adduct assumptions, and metrics. | Do not claim SOTA until harmonized direct comparison is complete. |

## Bottom Line

The current repository has stronger subset evidence for both native CFM-ID and CFM-ID + MS2DeepScore across nine selected complete-query CASMI rows, plus a fixed pairwise rank-delta audit and a formal trained-neural CASMI report. The remaining blockers are full native CFM-ID execution, a complete full-CASMI candidate spectrum library for MS2DeepScore/hybrid scoring, and harmonized direct comparisons before any strong SOTA claim.
