# Plan053 correction 001 — close post-edit source review findings

## Scope and authority

This correction responds to [post-edit source review 001](validate-049-plan053-postedit-source-review-001.md), verdict NEEDS_CORRECTION. It stays within Plan053/Addendum021, the nine already authorized source paths, focused CPU-only tests, and the existing 8 MiB ledger/ownership limits. It authorizes no diagnostic or aggregate. Preserve all Plan049 and Correction015 behavior, deadlines, selector and resource constraints.

## Acceptance criteria

- C1: `wait_owned_pid(..., WNOHANG)` durably records each poll, treats `(0, 0)` as a completed nonterminal observation, permits a later uniquely sequenced poll, and binds terminal wait evidence to the terminal poll.
- C2: replay accepts a direct matching-child descendant retirement exactly once when its matching wait is the current claimed operation; other unresolved operations remain blocking.
- C3: cap rejection and verified append rollback set a durable attempt-wide lock marker; a fresh process observes it and refuses subsequent appends without changing the verified ledger prefix.
- C4: signal targets, pidfd targets, signal receipts and successful pidfd-close receipts have exact closed schemas; malformed nested fields fail before append/replay, and uncertain close never emits a success receipt.
- C5: argv, effective environment, stdio descriptors, cwd, executable and mutable option sequences are frozen between candidate validation and OS creation; the frozen candidate re-renders byte-identically after caller mutation.
- C6: rerun the existing focused mutation test and relevant helper/ownership regressions; run syntax/diff checks; regenerate the exact nine-path source hash manifest. Obtain a distinct independent exact-hash source review PASS before any diagnostic.

## Work and evidence

The initial Main patch is in the existing nine source/test paths. Review 001's requested evidence is not yet complete. The system `python3` can compile the changed modules but lacks NumPy, and the existing environment at `/home/auss/git_repos/a-r-r-o-w/env312/bin/python` was denied execution even on the single escalated read-only retry. Do not probe alternate outside-workspace environments. Record tests unavailable unless a repository-authorized interpreter becomes available. No diagnostic/aggregate has launched in this correction.
