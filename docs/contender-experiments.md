# Contender experiments — current status, 2026-09-08

Use the [qualified SelfCap workflow](selfcap-workflow.md) for the retained 60-frame dance1 profile: STG Full is the compact completed-schedule default, FreeTimeGS reproduction the measured aggregate-quality option, and Lite the fastest measured renderer. Substantial fast-motion blur remains. The [file audit](experiments/selfcap-evidence-20260908/audit-02.md) and [actual temporal/crop inspection](experiments/selfcap-evidence-20260908/inspection.md) establish the evidence scope; no new training, GPU reload or metric inference ran in this milestone.

Basketball’s latest result is [Plan 016/v10 scientific rejection](experiments/basketball-shared-timing-v10.md), with [accepted timing null](experiments/basketball-shared-timing-v10/package/terminal-decision.json). All 34 static cameras are accepted, estimated scale is 1.31506947 metres per calibration unit, and held-outs are 0/10/20/30 (30 training cameras). Shared final preparation and reconstruction remain gated by timing. Result-or-specific-blocker coverage is complete for twelve pairs; the full reconstruction objective and six-method/two-scene ranking are not.

| Method | SelfCap | Basketball |
| --- | --- | --- |
| STG Lite baseline | Evaluated, native 30,000-step schedule complete; fastest measured FPS | Timing/input gates |
| [006 STG Full](experiments/006-stg-full.md) | Evaluated, native 30,000-step schedule complete; compact default | Timing/input gates |
| [007 FreeTimeGS reproduction](experiments/007-freetimegs.md) | Evaluated, budget stop at 42,061/70,000; dense training-only initialization | Timing/input gates, then training-only dense initialization |
| [008 MoE-GS](experiments/008-moe-gs.md) | Standalone modified-STG expert route/matching-state gate | Same implementation gate plus timing/input gates |
| [009 ATGS](experiments/009-atgs.md) | Evaluated, budget stop at 61,008/100,000 microsteps (20,336 updates) | Timing/input gates |
| [010 FreeTimeGS++](experiments/010-freetimegs-plus-plus.md) | Author fixed-B implementation unavailable in retained audit | Same implementation gate plus timing/input gates |

MoE-GS and FreeTimeGS++ availability findings are dated **2026-09-06**; they were not refreshed online. MoE-GS’s modified SH model and rasterizer source exist, but no validated standalone expert-training route or matching pretrained state was found. Router trainers expect pretrained experts; ordinary STG Full is not a matching substitute. FreeTimeGS++ has no identified author implementation for fixed configuration B; paper-only reimplementation is outside scope. These blockers are not quality failures.

The [comparison summary](experiments/contender-summary.md) contains metrics, motion observations and resource measurements for the four evaluated SelfCap pairs; eight pairs remain blocked. The unchanged training ledger has 22,523.417254 charged seconds out of 24 hours, with individual 7,200-second method/scene allocations, zero overruns and no live reservations. FreeTimeGS/ATGS remaining allowances are below their 185-second restart/reserve threshold. Unused allocations are not redistributed.

## Reproduction and scientific gates

Follow the [workflow guide’s preparation, initialization, complete-state and exact-model reload commands](selfcap-workflow.md), using the existing manifest `.local/data/selfcap/dance1-processed-20260906/manifest.json`. It contains all 24 SelfCap cameras, frames [4120,4180), 60 FPS, held-out camera 0015, camera-specific dimensions and corrected timestamps. Use its camera-offset normalization, not nominal frame-offset/count. Training-only initialization excludes held-out RGB. Preserve complete checkpoint/configuration/provenance and historical evidence.

The [Plan 004 comparison scope](../plans/plan_004.md), [data preparation record](experiments/contender-data-20260906.md) and [creation guide](local-creation.md) remain supporting records. A generic method wrapper records commands/provenance but does not supply loaders, resumability or budget enforcement. The supported native adapters and their saved results are now linked above.

The next necessary Basketball numerical phase needs user-approved concrete scope, elapsed-time cap and attempt caps. Plan 016’s five 81-attempt policies and six preflight allocations are consumed; its 90-minute window cannot restart. Unspent training/calibration budgets do not authorize more timing experiments. Full screens and final validation retain their scientific gates.

## Historical investigations

The [23-camera variant](experiments/basketball-no-camera19.md) and [v4 constrained evaluator](experiments/basketball-shared-timing-v4.md), [v5 bounded-depth pilot](experiments/basketball-shared-timing-v5.md), and [v6 exact-Hessian pilot](experiments/basketball-shared-timing-v6.md) are historical evidence, superseded for current status by v10. The 23-camera split is not the accepted 34-camera profile. Earlier `sear_steak` outputs and experiment reports remain preserved.
