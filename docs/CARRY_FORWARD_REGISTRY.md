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

## Goal reset: V3K full feature migration for 2U_C

Date: 2026-05-08

The previous `no-more-safe-candidates` state is reinterpreted as closure of the safe micro-candidate backport queue only. It is not proof that all non-LS V3 features have been implemented in `STOM_Version_2U_C`.

New target:

- `V3K = V3 features + Kiwoom retained`.
- Implement V3 non-LS features in `STOM_Version_2U_C`, including learning/analysis modules, V3-compatible learning DB/schema, backtest learning-data loading, and realtime learning-data usage.
- Exclude direct LS Securities REST/TR/REAL broker dependency.

Authoritative planning document:

- `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`

Directive: Do not continue blind BP micro-candidate loops for this goal. Start `V3K-DESIGN-0` first, then proceed through DB/schema, analyzer contract, backtest learning, realtime learning, UI, and verification phases. Do not rewrite existing V2/2U/2U_C history; use corrective commits and explicit migration specs.

## V3K-DESIGN-1: DB/learning-data design

- Date: 2026-05-09 KST
- Root commit target: `STOM_Version_2`
- Final implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_design_1_db_learning_design.md`
  - `docs/superpowers/specs/2026-05-09-v3k-db-learning-migration-spec.md`
- Decision: Preserve 2U_C/Kiwoom core DBs. Do not replace `setting.db`, `strategy.db`, `tradelist.db`, or `code_info.db` with V3 versions.
- Decision: Start V3 analyzer learning DBs in a shadow/read-only design: `pattern_analysis.db`, `volume_spike.db`, `volume_profile.db`, `volatility_pattern.db`, `volatility_stop_take.db`, plus optional `v3k_meta.db` and `v3k_code_meta.db`.
- Decision: Backtest learning data must default to `last_update < backtest_date`; same-day `<=` use remains hold until leakage safety is proven.
- Next: `V3K-DESIGN-1B` read-only schema diff/dry-run scripts, then `V3K-DESIGN-2` analyzer/data contract.

Directive: Do not create, modify, or commit `_database`, `_database_v3k_shadow`, `backup/_database_pre_v3k_*`, or `*.db` while executing DESIGN-1/1B. Runtime wiring belongs to later V3K-IMPL phases only.
## V3K-DESIGN-1B: read-only schema/dry-run scripts

- Date: 2026-05-09 KST
- Root commit target: `STOM_Version_2`
- Final implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_design_1b_readonly_scripts.md`
  - `scripts/diff_v3_vs_2uc_db_schema.py`
  - `scripts/init_v3k_shadow_db.py`
  - `scripts/v3k_db_health.py`
- Decision: DESIGN-1B scripts are verification scaffolding only. They must not create or modify `_database`, `_database_v3k_shadow`, `backup`, or `*.db`.
- Verification: `py_compile` passed; schema diff, shadow manifest, and health reports were written only under `.omx/reports/`.
- Next: `V3K-DESIGN-2` analyzer/data contract and Kiwoom data shape mapping.

Directive: Keep the scripts read-only until a later V3K-VERIFY-approved cutover stage. Runtime analyzer wiring must not import these scripts directly.

## V3K-DESIGN-2: analyzer/data contract

- Date: 2026-05-09 KST
- Root commit target: `STOM_Version_2`
- Final implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_design_2_analyzer_data_contract.md`
  - `docs/superpowers/specs/2026-05-09-v3k-analyzer-data-contract-spec.md`
- Decision: V3 analyzer modules must enter 2U_C through a Kiwoom-preserving adapter boundary, not by direct broad runtime merge.
- Decision: Feature flags default OFF. Analyzer output must not affect order/exit rules until a later explicitly verified facade stage.
- Decision: `strategy/analyzer_risk.py` in 2U_C remains dormant until import, fixture, OFF-regression, ON-smoke, and registry evidence are satisfied.
- Excluded: direct LS Securities REST/TR/REAL dependency, core DB replacement, `_database`/`*.db` artifacts, broad `manager_formula` or `stg_globals_func` replacement.
- Next: `V3K-IMPL-2A` adapter skeleton + AnalyzerRisk dormant smoke fixture in `STOM_Version_2U_C`.

Directive: Use this contract as the gate before implementing V3 analyzer learning/backtest/realtime wiring. If a future implementation needs to violate this boundary, create a new decision record before code changes.
## V3K-IMPL-2A: adapter skeleton + AnalyzerRisk dormant smoke

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_impl_2a_adapter_risk_smoke.md`
  - `strategy/v3k_analyzer_adapter.py`
  - `scripts/smoke_v3k_analyzer_adapter.py`
- Decision: V3K analyzer integration starts from a feature-flagged adapter boundary, not direct runtime wiring.
- Decision: Dormant `strategy.analyzer_risk.AnalyzerRisk` can be smoke-tested through `V3KAnalyzerAdapter` only when `V3K_BACKTEST_LEARNING_ENABLED`, `V3K_RISK_ANALYZER_V3_ENGINE`, and `리스크분석` are all enabled.
- Verification: py_compile passed; default OFF smoke passed; explicit ON AnalyzerRisk smoke passed for stock/coin tick/min synthetic fixtures.
- Excluded: `backtest/backengine_base.py` runtime wiring, realtime receiver/order path, core DB changes, LS API dependency, formula/global replacement.
- Next: `V3K-IMPL-2B` analyzer module staging and field-contract smoke.

Directive: Keep V3K analyzer flags default OFF until OFF regression and explicit runtime wiring verification pass. Do not let AnalyzerRisk output affect order/exit rules before the formula/global facade stage.
## V3K-IMPL-2B: analyzer module staging

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_impl_2b_analyzer_module_staging.md`
  - `strategy/analyzer_candle_pattern.py`
  - `strategy/analyzer_volume_spike.py`
  - `strategy/analyzer_volume_profile.py`
  - `strategy/analyzer_volatility_pattern.py`
  - `strategy/analyzer_volatility_stop_take.py`
  - `scripts/smoke_v3k_analyzer_modules.py`
- Decision: V3 analyzer modules are staged for import/field-contract verification only. They remain disconnected from backtest/realtime runtime.
- Decision: Analyzer constructors are not invoked in this phase because V3 analyzer DB classes initialize tables. DB use belongs to the later read-only/cutover gate.
- Verification: py_compile passed; module import smoke passed; stock/coin tick/min field-contract smoke passed; IMPL-2A adapter OFF/ON smoke still passed; forbidden artifact guard clean.
- Excluded: backtest runtime wiring, realtime receiver/order path, DB file/schema creation, formula/global facade, LS API dependency.
- Next: `V3K-IMPL-3` backtest learning-data load path under feature flag default OFF and read-only DB policy.

Directive: Do not instantiate staged analyzer classes from runtime until the V3K learning DB path, last_update policy, feature flags, and OFF regression guard are all verified.
## V3K-IMPL-3: backtest learning-data read-only load path

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_impl_3_backtest_learning_loader.md`
  - `strategy/v3k_analyzer_adapter.py`
  - `scripts/smoke_v3k_learning_loader.py`
- Decision: Backtest learning-data load policy uses strict `last_update < backtest_date`; same-day `<=` remains excluded to avoid leakage.
- Decision: Learning DB access starts as read-only adapter path only. Missing DB returns diagnostics and never creates `_database_v3k_shadow` or `*.db`.
- Decision: Feature flags default OFF. Actual read query requires `V3K_BACKTEST_LEARNING_ENABLED` plus analyzer-specific flag.
- Verification: py_compile passed; learning loader smoke passed; analyzer module smoke passed; IMPL-2A adapter OFF/ON smoke passed; forbidden artifact guard clean.
- Excluded: analyzer constructor invocation, DB file/schema creation, backtest loop output injection, realtime receiver/order path, formula/global facade, LS API dependency.
- Next: `V3K-IMPL-3B` backtest dry-run/no-op hook under feature flag default OFF.

Directive: Do not let backtest runtime instantiate analyzer DB classes or create learning DB files before the read-only load plan and OFF regression guard are wired and verified.
## V3K-IMPL-3B: backtest learning-data dry-run/no-op hook

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_impl_3b_backtest_learning_hook.md`
  - `backtest/backengine_base.py`
  - `scripts/smoke_v3k_backtest_learning_hook.py`
- Decision: `BackEngineBase` now has a `PrepareV3KLearningLoadPlan()` dry-run hook. With feature flags OFF it returns an empty tuple and does not mutate the load plan.
- Decision: Flag ON still remains missing-DB/read-only no-op unless an approved learning DB exists; the hook stores load diagnostics only and does not instantiate analyzers or affect orders.
- Verification: py_compile passed; backtest hook smoke passed; learning loader smoke passed; analyzer module smoke passed; adapter OFF/ON smoke passed; release sync passed; forbidden artifact guard clean.
- Excluded: analyzer constructor invocation, learning DB/table creation, `Strategy()` globals injection, order/exit changes, realtime receiver/order path, formula/global facade, LS API dependency.
- Next: `V3K-IMPL-4` realtime learning-data usage boundary under feature flag default OFF and missing-DB no-op.

Directive: Do not use `v3k_learning_load_plan` to alter strategy decisions until formula/global facade and OFF/ON regression evidence exist.

## V3K-IMPL-4: realtime learning-data boundary

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_impl_4_realtime_learning_boundary.md`
  - `strategy/v3k_analyzer_adapter.py`
  - `scripts/smoke_v3k_realtime_learning_boundary.py`
- Decision: Realtime learning-data usage starts as an adapter-only preload boundary. It does not import or modify Kiwoom receiver, trader, order, or strategy decision paths.
- Decision: `V3KRealtimeLearningAdapter` uses `V3K_REALTIME_LEARNING_ENABLED` as its master flag, while the existing backtest loader keeps `V3K_BACKTEST_LEARNING_ENABLED` by default.
- Decision: Default OFF returns no load results. ON with missing learning DB returns diagnostics only and never creates `_database_v3k_shadow` or `*.db`.
- Decision: Tick preload excludes `candle_pattern`; min preload includes it.
- Verification: py_compile passed; realtime learning boundary smoke passed; backtest learning hook smoke passed; learning loader smoke passed; analyzer module smoke passed; adapter OFF/ON smoke passed; forbidden artifact guard clean.
- Excluded: Kiwoom realtime receiver/order path changes, order/exit changes, formula/global facade injection, DB file/schema creation, core DB replacement, LS API dependency.
- Next: `V3K-IMPL-5` formula/global facade under feature flag default OFF and no-op/diagnostic behavior.

Directive: Do not call realtime preload results from live order/strategy decisions until the formula/global facade and OFF/ON regression evidence exist. Do not create learning DB files from this adapter boundary.

## V3K-IMPL-5: formula/global facade

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_impl_5_formula_global_facade.md`
  - `strategy/v3k_analyzer_adapter.py`
  - `strategy/v3k_formula_facade.py`
  - `scripts/smoke_v3k_formula_facade.py`
- Decision: V3 analyzer output is prepared for formula/global consumption through a side-effect-free facade only. Runtime `globals().update(...)`, `trade/formula_manager.py`, and `trade/base_strategy.py` are not changed in this phase.
- Decision: The implementation follows the existing design flag names: `V3K_FORMULA_MANAGER_ADAPTER` and `V3K_STG_GLOBALS_FACADE`. Both must be ON before prefixed globals are built.
- Decision: Facade output uses `V3K_`-prefixed callable names, for example `V3K_리스크점수()`, to avoid collisions with existing strategy/formula names.
- Verification: py_compile passed; formula/global facade smoke passed; realtime learning boundary smoke passed; backtest learning hook smoke passed; learning loader smoke passed; analyzer module smoke passed; analyzer adapter OFF/ON smoke passed; forbidden artifact guard clean.
- Excluded: Kiwoom receiver/order/strategy path changes, order/exit changes, runtime globals update, analyzer constructor runtime calls, DB file/schema creation, core DB replacement, LS API dependency.
- Next: `V3K-VERIFY-1A` OFF-regression and untouched-path audit before any UI/setting exposure or runtime dry-run hook.

Directive: Do not call `globals().update(...)` with V3K facade output from live runtime until OFF-regression, ON synthetic smoke, and explicit runtime hook design evidence exist. Keep unprefixed analyzer names out of globals until collision safety is proven.

## V3K-VERIFY-1A: OFF regression and untouched-path audit

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_verify_1a_off_regression_audit.md`
  - `scripts/audit_v3k_verify_1a.py`
- Decision: Before adding UI/setting exposure or runtime dry-run hooks, V3K implementation state is audited against OFF-regression and untouched-path invariants.
- Decision: The audit base is the parent of `V3K 설계 문맥을 2U_C 구현 lane에 고정한다` (`090421c167be26b1a5d2c4ec55023f5f5064058a` at this run).
- Verification: py_compile passed; VERIFY-1A audit passed; formula/global facade smoke passed; realtime learning boundary smoke passed; backtest learning hook smoke passed; learning loader smoke passed; analyzer module smoke passed; analyzer adapter OFF/ON smoke passed; forbidden artifact guard clean.
- Evidence: Kiwoom/runtime untouched audit passed; V3K flags default-OFF audit passed; forbidden artifact guard passed; Python-code LS dependency marker audit passed.
- Excluded: Kiwoom receiver/order/strategy path changes, `trade/base_strategy.py` runtime injection, `trade/formula_manager.py` runtime globals update, DB file/schema creation, core DB replacement, LS API dependency.
- Next: `V3K-IMPL-6A` non-invasive settings/feature-flag surface contract before any MainWindow/pyd wrapper or live runtime hook.

Directive: Treat VERIFY-1A as the gate for further V3K exposure. Do not add runtime globals update, live order/exit use, or GUI wrapper changes until the settings surface contract and another OFF regression pass are committed.

Post-commit correction: `scripts/audit_v3k_verify_1a.py` must skip its own marker table when scanning Python code for LS dependency markers; otherwise the audit self-reports its forbidden-pattern constants as a false positive.

## V3K-IMPL-6A: non-invasive settings surface contract

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_impl_6a_settings_surface.md`
  - `strategy/v3k_settings_surface.py`
  - `scripts/smoke_v3k_settings_surface.py`
  - `strategy/v3k_analyzer_adapter.py`
  - `scripts/audit_v3k_verify_1a.py`
- Decision: V3K setting exposure starts as a contract-only surface. It normalizes dict/JSON-like input and never reads or writes DB files.
- Decision: `V3K_ANALYSIS_UI_ENABLED` is added as a default-OFF flag, but no MainWindow/pyd wrapper or GUI runtime code is changed in this phase.
- Decision: All analyzer, learning, formula/global, and UI exposure keys remain default OFF and must stay aligned with `DEFAULT_FLAGS`.
- Verification: py_compile passed; settings surface smoke passed; VERIFY-1A audit passed; formula/global facade smoke passed; realtime learning boundary smoke passed; backtest learning hook smoke passed; learning loader smoke passed; analyzer module smoke passed; analyzer adapter OFF/ON smoke passed; forbidden artifact guard clean.
- Excluded: MainWindow/pyd wrapper changes, UI clicked/activated wrapper changes, Kiwoom receiver/order/strategy path changes, runtime globals update, DB file/schema creation, core DB replacement, LS API dependency.
- Next: `V3K-VERIFY-1B` final closure audit before any GUI/runtime hook phase.

Directive: Do not connect V3K settings surface to GUI wrappers or DB-backed settings without another OFF regression pass and explicit user approval for the GUI/runtime surface.

## V3K-VERIFY-1B: final closure audit

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_verify_1b_final_closure_audit.md`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: The `STOM_Version_2U_C` V3K safe-staged goal is complete at the adapter/contract/read-only/no-op level.
- Completed: DB/learning design and read-only scripts; analyzer module staging; AnalyzerRisk adapter smoke; backtest learning loader/hook; realtime learning boundary; formula/global facade; non-invasive settings surface; OFF regression and Kiwoom untouched audit.
- Held for safety: direct LS broker dependency; core DB replacement/cutover; MainWindow/pyd wrapper integration; live runtime globals hook; live order/exit use of analyzer output; analyzer DB constructor runtime use; V3 microstructure engine replacement beyond existing 2U_C paths.
- User approval required: DB shadow/cutover rehearsal; GUI setting surface connection; live Kiwoom runtime dry-run hook; production learning DB read; analyzer output use in actual strategy/order/exit logic.
- Verification: py_compile passed; VERIFY-1B closure audit passed; VERIFY-1A audit passed; settings surface smoke passed; formula/global facade smoke passed; realtime learning boundary smoke passed; backtest learning hook smoke passed; learning loader smoke passed; analyzer module smoke passed; analyzer adapter OFF/ON smoke passed; forbidden artifact guard clean.
- Next: default state is STOP / approval gate. Further GUI/runtime/DB cutover work must start only after explicit user approval and a new scoped phase document.

