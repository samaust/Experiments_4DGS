# Fresh runtime controls validation

Integrated source: `6a4cad3c`. Focused E5 setup and S1 fifth/seventh admission tests:54 passed in16.724 seconds. AST parsing passed for53 benchmark modules; this is syntax validation, not typechecking. No configured typechecker is available.

Full suite:1,113 tests in330.103 seconds; six errors, five skips, zero failures. The subprocess receipt reports331.780 seconds, exit1, no timeout under the600-second cap.

The exact command was `.local/envs/stg-colmap/bin/python -B -m unittest discover -s tests`, with the CPU-only environment recorded in receipt.json. These are existing host/test errors, not a sandbox denial: missing matplotlib, pytest (three modules) and plyfile; the inherited Basketball v6 deadline test expects AssertionError but receives TimeoutError. The interpreter approval prefix already exists; another permission rule cannot fix these errors. This full-suite attempt is complete and is not retried.

Recovery admission depends separately on a passing current-source canonical qualification capture. No full-suite passing claim is made.
