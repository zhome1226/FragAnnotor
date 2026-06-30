# Manuscript-Ready Benchmark Tables

This package collects clean tables for manuscript drafting without changing model weights or rerunning benchmark selection.

## Included Tables

- `table1_casmi2022_benchmark.csv`: CASMI2022 main rows plus explicitly labeled CFM-ID subset and trained neural checkpoint audit rows.
- `table2_pfas_locked_test_benchmark.csv`: PFAS locked-test benchmark rows.
- `table3_pfas_ablation.csv`: PFAS no-SIRIUS/full-fusion ablations where available.
- `supplementary_native_tool_audit_and_blockers.csv`: native tool status and blockers.
- `supplementary_remaining_gap_status.csv`: remaining gap audit.
- `supplementary_sota_guardrails.csv`: allowed/disallowed claims.

## Reporting Guardrails

- The CFM-ID subset row is candidate-limited (`first_n_plus_true`) and is not a full CASMI CFM-ID result.
- MS2DeepScore remains blocked for full candidate ranking because no configured pretrained model and complete candidate spectrum library are available.
- The trained neural checkpoint row is report-only and weak; do not use it as primary CASMI evidence.
- Strong SOTA claims remain blocked until all methods are rerun on the same candidate set, preprocessing, adduct assumptions, and metrics.