Directive: Do not continue automatic V3K implementation loops after VERIFY-1B. Treat 2U_C V3K as safe-staged complete; new GUI, live runtime, or DB cutover work requires explicit approval and a fresh plan.

## V3K-CLOSEOUT: safe-staged completion approval gate

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_closeout_safe_staged_completion.md`
- Decision: V3K safe-staged implementation is complete and the default next state is STOP / approval gate.
- Verification: VERIFY-1B closure audit passed; VERIFY-1A audit passed; settings surface smoke passed; release sync passed; forbidden artifact guard clean.
- Completed scope: adapter/contract/read-only/no-op implementation for V3 non-LS learning, analyzer, formula/global, and settings surface features while preserving Kiwoom runtime.
- Not completed by design: GUI wrapper connection, live Kiwoom runtime hook, DB cutover, production learning DB read, analyzer output use in live strategy/order/exit logic.
- Next: no automatic implementation loop. Further GUI/runtime/DB work requires explicit user approval and a fresh phase plan.

Directive: Stop automatic V3K implementation after this closeout. Use only read-only audits unless the user explicitly approves a new GUI, runtime, or DB cutover phase.

## V3K activation gap review: safe-staged vs full activation

- Date: 2026-05-09 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-09_v3k_activation_gap_review.md`
- Decision: V3K safe-staged implementation is complete, but full activation is intentionally not complete.
- Reconfirmed: GUI wrapper connection, live Kiwoom runtime hook, runtime globals update, DB cutover, production learning DB read, analyzer output use in strategy/order/exit, analyzer DB constructor runtime use, and V3 microstructure replacement are not omissions. They are approval-gated activation phases.
- Rationale: Each deferred item can alter GUI/pyd contracts, Kiwoom live runtime behavior, DB/schema state, latency, or live trading decisions. That exceeds the default-OFF/read-only/no-op safe-staged target.
- Final judgment: Deferral is valid for the current V3K safe-staged goal. If the target changes to full production activation, those items must be handled as separate approved phases with dedicated tests, rollback plans, and user approval.
- Verification: Based on prior closeout audits and current clean status; no runtime/code activation changes were made in this review.

Directive: Do not reinterpret safe-staged completion as full production activation. Treat each deferred activation area as a new phase requiring explicit approval.

## V3K-PHASE-A: shadow DB rehearsal

- Date: 2026-05-11 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/plans/2026-05-10_v3k_phase_a_shadow_db_plan.md`
  - `docs/update_log/2026-05-11_v3k_phase_a_shadow_rehearsal.md`
  - `scripts/init_v3k_shadow_db.py`
  - `scripts/apply_v3k_shadow_db.py`
  - `scripts/v3k_db_health.py`
  - `tests/unit/test_v3k_shadow_schema_hash.py`
  - `.omx/reports/v3k-shadow-manifest.json`
- Decision: V3K operational activation starts from an isolated `_database_v3k_shadow/` rehearsal, not from operational `_database/` cutover.
- Decision: `init_v3k_shadow_db.py` remains the schema single source for Phase A. `apply_v3k_shadow_db.py` imports the schema dictionaries and helpers instead of duplicating DDL.
- Decision: `compute_schema_hash()` is the lifetime schema drift key for Phase B-G. It is stamped into dry-run manifest output and `v3k_meta.db.v3k_schema_manifest`.
- Decision: Phase A applies DDL only. `v3k_feature_flags` and `v3k_listed_shares` stay empty, preserving default-OFF and no production data semantics.
- Verification: py_compile passed; schema hash unit tests passed; dry-run manifest generated; pre/post DB health passed; default-OFF row counts passed; V3K audits passed; nonrelease sync passed.
- Excluded: operational `_database/` changes, DB file commit, Kiwoom receiver/order/strategy changes, live runtime hook, analyzer output use in trading logic, LS Securities direct dependency.
- Next: `V3K-PHASE-B` read-only learning DB verification plan. Do not start Phase B implementation without a new phase plan.

Directive: Treat `_database_v3k_shadow/` as a local rehearsal artifact. Never commit DB files. Keep Phase B read-only and preserve Kiwoom runtime boundaries.

## V3K-PHASE-B: read-only learning DB verification

- Date: 2026-05-11 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/plans/2026-05-11_v3k_phase_b_readonly_learning_db_plan.md`
  - `docs/update_log/2026-05-11_v3k_phase_b_readonly_learning_db.md`
  - `scripts/smoke_v3k_learning_db_readonly_existing.py`
  - `strategy/v3k_analyzer_adapter.py`
- Decision: Phase B verifies the existing-learning-DB path without writing fixture rows into the real `_database_v3k_shadow/`. Real shadow DB files are used only for read-only health/hash/count checks.
- Decision: Row-read, leakage cutoff, flag-OFF, missing-DB, limit, and write-rejection behavior are verified in a temp fixture DB that is deleted after the smoke.
- Decision: `V3KLearningDataAdapter` now explicitly closes read-only SQLite connections with `contextlib.closing()` so Windows file handles do not outlive the read-only load.
- Verification: py_compile passed; Phase B read-only learning DB smoke passed; pre/post shadow health passed; existing V3K smoke suite passed; VERIFY-1A audit passed; VERIFY-1B closure audit passed; nonrelease sync passed; DB artifact status clean.
- Excluded: operational `_database/` changes, DB file commit, real shadow fixture row INSERT, Kiwoom receiver/order/strategy/live runtime changes, GUI wrapper integration, formula/global runtime hook, analyzer output use in trading decisions, LS Securities direct dependency.
- Next: plan the next activation boundary separately before Phase C-G work. Candidate boundaries are GUI/settings connection, formula/global runtime hook, live Kiwoom dry-run preload diagnostic, and analyzer output strategy integration.

Directive: Keep production learning DB reads and live trading consumption behind explicit feature flags and fresh phase plans. Do not reinterpret Phase B as DB cutover or live runtime activation.
## V3K-PHASE-C1: GUI/settings default-OFF bridge

- Date: 2026-05-11 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/plans/2026-05-11_v3k_phase_c_activation_boundary_plan.md`
  - `docs/update_log/2026-05-11_v3k_phase_c1_gui_settings_bridge.md`
  - `strategy/v3k_settings_surface.py`
  - `scripts/smoke_v3k_gui_settings_bridge.py`
- Decision: Phase C1 connects V3K settings to a dict-like settings boundary only. It does not change the real settings DB loader, MainWindow wrapper, or GUI layout.
- Decision: `bridge_v3k_settings_into_dict_set()` inserts all V3K keys as default-OFF, preserves legacy dict_set keys, normalizes existing V3K values, and accepts explicit override input without mutating the source dict.
- Decision: The first GUI/settings activation step is no-GUI and default-OFF. Real GUI wrapper exposure remains a separate Phase C2 candidate.
- Verification: py_compile passed; GUI/settings bridge smoke passed; settings surface smoke passed; Phase B read-only DB smoke passed; existing V3K smoke suite passed; VERIFY-1A audit passed; VERIFY-1B closure audit passed; nonrelease sync passed; DB artifact status clean.
- Excluded: operational `_database/` changes, settings DB write migration, MainWindow/pyd wrapper changes, formula globals runtime hook, live Kiwoom preload hook, analyzer output use in trading decisions, LS Securities direct dependency.
- Next: Re-select the next activation boundary. The safest next candidate is Phase C2 GUI wrapper inventory/plan before any actual wrapper mutation.

Directive: Do not wire V3K flags into persistent setting DB writes or GUI wrappers without a Phase C2 plan and GUI/wrapper smoke evidence. Keep all V3K flags default-OFF by default.

## V3K-PHASE-C2-PLAN: GUI wrapper inventory/plan

- Date: 2026-05-11 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md`
  - `docs/update_log/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_selection.md`
  - `docs/plans/2026-05-11_v3k_phase_c_activation_boundary_plan.md`
- Decision: After Phase C1, the next activation boundary is Phase C2 GUI wrapper inventory/plan. This closes Page 011 and opens Page 012.
- Decision: Phase C2 must not start with real checkbox/layout or persistent setting DB writes. The first executable step is a no-GUI wrapper adapter smoke that proves a MainWindow-like object can hold V3K settings/feature flags default-OFF.
- Decision: `ui/set_setup_tap.py`, `ui/ui_mainwindow.py`, `ui/ui_button_clicked_settings.py`, `utility/setting.py`, and `utility/setting_user.py` are known risk boundaries. They must not be changed without C2 smoke evidence and rollback notes.
- Verification: Read-only wrapper inventory completed; Page 011 progress updated to 5/5; audit_v3k_verify_1a, audit_v3k_verify_1b_closure, verify_nonrelease_sync, diff check, and DB artifact status were run before commit.
- Excluded: operational `_database/` changes, settings DB schema/write migration, real PyQt widget exposure, Kiwoom receiver/order/strategy/live runtime changes, formula globals runtime hook, analyzer output use in trading decisions, LS Securities direct dependency.
- Next: `V3K-PHASE-C2-1` no-GUI wrapper adapter smoke. Do not persist V3K flags to `setting.db` or add GUI widgets in the first C2 implementation commit.

Directive: Treat Page 011 completion as completion of the initial planning sequence only, not as full V3K production activation. Continue from Page 012 with narrow, default-OFF, no-GUI evidence before touching real GUI wrappers.

## V3K-PHASE-C2-1: no-GUI GUI-wrapper adapter smoke

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `ui/ui_v3k_settings_bridge.py`
  - `scripts/smoke_v3k_gui_wrapper_bridge.py`
  - `docs/update_log/2026-05-12_v3k_phase_c2_1_gui_wrapper_bridge.md`
  - `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md`
- Decision: C2 starts with a no-GUI/no-DB wrapper adapter helper, not with real GUI checkbox/layout or persistent setting DB writes.
- Decision: `attach_v3k_gui_settings_bridge()` attaches normalized `v3k_settings`, `v3k_feature_flags`, diagnostics, version, and a bridged dict copy to a MainWindow-like object while preserving default-OFF semantics.
- Decision: Existing `dict_set` is not replaced unless `replace_dict_set=True` is explicitly requested; even then, only an in-memory copy is assigned.
- Verification: py_compile passed; `smoke_v3k_gui_wrapper_bridge.py` passed; existing GUI/settings bridge and V3K smoke suite passed; VERIFY-1A/1B passed; nonrelease sync passed; DB artifact status stayed clean.
- Excluded: actual `ui/ui_mainwindow.py` runtime wiring, PyQt widget/checkbox exposure, operational `_database/setting.db` schema/write changes, shadow DB rows, Kiwoom live/order/exit runtime, formula globals runtime hook, analyzer output trading decision, LS Securities direct dependency.
- Next: `V3K-PHASE-C2-2` MainWindow in-memory helper integration. Do not add GUI widgets or persistent DB writes in C2-2.

Directive: Keep C2-1 helper as the narrow bridge contract. Future MainWindow integration should call this helper or preserve the same no-GUI/no-DB/default-OFF behavior.

## V3K-PHASE-C2-2: MainWindow in-memory helper integration

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `ui/ui_mainwindow.py`
  - `ui/ui_v3k_settings_bridge.py`
  - `scripts/smoke_v3k_gui_wrapper_bridge.py`
  - `docs/update_log/2026-05-12_v3k_phase_c2_2_mainwindow_in_memory_bridge.md`
  - `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md`
- Decision: MainWindow now attaches V3K settings state in memory immediately after `self.dict_set = dict_set` and before `WidgetCreater(self)`/widget construction.
- Decision: MainWindow integration does not use `replace_dict_set=True`; it preserves the existing `dict_set` object and adds only V3K in-memory attributes.
- Decision: C2-2 remains a default-OFF state bridge. It is not GUI checkbox exposure, setting DB persistence, or live/runtime activation.
- Verification: py_compile passed; `smoke_v3k_gui_wrapper_bridge.py` includes MainWindow source-level integration order checks and passed; existing V3K smoke suite passed; VERIFY-1A/1B passed; nonrelease sync passed; DB artifact status stayed clean.
- Excluded: PyQt checkbox/layout changes, persistent `_database/setting.db` writes, shadow DB rows, Kiwoom live/order/exit runtime, formula globals runtime hook, analyzer output trading decision, LS Securities direct dependency.
- Next: `V3K-PHASE-C2-3` GUI checkbox/layout feasibility review. Do not add widgets until layout, wrapper alias, settings persistence, and GUI smoke boundaries are documented.

Directive: Treat `v3k_settings`/`v3k_feature_flags` on MainWindow as inert default-OFF state. Do not read them from trading/order/runtime paths without a later approved phase.

## V3K-PHASE-C2-3: GUI checkbox/layout feasibility review

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_c2_3_gui_checkbox_layout_feasibility.md`
  - `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md`
  - `ui/set_setup_tap.py`
  - `ui/ui_button_clicked_settings.py`
  - `ui/ui_mainwindow.py`
- Decision: Actual V3K checkbox/widget exposure is technically feasible but should not be inserted into the existing general settings groupBoxes immediately because fixed geometry, existing load/save buttons, serial-key conditional UI, and pyd-free wrapper aliases make the blast radius larger than C2-3 allows.
- Decision: The safest future UI shape is a dedicated V3K tab or dialog that renders `v3k_settings_contract_rows()` metadata instead of crowding `sj_bs_groupBox_07` or `sj_bs_groupBox_08`.
- Decision: Persistent setting policy must be decided before actual user-toggle widgets are added. Session-only display is possible, but persistent toggles need a C2-4 storage decision.
- Verification: Read-only GUI/layout inventory completed; py_compile passed; wrapper/settings smokes passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.
- Excluded: PyQt checkbox/widget changes, persistent `_database/setting.db` writes, shadow DB rows, Kiwoom live/order/exit runtime, formula globals runtime hook, analyzer output trading decision, LS Securities direct dependency.
- Next: `V3K-PHASE-C2-4` persistent settings storage decision before any real widget commit.

Directive: Do not add V3K checkboxes to existing settings groupBoxes until persistent policy, layout target, wrapper alias impact, and GUI smoke strategy are documented.

## V3K-PHASE-C2-4: persistent settings storage decision

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_c2_4_persistent_storage_decision.md`
  - `docs/plans/2026-05-11_v3k_phase_c2_gui_wrapper_inventory_plan.md`
  - `docs/plans/2026-05-12_v3k_page_013_session_only_ui_preview_plan.md`
