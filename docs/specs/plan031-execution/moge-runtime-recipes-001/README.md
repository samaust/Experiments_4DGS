# D5/D6 runtime recipes 001

These two actual-origin recipe documents freeze CPU preparation inputs. They were generated and validated with the held administrative implementation `a6cbeac0`; that implementation must be integrated and the final worker source closure reviewed before dispatch. This documentation commit does not duplicate or integrate that implementation.

## Bound inputs

Both recipes bind the canonical source capture under the existing run's `prepare/plan069-moge-primary-research-001`. Root recorded source preparation accounting in `88be3a9c`. The MoGe source is pinned to `74fbce054ebed49800de42d0ad0e83495065719a`. All four actual `pyproject.toml` records are included; the FlexGEMM review also records the actual pinned `setup.py`.

| Offline source | Exact revision |
| --- | --- |
| utils3d_moge | `62f09d58509485564e24d5d9f6aac9ee9ebc0c37` |
| pipeline | `1c511390d90226c00c101f34b84df26a0f8789b4` |
| flex-gemm | `b2fadb29d41846c7981ade6801ffc689fae119cf` |

Requirements include ordinary MoGe dependencies, all three source dependency/build requirements, and wheel. In particular, utils3d_moge's `moderngl` and FlexGEMM's `filelock` are present. Windows Triton is retained with its upstream marker and excluded by resolution on Linux. MoGe training extras are not requested. Source archives remain exact pinned HTTPS acquisition inputs for the separately admitted setup; their local installation is offline with no dependency resolution.

Exact constraints remain `torch==2.6.0+cu124`, `torchvision==0.21.0+cu124`, `triton==3.2.0`, and `numpy==2.1.3`. The ordinary dependency ranges are source declarations; the actual setup must resolve and record the full hash lock and inventory. These documents are not resolved package locks or proof of installed compatibility.

The interpreter path retains the original E5 Python 3.11 environment identity. Its binary record and the actual uv binary record are bound separately. D5 and D6 differ only in candidate and owned runtime/cache paths. Cache paths are inside `jobs/plan069-C-setup-001/runtime/flex-cache`; host HOME is unchanged. The reviewed source-derived build patch and runtime cache override are still required during actual setup and qualification.

## Validation and remaining gates

CPU validation generated each document with `environment_request`, then passed `validate_environment_request` against the canonical source files. Independent review also checks source hashes against the retained primary capture, derives ordinary/build requirements directly from all four TOML files, checks exact pins and markers, and confirms candidate-specific runtime paths. No dependency download, source build, model import, setup reservation, GPU work, or shared ledger mutation was performed.

Before dispatch, integrate the administrative fix after the active slot finishes, review and freeze the resulting executable source closure, bind the immutable DO002 selection carrying the approved 6 GiB package and 9 GiB artifact allocations, and bind the selected recipe record in the exact setup request. The resolver and source archive acquisitions must remain within the shared candidate limits. Actual setup completion, dependency check, runtime inventory, and native CPU qualification remain pending. No dispatch-ready source qualification is claimed here.
