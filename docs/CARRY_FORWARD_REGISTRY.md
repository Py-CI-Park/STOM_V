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

## Candidate inventory checkpoint: `2UC-V3-CANDIDATE-INVENTORY`

Status: Page 4 official docs sync complete; no runtime code changed.  
Date: 2026-05-07 KST  
Inventory doc: `docs/update_log/2026-05-07_v3_2uc_candidate_inventory.md`

Purpose: before continuing V3 feature backports into `STOM_Version_2U_C`, map the full V3.0~V3.18 feature surface into completed, conditional, hold, and excluded queues.

Current result:

- Immediate safe code candidate: none.
- Completed safe candidates remain: BP-002A, BP-002B, BP-004A, BP-004B, BP-005A, BP-006A, BP-007A, BP-008A.
- Next candidate may only begin as read-only `2UC-V3-BP-009A` chart/UI small display/exception inventory.
- LS API, DB migration, pyd/UI broad merge, V3U-only pyd-free implementation, dashboard full import, broad backtest engine restructure, and analysis runtime wiring remain excluded/hold.

Directive: Do not open a code patch after this checkpoint unless a new BP-ID has completed Page 1 read-only inventory and Page 2 scope decision. The recommended next BP-ID is `2UC-V3-BP-009A`, and it must start with mapping only.
### Final guard for `2UC-V3-CANDIDATE-INVENTORY`

```text
candidate inventory [####################] 100.0% 5 / 5 pages
remaining           [--------------------]   0.0% 0 / 5 pages
```

Final guard: passed. Root and 2U_C release sync passed, both worktrees were clean before Page 5 doc append, forbidden runtime artifact guards were empty, and `STOM_Version_3U_C` was absent.

Next OMX command: start `2UC-V3-BP-009A` as read-only chart/UI inventory only. Do not write code before Page 1 mapping and Page 2 scope decision.
## Applied 2U_C V3 backport: `2UC-V3-BP-009A`

```text
전체 V3->2U_C 진행률 [####################]  98.8%  81 / 82 pages
BP-009A 진행률       [################----]  80.0%   4 /  5 pages
remaining pages      [####----------------]  20.0%   1 /  5 pages
```

Backport ID: `2UC-V3-BP-009A`
Source V3 version: `STOM V3.12`
Source upstream commit: `62e81349 STOM V3.12`
Source file: `ui/draw_chart/draw_crosshair.py`
Target branch: `STOM_Version_2U_C`
Target worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
Target file: `ui/ui_draw_crosshair.py`
Target code commit: `f791c54a BP-009A crosshair 표시 경계를 보정한다`
Goal: apply only the broker-neutral visual crosshair z-order and legend anchor guard from V3.12.
Applied scope: crosshair horizontal/vertical lines now use `setZValue(29)`; non-realtime label/legend anchor movement is guarded with `except Exception: pass`.
Excluded LS dependency: all LS API/runtime files excluded.
Kiwoom adjustment: no broker runtime change; preserved the 2U_C `ui.ui_draw_crosshair` path and pyd wrapper boundary.
DB impact: none.
UI impact: narrow visual-layer helper only; no pyd/UI broad merge.
Verification commands: `python -m py_compile ui/ui_draw_crosshair.py`; `git diff --check`; `git diff --cached --check`; root/2U_C `verify_release_sync.py`.
Verification result: passed before Page 4 docs sync.
Remaining risk: GUI mouse-move runtime was not executed offline.
Rollback plan: revert 2U_C code commit `f791c54a` if crosshair display, mouse move, or legend anchoring regresses.
### Final guard for `2UC-V3-BP-009A`

```text
전체 V3->2U_C 진행률 [####################] 100.0%  82 / 82 pages
BP-009A 진행률       [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  5 pages
```

Final guard: passed. `ui/ui_draw_crosshair.py` py_compile passed, root and 2U_C release sync passed, both worktrees were clean before Page 5 doc append, forbidden runtime artifact guards were empty, and `STOM_Version_3U_C` was absent.

Next candidate: `2UC-V3-BP-009B` read-only inventory for chart moneytop query/time/table clear. It must not start with a code patch.
## Applied 2U_C V3 backport: `2UC-V3-BP-009B`

```text
전체 V3->2U_C 진행률 [####################] 100.0%  87 / 87 pages
BP-009B 진행률       [####################] 100.0%   5 /  5 pages
remaining pages      [--------------------]   0.0%   0 /  5 pages
```