- Decision: The next UI implementation boundary is session-only V3K UI preview. Do not persist V3K GUI settings yet.
- Decision: Sidecar settings storage remains the preferred persistence candidate before any operating `setting.db` migration, but it requires a separate file/path/ignore/backup/corruption policy phase.
- Decision: Operating `_database/setting.db` schema/write migration is excluded until a dedicated DB migration/cutover/rollback plan exists.
- Verification: py_compile passed; wrapper/settings smokes passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.
- Excluded: PyQt checkbox/widget changes, sidecar file/DB writes, operating `setting.db` writes, shadow DB rows, Kiwoom live/order/exit runtime, formula globals runtime hook, analyzer output trading decision, LS Securities direct dependency.
- Next: Page 013 / `V3K-PHASE-C2-5` session-only V3K UI preview skeleton. No persistence in that phase.

Directive: Treat Page 012 as complete. The next UI step may add a preview skeleton only if it remains session-only and does not create or mutate any persistent settings artifact.

## V3K-PHASE-C2-5: session-only V3K UI preview skeleton

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_c2_5_session_only_ui_preview.md`
  - `docs/plans/2026-05-12_v3k_page_013_session_only_ui_preview_plan.md`
- Added:
  - `ui/ui_v3k_settings_preview.py`
  - `scripts/smoke_v3k_gui_settings_preview.py`
- MainWindow integration: `attach_v3k_settings_preview(self)` is called after the V3K settings bridge and before `WidgetCreater(self)`.
- Decision: Use a separate lazy dialog skeleton, not an existing settings groupBox.
- Decision: Do not add a visible launcher yet; Page 014 must decide menu/shortcut/layout exposure safety.
- Persistence: none. The preview only mutates `v3k_settings`, `v3k_feature_flags`, and diagnostics on the live MainWindow object.
- Excluded: operating `setting.db` writes, sidecar files, shadow DB rows, Kiwoom live/order/exit runtime, formula globals runtime hook, analyzer trading decision, LS Securities direct dependency.
- Verification: py_compile passed; `smoke_v3k_gui_settings_preview.py` passed; wrapper/settings/settings-surface smokes passed; diff check passed; DB artifact status stayed clean. Full C2 regression set is required before commit/final report.
- Next: Page 014 / `V3K-PHASE-C2-6` session-only preview launcher exposure.

Directive: Do not persist V3K GUI preview state. Any future visible launcher must still open a session-only preview unless a separate sidecar or DB migration phase is approved and verified.

## V3K-PHASE-C2-6: session-only V3K preview launcher exposure

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_c2_6_preview_launcher_exposure.md`
  - `docs/plans/2026-05-12_v3k_page_014_preview_launcher_exposure_plan.md`
  - `docs/plans/2026-05-12_v3k_page_015_gui_preview_closeout_plan.md`
- Modified:
  - `ui/set_main_menu.py`
  - `scripts/smoke_v3k_gui_settings_preview.py`
- Decision: Add a visible `V` launcher in the existing Alt button block.
- Launcher: `v3_pushButton`, shortcut `Alt+V`, geometry `(23, 450, 16, 15)`, action `ShowV3KSettingsPreview()`.
- Persistence: none. The launcher opens the existing session-only preview dialog and does not write `setting.db`, sidecar files, or shadow DB rows.
- Excluded: existing settings groupBox insertion, operating `setting.db` writes, sidecar files, shadow DB rows, Kiwoom live/order/exit runtime, formula globals runtime hook, analyzer trading decision, LS Securities direct dependency.
- Verification: py_compile passed; `smoke_v3k_gui_settings_preview.py` passed with launcher checks; wrapper/settings/settings-surface smokes passed; offline GUI smoke passed; pyd GUI contract passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.
- Next: Page 015 / `V3K-PHASE-C2-7` GUI preview closeout and sidecar persistence decision.

Directive: Keep `Alt+V` as a session-only preview launcher. Do not reinterpret it as persisted feature activation without a separate sidecar or DB migration decision.

## V3K-PHASE-C2-7: GUI preview closeout and sidecar persistence decision

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_c2_7_gui_preview_closeout.md`
  - `docs/plans/2026-05-12_v3k_page_015_gui_preview_closeout_plan.md`
  - `docs/plans/2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md`
- Decision: Close C2 GUI activation lane as complete with session-only preview + `Alt+V` launcher.
- Decision: Defer sidecar persistence. It remains a future option only after file path, ignore, backup, corruption recovery, and `setting_*.db` synchronization policy are written.
- Decision: Keep operating `_database/setting.db` migration prohibited.
- Next: Page 016 / Phase D-0 formula/global runtime boundary design.
- Excluded: sidecar file/DB write, operating `setting.db` write, shadow DB rows, `globals().update` runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, LS Securities direct dependency.
- Verification: py_compile passed; V3K GUI preview/wrapper/settings/settings-surface smokes passed; formula facade smoke passed; offline GUI smoke passed; pyd GUI contract passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.

Directive: Treat C2 as closed. Do not reopen GUI persistence unless a dedicated sidecar/DB migration plan is created; next work should start from Phase D-0 design, not runtime injection.
## V3K-PHASE-D0: formula/global runtime boundary design

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_d0_formula_global_boundary_design.md`
  - `docs/plans/2026-05-12_v3k_page_016_phase_d_formula_global_boundary_plan.md`
  - `docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md`
- Modified:
  - `scripts/smoke_v3k_formula_boundary_contract.py`
- Decision: Treat `trade/formula_manager.py::FormulaManager.UpdateGlobalsFunc` as the existing runtime `globals().update(dict_add_func)` boundary and do not modify it in Phase D-0.
- Decision: Treat `trade/base_strategy.py` dynamic formula callable keys (`dict_add_func[fm[0]]`) as the collision surface that future V3K hook work must dry-run before runtime injection.
- Decision: Keep `strategy/v3k_formula_facade.py` side-effect-free. V3K formula/global candidates must use the `V3K_` prefix and must not import/call trade runtime, Kiwoom order runtime, DB writes, or LS Securities dependencies.
- Added verification: `scripts/smoke_v3k_formula_boundary_contract.py` checks existing update points, no V3K runtime hook/import, prefix/non-collision, default-OFF no-op, and runtime artifact status stability.
- Excluded: `globals().update` runtime hook, `FormulaManager.UpdateGlobalsFunc` modification, Kiwoom live/order/exit runtime, analyzer trading decision, operating `setting.db` write, sidecar write, LS Securities direct dependency.
- Verification: py_compile passed; formula boundary contract smoke passed; formula facade smoke passed; GUI preview smoke passed; settings-surface smoke passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.
- Next: Page 017 / `V3K-PHASE-D1` formula/global dry-run adapter.

Directive: Do not connect V3K formula globals to `globals().update` directly. The next safe step is a dry-run adapter that returns candidate keys and collision diagnostics without mutating runtime globals.
## V3K-PHASE-D1: formula/global dry-run adapter

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_d1_formula_global_dryrun_adapter.md`
  - `docs/plans/2026-05-12_v3k_page_017_phase_d1_formula_global_dryrun_plan.md`
  - `docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md`
- Modified:
  - `strategy/v3k_formula_facade.py`
  - `scripts/smoke_v3k_formula_facade.py`
  - `scripts/smoke_v3k_formula_boundary_contract.py`
- Decision: Add `V3KFormulaGlobalFacade.dry_run()` as a side-effect-free adapter that returns candidate keys, collisions, diagnostics, and candidate globals without mutating runtime globals.
- Decision: Keep `FormulaManager.UpdateGlobalsFunc`, `trade/base_strategy.py`, and any live Kiwoom order/exit runtime untouched in Phase D-1.
- Decision: Treat collisions as not-ready state. Future hook work must require `result.ready` and feature flags default-OFF must remain unchanged.
- Excluded: `globals().update` runtime hook, runtime file guard relaxation, Kiwoom live/order/exit runtime, analyzer trading decision, operating `setting.db` write, sidecar write, LS Securities direct dependency.
- Verification: py_compile passed; formula boundary contract smoke passed; formula facade smoke passed; dry-run OFF no-op/ready/collision smokes passed; GUI preview smoke passed; settings-surface smoke passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.
- Next: Page 018 / `V3K-PHASE-D2` formula/global guarded runtime hook decision.

Directive: Do not call `globals().update` from the V3K facade. If a future hook is approved, it must consume the dry-run `ready`/`collisions` contract and preserve default-OFF rollback behavior.
## V3K-PHASE-D2: formula/global guarded runtime hook decision

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md`
  - `docs/plans/2026-05-12_v3k_page_018_phase_d2_formula_runtime_hook_decision_plan.md`
  - `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md`
- Modified:
  - `scripts/smoke_v3k_formula_runtime_hook_decision.py`
- Decision: Do not modify `FormulaManager.UpdateGlobalsFunc` or call `globals().update` in Phase D-2.
- Decision: Keep `V3KFormulaGlobalFacade.dry_run()` as the formula/global activation boundary until runtime guard relaxation and rollback conditions are explicitly approved.
- Decision: Keep VERIFY-1A runtime file guard for `trade/base_strategy.py` and `trade/formula_manager.py` unchanged.
- Excluded: formula/global runtime hook, runtime file guard relaxation, Kiwoom live/order/exit runtime, analyzer trading decision, operating `setting.db` write, sidecar write, LS Securities direct dependency.
- Verification: py_compile passed; formula runtime hook decision smoke passed; formula boundary contract smoke passed; formula facade smoke passed; GUI preview smoke passed; settings-surface smoke passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.
- Next: Page 019 / `V3K-PHASE-E0` runtime activation gap review.

Directive: Do not treat dry-run readiness as approval for live global namespace mutation. Future runtime hook work must first update the guardrail plan and prove rollback with dedicated smoke/audit coverage.
## V3K-PHASE-E0: runtime activation gap review

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md`
  - `docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md`
  - `docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md`
- Modified:
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: Select `GUI setting persistence sidecar design` as the next runtime activation candidate.
- Decision: Keep formula/global runtime hook, analyzer DB runtime constructor use, live order/exit rule consumption, production learning DB read, and DB cutover/migration deferred.
- Decision: Page 020 is a sidecar persistence design page only. It must not write a sidecar file or operating `setting.db` before path, ignore, backup, corruption recovery, schema version, default-OFF rollback, and smoke policy are documented.
- Excluded: sidecar write implementation, operating `setting.db` write, formula/global runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, LS Securities direct dependency.
- Verification: py_compile passed; runtime activation gap audit passed; V3K smoke set passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB artifact status stayed clean.
- Next: Page 020 / `V3K-PHASE-E1` GUI sidecar persistence design.

Directive: Do not jump from this decision directly to sidecar writes. First complete the Page 020 persistence design contract and prove default-OFF/corruption-recovery behavior with smoke coverage.
## V3K-PHASE-E1: GUI sidecar persistence design

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_e1_gui_sidecar_persistence_design.md`
  - `docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md`
  - `docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md`
- Modified:
  - `.gitignore`
  - `scripts/audit_v3k_gui_sidecar_persistence_design.py`
- Decision: Use `_v3k_sidecar/` as the ignored V3K GUI settings sidecar root and `_v3k_sidecar/v3k_gui_settings.json` as the future settings file candidate.
- Decision: Keep Page 020 as design-only. Do not create sidecar files or implement writes yet.
- Decision: Sidecar schema v1 requires `schema_version`, `surface_version`, `settings`, `updated_at`, and `source`; corrupt/missing/unknown schema must fall back to default-OFF without overwrite.
- Decision: Current V3K GUI preview remains session-only. Future sidecar load should be lower priority than current session preview overrides.
- Excluded: sidecar write implementation, operating `setting.db` write, formula/global runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, LS Securities direct dependency.
- Verification: py_compile passed; GUI sidecar persistence design audit passed; runtime activation gap audit passed; V3K smoke set passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB/sidecar artifact status stayed clean.
- Next: Page 021 / `V3K-PHASE-E2` GUI sidecar schema validator.

Directive: Do not implement sidecar writes before the schema validator proves valid/corrupt/default-OFF behavior without creating runtime artifacts.
## V3K-PHASE-E2: GUI sidecar schema validator

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_e2_gui_sidecar_schema_validator.md`
  - `docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md`
  - `docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md`
- Modified:
  - `strategy/v3k_gui_sidecar.py`
  - `scripts/smoke_v3k_gui_sidecar_schema_validator.py`
  - `scripts/audit_v3k_gui_sidecar_persistence_design.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: Implement a pure V3K GUI sidecar schema validator that accepts mapping/JSON payloads without reading or writing files.
- Decision: Missing/corrupt/unsupported payloads fall back to default-OFF with diagnostics and without overwrite.
- Decision: Valid sidecar settings are lower priority than current session-only preview overrides.
- Excluded: sidecar file read/write, operating `setting.db` write, formula/global runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, LS Securities direct dependency.
- Verification: py_compile passed; GUI sidecar schema validator smoke passed; GUI sidecar persistence design audit passed; runtime activation gap audit passed; V3K smoke set passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB/sidecar artifact status stayed clean.
- Next: Page 022 / `V3K-PHASE-E3` GUI sidecar read-only loader.

Directive: Do not implement sidecar writes before read-only loading and fallback behavior are proven without creating repo `_v3k_sidecar` artifacts.

## V3K-PHASE-E3: GUI sidecar read-only loader

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_e3_gui_sidecar_readonly_loader.md`
  - `docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md`
  - `docs/plans/2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md`
- Modified:
  - `strategy/v3k_gui_sidecar.py`
  - `scripts/smoke_v3k_gui_sidecar_readonly_loader.py`
  - `scripts/audit_v3k_gui_sidecar_persistence_design.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: Add a read-only loader for the `_v3k_sidecar/v3k_gui_settings.json` candidate path without creating directories, writing files, or touching operating setting DBs.
- Decision: Missing/unreadable/corrupt files fall back to default-OFF diagnostics and never trigger overwrite or recovery writes in this phase.
- Decision: Valid file settings remain lower priority than session-only preview overrides.
- Excluded: sidecar write implementation, operating `setting.db` write, formula/global runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, external broker direct dependency.
- Verification: py_compile passed; GUI sidecar read-only loader smoke passed; GUI sidecar persistence design audit passed; runtime activation gap audit passed; V3K smoke set passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB/sidecar artifact status stayed clean.
- Next: Page 023 / `V3K-PHASE-E4` GUI sidecar write guard/rollback decision.

Directive: Do not implement sidecar writes until Page 023 has fixed atomic write, backup, rollback, corruption recovery, no-DB-sync, and artifact handling invariants. Read-only loading is not approval for persistence writes.

## V3K-PHASE-E4: GUI sidecar write guard/rollback decision

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_e4_gui_sidecar_write_guard_decision.md`
  - `docs/plans/2026-05-12_v3k_page_023_phase_e4_gui_sidecar_write_guard_plan.md`
  - `docs/plans/2026-05-12_v3k_page_024_phase_e5_readonly_sidecar_preview_init_plan.md`
- Modified:
  - `scripts/audit_v3k_gui_sidecar_write_guard.py`
  - `scripts/audit_v3k_gui_sidecar_persistence_design.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: Keep actual GUI sidecar write deferred. Page 023 fixes the guard/rollback conditions but does not implement a writer.
