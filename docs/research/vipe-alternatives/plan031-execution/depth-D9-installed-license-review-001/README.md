# D9 accepted recovery002: independent installed-license inspection

This is a preliminary evidence review, not commercial admission or runtime qualification. It binds the actual accepted recovery002 inventory and verifies all 164 installed LICENSE/LICENCE/COPYING/NOTICE filename records for its 48 packages. `inspection.json` retains each exact installed record. The final commercial assessment must bind the complete dependency manifest from the actual native CPU capture and receive a separate independent review.

Scope: unmodified local inference and generated depth images on the user's NVIDIA workstation. Hosting, redistribution of models/environments/software, training, input media rights and output copyrightability are outside this assessment. Neither package metadata nor a successful setup grants blanket commercial permission.

## Source, weights and outputs

The acquired source LICENSE at revision `4f5ae23172ba60fd7bc11ef671cca678842c7072` is Apache 2.0 (actual setup binds its bytes). The separately retained Small checkpoint model card at revision `256875362cff76724b920335dfb4b29dd611f66e` declares Apache 2.0. A bounded GET returned 200, 1,111 bytes and matching `x-repo-commit`; exact bytes and response headers are retained in `primary/`. The card SHA-256 is `dea5a98977eae58de809fa3ca589090ab56f0ae326069ddb86fdcca1c5f8d8f0`.

Commercial code/weight inference is permitted under those terms. No separate generated-output restriction is stated by the inspected source license or card. Permission to use generated depth images is an inference from their license scope, not an explicit promise of output ownership or clearance of source-media rights. Retain applicable notices. Sources: [pinned source LICENSE](https://github.com/DepthAnything/Video-Depth-Anything/blob/4f5ae23172ba60fd7bc11ef671cca678842c7072/LICENSE), [pinned checkpoint card](https://huggingface.co/depth-anything/Video-Depth-Anything-Small/blob/256875362cff76724b920335dfb4b29dd611f66e/README.md).

## Dependency findings and required scope

| Exact installed component | Evidence-based finding for scoped local use |
|---|---|
| cuda-bindings 13.0.3 | Separate NVIDIA CUDA Python license grants install/use, restricts applications to NVIDIA GPU systems and prohibits specified reverse engineering/notice removal. It is not Apache/MIT. |
| cuda-toolkit 13.0.3.0 | Metadata-only metapackage: exactly INSTALLER, METADATA, RECORD, REQUESTED and WHEEL; no source/executable or LICENSE. Bind primary CUDA Toolkit EULA and the separately assessed actual component notices; missing license metadata alone is not a grant. |
| NVIDIA cublas/cupti/nvrtc/runtime/cufft/cufile/curand/cusolver/cusparse/nvjitlink/nvshmem | Actual installed EULA grants install/use; preserve NVIDIA restrictions and bundled third-party notices. These proprietary SDK terms permit the stated workstation execution, not blanket redistribution or hosting. |
| nvidia-cudnn-cu13 9.24.0.43 and nvidia-cusparselt-cu13 0.8.1 | Their own installed SDK agreements grant install/use with NVIDIA restrictions; retain their separate notices. |
| nvidia-nccl-cu13 2.30.7 | Actual License.txt contains BSD terms and incorporated NVTX terms, despite proprietary metadata. Assess actual notice text, not metadata shorthand. |
| nvidia-nvtx 13.0.85 | Apache 2.0 installed notice; retain notices. |
| easydict 1.13 | LGPL 3.0 permits unmodified local commercial execution. Conveying a library/combined work requires separate compliance; do not mislabel it permissive MIT/Apache. |
| tqdm 4.70.1 | Installed LICENCE includes MPL 2.0 and MIT. Commercial execution is permitted; covered source distribution/change obligations remain. [MPL primary terms](https://www.mozilla.org/en-US/MPL/2.0/). |
| NumPy 1.24.0 | BSD plus bundled-library/toolchain notices, including GPL 3 with GCC Runtime Library Exception. Local execution is permitted; preserve individual notices and do not describe all bundled code as BSD. |
| fonttools, matplotlib, OpenCV, Pillow, setuptools, Torch | Exact embedded notices require explicit coverage in the final findings. Fonts, OpenBLAS/toolchain and codec/library notices cannot be replaced by the top-level package label. Torch alone has 90 LICENSE/NOTICE-family records. |
| einops 0.4.1, Jinja2 3.1.6, OpenEXR 3.3.1 | UNKNOWN/absent metadata does not mean unknown actual terms: installed LICENSE is MIT, BSD and BSD respectively. |
| imageio-ffmpeg 0.4.7 | BSD wrapper license is distinct from shipped `binaries/ffmpeg-linux64-v4.2.2`. Adjacent README has no license terms. This binary must receive its own bound terms before invocation; it is outside frame-array inference and cannot silently inherit wrapper BSD. Host FFmpeg publication remains separately gated. |
| Other installed packages | Inspected MIT/BSD/Apache/PSF and incorporated notices contain no noncommercial or research-only restriction for the scoped execution. Final findings must still enumerate each exact package and all embedded notice bindings. |

[CUDA primary EULA](https://docs.nvidia.com/cuda/eula/index.html) supplements the metadata-only toolkit row. Actual installed terms govern their particular distributions; the live page does not replace pinned installed notices.

## Remaining evidence gates

- Rebind findings to actual CPU003 complete-dependencies.json, verifying all 48 distributions and installed notice bytes are unchanged.
- Enumerate embedded components, including the separately scoped bundled FFmpeg binary and managed CPython terms.
- Independently review the final findings, template, manifest and assembled report together. This preliminary inspection grants no admission.
- Preserve current code/weight/package notices and restrict execution to the stated frame-array/local-workstation scope.

## Unique preparation accounting

The bounded primary-card GET measured 0.2797177649990772 seconds. The immutable notice verification measured 0.08550226100487635 seconds. Earlier metadata inspections lacked a self-timer: charge a single conservative 10-second allowance, not a claim of measured CPU time. Include small metadata copying/checks in that allowance. Total proposed unique preparation debit: 10.365220026003954 seconds. Exclude worktree creation, editing, review wait and previously charged work. No model import, numerical package import, GPU operation or production-ledger mutation occurred.
