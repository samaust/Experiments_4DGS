# D8 next attempt handoff

CPU preparation only. No setup reservation, install, download, checkpoint read,
model execution or GPU operation occurred. The two previous source reviews are
historical: current ledger, package provenance and dispatcher bytes differ.

## Integrate, qualify, refresh

Integrate this change into `plan069-depth-extension`, then qualify the combined
sources. The D8/D11 setup CLI now accepts `--source-review`; the old source001
default remains. It verifies the selected receipt against the current source
closure, pinned revision, profile, passed status and reviewer **before writing a
request**. Ledger authorization repeats those checks and preserves the original
single-attempt limit. No retry number or authority is added.

Run the metadata-only refresh after the source freeze permits:

```bash
<explicit-qualified-CPU-python> -B docs/research/vipe-alternatives/plan031-execution/d8-next-attempt-preparation-001/refresh.py --root <canonical-depth-extension> --run <shared-plan031-run> --output <new-immutable-D8-source-input-directory>
```

It writes the exact production recipe, current 40-file closure and DO002/profile
bindings for independent review. It does not create a passing review. Use the
independently accepted source003 receipt, or the next unused revision, in setup:

```bash
<explicit-qualified-host-python> -B scripts/basketball_vipe_depth_setup_other_dispatch.py --candidate D8 --source-review <accepted-fresh-source-review.json>
```

Setup must remain root-owned after live ledger/resource and single-GPU ownership
checks. Existing output/request paths or consumed authorization prohibit another
setup; preserve successful writes and investigate failures before retrying.

## Approved bounds and outstanding gates

DO002 keeps one setup and one native attempt: setup 1,800 seconds, CPU 1,800
seconds, GPU 3,600 seconds, device 22,548,578,304 bytes, candidate transfer
7,747,448,624 bytes (including the approved 6 GiB dependencies), artifacts
9,663,676,416 bytes. Shared limits remain 110 GiB transfer / 210 GiB artifacts.
Recheck remaining allowances before each phase.

The exact profile remains Torch 2.14.1+cu130 / TorchVision 0.29.1+cu130, Python
3.11 and the recorded exception to unchanged upstream `torch<2.5.0`. The current
recipe has no added `runtime_directory` field. The recipe refresh only hashes
the retained seed interpreter/setup and uv; it does not demonstrate that these
versions resolve, install or run the model.

After accepted setup, use [the retained CPU method](../d8-cpu-method-001/README.md)
through a separately admitted root CPU wrapper. Its `capture` accepts at most
180 seconds; the outer wrapper must additionally cover preflight, full process
cleanup, zero network, allocated artifacts and CPU charging. Finalization needs
its own measured finite bound. The producer's direct-child cleanup flag is not
proof of descendant cleanup. No retained D5 wrapper can be reused with its D5
candidate/result hashes unchanged.

Actual CPU capture constructs the pinned bundled MoGe model twice on CPU. It
does not infer or initialize CUDA. Before finalization, independently assess the
exact installed dependency/license closure and refresh the **postsetup** source
review with verified archive plus nonempty absolute source records. Final
runtime and qualification receipts must repeat those same archive/file records.
Use that full qualification and postsetup review for the already-approved native
dispatch. Actual CUDA compatibility and numerical quality remain unproven until
the native attempt; no extra smoke attempt is proposed.

## Validation

`validation.json` preserves seven passing CPU cases: the request/admission
regression (including seven malformed-source subtests and a missing file), two
setup fixtures and four retained CPU/finalization fixtures. Test subprocesses
took 0.481306359 seconds total. Full combined-suite qualification remains owned
by the integration agent. Mypy was unavailable in the existing host/stg/private
overlays; no dependencies were installed to obtain it.

A metadata-only refresh against this isolated checkout passed in 0.144571408
seconds; its immutable outputs are retained under
`.local/d8-next-preparation-fixture-001`. That draft uses this worktree's paths
and is not a canonical admission receipt. Both timing scopes exclude preliminary
reads and reasoning; no ledger charge has been applied by this agent.
