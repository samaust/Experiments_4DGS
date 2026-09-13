# Exact E1 source review

Read-only review began 2026-09-13 05:41:43 UTC. The reviewed baseline is validation003 / commit 7e80be5 plus S0 result commit 67f2dfe. E1 subsequently failed during its base-package command; its one attempt remains consumed. These findings neither qualify S1 nor authorize another build.

Source roots below are relative to `.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E1-setup/sources/`. SAM-Track is pinned to `99ca4bd5074a6ed62db4664285073ab669503926`; independent AOT to `601c138435a1764eb01404f3495b914e6e2e8eca`. No model/native package was imported or executed, and no downloads, installs, builds, source edits or ledger changes were performed. All `prompts` directories were excluded without reading their contents.

## Confirmed incompatibilities and minimal adaptations

1. **Populated AOT directory prevents setup linking.** `runtime.py:389` calls `rmdir()` on `samtrack_source/aot`, but this exact revision vendors a populated AOT implementation, including `__init__.py`, configs, networks and utilities. The call would fail with ENOTEMPTY. Future setup should rename that entire directory to a new unused sibling, record both original and preserved locations/inventories, and then link `aot` to the separately pinned source. Retain all original bytes; never select the vendored revision implicitly. This recommendation does not mutate the failed E1 tree.

2. **SAM-Track passes an unsupported engine argument.** `samtrack_source/aot_tracker.py:35–41` passes `max_len_long_term`; independent `aot_source/networks/engines/deaot_engine.py:60` accepts only `aot_model`, `gpu_id`, `long_term_mem_gap`, `short_term_mem_skip`, and `max_aot_obj_num`. Native `build_engine` forwards kwargs unchanged. Current `backends.py:953` therefore reaches a TypeError if construction gets this far.

   A strictly scoped adapter can remove **only** `max_len_long_term=9999`, require eval/DeAOT, `long_term_mem_gap=9999` and `short_term_mem_skip=1`, and expose only reset singleton/two-frame operation. Exact engine diff shows that this parameter adds only truncation in `update_long_term_memory`. A fresh engine starts at frame 0 with no long-term memory; its reference initializes one memory without calling the truncation function. One successor advances to frame 1; the update condition `frame_step-last_mem_step >= 9999` is false. The adapter resets before another reference. Thus truncation is unreachable for these frozen inputs. The vendored extra repeated-reference branch is likewise unreachable with one reference per reset. Reject wider contracts and record the bridge in provenance.

3. **Original-grid labels are incompatible with upstream memory updates.** `aot_tracker.py:74–98` decodes original-image-size labels and forwards them unchanged to `engine.update_memory`. Vendored `aot/networks/engines/aot_engine.py:632` first applies `F.interpolate(curr_mask, self.input_size_2d)` (default nearest); independent `aot_source/.../aot_engine.py:625` does not. Native `MultiRestrictSize` can reduce the long edge to 1040 and rounds dimensions to the stride grid, so the original and engine grids need not match. `assign_identity` reshapes identity embeddings using the engine grid, causing a tensor-size mismatch on incompatible grids. `LegacyStandaloneBackend.segment` currently passes the original-grid labels directly.

   Apply the exact native nearest interpolation to `tracker.engine.input_size_2d` immediately before `update_memory`; retain original-grid labels for export. Preserve dtype, device, one memory update and final reset. Record source/destination shapes and interpolation in provenance. A fake tracker with distinct original/engine grids is necessary; the existing fake `update_memory` is a no-op and cannot expose this defect.

## Additional source checks and limits

- Exact common Python-file comparison found additional selected-path differences confined to explicit `meshgrid(indexing='ij')`, CUDA-availability handling, correlation import/fallback plumbing and an unused ResNet pretrain-path field. Under the prescribed CUDA device, disabled ID shuffle, mandatory successful correlation import and explicit checkpoint, these do not introduce another selected inference algorithm. Training/evaluator/demo and unused Swin changes are outside the called path. This is a source argument, not measured output parity.
- Official SAM-B accepts both box shapes used by the adapter and the selected low-resolution mask logits for its second refinement. Highest-score selection, original-grid masks and later-mask overwrite match SAM-Track's called box path. Local BERT directories are explicitly supported by the selected Grounding DINO tokenizer/model loader; the selected ResNet constructor does not load its unused pretrain path.
- Non-deserializing ZIP/pickle-opcode inspection of the three already-recorded historical checkpoint headers found standard tensor/OrderedDict globals for SAM/Grounding; AOT additionally has NumPy scalar metadata and its exact native loader explicitly uses `weights_only=False`. No checkpoint was unpickled or model constructed. The recorded Grounding digest is `3b3ca2563c77c69f651d7bd133e97139c186df06231157a64c507099c52bc799`.
- Remaining qualification limits: native AOT `load_network` merges matching checkpoint keys into initialized weights and discards its removed-key list in `AOTTracker`; source review alone does not establish complete state-dict coverage. The wrapper import also calls `np.random.seed(200)` for palette generation, changing the worker's previously seeded NumPy state. Config construction creates relative `result/`, `results/` and `img_logs/` directories. These are recorded observations, not silently changed in this review.
- No extra model probe is justified. E1's actual package-transfer failure already blocks S1 under the original allocation. Future implementation fixes still require fresh CPU fixtures and source binding; setup/import and first-forward compatibility remain unverified.

## Reviewed file fingerprints

- `samtrack_source/aot_tracker.py`: `49b2f4df0c8dcd2b36271d7263391df7fd3712805b5154f413e08409fa61f66e`
- `samtrack_source/aot/networks/engines/aot_engine.py`: `8a3f6010a7af5b33f8bc2727759ca3bdcfcd0905d9addaf83c36e5849cbee91d`
- `samtrack_source/aot/networks/engines/deaot_engine.py`: `0f65e2d7213936885961f7d9508c2b060308fab7a9b8b97c0fbfcbe3500c2aaf`
- `aot_source/networks/engines/aot_engine.py`: `730b3a9600715f00f3a3986856ac2112e89c298c401f4149d61ea5312463130d`
- `aot_source/networks/engines/deaot_engine.py`: `e4ac7b7370c7ddaa4c57cc6b141209101cd01351ee0426286b7160c1dc84734a`
- `aot_source/networks/layers/attention.py`: `caf7eca7eed16b2597c22ebace6fd10cf721149306ac10eeff57e0527dd89483`
- `aot_source/networks/layers/transformer.py`: `784848286a0afeae26e16b0b414a0657f3a7b8891a8d268d51c7bb99e29e7fab`
- `aot_source/configs/default.py`: `cefc6f2e6cc6250e4b18e22826105885fda4903e05793565fde1d7d60eeb5061`
- `aot_source/utils/checkpoint.py`: `f12283220a128f6c08b52d510fced4a9608772e0eb62fc8cba781301895ebfaf`
- `grounding_source/groundingdino/util/get_tokenlizer.py`: `bedc47db390249eb2230c2031b114d1d5f470ed6dbc1d3905e97e742289cb3b3`
- `sam_source/segment_anything/predictor.py`: `ab66c29ac0b5b204d23997ef49d8a2476f71b596ce97e35efbf116cfc2118fce`

Review ended 2026-09-13 05:48:57 UTC; conservative elapsed preparation charge **434.715 seconds**, below the 600-second review cap. Parent-authorized compatibility implementation begins after this saved review and is separate work.
