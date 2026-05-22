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

## V3K-VERIFY1B-LATEST-COVERAGE: closure audit includes Page073-Page076 governance/status
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page073-Page076 added goal completion checklist, agent entrypoint, worktree entrypoint alignment, and remaining gate status summary. VERIFY-1B needed to treat those as part of the closure inventory rather than only relying on the standalone V3K audit suite.
- Records:
  - `docs/plans/2026-05-14_v3k_page_077_verify1b_latest_coverage_plan.md`
  - `docs/update_log/2026-05-14_v3k_verify1b_latest_coverage.md`
- Added/modified:
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `docs/CARRY_FORWARD_REGISTRY.md`
- Decision: VERIFY-1B closure now includes Page068 through Page076 governance/status artifacts, their scripts, audit-suite step names, and no-complete/no-side-effect tokens. The closure audit still reports actual approval gate execution as `0/6` and does not grant approval.
- Current evidence: VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: actual gate execution still requires exact one-gate approval. The first executable phrase remains `I approve gui-sidecar-write-await-user-approval only`.

Directive: `V3K_VERIFY1B_LATEST_COVERAGE` expands closure verification only. It is not approval, not USER_ACK, not enable registry, and not final goal completion.

## V3K-PREAPPROVAL-STOP-CONDITION: stop review-only loop before explicit approval
- Date: 2026-05-14 KST
- Implementation lane: `STOM_Version_2U_C` / `C:/System_Trading/STOM/STOM_V.wt-dev`
- Source/trigger: Page076 created a machine-readable remaining gate status summary and Page077 added it to VERIFY-1B coverage. The next safety need is to prevent endless review-only expansion when no exact one-gate approval exists.
- Records:
  - `docs/plans/2026-05-14_v3k_page_078_preapproval_stop_condition_plan.md`
  - `docs/update_log/2026-05-14_v3k_preapproval_stop_condition.md`
- Added/modified:
  - `scripts/audit_v3k_preapproval_stop_condition.py`
  - `scripts/run_v3k_audit_suite.py`
  - `scripts/audit_v3k_verify_1b_closure.py`
  - `docs/update_log/2026-05-14_v3k_verify1b_latest_coverage.md`
  - `docs/CARRY_FORWARD_REGISTRY.md`
- Decision: V3K now has an explicit pre-approval stop condition: actual gate execution `0/6`, safe-staged progress `about 96%`, no USER_ACK, no sidecar writer/rollback/artifact, clean DB/runtime/live artifacts, and goal completion prohibited. The next meaningful action is the exact first gate approval phrase.
- Current evidence: preapproval stop condition audit, VERIFY-1B closure audit, V3K audit suite, nonrelease sync, diff check, and forbidden artifact status.
- Kiwoom adjustment: Kiwoom API, order, exit, and live runtime remain unchanged.
- LS dependency exclusion: LS Securities REST/TR/REAL direct broker dependency remains excluded.
- DB/artifact boundary: `_v3k_sidecar`, operating `_database/`, `_database_v3k_shadow/`, DB files, backup directory, live artifacts, and raw `.omx/reports` artifacts were not committed or created.
- Next: wait for exact one-gate approval before any execution work. The first executable phrase remains `I approve gui-sidecar-write-await-user-approval only`.

Directive: `V3K_PREAPPROVAL_STOP_CONDITION` is a stop/wait guard. Do not add more review-only execution packets unless new evidence, a new requirement, or exact one-gate approval changes the state.

## V3K-GUI-SIDECAR-WRITE-ACTUAL-APPROVAL

- Date: 2026-05-14 KST
- Branch/lane: `STOM_Version_2U_C`
- Page: Page 079
- User approval text: `gate 1 approved`
- Canonical approval phrase: `I approve gui-sidecar-write-await-user-approval only`
- Gate: `gui-sidecar-write-await-user-approval`
- Status: `completed-gate1-default-off-sidecar-write`
- Runtime artifact: `_v3k_sidecar/v3k_gui_settings.json` local ignored artifact; do not commit.
- Writer: `scripts/write_v3k_gui_sidecar_from_preview.py`
- Rollback: `scripts/rollback_v3k_gui_sidecar.py`
- Audit: `scripts/audit_v3k_gui_sidecar_gate1_execution.py`
- Progress: `1/6` approval gates executed.
- Next gate: `phase-f-f4-on-await-user-approval`.

Scope guard:

- No DB cutover
- No KHOPENAPI connect/login
- No Phase F/G/H ON
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

Directive: This approval only covers the first GUI sidecar default-OFF seed write. Later Phase F/G/H ON, F1 actual DB cutover, and live order/exit consumption each require their own explicit one-gate approval cycle.

## V3K-PHASE-F-ENABLE

- Date: 2026-05-14 KST
- Branch/lane: `STOM_Version_2U_C`
- Page: Page 080
- Canonical approval phrase: `I approve phase-f-f4-on-await-user-approval only`
- Gate: `phase-f-f4-on-await-user-approval`
- Status: `completed-gate2-phase-f-sidecar-enable`
- USER_ACK used during execution: `V3K_PHASE_F_USER_ACK=1`
- Source-of-truth: `_v3k_sidecar/v3k_gui_settings.json` local ignored artifact; do not commit.
- Enabled sidecar setting: `V3K_PHASE_F_ANALYZER_STRATEGY=true`
- Writer: `scripts/write_v3k_phase_f_sidecar_enable.py`
- Audit: `scripts/audit_v3k_phase_f_gate2_execution.py`
- Rollback guard: `V3K_PHASE_F_DISABLE=1` still disables candidate formula output.
- Progress: `2/6` approval gates executed.
- Next gate: `phase-g-g3-on-await-user-approval`.

Scope guard:

- No DB cutover
- No KHOPENAPI connect/login
- No Phase G/H ON
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

Directive: This approval only enables Phase F analyzer strategy as a sidecar source-of-truth for approved candidate formula building. Live order/exit consumption, Phase G/H ON, and F1 actual DB cutover each require their own explicit one-gate approval cycle.

## V3K-PHASE-G-ENABLE

- Date: 2026-05-14 KST
- Branch/lane: `STOM_Version_2U_C`
- Page: Page 081
- Canonical approval phrase: `I approve phase-g-g3-on-await-user-approval only`
- Gate: `phase-g-g3-on-await-user-approval`
- Status: `completed-gate3-phase-g-sidecar-enable`
- USER_ACK used during execution: `V3K_PHASE_G_USER_ACK=1`
- Source-of-truth: `_v3k_sidecar/v3k_gui_settings.json` local ignored artifact; do not commit.
- Enabled sidecar setting: `V3K_PHASE_G_MICROSTRUCTURE_ENGINE=true`
- Preserved sidecar setting: `V3K_PHASE_F_ANALYZER_STRATEGY=true`
- Writer: `scripts/write_v3k_phase_g_sidecar_enable.py`
- Audit: `scripts/audit_v3k_phase_g_gate3_execution.py`
- Rollback guard: `V3K_PHASE_G_DISABLE=1` still disables candidate microstructure engine output.
- Progress: `3/6` approval gates executed.
- Next gate: `phase-h-h2-h3-live-dryrun-await-user-approval`.

Scope guard:

- No DB cutover
- No KHOPENAPI connect/login
- No Phase H ON
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

Directive: This approval only enables Phase G microstructure engine as a sidecar source-of-truth for approved candidate output building. Live order/exit consumption, Phase H ON, and F1 actual DB cutover each require their own explicit one-gate approval cycle.

## V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED

- Date: 2026-05-14 KST
- Branch/lane: `STOM_Version_2U_C`
- Page: Page 082
- Canonical approval phrase: `I approve phase-h-h2-h3-live-dryrun-await-user-approval only`
- Gate: `phase-h-h2-h3-live-dryrun-await-user-approval`
- Status: `blocked-after-approval-missing-khopenapi-environment`
- Completion marker intentionally absent: `V3K-PHASE-H-LIVE-DRYRUN-ACTUAL-APPROVAL`
- USER_ACK status: `V3K_PHASE_H_USER_ACK=1 not used`
- Environment evidence: `khopenapi_compatible=false`
- Live execution evidence: `live_connect_attempted=false`, `order_api_calls=0`, `post_health_passed=false`
- Audit: `scripts/audit_v3k_phase_h_gate4_blocked_environment.py`
- Progress: `3/6` approval gates executed.
- Current gate remains: `phase-h-h2-h3-live-dryrun-await-user-approval`.

