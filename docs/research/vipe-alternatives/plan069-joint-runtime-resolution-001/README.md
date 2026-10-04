# Joint runtime OpenCV ownership correction

Base: `944f7138` on `plan069-joint-runtime`. No model imports, installation,
network, GPU use or production ledger mutation occurred.

The union of the selected installed package METADATA closes over **91**
distributions on Linux/Python 3.14, including CUDA-toolkit requested extras, with
no missing metadata or version constraint conflicts. This is a metadata graph,
not a reproducible wheel/source lock or installed-byte qualification.

The graph includes both OpenCV variants at 5.0.0.93. Their RECORD files declare
conflicting hashes for `cv2.abi3.so`, `cv2/typing/__init__.py` and `cv2/version.py`.
Blindly merging the environments therefore cannot prove a coherent package
closure. Albumentations 2.0.8 requires `opencv-python-headless>=4.9.0.80`.

The prospective custom recipe selects **opencv-python-headless 5.0.0.93 only**;
its metadata graph has 90 distributions. Pinned RoMa is source-loaded; its
upstream `opencv-python` distribution spelling is explicitly substituted by the
headless provider of `cv2`. This is not a claim that pip considers those two
project names interchangeable. The full current source/dependency/notice and
native compatibility review remains required before execution.

The matcher inventory boundary now accepts either exact single provider and
rejects a dual-provider inventory, preserving all other required distributions,
complete installed file records, source/weights and active environment gates.
The unchanged matcher/LK uses `cv2` operations available in both variants. No
existing environment was altered and no provider compatibility was measured.

## Evidence and validation

- [combined-installed-metadata.json](combined-installed-metadata.json) binds the
  91 observed distribution METADATA/RECORD records and the declared ownership
  conflict. It does not rehash installed libraries or inspect weights.
- [headless-candidate-metadata.json](headless-candidate-metadata.json) retains the
  explicit 90-distribution prospective closure and substitution. It is not an
  artifact lock: verified acquisition files, builds/notices, actual new installed
  bytes and setup/time/storage bounds are pending.
- Public `validate_inventory` CPU fixtures cover headless, existing GUI, missing
  provider and conflicting dual provider. The new fixtures first failed on the
  previous behavior; all nine matcher tests pass after the correction. Fake
  metadata/checkpoints test inventory validation only, with the pinned source
  discovery seam isolated; they do not confer native execution permission.
- No configured static type checker was found; changed Python files parse. Final
  combined suite belongs to the integration owner after all lanes are merged.

The earlier preparation packet describes its baseline snapshot. Its source file
records must be regenerated for the corrected helper before future admission.
Keep #3/#34/#35 open. Separate source and whole-stack commercial review, human D*,
exact environment setup, reviewed compatibility protocol/allocations, measured
production storage adequacy and native qualification remain pending.
