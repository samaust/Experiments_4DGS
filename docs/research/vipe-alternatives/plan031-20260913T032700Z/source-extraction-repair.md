Source extraction repair, 2026-09-13 06:32 UTC

E2 failed during source acquisition because `runtime.extract_source` rejected
every symbolic link. The retained [failure record](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E2-setup/failure.json)
identifies that check as the cause. The separately reported read-only SAM2
archive inspection found four ordinary YAML file aliases, including
`sam2/sam2_hiera_l.yaml -> configs/sam2/sam2_hiera_l.yaml`, whose targets are
regular members within the pinned archive root. This is an extraction-policy
defect; the failure record does not identify a sandbox or network denial.

The repair changes only `extract_source` and `tree_record` in
[runtime.py](../../../../scripts/vipe_benchmark/runtime.py). Extraction first
validates the complete member list under one exact commit root without opening
file payloads. It accepts relative symbolic links only when their normalized
target is a regular member in that same root. Regular files are extracted
before links are created, and original link text is preserved.

Absolute/external targets, root escapes, dangling links, directory targets,
link chains/cycles, hardlinks, duplicate or conflicting paths, special files,
and set-id/sticky modes are rejected. Any alias path or link target containing
the `prompts` component is rejected before payload access; ordinary excluded
`prompts` members remain unread and unextracted. Existing destinations still
fail instead of being overwritten or reused.

Tree inventories now retain `symlink_target` alongside each alias's lexical
path, target-content hash, and mode. Extraction also records `archive_root` and
the original archive member/link/target-member relationships in
`archive_symlinks`. This makes a link retargeting visible even when two target
files contain identical bytes. Original archive files are not modified.

Validation used synthetic archives and disposable CPU fixtures only:

- `.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p test_vipe_benchmark_source_archives.py -v`
  passed all **20 tests** in 0.036 seconds. Fixtures cover the pinned SAM2 alias
  layout, forward targets, safe parent-relative links, deferred link creation,
  link provenance, malicious aliases/collisions, and failure before payload reads.
- `.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p test_vipe_benchmark_runtime.py -v`
  passed all **26 tests** in 0.153 seconds, including lexical Hugging Face snapshot
  paths, executable modes, forbidden-payload exclusion, auth, and metering.
- The scoped `git diff --check` passed.

| Validated file | SHA-256 |
| --- | --- |
| `scripts/vipe_benchmark/runtime.py` | `468c236a703ea4f1021f451f099ea2ea30397196b6329939fdf89a2adfbf95ab` |
| `tests/test_vipe_benchmark_source_archives.py` | `e9c5134aa39ce51240eb5f74131450d41128b4122772dc2cb4119748bdd70cb6` |

No real archive was re-extracted, no build/download/model job ran, and no E2
output or ledger was modified by this repair. E2 remains failed with its one
allocated attempt consumed. These checks support Plan 031's engineering and
integrity requirements; they do not qualify E2 or authorize another attempt.
