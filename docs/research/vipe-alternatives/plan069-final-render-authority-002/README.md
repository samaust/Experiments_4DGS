# D8 final-render authority at the 70k endpoint (#34)

This folder holds the authority scripts for the 70,000-step retraining of the five
D8 arms. It is a copy of `plan069-final-render-authority-001` with these changes:

- requests come from `plan069-final-render-review-003`;
- the ledger configuration is derived from the requests' v2 cap extension
  (`amended_configuration`);
- the basis records the user's 2026-10-07 choice.

`authority-001` stays as the hash-bound record of the 5k production. The
specification is `docs/specs/plan031-execution/final-render-70k-endpoint.md`.

Run `wrap_qualification.py` from `authority-001`.

## Code review dispositions (2026-10-07, high effort)

| Finding | Disposition |
|---|---|
| The v2 authorization pin was `None`, so no actual 70k request could parse | Fixed: pinned to `final-render-cap-approval-002.json`, with a test that derives the approved caps from the real records |
| The v2 extension was accepted for any endpoint | Fixed: v2 requires `iterations == 70000` (tested) |
| `parse_request` validated the configuration against itself, and the cap logic was duplicated | Fixed: `validate_budget_configuration` returns the amended configuration, and `amended_configuration` calls it |
| `_Budget.check` recomputed the phase deadline on every update | Fixed: computed once in `__init__` |
| `final_render_qualification.py` (compatibility probe) still caps phases at the static `PHASES` | Kept: the probe is not on the QUALIFY or DO path, which use the production workers and `phase_seconds` |
| `review-003/build.py` leaves a partial folder on failure | Accepted: the chain script removes the folder before a rebuild |
| The 70k worker tests run 70,000 fake updates | Accepted: the worker module runs in about 20 s |
| `authority-002` and `review-003` copy the 001/002 scripts | Kept: the earlier scripts are hash-bound evidence of the 5k run, and parameterizing them would change that evidence |