Backport ID: `2UC-V3-BP-009B`
Source V3 version: `STOM V3.07`
Source upstream commit: `6ab5d036 STOM V3.07`
Source file: `ui/event_click/button_clicked_chart.py`
Target branch: `STOM_Version_2U_C`
Target worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
Target file: `ui/ui_show_dialog.py`
Target code commit: `cd35395f BP-009B moneytop 리스트 초기화를 보정한다`
Goal: apply only the safe table refresh part of the V3 chart moneytop list fix.
Applied scope: clear `ct_tableWidgett_01` before empty-result return; use `df.empty` for empty DataFrame check.
Excluded scope: V3 `starttime < 90030` and query/time normalization are held because 2U_C has coin/stock/future and Kiwoom/future DB path branches.
Excluded LS dependency: all LS API/runtime files excluded.
Kiwoom adjustment: preserved existing Kiwoom/coin/future DB query branches.
DB impact: no schema or query path change.
UI impact: narrow table refresh behavior only; no pyd/UI broad merge.
Verification commands: `python -m py_compile ui/ui_show_dialog.py`; `git diff --check`; `git diff --cached --check`; root/2U_C `verify_release_sync.py`.
Verification result: passed before docs sync.
Remaining risk: GUI chart moneytop runtime was not launched offline.
Rollback plan: revert 2U_C code commit `cd35395f` if chart moneytop refresh regresses.
## Applied 2U_C V3 backport: residual batch `BP-009C` / `BP-010A` / `BP-011A` / `BP-012A` / `BP-013A` / `BP-014A`

Source window: V3.07, V3.11, V3.12, V3.17, V3.18 residual candidate review after `BP-009B`.

Backport result:

- `2UC-V3-BP-010A`: applied Binance websocket malformed/non-data payload guard in `trade/binance/binance_receiver_tick.py`.
  - Target code commit: `41a09d76 BP-010A Binance 웹소켓 비정형 수신을 무시한다`.
- `2UC-V3-BP-011A`: applied residual timezone/dependency cleanup in `utility/telegram_bot.py`, `requirements32.txt`, `requirements64.txt`.
  - Target code commit: `59ffaafc BP-011A 잔여 timezone 의존성을 제거한다`.
- `2UC-V3-BP-009C`: hold. Chart moneytop time/query normalization requires runtime evidence because 2U_C keeps coin/stock/future and tick/min DB branches.
- `2UC-V3-BP-012A`: no-op/hold. 2U_C already keeps BackCodeTest wrapper boundary; V3 pyd split names do not map safely.
- `2UC-V3-BP-013A`: hold. Strategy-test dummy microstructure change requires analysis runtime/test spec.
- `2UC-V3-BP-014A`: hold/excluded. Order-type guard requires broker support matrix before Kiwoom/custom integration.

Excluded from this batch: LS API, DB migration, pyd/UI broad merge, V3U-only pyd-free work, websocket resource-manager rewrite, Telegram runtime rewrite, analysis runtime wiring, broad backtest engine restructure.

Directive: After this residual batch, do not continue blind candidate loops. Start only a final closure audit or a new design track with explicit evidence/spec.

## Final closure audit: V3 -> 2U_C selected backport cycle

Final audit date: 2026-05-08

Closure result: no immediate safe candidate remains after `BP-010A` and `BP-011A`.

Evidence:

- Root and 2U_C residual batch docs match by SHA256.
- `verify_release_sync.py` passed for root.
- `verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev` passed for 2U_C.
- `py_compile` passed for `trade/binance/binance_receiver_tick.py` and `utility/telegram_bot.py`.
- Direct `pytz`, `dateutil`, `tzlocal` residue scan found no hits outside `_update.txt`.
- Forbidden artifact guard found no `_database`, `_log`, `*.db`, or `backtest/graph` status entries in root/2U_C.
- `STOM_Version_3U_C` branch remains absent.

Directive: Do not continue blind V3 -> 2U_C backport loops after this point. Open a new BP-ID only when new evidence/spec exists: runtime reproduction, mockable test case, broker order-type matrix, DB migration spec, analysis runtime wiring spec, or a new V3 upstream source update.

## Post-closure status check: V3 -> 2U_C selected backport cycle

Check date: 2026-05-08

Executed recommended OMX status command after final closure audit.

Evidence:

- Root latest closure commit observed: `a17e59be V3 선별 백포트 종료 기준을 고정한다`.
- 2U_C latest closure mirror commit observed: `eb04a981 V3 선별 백포트 종료 기준을 2U_C에 미러링한다`.
- `verify_release_sync.py` passed for root.
- `verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-dev` passed for 2U_C.
- Root and 2U_C worktrees were clean after the check.

Directive: Keep `no-more-safe-candidates` as the default state. Do not open another V3 -> 2U_C backport loop without new evidence/spec or a new upstream V3 source update.
## Post-closure recheck 002: V3 -> 2U_C selected backport cycle

Check date: 2026-05-08

Executed the recommended OMX status command again after post-closure status check.

Evidence:

- Root status remained clean at `STOM_Version_2` ahead 83.
- 2U_C status remained clean at `STOM_Version_2U_C` ahead 78.
- Root release sync passed.
- 2U_C release sync passed.
- No new immediate safe candidate was identified.

Directive: Keep `no-more-safe-candidates` as the default state. Repeated status checks should not become new code backport loops without new evidence/spec.