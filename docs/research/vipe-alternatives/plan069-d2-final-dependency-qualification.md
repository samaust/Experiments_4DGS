# D2 final dependency qualification research

Checked 2026-10-03. Scope: copyright permission for commercial inference on the existing host, using pinned DA3METRIC-LARGE and the retained E5-004 runtime. The selected permission scope is 95 installed packages: the historically loaded native/API set, its active Requires-Dist closure with no extras, and dynamic setuptools, plus separately assessed publication FFmpeg. Reviewed terms support commercial host use of this selected closure subject to retained notices. The final qualification must bind current bytes and native evidence; this report does not authorize execution or assess redistribution, codec patents, or third-party image rights.

## Findings

The pinned [DA3 source license](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/LICENSE) is Apache-2.0. The exact [DA3METRIC-LARGE card](https://huggingface.co/depth-anything/DA3METRIC-LARGE/blob/4010e39f3634a45bc60553321fb49fb760bd594e/README.md) declares Apache-2.0. These findings concern this metric checkpoint; the unresolved LARGE-1.1 card/README disagreement in the survey is a different asset.

The retained D7 `commercial-assessment-003` and `installed-dependencies-003` assess 28 shared packages plus host FFmpeg/ffprobe. They provide reusable terms evidence for the same E5-004 PyTorch/CUDA/xFormers runtime, conditional on current byte/hash verification. Their scope preserves NVIDIA host-use versus redistribution conditions, NCCL notice ambiguity, and host GPL FFmpeg conditions. D7 alone does not establish permission for DA3's additional packages.

Read-only intersection of historical `D2-check/loaded-runtime.json` with E5 `inventory.json` identifies 3,697 recorded loaded paths and 66 installed distributions, including 41 beyond D7's manifest. Metadata Requires-Dist traversal from `depth-anything-3`, with default extras, identifies 146 distributions (118 beyond D7). The final selected set contains 95 packages after extending the 66 loaded distributions through active Requires-Dist edges (no extras) and including dynamic setuptools. It does not assert license clearance for all 146 declared-default packages or all 159 installed distributions. DA3 `api.py` imports `utils.export`, whose initializer eagerly imports geometry/export modules, so choosing NPZ export alone does not exclude their imported dependencies.

## Additional permission evidence

Installed notice files are the primary evidence for the exact wheels; upstream links below corroborate terms but mutable upstream branches are not a replacement for installed-file hashes.

| Component | Installed terms and host-use disposition | Primary evidence |
| --- | --- | --- |
| einops 0.8.2, trimesh 5.1.0 | MIT permits commercial host use, subject to notices | Installed LICENSE / LICENSE.md; [einops](https://github.com/arogozhnikov/einops/blob/main/LICENSE), [trimesh](https://github.com/mikedh/trimesh/blob/main/LICENSE.md) |
| omegaconf 2.3.1 | BSD-3-Clause; blank License metadata does not negate bundled license | Installed licenses/LICENSE; [author license](https://github.com/hydra-ecosystem/omegaconf/blob/main/LICENSE) |
| huggingface-hub 2.0.0, safetensors 0.8.0 | Apache-2.0; safetensors has bundled LICENSE despite blank License metadata | Installed LICENSE; [safetensors](https://github.com/safetensors/safetensors/blob/main/LICENSE) |
| evo 1.37.1, plyfile 1.1.3 | GPLv3 / GPLv3-or-later. Executing private copies is permitted; conveying software has copyleft conditions. GPL is not a noncommercial restriction. | Installed LICENSE / COPYING, particularly GPL §2; [evo](https://github.com/MichaelGrupp/evo/blob/master/LICENSE), [plyfile](https://github.com/dranjan/python-plyfile/blob/master/COPYING) |
| certifi 2026.7.22, tqdm 4.70.1 | MPL-2.0 certificate bundle; tqdm metadata MPL-2.0 AND MIT. Commercial host use is consistent with these terms; retain notices | Installed certifi LICENSE and tqdm metadata; [certifi](https://github.com/certifi/python-certifi/blob/master/LICENSE) |
| moviepy 1.0.3 | MIT; installed wheel has no separate bundled LICENSE in inventory. Exact upstream tag supplies permission evidence | [v1.0.3 author license](https://github.com/Zulko/moviepy/blob/v1.0.3/LICENCE.txt) |
| pycolmap 4.2.1 | Installed COPYING.txt permits BSD host use for COLMAP itself and explicitly separates dependency licenses | Installed licenses/COPYING.txt; [COLMAP license](https://colmap.github.io/license.html) |
| scipy 1.17.1 | BSD source plus bundled OpenBLAS/LAPACK/GCC runtime and libquadmath notices. Native contents require notice/hash binding; source BSD alone is incomplete | Installed wheel METADATA full license text and bundled LICENSE; [SciPy source license](https://github.com/scipy/scipy/blob/main/LICENSE.txt) |
| imageio 2.38.0, imageio-ffmpeg 0.6.0 | BSD Python wrappers. Installed FFmpeg executable has separate native terms and is not the D7-assessed host executable | Installed LICENSE and `imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2`; [wrapper license](https://github.com/imageio/imageio-ffmpeg/blob/main/LICENSE), [subprocess/binary behavior](https://github.com/imageio/imageio-ffmpeg/blob/main/README.md) |
| Remaining historically loaded extras | Installed notices inspected for MIT, BSD, Apache, PSF-style terms. No reviewed notice asserts a noncommercial-only host-use restriction. This is a scoped observation, not an all-native-library redistribution audit | E5 package inventory and installed LICENSE/COPYING files; full package list below |

## pycolmap 4.2.1 native dependency disposition

The COLMAP BSD notice explicitly excludes third-party dependency terms. This assessment therefore inspects the wheel's native dependencies separately. `readelf -d` and `ldd` on installed `_core.cpython-311-x86_64-linux-gnu.so` identify exactly three bundled DSOs in `pycolmap.libs`: `libgfortran-83c28eba.so.5.0.0`, `libgomp-e985bcbb.so.1.0.0`, and `libquadmath-2284e583.so.0.0.0`. Resolved host dependencies are libc/libm/pthread/dl/loader, libstdc++, libgcc_s and zlib. The historical native mapping binds these files; it does not supply copyright permission by itself.

The official [4.2.1 wheel configuration](https://github.com/colmap/colmap/blob/4.2.1/pyproject.toml) selects [the AlmaLinux wheel build recipe](https://github.com/colmap/colmap/blob/4.2.1/python/ci/install-colmap-almalinux.sh), GCC toolset 12 and the [vcpkg registry baseline](https://github.com/colmap/colmap/blob/4.2.1/vcpkg-configuration.json) `127402f1c75bb3d5ff6bce04b285faa4930a5aca`. The [COLMAP dependency manifest](https://github.com/colmap/colmap/blob/4.2.1/vcpkg.json) and registry ports are version constraints for interpreting the wheel; they are not independent attestations of every statically linked library's exact patch revision. Embedded binary source paths confirm Ceres revision suffix `fa3e134b01`, glog 0.7.1, gflags 2.3.0, OpenImageIO 3.1.14.0, LAPACK 3.12.1, SuiteSparse 7.13.0, OpenJPH 0.31.0, libtiff 4.7.2, curl 8.21.0 and METIS revision suffix `ad4f261256`.

| Native component / build constraint | Specific primary terms and host-use disposition |
| --- | --- |
| Bundled libgfortran and libgomp; build selects GCC toolset 12 | GPLv3-or-later with GCC Runtime Library Exception 3.1. Private execution is permitted. SONAMEs do not establish the compiler patch version. [GNU Fortran notice](https://github.com/gcc-mirror/gcc/blob/releases/gcc-12/libgfortran/runtime/main.c), [libgomp notice](https://github.com/gcc-mirror/gcc/blob/releases/gcc-12/libgomp/libgomp.h) |
| Bundled libquadmath | LGPL-2-or-later in [GCC source notice](https://github.com/gcc-mirror/gcc/blob/releases/gcc-12/libquadmath/quadmath.h); host use permitted, redistribution conditions separate |
| Ceres build REF `85331393dc0dff09f6fb9903ab0c4bfa3e134b01` (2.2.0 line) | Exact [owner LICENSE](https://github.com/ceres-solver/ceres-solver/blob/85331393dc0dff09f6fb9903ab0c4bfa3e134b01/LICENSE) is BSD-3-Clause, despite Apache-2.0 registry metadata; owner terms control |
| SuiteSparse 7.13.0; CHOLMOD 5.3.5 and SPQR 4.3.6 port constraints | [CHOLMOD module licenses](https://github.com/DrTimothyAldenDavis/SuiteSparse/blob/v7.13.0/CHOLMOD/Doc/License.txt) include LGPL-2.1-or-later / GPL-2-or-later; [SPQR license](https://github.com/DrTimothyAldenDavis/SuiteSparse/blob/v7.13.0/SPQR/Doc/License.txt) is GPL-2-or-later with stated attribution. These permit host use; an alternate commercial license offer does not invalidate their GPL/LGPL grants. Bundled runtime redistribution is not assessed. |
| Eigen 5.0.1 registry constraint | MPL-2.0 and accompanying permissive source notices: [versioned owner license overview](https://gitlab.com/libeigen/eigen/-/blob/5.0.1/COPYING.README); [registry version constraint](https://github.com/microsoft/vcpkg/blob/127402f1c75bb3d5ff6bce04b285faa4930a5aca/ports/eigen3/vcpkg.json). Commercial host use permitted under MPL. |
| Boost 1.92.0 family | [Boost Software License 1.0](https://github.com/boostorg/boost/blob/boost-1.92.0/LICENSE_1_0.txt) permits use with notices; registry selects seven direct Boost modules with common family version constraints |
| gflags 2.3.0, glog 0.7.1, pybind11 3.0.4 | BSD grants: [gflags](https://github.com/gflags/gflags/blob/v2.3.0/COPYING.txt), [glog](https://github.com/google/glog/blob/v0.7.1/COPYING), [pybind11](https://github.com/pybind/pybind11/blob/v3.0.4/LICENSE) |
| METIS REF `94c03a6e2d1860128c2d0675cbbb86ad4f261256`, GKlib REF `8bd6bad750b2b0d90800c632cf18e8ee93ad72d7` | Apache-2.0 owner grants: [METIS](https://github.com/KarypisLab/METIS/blob/94c03a6e2d1860128c2d0675cbbb86ad4f261256/LICENSE), [GKlib](https://github.com/KarypisLab/GKlib/blob/8bd6bad750b2b0d90800c632cf18e8ee93ad72d7/LICENSE.txt); exact COLMAP overlay ports select these revisions |
| OpenBLAS 0.3.33 / LAPACK 3.12.1 constraints | BSD terms: [OpenBLAS](https://github.com/OpenMathLib/OpenBLAS/blob/v0.3.33/LICENSE), [LAPACK](https://github.com/Reference-LAPACK/lapack/blob/v3.12.1/LICENSE) |
| OpenImageIO 3.1.14.0, JasPer 4.2.9 | [OpenImageIO Apache-2.0](https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/v3.1.14.0/LICENSE.md); [JasPer License 2.0](https://github.com/jasper-software/jasper/blob/version-4.2.9/LICENSE.txt) permits use/sale with notice conditions |
| Image codec dependencies selected by registry | [libjpeg-turbo 3.2.0 BSD/IJG terms](https://github.com/libjpeg-turbo/libjpeg-turbo/blob/3.2.0/LICENSE.md), [libpng 1.6.58 PNG license](https://github.com/pnggroup/libpng/blob/v1.6.58/LICENSE), [libtiff 4.7.2 use/sale grant](https://github.com/libsdl-org/libtiff/blob/v4.7.2/LICENSE.md), [OpenEXR 3.4.14 BSD](https://github.com/AcademySoftwareFoundation/openexr/blob/v3.4.14/LICENSE.md), [Imath 3.2.2 BSD](https://github.com/AcademySoftwareFoundation/Imath/blob/v3.2.2/LICENSE.md), [OpenJPH 0.31.0 BSD-2-Clause](https://github.com/aous72/OpenJPH/blob/0.31.0/LICENSE) |
| Further build-selected support libraries | [fmt 12.2.0 MIT](https://github.com/fmtlib/fmt/blob/12.2.0/LICENSE), [OpenColorIO BSD](https://github.com/AcademySoftwareFoundation/OpenColorIO/blob/main/LICENSE), [robin-map MIT](https://github.com/Tessil/robin-map/blob/master/LICENSE), [zlib 1.3.2](https://github.com/madler/zlib/blob/v1.3.2/LICENSE), [libdeflate 1.25 MIT](https://github.com/ebiggers/libdeflate/blob/v1.25/COPYING), [curl 8.21.0](https://github.com/curl/curl/blob/curl-8_21_0/COPYING), [OpenSSL 3.6.3 Apache-2.0](https://github.com/openssl/openssl/blob/openssl-3.6.3/LICENSE.txt), [SQLite public domain](https://sqlite.org/copyright.html). Owner grants support host use; linked source constraints do not claim a complete redistributed-wheel notice bundle. |
| COLMAP embedded CPU third-party code | [PoissonRecon MIT](https://github.com/colmap/colmap/blob/4.2.1/src/thirdparty/PoissonRecon/LICENSE), [VLFeat BSD](https://github.com/colmap/colmap/blob/4.2.1/src/thirdparty/VLFeat/LICENSE), [PoseLib BSD at selected commit](https://github.com/PoseLib/PoseLib/blob/fa7280fee27f97aff31ae7f98bab7f583fac7d08/LICENSE), [Faiss 1.14.1 MIT](https://github.com/facebookresearch/faiss/blob/v1.14.1/LICENSE) |

**Restricted upstream code is excluded from this wheel disposition.** The [SiftGPU source license](https://github.com/colmap/colmap/blob/4.2.1/src/thirdparty/SiftGPU/LICENSE) grants educational/research/nonprofit use, so it cannot receive a commercial-use disposition merely from COLMAP BSD metadata. The [official dependency conditions](https://github.com/colmap/colmap/blob/4.2.1/cmake/FindDependencies.cmake) disable OpenGL when GUI is disabled and enable GPU only for OpenGL or CUDA; [third-party CMake](https://github.com/colmap/colmap/blob/4.2.1/src/thirdparty/CMakeLists.txt) includes SiftGPU only with GPU enabled. Linux wheel recipe sets GUI off. The parent's explicit CPU-only compile-flag probe of the installed exact 4.2.1 module reports `has_cuda == False`; `ldd` contains no CUDA/OpenGL/GLEW linkage, and binary inspection found no SiftGPU function symbols. A single COLMAP option diagnostic mentions SiftGPU; it is not evidence of including the restricted implementation. These combined observations support excluding SiftGPU. The recipe also disables LSD, CGAL and ONNX; LSD's upstream AGPL is therefore outside this installed wheel's selected scope.

SPQR attribution retained for this documentation: Copyright 2008–2016 Timothy A. Davis; licensed under GNU GPL version 2 or later; original available at [SuiteSparse](https://www.suitesparse.com); Used by permission. The complete [SPQR notice](https://github.com/DrTimothyAldenDavis/SuiteSparse/blob/v7.13.0/SPQR/Doc/License.txt) remains part of the cited dependency evidence.

The pycolmap **host-use disposition is allowed for the observed CPU wheel under the terms above**. It is conditioned on the recorded CPU flag and exact installed binary hashes, excludes SiftGPU operations or substitution with a GPU wheel, and does not grant runtime redistribution. Exact compiler patch and unlabelled static-component patch revisions are not derivable from the wheel's BSD metadata; recipe/baseline constraints and embedded identifiers document that limit explicitly.

## NVIDIA driver host-use terms

The parent linkage inventory identifies 186 mapped native libraries, including 25 host paths outside E5. The installed `libcuda` 595.91.07 belongs to `libnvidia-compute-595:amd64`; its primary installed notice is `/usr/share/doc/libnvidia-compute-595/copyright` (driver agreement dated February 25, 2025). The [official NVIDIA driver agreement](https://www.nvidia.com/en-us/drivers/nvidia-license/) corroborates the relevant clauses.

Sections 1.1(a),(c) permit installing/using the driver and deploying it for one's own use on owned or leased infrastructure. Section 2.1 limits use to NVIDIA platforms. Sections 2.7 and 2.8 exclude commercial hosting outside expressly granted rights and GeForce datacenter deployment, and require owned GeForce hardware. Accordingly, the stated local single RTX 4090 workstation inference scope supports host use, conditioned on owned hardware and absence of datacenter deployment/commercial hosting. Commercial use of locally generated depth outputs is not itself a commercial hosting service. This is an inference about the stated operation, not permission for hosting, binary modification, reverse engineering or redistribution. Section 6 preserves separate component terms and does not supply third-party codec patent rights. The final receipt must bind the installed notice and driver file hashes independently of CUDA wheel notices.

## Additional 29 packages in the selected active closure

The selected set adds 29 packages to the historical loaded set. Installed license files were read for each, including vendored Jedi/parso and pandas notices. MIT, BSD, Apache and ISC terms permit commercial host use with notice retention. APSW's exact installed notice expressly permits commercial applications and explains its `any-OSI` choice ([official terms](https://rogerbinns.github.io/apsw/copyright.html)). The request to sponsor argcomplete in NOTICE is a request; its grant is Apache-2.0.

| Additional packages | Reviewed installed terms |
| --- | --- |
| argcomplete, asttokens, hf-xet, rosbags | Apache-2.0 |
| contourpy, fsspec, ipython-pygments-lexers, jinja2, markupsafe, matplotlib-inline, pandas, prompt-toolkit, psutil, seaborn, click | BSD; pandas bundled license also contains permissive vendor terms |
| executing, natsort, numexpr, pure-eval, ruamel-yaml, stack-data, wcwidth | MIT; numexpr includes BSD cpuinfo notice; wcwidth has permissive auxiliary notices |
| jedi, parso | MIT plus bundled Apache typeshed / PSF-derived Python terms |
| pexpect, ptyprocess | ISC; installed ptyprocess LICENSE resolves `UNKNOWN` metadata |
| lz4, zstandard | BSD wrapper notices; bundled compression code has separate permissive upstream terms |
| APSW | Installed permission explicitly includes commercial applications; `any-OSI` is an alternate license choice |

Addict 2.4.0 is in the historical set: its installed `addict-2.4.0.dist-info/LICENSE` is MIT, resolving `UNKNOWN` metadata; the [author license](https://github.com/mewwts/addict/blob/master/LICENSE) corroborates it. Blank License metadata for ipython-pygments-lexers, jinja2, lz4, prompt-toolkit, seaborn and wcwidth is resolved by the installed BSD/MIT notices. Safetensors and OmegaConf were resolved above; xFormers/Triton retain D7's prior terms evidence. Metadata absence is not a denial.

## Packages outside the selected permission scope

The larger default-declared installation contains Open3D, pillow-heif, e3nn and development/web packages. This report does not label that entire set commercially qualified. Open3D's installed notice is MIT ([official license](https://github.com/isl-org/Open3D/blob/main/LICENSE)).

Pillow-heif 1.8.0's installed `LICENSES_bundled.txt` labels binary wheels GPLv2 and lists libheif LGPLv3 v1.23.4, libde265 LGPLv3 v1.1.3 and x265 GPLv2 v4.2. Its BSD-3-Clause source license does not describe the complete binary wheel. The installed notice itself is the version-specific evidence; [author bundle notice](https://github.com/bigcat88/pillow_heif/blob/master/LICENSES_bundled.txt), [libheif COPYING](https://github.com/strukturag/libheif/blob/master/COPYING), and [libde265 v1.1.3 COPYING](https://github.com/strukturag/libde265/blob/v1.1.3/COPYING) corroborate the license families. Host-use permission can be assessed under these terms; binary redistribution needs separate analysis.

## Exact remaining evidence work

1. Bind the selected D2 dependency set, active requirement edges, installed notices, native binaries and resolved shared libraries in the final D2 manifest. Reuse D7 terms only for files/versions verified unchanged.
2. Include dynamic dependencies such as setuptools already captured by D7 and addict observed in historical D2 even though absent from DA3's declared dependencies.
3. For pycolmap and SciPy, record actual native linkage/bundled notices. For imageio-ffmpeg, distinguish its wheel binary from `/usr/bin/ffmpeg`; bind its license/configuration if the final D2 path invokes it. Historical Python module import alone does not prove that executable ran. The parent qualification agent subsequently inspected the installed wheel executable with `-version` / `-L`: FFmpeg 7.0.2-static enables GPL/version3, libx264 and libx265 and reports GPLv3-or-later. The final manifest must preserve those exact outputs and the executable hash.
4. Where a package omits a bundled notice (ANTLR runtime, moviepy) or has a license file name such as `LICENCE` (tqdm), use exact version author source/license evidence rather than treating missing metadata as denied permission. Exact author tags directly resolve these permission gaps: [ANTLR 4.9.3 BSD-3-Clause](https://github.com/antlr/antlr4/blob/4.9.3/LICENSE.txt), [moviepy v1.0.3 MIT](https://github.com/Zulko/moviepy/blob/v1.0.3/LICENCE.txt), and [tqdm v4.70.1 MPL-2.0/MIT](https://github.com/tqdm/tqdm/blob/v4.70.1/LICENCE). Preserve these source references in the final assessment.
5. Keep generated-output permission as an inference from assessed code/weight/runtime terms. No reviewed term was found assigning ownership of depth predictions to a package author; this does not license the input media.

This research agent performed no new model import, GPU operation, package/model transfer, installation, or ledger write. Official source/license pages were read over the network; the separately reported parent CPU probe imported pycolmap and read its compile-time flag. Metadata inspection used the explicit retained E5 interpreter; installed notice files and historical receipts were read.

## Historical loaded extras

- `addict==2.4.0`
- `antlr4-python3-runtime==4.9.3`
- `anyio==4.15.1`
- `attrs==26.1.0`
- `certifi==2026.7.22`
- `charset-normalizer==3.5.2`
- `colorama==0.4.6`
- `cycler==0.12.1`
- `decorator==4.4.2`
- `einops==0.8.2`
- `evo==1.37.1`
- `fonttools==4.66.1`
- `h11==0.16.0`
- `httpcore2==2.13.1`
- `httpx2==2.13.1`
- `huggingface-hub==2.0.0`
- `idna==3.20`
- `imageio==2.38.0`
- `imageio-ffmpeg==0.6.0`
- `ipython==9.17.1`
- `kiwisolver==1.5.1`
- `matplotlib==3.11.2`
- `moviepy==1.0.3`
- `omegaconf==2.3.1`
- `packaging==26.3`
- `plyfile==1.1.3`
- `proglog==0.1.12`
- `pycolmap==4.2.1`
- `pygments==2.21.0`
- `pyparsing==3.3.3`
- `python-dateutil==2.9.0.post0`
- `pyyaml==6.0.3`
- `requests==2.34.2`
- `safetensors==0.8.0`
- `scipy==1.17.1`
- `six==1.17.0`
- `tqdm==4.70.1`
- `traitlets==5.16.1`
- `trimesh==5.1.0`
- `truststore==0.10.4`
- `urllib3==2.8.0`

## Evidence bindings

- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/d2-depth/.local/d2-cpu-preflight-002/result.json`: 3180 bytes; SHA-256 `acd1964ea76dea2a08f4fe7d96de80159fa4412f43675604a90f9a1238482ba9`.
- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E5-setup-recovery-004/inventory.json`: 12566463 bytes; SHA-256 `9213e11a4529c7dee9a0d6c797616da7ffce666c1bd8d10266bf50457bda6bc5`.
- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/D2-check/loaded-runtime.json`: 1588595 bytes; SHA-256 `6d282819703145835295b0d9e8c2157f70f2720aa77fe5823af5a7197bc7b83c`.
- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension/docs/research/vipe-alternatives/plan031-execution/depth-D7-installed-dependencies-003.json`: 384009 bytes; SHA-256 `76dc3e4f52261433d3ebad99d6eb5075d8b23c56ec00f1aa9c6830d74750d770`.
- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension/docs/research/vipe-alternatives/plan031-execution/depth-D7-commercial-assessment-003.json`: 5149 bytes; SHA-256 `6f747b2e6bdc2c81be20587cb2845d0ec7e535c993198b233ef0445f4881b1b2`.

## Added active dependency notice bindings

- `apsw==3.53.4.0`: `LICENSE` (1166 bytes, SHA-256 `b85a7dc6463f286c14a638070a14f4888564ac7245dc99a17950ec24cf1a7b9d`).
- `argcomplete==3.7.2`: `LICENSE.rst` (10174 bytes, SHA-256 `0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594`); `NOTICE` (387 bytes, SHA-256 `2c889c721ec8ae6d7664680afaefbb4c7620976f434b57a506ecd92f0649b6a0`).
- `asttokens==3.0.2`: `LICENSE` (11359 bytes, SHA-256 `62fb8a3a9621dc2388174caaabe9c2317b694bb9a1d46c98bcf5655b68f51be3`).
- `click==8.5.0`: `LICENSE.txt` (1475 bytes, SHA-256 `9a8ad106a394e853bfe21f42f4e72d592819a22805d991b5f3275029292b658d`).
- `contourpy==1.3.3`: `LICENSE` (1534 bytes, SHA-256 `34170979fc64f4f5e6dfa66ef27dec314ffffc5852000c60f4836ec1dfbf156e`).
- `executing==2.2.1`: `LICENSE.txt` (1066 bytes, SHA-256 `a476a2cb0ef4c41450340a577a28b91ac4c7f669136b2ee148047fabd5fc4181`).
- `fsspec==2026.9.0`: `LICENSE` (1513 bytes, SHA-256 `2dc35496ce53a7307915c008a844aad53e772b49b34cdd00445067691407ec94`).
- `hf-xet==1.6.0`: `LICENSE` (11357 bytes, SHA-256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`).
- `ipython-pygments-lexers==1.1.1`: `LICENSE` (1535 bytes, SHA-256 `b1d0dbc0fa79774d34b8e2d0aec91d50d8caf05f7b40fc22c3010a4bd9ad2bf9`).
- `jedi==0.20.0`: `LICENSE.txt` (1241 bytes, SHA-256 `78e60cd0b8f28694f30195482c33d76908d846b0d15278deb7332aa22ba8e412`); `LICENSE.txt` (1075 bytes, SHA-256 `235e993965d399a25e7d493d25c8622f78718510884b9c051f1f1866b6f34e9d`); `LICENSE` (12657 bytes, SHA-256 `295f8538c94ae5c3043301cf7cff1c852dab6a786a8ddee471e061b40d5ecabe`).
- `jinja2==3.1.6`: `LICENSE.txt` (1475 bytes, SHA-256 `3b49dcee4105eb37bac10faf1be260408fe85d252b8e9df2e0979fc1e094437b`).
- `lz4==4.4.5`: `LICENSE` (1495 bytes, SHA-256 `e2ac43d6eb80eb4e52141817c812437e0b981b1d7b2dc7cc86c7ef5524044c6f`).
- `markupsafe==3.0.3`: `LICENSE.txt` (1475 bytes, SHA-256 `489a8e1108509ed98a37bb983e11e0f7e1d31f0bd8f99a79c8448e7ff37d07ea`).
- `matplotlib-inline==0.2.2`: `LICENSE` (1538 bytes, SHA-256 `8521b036c6448e0e0aa7213d4713b6fdee0f4c64c9f320450f77346bf5c0e8e4`).
- `natsort==8.4.0`: `LICENSE` (1063 bytes, SHA-256 `81d078140eae25b31f257407190f4cdcb80177979749726e2aae4f2cdd90f623`).
- `numexpr==2.14.2`: `LICENSE.txt` (1193 bytes, SHA-256 `03fdd8025a4e6d70caf27720e91a79ad8d9fe422ebe1820f5cec61dceae709ff`); `cpuinfo.txt` (1552 bytes, SHA-256 `4895457f375ba073717a80751d72a4817d2aae539c94890e69917429fd6d9374`).
- `pandas==3.0.6`: `LICENSE` (52127 bytes, SHA-256 `5c1052e921e62d36ccda50a61585e9c0444b80c62f39b57c4f3f0d5fb62f5071`).
- `parso==0.8.7`: `LICENSE.txt` (4176 bytes, SHA-256 `fa67973073753d17624caf8684d5ee816d70c89d912c5bca7ca0f08e7b150edb`).
- `pexpect==4.9.0`: `LICENSE` (987 bytes, SHA-256 `4a483ae1c4dc738a6c8b73feb49074e1835da02ab5aa686f2675029906fa364d`).
- `prompt-toolkit==3.0.53`: `AUTHORS.rst` (148 bytes, SHA-256 `d3dc62c6bc8436658495ab89aea37511e7fa9391d282657239c9cfb80dbd42e5`); `LICENSE` (1493 bytes, SHA-256 `303574d9bdd85c757d6025017942bf17baeedf2778f62bd7f425d07d880f4c4a`).
- `psutil==7.2.2`: `LICENSE` (1548 bytes, SHA-256 `b89c063b3786e28e0c0a38f1931db61fed35e69dd2a2966fbecffee0f46c8d10`).
- `ptyprocess==0.7.0`: `LICENSE` (905 bytes, SHA-256 `c822d385b1a73329846241799becf18690b5d44764c1bed69300b536a405030a`).
- `pure-eval==0.2.4`: `LICENSE.txt` (1066 bytes, SHA-256 `a476a2cb0ef4c41450340a577a28b91ac4c7f669136b2ee148047fabd5fc4181`).
- `rosbags==0.11.5`: `LICENSE.txt` (10280 bytes, SHA-256 `074e6e32c86a4c0ef8b3ed25b721ca23aca83df277cd88106ef7177c354615ff`).
- `ruamel-yaml==0.19.1`: `LICENSE` (1121 bytes, SHA-256 `3e7632bb0dc1150f15f8161f5eec48dec8a99aaa1dfc9e8f63c02931e0fba7f8`).
- `seaborn==0.13.2`: `LICENSE.md` (1491 bytes, SHA-256 `357ad276e086fab501163d4e9a0ae13c2fd0647eb08d2305fbc0ca3813892601`).
- `stack-data==0.6.3`: `LICENSE.txt` (1066 bytes, SHA-256 `a476a2cb0ef4c41450340a577a28b91ac4c7f669136b2ee148047fabd5fc4181`).
- `wcwidth==0.9.1`: `LICENSE` (1322 bytes, SHA-256 `70b98a95a2144eb70af8017fa8c6d95ce247e40867436e8bc649e137fe13d21a`).
- `zstandard==0.25.0`: `LICENSE` (1484 bytes, SHA-256 `788fe85e53724a40b299051c4abc9cf74d42b27e7968325b80891c25f79adb4b`).

- Installed NVIDIA driver notice `/usr/share/doc/libnvidia-compute-595/copyright`: 29736 bytes; SHA-256 `d088d505751b1a2246744d16bdb5846d0df1a804700ab8d09330b6e79165edef`.

## pycolmap native file bindings

- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E5-setup-recovery-004/environment/lib/python3.11/site-packages/pycolmap/_core.cpython-311-x86_64-linux-gnu.so`: 126216769 bytes; SHA-256 `b2932f64203de05c0c4a878bf4be5e1a7ebc1195d5f63020ab1de1b25300431f`.
- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E5-setup-recovery-004/environment/lib/python3.11/site-packages/pycolmap.libs/libgfortran-83c28eba.so.5.0.0`: 8426449 bytes; SHA-256 `d06e88dcb39248adf44b9ab845fe98df055498523801c83254e88ab61f0de46e`.
- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E5-setup-recovery-004/environment/lib/python3.11/site-packages/pycolmap.libs/libgomp-e985bcbb.so.1.0.0`: 2114857 bytes; SHA-256 `25b19bcd491ab3a317c65c9b6a44b3075f8ab25a57b901cfa1ee6c0d6ea206ac`.
- `/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E5-setup-recovery-004/environment/lib/python3.11/site-packages/pycolmap.libs/libquadmath-2284e583.so.0.0.0`: 2100929 bytes; SHA-256 `570b1bc35e2f2e178f5233a8c9dddca076ecb47c5c65fa09f8bd3951989cb481`.