Scope guard:

- No DB cutover
- No KHOPENAPI connect/login
- No Phase H ON
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

Directive: This entry records that the user approval phrase was received but live dry-run completion is blocked by the missing KHOPENAPI environment. Do not advance to F1 cutover or live order/exit consumption until Phase H live dry-run evidence proves `khopenapi_compatible=true`, `live_connect_attempted=true`, `order_api_calls=0`, and `post_health_passed=true`.

## V3K-GATE5-GATE6-REVIEW-ONLY-BLOCKED

- Date: 2026-05-14 KST
- Branch/lane: `STOM_Version_2U_C`
- Page: Page 083
- Mode: `review-only`
- Current gate: `phase-h-h2-h3-live-dryrun-await-user-approval`
- Reviewed later gates: `f1-actual-db-cutover-await-user-approval`, `live-order-exit-rule-consumption-await-user-approval`
- Status: `completed-review-only-later-gates-still-blocked`
- Audit: `scripts/audit_v3k_gate5_gate6_review_only_blocked.py`
- Progress: `3/6` approval gates executed.
- Gate 5 phrase remains rejected as out-of-order: `I approve f1-actual-db-cutover-await-user-approval only`
- Gate 6 phrase remains rejected as out-of-order: `I approve live-order-exit-rule-consumption-await-user-approval only`

Scope guard:

- No USER_ACK creation
- No enable registry creation
- No DB cutover
- No KHOPENAPI connect/login
- No live order/exit wiring
- No Kiwoom live runtime mutation
- No direct LS Securities dependency

Directive: This entry is review-only. Gate 5 and Gate 6 remain blocked until Phase H live dry-run completion evidence exists. Do not create `V3K_CUTOVER_USER_ACK=1`, `V3K_LIVE_DECISION_USER_ACK=1`, `V3K-F1-ACTUAL-DB-CUTOVER-APPROVAL`, or `V3K-LIVE-ORDER-EXIT-ENABLE` from this review.

## V3K-AUDIT-V2-COMPAT

- Date: 2026-05-15 KST
- Branch/lane: `STOM_Version_2U_C`
- Plan: `docs/plans/2026-05-14_v3k_audit_v2_compat_kiwoom_sentinel_plan.md` (ralplan iteration 2 합의 v2, `4d132139`)
- Trigger: `docs/update_log/2026-05-14_v3k_gate4_blocked_root_cause_v2_compat.md` (`cdd77093`) Gate4 false-negative 발견
- Tasks executed: T01 (hook 별도 메서드) + T02 (sentinel helper 모듈) + T03 (audit schema v2) + T04a (mock 4 scenario) + T04b (본 PC live audit)
- Commits: `5da51dcd` (T01+T02), `696cc4b3` (T03), `2611ab61` (T04a), 본 commit (T04b + registry + update_log)

### Records

- 신규 파일: `strategy/v3k_kiwoom_sentinel.py` (T02 helper 모듈, 98줄)
- 수정 파일: `strategy/v3k_kiwoom_dryrun_hook.py` (T01, +44줄 dataclass + 신규 메서드)
- 수정 파일: `scripts/audit_v3k_phase_h_env_check.py` (T03, schema v2 + primary/corroborating)
- 신규 파일: `scripts/smoke_v3k_kiwoom_sentinel_scenarios.py` (T04a, mock matrix 4종)
- 신규 evidence: `docs/evidence/v3k-phase-h-env-host-9024e3b9.json` (T04b live audit, host hash trail)

### Decision (Synthesis 1)

1. `khopenapi_compatible` = primary signal S1 ActiveX ProgID 단독 산식 (V07 invariant)
2. corroborating signals (S2 OPENAPI_PATH dir + S3 legacy DLL)는 evidence emit 전용, 결정에 직접 영향 없음
3. audit JSON schema_version 1 → 2 bump, `candidates[]` backward compat 보존
4. hook `resolve_khopenapi_path() -> Path | None` 시그니처 보존, 신규 `resolve_khopenapi_sentinel() -> V3KSentinelResult | None` 별도 메서드

### Verification (V01–V08)

- V01 PASS: `resolve_khopenapi_path` 시그니처 `Path | None` 보존 (정적 assertion)
- V02 PASS: `resolve_khopenapi_sentinel` 신규 메서드 export + `V3KSentinelResult | None` 반환
- V03a/V03b/V04a/V04b PASS: mock scenario matrix 4종 (R4 boundary 포함)
- V05 SKIP: `gate4_blocked_environment` audit은 `primary exists → SKIP` 결정 룰 (plan §D.1)
- V06 PASS: `schema_version == 2` + 신규 4 필드 + `candidates[]` 보존
- V07 PASS: `khopenapi_compatible == khopenapi_primary_signal.exists` invariant
- V08 PASS: 본 PC live audit `khopenapi_compatible=true`, host_identifier=`9024e3b9`, schema_version=2

### Effect

- **Gate4 BLOCKED 자연 해제**: 본 PC에서 `khopenapi_compatible: false → true` 전환
- **`gate4_blocked_environment` audit의 의미 변경**: self-reject (compatible=true 환경이므로 적용 불가). plan v2 §D.1 V05 결정 룰의 코드 측면 자동 검증. 별도 분기 plan(`2026-05-XX_v3k_phase_h_lh4_clarification_plan.md`)에서 audit name/logic 정정 후속 처리.
- Gate5/Gate6 unlock 가능성 회복 (단, 별도 사용자 승인 + Phase H 본체 실행 필요)

Scope guard:

- No Kiwoom runtime mutation (trade/utility/Kiwoom_OpenAPI 0건)
- No operating `_database/` write
- No direct LS Securities dependency
- No `V3K_PHASE_H_USER_ACK=1` creation
- No live connect/login attempted (hook still default-OFF)
- No order/exit wiring

Directive: 본 entry는 audit V2-compat sentinel 보강 완료를 기록한다. Phase H 본체(H-2 dry-run, H-3 ON) 진입은 별도 사용자 명시 승인과 H-2 plan 작성 후에만 진행한다. `gate4_blocked_environment` audit의 self-reject 의미 정정은 분기 plan에서 처리한다.

## V3K-PHASE-H-LH4-CLARIFICATION

- Date: 2026-05-15 KST
- Branch/lane: `STOM_Version_2U_C`
- Plan: `docs/plans/2026-05-15_v3k_phase_h_lh4_clarification_plan.md` (ralplan iteration 2 APPROVE 합의 정본)
- ralplan: iteration 1 (Architect ITERATE / Critic ITERATE 4 Rev + 4 Opt) → iteration 2 (Planner v2 흡수 / Architect APPROVE / Critic APPROVE)
- Trigger: v4 mid-checkpoint `9423735e` §7.1 1순위 잔여 작업 + v2-compat sentinel plan `4d132139` §I.6 위임
- Tasks executed: T01 (신규 environment_status audit 신설, Option B) + T02 (Phase H plan §K.5 amend) + T03 (본 plan commit)

### Records

- 신규 파일: `scripts/audit_v3k_phase_h_gate4_environment_status.py` (`V3K_PHASE_H_GATE4_ENV_STATUS_AUDIT_V1`, 159줄)
- 신규 파일: `docs/plans/2026-05-15_v3k_phase_h_lh4_clarification_plan.md` (분기 plan, ralplan iteration 2 합의 정본)
- 수정 파일: `docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md` (§K에 K.5 단일 절 amend, K.1–K.4 본문 무변경)
- 무변경 (Option B historical 보존): `scripts/audit_v3k_phase_h_gate4_blocked_environment.py` (`b6327b30` historical audit trail)

### Decision (분기 plan ADR §I.1)

