# Harmonized SOTA Rerun Readiness

No ICEBERG/MassFormer/NEIMS direct harmonized CASMI rerun is marked complete by this audit.

## Current Status

### ICEBERG

- `current_status`: `direct_rerun_partial_harmonized_candidate_rerun`
- `smoke_status`: `predicted_spectrum`
- `smoke_predicted_peak_count`: `100`
- `required_next_step`: Continue the resumable ICEBERG candidate-set query shards until all supported queries complete.

### MassFormer

- `current_status`: `direct_rerun_partial_harmonized_candidate_rerun`
- `smoke_status`: `command_failed`
- `smoke_predicted_peak_count`: `0`
- `required_next_step`: Continue the resumable MassFormer candidate-set query shards until all supported queries complete.

### NEIMS

- `current_status`: `no_validated_wrapper_or_checkpoint`
- `smoke_status`: `not_run_no_validated_wrapper`
- `smoke_predicted_peak_count`: `0`
- `required_next_step`: Add or locate a NEIMS-compatible inference wrapper and checkpoint, then run the same candidate-set ranking protocol.
