# Candidate017 preflight publication allowance correction

Candidate017 preflight001 is preserved but does not clear the artifact-capacity gate: it is 74,896 bytes, exceeding its 65,536-byte publication allowance by 9,360 bytes. The measured evidence tree remains far below Plan049's 150 GiB cap; this is a short allowance in the gate record, not a cap exceedance.

Preflight002 rescans the current evidence tree after preflight001 and census artifacts exist. Its 1 MiB publication buffer covers this gate record and nearby small prelaunch evidence; full diagnostic outputs remain subject to the same 150 GiB cap and a fresh post-run scan. No Plan049 cap or workload limit changes.
