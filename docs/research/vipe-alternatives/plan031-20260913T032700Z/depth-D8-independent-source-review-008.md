# D8 post-retry source008 independent physical review

Builds on source007 (`886dbdfe`) after the native loader fix (`39428e6c`) and the
operator-approved maps-002 retry path (`c1d8bdf7`). An independent read-only
reviewer verified:

1. `source_archive` (sha256 `431a8a92…`, 33,827,421 bytes) and all 101 native
   `source_files` are identical to source007 and match current bytes.
2. All 48 helper `local_sources` match current bytes; exactly 8 differ from
   source007 (7 modified, `depth_map_retry.py` added), matching
   `git diff 886dbdfe HEAD -- scripts`.
3. `native_cpu` binds native capture 002 (passed, two strict CPU loads of
   326,209,221 parameters, no CUDA, no inference) with the same archive, source
   files and helper closure. `profile_inventory` is unchanged.
4. Security: the D8 loader keeps `weights_only=True`, `strict=True`, the pinned
   weight hash and no Hub fallback. The retry is D8-only, one fixed maps-002 job,
   only after a clean 0-row worker failure, hash-bound to the operator approval,
   capped at the approved GPU seconds minus the first attempt's charge. No
   network, subprocess or unsafe-deserialization additions.

Verdict: PASS. No execution authority is granted.
