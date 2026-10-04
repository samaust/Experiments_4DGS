# Final full CPU qualification preparation

Prepared for #44; no actual qualification has run from this packet.

After all production changes and reviews are committed in
`plan069-depth-extension`, root runs `build_request.py` with the canonical
checkout, existing private CPU overlay, fresh private packet and capture paths,
a candidate CPU allocation and its fresh CPU admission file. The builder binds
that final HEAD, every safe tracked source, the explicit stg-colmap interpreter,
and the unchanged existing CPU environment inventory. Direct and resolved
`prompts` paths are rejected before reading. A changed inventory requires a
reviewed environment update; the builder does not accept replacement packages.

Example (replace the admission and candidate with the approved live allocation):

```sh
python3 -B docs/research/vipe-alternatives/plan031-execution/depth-full-cpu-final-preparation-001/build_request.py \
  --checkout /home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension \
  --overlay /home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/review-downstream/.local/plan069-cpu-validation/site-packages \
  --packet .local/plan069-final-full-cpu-review-008 \
  --output .local/plan069-combined-cpu-qualification-008 \
  --candidate D6 --cpu-admission /absolute/path/to/fresh/admission.json
```

Root reviews the generated request and fresh ledger ownership/budget checks,
then executes its exact command outside the sandbox. No tracked changes or
commits may occur until the source freeze ends. The inherited cap is 1,200
seconds including cleanup, source and environment verification; the previous
full capture took approximately 903 seconds with one numerical CPU thread.
It executes the existing three pytest function-test modules and full unittest
discovery once, with GPU visibility masked, disposable S1 outputs, Agg plotting,
no pytest plugin autoload and no bytecode writes.

The launcher refuses mismatched HEAD, source set, checkout, overlay, interpreter,
launcher, builder or admission bytes. The receipt includes source/HEAD and
bound-environment checks before and after execution, separate test logs,
observed PID/start-ticks ownership and survivor checks. The inherited 100 ms
process census cannot prove absence of unobserved detached descendants.
A passing receipt qualifies CPU tests on that captured HEAD; it does not grant
native model admission, dependency licenses, GPU compatibility or final-render
completion. The metadata plus pycolmap inventory remains the historical CPU
test binding scope, rather than a complete native runtime file closure.

The launcher does not install, download, run models, mutate the shared ledger,
or create GPU authority. Root must preserve the generated packet and logs,
inspect the receipt and cleanup evidence, and charge preparation and capture
elapsed time exactly once to the admitted CPU allocation/global ledger. The
builder retains a separately measured preparation receipt. Candidate selection
is attribution metadata; root admission must independently check its remaining
budget. A failed capture remains immutable; diagnose and fix before a new fresh
capture under standing retry authorization.

Preparation validation: both Python files parse successfully with host python3.
No actual tests, GPU operations, package imports/installation or ledger mutations
were performed while preparing these files.
