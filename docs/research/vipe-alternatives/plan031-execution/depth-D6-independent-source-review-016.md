# D6 source016 independent physical review (qualification004)

Builds on source015 (`afd0c096`) at `65290ded`. An independent read-only reviewer verified:

1. `source_archive` and all 123 native `source_files` are identical to source015 and match current bytes.
2. All 63 helper `local_sources` match current bytes; the 18 `changed_local_sources` (7 new: method-007
   guard/producer/startup, both local-listen files, `depth_map_retry`, setup-recovery core/candidates)
   are exactly the difference from source015 and are committed history (`afd0c096..65290ded`).
3. All 9 `setup_sources` match current bytes (first pass found the stale source015 `depth_environment.py`
   record; refreshed and re-verified).
4. The five qualification004 method bindings (worker, network guard, startup, dispatcher, authority) match
   current bytes and the REVIEW004 `proposal`; the REVIEW004 record matches.
5. Security: guard007 differs from guard006 only by removing `listen` from the deny list; connect,
   socketpair, accept*, send*/recv*, pidfd_getfd and io_uring remain denied; socket creation is limited to
   AF_UNIX SEQPACKET after the zero-inherited-socket, single-thread, pre-numeric-import check. The producer
   performs two strict `weights_only` CPU loads, no forward/benchmark/kernel, no GPU allocation and no
   downloads. Non-D6 changes add no network, subprocess or unsafe deserialization and are not reached.

Verdict: PASS. No execution authority is granted.
