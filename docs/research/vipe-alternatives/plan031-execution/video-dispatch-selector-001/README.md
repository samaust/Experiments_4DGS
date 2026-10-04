# Immutable post-setup video source selection

Issue #57 follow-up to preparation commit `5a993e7a`. Apply this commit after
that packet, after root's active D5 source freeze finishes, then refresh exact
source reviews and qualify the combined checkout before execution.

`basketball_vipe_video_actual_dispatch.py --source-review PATH` selects a new,
immutable post-setup independent source review. Omission retains historical 001;
older receipts are never rewritten. Before writing a request or authorizing an
attempt, dispatch verifies the approved candidate revisions/profile, current
local hashes, exact setup DO bindings, native archive and current extracted
source files, runtime and the explicitly supplied full qualification bundle.
Both video candidates require that bundle; a runtime receipt is insufficient.
This changes no attempt counts, budgets or GPU authority.

Eight CPU dispatch tests cover existing D9/D10 default binding, explicit fresh
selection, thirteen rejection subcases (missing, mismatched or stale review,
changed native source, missing/runtime-only/wrong-schema full qualification),
worker checks and publication gates. Admission, supervision and resources are
mocked. Fixture documents cannot serve as actual run evidence.

Two independent reviews inspected the changes. Contract review found a missing
bundle schema check; it was added with negative fixtures and independently
rechecked. No actual model, setup, download, GPU or ledger operation occurred.
