# Failed initial standing retry integration

Capture012 ran1182 tests in511.359 seconds (outer513.060719511006 seconds), under
600 seconds, exit1 and no timeout. It has two failures,24 errors and five skips.
Six errors are the known unrelated dependency/inherited-deadline errors; the
other18 errors and second failure share the historical worker binding defect.
The first failure is an obsolete test expecting canonical010 to be rejected.

The worker entrypoint changed, while historical lifecycle validation still
compared old reserved worker records to today's worker. Correction3c27848a
preserves historical worker metadata from its immutable qualification and keeps
current dispatch strict. The relevant fixture and clock expectation are fixed.
Focused historical, standing and current reservation checks pass. A fresh full
integration capture014 rechecks the corrected complete source. No GPU attempt
or live ledger write occurred in this failed test capture.
