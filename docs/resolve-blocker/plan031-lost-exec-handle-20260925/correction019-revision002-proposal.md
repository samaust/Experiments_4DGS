# Correction019 plan revision 002 — reboot retirement as an edit/readiness gate

## Reason

Candidate015's exact Main handle 13761 returned live at 2026-09-25T12:48:23Z, then became unpollable after the administrator-reported reboot. The exact same handle now returns `Unknown process id 13761`, not an exec terminal receipt. An independently reviewed audit confirms that the reboot retired Candidate015's local execution job and descendants and releases its local B/H capacity charge. The captured unchanged suite output remains a failed historical result: 73 tests, 81 failures, 47 errors.

Correction019's original plan required a successful exact Main terminal result before changing source. That condition is no longer recoverable through available tools. This revision permits the independently proven local-job retirement to satisfy only the operational safety prerequisite for read-only source revalidation and the two-call source correction. It does not reinterpret the missing terminal as success or make Candidate015 acceptable.

## Narrow amended sequence

1. Independently verify the reviewed reboot-retirement evidence, the poll086 exact-handle error, and current absence of the owned workload. Keep Candidate015's Main terminal result recorded as unavailable and its suite recorded as failed. Keep its identity, index, and output paths consumed.
2. Reverify the recorded source baseline and active interpreter API. Apply only the two substitutions already in Correction019 plan001: replace `os.pidfd_send_signal` with `signal.pidfd_send_signal` in `signal_job_pidfd`, preserving every argument and surrounding branch/exception behavior. Add no test and change no other path.
3. Obtain independent review of the exact changed source and hashes before running code.
4. Run the authorized focused checks, then the unchanged full CPU-only serial diagnostic, with fresh source/authority hash, artifact-capacity, process/thread-ownership/capacity, output-path, and high-water/index preflights before each run. Use a fresh attempt index and vacant output paths; never reuse Candidate015's identity or paths. Capture and independently review each exact Main handle and terminal result. Preserve every failure.
5. Continue Plan031 in its existing serial order. Do not run the final aggregate until its existing diagnostic, audit, and acceptance gates pass.

## Unchanged constraints

This revision changes only the prerequisite for local source editing and focused/full retesting after independently audited local-job retirement. It does not waive Plan049's requirement for an exact terminal receipt to accept a run: Candidate015 remains failed/unaccepted because no exact terminal result was recovered. It preserves CPU-only execution, serial testing, `B+max(1,H)≤8`, the 150 GiB artifact cap, original assertions and behavioral deadlines, source scope, no PID/self-report identity, and all fresh independent review and launch/admission requirements. No source edit, test, diagnostic launch, identity reuse, or aggregate is authorized until this exact revision receives independent PASS review.
