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

## 2U_C V3 backport allowlist rule

`STOM_Version_2U_C` may receive selected V3 features only as intentional documented backports. It remains a V2/Kiwoom-maintained custom lane, not a V3 branch.

Backport entries must be recorded in this registry or in the active `docs/update_log/` backport queue/status document before the difference is treated as intentional.

Minimum template:

```text
Backport ID:
Source V3 version:
Source upstream commit:
Source files:
Target branch: STOM_Version_2U_C
Target worktree: C:/System_Trading/STOM/STOM_V.wt-dev
Goal:
Applied scope:
Excluded LS dependency:
Kiwoom 유지 보정:
DB impact:
UI impact:
Verification commands:
Verification result:
Remaining risk:
Rollback plan:
```

Default exclusions until separately designed:

- LS API runtime assumptions
- `trade/restapi_ls.py` / `trade/restapi_lsdata.py` direct runtime adoption
- DB-incompatible schema/key changes without migration spec
- Kiwoom file removal prerequisites
- V3U pyd-free changes unrelated to the selected 2U_C backport


## Active 2U_C V3 backport queue snapshot

The active Phase 11.4 allowlist and verification plan is recorded in:

- `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`

Current allowlist IDs:

- `2UC-V3-BP-001`: backtest engine stability fixes, broker-neutral only
- `2UC-V3-BP-002`: chart / DB chart / crosshair stability fixes, path-mapped manually
- `2UC-V3-BP-003`: Binance / Upbit stability fixes, LS-free only
- `2UC-V3-BP-004`: webcrawling / sound / log small stability fixes
- `2UC-V3-BP-005`: UI bounce / progress no-op or small improvement check

Current hold IDs:

- `HOLD-001`: V3 analysis-system expansion, requires separate design
- `HOLD-002`: V3 DB structure changes, requires migration design

No candidate may be treated as intentional 2U_C drift unless it is tied to one of these IDs or a later registry/update-log entry.

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

## Applied 2U_C V3 backport: `2UC-V3-BP-007A`

```text
total progress       [####################]  98.5%  66 / 67 pages
BP-007A current      [################----]  80.0%   4 /  5 pages
remaining pages      [####----------------]  20.0%   1 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```

Backport ID: `2UC-V3-BP-007A`
Source V3 version: `STOM V3.0`, `STOM V3.11`
Source upstream commit: `06b70418`, `dbab03b3`
Source files: `utility/sub_process_and_thread/timesync.py`
Target branch: `STOM_Version_2U_C`
Target worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
Goal: apply only the broker-neutral existing-file timesync cleanup/log text from V3.
Applied scope: `utility/timesync.py` docstring, local `dateutil.tz` removal, `astimezone()`, Korean queue logs, `except Exception`.
Excluded LS dependency: all LS API/runtime files excluded.
Kiwoom adjustment: kept the existing 2U_C `utility.timesync` path and `utility.static.thread_decorator` import.
DB impact: none.
UI impact: no pyd/UI wrapper impact; only system-log queue text changes.
Verification commands: `python -m py_compile utility/timesync.py`; isolated mock; `git diff --check`; `git diff --cached --check`.
Verification result: passed before Page 4 docs sync.
Remaining risk: live NTP/SystemTime behavior was not executed offline.
Rollback plan: revert 2U_C code commit `61e12951` and the BP-007A docs commits if the timesync runtime path regresses.

### Final guard for `2UC-V3-BP-007A`

```text
total progress       [####################] 100.0%  67 / 67 pages
BP-007A current      [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  0 pages
```

Next OMX command:

```powershell
omx cancel
```

Final guard: passed. Root and 2U_C release sync passed, both worktrees were clean, forbidden runtime artifact guards were empty, and `STOM_Version_3U_C` was absent.


## Applied 2U_C V3 backport: `2UC-V3-BP-008A`

```text
total progress       [####################]  98.6%  71 / 72 pages
BP-008A current      [################----]  80.0%   4 /  5 pages
remaining pages      [####----------------]  20.0%   1 /  5 pages
```

Next OMX command:

```powershell
omx sparkshell powershell -NoProfile -Command "python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py; python C:/System_Trading/STOM/STOM_V/scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev; git -C C:/System_Trading/STOM/STOM_V status --short; git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short"
```

Backport ID: `2UC-V3-BP-008A`
Source V3 version: `STOM V3.11`
Source upstream commit: `dbab03b3`
Source file: `utility/static_method/static_datetime.py`
Target branch: `STOM_Version_2U_C`
Target worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
Goal: apply only the broker-neutral existing-file timezone dependency cleanup from V3.11.
Applied scope: `utility/static.py` UTC/CME DST bootstrap now uses stdlib `datetime.timezone.utc` and `zoneinfo.ZoneInfo`.
Excluded LS dependency: all LS API/runtime files excluded.
Kiwoom adjustment: kept the existing 2U_C `utility.static` path and all existing exported names.
DB impact: none.
UI impact: no pyd/UI wrapper impact.
Verification commands: `python -m py_compile utility/static.py`; DST equivalence mock; `git diff --check`; `git diff --cached --check`.
Verification result: passed before Page 4 docs sync.
Remaining risk: full GUI/runtime launch was not executed offline.
Rollback plan: revert 2U_C code commit `6e4c10a0` and the BP-008A docs commits if the static timezone bootstrap regresses.


### Final guard for `2UC-V3-BP-008A`

```text
total progress       [####################] 100.0%  72 / 72 pages
BP-008A current      [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  0 pages
```

Next OMX command:

```powershell
omx cancel
```

Final guard: passed. Root and 2U_C release sync passed, both worktrees were clean before Page 5 doc append, forbidden runtime artifact guards were empty, and `STOM_Version_3U_C` was absent.
