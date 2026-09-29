# S1 worker monitor gap recovery

The approved recovery 002 started its worker but failed during `worker_sample`
after 10.944929263 seconds of charged allocation. The terminal record says
`S1 phase deadline reached`; it does not identify which sampling component was
slow. Recovery 002 is consumed and remains terminal. This change prepares a
source correction; it does not authorize or dispatch another GPU attempt.

## Behavior

Every S1 sample still expires one second after dispatch. A sample that misses
that deadline cannot certify resource limits, GPU ownership, worker exit or
result acceptance. During worker monitoring only, the supervisor now allows
up to 15 seconds from the beginning of the monitoring call to obtain a later
fresh sample. The interval is capped by the existing work deadline. The
15-second cap covers the two existing five-second `nvidia-smi` query timeouts
plus five seconds for the budget snapshot, process census and transport. This
is a bounded policy choice; the consumed outcome provides no measurement of
the actual slow component.

A late reply retains its original request ID and is drained before a new
request is sent. If the pre-sample census is late, the original request ID is
sent and drained first because the helper has not yet seen it. The census is
still checked for identity and lineage. A late post-sample census is checked
for the complete process bracket. Late readings can establish a resource
ceiling breach or a definitely foreign GPU PID, and those observations still
stop the worker. They never establish safety. Transport errors, malformed
responses, ownership uncertainty, sustained monitor loss and the original
work deadline remain failures. Initial admission, prelaunch, acceptance and
publication keep their prior deadline behavior.

A recovered gap appends `monitor_gap_recovered` with the job ID, expired sample
count and measured gap duration. There is no ledger or scientific input change
until a future authorized attempt runs this source. The cumulative allocation,
cleanup reserve, frozen configuration and consumed 459-event prefix are not
rewritten.

## CPU validation

Focused real-helper tests cover a late reply followed by a fresh accepted
sample, a late pre-census preserving helper request sequence, exhaustion of
the outer gap, a late resource ceiling breach, and a late foreign GPU PID.
The consumed predecessor test uses the immutable 453-event historical prefix
for its pre-dispatch synthetic review; it never reopens the live identity.

The first aggregate exposed that historical fixture's use of the now-consumed
live 002 identity. The second and third aggregates passed on intermediate
source sets. These preparatory captures were removed after the final run; only
the complete source-bound qualification is retained in this review. The final
`aggregate-timed-004` passed 267 tests in 215.561 seconds under its 240-second
cap, with zero failures, errors or skips. The runner and outer execution
record the same current 78-file source set before and after the run.
[validation.json](validation.json) passes `validate_inner`,
`validate_execution` and `validate_wrapper` against those exact records. Its
`ready_for_live_admission` flag is false because no new identity or live gate
has been prepared. No GPU validation or dispatch was run.

## Remaining work before another GPU attempt

The consumed 002 authorization and source validation cannot authorize another
run. A separately reviewed recovery identity, current source binding and
explicit one-attempt authorization are required. The new identity should bind
the 459-event consumed prefix and this qualified source set. A future host
preflight must verify current GPU exclusivity, assets, request capacity and
ledger state before reservation. No such authorization or dispatch is part of
this change.
