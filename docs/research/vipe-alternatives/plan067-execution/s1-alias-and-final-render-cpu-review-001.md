# S1 alias acceptance and final-render CPU review

## S1 acceptance correction

Worktree commits c2599ca3/c219a5cf are integrated as d5545396/6cb9840a.
The strict collector rejected normal admitted Hugging Face snapshot aliases in
recovery009. Only original known request snapshot-file locations now receive the
exception: lexical alias, filesystem identity, raw relative link, sibling regular
blob and exact payload are bound and reverified. Ordinary result references,
including a shared request dictionary object, retain strict reads. Target and
parent symlinks, escape, missing/cyclic targets, changed payloads, alias recreation
and parent replacement are rejected. Original request/result bytes are unchanged.

Independent Spec review found a shared-object traversal gap; both axes audited
the follow-up correction. Final Spec review reports zero remaining blocking
findings. Independent Standards review reports no documented violations; the
optional repeated terminal/finish fixture setup is deferred. Alias filesystem
identity was also added and tested as a required acceptance/resolution guard.

The original public acceptance reproduction failed with ELOOP before the fix.
Fourteen focused tests passed in119.490 seconds; the two additional guard tests
failed before correction, and four targeted checks passed in75.401 seconds after
correction. The new ten-method acceptance suite is required by the qualification
contract, which now collects ten suites. AST and diff checks pass; no configured
static typechecker is claimed. Full integration and current-source qualification
are separate root gates, recorded with their actual outcomes.

Recovery009 remains failed and consumed, including510 individually qualified
rows, stop_required=true, absent terminal receipt and poisoned helper. No raw
result is promoted. This correction allocates no GPU retry.

## Final-render CPU contracts and assembly

The prospective contract and pure initializer are integrated through d2e38dca.
Independent Standards and Spec reviews found no remaining blocking findings.
Corrections pin actual processed-manifest and S2/D4 decision records, preserve
the full4×4 normalization, reuse its similarity validator and verify declared
historical scale/normalization against unchanged source contents before geometry
derivation. Consistent downstream rewrites are rejected at the public seam.

All22 focused CPU tests passed on main in10.506 seconds. Four changed Python
files passed AST parsing. The optional repeated human-decision validation remains
deferred. Fixtures grant neither native qualification nor execution authority.
Native geometry, supervised generation, viability, allocation authority, actual
final media and human review remain unfinished under34/35 and parents23/18.

Neither review ran model jobs, GPU operations or live ledger writes. Historical
scientific evidence and consumed attempt identities remain unchanged.
