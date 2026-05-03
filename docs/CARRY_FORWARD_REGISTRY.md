# Carry Forward Registry

## Purpose
Tracks known issues that were intentionally not fixed in the current official update cycle.

## Current V2.79 scope note
The active V2.79 official propagation chain is `V2 -> 2U -> 2U_C`.
Entries below that name `CLI_v267` or `research/init` are historical carry-forward records from the closed V2.74~V2.77 cycle. They are not active V2.79 propagation targets unless a separate migration or corrective-fix cycle explicitly reopens them.

## 2U_C custom allowlist rule
`STOM_Version_2U_C` is the custom update lane derived from `STOM_Version_2U`.
Custom edits are allowed in 2U_C, but any runtime difference from 2U must be recorded as an intentional 2U_C custom item in this registry or the active `docs/update_log/` status document.

This rule does not loosen the 2U rule: `STOM_Version_2U` remains the pyd-to-py inference lane and should differ from `STOM_Version_2` only by pyd-to-py inference outputs and related verification scaffolding.

## Decision schema
- Deferred because: the current wave did not touch the surface directly, or the known issue did not block official intake propagation in this cycle.
- Reclassify when: a future wave changes the surface directly, the failure reproduces during blocker audit, or the affected branch becomes the active corrective-fix target.

## Release-side upstream risks
- V2.74: empty-result MDD bootstrap failure risk
  - Deferred because: the issue was recorded as an upstream risk and was not reopened by the V2.74~V2.77 downstream propagation wave.
  - Reclassify when: a future intake or corrective fix touches MDD bootstrap behavior or reproduces the empty-result path.
- V2.74: plotting-before-persistence robustness risk
  - Deferred because: the wave did not require a plotting pipeline rewrite and the risk remained unchanged from release intake.
  - Reclassify when: plotting order, persistence sequencing, or related guard handling is touched in a future wave.
- V2.75: strategy version parsing with spaces / empty compare selection
  - Deferred because: downstream propagation did not directly modify strategy version parsing or compare-selection logic.
  - Reclassify when: version parsing, compare-selection UX, or input normalization changes in a later cycle.
- V2.75: duplicate scrollbar signal connections
  - Deferred because: the known connection-management risk stayed outside the branches touched for this wave.
  - Reclassify when: scrollbar wiring, signal lifecycle handling, or the affected UI surface is edited again.
- V2.75: lexical version ordering
  - Deferred because: no version-ordering correction was required to complete this intake wave.
  - Reclassify when: version sorting logic, compare lists, or release-selection ordering is changed.
- V2.76: sparse-parameter heatmap crash risk
  - Deferred because: the heatmap path was not the active blocker for the official wave and remained an isolated risk item.
  - Reclassify when: sparse-parameter visualization logic is touched or the crash reproduces during blocker audit.
- V2.76: cubic interpolation crash risk
  - Deferred because: interpolation behavior was not part of the branch-local corrective fixes required for this cycle.
  - Reclassify when: interpolation mode handling, heatmap rendering, or numeric-grid assumptions are changed.
- V2.77: stock strategy example-button wiring issue
  - Deferred because: the example-button path did not block propagation and was left for a dedicated follow-up cycle.
  - Reclassify when: stock strategy UI wiring, example-button handlers, or the surrounding dialog flow is modified.

## Downstream carry-forward tests
- CLI_v267: `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`
  - Deferred because: protected result data existed on the branch and the current wave prioritized keeping the downstream baseline stable.
  - Reclassify when: backtest-result expansion code is touched again or the branch enters a dedicated result-persistence follow-up cycle.
- research/init: `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`
  - Deferred because: the branch remained downstream of the official wave and this failure was not required to close the intake cycle.
  - Reclassify when: research/init changes backtest-result expansion or a later wave selects this test surface for correction.
- research/init: `tests/unit/test_exit_codes.py::TestExitCodes::test_execution_error_returns_two`
  - Deferred because: exit-code alignment was not the active branch-local fix target for the current official cycle.
  - Reclassify when: execution error handling, CLI exit semantics, or test-expectation policy changes on research/init.

## Rule
- If a future wave touches one of these surfaces directly, reclassify it through blocker audit before continuing.
