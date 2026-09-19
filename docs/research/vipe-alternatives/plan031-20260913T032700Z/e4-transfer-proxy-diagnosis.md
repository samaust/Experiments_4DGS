# E4 transfer proxy diagnosis — 2026-09-19

Two independent problems are evidenced: the active sandbox explicitly blocks the
PyTorch domain, and the worker's synchronous byte-accounting scan can delay its
proxy beyond the client's handshake timeout. The proxy also failed to preserve
an inherited egress route, a separate reproduced application defect.

The setup worker can change the network route even when its `uv` arguments match
the successful manual command. `runtime.setup` replaced inherited HTTPS/ALL proxy
variables with its byte-metering localhost proxy. That proxy then resolved and
connected directly to the package host. It did not chain through the inherited
HTTP CONNECT proxy. Consequently, manual `uv` could use the working inherited
egress route while the worker bypassed it, when those variables are inherited.
This is a reproduced application defect, not yet a complete historical diagnosis.

The saved E4 attempts reported one upstream connection, zero received bytes and
roughly 12–14 seconds before `CalledProcessError`. Those records alone do not
establish an upstream PyTorch outage. The earlier attribution to an upstream
network failure was unsupported; application-level route replacement is a
reproduced defect. `runtime.setup` directly calls `subprocess.run` for uv, without
adding bubblewrap. This does not establish which host or Codex network controls
were active outside the worker.

The coordinating agent inspected the in-sandbox environment and found an HTTP
HTTPS proxy and a separate SOCKS ALL proxy, with no proxy credentials. A bounded
read-only HEAD outside the sandbox returned HTTP 200 in about 0.19 s. Subsequent
inspection established that the escalated host command had no inherited proxy,
so that successful HEAD used direct egress. It must not be reported as proof of
the inherited route working. Historical failed workers' exact proxy environment
is not established by these current-context observations. The original metering
proxy also chooses only the first `getaddrinfo` address and makes one connection,
whereas curl/uv can select addresses differently; that remains a distinct candidate
for direct-host discrepancies pending bounded diagnostics.
The local Codex configuration lists a limited domain policy that excludes the
package domains. A corrected in-sandbox proxy diagnostic subsequently returned
the explicit tool-level denial: `Network access to "download.pytorch.org" was
blocked: domain is not on the allowlist for the current sandbox mode.` This
confirms an active sandbox gate. The coordinator stopped external probes; no
global policy was changed and the denial was not bypassed. Relevant package
domains are `download.pytorch.org`, `pypi.org` and `files.pythonhosted.org`.

Outside the sandbox, the corrected direct proxy with a tiny diagnostic root
completed HEAD with HTTP 200 and 5,054 charged bytes. The authoritative study
root, however, took 22.903 seconds for one accounting snapshot in the coordinator's
measurement. The initial snapshot used to run inside CONNECT after the client
had started its connection timeout. Later snapshots also block the single
selector thread. This explains why a working manual network command alone does
not establish that the worker's metered route can respond in time.

The previously suggested manual worker used a new output directory, so setup
would create another `output/environment`; it would not continue the environment
where the user's manual installation succeeded. Read-only installed metadata in
`recovery004/environment` showed torch 2.13.0+cu130, torchvision 0.28.0+cu130 and
NumPy 2.1.3, while `recovery004-manual/environment` had none of those installations.
That metadata is not native import or model qualification.

## Change and boundaries

Setup now selects its inherited HTTPS route before replacing the child proxy
variables. Selection prefers lowercase/uppercase HTTPS_PROXY, then lowercase/
uppercase ALL_PROXY. HTTP_PROXY alone does not govern an HTTPS request. When a
route exists, the metering proxy connects to that HTTP proxy and requests CONNECT
to the package host; destination DNS stays with the upstream proxy. Unsupported
proxy schemes fail closed, with no direct fallback. HTTP Basic proxy credentials
are supported but are absent from receipts and validation errors.

The existing durable reservation precedes every upstream response read, including
the upstream proxy handshake. Its response headers count conservatively toward
the byte cap. The same one-thread relay, receipt identity, monotonic counters,
failure reservations, allowed destination ports and zero automatic retries remain.
Direct mode remains available when there is no inherited route. TLS certificate
verification belongs to the client and is unchanged.

The proxy now finishes the initial accounting inventory before reporting ready
and launching UV. Exact inventory classification now uses each file's first
relative path component once instead of repeated `Path.relative_to` and
`Path.is_relative_to` calls. Every file is still inventoried, every prior receipt
is still read, inode deduplication is unchanged, and all limits and the existing
one-second interval after a completed scan remain intact. There is no additional
thread, extended timeout, reduced accounting scope or delayed accounting check.

## Local verification

An execution of the pre-change source from `git show HEAD:.../transfer_proxy.py`
with inherited HTTPS_PROXY and mocked external DNS failed deterministically:
`Pre-fix failure: external DNS forbidden`; its DNS target was
`unresolved.invalid`, proving that it ignored the inherited route without making
an external connection.

