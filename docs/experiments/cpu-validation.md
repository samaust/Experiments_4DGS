# CPU test dependencies

The preprocessing environment does not include pytest or matplotlib. Repository
tests need pytest for function tests and matplotlib for CPU report rendering.
`environments/cpu-validation.in` specifies these dependencies;
`environments/locks/cpu-validation-py314-linux.txt` records the validated CPython
3.14 Linux resolution. It retains the validation base's NumPy 2.5.2, Pillow 12.3.0
and packaging 26.3 versions. It does not install or qualify a model runtime.

Install into a private overlay from the checkout being tested. This preserves
the shared experiment environment. Use its explicit interpreter:

```bash
validation_python="$PWD/.local/envs/stg-colmap/bin/python"
validation_site="$PWD/.local/cpu-validation/site-packages"
uv pip install --python "$validation_python" --default-index https://pypi.org/simple \
  --target "$validation_site" --require-hashes \
  -r environments/locks/cpu-validation-py314-linux.txt
export PYTHONPATH="$validation_site:$PWD/scripts:$PWD/tests"
export CUDA_VISIBLE_DEVICES=''
export MPLCONFIGDIR="$PWD/.local/cpu-validation/matplotlib"
export VIPE_CPU_VALIDATION=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
```

Do not install this overlay into shared experiment environments. If the base
versions differ, resolve and validate an appropriate lock before using it.
If uv's cache is sandbox restricted, follow AGENTS.md's outside-sandbox retry rule.

## Run the two test styles

Unittest imports pytest modules but does **not** execute their function tests.
Run the affected pytest modules explicitly:

```bash
"$validation_python" -B -m pytest -q tests/test_basketball_scene.py \
  tests/test_sync_pivot_budget.py tests/test_sync_timing.py
```

The full unittest suite requires a dedicated process session for its process
ownership tests and a fresh `S1_VALIDATION_RUN_DIRECTORY` for disposable outputs:

```bash
export S1_VALIDATION_RUN_DIRECTORY="$(mktemp -d /tmp/4dgs-cpu-tests.XXXXXX)"
setsid --wait "$validation_python" -B -m unittest discover -s tests
```

An isolated worktree also needs the historical calibration, request and ledger
fixtures referenced by existing tests. Copy a locked ledger snapshot; do not
point fixture tests at a writable live ledger. See the Plan069 handoff capture
for the tested worktree setup. These commands do not produce experiment admission
or GPU execution authority.
