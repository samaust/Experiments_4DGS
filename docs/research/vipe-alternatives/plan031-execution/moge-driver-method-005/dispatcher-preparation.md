# Qualification002 dispatcher and producer preparation

New `scripts/basketball_vipe_depth_driver_qualification_recovery.py` delegates
checked request/result authority to `depth_driver_qualification_recovery` and
requires current D6 source records, an actual request, no loader/path injection,
a fresh owned output/log/cache and no active attempt. It uses the existing
supervisor with 180 seconds total, a 30-second cleanup reserve and seven CPU
workers. Its 64 MiB attempt cap includes result files, retained supervisor cache
and log; 64 KiB remains reserved for terminal evidence. A real clean completed
finish, exact result and no active attempt are required before publishing the
retained finish. The authority owner checks original failed001 and completed
diagnostic001 evidence, exact trace bytes and the new matching REVIEW/DO.

New method005 `producer.py` preserves method004 science, source/interpreter and
dependency checks, no-inference guards and exactly two strict CPU weight loads.
It imports only the new qualification002 authority. Before CUDA imports, it
verifies and executes the exact reviewed `network_guard.py` bytes. The v2 result
binds that guard and the literal creation-only exception:
`socket(AF_UNIX=1, SOCK_SEQPACKET|SOCK_CLOEXEC=524293, protocol=0)`. Connection,
transfer and io_uring denials remain in the independently reviewed guard.
Finalization uses the new authority's accepted qualification proof. No existing
native-map guard selection changes automatically.

Actual dispatch remains unapproved. Integrate the independently reviewed guard
commit `68d32f7f`, authority/ledger hook and this preparation into the canonical
checkout after the current source freeze. Mandatory source/supplemental and
combined CPU qualification must bind both new executables and the exact guard.
Use the new dispatcher with `--request <new002-immutable-request>` only after
fresh reviewed authority and live checks. Historical dispatcher001, producer004,
failed attempts and diagnostic evidence remain unchanged.

Eleven CPU fake boundary cases pass, including exact cleanup reserve, current
source forwarding, fixture/injection/active rejection, fresh log ownership,
clean-finish acceptance, owned artifact monitoring, exact guard binding without
installing a real filter, and preserved inference prohibition. Mypy passes for
both executables. Standards and Spec reviews have no unresolved findings after
correcting the per-attempt cache/log accounting gap. Private immutable command
captures retain all failed and passing validation attempts. No actual driver,
model, GPU, installation, network or production ledger operation was performed.

## Stable syscall trace envelope

Qualification002 uses the exact diagnostic001 strace executable and filters,
checked by the independent authority. The worker writes `worker-result.json`
and its expected trace path. After tracer exit and supervisor child checks,
the dispatcher validates and publishes `result.json` with exact raw worker
and stable trace records. The protected clean finish binds this envelope.
A failed clean attempt retains a trace record without a passing result;
uncertain cleanup retains the raw trace without claiming stable acceptance.
Freshness and artifact checks include both syscall trace and retained receipt.

Thirteen focused preparation cases and ten real authority cases pass together
(23 total), including a private fixture ledger through the public envelope
boundary with the real request/result validators. The final type check passes
for both executables. Independent Standards and Spec reviews have no remaining
actionable findings. Four separate trace-follow-up command captures measure
3.010930487002043 seconds; these exclude the previously reported baseline
inventory and all actual execution. No actual strace, driver, model, GPU,
installation, network or production ledger operation was performed.
