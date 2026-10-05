# D6 source023 independent physical review (offline runtime replacement)

Builds on source022 at `c67b4e23`. An independent read-only reviewer verified 218 records against current
bytes (82 helper sources, 9 setup sources, archive, 123 native files, the recovery REVIEW/DO); the 8 changed
helper sources are exactly Plan 071 milestone A (`2b597fa6`). The proposal hash, DO approval, original
setup-001 ancestry (finish 712) and the clean failed maps-001 (finish 976) agree; the recipe changes only
the runtime pins, indexes and owned cache path; downloads are 0; the setup time fits the allocation. The
runner hard-links verified sources and checkpoint, provisions offline for every uv step, and both the
runner and dispatcher sampler reject any downloaded byte. Other candidates and retained D6 budgets are
unaffected.

Verdict: PASS. Authority is limited to the one approved runtime replacement job.
