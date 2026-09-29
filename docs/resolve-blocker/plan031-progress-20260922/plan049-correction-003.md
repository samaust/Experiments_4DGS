# Plan049 correction003 — narrowly permit late temporary-directory safety retirement

Append-only correction to Plan049 correction002, issued by Main under the user's CPU-only completion authorization. This does not alter Plan049 W/C behavior checks or the no-timeout operational allocation.

## Concrete conflict

An approved synchronous opaque/native constructor may create and return an owned `TemporaryDirectory` only after C. At that point ordinary S1 work and evidence publication are closed. Refusing cleanup would leave actual filesystem state behind; performing cleanup is a filesystem mutation after C. Merely retaining the path/handle in memory records uncertainty but is not final cleanup and cannot count as B4 met.

## Exact exception

Permit one **safety-retirement** path after C only for the exact `TemporaryDirectory` object (or equivalent exact owned temporary root) that was acquired by the S1 backend call and returned after C. The code must already hold its explicit ownership handle before testing the returned deadline. It may perform only the object's bounded ownership cleanup: unlink/rmdir operations strictly contained beneath that exact generated temporary root. No reads, hashes, serialization, progress/ledger/reference updates, model work, unrelated cleanup, path discovery, generic recursive cleanup or new evidence-file writes are allowed after C.

Record the retirement attempt/result, original C, actual start/end, root identity and any cleanup failure in memory as an ordered secondary event; preserve the original primary exception/class/text/kind/phase/first-observation unchanged. Cleanup failure retains the exact unresolved handle/identity as charged ownership and fails final acceptance; do not retry blindly or pretend it was cleaned. The cleanup exception never permits another production operation. Any durable retrospective record is written only after leaving the production clock/tripwire scope through already-authorized enclosing task evidence, and is labeled safety retirement, not pre-C production evidence.

Tests must tripwire all post-C operations and demonstrate the sole allowed exact-root removals, containment, no unrelated path operation, successful retirement or exact unresolved ownership on failure, and primary preservation. Normal in-window cleanup remains W/C-gated as Plan049/Correction002 require. Independent validation must review this exception and count cleanup in resource/ownership evidence.

This exception is not authority for general post-C I/O and does not waive any B1–B4 criterion. B4 requires owned temporary directories to be retired and unresolved cleanup uncertainty to be zero at final acceptance.
