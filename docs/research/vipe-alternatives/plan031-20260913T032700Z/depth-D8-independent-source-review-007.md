# D8 post-setup source007 independent physical review

Builds on source006 (pre-recovery, `41ec10d2`) for the recovered setup
`plan069-D8-setup-recovery-001`. An independent read-only reviewer verified:

1. `source_archive` is the retained original `jobs/plan069-D8-setup-001/source.tar.gz`
   (sha256 `431a8a92…105a`, 33,827,421 bytes), with the single top directory
   `metric-anything-616a5e6762f5fc40d1a4ef990fee04c800532f59` (pinned revision).
2. All 101 native `source_files` under the recovery job's `source/` match current
   bytes and are byte-identical to their archive members; the archive and the
   extracted tree each hold exactly those 101 regular files.
3. All 47 helper `local_sources` and the `profile_inventory` match current bytes.

Security notes (informational): upstream `MoGeModel.from_pretrained` and
`infer.py` can download from the Hub and use `strict=False`; the project's
`native_d8` worker instead loads the local checkpoint with `weights_only=True`
and `strict=True` and has no Hub fallback. DINOv2 `init_weights()` (network)
is not on the inference path.

Verdict: PASS. No execution authority is granted.
