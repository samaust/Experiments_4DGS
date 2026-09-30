# Fresh attempts assessment and proposed corrections

## Actual outcomes

User approval in fresh-runtime-attempts-approval-001 was consumed exactly once per identity, serial E5 then S1 after confirmed cleanup. No reconstruction, D2, extra attempt or GPU overlap occurred.

Qualification009 passed298 tests/1030 subtests in238.060 seconds under the600-second limit. Focused tests passed54; independent Standards/Spec reviews found zero blocking findings. The full suite had six existing errors/five skips and remains non-passing.

E5 recovery003 failed import qualification in75.793 seconds. The blanket model-constructor guard rejected import-time torchvision Normalize preprocessing. S1 recovery007 produced/qualified510 rows and passed first-result provenance, but failed final runtime acceptance in2024.690 seconds when an owned temporary generated Torch module had already been deleted. Secondary terminal publication failed because the retained helper was unavailable. Neither attempt timed out. S1 stop_required remains true; neither historical failure is rewritten or promoted.

Host read-only final check: zero GPU pids and no active reservations; device667942912 bytes, artifact92390653952 allocated bytes, downloads37864845768 bytes. GPU cumulative6660.617138481872 seconds (41 attempts); setup5972.2738981778275 seconds (20 attempts). CPU remains13792.196516173037 seconds (4 attempts). All original cumulative caps remain unchanged.

## Concrete CPU correction proposal — not yet authorized after failed host runs

AGENTS.md requires stopping affected work after outside-sandbox failure and waiting for user resolution. The affected E5/S1 work is stopped; read-only diagnosis and immutable outcome preservation were completed.

1. E5: permit construction only of the exact pinned torchvision.transforms.Normalize class during import qualification. Reject subclasses and every other Module constructor. Keep all forwards, network, subprocess and CUDA-context prohibitions. Record permitted preprocessing construction distinctly; test the precise exception and prohibited cases. No namespace-wide exemption.
2. S1: capture supported generated Torch Python source into immutable job evidence before its owned temporary directory is retired. Bind original path, bytes/hash/module, owner/temporary-root identity and admitted Torch generator/template. Verify both live and retained bytes before cleanup. Define an explicit generated-source provenance contract so final acceptance validates retained evidence after cleanup; ordinary installed/source/native files retain their current strict checks. Test generation/capture/cleanup/acceptance and tampering, unsupported modules, foreign roots and missing generator identities. Do not mutate recovery007's manifest or retroactively accept its result.
3. Independently review both corrections and run fresh current-source CPU qualification. Determine exact handling of the preserved S1 stop requirement before proposing any new admission. No further identity or automatic retry is granted here.

A subsequent E5 or S1 attempt would require another concrete reviewed scope and explicit approval. The current approval has no unused retry.

## Issue disposition

#27 stays open: E5 has no qualified runtime. #28 stays open: D2 fit/check remain original unconsumed slots blocked by E5. Thus #20/#21 and execution parent#18 remain open. #33 awaits actual human qualitative feedback; #34/#35 follow it. No incomplete issue was closed. #3's previously completed preparation and closed children remain historical completion; runtime follow-ups are in#18.

Actual issue comments: #27 https://github.com/samaust/Experiments_4DGS/issues/27#issuecomment-5911341302 and #18 https://github.com/samaust/Experiments_4DGS/issues/18#issuecomment-5911916522.
