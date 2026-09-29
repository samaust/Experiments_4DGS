# Wrapper correction 001 — direct Main escrow and honest timestamp bounds

## Finding

Independent Plan050 review found that the Python command-line escrow proposal can fail before persistence, introduces extra processes while the driver is live, does not provide exact Main-call-boundary monotonic samples, and omitted several attempt-indexed output families from high-water selection. Diagnostic007 already demonstrates that preserving a handle only in JS memory is insufficient if a later operation throws.

## Proposed correction

Replace shell-argument escrow and per-event Python helper launches with direct exclusive evidence-file creation through the existing `functions.exec` tool bridge: immediately after the nested tool call returns, retain the exact returned handle and pass the raw argument/result JSON text to `tools.apply_patch` to create a uniquely named escrow file. Do no readiness parsing, hashing, poll, or admission work before this persistence call. Treat serialization or tool-write failure as an aborted attempt, reconcile only through the exact in-memory handle returned by that call, and never claim a durable event when escrow is absent or uncertain. Read back the saved file and compare all tool-native fields and exact output to the original return. Use no new OS observer/helper process while the driver is live.

Use an already-available pure-JavaScript SHA-256 implementation only if it is written and independently verified on synthetic UTF-8/CRLF inputs before any launch; otherwise stop rather than spawn an unapproved hash helper. Capture a contemporaneous UTC observation immediately before and immediately after each actual nested tool call, and preserve the tool's native measured `wall_time_seconds`. For monotonic values, use only a method whose actual measurement semantics are verified before launch. If available APIs cannot record exact monotonic boundaries, record the finest valid lower/upper observation bounds and their uncertainty explicitly; do not label estimated values exact. An independent reviewer must decide whether those bounds satisfy Plan049 §1/§7 and Correction008 §3 or whether new explicit user authorization/contract correction is required. No live launch until that interpretation is independently cleared.

Expand attempt-index scanning to every indexed family under the Plan049 run root: identity, admission, launch note, driver start/stdout/stderr, diagnostic/aggregate output directory, Main launch state/start/terminal/cleanup/outcome, all session event/proof/send/poll/terminal records, raw escrow files, partial/failed writer records, and any additional correction-specific outputs. Any occupied candidate path retires that index; choose a strictly higher index. No prior data deletion.

## Acceptance

- C1 remains conditional on exact tool return and handle being exclusively durably written and read back before dependent processing; all failed/uncertain writes retire through the same exact handle and never admit.
- C2 requires byte-exact tool JSON/output preservation, independently verified SHA-256, contemporaneous UTC brackets, and an independently accepted interpretation for monotonic stamps. If monotonic bounds are not authorized by existing Plan049/Correction008, stop pending a reviewed amendment and explicit user authorization.
- C3 requires a distinct reviewer to inspect the concrete no-extra-process wrapper procedure and actual event/proof/admission/terminal evidence, while confirming all existing resource and deadline restrictions.
- C4 requires fresh full source/authority, capacity, ownership, all-family high-water/vacancy, storage-cap, CPU-only and status checks immediately before any prospective index008-or-higher launch.

## Scope and stop conditions

No runner, capture, driver, contract, test, behavioral deadline, fixture, declaration, assertion, admission rule or trust level changes are authorized by this correction. No diagnostic008 launch is authorized by this document. Do not reuse diagnostic007 request, handle or paths. If the tool bridge cannot durably preserve its exact return or a reviewer cannot accept the timestamp meaning within the existing Plan049/Correction008 authority, stop launch work and record the precise missing platform capability or authorization required.
