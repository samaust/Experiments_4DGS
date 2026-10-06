# D8 final-render runtime inventories (#34)

`prepare.py` (run with the joint interpreter, CPU only, 10 s) resolved the native
`default_keyframe` configuration with frames 0/50, the D8 similarity normalization
and the historical scene scale (`resolved-config.json`), then published:

- `gs-runtime.json`: `plan069-final-render-native-runtime/v1`, status `prepared`,
  with the eight GS dependencies, both native binaries and the offline AlexNet
  checkpoint in `.local/envs/plan069-joint-native-001`.
- `matcher-runtime.json`: `plan069-final-render-matcher-runtime/v1`, status
  `prepared`, with the RoMa-edgs checkout at `3701174`, both hash-verified weights
  and every installed file of the 15 matcher distributions.

These are inventories, not qualification. Changing any listed source requires a
fresh inventory.
