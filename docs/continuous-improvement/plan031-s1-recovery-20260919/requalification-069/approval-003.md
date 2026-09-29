# S1 third-identity approval

On 2026-09-28 (America/Toronto), the user explicitly approved exactly one GPU
calibration attempt for `S1-calibration-recovery-003` using the prepared
authorization, unchanged scientific inputs and limits, current source
qualification, and intact consumed 459-event ledger. The user explicitly
excluded redispatch of 001 or 002, a consumption reset, reconstruction, new
setup, and downloads.

The approval applies to the prepared 003 identity and reviewed command
`bash scripts/run_s1_calibration_recovery_003.sh --run` only. The host
`--check` gate must report GO before the single dispatch. The approval record
and this note do not themselves reserve or launch a GPU attempt.