`python3 -m unittest tests.test_vipe_benchmark_transfer_proxy -q` passed the 25
tests. The new chained fixture gives it a reachable localhost proxy and a
deliberately unresolved destination; only localhost is resolved. It verifies
bidirectional payloads, CONNECT authorization, exact response-header-plus-payload
charges, one connection, zero retries and no credential leakage. Other new
fixtures verify route precedence, unsupported-scheme rejection before DNS,
407 rejection without fallback, and handshake reads stopping at the byte cap.
Existing half-close, selector, reservation and shared-cap tests also pass.

An additional deterministic test delays the initial snapshot by 0.2 seconds,
asserts that it finishes before context entry returns, then completes a local
tunnel with a 0.1-second client timeout. It verifies that the warm snapshot is
reused and exact received-byte accounting is retained.

Read-only profiling of the original accounting implementation on the real run
recorded 289,282,111 function calls over 63.916 seconds under cProfile, with
47.792 seconds in 518,297 `Path.is_relative_to` calls. These profiled timings
include instrumentation overhead. An unprofiled before/after comparison using
the original source loaded from Git and the optimized source measured 14.738
seconds versus 2.381 seconds. Their results were exactly identical:

| Counter | Bytes before and after |
| --- | ---: |
| Download | 20,793,307,392 |
| Artifact | 61,806,170,112 |
| Logical artifact | 80,935,253,473 |

The final combined command
`.local/envs/stg-colmap/bin/python -m unittest tests.test_vipe_benchmark_transfer_proxy tests.test_vipe_benchmark_runtime tests.test_vipe_benchmark_budgets -q`
passed all 83 tests. Real scans now fit within the observed client timeout, but
the selector remains synchronous: arbitrary future filesystem stalls or a much
larger run can still delay it. This patch does not claim an unconditional latency
bound, and no installed-package download was used to validate it.

System `python3` cannot import NumPy, so the runtime suite must use the existing
qualified local Python; no package installation was attempted. The coordinating
agent reported 51 combined proxy/runtime tests passing with
`.local/envs/stg-colmap/bin/python -m unittest tests.test_vipe_benchmark_transfer_proxy tests.test_vipe_benchmark_runtime`.
The runtime fixture additionally asserts that each UV proxy receives the inherited
route before environment replacement.

An optional bounded real-route diagnostic is implemented as
`python3 -m scripts.vipe_benchmark.proxy_diagnostic --output /tmp/e4-proxy-diagnostic-UNIQUE`.
By default it requires an inherited route. Explicit `--direct` tests host direct
egress only when no inherited proxy is configured; it never falls back from an
inherited route. It uses a fresh independent meter capped at 1 MiB,
performs one HEAD of the official cu130 Torch index with a 20-second curl limit,
and prints only HTTP status, charged bytes and receipt path. It performs no
installation, model work, setup allocation or historical record mutation.
Real-route results and the blocking command are recorded below.

## Confirmed policy blocker and required configuration

The in-sandbox command was:

```sh
python3 -m scripts.vipe_benchmark.proxy_diagnostic --output .local/vipe-alternatives/plan031-20260913T032700Z/diagnostics/e4-proxy-route-003
```

The exact tool error was:

```text
exec_command failed: ProcessFailed { message: "Network access to \"download.pytorch.org\" was blocked: domain is not on the allowlist for the current sandbox mode." }
```

This is a definite sandbox domain denial, not a suspected host outage or an
automatic approval-review rejection. No additional probe was attempted after
this denial. A shell execution allow rule does not supply missing domain access.
Add these entries to the existing domain table in `/home/auss/.codex/config.toml`
to admit the package indexes and wheel host:

```toml
[permissions.docker-workspace.network.domains]
# Preserve the existing entries and add:
"download.pytorch.org" = "allow"
"pypi.org" = "allow"
"files.pythonhosted.org" = "allow"
```

Only the PyTorch-domain denial was exercised; the other two are the package
index and distribution hosts required for Python package installation, also
missing from the inspected table. This does not qualify every later source or
model host. No global configuration was modified. Domain rules govern the
active network proxy; see the [OpenAI permissions documentation](https://learn.chatgpt.com/docs/permissions).

Local diagnostic receipts (paths relative to the repository):

- Successful host direct route, HTTP 200, 5,054 bytes:
  `.local/vipe-alternatives/plan031-20260913T032700Z/diagnostics/e4-proxy-route-002/uv-transfers/transfer-0d48477cabf94f3b9263b939fe1993af.json`.
- Denied inherited route, 170 bytes, one connection, no automatic retries:
  `.local/vipe-alternatives/plan031-20260913T032700Z/diagnostics/e4-proxy-route-003/uv-transfers/transfer-b299a56410384465a621d65e43f6a939.json`.

These checks establish the routing correction; they do not qualify E4 dependencies,
xFormers native compatibility, D1 inference or a resumed study attempt.
