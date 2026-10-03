# CPU native runtime inventory preparation (#34)

`vipe_benchmark.final_render_inventory.prepare_inventory(...)` publishes an
immutable `plan069-final-render-native-runtime/v1` inventory from explicit files.
It performs no setup, download, native import, GPU operation or ledger mutation.
The inventory describes preparation, not qualification or execution authority.

## Preparation seam

Supply keyword arguments `checkout`, `environment_prefix`, `interpreter`,
`binaries`, `dependencies`, `resolved_config`, `lpips_checkpoint`, `output` and
optional additional `source_files`. File arguments are exact path/hash/byte records;
checkout and environment are explicit directories. No implicit asset discovery is
performed. The output is published exclusively; an existing output is preserved.

The contract retains schema, record_kind=actual, status=prepared,
environment_prefix, interpreter, source_files, binaries, resolved_config and
lpips_checkpoint, and requires `dependencies`. It contains no execution or
qualification receipt. Fake files can exercise this metadata boundary in CPU tests;
those tests do not establish compatibility of the corresponding native packages.

Sources bind the current model/training/checkpoint/sampler/RNG/offline adapters,
resume comparison, native runtime, input adapter, inventory validator, and exact
checkout trainer/utils. Each extra source is also rehashed. Native admission still
requires the audited trainer hash and qualified source identity; source inventory
alone cannot authorize another checkout or recipe.

`binaries` contains exact `gsplat` and `fused_ssim` installed binary file records
within the environment. Native loading independently compares the loaded binary
paths and contents against these records. Venv interpreter symlinks may resolve to
host binaries: interpreter bytes and the separate environment prefix are pinned.

`dependencies` contains exactly torch, numpy, scipy, Pillow, torchvision,
torchmetrics, gsplat and fused-ssim. Each value contains version, metadata and
record; metadata/record bind METADATA and RECORD in the same installed dist-info
directory within the environment. Package names accept standard case and
hyphen/underscore/dot equivalence. Version text must equal the bound METADATA.
The native process additionally checks that active distribution discovery resolves
those same files, preventing an alternate user-site/PYTHONPATH distribution from
substituting its metadata.

These records freeze installed distribution identities and their file manifests.
They do not prove every transitive installed file, ABI, license or asset compatible;
compatibility/license verification and current-source qualification remain gates.
No package import is needed to prepare or validate the inventory.

## Configuration and revalidation

The caller supplies an already resolved configuration JSON with exact fields
native, normalization and scene_scale. Native start/end are typed integers 0/50;
normalization is the existing full positive isotropic similarity transform;
scene_scale is finite and positive. Validation can require the exact request
normalization and frozen historical normalized scene scale. The native runtime
performs this check during CPU construction and again before preparation, along
with exact current environment/interpreter and all source/dependency file records.

The inventory generator does not evaluate the trainer or invent defaults. The
admitted native loader retains its independent complete `asdict(cfg)` comparison
after loading the audited default_keyframe recipe and adjusting its native
schedule. An arbitrary hash-valid configuration cannot pass that comparison.
The 5,000-update endpoint does not shorten the native learning schedule.

After merging source changes, regenerate this inventory against the final source
paths and run combined-source qualification. D* selection, native qualification,
supervised admission, final renders and human feedback remain unfinished. This
module issues no DO command and updates no shared live admission state.
