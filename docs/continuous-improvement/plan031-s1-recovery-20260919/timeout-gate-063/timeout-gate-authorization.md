# Timeout-mode gate duration authorization

## Verbatim user instructions (2026-09-27, pi session)

Instruction 1:

> I want to fix this by increasing the Timeout-mode gate duration.
> The current 300 seconds cap was most likely chosen arbitrarily.
> A short duration cap was likely chosen to optimize the implementation toward minimizing duration.
> Propose a new Timeout-mode gate duration that fits that goal while being realistic for the amount of work to do.

Instruction 2 (confirming the proposal):

> I confirm 360 s

## Proposal record

Proposed value: **360 s**, replacing the 300 s aggregate timeout-mode cap.
Diagnostic cap (120 s) is unchanged — diagnostic mode is a focused work class
that never contains the full suite.

Measurement basis (post-R18-1 sources, boot `ba1b4efe-ee43-4088-86df-706c41cfac12`,
pi no-timeout aggregates, full 249-test owned suite):

| run | elapsed s |
|---|---|
| aggregate-061-003 | 321.24 |
| aggregate-061-004 | 320.28 |
| aggregate-061-005 | 320.79 |
| aggregate-061-006 | 326.65 |

Worst case 326.65 s; spread ~6 s (~2%). This is the floor of the mandated
work (the R18-1 reducible pool is already removed; the remainder is the
full-510 guard work plus the 114 mandated re-qualifications).

Rationale: 360 = worst measured + 33 s (~10%) margin — realistic against
boot-to-boot and transient variance while leaving only ~9% headroom, so the
gate still binds and preserves the "optimize toward minimizing duration"
pressure. The old 300 s sat below the mandated floor (326.65 s) and was
unachievable by construction. Rejected: 340 s (flake-thin, 4% margin),
420 s (~25% headroom absorbs regressions), 510 s+ (never binds).

## Scope granted by this authorization

- Raise the aggregate timeout-mode cap 300 → 360 in the two source constants
  (`s1_validation_capture.py` bound/default, `s1_validation_contract.py`
  timed-execution bound).
- Declare the owned-note environment precondition of the owned-only
  `test_progress_plan047_ownership` via the house `control_record` pattern,
  so the timed-mode (non-owned) gate run reports the suite result cleanly
  instead of an environmental KeyError. In the owned no-timeout environment
  the test is exercised in full, unchanged.
- Validate with one timed-mode aggregate at `--timeout 360` (non-owned
  direct module-form launch, the same environment as all prior 300 s
  measurements) and one no-timeout pi re-validation (source set changes).

Not granted: any suite/fixture/gate shrink, any timeout/cap reduction, any
change to the 120 s diagnostic cap, any GPU/model/production work, any
Plan049/pi-launch chain change, any new owned-timeout provenance class.

## Amendment — Option B (user-confirmed, 2026-09-27)

The 360 s cap was empirically falsified before acceptance. The first
timed-mode 360 s attempt (`aggregate-063-001`) timed out at 360.1 s, and the
true non-owned timed-mode wall time (measured by replicating the capture
launch without the external kill, `measure-063-001`) was **430.64 s**:
235 ok / 14 errors / 0 failures. The 14 non-owned errors were owned-only
tests performing heavy partial work (~234 s across three `s1_recovery`
tests) before failing on `KeyError: 'S1_OWNED_ROOT_NOTE'` — non-mandated
dead weight in timed mode.

The user was presented two options (A: cap 480 s with no further test
changes; B: owned-note precondition guards on the 14 owned-only tests plus
an empirical ~240 s cap) and confirmed:

> B

Scope granted by the amendment (replaces the 360 s plan):

- Declare the owned-note precondition on the 14 owned-only tests (11 in
  `tests/test_vipe_benchmark_supervisor.py`, 3 in
  `tests/test_vipe_benchmark_s1_recovery.py`) using the house guard pattern;
  the five parameterized guards re-fire their declared `SUBTEST_CASES`
  callbacks so the receipt callback-multiplicity contract holds; each guard
  writes a control/precondition record into the run directory; owned
  no-timeout runs exercise every test in full, unchanged.
- Final cap: **240 s** — post-guard non-owned measurement
  (`measure-063-002`): 249 ok / 0 / 0 in **198.23 s** → 1.25x ≈ 248 s →
  rounded to 240 s (measured run binds at 83% of cap; ~20% margin over the
  pre-guard noise floor).
- Align the `timeout_seconds=300` synthetic receipt fixture in
  `tests/test_vipe_benchmark_s1_recovery.py` with the 240 s cap; mutation
  tests keep their 300 s rejection cases (still correctly rejected).
- Validation: timed-mode aggregates under `timeout-gate-063/`
  (002: fixture-cap mismatch rc=1; 003: callback-multiplicity mismatch rc=1;
  004: accepted at 240 s) then one no-timeout pi re-validation
  (`aggregate-061-007`) on the final source bytes.
