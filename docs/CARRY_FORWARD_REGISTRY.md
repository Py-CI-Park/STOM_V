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