- Decision: Required future write conditions are atomic write, backup-before-replace, rollback, corruption recovery, no-DB-sync, session override priority, and artifact cleanliness.
- Decision: `strategy/v3k_gui_sidecar.py` remains read-only and `Actual GUI sidecar write implementation` stays in `USER_APPROVAL_REQUIRED`.
- Excluded: sidecar write implementation, operating `setting.db` write, formula/global runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, external broker direct dependency.
- Verification: py_compile passed; GUI sidecar write guard audit passed; GUI sidecar persistence design audit passed; runtime activation gap audit passed; V3K smoke set passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB/sidecar artifact status stayed clean.
- Next: Page 024 / `V3K-PHASE-E5` read-only sidecar preview initialization bridge.

Directive: Do not convert the read-only sidecar loader into a writer without satisfying the Page 023 approval gate. The next safe step is read-only preview initialization, not persistence writes.

## V3K-PHASE-E5: read-only sidecar preview initialization bridge

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_e5_readonly_sidecar_preview_init.md`
  - `docs/update_log/2026-05-12_v3k_cd6f5bd_to_page024_flow_review.md`
  - `docs/plans/2026-05-12_v3k_page_024_phase_e5_readonly_sidecar_preview_init_plan.md`
  - `docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md`
- Modified:
  - `ui/ui_v3k_settings_preview.py`
  - `scripts/smoke_v3k_gui_sidecar_preview_init.py`
  - `scripts/smoke_v3k_gui_settings_preview.py`
  - `scripts/audit_v3k_gui_sidecar_persistence_design.py`
  - `scripts/audit_v3k_gui_sidecar_write_guard.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: Read-only sidecar values may initialize the session-only preview state, but actual sidecar writes remain deferred.
- Decision: Missing/corrupt sidecars keep default-OFF preview behavior. Valid sidecars only populate in-memory `v3k_settings` / `v3k_feature_flags`.
- Decision: User toggles remain session-only overrides and mark the preview state dirty only in memory.
- Excluded: sidecar write implementation, operating `setting.db` write, formula/global runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, external broker direct dependency.
- Verification: py_compile passed; GUI settings preview smoke passed; GUI sidecar preview init smoke passed; GUI sidecar write guard audit passed; GUI sidecar persistence design audit passed; runtime activation gap audit passed; V3K smoke set passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB/sidecar artifact status stayed clean.
- Next: Page 025 / `V3K-PHASE-E6` sidecar tempfile-only writer prototype.

Directive: Do not treat preview initialization as persistence. The next safe writer work must stay tempfile-only until atomic write, backup, rollback, and corruption recovery are proven.

## V3K-PHASE-E6: sidecar tempfile-only writer prototype

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C`
- Trigger: f51 playbook A1, repeated stepwise V3K command
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_e6_sidecar_tempfile_writer.md`
  - `docs/plans/2026-05-12_v3k_page_025_phase_e6_sidecar_tempfile_writer_plan.md`
  - `docs/plans/2026-05-12_v3k_page_026_phase_h_h1_kiwoom_dryrun_hook_plan.md`
- Modified:
  - `scripts/smoke_v3k_gui_sidecar_tempfile_writer.py`
  - `scripts/audit_v3k_gui_sidecar_write_guard.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: Prototype the future GUI sidecar writer contract inside tempfile directories only.
- Decision: Keep `strategy/v3k_gui_sidecar.py` read-only. The prototype smoke may use `os.replace` and backup files only under `tempfile.TemporaryDirectory`.
- Decision: Invalid payloads, simulated replace failures, and corrupt existing files must roll back or reject without mutating repo artifacts.
- Decision: Actual repo `_v3k_sidecar/v3k_gui_settings.json` writes remain deferred and still require a separate approval gate.
- Excluded: repo sidecar write implementation, operating `setting.db` write, formula/global runtime hook, Kiwoom live/order/exit runtime, analyzer trading decision, external broker direct dependency.
- Verification: py_compile passed; GUI sidecar tempfile-only writer smoke passed; GUI sidecar write guard audit passed; V3K smoke set passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB/sidecar artifact status stayed clean.
- Next: Page 026 / `Phase H H-1` Kiwoom dry-run hook module design.

Directive: Do not promote the tempfile writer prototype into a repo sidecar writer without a separate go/no-go document, user approval, and artifact/rollback verification. The next f51 step is H-1, not actual sidecar write.

## V3K-PHASE-H-H1: Kiwoom dry-run hook contract-only staging

- Branch/worktree: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook A2, Page 026 plan
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_h_h1_kiwoom_dryrun_hook.md`
  - `docs/plans/2026-05-12_v3k_page_026_phase_h_h1_kiwoom_dryrun_hook_plan.md`
  - `docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md`
- Modified/added:
  - `strategy/v3k_kiwoom_dryrun_hook.py`
  - `scripts/smoke_v3k_phase_h_hook_unit.py`
  - `scripts/audit_v3k_phase_h_env_check.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Kiwoom adjustment: live Kiwoom runtime files are not imported or edited. The hook registers only to caller-supplied login/connect receiver methods and remains detached from order/exit/account mutation paths.
- LS dependency exclusion: no LS Securities REST/TR/REAL dependency is introduced.
- Feature flag: `V3K_PHASE_H_KIWOOM_DRYRUN` is default-OFF. H-1 smoke enables it only with a fake tempfile `khopenapi.dll` sentinel.
- Gate decision:
  - H-1 contract-only module/smoke/audit: completed.
  - H-2 actual KHOPENAPI connect/login dry-run: held until compatible environment and explicit user approval.
  - H-3 ON transition/rollback flag/live dry-run monitoring: held until H-2 evidence and explicit user approval.
- Verification:
  - `python -m py_compile strategy/v3k_kiwoom_dryrun_hook.py scripts/smoke_v3k_phase_h_hook_unit.py scripts/audit_v3k_phase_h_env_check.py`
  - `python scripts/smoke_v3k_phase_h_hook_unit.py`
  - `python scripts/audit_v3k_phase_h_env_check.py --stdout`
  - full V3K smoke/audit set, `audit_v3k_verify_1a --base 57496d24`, `audit_v3k_verify_1b_closure`, `verify_nonrelease_sync`, `git diff --check`, DB/sidecar artifact status.
- Next: Page 027 / F5 production learning DB read, with `mode=ro` SQLite read-only URI and DB write/commit prohibition.

Directive: Do not connect this hook to real Kiwoom runtime, KHOPENAPI login, or ON flags without a separate H-2/H-3 user-approval cycle.

## V3K-F5-PROD-READ: production learning DB read-only boundary

- Branch/worktree: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook A3, Page 027 plan
- Records:
  - `docs/update_log/2026-05-12_v3k_f5_production_learning_db_read.md`
  - `docs/plans/2026-05-12_v3k_page_027_f5_production_learning_db_read_plan.md`
  - `docs/plans/2026-05-12_v3k_page_028_mid_checkpoint_v3_plan.md`
- Modified/added:
  - `strategy/v3k_analyzer_adapter.py`
  - `scripts/smoke_v3k_learning_db_production_read.py`
  - `scripts/smoke_v3k_learning_db_leakage_guard.py`
  - `scripts/smoke_v3k_learning_db_fallback.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: Production learning DB access is read-only only. `V3KAnalyzerAdapter.read_production_learning_db(...)` opens DB files only through SQLite `mode=ro` URI and applies `PRAGMA query_only = ON`.
- Decision: Missing production learning DB/table is a successful no-op diagnostic, not a runtime failure.
- Decision: `last_update < backtest_date` remains the leakage invariant. Same-day `<=` remains excluded.
- Current local evidence: `_database` exists, but the five V3K production learning DB candidates are absent in this worktree, so the real production path returned missing-db no-op for all five candidates.
- Kiwoom adjustment: no Kiwoom order/exit/live runtime file is changed. Production read results are not consumed by trading decisions.
- LS dependency exclusion: no LS Securities REST/TR/REAL dependency is introduced.
- Verification:
  - `python -m py_compile strategy/v3k_analyzer_adapter.py scripts/smoke_v3k_learning_db_production_read.py scripts/smoke_v3k_learning_db_leakage_guard.py scripts/smoke_v3k_learning_db_fallback.py`
  - `python -c "from strategy.v3k_analyzer_adapter import V3KAnalyzerAdapter; assert hasattr(V3KAnalyzerAdapter, 'read_production_learning_db')"`
  - `python scripts/smoke_v3k_learning_db_production_read.py`
  - `python scripts/smoke_v3k_learning_db_leakage_guard.py`
  - `python scripts/smoke_v3k_learning_db_fallback.py`
  - full V3K smoke/audit set, `audit_v3k_verify_1a --base 57496d24`, `audit_v3k_verify_1b_closure`, `verify_nonrelease_sync`, `git diff --check`, DB/sidecar artifact status.
- Next: Page 028 / mid-checkpoint v3.

Directive: Do not use production learning DB rows in live strategy/order/exit decisions before Phase F parity, explicit ON gate, rollback flag, and user approval.
## V3K-MIDPOINT-V3: A1/A2/A3 완료 후 중간 점검

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Baseline: `cd6f5bd24bd41a190feb59a8cc65b921df84ca0d`
- Reviewed HEAD: `bbb8975a V3K production learning DB read를 mode-ro 경계로 고정한다`
- Records:
  - `docs/update_log/2026-05-12_v3k_midpoint_checkpoint_cd6f5bd_to_bbb8975a.md`
  - `docs/plans/2026-05-12_v3k_page_028_mid_checkpoint_v3_plan.md`
  - `docs/plans/2026-05-12_v3k_page_029_f1_db_cutover_pre_ralplan_plan.md`
- Decision: v1/v2 checkpoint를 amend하지 않고 v3 snapshot으로 A1/A2/A3 완료 후 방향을 재고정한다.
- Progress: F6 execution progress `225/700 = 32.1%` → `300/700 = 42.9%`; plan coverage `600/700 = 85.7%` → `700/700 = 100.0%`; f51 major step `4/13 = 30.8%`.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다. H-1은 contract-only hook이며 H-2/H-3는 KHOPENAPI 환경과 사용자 승인 전까지 gate로 남긴다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 계속 0건이어야 하며 V3K에서는 영구 금지 항목으로 유지한다.
- DB boundary: F5 production read는 SQLite `mode=ro` + `PRAGMA query_only = ON` 경계만 허용한다. 운영 `_database/` write와 DB 파일 commit은 금지한다.
- Next: Page 029 / `f1-db-cutover-pre-ralplan`. 실제 DB cutover가 아니라 LC1/LC2/LC3 재합의와 pre-mortem 문서화부터 수행한다.

Directive: Do not jump from the v3 checkpoint directly to operational DB cutover. The next safe step is consensus/pre-mortem only; cutover scripts and actual cutover remain separate gated commits.

## V3K-F1-PRE-RALPLAN: DB cutover 사전 합의와 pre-mortem

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook B1, Page 029 plan
- Records:
  - `docs/update_log/2026-05-12_v3k_f1_db_cutover_pre_ralplan.md`
  - `docs/plans/2026-05-12_v3k_page_029_f1_db_cutover_pre_ralplan_plan.md`
  - `docs/plans/2026-05-12_v3k_page_030_f1_cutover_scripts_dryrun_plan.md`
- Decision: F1 cutover는 B1 사전 합의 → B2 script/dry-run → T05 actual cutover의 3단계로 분리한다.
- Decision: Page 030에서는 backup/cutover/rollback script와 tempfile dry-run smoke만 허용하고, 운영 `_database/` write와 actual cutover는 금지한다.
- Decision: LC1 backup-first, LC2 단일 commit + 사용자 명시 승인, LC3 7일 모니터링은 유지하되, `V3K_CUTOVER_USER_ACK`와 branch/backup-first guard를 script 단계에서 강제해야 한다.
- Kiwoom adjustment: DB cutover 준비 단계는 Kiwoom 주문/청산/live runtime을 건드리지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 추가하지 않는다.
- DB boundary: 본 단계는 문서/합의만 수행한다. 운영 `_database/`, `_database_v3k_shadow`, backup 디렉터리, DB 파일은 변경·커밋하지 않는다.
- Next: Page 030 / `f1-cutover-script-dryrun`. 실제 cutover가 아니라 script 신설과 tempfile-only dry-run 검증이다.

Directive: Do not interpret Page 029 approval as actual cutover approval. Only Page 030 script/dry-run work is unlocked; T05 actual cutover still requires explicit user approval and a separate commit cycle.

## V3K-F1-SCRIPT-DRYRUN: DB cutover script와 tempfile 검증

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook B2, Page 030 plan
- Records:
  - `docs/update_log/2026-05-12_v3k_f1_cutover_scripts_dryrun.md`
  - `docs/plans/2026-05-12_v3k_page_030_f1_cutover_scripts_dryrun_plan.md`
  - `docs/plans/2026-05-12_v3k_page_031_f1_actual_cutover_approval_gate_plan.md`
- Added/modified:
  - `scripts/backup_operational_database.py`
  - `scripts/cutover_v3k_shadow_to_database.py`
  - `scripts/smoke_v3k_cutover_dryrun.py`
  - `scripts/rollback_v3k_cutover.py`
  - `.gitignore`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: Page 030은 actual cutover가 아니라 script + tempfile dry-run 검증이다.
- Decision: apply 경로는 branch guard, `V3K_CUTOVER_USER_ACK=1`, backup-first, backup manifest checksum, real `_database` target extra flag를 요구한다.
- Decision: `_database.backup.*/`는 commit 금지 artifact로 `.gitignore`에 추가한다.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 추가하지 않는다.
- DB boundary: smoke는 `tempfile.TemporaryDirectory` fixture만 사용한다. 운영 `_database/`, `_database_v3k_shadow/`, backup 디렉터리, DB 파일은 변경·커밋하지 않는다.
- Verification: py_compile passed; `smoke_v3k_cutover_dryrun.py` passed; runtime activation gap audit passed; VERIFY-1A/1B passed; nonrelease sync passed; diff check passed; DB/sidecar artifact status stayed clean.
- Next: Page 031 / `f1-actual-cutover-approval-gate`. 실제 cutover를 실행하지 말고 사용자 승인과 gate 충족 여부만 문서화한다.

Directive: Do not treat the presence of cutover scripts as approval to run them against `_database/`. Actual cutover still requires a separate user-approved cycle with backup, health, and monitoring evidence.

## V3K-F1-ACTUAL-CUTOVER-GATE: actual cutover 승인 대기

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook F1 actual cutover gate, Page 031 plan
- Records:
  - `docs/update_log/2026-05-12_v3k_f1_actual_cutover_approval_gate.md`
  - `docs/plans/2026-05-12_v3k_page_031_f1_actual_cutover_approval_gate_plan.md`
  - `docs/plans/2026-05-12_v3k_page_032_phase_h_h2_h3_approval_gate_plan.md`
- Decision: actual DB cutover는 현재 BLOCK 상태로 유지한다. Page 030의 script/dry-run PASS는 real `_database` write 승인으로 해석하지 않는다.
- Missing gates: 사용자 명시 승인, `V3K_CUTOVER_USER_ACK=1`, 운영 `_database/` backup apply, backup checksum manifest, actual cutover apply, post-cutover health, 7일 monitoring.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 추가하지 않는다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, backup 디렉터리, DB 파일은 변경·커밋하지 않는다.
- Next: Page 032 / `phase-h-h2-h3-approval-gate`. 실제 KHOPENAPI live dry-run이 아니라 환경/승인 gate 문서화만 수행한다.

