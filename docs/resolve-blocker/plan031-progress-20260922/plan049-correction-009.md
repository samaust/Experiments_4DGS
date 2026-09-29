# Plan049 correction009 — exact sole-exec structure and exclusive identity witnesses

Prepared 2026-09-23 UTC after independent correction008 recheck. This is a narrow correction within correction008 authorization; no runtime launch is authorized by this record. Source gates remain launch_ready=false until a distinct validator rechecks the changes.

## Findings

1. **V008-1 exact sole-exec command:** `s1_validation_contract.py:489–492` compares `shlex.split(cmd)` to expected argv. Replacing the initial space after `exec` with a literal newline yields the same tokens but a different shell parse (`exec` command followed by Python without exec). Token equality does not prove one replacing command.
2. **V008-2 exclusive identity witnesses:** in `test_execution_mutations` retained nested-identity controls at recovery test lines 1043–1049 replace logical R identity/admission references with physical fixture paths and leave proof/readiness records stale after identity mutations. Generic ValueError can still pass due to unrelated graph mismatch if the intended identity validator stops rejecting. The finding is exclusive attribution/evidence quality, not that current checks all fail before target validation.

## Planned change

Limited to the same correction008 implementation files: `scripts/vipe_benchmark/s1_validation_contract.py`, `tests/test_vipe_benchmark_s1_recovery.py`, and `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` only if required by consistent command evidence. Preserve the explicitly authorized `session-bound/v1` trust model and every other Plan049 rule.

- Bind the sole launch command to exact canonical safely quoted command text (e.g. `shlex.join(expected_argv)`), not tokenized equivalence. Require exact tool start args for the command and execution-affecting `shell`, `login`, `workdir`, `tty`, `sandbox_permissions`, `yield_time_ms`; reject shell metacharacter/newline/command-chain alternatives. Add controls for canonical command acceptance; newline, altered structure/command, cwd, tty, permission, yield and shell-option rejection.
- Repair retained nested-identity mutation fixtures to maintain logical fixed R paths through the fixture router and rehash the complete affected identity→readiness→event→proof→admission→note chain. Establish a valid unmutated graph on the same routed path first, mutate one target field at a time, and assert target-specific rejection (or instrument the named validator boundary) so unrelated stale/physical-path evidence cannot satisfy the expected rejection. Preserve existing assertions and declaration/callback map.
- No test/project invocation, runtime launch, process/session action, admission, mode change, source expansion, new method/callback, or commit during correction. Static syntax, exact preservation, source-record/hash graph and scoped diff checks only.

## Independent recheck and handoff

A distinct validator must verify the exact corrected shell parse invariant and each exclusive identity mutation witness, then recheck complete correction008 preservation/scope/hash manifests. Main can proceed only if the validator reports static launch_ready=true for current exact hashes. Failed/ambiguous send handling and all live external evidence remain Main's responsibility. No B1–B4 runtime criterion is accepted here.

## Evidence basis

- Independent report: `validate-049-correction008-report-001.md`, SHA-256 `48dde6f20b9feaca8812ce8c0dc0b51e0ffebec326c8ec915e5f271411faac6c`.
- Independent assessment: `validate-049-correction008-assessment-001.json`, SHA-256 `8e653d768fd8a7d4b560482f1c6c36c73ec163835862593d887cf23d3741a992`.
- Implemented correction008 source hashes: contract `120363f0518a2c838da839162b015a4f736ef433d1bdb70f5b9d63f0b09aba33`, recovery tests `aeeb6a12adad3a1d033a3ae8321d410555049a68ac756eedd442a0165dda6d10`, driver `515e6832da0cbac4c8b1d19efa3a953bb1030f8ec9467f7508cabe4460992c29`.

