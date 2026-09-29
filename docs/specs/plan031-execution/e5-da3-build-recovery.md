## Problem Statement

The original E5 setup attempt acquired the pinned DA3 assets and installed the locked dependencies, but its offline editable build failed with ModuleNotFoundError for editables. E5 is unqualified and D2 cannot run. The consumed attempt must be preserved while the missing build requirement receives a bounded correction.

## Solution

Include Hatchling’s editable-build requirement in E5’s locked dependency preparation, verify the repaired setup contract with CPU fixtures, and prepare one explicitly approved fresh E5 recovery. Qualify imports and inventory before allowing D2 to use the recovered environment.

## User Stories

1. As a maintainer, I want the exact offline build failure retained, so that the repair addresses the observed missing dependency.
2. As a maintainer, I want Hatchling’s dynamic editable requirement included, so that the offline build has its required package available.
3. As an operator, I want the requirement resolved and hash-locked, so that the build does not fetch an unrecorded dependency later.
4. As a research reviewer, I want the prescribed E5 runtime unchanged, so that a packaging repair cannot change the comparison.
5. As an operator, I want the pinned DA3 source and checkpoint verified, so that the recovery cannot substitute candidate assets.
6. As an operator, I want a private source build tree, so that generated build files cannot mutate historical sources.
7. As an operator, I want verified reusable weights and archives identified, so that avoidable downloads can be bounded without accepting stale bytes.
8. As a maintainer, I want the original E5 failure preserved, so that successful recovery cannot relabel the failed build.
9. As an operator, I want a fresh numbered setup identity, so that the consumed original setup cannot be reused.
10. As a user, I want a REVIEW proposal that cannot allocate, so that review does not start a second build.
11. As a user, I want one explicit additional setup attempt to approve, so that the recovery has a known allocation and recipe.
12. As an operator, I want the original cumulative setup and storage charges retained, so that unused time does not reset consumption.
13. As an operator, I want serial setup and one GPU owner, so that the recovery obeys the host resource constraints.
14. As a maintainer, I want no automatic fallback or retry, so that an incompatible environment remains an explicit failure.
15. As a maintainer, I want import-only qualification, so that setup cannot spend an unapproved model forward.
16. As a maintainer, I want the runtime inventory and dependency lock frozen, so that D2 can bind a concrete qualified environment.
17. As an operator, I want successful recovery resolved through its validated result, so that downstream work cannot use an orphaned result file.
18. As a research reviewer, I want commercial/license evidence preserved separately, so that runtime qualification cannot imply permission or accuracy.
19. As a maintainer, I want D2 released only after E5 qualification, so that a partial build cannot fund model execution.
20. As a maintainer, I want a reviewed and committed repair milestone, so that the user can approve a concrete implementation.

## Implementation Decisions

- Parent: #18. Related preparation: #3 and #11. This issue supplies E5 qualification; the depth follow-up owns D2 fit/check.
- The observed missing dynamic editable-build dependency is editables~=0.3, returned by the installed Hatchling build hook. Include it in the E5 dependency resolution and hash-locked install before the offline editable DA3 build.
- Retain Python 3.11, torch 2.5.1+cu124, torchvision 0.20.1+cu124, NumPy 1.26.4 and xFormers 0.0.28.post3, with the frozen DA3 source and DA3METRIC-LARGE checkpoint selection.
- Use the existing setup recipe, qualification and checked ledger transition interfaces. Support a narrow E5 recovery authorization if required; preserve the refusal of unregistered or unrelated recovery identities.
- Require a fresh numbered identity, one additional setup attempt, the original cleaned-up E5 failure, passing source-bound repair validation, exact repaired recipe and explicit DO approval. A REVIEW document cannot register or reserve.
- A fresh recovery must use a private build source. Reuse only hash-verified immutable asset bytes or archives with recorded provenance; preserve the failed environment and its source/build receipts.
- Share the original 57,600-second cumulative setup cap and existing download/artifact ceilings. No automatic retries, altered torch pins, build-isolation fallback or model smoke forwards are permitted.
- Qualify native imports without model constructors, forwards, network use or CUDA context initialization, then freeze the inventory, build-input provenance and dependency lock.
- Acceptance requires the validated packaging repair, separately approved recovery allocation, successful E5 import/inventory qualification, preserved original failure and a downstream resolver that recognizes only the ledger-frozen qualified result. Keep unresolved approval or qualification blocks open.

## Testing Decisions

- Prefer the existing setup worker request/result and admission/ledger seams with fake external package commands.
- Reproduce an offline editable build that requires editables, verify that the dependency is included before that command, and retain a negative case for its absence.
- Cover REVIEW refusal, absent/altered approval, altered recipe, wrong environment, consumed identities, unchanged history and cumulative charges.
- Cover private source extraction, changed archive/weight rejection, orphaned result refusal, zero-forward import qualification and immutable lock/inventory binding.
- Run the affected runtime/setup recovery suites, current source qualification and independent review before asking for recovery approval. A real setup result is required before declaring E5 qualified.

## Out of Scope

- Retrying the original E5 identity, mutating its failed environment, or granting another build through publication of this spec.
- Changing the model, checkpoint, E5 core runtime pins, scientific precision/resolution, optional application/training extras or dependency fallback strategy.
- D2 inference, independently measured depth accuracy, E6/E7 rebuilds or unrelated setup recovery pools.

## Further Notes

- The original E5 attempt is consumed after 109.466 recorded seconds. Cleanup is confirmed, the failure is candidate-specific, and stop_required is false.
- Asset acquisition, base install, dependency resolution and locked install completed before the editable build failed. This is an application packaging failure, not evidenced as a sandbox/network denial.
- The latest generic resume authorizes original unstarted slots. It does not by itself grant this additional E5 build.
