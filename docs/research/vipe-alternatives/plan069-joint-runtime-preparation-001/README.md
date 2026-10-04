# Joint RoMa/FreeTimeGS runtime preparation (#34)

Prepared against integrated `23c468e3`, including native execution through
`b96e664e` and the interpreter correction. This read-only preparation does not
qualify a runtime or authorize an installation/model job. The retained
[proposal](proposal.json) binds the `ca5ccb5e` partial inventories by hash; integrate
that handoff separately. Keep #3, #34 and #35 open.

## Minimal candidate

Use the existing FreeTimeGS environment as the recipe basis for one **new,
isolated** environment at `.local/envs/plan069-joint-native-001`. Its GS native
extensions are already present; starting from RoMa would instead require adding
three GS distributions, including two native extensions. This is a preparation
recommendation, not evidence that copying or rebuilding those extensions works.

Both existing environments have Python 3.14, torch 2.13.0+cu130 and torchvision
0.28.0+cu130. Their selected overlapping distribution versions match. The GS
basis lacks these eight directly required matcher distributions:

| Distribution | Existing RoMa version to evaluate |
| --- | --- |
| einops | 0.8.2 |
| kornia | 0.8.3 |
| albumentations | 2.0.8 |
| loguru | 0.7.3 |
| h5py | 3.16.0 |
| wandb | 0.29.0 |
| timm | 1.0.29 |
| poselib | 2.0.5 |

These are observed metadata pins, **not a complete installation lock**. Their
transitive dependencies, build requirements, wheel availability, licenses and ABI
compatibility still require verification. Equal package versions do not establish
equal installed bytes; even common RECORD hashes differ between the environments.

## Preparation sequence

1. Resolve the union of the eight GS and 15 matcher required distributions,
   including the full transitive/build closure. Freeze exact acquired wheel/source
   hashes and notices. Prefer verified existing local artifacts; retained metadata
   cannot reconstruct a wheel. An unavailable artifact requires a separately
   bounded transfer/build proposal. Never import one existing environment through
   PYTHONPATH/system-site-packages: production inventories require dependency files
   within the one selected environment.
2. Derive installation, transfer, storage and CPU preparation limits from that
   exact recipe and current live accounting before setup admission. This packet
   supplies no numeric setup allocation. It changes neither existing environments
   nor their packages. A fresh environment must launch its own literal `bin/python`
   path; resolving that symlink to host Python loses the environment.
3. Install only after applicable reviewed setup authority is bound. Recreate the
   GS native binaries from verified artifacts, or explicitly review a bounded
   build; do not assume that blindly copying a venv preserves entry-point paths,
   RECORD entries, native ABI or binary loading. Freeze interpreter invocation,
   executable bytes, environment prefix and complete installed file records.
4. After the actual human D* choice, resolve the exact native configuration with
   the existing scene normalization/scale, keyframes and typed frame range 0/50.
   Call `final_render_inventory.prepare_inventory` with exact GS dependency
   METADATA/RECORD pairs, two native binaries, AlexNet checkpoint and current
   sources. Call `final_render_matcher.prepare_inventory` with the same prefix and
   executable, pinned RoMa checkout, two freshly verified weight hashes and every
   required installed distribution file from RECORD (excluding prohibited prompts
   and bytecode). Both inventories are `prepared`, not `qualified`.
5. Audit the complete final-render stack's code, weights, dependencies and output
   permissions against primary sources. Earlier component research preferences or
   a depth-only commercial assessment cannot supply the required whole-stack
   `plan069-final-render-commercial-assessment/v1` with all permissions allowed.
   In particular, S2's research selection does not itself grant commercial rights.
6. Freeze the fresh D* REVIEW request after exact runtime/source preparation and
   before qualification: every qualification receipt must bind that immutable
   request. Obtain `plan069-final-render-source-review/v1`, actual/passed, with a
   named independent reviewer and exact request/current source records. Implement
   and CPU-test the **separately supervised native qualification
   producer/admission** before execution. Existing production workers require a
   passed qualification envelope; invoking them unmodified as a qualification
   bootstrap creates a dependency cycle. Preserve their production guard.
   Qualification jobs need distinct approved identities/allocations and the
   existing worker/result and locked ledger seams, verified sources/runtime,
   bounded cleanup, actual measurements and no fixture promotion.
7. Run only independently authorized qualifications for geometry, initializer,
   train and render, serially on the exclusive GPU where required. Publish exact
   `plan069-final-render-native-phase-qualification/v1` receipts and cleaned
   successful ledger finishes; aggregate them into the native qualification.
   Reconcile measured initializer/checkpoint bytes, checkpoint time and cleanup
   reserves. Then freeze the exact production DO envelope and human approval
   over the already frozen REVIEW request.

## Existing limits and approval boundary

The production contract has five arms and 21 allocations: geometry 5,400 seconds,
initializer 900, train 3,600, render 900 per arm, and CPU publication 900. These are
hard ceilings; they include no setup/build/download or independent pilot jobs.
The native qualification validator separately requires all four phases; each
qualification's elapsed time must fit its corresponding unchanged phase ceiling,
but that validation does not allocate those seconds or reuse production slots.

Current approved global storage amendments are 110 GiB downloads / 210 GiB
artifacts. Existing cumulative time, exclusive one-GPU / 22 GiB device limits and
at most eight CPU workers still apply. Recheck remaining budgets under the shared
ledger lock; depth attempts cannot fund final-render setup or qualification.
Generic implementation/resume approval does not manufacture exact DO authority.
The older D4 REVIEW remains historical; use a fresh request binding human D*.

## What is complete

- The existing inventory and admission seams and integrated interpreter fix were
  inspected without package imports, model execution, downloads or runtime edits.
- The exact missing direct distributions and matching selected versions are bound
  to retained metadata evidence. Full installed bytes/weights were not rehashed.
- A reproducible dependency and authorization handoff is prepared; installation,
  actual D* choice, whole-stack commercial audit, native qualification producer,
  distinct approved qualification jobs, independent source review, DO admission and
  final renders remain open.

No runtime implementation changed, so no additional implementation tests or full
suite are claimed. The integration owner's combined CPU qualification remains the
applicable source check; this document cannot extend it to native execution.