1. **Option B 채택**: historical script frozen 보존 + 신규 `environment_status` audit 병렬 추가. rename(Option A)은 audit immutability + docs freeze 충돌 우려로 명시 거부
2. **§K.5 단일 절 amend**: K.6/K.7 신설 위임. K.1–K.4 본문 무변경
3. **LH5 forward-only invariant**: `schema_version >= 2` audit artifact에만 적용. `b6327b30` `schema_version == 1` historical은 retroactive 재평가 배제

### Verification (V01–V08)

- V01 PASS: 신규 script `audit_v3k_phase_h_gate4_environment_status.py` 신설 (Test-Path)
- V02 PASS: historical script `audit_v3k_phase_h_gate4_blocked_environment.py` unchanged (last commit `b6327b30`, no diff)
- V03 PASS: 본 PC unblocked branch 실행 (`primary_signal.exists=True`, schema_version=2, AUDIT_VERSION=V3K_PHASE_H_GATE4_ENV_STATUS_AUDIT_V1)
- V04 PASS: Phase H plan §K.1–K.4 본문 변경 0줄 + §K.5 단일 절 신설
- V05 PASS: LH5 forward-only assertion (`schema_version < 2` 검출 시 AssertionError)
- V06 PASS: Phase H plan amend target 명시 (docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md)
- V07 PASS: docs freeze 충돌 0건 (page082 unchanged, V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED heading 유지)
- V08 PASS: audit_v3k_verify_1a + verify_nonrelease_sync 모두 PASS

### Effect

- **Gate4 environment_status audit가 양 branch 모두 PASS**: 본 PC에서 unblocked branch(`primary_signal.exists=True`) 동작 검증 완료
- **historical audit identity 보존**: `b6327b30` audit trail self-reject 동작 유지 (Option B 채택으로 docs freeze 충돌 0건)
- **LH5 신규 lifetime invariant**: future audit JSON schema bump 의무화 (forward-only 적용 범위 명문화)
- **Phase H §K.6/K.7 위임**: 미래 freeze 예외 사안은 별도 분기 plan으로 처리

Scope guard:

- No Kiwoom runtime mutation (trade/utility/Kiwoom_OpenAPI 0건)
- No operating `_database/` write
- No direct LS Securities dependency
- No `V3K_PHASE_H_USER_ACK=1` creation
- No live connect/login attempted (hook still default-OFF)
- No order/exit wiring
- Historical audit script (`b6327b30`) unchanged

Directive: Phase H §K.5 amend로 v4 mid-checkpoint §7.1 1순위 잔여 작업 종결. 다음 잔여 작업(우선 2: Phase H H-2 본체 dry-run plan)은 별도 ralplan + 사용자 명시 승인 + KHOPENAPI 환경 재확인 + V3K_PHASE_H_USER_ACK=1 필수.

## V3K-STEP2-TO-STEP6-STATUS

- Date: 2026-05-15 KST
- Branch/lane: `STOM_Version_2U_C`
- Plan: `docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md` (status 보고서, implementation plan 아님)
- Trigger: v4 mid-checkpoint `9423735e` §7.1 잔여 작업 + Step 1 closure (`f318d1c1` / `33aa50c5` / `0c1735d4`) 직후 보충 status freeze
- Tasks executed: 본 progress status plan 정본화 + registry 갱신 (단일 commit)

### Records

- 신규 파일: `docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md` (Step 2~6 진척 status 보고서)
- 갱신 파일: `docs/CARRY_FORWARD_REGISTRY.md` (본 섹션 추가)

### Decision

1. **본 plan 정체성 명시**: Step 2~6 실제 implementation plan 의 대체물이 아닌, mission state-of-the-art freeze 의 status 보고서로 정본화
2. **자동 vs 수동 경계 명문화**: Step 2~6 각 단계의 plan ralplan 은 자동, execution trigger (USER_ACK env var + 사용자 명시 phrase + GUI Kiwoom OCX login + 24h/7-day/48h monitoring + transaction lock window 등) 은 본질적으로 수동 사용자 개입 필수
3. **다음 trigger 매트릭스 §G**: Step 2~6 의 의존 / 자동 가능 / 수동 trigger / 시간 경과 항목을 단일 표로 정리. 총 최소 monitoring 경과 시간 24h + 7-day + 24h + 48h ≈ 11일 (이상적 fast-path)
4. **운영자 수동 개입 7항목 §H**: 본 자동 세션 scope 외 항목을 명시. 별도 세션에서 사용자 직접 trigger 후 진행
5. **v5 mid-checkpoint 기준선 명시**: 본 plan 은 v4 mid-checkpoint `9423735e` 시점 진척률 50.0% 의 직후 보충 status 이며, 다음 v5 mid-checkpoint 가 정본화될 때까지 운영 기준선으로 사용

### Verification

- VS1 PASS: docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md 작성 완료
- VS2 PASS: 본 plan §J Scope guard 준수 (runtime mutation 0건, USER_ACK env var 발급 0건, DB/log/shadow/sidecar 미커밋)
- VS3 PASS: docs/plans/2026-05-12_v3k_phase_h_live_kiwoom_dryrun_plan.md (H-2 본체) 기 정본화 사실 확인
- VS4 PASS: docs/plans/2026-05-15_v3k_phase_h_lh4_clarification_plan.md (Step 1) 직후 freeze 확인
- VS5 PASS: registry V3K-STEP2-TO-STEP6-STATUS 섹션 신설

### Effect

- **Mission state-of-the-art 보충 freeze**: v4 mid-checkpoint 이후 Step 1 closure 까지 반영한 진척 보고서로 다음 trigger 시점에 운영자가 즉시 참조 가능
- **다음 trigger 조건 명확화**: 각 Step (2~6) 의 trigger 조건이 단일 매트릭스로 정리되어, 별도 세션에서 사용자가 trigger 단계를 진입할 때 누락/순서 오류 방지
- **자동 vs 수동 경계 명문화**: 본 자동 세션 scope 외 항목 (GUI Kiwoom OCX login, USER_ACK env var, 24h/7-day/48h monitoring, transaction lock window, rollback 의사결정 등) 이 7건으로 한정되어 다음 세션 운영자 개입 범위 사전 합의

Scope guard:

- No Kiwoom runtime mutation (trade / utility / Kiwoom_OpenAPI 0건)
- No operating `_database/` write
- No direct LS Securities dependency
- No USER_ACK env var 발급
- No live connect / login / 주문 경로 wiring
- No DB / log / shadow / sidecar artifact 커밋
- 본 plan 은 docs 1건 + registry 1건 추가에 한정

Directive: 본 status plan 정본화로 v4 mid-checkpoint §7.1 잔여 작업의 mission state-of-the-art 보충 freeze 종결. Step 2 (Phase H H-2 본체 dryrun) 실제 execution 은 사용자가 §B.2 의 4건 trigger 조건 (phrase + `V3K_PHASE_H_USER_ACK=1` + gate4 audit 재실행 + registry 사전 freeze) 을 모두 충족시킨 후 별도 세션에서 진행한다.

## V3K-STEP2-TO-STEP6-MOCK-EXECUTION

- Date: 2026-05-15 KST
- Branch/lane: `STOM_Version_2U_C`
- Plan: `docs/plans/2026-05-15_v3k_step2_to_step6_mock_execution_plan.md`
- Trigger: stop hook feedback (Step 2~6 progress status plan `a7cded80` 직후) — /goal directive 충족을 위해 mock execution layer 까지 진행. Actual execution 은 별도 세션에서 사용자 GUI / USER_ACK env var / 24h+ monitoring trigger 후 진행
- Tasks executed: 통합 mock execution plan 정본화 + 통합 mock execution script 신설 + 본 PC 실행 + evidence freeze + registry 갱신 (단일 commit cycle)

### Records

- 신규 파일: `docs/plans/2026-05-15_v3k_step2_to_step6_mock_execution_plan.md`
- 신규 파일: `scripts/run_v3k_step2_to_step6_mock_execution.py`
- 신규 파일: `docs/evidence/v3k-step2-to-step6-mock-execution-9024e3b9.json` (host_identifier `9024e3b9` 매치, T04b evidence 정합)
- 갱신 파일: `docs/CARRY_FORWARD_REGISTRY.md` (본 섹션)

