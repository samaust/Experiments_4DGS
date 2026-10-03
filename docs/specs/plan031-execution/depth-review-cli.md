# Extended depth review commands

Issue #60's viewer exports `plan069-depth-review/v1` for the extended package.
Record all five observations, named frame/time examples, tradeoffs, reviewer
identity/date and a separately justified metric choice. Visual preference does
not select reconstruction depth automatically.

From the checkout containing this implementation, use the explicit interpreter
of the qualified environment. The following commands publish new files and
refuse to overwrite existing records:

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python scripts/basketball_vipe_depth_review.py blank-review /path/to/package.json /path/to/blank-review.json
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python scripts/basketball_vipe_depth_review.py import-review /path/to/human-review.json /path/to/imported-review.json --package /path/to/package.json
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python scripts/basketball_vipe_depth_review.py decision /path/to/imported-review.json /path/to/depth-decision.json
```

Complete the blank form or use the viewer's export before import. Blank forms
are not feedback. Import and decision commands require actual human evidence;
the CLI has no fixture override. Only D2/D5/D6/D7/D8/D10 may supply metric D*,
after the exact engineering gates pass. Ties and blocked choices remain blocked.
An accepted review or ready decision grants no execution authority.

The historical review CLI and records retain their original format. For the
new five-arm REVIEW contract use
`vipe_benchmark.extended_final_render_contract`, described in
[the admission contract](extended-final-render-contract-001.md).
