# Plan049 correction004 — exact-root temporary cleanup enumeration

Append-only clarification of Correction003, issued by Main under the user's CPU-only completion authorization. It resolves the exact implementation question raised by the Plan049 implementer.

An opaque constructor may return after C with nested, previously unknown entries beneath its exact owned TemporaryDirectory root. Safe complete cleanup requires enumerating those directory entries. Correction003's ban on path discovery/generic recursive cleanup continues to prohibit discovery outside the bound root and generic path-based `shutil.rmtree` behavior, but does not prohibit the following exact-root operation:

- Retain and verify the generated root's directory descriptor and device/inode identity from acquisition; if identity cannot be established, do not traverse.
- Enumerate directory-entry names relative to the retained directory descriptor only. Use descriptor-relative `openat`/`statat`/`unlinkat`/`rmdirat` equivalents with no-follow semantics; reject mount/device escape and never follow symlinks. Symlink entries may only be unlinked as entries. Descend only into verified directories beneath the retained root, preserving descriptor/identity ownership for every descent.
- Read directory metadata/names only as needed to enumerate; never open/read file contents, hash, parse, serialize, alter progress/ledger/reference state, perform model work, or write new evidence. Remove entries only beneath the exact root. Then remove the exact root only after its contents are retired and identity remains bound.
- Save timestamps, identities, entries/operations and outcome in the in-memory safety-retirement record. Preserve the original primary and ordered cleanup failures. Any uncertainty or failed retirement retains charged ownership and fails B4. No blind retries against reused names/descriptors.

This tightly scoped metadata enumeration is part of the singular post-C safety-retirement exception from Correction003, not general post-C I/O and not production progress. The independent validator must inspect path containment, no-follow and FD identity handling, cleanup failure/primary preservation, and absence of other post-C operations. No additional file/scope or scientific behavior changes are authorized.
