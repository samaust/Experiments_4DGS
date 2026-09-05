  # Document local 4DGS creation and rendering

  ## Summary

  Create a README and practical research documentation for experimenting with 3DGS and, primarily, 4DGS on
  Ubuntu 24.04 LTS with an NVIDIA RTX 4090.

  Document the workflow from synchronized multi-view images and camera metadata to trained dynamic Gaussian
  representations, rendered videos, and interactive playback. Generating the animated virtual worlds remains
  outside scope.

  This change delivers documentation, including commands and experiment procedures; it does not install
  research environments, train models, or implement a new pipeline.

  ## Research and recommendations

  Research arXiv, official conference publications, authors’ project pages, GitHub implementations, and
  Hugging Face model cards and files.

  Cover these initial candidates:

   Candidate                      Role in the research
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   HUST 4DGaussians               Foundational deformation-based method; first synthetic-scene training
                                  walkthrough
  ─────────────────────────────  ───────────────────────────────────────────────────────────────────────────
   Fudan 4D Gaussian Splatting    Native 4D primitives and their rendering pipeline
  ─────────────────────────────  ───────────────────────────────────────────────────────────────────────────
   SpacetimeGaussians             Multi-view training walkthrough, scene checkpoints, and viewer options
  ─────────────────────────────  ───────────────────────────────────────────────────────────────────────────
   Swift4D and Mango-GS           More recent approaches to efficient reconstruction and temporal
                                  consistency
  ─────────────────────────────  ───────────────────────────────────────────────────────────────────────────
   NoPo4D                         Pretrained reconstruction from multi-view videos
  ─────────────────────────────  ───────────────────────────────────────────────────────────────────────────
   L4GM and 4DGT                  Additional downloadable models, with their object-centric or monocular
                                  scope explained

  - Perform a bounded search for newer relevant releases through the documentation’s research date. Keep
    unreleased implementations in a watchlist.

  - Compare input requirements, representation, training versus inference, downloadable assets, supported
    rendering, environment requirements, reported memory use, and suitability for this hardware.

  - Distinguish reusable model weights, scene-specific checkpoints, datasets, viewer binaries, and hosted
    demos.

  - Record code, dependency, and weight licenses separately. Include research-only and noncommercial
    implementations with clear labels; flag conflicting or missing terms.

  - Link every recommendation to primary evidence. Record source dates and repository revisions used for
    commands. Separate published results from estimates and locally verified results.

  ## Documentation changes

  Create README.md with the repository’s purpose, current documentation-only status, target hardware,
  workflow overview, recommended starting points, and links to the guides.

  Organize docs into four guides:

  - Research guide: Explain static 3DGS, deformation-based dynamic Gaussians, native space-time Gaussians,
    and per-frame Gaussian sequences. Include the comparison above, paper/code/model links, license notes,
    and recommendations.

  - Input-data guide: Describe synchronized images, timestamps, intrinsics, extrinsics, coordinate
    conventions, frame indexing, and optional depth, masks, and initialization points. Explain how these map
    to the selected implementations’ actual loaders. Preserve known synthetic camera poses where supported.
    Cover held-out views and the need for consistent geometry and motion across cameras.

  - Local creation guide: Provide isolated environment instructions and source-checked walkthroughs for HUST
    4DGaussians on a small D-NeRF example and SpacetimeGaussians on a short Neural 3D sequence. Explain
    configuration, training, checkpoint contents, resuming where supported, and adaptation to custom inputs.
    Include Ubuntu 24.04/CUDA/compiler compatibility notes and memory reduction options supported by the
    code.

  - Rendering guide: Cover loading complete checkpoints, rendering selected timestamps, fixed-camera
    animation, frozen-time camera movement, and animated camera paths. Document native renderer options and
    locally hosted browser playback, starting with splaTV. Map each representation to compatible viewers and
    verified conversion paths; explicitly identify unsupported conversions.

  The guides will distinguish upstream-tested environments from proposed Ubuntu 24.04 adaptations. Browser
  examples will use locally stored assets. No public API or new universal 4DGS file format will be
  introduced.

  ## Validation and acceptance

  - Check Markdown links, navigation, citations, and consistency between the README and guides.
  - Check commands, configuration names, dataset layouts, and checkpoint requirements against the recorded
    upstream revisions.

  - Ensure every recommended workflow identifies prerequisites, input, output artifacts, rendering route,
    and known limitations.

  - Document runtime acceptance procedures: train a small sequence, reload its checkpoint, render multiple
    times and held-out viewpoints, and verify animation and camera controls in a compatible viewer.

  - Include an experiment record template for revision, configuration, resolution, frame/view counts,
    training time, peak VRAM, checkpoint size, rendering speed, and visual artifacts.

  - Label unexecuted procedures accurately. The current environment’s NVIDIA driver query failed, so GPU
    execution is not a completion requirement for this documentation change.

  Preserve existing user files and follow the repository instruction prohibiting reading prompts.
  Proprietary cloud-only services and world-generation tooling remain excluded.
