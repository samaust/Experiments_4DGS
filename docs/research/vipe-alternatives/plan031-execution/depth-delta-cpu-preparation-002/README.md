# Focused D6 delta CPU capture (preparation 002)

Reuses the reviewed CPU016 delta method for a D6-owned focused capture after full
capture027. `launcher.py` is byte-identical to the reviewed
`full-qualification-prep/.local/delta-cpu-016-preparation/launcher.py` (its fixed
receipt scope text still names capture015). `build_request.py` differs only in:
the D6 accounting owner (admission owner must match), the prior captures (full027
as the changed-source baseline, plus full025/026 and delta016, all passing) and the
request scope text.

The capture binds every tracked source and the reviewed D6 helper closure before and
after, and runs only the public tests changed since full027's head plus explicit
selectors, within 60 seconds. It grants no native, model or GPU authority. It exists
because the D6 CPU allowance cannot fit another ~1,000-second full suite.
