# Harmonized SOTA Rerun Readiness

No ICEBERG/MassFormer/NEIMS direct harmonized CASMI rerun is marked complete by this audit.

## Current Status

### ICEBERG

- `current_status`: `wrapper_smoke_passed_full_candidate_rerun_not_started`
- `smoke_status`: `predicted_spectrum`
- `smoke_predicted_peak_count`: `100`
- `required_next_step`: Implement and run a resumable batch/shard ICEBERG candidate-set predictor; do not use per-candidate smoke output as ranking evidence.

### MassFormer

- `current_status`: `wrapper_smoke_passed_full_candidate_rerun_not_started`
- `smoke_status`: `predicted_spectrum`
- `smoke_predicted_peak_count`: `95`
- `required_next_step`: Implement and run a resumable batch/shard MassFormer candidate-set predictor; do not use smoke output as ranking evidence.

### NEIMS

- `current_status`: `no_validated_wrapper_or_checkpoint`
- `smoke_status`: `not_run_no_validated_wrapper`
- `smoke_predicted_peak_count`: `0`
- `required_next_step`: Add or locate a NEIMS-compatible inference wrapper and checkpoint, then run the same candidate-set ranking protocol.
