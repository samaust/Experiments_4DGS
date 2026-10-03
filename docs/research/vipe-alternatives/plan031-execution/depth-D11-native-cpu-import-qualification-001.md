# D11 genuine CPU import qualification

The exact prepared D11 virtual-environment interpreter successfully imported
Torch, NumPy, torchvision, safetensors, Transformers, Diffusers, bitsandbytes,
OpenCV and the pinned Marigold CLI, component loader, network graph, evaluation
entry and folder-output adapters. Qwen pipeline, VAE and transformer classes
also imported. CPU NumPy/Torch interoperability and OpenCV resize passed.
The process exited zero with empty stderr; its captured stdout and exact
installed inventory/interpreter hashes are bound in the adjacent JSON receipt.
Separate read-only reviewer `runtime_resume/d11_setup_source_review` verified
the capture and inspected the retained launcher; import/ABI and method review
passed.

The interpreter ran with `-I -B` and the verified source directory explicitly
added to its module search path. `CUDA_VISIBLE_DEVICES=-1` and offline flags
were set. Socket connect operations were blocked. HF, Torch, Triton, Matplotlib,
Numba, XDG and temporary paths were scoped to this isolated worktree's `.local`
capture directory. Python bytecode writes were disabled. No global HOME change,
weight load, model construction, download or actual ledger write occurred.
Torch CUDA initialization remained false after imports and CPU checks.
The original launcher was retained after execution from the recorded tool
input; its hash is not a pre-execution binding. Socket connection guards plus
offline flags are not a general network namespace restriction.

Charge the **11.224516887999926 seconds** outer subprocess duration once as
CPU preparation. The inner import/check duration is supporting detail and must
not be charged again. This is actual import/ABI qualification, distinct from
the earlier metadata-only check. It does not establish successful NF4 CUDA
model loading, peak GPU memory, timing or output quality; those remain inside
the root's one approved native GPU attempt.
