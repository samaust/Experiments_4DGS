# Lost exec-handle blocker

Calling task: complete Plan031 under Plan049 and the adopted Plan053/054/055 decisions. Candidate009 had independent prelaunch clearance for a pre-admission proof capture only. Main invoked its driver, but a wrapper error after the nested `exec_command` returned prevented immediate persistence of the returned session handle.

## Scope and criteria

- C1: Establish whether an authorized, trusted tool route can recover the exact Main exec session handle without inferring identity from a process PID.
- C2: Preserve the launch attempt, wrapper error, and read-only host census evidence; send neither a start frame nor `ADMIT` to an unbound session.
- C3: Define a reviewed Main capture sequence that persists the exact returned result and handle before any fallible formatting, hashing, polling, or further launch action.
- C4: Independently validate the route and sequence. Resume runtime work only if exact handle recovery/retirement and fresh launch gates are proven.

Restrictions: never read `prompts`; CPU-only; preserve Plan049 ownership/resource limits, exact same-handle proof, output-path/high-water rules, behavior and deadlines; no PID-based signaling or admission; do not reuse attempt008 or candidate009 identity. No payload or diagnostic is authorized by this blocker run.
