# Combined CPU test retry review

Issue #44; base source `66bdde82`. This proposal changes only the CPU test
launcher limit to 1,800 seconds, within the existing D11 CPU allocation of
3,600 seconds and global CPU budget of 57,600 seconds. The earlier 900-second
limit was an agent launcher choice. No external 900-second authority was found
in the depth execution review, approval, Plan069, or depth configurations.
Native GPU (7,200 seconds), setup (3,600 seconds), and attempt bounds are unchanged.

Concrete fixes before retry: use the existing CPython 3.14 stg-colmap interpreter
with pycolmap 4.2.0 and the unchanged private test overlay; use a guarded entry;
precreate a fresh disposable result directory; retain verbose case names and
tracebacks. The four previous missing-pycolmap cases passed with this environment.
The root integrated the D11, anchor-preview, and allocation fixes at the base
source. No environment installation, network transfer, or GPU operation is needed.

`request.json` records the exact command, source/environment file bindings,
launcher, interpreter, fresh output, and bounds. The launcher verifies these
records before tests. Installed distribution metadata inventories plus complete
pycolmap owned-file hashes bind this test environment; this is not a full native
model runtime or commercial qualification. Root must commit and review this
proposal, check remaining CPU/resource budgets, and freeze sources before launch.

The retry runs 22 pytest function cases explicitly, followed by the full verbose
unittest discovery. Root owns actual CPU accounting after the measured capture;
the launcher does not mutate the shared ledger. Logs, command provenance,
source-before/after hashes, timeout outcome, and observed process cleanup are
retained. Cleanup evidence states the polling limitation and does not infer
complete descendant cleanup from killing a parent process group.

Previous full captures took 806.759 and 878.155 seconds. The latest incomplete
capture took 889.025 seconds. Approximate full runtime is 15–20 minutes, uncertain;
1,800 seconds provides headroom within the original allocation. Around 1,045
seconds of previous qualification/diagnostics plus the maximum retry leaves
about 755 seconds for preparation and publication, subject to root's fresh exact
accounting checks. No passing full-suite receipt is claimed by this proposal.
