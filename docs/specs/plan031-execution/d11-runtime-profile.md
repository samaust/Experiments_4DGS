# D11 native inference profile and admission costs

The D11 adapter consumes the released `depth/Log-stage2` prediction, an
affine-invariant **log-depth** field. It never labels these numbers as metres or
passes them to metric-scale or geometry admission. The worker keeps the restored
float32 map, original native values, validity, input RGB hash and package binding.
Each accepted image is an independent inference call with seed 2025.

| Frozen input | Revision / setting |
|---|---|
| [Marigold source](https://github.com/huawei-bayerlab/marigold-v2/tree/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85) | `bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85`; `scripts/infer.py` native-size `ReshapeToMultiple(16, Lanczos)`, original-size linear restoration; `evaluation/config/inference_depth.yaml` one step, guidance 1, bf16 |
| [Log-stage2 checkpoint](https://huggingface.co/huawei-bayerlab/marigold-v2-0/tree/cdf9810fb690886391a63aec012b5f501064fb0d/depth/Log-stage2) | `cdf9810fb690886391a63aec012b5f501064fb0d`; adapter and tuned decoder, not Log-stage1 or disparity |
| [Qwen base](https://huggingface.co/Qwen/Qwen-Image-Edit-2509/tree/d3968ef930e841f4c73640fb8afa3b306a78167e) | `d3968ef930e841f4c73640fb8afa3b306a78167e`; native 4-bit NF4 DiT, bf16 compute and VAE |
| Inference-only assets | Base VAE and transformer, Log-stage2 trainables, `qwen_edit_2509_qwen_depth_realimg512_{prompt_embeds,prompt_mask}.pt`; no training datasets or DINOv3 checkpoint |
| Required Python release profile | Python ≥3.10; pinned `accelerate==1.13.0`, `bitsandbytes==0.49.2`, `diffusers==0.38.0`, `huggingface_hub==1.8.0`, `omegaconf==2.3.0`, `peft==0.18.1`, `safetensors==0.8.0`, `transformers==5.4.0`, `numpy==2.2.5`, `pillow==12.1.1`, `opencv-python-headless==4.13.0.92`; exact full `pyproject.toml` and Torch/CUDA wheels must be captured in qualification. |

The [release README](https://github.com/huawei-bayerlab/marigold-v2/blob/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85/README.md) reports about 17 GB GPU memory at 1024², 29 GB at 2048² and a few minutes for first-load quantization. Its paper reports 1.9 seconds/image at 1024² on one 32 GB GPU; these are **reference observations**, not accepted host estimates. A fresh proposal must budget and measure source/asset transfers, isolated environment setup, one first-load quantization, 960×540 inference for the selected frame/clip inventory, CPU publication, memory peak and retained bytes. It must reserve within the host's 22 GiB GPU ceiling and cumulative CPU limits. A 960×540 float32 prediction alone occupies 2,073,600 bytes before validity, raw copy, package media and codec files; retained predictions therefore need explicit disk accounting. No GPU run or commercial claim follows from the CPU fixture.