### Decision (mock execution 정체성)

1. **Mock execution scope 명시**: sentinel mock evaluation + read-only parity check + default-OFF flag normalization + benchmark mock + closure readiness check 의 5단계 mock 만 수행. Actual production 행위 6항목 (Kiwoom runtime mutation / LS / operating DB write / live connect / USER_ACK / 24h+ monitoring) 모두 0건 (scope_guard 필드로 evidence JSON 안에 명시)
2. **Single commit cycle**: context efficiency 를 위해 plan + script + evidence + registry 단일 commit. 각 Step 별 분리 commit 회피
3. **host_identifier 일관성**: T04b evidence `9024e3b9` 와 동일 hash 규칙 (sha256(platform.node())[:8]) 사용. 본 PC 환경 cross-reference 가능
4. **schema_version 분리**: evidence 자체 schema_version=1 (mock evidence 별도 schema). audit_schema_version=2 (LH5 forward-only invariant 와 정합) 별도 필드로 추적

### Verification (V01~V08)

- V01 PASS: `scripts/run_v3k_step2_to_step6_mock_execution.py` 신설
- V02 PASS: 본 PC 실행 결과 — closure_ready=True, 5 step phase 모두 expected 와 매치
- V03 PASS: evidence JSON 생성 (`docs/evidence/v3k-step2-to-step6-mock-execution-9024e3b9.json`), schema_version=1
- V04 PASS: evidence closure_ready=True + Step 2~5 collected_step_set 정합
- V05 PASS: scope_guard 6항목 모두 False (Kiwoom runtime / LS / operating DB write / live connect / USER_ACK / 24h+ monitoring 0건)
- V06 PASS: `audit_v3k_phase_h_gate4_environment_status` 직후 재실행 — branch=unblocked, schema_version=2
- V07 PASS: `audit_v3k_verify_1a --base 9423735e` — Kiwoom/runtime untouched + V3K flag default-OFF + Forbidden artifact + LS marker 모두 PASS
- V08 PASS: `verify_nonrelease_sync` PASS

### Effect

- **Step 2 sentinel mock**: compatible=True, primary_kind=active_x_progid, primary_path=HKEY_CLASSES_ROOT\KHOPENAPI.KHOpenAPICtrl.1, corroboration_count=1 (T04b 와 정합)
- **Step 3 F1 cutover parity mock**: operating_db_count=1176, shadow_db_count=7, parity_status=delta (selective shadow propagation 확인, operating write 0건)
- **Step 4 F3 F-4 mock**: flag_default_off=True, hook_reachable=True, actual_flip 0건
- **Step 5 F4 G-3 mock**: flag_default_off=True, hook_reachable=True, benchmark_ms<1ms, actual_flip 0건
- **Step 6 closure gate mock**: collected_step_set={2,3,4,5}, closure_ready=True, mission_complete_commit 0건
- **Actual execution 직전 baseline evidence 확보**: 각 Step 의 actual execution trigger 시점에 본 mock evidence 를 사전 검증 baseline 으로 인용 가능

Scope guard:

- No Kiwoom runtime mutation (trade / utility / Kiwoom_OpenAPI 0건)
- No operating `_database/` write (read-only inspection 만)
- No direct LS Securities dependency
- No live connect / login / 주문 경로 wiring
- No USER_ACK env var 발급 (4건 모두 미설정)
- No DB / log / shadow / sidecar artifact 커밋 (evidence JSON 만 추가, operating DB 미변경)
- 본 commit 은 plan 1건 + script 1건 + evidence 1건 + registry 1건 추가

Directive: 본 mock execution 으로 Step 2~6 의 본 자동 세션 scope 내 진행 가능 layer 종결. Actual execution 의 trigger 매트릭스 (status plan `2026-05-15_v3k_step2_to_step6_progress_status_plan.md` §G) 은 사용자 명시 phrase + USER_ACK env var + GUI Kiwoom login + 24h/7-day/48h monitoring + transaction lock window 충족 후 별도 세션에서 진행한다.

## V3K-PREPARATION-FIRST-SEQUENCE

- Date: 2026-05-15 KST
- Branch/lane: `STOM_Version_2U_C`
- Plan: `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md`
- Trigger: 사용자 질의 — “페이지 1은 마지막으로 이동하고 2,3,4,5 진행 후 1은 나중에 가능한가 / 미리 준비는 코드 업데이트를 의미하는가”
- Scope: 기준 변경 문서화 + 준비 선행 계획 정본화. 코드/runtime 변경 0건.

### Decision

1. **actual execution 순서는 변경하지 않는다.** Phase H H-2 live dry-run → F1 DB cutover → Phase F F-4 ON → Phase G G-3 ON → F7 closure 순서를 유지한다.
2. **preparation 순서는 분리한다.** F1/F3/F4/F7의 default-OFF 준비 코드, read-only 검증 script, rollback/checksum/benchmark/closure checklist는 Phase H H-2 actual 전에 선행 가능하다.
3. **준비 완료와 actual 완료를 분리 기록한다.** 준비 패키지 commit은 runtime activation 또는 closure progress로 계산하지 않는다.
4. **준비 패키지 guard를 고정한다.** No operating `_database/` write, no live connect/login, no USER_ACK env var, no feature flag default-ON, no Kiwoom order/exit wiring, no LS direct dependency.

### Records

- 신규 파일: `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md`
- 갱신 파일: `docs/CARRY_FORWARD_REGISTRY.md` (본 섹션)

### Preparation-first plan

| 순서 | 작업 | 상태 |
| ---: | --- | --- |
| P0 | 기준 변경 문서화 | 본 commit에서 수행 |
| P1 | F1 cutover prep package (read-only parity/checksum/rollback/preflight) | 다음 추천 작업 |
| P2 | Phase F F-4 prep package (default-OFF parity/approval/rollback) | P1 후 |
| P3 | Phase G G-3 prep package (benchmark/parity/rollback) | P2 후 |
| P4 | F7 closure prep package (manifest/checklist audit) | P3 후 |
| P5 | 준비 선행 중간 점검 | P4 후 |

### Actual execution dependency remains

| 순서 | actual gate | 선행 조건 |
| ---: | --- | --- |
| A1 | Phase H H-2 live dry-run | 사용자 phrase + `V3K_PHASE_H_USER_ACK=1` + GUI Kiwoom login + gate4 audit PASS |
| A2 | F1 DB cutover | A1 closure + 24h monitoring + `V3K_CUTOVER_USER_ACK=1` + transaction lock window |
| A3 | Phase F F-4 ON | A2 closure + 7-day monitoring + `V3K_PHASE_F_USER_ACK=1` |
| A4 | Phase G G-3 ON | A3 closure + 24h monitoring + `V3K_PHASE_G_USER_ACK=1` |
| A5 | F7 closure | A1~A4 actual closure + final phrase |

### Verification

- Plan file created with explicit 기준 변경 / unchanged actual dependency / allowed preparation code table / P0~P5 plan / A1~A5 actual dependency.
- Scope guard: docs-only change, runtime mutation 0건.
- Required follow-up verification for subsequent P1~P5 packages: `audit_v3k_phase_h_gate4_environment_status`, `audit_v3k_verify_1a --base 9423735e`, `verify_nonrelease_sync`, `git diff --check`.

Scope guard:

- No Kiwoom runtime mutation (trade / utility / Kiwoom_OpenAPI 0건)
- No operating `_database/` write
- No direct LS Securities dependency
- No live connect / login / 주문 경로 wiring
- No USER_ACK env var 발급
- No DB / log / shadow / sidecar artifact 커밋
- 본 commit은 plan 1건 + registry 1건 문서 변경에 한정

Directive: 다음 추천 작업은 P1 F1 cutover prep package다. 이 작업은 read-only/default-OFF 준비 코드만 허용하며, actual F1 cutover는 Phase H H-2 live dry-run actual + 24h monitoring evidence 후에만 가능하다.

