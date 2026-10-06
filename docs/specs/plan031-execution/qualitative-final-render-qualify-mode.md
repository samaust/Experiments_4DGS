# Final-render native qualification by a QUALIFY arm (#34)

Production DO admission requires a passed native qualification. The earlier
compatibility-probe design (`final_render_qualification.py`) only ever publishes
`measured` receipts, so nothing could satisfy that requirement. This amendment
closes the gap without weakening production admission.

## QUALIFY mode

- A second REVIEW request, `plan069-final-render-D8-qualification-001`, has the
  same settings as production `plan069-final-render-D8-002`. Only its `id`, its
  allocation identities and its proposal binding differ.
- A `plan069-final-render-do/v1` envelope with `mode: QUALIFY` and
  `qualification: null` authorizes one arm (QF-B) with all four phases. All other
  DO checks apply unchanged: human approval of the exact allocations, inventories,
  interpreter, source closure, source review and licence assessment.
- QUALIFY runs use the unchanged production workers, dispatcher, supervisor and
  acceptance. Reservations carry `role: native-qualification`, plus the runtime
  and source closure. Production reservations carry `role: production`.
- In actual worker records, `native_adapter_qualified` means "ran under a reviewed
  native-adapter envelope (DO or QUALIFY)". The reservation role marks
  qualification runs. Only the aggregate record below states that the stack is
  qualified.

## Aggregate qualification

`final_render_native_qualification.build` derives, from the ledger only:

- one `plan069-final-render-qualify-phase-receipt/v1` per phase, for a cleaned,
  successful, in-deadline finish reserved under that QUALIFY envelope;
- `plan069-final-render-native-qualification/v1`, with measured
  `initializer_bytes`, `checkpoint_bytes`, `checkpoint_seconds` (checkpoint save,
  metadata reload and hashing) and `cleanup_seconds`. The cleanup figure is a
  conservative upper bound: the allocation time outside the worker's own budget.

Production admission calls `verify`, which re-derives the record from the ledger
and requires byte-for-byte agreement. A hand-written or compatibility-only
receipt therefore cannot qualify production. The measured checkpoint and cleanup
time must fit together inside the train worker's 150 s publication reserve.

## Licence gate

`final_render_commercial.validate_commercial` accepts status `allowed` (every
permission allowed) or `research_use`. `research_use` requires all of:

- every permission in {allowed, research_only, unverified};
- `commercial_clearance: false`;
- an approved human `plan069-final-render-research-use-decision/v1` bound to the
  exact runtime inventory.

The user chose research use on 2026-10-05. FreeTimeGsVanilla is AGPL-3.0, and
the RoMa `roma_indoor.pth` weights have no verified licence. EDGS code does not
run in this stack.

## Budgets

Both requests set `artifact_bytes_limit` to 12 GiB. Every reservation needs the
current artifact total plus this limit to fit within the cumulative 260 GiB
artifact cap. A 50 GiB limit would block production after one or two arms.
`device_bytes_limit` is 21 GiB, because idle display memory counts against the
22 GiB device ceiling at admission. Neither change raises any cumulative ceiling.
