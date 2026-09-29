# Proposed addendum: diagnostic writes after the original total cutoff

Not authorized or applied. No launch may claim this boundary resolved.

Existing callback: `test_vipe_benchmark_s1_recovery.ReservationClockTests.test_failure_reconciliation::[["kind","str","late"]]`.

The case sets `observation = clock.total_deadline + 1` for an effective 90-second clock. It invokes `preserve_failure`, reads the newly created failure and first-result files, and retains these substantive assertions, including `self.assertEqual(value['elapsed_seconds_from_reservation'],91)`, `self.assertEqual(read_json(record['path'])['error'],'original primary')`, and `self.assertEqual(value['clock_status'],'unverified')`.

Plan048 section3 permits metadata-only diagnostics only within the original cleanup allowance, which ends at `total_deadline`. A source-only implementation cannot both prohibit these new writes after that boundary and create the files required by this old callback. The observed elapsed91 assertion excludes reinterpreting the fixture as inside cleanup. No source-only compliant resolution is proved.

Proposed semantic amendment, requiring main/user plan authority: retain the callback ID but replace its after-cutoff write/read assertions with assertions that original primary class/text remains available in memory, the diagnostic publication is unavailable because C expired, and no open/write/hash/read operation starts after C; separately preserve a before-C diagnostic publication control with the original file/content checks and its actual elapsed value. This changes old substantive assertion expressions and therefore cannot satisfy Plan048's current exact preservation rule without an explicit prospective exception. Historical Plan047 acceptance remains false. Do not silently move the old assertion to dead code or execute it retrospectively as production evidence.

The implementer has paused this disputed boundary, preserved the original test and legacy out-of-window diagnostic behavior, and continues independent source work. B1 and B4 preservation acceptance cannot be claimed complete while the contradiction remains. All tests remain unlaunched; B+max(1,H)≤8.
