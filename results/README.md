# Results Directory

- `environment_audit.json`: OS, Python, Git, package, executable, Java, and CUDA audit.
- `native_baseline_audit.csv/json`: native tool availability and blockers.
- `native_tool_ready_audit.csv/json`: server-side native tool readiness audit from `scripts/setup_native_baselines.sh`.
- `benchmark_results.csv/json`: unified benchmark metrics.
- `predictions/`: per-dataset, per-model candidate-level prediction exports; large full tables are stored as adjacent `.csv.gz` files with a small `.csv` manifest.
- `casmi2022_native_benchmark_summary.csv/json`: CASMI native benchmark status and metrics where available.
- `sota_comparison_summary.csv/json`: unified model comparison table.
- `sota_pairwise_rank_comparison.csv`: paired query-level rank comparisons.
- `sota_bootstrap_confidence_intervals.csv`: bootstrap confidence intervals for Top-10 and MRR differences.
- `ablation/`: FragAnnotor component ablation and weight sensitivity outputs.
- `query_level/`: query-level comparison tables and PFAS Top-10 candidates.
- `case_studies/`: automatically selected PFAS case-study rows and peak-annotation availability status.
- `casmi_fragannotor_adapter/`: CASMI zero-shot formula/fragment adapter components and guardrail audit.
- `external_public_model_audit/`: optional public-model readiness probes such as FIORA smoke execution.
- `stratified/`: PFAS subclass and difficulty-stratified summaries.
- `figures/`: matplotlib-only publication-draft plots.
- `preliminary/`: preserved preliminary fallback CASMI result files.
