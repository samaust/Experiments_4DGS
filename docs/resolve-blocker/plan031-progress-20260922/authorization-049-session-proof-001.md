# Authorization 049 — session-bound admission proof

Recorded by Main on 2026-09-23 UTC from the user's explicit reply to the identity-proof question:

> Authorize session-bound proof

The question presented the specific change: bind the live exec session handle to the driver's identity request, use its stable in-process census, and retain the other exact limits. The user authorized this despite changing the independent kernel-identity check.

Under Plan049 correction008, Main may use tool-session routing/transcript correlation plus the driver's reviewed fresh local root/thread/ancestry verification as the external admission proof (`session-bound/v1`). This is not independent cross-session kernel attestation. It does not authorize a weaker local identity census, resource accounting, source/authority/output binding, ownership/retirement proof, test criteria or any other Plan049 constraint. The separate-shell PID/start-tick mismatch remains historical and must not be claimed as a match.

This authorization covers only the Plan049 CPU-only blocker resolution already authorized by the user. No GPU/device/model/production/real-ledger/setup/download/scientific work is authorized. No operational wall/CPU duration, attempt or correction ceiling is imposed under the user's latest direction; record durations and preserve all original internal W/C and scenario timing assertions.

Correction008 is the exact implementation basis. This note records the user's direction and is not itself a platform attestation, implementation validation or runtime admission.
