# Canonical pre-setup D8 refresh003

The selector and handoff commits are integrated into `plan069-depth-extension`.
The refresh builder generated canonical input at
`fb6caac6dcdbde830dfe41d7f5a536511d4387e9`; copies of the input, exact production
environment and measurement are retained beside this report.

Only three of the 40 helper records differ from source-review002:
`ledger.py`, `depth_native_packages.py`, and
`basketball_vipe_depth_setup_other_dispatch.py`. The runtime profile, DO002,
candidate pins, allocation and production environment remain unchanged.

The integration owner separately ran the canonical selector regression:
one passing test and seven malformed-receipt subtests, with 0.021 seconds reported
by unittest and 0.0711397 seconds for the tool. Its retained receipt is
`<canonical-checkout>/.local/D8-selector-validation-001/receipt.json`.
This is focused selector validation. The previous passing combined qualification
007 applies to its recorded source snapshot; neither receipt proves actual D8
setup or CUDA compatibility.

Canonical HEAD subsequently advanced to `7142cc06` through metadata changes.
Source validity is determined by the exact reviewed helper bytes and immutable
approval/profile/recipe records. Review003 is pre-setup only: no acquired archive,
native source manifest, installed dependency closure or checkpoint load can be
claimed. A separate postsetup review and CPU qualification remain mandatory.

Root owns all actual setup and native attempts. This agent generated only
metadata, with 0.120379976 seconds measured by the refresh process; no shared
ledger charge or setup authorization was written.

Independent pre-setup review passed; the source003 receipt retains all 40 ordered
records, profile/DO/recipe, current selector SHA and its focused validation
receipt. Successful verification took 0.074705592 seconds. The reviewer corrected
two private checker errors (requiring identical metadata HEAD, then parsing a
`dict(...)` declaration as a literal) before that successful verification. Those
earlier processes were not accurately timed; no canonical or shared state was
changed. The reported 0.195085568 seconds for refresh plus successful verification
is that measured scope only.
