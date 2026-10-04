# D6 commercial permission preparation

Status: pending. No actual D6 commercial assessment has been issued.

## Comparison with D5

D6 uses the same MoGe source pin `74fbce054ebed49800de42d0ad0e83495065719a`; the retained source LICENSE is MIT. D6 uses a different checkpoint: `Ruicheng/moge-3-vitl` at `184008f877d7ad1ad4c2cd2182a9bd1f63d0e5be`. Its exact checkpoint/model-card license bytes must be retained and reviewed after setup; D5's MoGe-2 weight permission cannot establish D6's weight permission.

The approved D5 and D6 environment recipes differ only in candidate and FlexGEMM cache path. Requirements and four version constraints match. Several dependency versions are unpinned, so matching recipes cannot establish matching installed packages or permission closure. D5's 90-package assessment is useful reference evidence only.

## Exact post-setup checks

1. Bind the successful actual D6 setup receipt, source archive/files, checkpoint, exact pinned README/model card and license evidence to approved D6 configuration.
2. Generate the actual D6 installed-dependencies manifest through reviewed CPU qualification; bind setup and runtime inventory. Run `prepare.py --checkout <canonical-checkout> --manifest <actual-D6-manifest> --output <fresh-output>` to identify package/version/metadata and installed-byte changes against D5. The builder always leaves permissions pending.
3. Review every installed license/NOTICE, including bundled third-party licenses and native library terms. Reuse retained D5 primary evidence only when exact installed terms and versions match; separately verify utils3d_moge, pipeline and derived FlexGEMM archive/revision provenance and local URI bindings. RECORD, direct_url, generated scripts or relocated build bytes can differ legitimately, but require attribution rather than blanket equality claims.
4. Preserve D5's NVIDIA local workstation restrictions, MPL/LGPL/GCC bundled obligations and supplemental Triton/cuSPARSELt/tqdm/Gradio evidence where applicable; assess any changed closure.
5. Issue the actual `plan069-depth-commercial-assessment/v1` for D6 only after exact code, weight, dependency and inference-output findings plus independent review. Bind the actual manifest and retained primary sources. Preparation artifacts are not admission evidence.
6. Recheck the separate exact FFmpeg/ffprobe publication closure before commercial clips. No hosting, environment/model redistribution, input-media permission or output copyrightability conclusion is provided here.

The checkpoint primary source to retain after setup is https://huggingface.co/Ruicheng/moge-3-vitl/raw/184008f877d7ad1ad4c2cd2182a9bd1f63d0e5be/README.md . This CPU-only preparation performed no network requests, environment installs, model imports, GPU work or shared ledger writes.