## V3K-PREPARATION-FIRST-SEQUENCE-EXECUTION

- Date: 2026-05-15 KST
- Branch/lane: `STOM_Version_2U_C`
- Plan: `docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md`
- Update log: `docs/update_log/2026-05-15_v3k_preparation_first_sequence_execution.md`
- Evidence: `docs/evidence/v3k-preparation-first-sequence-9024e3b9.json`
- Script: `scripts/audit_v3k_preparation_first_sequence.py`
- Trigger: 사용자 `ralph` 요청 — `34f038c0` 문서를 기준으로 추천 순서대로 모두 진행

### Result

```text
preparation_lane_complete: true
actual_lane_complete: false
next_actual_gate: phase-h-h2-h3-live-dryrun-await-user-approval
```

### P1~P5 status

| 순서 | 작업 | 결과 |
| ---: | --- | --- |
| P1 | F1 cutover prep package | PASS — dry-run + guarded rollback policy, operating DB write 0건 |
| P2 | Phase F F-4 prep package | PASS — default-OFF smoke + parity delta 0.00% |
| P3 | Phase G G-3 prep package | PASS — parity + benchmark 통과 |
| P4 | F7 closure prep package | PASS — actual evidence absent 시 closure disallow |
| P5 | 준비 선행 checkpoint | PASS — P1~P4 ready, actual side effects all false |

### Actual lane remains blocked

Actual execution 순서는 변경하지 않는다.

```text
A1 Phase H H-2 live dry-run
→ A2 F1 DB cutover
→ A3 Phase F F-4 ON
→ A4 Phase G G-3 ON
→ A5 F7 closure
```

현재 A1은 사용자 phrase, `V3K_PHASE_H_USER_ACK=1`, GUI Kiwoom login, 24h monitoring evidence 전에는 실행하지 않는다.

### Verification

- `python scripts/audit_v3k_preparation_first_sequence.py --stdout`
- `python scripts/audit_v3k_preparation_first_sequence.py --evidence docs/evidence/v3k-preparation-first-sequence-9024e3b9.json`
- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`

Scope guard:

- No Kiwoom runtime mutation
- No operating `_database/` write
- No live connect/login
- No USER_ACK env var 발급
- No feature flag default-ON 변경
- No mission complete commit
- No direct broker dependency 추가

Directive: preparation lane은 완료되었다. 다음 작업은 A1 Phase H H-2 live dry-run actual이며, 사용자 명시 approval phrase + `V3K_PHASE_H_USER_ACK=1` + GUI Kiwoom login + 24h monitoring evidence 없이는 F1 actual cutover 또는 이후 actual gate로 진행하지 않는다.

---

## V3K-FEATURE-TO-PAGE-MAPPING

Records: V3 신기능 8개 기능군과 잔여 5 페이지(Step 2~6) 사이의 1:N 매핑을 단일 지도로 정본화한다. prior `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md` §4.1과 `docs/update_log/2026-05-15_v3k_midpoint_checkpoint_cd6f5bd_to_4dbac74f.md` §5.1을 합쳐 단일 표로 제공.

Decision: 본 plan은 prior 두 문서를 supersede하지 않고 보완 공존한다. F6 산식 표기(`350/700 = 50.0%`)는 mid-checkpoint와 동일하게 유지한다. 페이지별 활성화되는 V3 기능과 sidecar source-of-truth, monitoring 기간, 사전 조건이 단일 지도에 명시된다.

Plan: `docs/plans/2026-05-20_v3k_feature_to_page_mapping_overview_plan.md`

Verification:

- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`

