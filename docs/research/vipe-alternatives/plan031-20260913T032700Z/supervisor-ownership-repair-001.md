# Supervisor ownership race repair

Original S2 reconstruction wrote all 840 outputs and a result manifest, then failed supervision with `exclusive GPU access lost`. Its 328.062 seconds and failed state remain unchanged. Cleanup is confirmed. A subsequent approved host check found no GPU process; historical PID readings were not recorded, so a transient competing process cannot be ruled out.

The old supervisor queried GPU PIDs and then enumerated only live members of the owned process group. Its unreaped worker could exit between those reads: nvidia-smi sampled the worker PID while it still owned GPU state, but the later group scan omitted its zombie entry. The deterministic CPU fixture makes exactly this transition and proves that the zombie retains the real PGID. Zombies cannot execute and their PIDs cannot be reused before reaping.

The fix includes zombies only when checking sampled GPU ownership. Live-child detection, cleanup, foreign-PID rejection, device-memory limits, deadlines, and failed-result handling remain enforced. New ownership failures record sampled, owned and foreign PIDs. A separate CPU fixture verifies a foreign PID still rejects the result and triggers cleanup.

A fresh, explicitly authorized recovery derives its immutable recipe from the original segmentation arm. Registration binds the original cleaned-up failure, current passing source hashes, one fresh attempt identity and the original per-job/cumulative GPU limits. Successful lookup verifies the component, branch and full output count. Original failures are never relabeled. No output from the failed S2 attempt is promoted.

[Validation014](implementation-validation-014.json) records 338 passing CPU tests. [Retry authorization](s2-reconstruction-recovery-authorization-001.json) uses the user's standing Plan031 retry amendment for one 5400-second S2 reconstruction. Network setup remains stopped.
