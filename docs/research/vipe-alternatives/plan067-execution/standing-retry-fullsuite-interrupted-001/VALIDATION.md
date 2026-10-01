# Interrupted capture; not validation evidence

Capture013 started before the historical worker correction was integrated:
cherry-pick was temporarily blocked by concurrent unrelated staged work. The
command sequence incorrectly proceeded to tests; root interrupted its owned
test process group rather than repeat integration on unchanged failing source.

Outer elapsed61.584535325993784 seconds, returncode-2, no timeout. The exact
partial log and receipt are preserved. The owned parent932621 and test group
932622 were confirmed absent. After the index cleared, correction3c27848a was
integrated successfully; capture014 uses a fresh directory. This capture grants
no qualification, allocation or GPU dispatch authority.