Effect: 잔여 5 페이지의 후속 plan들은 본 지도 §4.x를 baseline으로 인용한다. 부분반영 항목(#3 GUI setting persistence, #4 formula globals)은 페이지 3/4 sidecar 작업으로 자동 흡수된다.

Scope guard:

- No code change
- No operating `_database/` write
- No `_database_v3k_shadow/` 변경
- No `_v3k_sidecar/` 토글 변경
- No live connect/login
- No USER_ACK env var 발급
- No feature flag default-ON 변경

Directive: 본 지도가 잔여 페이지 작업의 단일 baseline이다. 후속 page plan은 본 지도 §4.x 셀을 인용한다.

---

## V3K-PHASE-H-H2-RUNNER-PREP

Records: `phase_h_live_kiwoom_dryrun_plan.md` §C T05/T06 task의 P-lane 실행 plan을 정본화한다. T05 runner(`scripts/run_v3k_phase_h_dryrun.py`) + T06 health smoke(`scripts/smoke_v3k_phase_h_post_health.py`) 코드 작성에 대한 분해, 가드 체인(G1~G5), 검증 시나리오, scope_guard를 단일 plan에 고정.

Decision: T05 runner는 G1~G5 가드 체인(--ack 인자, --account-mode read-only, `V3K_PHASE_H_USER_ACK=1` env, T03 sentinel, host_identifier)을 통과해야만 실제 connect를 시도한다. 본 P-lane plan commit은 G3 가드에서 abort하도록 default-OFF 유지. A-lane(actual execution) 진입은 본 plan 종료 후 별도 사용자 phrase + USER_ACK 발급 시점.

Plan: `docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md`

Verification:

- `python -m py_compile scripts/run_v3k_phase_h_dryrun.py`
- `python -m py_compile scripts/smoke_v3k_phase_h_post_health.py`
- G1~G5 abort 시나리오 5건 PASS
- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check`

Effect: 본 P-lane plan 종료 후 사용자 phrase + `V3K_PHASE_H_USER_ACK=1` 발급 시점에 A-lane 진입 가능. A1(Phase H H-2 actual)이 통과하면 24h monitoring 후 Step 3(F1 cutover)으로 진입.

Scope guard:

- No Kiwoom runtime mutation
- No operating `_database/` write
- No live connect/login (G3 가드에서 abort)
- No USER_ACK env var 발급
- No feature flag default-ON 변경
- No LS direct dependency
- No `_v3k_sidecar/` 토글 변경

Directive: T05/T06 작성 후 G1~G5 가드 체인 abort 5건이 모두 PASS인 시점까지 P-lane이다. G3 가드를 통과시키는 환경 설정(USER_ACK env)을 발급하는 순간 A-lane 진입이므로, 본 P-lane plan commit 단계에서는 USER_ACK env를 절대 발급하지 않는다.

---

## V3K-PHASE-H-H2-RUNNER-PREP-EXECUTION

Records: `docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md` §3 Task 분해의 실제 실행 결과를 정본화한다. T05 runner `scripts/run_v3k_phase_h_dryrun.py` + T06 health smoke `scripts/smoke_v3k_phase_h_post_health.py` 신설, G1~G5 가드 체인 abort 시나리오 4건 + dry-mock 정상 흐름 1건 모두 PASS, T06 smoke baseline + mock archive 검증 모두 PASS, 회귀 audit suite(gate4 + verify_1a + verify_nonrelease_sync + git diff --check) 모두 PASS.

Decision: host_identifier 산정 방식은 prior T04b / preparation-first / step2-to-step6 evidence 규칙(`sha256(platform.node().encode()).hexdigest()[:8]`)을 그대로 따라 `9024e3b9`로 정합 유지한다. 본 P-lane execution은 ad-hoc dry-mock archive(`.omx/reports/v3k-phase-h-dryrun-<utc>.json`)를 산출하지만 `.omx/` 디렉토리는 git exclude이므로 commit 외이고, 정본 evidence는 `docs/evidence/v3k-phase-h-h2-runner-prep-9024e3b9.json` 한 건으로 보존한다.

Plan: `docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md`

Evidence: `docs/evidence/v3k-phase-h-h2-runner-prep-9024e3b9.json`

Verification:

- `python -m py_compile scripts/run_v3k_phase_h_dryrun.py`: PASS
- `python -m py_compile scripts/smoke_v3k_phase_h_post_health.py`: PASS
- G1 abort (no --ack): exit 1, "Refused: --ack required"
- G2 abort (wrong --account-mode full): exit 1, "Refused: --account-mode must be read-only"
- G3 abort (no USER_ACK env): exit 1, "Refused: V3K_PHASE_H_USER_ACK env var not set"
- G5 abort (host mismatch --expected-host deadbeef): exit 1, "Refused: host_identifier mismatch"
- dry-mock all-guards-pass: exit 0, mock archive written
- T06 smoke baseline (no archive): exit 0, graceful SKIP
- T06 smoke against mock archive (--no-runtime-check): exit 0, PASS
- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`: PASS (unblocked, schema v2)
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`: PASS
- `python scripts/verify_nonrelease_sync.py`: PASS
- `git diff --check`: PASS

Effect: V3K Phase H H-2 본 실행을 위한 runner + smoke 인프라가 P-lane으로 완성되었다. 다음 A-lane 진입(Phase H H-2 actual)은 사용자 명시 phrase + `V3K_PHASE_H_USER_ACK=1` 환경변수 발급 + 본 PC KHOPENAPI GUI 활성 + 24h monitoring 시작 시점에 가능하다. A-lane commit에서는 `--dry-mock` 인자를 제거하고 실제 OCX connect를 시도한다.

Scope guard (P-lane execution 시점):

- Kiwoom runtime mutation: 0건 (trade/, utility/, Kiwoom_OpenAPI/ 무변경)
- operating `_database/` write: 0건
- `_database_v3k_shadow/` 변경: 0건
- `_v3k_sidecar/` 토글 변경: 0건
- live connect/login: 0건 (G3 가드는 inline env로만 잠깐 통과시켜 mock 산출, child process 종료 시 자동 해제)
- USER_ACK env var durable 발급: 0건 (mock 검증용 inline env만 사용)
- feature flag default-ON 전환: 0건
- LS direct dependency 추가: 0건

Directive: 본 EXECUTION commit으로 P-T05/P-T06 task 종결. A-lane 진입은 별도 사용자 승인 commit으로 분리한다. A-lane commit 전까지 `--dry-mock` 인자 제거 또는 실제 OCX connect 호출을 절대 발생시키지 않는다.

---

## V3K-PHASE-H-H2-LOGIN-ENV-RECOVERY

Records: V3K 페이지 1(Phase H H-2 A-lane) 진입 직전 stom.bat 키움 로그인이 2026-05-20부터 30시간 동안 실패했고, 진짜 원인은 KOA Studio 모의투자 모드였음을 정본화한다. 사용자가 KOA Studio에서 모의투자 해제 + 업데이트 + 실거래 로그인 끝까지 진행한 후 2026-05-22 06:48:50 stom.bat "OpenAPI 로그인 완료" 확인.

Decision: STOM 정규 운영(`STOM_Version_2` lane 포함)은 키움 실거래 모드를 가정하며, KOA Studio가 모의투자 모드일 때 `manuallogin.py`의 GetDlgItem(0x3E8/0x3E9/0x3EA)이 실거래 dialog control ID와 매핑되지 않아 invalid handle을 반환하는 것으로 추정된다. 향후 stom.bat 로그인 실패 시 가장 먼저 KOA Studio 모의투자 토글을 점검하는 것을 운영 매뉴얼 amend 의무로 등록한다. 본 환경 복구는 STOM/V3K 코드 변경 0건이며 V3K 보존 invariant L1~L9 + LH1~LH5 모두 보존된다.

Plan: 없음 (외부 SDK 환경 복구이며 별도 plan 신설 없이 본 update_log 보고서로 정본화)

Evidence:

- `docs/update_log/2026-05-22_v3k_phase_h_h2_login_env_recovery.md` (timeline + 가설 검증 + 진짜 원인 + 해결 절차 + 학습 포인트)
- 사용자 cmd 정상 로그인 로그 (2026-05-22 06:46:34 ~ 06:48:54) 본 보고서 §2.1에 인용 보존

Verification:

- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`: PASS (unblocked, schema v2)
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`: PASS (trade/, utility/, Kiwoom_OpenAPI/ 무변경)
- `python scripts/verify_nonrelease_sync.py`: PASS
- `git diff --check`: PASS
- stom.bat 정상 로그인 evidence ("업데이트 확인 완료" → "OpenAPI 로그인 완료" → "실시간 등록 완료"): 본 보고서 §2.1

Effect: V3K Phase H H-2 A-lane 진입 차단 요인이 해소되었다. A-lane 진입 조건 4건 중 3건이 만족된 상태이며, 잔여 1건은 A-lane 실행 시점에 `V3K_PHASE_H_USER_ACK=1` env 발급으로 만족된다. 본 보고서 직후 사용자가 32-bit Python으로 `scripts/run_v3k_phase_h_dryrun.py --ack --account-mode read-only` 실행 가능 상태.

Scope guard:

- Kiwoom runtime mutation: 0건 (trade/, utility/, Kiwoom_OpenAPI/, receiver/ 무변경)
- LS direct dependency: 0건
- operating `_database/` write: 0건
- `_database_v3k_shadow/` 변경: 0건
- `_v3k_sidecar/` 토글 변경: 0건
- V3K USER_ACK env var durable 발급: 0건
- V3K feature flag default-ON 전환: 0건
- live connect/login: 정규 STOM 운영 경로로만 발생 (V3K A-lane 측은 0건)

Directive: 향후 stom.bat 로그인 첫 실패 시 다음 우선순위로 진단한다. (1) KOA Studio 모의투자 모드 토글 확인 → (2) 키움 OpenAPI 환경 점검(`opstarter` 실행) → (3) OCX 등록(`regsvr32`) → (4) 재설치. 본 trail은 V3K closeout audit(F7) 검출 대상에서 제외(외부 SDK 환경 복구로 V3K 미션과 직결되지 않음). V3K Phase H H-2 A-lane 본 실행 evidence는 별도 `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json`으로 산출 예정.

---

## V3K-PHASE-H-H2-ACTUAL

Records: V3K 페이지 1(Step 2, Phase H H-2 live dry-run)의 A-lane execution을 정본화한다. 2026-05-22 03:02 UTC에 `scripts/run_v3k_phase_h_dryrun.py --ack --account-mode read-only`를 32-bit Python(`C:\Python\32\Python3119\python32.EXE`)으로 실행하였고, `V3K_PHASE_H_USER_ACK=1` env + 사용자 명시 phrase `I approve phase-h-h2-await-user-approval only` 발급 + `V3K_KHOPENAPI_DLL=C:/OpenAPI/khopenapi.ocx` env workaround 적용 하에 키움 OCX OnEventConnect 이벤트가 정상 발생, `V3KKiwoomDryrunHook.on_login` 호출, Phase H contract-only diagnostic 1회 실행, 30초 timeout 후 `CommTerminate()` 정상 disconnect로 종료되었다.

Decision:

- canonical phrase: `I approve phase-h-h2-await-user-approval only` (2026-05-20 사용자 발급, page 080/081 패턴 정합)
- USER_ACK env: Claude session inline env로 발급(child process scope, durable env 외)
- 키움 로그인 인증: 사용자의 prior KOA Studio + stom.bat 로그인 세션의 자동 인증 cookie를 OCX가 재사용했고, A-lane runner는 OnEventConnect 시 account_info와 함께 hook callback 호출만 받음. 본 A-lane execution 시점에 새 ID/PW 입력 prompt는 발생하지 않음.
- env workaround `V3K_KHOPENAPI_DLL=C:/OpenAPI/khopenapi.ocx`: `V3KKiwoomDryrunHook.DEFAULT_KHOPENAPI_DLL_CANDIDATES`가 `.dll` 확장자만 enumerate하나 키움은 `khopenapi.ocx`로 배포. hook은 `ENV_KHOPENAPI_DLL` env로 임의 경로 추가를 지원하므로 본 env 사용으로 정합 회피. 향후 hook 코드 amend(`.ocx` 디폴트 후보 추가)는 별도 P-lane work item으로 분리.

Plan: `docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md`

Evidence: `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json`

Source archive: `.omx/reports/v3k-phase-h-dryrun-20260522T025930Z.json` (untracked, `.omx/` exclude)

Runner result:

- `connect_attempted`: True
- `connect_result_code`: 0
- `login_succeeded`: True
- `account_info_seen`: True
- `diagnostic_steps[0].step`: phase_h_diagnostic / `result`: ok
- `elapsed_sec`: 30.982
- `disconnect_clean`: True
- `order_api_calls`: 0 (LH1 보존)
- `account_api_calls`: 0 (LH1 보존)
- `sentinel.primary_kind`: active_x_progid, `primary_exists`: True, `corroboration_count`: 2

Verification:

- runner stdout: `[OK] live dry-run archive: .omx\reports\v3k-phase-h-dryrun-20260522T025930Z.json`
- `python scripts/smoke_v3k_phase_h_post_health.py`: `[PASS] Phase H H-2 post-health smoke clean`
- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`: PASS (unblocked, schema v2)
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`: PASS (trade/, utility/, Kiwoom_OpenAPI/ 무변경)
- `python scripts/verify_nonrelease_sync.py`: PASS
- `git diff --check`: PASS

F6 progress update:

- 항목 #5 live Kiwoom dry-run (Gate4): S2 (50%) → **S4 (100%)** (+50%p)
- 전체 실행 진척률: `350/700 = 50.0%` → **`375/700 = 53.6%`** (+3.6%p)
- Plan coverage: 100% 유지

Monitoring:

- baseline UTC: 2026-05-22T03:02:05Z
- window: 24h
- window end UTC: 2026-05-23T03:02:05Z (KST 2026-05-23 12:02)
- 24h 동안 키움 OCX runtime 안정성 + LH1 invariant 보존 + `_database/` 무변경 모니터링 의무

Effect: V3K 잔여 5단계(페이지 1~5) 중 페이지 1(Step 2, Phase H H-2)이 closure되었다. F6 진척률 53.6%. 다음 actual gate는 A2(F1 DB cutover, 페이지 2)이며 본 A-lane closure + 24h monitoring evidence 통과 후에만 진입 가능. F1 cutover는 CRITICAL risk이므로 `--deliberate ralplan` + `V3K_CUTOVER_USER_ACK=1` + transaction lock window 추가 trigger 필요.

Scope guard:

- Kiwoom runtime mutation: 0건 (trade/, utility/, Kiwoom_OpenAPI/, receiver/ 무변경)
- LS direct dependency: 0건
- operating `_database/` write: 0건
- `_database_v3k_shadow/` 변경: 0건
- `_v3k_sidecar/` 토글 변경: 0건
- order API 호출: 0건 (LH1)
- account API 호출: 0건 (LH1)
- V3K USER_ACK env durable 발급: 0건 (Claude session inline scope만)
- V3K feature flag default-ON 전환: 0건

Preservation invariant check (L1-L9, LH1-LH5): 전부 보존 (L1/L7/L9 + LH1/LH2/LH3/LH4/LH5)

Directive: 본 A-lane closure 후 페이지 2(Step 3, F1 DB cutover) 진입은 24h monitoring window(2026-05-23T03:02 UTC 이후) + `V3K_CUTOVER_USER_ACK=1` durable env + `--deliberate ralplan` 합의 + transaction lock window evidence 4건이 모두 충족된 시점에만 가능하다. 본 trail에서 hook 코드의 `.ocx` 디폴트 누락 followup은 별도 P-lane work item으로 분리(`V3K-PHASE-H-HOOK-OCX-DEFAULT-AMEND`).

---

## V3K-PHASE-H-ENABLE

Records: V3K Phase H sub-phase H-2 live dry-run hook이 본 PC KHOPENAPI 호환 환경에서 정상 가동되었음을 V3K-PHASE-H-ENABLE registry로 등록한다. Phase F/G의 sidecar toggle pattern(`V3K_PHASE_F_ANALYZER_STRATEGY`, `V3K_PHASE_G_MICROSTRUCTURE_ENGINE`)과 달리 Phase H는 sidecar toggle source-of-truth가 아니라 archive 기반 evidence trail이 source-of-truth다(page 082 Phase H gate4 plan 정합).

Decision: Phase H ENABLE 등록은 본 A-lane evidence(`docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json`)의 `login_succeeded=true` + `diagnostic_steps[0].result=ok` + scope_guard 통과 + smoke PASS를 기준으로 한다. 추가 sidecar toggle은 도입하지 않는다. Phase H 본 ENABLE은 1회성 evidence이며 24h monitoring 종료 후 mature 판정.

Plan: `docs/plans/2026-05-20_v3k_phase_h_h2_runner_prep_lane_plan.md` §8 A-lane entry

Evidence: `docs/evidence/v3k-phase-h-h2-actual-9024e3b9.json`

Verification: V3K-PHASE-H-H2-ACTUAL 섹션 Verification 항목과 동일

Effect: V3K Phase H가 본 PC KHOPENAPI 환경에서 default-OFF → 1회성 dry-run ON → 자동 disconnect 흐름으로 검증 완료. 향후 Phase H H-3 sub-phase(7일 모니터링 audit + feature flag 이중 gate)는 본 A-lane evidence를 baseline으로 인용한다.

Scope guard: V3K-PHASE-H-H2-ACTUAL 섹션과 동일

Directive: Phase H ENABLE 상태는 본 evidence가 baseline이고, 향후 Phase H 관련 모든 audit/closure는 본 commit hash를 참조한다.

---

## V3K-F1-DELIBERATE-RALPLAN-PLANNER-V1

Records: V3K 페이지 2(Step 3, F1 DB cutover, CRITICAL risk)의 `--deliberate ralplan` 합의 plan Planner v1을 정본화한다. 본체 plan(`docs/plans/2026-05-12_v3k_db_cutover_plan.md`)과 approval prep(`docs/plans/2026-05-13_v3k_page_053_f1_actual_db_cutover_approval_prep_plan.md`)을 supersede하지 않고 합의 layer를 얹어 Pre-mortem 12건 + 확장 테스트 4축(unit/integration/e2e/observability) + Rollback drill 의무를 정본화한다.

Decision:

- ralplan iteration 1 (Planner v1)을 본 commit으로 종결. iteration 2(Architect review) + iteration 3(Critic review) + iteration 4(Planner v2) + iteration 5(APPROVE 합의)는 별도 후속 commit으로 분리한다.
- 24h monitoring window(2026-05-22T03:02 UTC ~ 2026-05-23T03:02 UTC, V3K-PHASE-H-H2-ACTUAL 섹션 baseline) 동안 iteration 2-5를 병렬로 진행 가능하다.
- A2 trigger 4건은 본 plan §9에서 확정: (1) A1 24h monitoring 종료 + (2) `V3K_CUTOVER_USER_ACK=1` durable env + (3) ralplan 합의 종결 + (4) transaction lock window 진입 시각 명시.
- transaction lock window는 본 plan §3.3에서 명시: 한국 정규장 외 + 주말 + 키움 정기점검 회피, 권장은 토요일 자정~일요일 자정.
- 5중 guard(branch/USER_ACK/--backup-first/--backup-dir/--allow-operating-target)는 `scripts/cutover_v3k_shadow_to_database.py:require_apply_guards`로 이미 구현되어 있으며 본 합의 plan은 이를 인용한다.

Plan: `docs/plans/2026-05-22_v3k_f1_db_cutover_deliberate_ralplan_plan.md`

Verification:

- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`: PASS (unblocked, schema v2)
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`: PASS
- `python scripts/verify_nonrelease_sync.py`: PASS
- `git diff --check`: PASS
- `git status --short -- _database _database_v3k_shadow _log backup *.db .omx/reports _v3k_sidecar`: 무변경

Effect: F1 cutover의 `--deliberate ralplan` 의무 산출 3건(Pre-mortem 12건 / 확장 테스트 4축 / Rollback drill)이 baseline으로 정본화되었다. 24h monitoring window 동안 ralplan iteration 2-5를 진행해 합의 종결 후 A2(F1 cutover actual) 진입 가능 상태로 전이한다. F6 산식 진척률 영향 없음(53.6% 유지).

Scope guard:

- Kiwoom runtime mutation: 0건
- LS direct dependency: 0건
- operating `_database/` write: 0건
- `_database_v3k_shadow/` 변경: 0건
- `_v3k_sidecar/` 토글 변경: 0건
- order/account API 호출: 0건
- V3K USER_ACK env durable 발급: 0건
- V3K_CUTOVER_USER_ACK env 발급: 0건
- V3K feature flag default-ON 전환: 0건
- cutover script `--apply` 실행: 0건

Preservation invariant: L1/L7/L9 + LH1-LH5 + LC1/LC2/LC3 모두 보존 (cutover 미실행)

Directive: 24h monitoring window 종료 + ralplan iteration 5(APPROVE 합의) 종결 + USER_ACK env 발급 + transaction lock window 진입 시각 명시 4건이 모두 충족된 시점에만 A2 진입 가능. Architect review(iteration 2)와 Critic review(iteration 3)는 별도 commit으로 분리하며, 각 review가 본 Planner v1 §4(Architect baseline) / §5(Critic baseline)을 amend 또는 확장한다. iteration 4(Planner v2)는 Architect/Critic 피드백을 흡수해 plan을 amend하고 iteration 5에서 APPROVE 합의를 등록한다. cutover script `--apply` 실행은 iteration 5 합의 + A2 trigger 4건 모두 충족 시점에만 가능하다.

---

## V3K-MIDCOURSE-REVIEW-2026-05-22

Records: V3K 페이지 1(`4fd48ad2`) A-lane closure + F1 ralplan Planner v1(`6e8e23d0`) 직후 사용자가 진행 순서를 재정렬하기로 결정한 사실을 정본화한다. V3K mission(V3 8개 기능군을 2U_C에 모두 반영)은 변경하지 않고, 진행 순서만 운영 트랙(#1 cutover + 페이지 2~5 actual) 보류 + 백테스트 트랙(#2 production learning DB read + #4 formula globals + #6/#7 default-OFF parity) + CLI 트랙(2026-03-24 plan Phase 1~3) 우선 진입으로 재정렬한다.

Decision:

- V3K 항목 #1 (shadow DB + cutover) 보류. 본체 plan + ralplan Planner v1 + scripts 모두 자산 보존.
- V3K 페이지 2~5 actual 보류. F1 ralplan iteration 2-5 미진행 상태 유지.
- V3K 항목 #2, #4, #6, #7의 default-OFF / read-only 측면 우선 진행 가능.
- CLI 확장 plan(2026-03-24)의 Phase 1~3 우선 진행 가능 (V3K LH9와 호환, 기존 동작 보존 + 신규 추가만).
- V3K 항목 #3 (GUI setting persistence sidecar)은 보조 트랙으로 병행 가능.
- mission 무변경: "단계적 cutover"의 *단계 순서*는 mission에 명시되지 않으므로 순서 재정렬은 mission 위반이 아님.

Plan: `docs/update_log/2026-05-22_v3k_midcourse_review_backtest_cli_prioritization.md`

Verification:

- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`: PASS (unblocked, schema v2)
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`: PASS
- `python scripts/verify_nonrelease_sync.py`: PASS
- `git diff --check`: PASS
- 인용 plan/update_log 파일 cross-ref 정합 확인 완료

Effect: 트랙 D(운영) 자산은 보존된 채 보류되고 트랙 A(V3K 백테스트 강화) + 트랙 B(CLI 확장) + 트랙 C(sidecar)가 active로 전이된다. F6 산식 진척률은 변동 없음(53.6% 유지). 동반 master plan(`docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md`)에 4개 트랙별 우선순위 + 의존성 + milestone 정본화.

Scope guard:

- Kiwoom runtime mutation: 0건
- LS direct dependency: 0건
- operating `_database/` write: 0건 (트랙 D 보류)
- `_database_v3k_shadow/` 변경: 0건
- `_v3k_sidecar/` 토글 ON 발급: 0건
- order/account API 호출: 0건
- V3K USER_ACK env durable 발급: 0건
- V3K feature flag default-ON 전환: 0건
- cutover script `--apply` 실행: 0건

Preservation invariant: L1/L7/L9 + LH1-LH5 + LC1/LC2/LC3 모두 보존

Directive: 본 검토는 V3K mission을 변경하지 않는다. 트랙 D 자산은 사용자가 명시적으로 재개 의사를 표시하는 시점에 본 commit 인용으로 깨워서 이어간다.

---

## V3K-BACKTEST-CLI-PRIORITIZATION-MASTER-PLAN

Records: V3K 미션을 유지하면서 진행 순서를 재정렬한 사용자 결정(`V3K-MIDCOURSE-REVIEW-2026-05-22` 섹션)에 따른 전체 작업 계획 master를 정본화한다. 4개 트랙(A V3K 백테스트 강화 / B CLI 확장 / C Sidecar / D 운영 보류) 각각의 우선순위 + 의존성 + milestone + 검증 기준 + 보류 트랙 재개 조건을 단일 plan에 정본화한다.

Decision:

- 트랙 A (V3K 백테스트 강화): V3K #2 (production learning DB read 75%) + #4 (formula globals 50%) + #6 (Phase F default-OFF parity 25%) + #7 (Phase G default-OFF parity 25%)을 active로 전이.
- 트랙 B (CLI 확장): 2026-03-24 plan의 Phase 1 (라이브러리 5개 노출) + Phase 2 (출력 표준화) + Phase 3 (설정관리/리포트 신규)을 active로 전이.
- 트랙 C (Sidecar): V3K #3 (GUI setting persistence 75%) 보조 트랙으로 active.
- 트랙 D (운영): V3K #1 (shadow DB + cutover) + 페이지 2~5 actual 보류, 4건 재개 조건 명시(§7).
- 진행 순서: M1 진단 phase → M2 첫 cycle → M3 두 번째 cycle → M4 세 번째 cycle → M5 트랙 A closure → M6 사용자 결정 시점에 트랙 D 재개 여부 결정.
- 즉시 시작 가능한 4건 진단 작업: CLI Phase 진척 / V3K-IMPL-3 진척 / 유닛 테스트 720건 실패 / sidecar 메커니즘 (각각 독립 read-only).

Plan: `docs/plans/2026-05-22_v3k_backtest_cli_prioritization_master_plan.md`

Verification:

- `python scripts/audit_v3k_phase_h_gate4_environment_status.py`: PASS
- `python scripts/audit_v3k_verify_1a.py --base 9423735e`: PASS
- `python scripts/verify_nonrelease_sync.py`: PASS
- `git diff --check`: PASS
- master plan cross-ref 8건 plan + 2건 update_log 모두 파일 존재 확인 완료

Effect: M1 진단 phase 진입 가능 상태. 진단 4건 commit 산출 후 M2 첫 cycle(CLI Phase 1 첫 서브커맨드 또는 V3K-IMPL-3 baseline) 진입 시점에 사용자 작업 선택. F6 진척률은 트랙 A 항목별 +25%p 가능(실측치는 cycle별 확정).

Scope guard:

- Kiwoom runtime mutation: 0건
- LS direct dependency: 0건
- operating `_database/` write: 0건 (트랙 D 보류)
- `_database_v3k_shadow/` 구조 변경: 0건 (read-only 사용만)
- `_v3k_sidecar/` 토글 ON 발급: 0건 (트랙 C는 메커니즘만, ON 활성화 안 함)
- order/account API 호출: 0건
- V3K USER_ACK env durable 발급: 0건
- V3K feature flag default-ON 전환: 0건
- cutover script `--apply` 실행: 0건 (트랙 D 보류)

Preservation invariant: L1/L7/L9 + LH1-LH5 + LC1/LC2/LC3 모두 보존

Directive: 본 master plan은 M1 진단 phase의 baseline이다. M1 진단 4건 commit이 종결된 시점에 M2 첫 작업이 사용자 결정으로 선정된다. 트랙 D 자산은 §7의 4건 재개 조건 충족 시점까지 동결 유지.
