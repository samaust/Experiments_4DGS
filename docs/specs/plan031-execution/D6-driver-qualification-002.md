# D6 qualification002 proposal

Status: REVIEW; no DO has been created. The exact v2 proposal is
`D6-driver-qualification-review-002.json`.

Request one distinct `plan069-D6-driver-qualification-002` attempt, bounded to
180 seconds including explicit 30-second cleanup, 2 GiB device memory, 64 MiB
owned output/cache/log/trace including terminal evidence, and zero downloads.
The existing accepted D6 setup, runtime/source pins and scientific settings remain
unchanged. Global caps and the separate native map attempt limit remain unchanged.

The canonical method005 producer uses the reviewed native socket creation
exception only: `socket(AF_UNIX=1, SOCK_SEQPACKET|SOCK_CLOEXEC=524293, 0)`.
Connection, binding, acceptance, socketpair, send/receive and io_uring operations
remain denied. The retained Python audit guard remains in effect. No broader Unix
communication is requested. This exception removed the observed denial in CPU
fixtures; CUDA recovery remains unproven until actual qualification.

The proposed traced attempt performs driver-aware import and exactly two strict
actual CPU model weight loads. All parameters and buffers must remain on CPU.
No forward pass, inference, benchmark, JIT kernel launch, GPU model load or GPU
tensor allocation is permitted. The tracer and filters match the completed
driver-only diagnostic; send/receive/ioctl contents remain raw to avoid payload
capture. A stable post-exit trace and raw worker-result envelope are retained.

Exact canonical guard, producer, dispatcher, tracer, filter and setup records are
in REVIEW. Its ancestry includes failed qualification001 finish750 and clean
completed diagnostic001 finish777, diagnostic result and exact trace. Neither
consumed attempt is reopened or rewritten. Protected history/ledger checks remain
the execution owner's gate; this metadata preparation does not inspect or mutate
the live ledger.

## Before requesting or using approval

Complete the pending authority/admission fixes and independent implementation
reviews, then freeze current executable sources. Bind a fresh independent D6
source review and passing CPU capture to those bytes. The final authority must
bind the approved producer record as well as the guard and ancestry; dispatcher
bytes are covered by current public source closure. If any proposed guard,
producer or tracer bytes change, preserve this REVIEW and regenerate its bindings
before asking for approval. The preliminary source commit is provenance, not a
claim that later helper changes are already qualified.

Create a separate v2 DO only after explicit approval of the concrete new max1
allocation. Dispatch only after fresh ownership, deadline, artifact, global
budget and protected predecessor checks. A successful002 qualification does not
authorize a native map run or establish image quality. Native D6 guard selection
must separately bind the approved005 grant and accepted002 evidence.

## CPU metadata preparation

Measured canonical proposal/evidence hashing and metadata writing took
0.005625910001981538 seconds; its retained private generation record excludes
editing/reviewer wall time and the terminal capture write. No CUDA, model payload,
runtime imports, live ledger reads/writes or execution approval occurred.
The current producer/dispatcher/guard preparation has separate implementation
reviews; this document is a concrete allocation proposal and binding review.

Independent Standards PASS and Spec PASS; no actionable metadata findings. Both
verified nine physical bindings and the exact v2 allocation contract. Standards
reported 0.003911 seconds verification; Spec reported no timing. These are binding
reviews, not execution approval or proof that pending helper fixes are qualified.
