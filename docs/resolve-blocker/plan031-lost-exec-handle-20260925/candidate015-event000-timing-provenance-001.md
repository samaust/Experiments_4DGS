# Candidate015 event000 capture timing provenance

The start and return stamps are direct UTC clock readings immediately before the nested `exec_command` and after the exact raw return was retained and durably persisted. They are truthful enclosing bounds, not claims about sub-second internal tool instants. The raw result includes the positive session handle. The capture uses direct JSON serialization and no `crypto` or `btoa`.