Directive: Do not run `cutover_v3k_shadow_to_database.py --apply` against the real `_database/` unless the user explicitly approves actual cutover in a separate cycle.

## V3K-PHASE-H-H2H3-GATE: KHOPENAPI live dry-run 승인 대기

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook B3, Page 032 plan
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_h_h2_h3_approval_gate.md`
  - `docs/plans/2026-05-12_v3k_page_032_phase_h_h2_h3_approval_gate_plan.md`
  - `docs/plans/2026-05-12_v3k_page_033_phase_f_analyzer_pre_ralplan_plan.md`
- Decision: H-2/H-3 actual KHOPENAPI live dry-run과 ON 전환은 현재 BLOCK 상태로 유지한다.
- Missing gates: KHOPENAPI 호환 환경, `V3K_PHASE_H_USER_ACK=1`, live dry-run 승인, 주문 API 0건 증거, post-health, ON 승인, 7일 monitoring.
- Kiwoom adjustment: H-1 contract-only hook은 유지하지만 Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 추가하지 않는다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일은 변경·커밋하지 않는다.
- Next: Page 033 / `phase-f-pre-ralplan`. Phase F analyzer 전략 반영 전 LF1~LF4 재합의만 수행한다.

Directive: Do not run KHOPENAPI connect/login, live dry-run, or Phase H ON transition unless the user explicitly approves an H-2/H-3 execution cycle in a compatible environment.

## V3K-PHASE-F-PRE-RALPLAN: analyzer output ?? ?? ?? ??

- Date: 2026-05-12 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook C1, Page 033 plan
- Records:
  - `docs/update_log/2026-05-12_v3k_phase_f_analyzer_pre_ralplan.md`
  - `docs/plans/2026-05-12_v3k_page_033_phase_f_analyzer_pre_ralplan_plan.md`
  - `docs/plans/2026-05-12_v3k_page_034_phase_f_f123_pre_on_work_plan.md`
- Decision: Phase F? Option A? ????. F-1/F-2/F-3 pre-ON ??? ????, F-4 ON ??? ?? ??? ?? cycle? ????.
- LF1: analyzer output ??? parity ?? ??? ON ????.
- LF2: `V3K_PHASE_F_DISABLE=1` rollback flag? env/DB enable ???? ???? ??.
- LF3: ?? ??? ?? ?5%, MDD ?3%, ???? ?10%? ??. Page034 parity report? ?? ??? ????.
- LF4: `V3K-PHASE-F-ENABLE` registry? Page034?? ???? ???. F-4 ON ?? cycle ????.
- Kiwoom adjustment: pre-ON ??? Kiwoom ??/??/live runtime? ???? ???.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? ??? ???? ???.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, sidecar, DB ??? ??????? ???.
- Next: Page 034 / `phase-f-f123-pre-on-work`. Default-OFF adapter, parity, dual gate, rollback audit? ????.

Directive: Do not treat Phase F pre-ralplan as approval to enable analyzer output in live strategy decisions. F-4 ON requires a separate explicit user-approved cycle with parity, rollback, registry, and monitoring evidence.

## V3K-PHASE-F-F123-PRE-ON: analyzer output 사전 구현과 rollback proof

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook C2, Page 034 plan
- Records:
  - `docs/update_log/2026-05-13_v3k_phase_f_f123_pre_on_work.md`
  - `docs/plans/2026-05-12_v3k_page_034_phase_f_f123_pre_on_work_plan.md`
  - `docs/plans/2026-05-13_v3k_page_035_phase_f_f4_approval_gate_plan.md`
- Added/modified:
  - `strategy/v3k_analyzer_adapter.py`
  - `strategy/v3k_formula_facade.py`
  - `scripts/smoke_v3k_phase_f_default_off.py`
  - `scripts/backtest_v3k_phase_f_parity.py`
  - `scripts/audit_v3k_phase_f_rollback.py`
  - `scripts/audit_v3k_verify_1a.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: F-1/F-2/F-3 pre-ON 작업은 완료한다. F-4 ON 전환은 별도 사용자 승인 gate로 남긴다.
- Gate: `V3K_PHASE_F_ENABLE=1` env gate와 `phase_f_analyzer_strategy.enabled=1` DB-row gate가 모두 true일 때만 candidate callable을 만들 수 있다.
- Rollback: `V3K_PHASE_F_DISABLE=1`은 env/DB enable보다 우선하며 즉시 OFF로 평가된다.
- Parity: Page034 synthetic pre-ON parity는 loss 0.00%, MDD 0.00%, trade count 0.00% delta로 한계 내 PASS다. 이는 runtime hook 미연결 상태의 no-impact baseline이다.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 추가하지 않는다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일은 변경·커밋하지 않는다. `.omx/reports/v3k-phase-f-parity-latest.json`은 ignored local evidence다.
- Next: Page 035 / `phase-f-f4-approval-gate`. 실제 ON이 아니라 사용자 승인과 운영 조건 충족 여부만 확인한다.

Directive: Do not add `V3K-PHASE-F-ENABLE` or run F-4 ON from Page034 evidence alone. F-4 requires a separate explicit user-approved cycle with parity, rollback, registry, and monitoring evidence.

## V3K-PHASE-F-F4-GATE: analyzer output ON 전환 승인 대기

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook C2 이후 F-4 approval gate, Page 035 plan
- Records:
  - `docs/update_log/2026-05-13_v3k_phase_f_f4_approval_gate.md`
  - `docs/plans/2026-05-13_v3k_page_035_phase_f_f4_approval_gate_plan.md`
  - `docs/plans/2026-05-13_v3k_page_036_phase_g_g1_pre_ralplan_plan.md`
- Decision: F-4 ON 전환은 현재 `blocked-awaiting-user-approval`로 고정한다. Page034 pre-ON proof는 ON 승인으로 해석하지 않는다.
- Missing gates: 사용자 명시 승인, `V3K_PHASE_F_USER_ACK=1`, F1 actual cutover 또는 sidecar source-of-truth 결정, `V3K-PHASE-F-ENABLE` registry, 24h monitoring 계획.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다. Analyzer output은 live order/exit rule 소비 경로에 연결하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 추가하지 않는다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일은 변경·커밋하지 않는다.
- Next: Page 036 / `phase-g-g1-pre-ralplan`. Phase G microstructure engine 구현 전에 LG1~LG5 consensus, V3 engine inventory, Kiwoom OPT* mapping, expanded test plan을 먼저 문서화한다.

Directive: Do not create `V3K-PHASE-F-ENABLE`, set `V3K_PHASE_F_USER_ACK=1`, or connect analyzer output to live/runtime decisions unless the user explicitly approves a separate F-4 ON cycle with registry and monitoring evidence.

## V3K-PHASE-G-G1-PRE-RALPLAN: microstructure engine 이식 전 합의

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: f51de818 playbook C3, Page 036 plan
- Records:
  - `docs/update_log/2026-05-13_v3k_phase_g_g1_pre_ralplan.md`
  - `docs/plans/2026-05-13_v3k_page_036_phase_g_g1_pre_ralplan_plan.md`
  - `docs/plans/2026-05-13_v3k_page_037_phase_g_g1_engine_staging_plan.md`
- Decision: Phase G G-1은 Option C, 즉 inventory/mapping-first default-OFF staging으로 진행한다.
- LG invariant: LG1 LS excise audit 0건, LG2 Kiwoom OPT* mapping 선행, LG3 parity ±15%는 G-2에서 검증, LG4 성능 ±20%는 G-2에서 검증, LG5 ON은 사용자 승인 cycle로 분리.
- Kiwoom adjustment: Page036은 문서 합의만 수행했으며 Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 추가하지 않는다. 다음 Page037에서 audit guard를 신설해야 한다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일은 변경·커밋하지 않는다.
- Next: Page 037 / `phase-g-g1-engine-staging`. T01~T05만 수행하고 G-2 parity/benchmark 및 G-3 ON은 섞지 않는다.

Directive: Do not implement Phase G ON, `V3K-PHASE-G-ENABLE`, or live runtime consumption during G-1. G-1 may only create inventory, mapping, LS-free default-OFF engine staging, audit guard, and unit smoke.

## V3K-PHASE-G-G1-STAGING: microstructure engine default-OFF staging

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 037 plan, Phase G G-1 T01~T05
- Records:
  - `docs/plans/v3k_phase_g_inventory.md`
  - `docs/update_log/2026-05-13_v3k_kiwoom_opt_data_shape_mapping.md`
  - `docs/update_log/2026-05-13_v3k_phase_g_g1_engine_staging.md`
  - `docs/plans/2026-05-13_v3k_page_037_phase_g_g1_engine_staging_plan.md`
  - `docs/plans/2026-05-13_v3k_page_038_phase_g_g2_parity_benchmark_plan.md`
