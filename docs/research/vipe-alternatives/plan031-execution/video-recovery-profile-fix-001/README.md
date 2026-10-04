# D9 recovery runtime-profile contract repair

Approved recovery001 failed before environment commands because the worker compared the real `runtime_profile` dictionary with its ID string. The same string was also emitted into runtime/setup results and required by acceptance. Handwritten fixtures supplied the string and hid the mismatch.

The repair validates the complete immutable recipe-bound profile dictionary, checks its ID separately, propagates the dictionary unchanged and validates it at both result boundaries. Fixtures now use the real `environment_request(FRAME_RECIPE)` and `bind_source_environment` contract, with all 48 pins. They check full dictionary acceptance and reject strings or changed dictionary fields before commands and during result acceptance.

Fourteen focused CPU cases and one-worker mypy passed; both independent reviews found no actionable issues. `validation.json` records unique final outer CPU times. The earlier exploration has only a reported internal unittest time; it must not be presented as an actual outer measurement.

This narrow repair leaves recovery001's job/schema unchanged and grants no retry. Original setup001 and failed recovery001 history, artifacts and consumed approvals remain preserved. A separately reviewed recovery002 proposal/authority and fresh source/CPU qualification are required before another attempt. No installation, model import, GPU, download, production ledger change or DO occurred here.