- Added/modified:
  - `strategy/v3k_microstructure_engine.py`
  - `scripts/audit_v3k_phase_g_ls_excise.py`
  - `scripts/smoke_v3k_phase_g_engine_unit.py`
  - `strategy/v3k_analyzer_adapter.py`
  - `scripts/audit_v3k_verify_1a.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: G-1 T01~T05는 default-OFF/caller-owned data 전용 staging으로 완료한다. G-2 parity/benchmark와 G-3 ON은 별도 cycle로 분리한다.
- Kiwoom adjustment: 기존 2U_C field name(`현재가`, `초당매수수량`, `매도호가1..5`, `매수잔량1..5`)을 mapping으로 사용하되, Kiwoom API/runtime을 직접 호출하지 않는다.
- Broker dependency exclusion: broker runtime marker와 금지 import는 `scripts/audit_v3k_phase_g_ls_excise.py`에서 0건이어야 한다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일은 변경·커밋하지 않는다.
- Next: Page 038 / `phase-g-g2-parity-benchmark-plan`. parity ±15%, 성능 ±20% 검증을 준비하되 ON은 하지 않는다.

Directive: Do not connect `strategy/v3k_microstructure_engine.py` to live strategy/order/exit paths or create `V3K-PHASE-G-ENABLE` before G-2 proof and a separate G-3 user approval cycle.

## V3K-PHASE-G-G2-PARITY-BENCHMARK-PLAN: microstructure parity/benchmark 실행 전 계획

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 038 plan, Phase G G-2 planning boundary
- Records:
  - `docs/plans/2026-05-13_v3k_page_038_phase_g_g2_parity_benchmark_plan.md`
  - `docs/update_log/2026-05-13_v3k_phase_g_g2_parity_benchmark_plan.md`
  - `docs/plans/2026-05-13_v3k_page_039_phase_g_g2_parity_benchmark_work_plan.md`
- Decision: Page038은 plan-only로 완료한다. `scripts/backtest_v3k_phase_g_parity.py`와 `scripts/benchmark_v3k_phase_g_engine.py` 구현은 Page039에서 수행한다.
- Parity threshold: Phase G output contract 5개 값은 synthetic/caller-owned 기준 fixture 대비 ±15%를 넘지 않아야 한다.
- Benchmark threshold: wall-clock 및 보조 memory 지표는 기준 budget 대비 ±20% 한계를 넘지 않아야 한다.
- Kiwoom adjustment: Kiwoom field name mapping은 Page037 contract를 유지하되, Page039는 Kiwoom API/runtime을 호출하지 않고 caller-owned dict만 사용한다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 Page039 script에도 추가하지 않는다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일은 읽거나 쓰지 않는다. `.omx/reports/*latest.json`은 ignored local evidence로만 생성한다.
- Next: Page 039 / `phase-g-g2-parity-benchmark-work`. 두 신규 script를 구현·실행하되 Phase G ON은 하지 않는다.

Directive: Do not treat Page038 planning completion as permission to enable `V3K_PHASE_G_MICROSTRUCTURE_ENGINE` in runtime or create `V3K-PHASE-G-ENABLE`. Page039 must remain proof-only; Page040/G-3 handles approval gating.

## V3K-PHASE-G-G2-PARITY-BENCHMARK-WORK: microstructure parity/benchmark proof

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 039 plan, Phase G G-2 proof-only implementation
- Records:
  - `scripts/backtest_v3k_phase_g_parity.py`
  - `scripts/benchmark_v3k_phase_g_engine.py`
  - `docs/update_log/2026-05-13_v3k_phase_g_g2_parity_benchmark_work.md`
  - `docs/plans/2026-05-13_v3k_page_039_phase_g_g2_parity_benchmark_work_plan.md`
  - `docs/plans/2026-05-13_v3k_page_040_phase_g_g3_approval_gate_plan.md`
- Decision: Page039는 proof-only로 완료한다. Phase G engine은 explicit `enabled=True` synthetic fixture에서만 parity/benchmark를 실행하고, runtime 기본값은 default-OFF로 유지한다.
- Parity result: `buy_flow`, `sell_flow`, `balanced_flow` scenario가 output contract 5개 값에서 기준 대비 ±15% 한계를 통과했다.
- Benchmark result: 6,000 operations synthetic benchmark가 baseline 3.00s +20% 한계와 peak memory 8,000,000 bytes +20% 한계를 통과했다.
- Kiwoom adjustment: Kiwoom field name은 `KIWOOM_OPT_FIELD_MAPPING`에서 가져온 caller-owned dict로만 사용하며 Kiwoom API/runtime은 호출하지 않는다.
- LS dependency exclusion: 두 신규 script는 LS Securities REST/TR/REAL 직접 의존과 broker runtime marker를 포함하지 않는다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일은 읽거나 쓰지 않는다. `.omx/reports/*latest.json`은 ignored local evidence로만 생성한다.
- Next: Page 040 / `phase-g-g3-approval-gate`. G-2 proof 이후에도 ON은 사용자 승인 gate로 분리한다.

Directive: Do not treat G-2 parity/benchmark PASS as permission to enable `V3K_PHASE_G_MICROSTRUCTURE_ENGINE` in runtime, create `V3K-PHASE-G-ENABLE`, or connect output to live order/exit decisions.

## V3K-PHASE-G-G3-APPROVAL-GATE: microstructure ON 전환 승인 대기

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 040 plan, Phase G G-3 approval gate
- Records:
  - `docs/plans/2026-05-13_v3k_page_040_phase_g_g3_approval_gate_plan.md`
  - `docs/update_log/2026-05-13_v3k_phase_g_g3_approval_gate.md`
  - `docs/plans/2026-05-13_v3k_page_041_v3k_governance_gap_triage_plan.md`
- Decision: Page039 parity/benchmark proof는 통과했지만 Phase G ON은 `blocked-awaiting-user-approval`로 고정한다.
- Missing gates: 사용자 명시 승인, `V3K_PHASE_G_USER_ACK=1`, `V3K-PHASE-G-ENABLE` registry, live order/exit 연결 승인, rollback 운영 승인, 24h monitoring 승인, benchmark/parity baseline archive 정책.
- Kiwoom adjustment: Kiwoom field mapping proof는 유지되지만 Kiwoom API/runtime, 주문/청산/live decision path는 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 계속 금지한다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, sidecar, DB 파일, `.omx/reports/`는 commit 대상이 아니다.
- Next: Page 041 / `governance-gap-triage-plan`. Architect addendum M1/M2/M3를 ON 전 governance 후속으로 triage한다.

Directive: Do not create `V3K-PHASE-G-ENABLE`, set `V3K_PHASE_G_USER_ACK=1`, or connect Phase G output to live order/exit decisions without a separate explicit user-approved ON cycle.

## V3K-GOVERNANCE-GAP-TRIAGE: M1/M2/M3 ON 전 후속 분류

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 041 plan, Architect addendum M1/M2/M3
- Records:
  - `docs/plans/2026-05-13_v3k_page_041_v3k_governance_gap_triage_plan.md`
  - `docs/update_log/2026-05-13_v3k_governance_gap_triage.md`
  - `docs/plans/2026-05-13_v3k_page_042_m1_adapter_coupling_contract_plan.md`
- Decision: M1은 즉시 안전 후보, M2/M3는 별도 설계/정책 page로 보류한다.
- M1: `v3k_analyzer_adapter.py` single point of coupling contract를 Page042에서 docstring/audit 형태로 고정한다.
- M2: audit guard CI/pre-commit 자동화는 tracked runner 또는 CI 정책 선택이 필요하므로 Page041에서 직접 hook 설치하지 않는다.
- M3: `.omx/reports/` commit 금지 원칙과 충돌하므로 baseline evidence archive 정책은 별도 page에서 설계한다.
- Kiwoom adjustment: Kiwoom live runtime, 주문/청산, live decision path는 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 의존은 계속 금지한다.
- DB boundary: 운영 `_database/`, DB 파일, `.omx/reports/`는 commit하지 않는다.
- Next: Page 042 / `governance-m1-adapter-contract`.

Directive: Do not use governance triage as authorization for Phase F/G/H ON. M1/M2/M3 are pre-ON hardening tasks only.

## V3K-GOVERNANCE-M1-ADAPTER-CONTRACT: adapter single point of coupling ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 042 plan, Architect addendum M1
- Records:
  - `docs/plans/2026-05-13_v3k_page_042_m1_adapter_coupling_contract_plan.md`
  - `docs/update_log/2026-05-13_v3k_m1_adapter_coupling_contract.md`
  - `docs/plans/2026-05-13_v3k_page_043_m2_audit_runner_policy_plan.md`
- Added/modified:
  - `strategy/v3k_analyzer_adapter.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: `strategy/v3k_analyzer_adapter.py`? V3K staging ??? single point of coupling?? ????, marker ?? VERIFY-1B guard? contract ??? ????.
- Contract markers: `V3K_SINGLE_POINT_OF_COUPLING`, `V3K_FLAGS_BACKWARD_COMPATIBLE`, `V3K_DEFAULT_FLAGS_MUST_REMAIN_OFF`, `V3K_ANALYZER_OUTPUT_SURFACE_STABLE`, `V3K_NO_BROKER_RUNTIME_SIDE_EFFECTS`.
- Kiwoom adjustment: Kiwoom live runtime, ??/??, live decision path? ???? ???. Adapter contract? staging surface? ????.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? ??? ?? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??, `.omx/reports/`? commit?? ???.
- Next: Page 043 / `governance-m2-audit-runner-policy`. `.git/hooks` ?? ?? ?? repo-tracked audit runner/policy? ????.

Directive: M1 contract completion is not authorization for Phase F/G/H ON. Do not remove or rename V3K adapter flags or stable surfaces without a documented migration plan and updated audits.

## V3K-GOVERNANCE-M2-AUDIT-RUNNER-POLICY: repo-tracked audit runner ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 043 plan, Architect addendum M2
- Records:
  - `scripts/run_v3k_audit_suite.py`
  - `docs/plans/2026-05-13_v3k_page_043_m2_audit_runner_policy_plan.md`
  - `docs/update_log/2026-05-13_v3k_m2_audit_runner_policy.md`
  - `docs/plans/2026-05-13_v3k_page_044_m3_benchmark_archive_policy_plan.md`
- Added/modified:
  - `scripts/run_v3k_audit_suite.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: `.git/hooks` ?? ??? ?? CI ?? ?? `scripts/run_v3k_audit_suite.py`? repo-tracked V3K audit entry point? ????.
- Runner scope: py_compile, Phase G parity/benchmark, LS excise audit, Phase G unit smoke, runtime activation gap, VERIFY-1A, VERIFY-1B, nonrelease sync, `git diff --check`, artifact status guard.
- Kiwoom adjustment: Kiwoom live runtime, ??/??, live decision path? ???? ???. Runner? ??? ????.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? ??? ?? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??? ???? ???. `.omx/reports/*latest.json`? runner ? ??? ? ??? ignored local evidence?? ????.
- Rejected: `.git/hooks` ?? ?? | git ?? ??? ??? ??? ???? ???? ?? Page043?? ???? ???.
- Rejected: ?? CI ?? ?? | ?? CI ??? ???? ??? ?? ??? ??? ????.
- Next: Page 044 / `governance-m3-benchmark-archive-policy`. `.omx/reports` raw artifact commit ?? evidence archive ??? ????.

Directive: Running `scripts/run_v3k_audit_suite.py` proves the staged safety checks pass; it does not authorize Phase F/G/H ON, live Kiwoom runtime wiring, DB cutover, or `.omx/reports` commit.

## V3K-GOVERNANCE-M3-BENCHMARK-ARCHIVE-POLICY: Phase G evidence summary/hash ?? ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 044 plan, Architect addendum M3
- Records:
  - `scripts/summarize_v3k_phase_g_evidence.py`
  - `docs/plans/2026-05-13_v3k_page_044_m3_benchmark_archive_policy_plan.md`
  - `docs/update_log/2026-05-13_v3k_m3_benchmark_archive_policy.md`
  - `docs/plans/2026-05-13_v3k_page_045_governance_closeout_and_approval_gate_plan.md`
- Added/modified:
  - `scripts/summarize_v3k_phase_g_evidence.py`
  - `scripts/run_v3k_audit_suite.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: `.omx/reports` raw JSON? ?? ignored/local evidence? ????, commit ??? docs/update_log summary, threshold, command, SHA-256 hash, pass/fail, scenario/benchmark ???? ????.
- Policy markers: `V3K_PHASE_G_EVIDENCE_ARCHIVE_POLICY`, `RAW_OMX_REPORTS_MUST_REMAIN_UNCOMMITTED`.
- Kiwoom adjustment: Kiwoom live runtime, ??/??, live decision path? ???? ???. Evidence summarizer? local report? ??? ??.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? ??? ?? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??, sidecar artifact? ???? ???. `.omx/reports/*latest.json`? raw commit?? ???.
- Rejected: `.omx/reports/*.json` raw commit | ?? ignored artifact policy? ???? ? ???? timestamp/elapsed ?? ???? ?? ??? hash/summary ???? ????.
- Rejected: benchmark threshold ?? | G-2 proof ??? ???? ???.
- Next: Page 045 / `governance-closeout-and-approval-gate`. M1/M2/M3 governance hardening? ?? ?? ??? approval gate? ????.

Directive: M3 archive policy completion is not authorization for Phase G ON, `.omx/reports` raw artifact commits, live Kiwoom runtime wiring, or DB cutover.

## V3K-GOVERNANCE-CLOSEOUT-APPROVAL-GATE: M1/M2/M3 closeout? approval-gated only ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 045 plan, Page041~Page044 governance hardening
- Records:
  - `docs/plans/2026-05-13_v3k_page_045_governance_closeout_and_approval_gate_plan.md`
  - `docs/update_log/2026-05-13_v3k_governance_closeout_and_approval_gate.md`
  - `docs/plans/2026-05-13_v3k_page_046_approval_gate_handoff_plan.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: M1 adapter coupling contract, M2 audit runner policy, M3 benchmark archive policy? governance hardening ??? ??, ?? ??? ??? approval-gated only? ????.
- Closed governance items: M1 `completed-contract`, M2 `completed-runner-policy`, M3 `completed-archive-policy`.
- Remaining approval gates: Phase F F-4 ON, Phase G G-3 ON, F1 actual DB cutover, H-2/H-3 Kiwoom live dryrun, GUI actual sidecar write, live order/exit rule consumption.
- Kiwoom adjustment: Kiwoom live runtime, ??/??, live decision path? ???? ???. ?? live ?? ??? ??? ??? KHOPENAPI ?? ??? ????.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? ??? ?? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??, sidecar artifact, `.omx/reports` raw artifact? ??/commit?? ???.
- Next: Page 046 / `approval-gate-handoff`. ??? ?? ??? decision matrix? ??? ON/DB/live runtime ??? ?? ???.

Directive: `V3K_GOVERNANCE_CLOSEOUT` means the governance hardening queue is closed; it is not authorization for Phase F/G/H ON, DB cutover, live Kiwoom runtime wiring, or `.omx/reports` raw artifact commits.

## V3K-APPROVAL-GATE-HANDOFF: ??? ?? decision matrix ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 046 plan, Page045 governance closeout
- Records:
  - `docs/plans/2026-05-13_v3k_page_046_approval_gate_handoff_plan.md`
  - `docs/update_log/2026-05-13_v3k_approval_gate_handoff.md`
  - `docs/plans/2026-05-13_v3k_page_047_mission_closeout_review_plan.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: ?? ??? ??? `approval decision matrix`? ????, ??? ?? ?? ??? ?? ON/DB/live runtime ??? ???? ?? STOP condition? ????.
- Approval gates: Phase F F-4 ON, Phase G G-3 ON, F1 actual DB cutover, H-2/H-3 Kiwoom live dryrun, GUI actual sidecar write, live order/exit rule consumption.
- STOP condition: ??? ?? ??, gate? USER_ACK ?? ?? equivalent, rollback/monitoring, `run_v3k_audit_suite.py` PASS, ?? ?? ?? ???, gate ?? ?? ??? ??? ???? ???.
- Kiwoom adjustment: Kiwoom live runtime, ??/??, live decision path? ???? ???. H-2/H-3? live decision? ?? ??? ??? KHOPENAPI ?? ??? ????.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? ??? ?? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??, sidecar artifact, `.omx/reports` raw artifact? ??/commit?? ???.
- Next: Page 047 / `mission-closeout-review`. ?? closeout review? ???? ON/DB/live runtime ??? ?? ???.

Directive: `V3K_APPROVAL_GATE_HANDOFF` is a decision matrix only. It is not authorization for Phase F/G/H ON, DB cutover, live Kiwoom runtime wiring, live order/exit consumption, or raw artifact commits.

## V3K-MISSION-CLOSEOUT-REVIEW: safe-staged mission closed ? approval gate ?? ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 047 plan, Page046 approval gate handoff
- Records:
  - `docs/plans/2026-05-13_v3k_page_047_mission_closeout_review_plan.md`
  - `docs/update_log/2026-05-13_v3k_mission_closeout_review.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: V3K safe-staged mission closed ??? ????, ?? ??? ?? page? ?? `approval-gate-selection` terminal hold? ????.
- Closed scope: DB/learning read-only and tempfile-only tools, analyzer staging, backtest/realtime learning boundary, formula/global facade, GUI sidecar prototype, Kiwoom H-1 dryrun contract, Phase F/G pre-ON proof, M1/M2/M3 governance, approval gate handoff.
- Remaining approval gates: Phase F F-4 ON, Phase G G-3 ON, F1 actual DB cutover, H-2/H-3 Kiwoom live dryrun, GUI actual sidecar write, live order/exit rule consumption.
- Kiwoom adjustment: Kiwoom ??/??/live runtime? ???? ???. H-2/H-3 ?? ??? KHOPENAPI ??? ??? ??? ????.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? broker dependency? ?? ??? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??, sidecar artifact, `.omx/reports` raw artifact? write/commit?? ???.
- Next: `approval-gate-selection`. ??? ?? ?? ??? ? ?? ON/DB/live runtime ?? page? ???? ???.

Directive: `V3K_MISSION_CLOSEOUT_REVIEW`? safe-staged mission closed ? ?? ?? ??? ???. ??? Phase F/G/H ON, DB cutover, Kiwoom live runtime, GUI write, live order/exit consumption ???? ???? ? ??.

## V3K-APPROVAL-GATE-SELECTION: ?? gate ????? ?? ?? ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 048 plan, Page047 mission closeout review
- Records:
  - `docs/plans/2026-05-13_v3k_page_048_approval_gate_selection_plan.md`
  - `docs/update_log/2026-05-13_v3k_approval_gate_selection.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: ?? approval gate? ???? ?? ???/??/??/rollback ???? ????. ?? ??? `await-user-gate-approval`?? ??? ?? ?? ??? ?? page? ???? ???.
- Recommended first review candidate: `GUI actual sidecar write`. ?, ?? ?? ??? ??? ??? ??? ?? planning recommendation??.
- Gate order: GUI actual sidecar write ? Phase F F-4 ON ? Phase G G-3 ON ? H-2/H-3 Kiwoom live dryrun ? F1 actual DB cutover ? live order/exit rule consumption.
- Kiwoom adjustment: Kiwoom ??/??/live runtime? ???? ???.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? broker dependency? ?? ??? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??, sidecar artifact, `.omx/reports` raw artifact? write/commit?? ???.
- Next: `await-user-gate-approval`. ???? gate? ????? ???? ?? ??? ???? ??.

Directive: `V3K_APPROVAL_GATE_SELECTION`? gate ?? planning record??, Phase F/G/H ON, DB cutover, Kiwoom live runtime, GUI write, live order/exit consumption ???? ???? ? ??.

## V3K-GUI-SIDECAR-WRITE-APPROVAL-PREP: actual write ? ?? ?? ??

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 049 plan, Page048 approval gate selection
- Records:
  - `docs/plans/2026-05-13_v3k_page_049_gui_sidecar_write_approval_prep_plan.md`
  - `docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_prep.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_gui_sidecar_write_guard.py`
- Decision: GUI actual sidecar write gate? source-of-truth, prompt-to-artifact checklist, rollback/monitoring, STOP condition? ?????. actual writer ??? sidecar artifact ??? ???? ???.
- Current evidence: read-only sidecar loader, write guard audit, tempfile-only writer prototype, full V3K audit suite.
- Kiwoom adjustment: Kiwoom ??/??/live runtime? ???? ???.
- LS dependency exclusion: LS Securities REST/TR/REAL ?? broker dependency? ?? ??? ????.
- DB boundary: ?? `_database/`, `_database_v3k_shadow/`, DB ??, sidecar artifact, `.omx/reports` raw artifact? write/commit?? ???.
- Next: `gui-sidecar-write-await-user-approval`. ??? ?? ??, source-of-truth ??, rollback/monitoring ?? ??? actual writer ???? ???? ???.

Directive: `GUI_SIDECAR_WRITE_APPROVAL_PREP`? ?? ?? ???? actual sidecar write, ON ??, USER_ACK, DB cutover, Kiwoom live runtime ???? ???? ? ??.

## V3K-PHASE-F-F4-ON-APPROVAL-PREP: analyzer strategy ON 승인 전 준비

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 050 plan, Page035 Phase F F-4 approval gate, Page048 approval gate selection
- Records:
  - `docs/plans/2026-05-13_v3k_page_050_phase_f_f4_on_approval_prep_plan.md`
  - `docs/update_log/2026-05-13_v3k_phase_f_f4_on_approval_prep.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: Phase F F-4 ON 전 USER_ACK, enable registry, rollback, monitoring, parity/default-OFF/rollback 검증 조건을 문서화한다. 실제 ON은 수행하지 않는다.
- Current evidence: Phase F default-OFF smoke, Phase F parity baseline, rollback audit, full V3K audit suite.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 broker dependency는 추가하지 않는다.
- DB boundary: 운영 `_database/`, `_database_v3k_shadow/`, DB 파일, sidecar artifact, `.omx/reports` raw artifact는 write/commit하지 않는다.
- Next: `phase-f-f4-on-await-user-approval`. 사용자 명시 승인, `V3K_PHASE_F_USER_ACK=1` 또는 동등 승인 기록, `V3K-PHASE-F-ENABLE` registry, rollback/monitoring 확정 전에는 actual ON을 수행하지 않는다.

Directive: `PHASE_F_F4_ON_APPROVAL_PREP`는 승인 준비 기록이며 Phase F ON, USER_ACK 생성, enable registry 생성, DB cutover, Kiwoom live runtime 변경으로 해석하면 안 된다.

## V3K-PHASE-G-G3-ON-APPROVAL-PREP: microstructure engine ON 승인 전 준비

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 051 plan, Page039 Phase G G-2 parity/benchmark work, Page040 Phase G G-3 approval gate
- Records:
  - `docs/plans/2026-05-13_v3k_page_051_phase_g_g3_on_approval_prep_plan.md`
  - `docs/update_log/2026-05-13_v3k_phase_g_g3_on_approval_prep.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: Phase G G-3 ON 전 USER_ACK, enable registry, rollback/kill switch, monitoring, parity/benchmark/default-OFF/LS-excise 검증 조건을 문서화한다. 실제 ON은 수행하지 않는다.
- Current evidence: Phase G default-OFF unit smoke, Phase G parity proof, Phase G benchmark proof, Phase G LS excise audit, full V3K audit suite.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 broker dependency는 추가하지 않는다.
- DB/artifact boundary: 운영 `_database/`, DB 파일, sidecar artifact, `.omx/reports` raw artifact는 write/commit하지 않는다.
- Next: `phase-g-g3-on-await-user-approval`. 사용자 명시 승인, `V3K_PHASE_G_USER_ACK=1` 또는 동등 승인 기록, `V3K-PHASE-G-ENABLE` registry, rollback/monitoring 확정 전에는 actual ON을 수행하지 않는다.

Directive: `PHASE_G_G3_ON_APPROVAL_PREP`는 승인 준비 기록이며 Phase G ON, USER_ACK 생성, enable registry 생성, DB cutover, Kiwoom live runtime 변경, live order/exit rule 연결로 해석하면 안 된다.

## V3K-PHASE-H-H2-H3-LIVE-DRYRUN-APPROVAL-PREP: Kiwoom live dry-run 승인 전 준비

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 052 plan, Page026 Phase H H-1 contract-only hook, Page032 Phase H H-2/H-3 approval gate
- Records:
  - `docs/plans/2026-05-13_v3k_page_052_phase_h_h2_h3_live_dryrun_approval_prep_plan.md`
  - `docs/update_log/2026-05-13_v3k_phase_h_h2_h3_live_dryrun_approval_prep.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: H-2/H-3 Kiwoom live dry-run 전 KHOPENAPI compatible environment, USER_ACK, zero-order evidence, rollback/kill switch, post-health, monitoring 조건을 문서화한다. 실제 KHOPENAPI connect/login 또는 ON은 수행하지 않는다.
- Current evidence: Phase H H-1 contract-only hook, hook unit smoke, env sentinel audit, full V3K audit suite.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 broker dependency는 추가하지 않는다.
- DB/artifact boundary: 운영 `_database/`, DB 파일, live artifact, `.omx/reports` raw artifact는 write/commit하지 않는다.
- Next: `phase-h-h2-h3-live-dryrun-await-user-approval`. 사용자 명시 승인, KHOPENAPI 환경 확인, `V3K_PHASE_H_USER_ACK=1` 또는 동등 승인 기록, zero-order evidence/post-health/monitoring 확정 전에는 actual live dry-run 또는 ON을 수행하지 않는다.

Directive: `PHASE_H_H2_H3_LIVE_DRYRUN_APPROVAL_PREP`는 승인 준비 기록이며 KHOPENAPI connect/login, H-2 live dry-run, H-3 ON, USER_ACK 생성, Kiwoom live runtime 변경, live order/exit rule 연결로 해석하면 안 된다.

## V3K-F1-ACTUAL-DB-CUTOVER-APPROVAL-PREP: 운영 DB cutover 승인 전 준비

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 053 plan, Page029 F1 DB cutover pre-ralplan, Page030 cutover scripts dry-run, Page031 actual cutover approval gate
- Records:
  - `docs/plans/2026-05-13_v3k_page_053_f1_actual_db_cutover_approval_prep_plan.md`
  - `docs/update_log/2026-05-13_v3k_f1_actual_db_cutover_approval_prep.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: F1 actual DB cutover 전 사용자 승인, `V3K_CUTOVER_USER_ACK=1`, backup checksum manifest, rollback, post-cutover health, 7-day monitoring 조건을 문서화한다. 실제 운영 `_database/` write 또는 cutover는 수행하지 않는다.
- Current evidence: backup/cutover/rollback scripts, tempfile-only cutover dry-run smoke, read-only DB health helper, full V3K audit suite.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 broker dependency는 추가하지 않는다.
- DB/artifact boundary: 운영 `_database/`, `_database_v3k_shadow/`, DB 파일, backup directory, raw report artifact는 write/commit하지 않는다.
- Next: `f1-actual-db-cutover-await-user-approval`. 사용자 명시 승인, backup apply, checksum manifest, rollback, post-health, 7-day monitoring 확정 전에는 actual cutover를 수행하지 않는다.

Directive: `F1_ACTUAL_DB_CUTOVER_APPROVAL_PREP`는 승인 준비 기록이며 운영 DB write, actual cutover, USER_ACK 생성, backup apply, rollback apply, DB 파일 commit, Kiwoom live runtime 변경으로 해석하면 안 된다.

## V3K-LIVE-ORDER-EXIT-RULE-CONSUMPTION-APPROVAL-PREP: live decision 연결 승인 전 준비

- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page 054 plan, Page050 Phase F F-4 ON approval prep, Page051 Phase G G-3 ON approval prep, Page052 Phase H H-2/H-3 approval prep, Page053 F1 actual DB cutover approval prep
- Records:
  - `docs/plans/2026-05-13_v3k_page_054_live_order_exit_rule_consumption_approval_prep_plan.md`
  - `docs/update_log/2026-05-13_v3k_live_order_exit_rule_consumption_approval_prep.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: V3K output의 live order/exit rule consumption 전 사용자 승인, `V3K_LIVE_DECISION_USER_ACK=1`, `V3K-LIVE-ORDER-EXIT-ENABLE`, `V3K_LIVE_DECISION_DISABLE=1`, kill switch, shadow/dryrun proof, staged rollout, monitoring 조건을 문서화한다. 실제 live decision wiring은 수행하지 않는다.
- Current evidence: VERIFY-1A Kiwoom/runtime untouched audit, Phase F default-OFF/parity/rollback proof, Phase G parity/benchmark/LS-excise proof, Phase H env sentinel, full V3K audit suite.
- Kiwoom adjustment: Kiwoom 주문/청산/live runtime은 변경하지 않는다.
- LS dependency exclusion: LS Securities REST/TR/REAL 직접 broker dependency는 추가하지 않는다.
- DB/artifact boundary: 운영 `_database/`, DB 파일, live artifact, `.omx/reports` raw artifact는 write/commit하지 않는다.
- Next: `live-order-exit-rule-consumption-await-user-approval`. 사용자 명시 승인, 선행 gate 승인, USER_ACK, enable registry, kill switch, shadow/dryrun proof, staged rollout, monitoring 확정 전에는 actual live order/exit consumption을 수행하지 않는다.

Directive: `LIVE_ORDER_EXIT_RULE_CONSUMPTION_APPROVAL_PREP`는 승인 준비 기록이며 Kiwoom 주문/청산/live runtime 변경, live order/exit rule 연결, USER_ACK 생성, enable registry 생성, Phase F/G/H ON, DB cutover로 해석하면 안 된다.

## V3K-APPROVAL-GATE-CLOSEOUT-REVIEW: Page049-Page054 approval gate closeout review
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page049-Page054 approval prep completion and final gate alignment review.
- Records:
  - `docs/plans/2026-05-13_v3k_page_055_approval_gate_closeout_review_plan.md`
  - `docs/update_log/2026-05-13_v3k_approval_gate_closeout_review.md`
- Added/modified:
  - `docs/plans/2026-05-13_v3k_page_049_gui_sidecar_write_approval_prep_plan.md`
  - `docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_prep.md`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: Page049-Page054 approval prep is now closed as a user-approval waiting packet. Page049 mojibake/question-mark corruption was repaired. Actual ON, USER_ACK creation, enable registry creation, KHOPENAPI connect/login, operating `_database/` write, DB file commit, Kiwoom live runtime modification, and live order/exit rule wiring were not performed.
- Current evidence: `audit_v3k_runtime_activation_gap`, `audit_v3k_verify_1a --base 57496d24`, `audit_v3k_verify_1b_closure`, full V3K audit suite, `verify_nonrelease_sync`, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, sidecar artifacts, and raw `.omx/reports` artifacts were not committed.
- Next: `live-order-exit-rule-consumption-await-user-approval` remains the single next candidate, but actual live decision wiring still requires explicit user approval, USER_ACK, enable registry, kill switch, shadow/dryrun proof, staged rollout, monitoring, and green audits.

Directive: `APPROVAL_GATE_CLOSEOUT_REVIEW` is a review/guardrail record only. Do not interpret it as approval for actual ON, USER_ACK creation, enable registry creation, KHOPENAPI connect/login, operating DB write, Kiwoom live runtime modification, or live order/exit rule connection.

## V3K-APPROVAL-GATE-FINAL-DECISION-TABLE: remaining gate user decision table
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page055 approval gate closeout review and remaining user approval gates.
- Records:
  - `docs/plans/2026-05-13_v3k_page_056_approval_gate_final_decision_table_plan.md`
  - `docs/update_log/2026-05-13_v3k_approval_gate_final_decision_table.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: The six remaining gates are fixed as a final user decision table: GUI actual sidecar write, Phase F F-4 ON, Phase G G-3 ON, Phase H H-2/H-3 Kiwoom live dry-run, F1 actual DB cutover, and live order/exit rule consumption. This does not grant or execute any gate.
- Current evidence: runtime activation gap audit, VERIFY-1A, VERIFY-1B, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, sidecar artifacts, live artifacts, and raw `.omx/reports` artifacts were not committed.
- Next: `live-order-exit-rule-consumption-await-user-approval` remains the single next candidate, but actual execution still requires explicit user approval, USER_ACK, enable registry, rollback/kill switch, monitoring owner, fallback trigger, and green audits.

Directive: `APPROVAL_GATE_FINAL_DECISION_TABLE` is a user-decision aid only. Do not interpret it as approval for actual ON, USER_ACK creation, enable registry creation, KHOPENAPI connect/login, operating DB write, Kiwoom live runtime modification, or live order/exit rule connection.

## V3K-GUI-ACTUAL-SIDECAR-WRITE-PREFLIGHT: actual write approval preflight
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page056 approval gate final decision table selected GUI actual sidecar write as the first recommended approval gate.
- Records:
  - `docs/plans/2026-05-13_v3k_page_057_gui_actual_sidecar_write_preflight_plan.md`
  - `docs/update_log/2026-05-13_v3k_gui_actual_sidecar_write_preflight.md`
- Added/modified:
  - `scripts/audit_v3k_gui_sidecar_write_guard.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
- Decision: GUI actual sidecar write preflight is complete, but actual writer implementation/execution remains blocked. `_v3k_sidecar/v3k_gui_settings.json` is only the source-of-truth candidate until user approval. `V3K_GUI_SIDECAR_USER_ACK=1` was not created.
- Current evidence: GUI sidecar write guard audit, tempfile-only writer smoke, runtime activation gap audit, VERIFY-1A, VERIFY-1B, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, DB files, raw `.omx/reports` artifacts, and live artifacts were not committed.
- Next: actual GUI sidecar write still requires explicit user approval, `V3K_GUI_SIDECAR_USER_ACK=1` or equivalent approval record, writer call-site decision, rollback owner, monitoring owner, fallback trigger, and green audits.

Directive: `GUI_ACTUAL_SIDECAR_WRITE_PREFLIGHT` is a preflight record only. Do not interpret it as approval for actual sidecar write, USER_ACK creation, writer implementation, MainWindow wiring, operating DB write, Kiwoom live runtime modification, or live order/exit rule connection.
## V3K-APPROVAL-ORDER-RUNTIME-NEXT-RECONCILIATION: approval order and runtime next split
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page056 final decision table, Page057 GUI actual sidecar write preflight, runtime activation gap audit.
- Records:
  - `docs/plans/2026-05-13_v3k_page_058_approval_order_runtime_next_reconciliation_plan.md`
  - `docs/update_log/2026-05-13_v3k_approval_order_runtime_next_reconciliation.md`
- Added/modified:
  - `docs/update_log/2026-05-13_v3k_approval_gate_final_decision_table.md`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: `gui-sidecar-write-await-user-approval` remains recommended approval order first, while `live-order-exit-rule-consumption-await-user-approval` remains runtime critical next candidate. They are separate axes and neither value grants actual gate execution.
- Current evidence: runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed.
- Next: actual GUI sidecar write remains the first recommended approval cycle, but it still requires explicit user approval, USER_ACK or equivalent approval record, writer call-site decision, rollback owner, monitoring owner, fallback trigger, and green audits.

Directive: `APPROVAL_ORDER_RUNTIME_NEXT_RECONCILIATION` is a guardrail and meaning split record only. Do not interpret it as approval for actual sidecar write, ON transition, USER_ACK creation, enable registry creation, KHOPENAPI connect/login, operating DB write, Kiwoom live runtime modification, or live order/exit rule connection.
## V3K-GUI-SIDECAR-WRITE-APPROVAL-EXECUTION-PACKET: actual write ?? ?? packet
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page057 GUI actual sidecar write preflight and Page058 approval order reconciliation.
- Records:
  - `docs/plans/2026-05-13_v3k_page_059_gui_sidecar_write_approval_execution_packet_plan.md`
  - `docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md`
- Added/modified:
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
- Decision: GUI actual sidecar write is prepared as an approval execution packet only. The source of truth candidate is `_v3k_sidecar/v3k_gui_settings.json`, the first payload is default-OFF V3K settings seed, and rollback plus monitoring plus fallback roles are defined. No actual write is performed.
- Current evidence: runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed.
- Next: actual GUI sidecar write still requires explicit user approval, USER_ACK or equivalent approval record, source of truth acceptance, rollback owner acceptance, monitoring owner acceptance, fallback trigger acceptance, and green audits.

Directive: `GUI_SIDECAR_WRITE_APPROVAL_EXECUTION_PACKET` is a blocked approval packet. Do not interpret it as approval for actual sidecar write, USER_ACK creation, writer implementation, MainWindow wiring, ON transition, KHOPENAPI connect/login, operating DB write, Kiwoom live runtime modification, or live order/exit rule connection.
## V3K-GUI-SIDECAR-WRITE-READINESS-AUDIT: actual write pre-approval blocked-readiness audit
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page057 preflight and Page059 approval execution packet.
- Records:
  - `docs/plans/2026-05-13_v3k_page_060_gui_sidecar_write_readiness_audit_plan.md`
  - `docs/update_log/2026-05-13_v3k_gui_sidecar_write_readiness_audit.md`
- Added/modified:
  - `scripts/audit_v3k_gui_sidecar_write_readiness.py`
  - `scripts/audit_v3k_gui_sidecar_write_guard.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: GUI actual sidecar write is prepared but remains blocked. The readiness audit verifies missing USER_ACK, absent sidecar artifact, read-only strategy module, no MainWindow wiring, default-OFF fallback, and clean artifact status.
- Current evidence: GUI sidecar write readiness audit, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed.
- Next: actual GUI sidecar write now requires explicit user approval, USER_ACK or equivalent approval record, owner acceptance, fallback acceptance, and green readiness audit immediately before execution.

Directive: `GUI_SIDECAR_WRITE_READINESS_AUDIT` is a blocked-readiness proof. Do not interpret it as approval for actual sidecar write, USER_ACK creation, writer implementation, MainWindow wiring, ON transition, KHOPENAPI connect/login, operating DB write, Kiwoom live runtime modification, or live order/exit rule connection.
## V3K-REMAINING-APPROVAL-GATE-BLOCKER-AUDIT: six gate no-go guard
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page056 final decision table and Page060 GUI sidecar readiness audit.
- Records:
  - `docs/plans/2026-05-13_v3k_page_061_remaining_approval_gate_blocker_audit_plan.md`
  - `docs/update_log/2026-05-13_v3k_remaining_approval_gate_blocker_audit.md`
- Added/modified:
  - `scripts/audit_v3k_remaining_approval_gates.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: All six remaining approval gates now have one central blocker audit. The audit verifies absent USER_ACK env vars, absent enable registry headings, clean artifact status, stable approval order, and unchanged Kiwoom runtime guard files.
- Current evidence: remaining approval gate blocker audit, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed.
- Next: explicit user approval is required for exactly one gate at a time, starting with `gui-sidecar-write-await-user-approval` if the user chooses to proceed.

Directive: `REMAINING_APPROVAL_GATE_BLOCKER_AUDIT` is a no-go guard. Passing it means gates are still blocked, not approved.
## V3K-GUI-SIDECAR-DEFAULT-OFF-PAYLOAD-PREVIEW: first payload no-write proof
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page059 approval execution packet, Page060 readiness audit, and Page061 remaining approval gate blocker audit.
- Records:
  - `docs/plans/2026-05-13_v3k_page_062_gui_sidecar_default_payload_preview_plan.md`
  - `docs/update_log/2026-05-13_v3k_gui_sidecar_default_payload_preview.md`
- Added/modified:
  - `scripts/preview_v3k_gui_sidecar_default_payload.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: The first GUI sidecar payload is now deterministic and reviewable before approval, but it is preview-only and stdout-only. It validates schema v1, current settings surface version, default-OFF settings, clean artifact status, and unchanged artifact status before/after preview.
- Current evidence: payload preview script, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created by the preview.
- Next: actual GUI sidecar write still requires explicit user approval, USER_ACK or equivalent approval record, owner acceptance, immediate pre-write audit, rollback acceptance, and post-write validation.

Directive: `GUI_SIDECAR_DEFAULT_OFF_PAYLOAD_PREVIEW` is not writer implementation and not approval. Do not create USER_ACK, enable registry, sidecar artifact, MainWindow wiring, DB cutover, KHOPENAPI login, or live decision wiring from this preview.
## V3K-GUI-SIDECAR-WRITE-APPROVAL-TEMPLATE: explicit approval packet
- Date: 2026-05-13 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page059 approval packet, Page060 readiness audit, Page061 blocker audit, and Page062 default-OFF payload preview.
- Records:
  - `docs/plans/2026-05-13_v3k_page_063_gui_sidecar_write_approval_template_plan.md`
  - `docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_template.md`
- Added/modified:
  - `scripts/audit_v3k_gui_sidecar_approval_template.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: The GUI sidecar write gate now has an explicit approval phrase, current review command, future execution command shape, future rollback command shape, and post-write validation checklist. The actual writer and rollback commands remain intentionally absent before approval.
- Current evidence: approval template audit, payload preview, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: actual GUI sidecar writer implementation remains blocked until explicit approval, USER_ACK or equivalent approval record, owner acceptance, green pre-write audit, rollback acceptance, and post-write validation owner are all present.

Directive: `GUI_SIDECAR_WRITE_APPROVAL_TEMPLATE` is template-only. Do not create USER_ACK, writer or rollback scripts, sidecar artifact, MainWindow wiring, DB cutover, KHOPENAPI login, or live decision wiring from this template.
## V3K-GUI-SIDECAR-PREAPPROVAL-COMPLETION-AUDIT: first gate review-ready but execution-blocked
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page059 approval packet, Page060 readiness audit, Page061 blocker audit, Page062 default-OFF payload preview, and Page063 approval template.
- Records:
  - `docs/plans/2026-05-14_v3k_page_064_gui_sidecar_preapproval_completion_audit_plan.md`
  - `docs/update_log/2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md`
- Added/modified:
  - `scripts/audit_v3k_gui_sidecar_preapproval_completion.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: The first GUI sidecar gate is review-ready but execution-blocked. Payload preview, approval template, and audit surface are complete; explicit approval, USER_ACK, writer implementation, rollback implementation, sidecar artifact, and owner acceptance remain intentionally absent.
- Current evidence: pre-approval completion audit, approval template audit, payload preview, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order/exit/live runtime remains unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: actual GUI sidecar writer implementation remains blocked until explicit approval, USER_ACK or equivalent approval record, owner acceptance, green pre-write audit, rollback implementation approval, rollback acceptance, and post-write validation owner are all present.

Directive: `GUI_SIDECAR_PREAPPROVAL_COMPLETION_AUDIT` is not approval. Do not create USER_ACK, writer or rollback scripts, sidecar artifact, MainWindow wiring, DB cutover, KHOPENAPI login, or live decision wiring from this audit.

## V3K-REMAINING-GATE-APPROVAL-MATRIX: six gate approval phrases and no-go verdicts
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page056 final decision table, Page061 blocker audit, and Page064 GUI sidecar pre-approval completion audit.
- Records:
  - `docs/plans/2026-05-14_v3k_page_065_remaining_gate_approval_matrix_plan.md`
  - `docs/update_log/2026-05-14_v3k_remaining_gate_approval_matrix.md`
- Added/modified:
  - `scripts/audit_v3k_remaining_gate_approval_matrix.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: All six remaining V3K gates now have one matrix with gate order, risk, exact approval phrase, required USER_ACK or enable marker, missing execution condition, and current `not executable` verdict. This is a matrix-only record and does not grant actual gate execution.
- Current evidence: remaining gate approval matrix audit, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: the user must explicitly approve exactly one gate before any USER_ACK, enable registry, sidecar write, DB cutover, KHOPENAPI login, Kiwoom live runtime mutation, or live order/exit rule consumption can proceed. The first recommended approval gate remains `gui-sidecar-write-await-user-approval`.

Directive: `REMAINING_GATE_APPROVAL_MATRIX` is not approval. Do not create USER_ACK, enable registry, writer or rollback scripts, sidecar artifact, MainWindow wiring, DB cutover, KHOPENAPI login, Kiwoom live runtime mutation, or live decision wiring from this matrix.

## V3K-GOAL-COMPLETION-AUTHORITY-AUDIT: objective evidence and no-complete guard
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: active V3K objective, Page065 remaining gate approval matrix, and the need to avoid premature completion claims.
- Records:
  - `docs/plans/2026-05-14_v3k_page_066_goal_completion_authority_audit_plan.md`
  - `docs/update_log/2026-05-14_v3k_goal_completion_authority_audit.md`
- Added/modified:
  - `scripts/audit_v3k_goal_completion_authority.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: The current V3K state is safe-staged and review-ready, but final objective completion authority is absent. The remaining six gates still require exactly one explicit user-approved gate cycle at a time before USER_ACK, enable registry, sidecar write, DB cutover, KHOPENAPI login, Kiwoom live runtime mutation, or live order/exit rule consumption can proceed.
- Current evidence: goal completion authority audit, remaining gate approval matrix audit, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: choose either review-only continuation or explicit approval for exactly one gate. The first recommended approval gate remains `gui-sidecar-write-await-user-approval`.

Directive: `V3K_GOAL_COMPLETION_AUTHORITY_AUDIT` is not final completion and not approval. Do not call goal completion, create USER_ACK, enable registry, writer or rollback scripts, sidecar artifact, MainWindow wiring, DB cutover, KHOPENAPI login, Kiwoom live runtime mutation, or live decision wiring from this audit.


## V3K-ONE-GATE-SEQUENCE-GUARD: single gate approval sequencing guard
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page065 remaining gate approval matrix and Page066 goal completion authority audit.
- Records:
  - `docs/plans/2026-05-14_v3k_page_067_one_gate_sequence_guard_plan.md`
  - `docs/update_log/2026-05-14_v3k_one_gate_sequence_guard.md`
- Added/modified:
  - `scripts/audit_v3k_one_gate_sequence_guard.py`
  - `scripts/audit_v3k_runtime_activation_gap.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `scripts/run_v3k_audit_suite.py`
- Decision: The remaining V3K gates now have a sequence guard. Exactly one gate may be approved and executed per cycle, the first recommended approval gate remains `gui-sidecar-write-await-user-approval`, and broad or out-of-order approval remains blocked.
- Current evidence: one gate sequence guard audit, goal completion authority audit, remaining gate approval matrix audit, runtime activation gap audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: continue review-only work or provide exactly one explicit approval phrase. The next executable approval phrase remains `I approve gui-sidecar-write-await-user-approval only`.

Directive: `V3K_ONE_GATE_SEQUENCE_GUARD` is not approval. Do not accept broad approval, create USER_ACK, enable registry, writer or rollback scripts, sidecar artifact, MainWindow wiring, DB cutover, KHOPENAPI login, Kiwoom live runtime mutation, or live decision wiring from this guard.

## V3K-GOAL-COMPLETION-OBJECTIVE-CHECKLIST: active goal evidence map and no-complete verdict
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: active goal continuation, Page068 goal skill handoff, Page069 audit-suite handoff, Page070 approval phrase intake, Page071 first gate preflight, and Page072 first gate blocker snapshot.
- Records:
  - `docs/plans/2026-05-14_v3k_page_073_goal_completion_audit_checklist_plan.md`
  - `docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md`
- Added/modified:
  - `scripts/audit_v3k_goal_completion_objective_checklist.py`
  - `scripts/run_v3k_audit_suite.py`
  - `docs/CARRY_FORWARD_REGISTRY.md`
- Decision: The active V3K objective is now mapped to a prompt-to-artifact checklist. The objective remains `V3 기능 + Kiwoom 유지` with `LS Securities` direct dependency excluded, but final completion is explicitly blocked because actual approval gate execution remains `0/6`.
- Current evidence: objective checklist audit, first gate blocker snapshot audit, first gate preflight audit, gate approval phrase intake audit, goal handoff audit, goal completion authority audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: do not call `update_goal(status="complete")` until all six approval gates have concrete evidence. The first executable approval phrase remains `I approve gui-sidecar-write-await-user-approval only`.

Directive: `V3K_GOAL_COMPLETION_OBJECTIVE_CHECKLIST` is not approval and not completion. Passing it means the goal is correctly understood and safely blocked before gate execution, not that V3K is fully activated.

## V3K-2UC-AGENT-ENTRYPOINT-CONTRACT: branch-local V3K routing guard
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page073 objective checklist showed the active V3K goal is correctly understood but still approval-gated. The branch-local `AGENTS.md` did not yet expose that V3K routing contract to future agents entering this checkout.
- Records:
  - `docs/plans/2026-05-14_v3k_page_074_agent_entrypoint_contract_plan.md`
  - `docs/update_log/2026-05-14_v3k_agent_entrypoint_contract.md`
- Added/modified:
  - `AGENTS.md`
  - `scripts/audit_v3k_agent_entrypoint_contract.py`
  - `scripts/run_v3k_audit_suite.py`
  - `docs/CARRY_FORWARD_REGISTRY.md`
- Decision: `AGENTS.md` now has `V3K_2UC_AGENT_ENTRYPOINT_CONTRACT`, which states `V3K = V3 features + Kiwoom retained`, LS Securities REST/TR/REAL direct dependency exclusion, Kiwoom runtime preservation, approval gate execution `0/6`, the six-gate order, the first exact approval phrase, and the 2U_C verification commands.
- Current evidence: agent entrypoint contract audit, objective checklist audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: future agents should start from `AGENTS.md` and Page073 before deciding whether to continue review-only work or wait for exact one-gate approval.

Directive: `V3K_2UC_AGENT_ENTRYPOINT_CONTRACT` is a routing and safety guard. It does not approve any gate and must not be used to create USER_ACK, enable registry, sidecar artifact, DB cutover, KHOPENAPI login, or live decision wiring.

## V3K-WORKTREE-ENTRYPOINT-ALIGNMENT: current five-worktree map in 2U_C AGENTS
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page074 added the V3K entrypoint to `AGENTS.md`, but the same file still referenced the retired `STOM_V.wt-2uc/` archive layout. The current active map has five worktrees: V2, 2U, V3, 3U, and 2U_C.
- Records:
  - `docs/plans/2026-05-14_v3k_page_075_worktree_entrypoint_alignment_plan.md`
  - `docs/update_log/2026-05-14_v3k_worktree_entrypoint_alignment.md`
- Added/modified:
  - `AGENTS.md`
  - `scripts/audit_v3k_worktree_entrypoint_alignment.py`
  - `scripts/run_v3k_audit_suite.py`
  - `docs/CARRY_FORWARD_REGISTRY.md`
- Decision: `AGENTS.md` now reflects the current five-worktree layout: `STOM_V`/2, `STOM_V.wt-2u`/2U, `STOM_V.wt-3`/3, `STOM_V.wt-3u`/3U, and `STOM_V.wt-dev`/2U_C. `STOM_V.wt-2uc/` is documented as retired/not active.
- Current evidence: worktree entrypoint alignment audit, agent entrypoint contract audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: the layout is now aligned; actual V3K gate execution still requires exact one-gate approval.

Directive: `V3K_WORKTREE_ENTRYPOINT_ALIGNMENT` is layout documentation only. Do not create/delete worktrees, check out branches, or execute approval gates from this record.

## V3K-REMAINING-GATE-STATUS-SUMMARY: machine-readable six-gate no-go status
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page075 aligned the worktree entrypoint. The remaining gate state now needs one machine-readable summary for future agents and progress reporting without executing any gate.
- Records:
  - `docs/plans/2026-05-14_v3k_page_076_remaining_gate_status_summary_plan.md`
  - `docs/update_log/2026-05-14_v3k_remaining_gate_status_summary.md`
- Added/modified:
  - `scripts/summarize_v3k_remaining_gate_status.py`
  - `scripts/audit_v3k_remaining_gate_status_summary.py`
  - `scripts/run_v3k_audit_suite.py`
  - `docs/CARRY_FORWARD_REGISTRY.md`
- Decision: The six remaining approval gates now have a JSON/text/markdown status summary. It reports `actual_gate_execution_progress=0/6`, `safe_staged_progress=about 96%`, the next gate `gui-sidecar-write-await-user-approval`, and the exact first approval phrase while keeping `review_only=true`, `creates_user_ack=false`, `creates_artifacts=false`, and `executes_runtime=false`.
- Current evidence: remaining gate status summary audit, worktree entrypoint alignment audit, agent entrypoint contract audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: actual gate execution still requires exact one-gate approval. The first executable phrase remains `I approve gui-sidecar-write-await-user-approval only`.

Directive: `V3K_REMAINING_GATE_STATUS_SUMMARY` is a no-side-effect status surface. It is not approval, not USER_ACK, not enable registry, and not final goal completion.
