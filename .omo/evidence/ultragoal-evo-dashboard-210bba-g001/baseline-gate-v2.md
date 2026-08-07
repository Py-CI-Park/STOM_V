# G001 Baseline Gate — 210bba Execution Worktree v2

Status: **PASS, with tracked baseline protected reference classified**

## Baseline

| Item | Result |
|---|---|
| Execution worktree | `C:/System_Trading/STOM/STOM_V.wt-evo-governance` |
| Branch | `feature/evo-dashboard-condition-discovery-governance` |
| Expected HEAD | `210bba854d03a8680ffebfb94f2544c52e81858b` |
| Actual HEAD | `210bba854d03a8680ffebfb94f2544c52e81858b` |
| Git status | clean |
| `.gjc` | absent from execution worktree |
| `_database`, `_database_v3k_shadow`, `_log`, `backup`, `backtest/graph` | clean/absent/no tracked files |
| `ai_strategy_loop/state` | tracked `.gitignore` placeholder only |
| `test-results` | tracked `.last-run.json` placeholder only |
| `.omx/reports` | tracked baseline report `.omx/reports/v3k-shadow-manifest.json`; clean, not modified, not source input |

## Protected path classification

`210bba` includes `.omx/reports/v3k-shadow-manifest.json` as a tracked baseline reference artifact. It was not created or modified by this run, `git status --short -- .omx/reports ...` is clean, and it is explicitly classified as **not a source input** for this condition-discovery dashboard work. No live/export/operating DB/V3K/KHOPENAPI work was performed.

## 210bba seams verified

| Seam | Evidence |
|---|---|
| Additive state seam | `LoopState.page_data` in `ai_strategy_loop/controller/contract.py` |
| Generation telemetry fields | `telemetry_events` and `telemetry_contract` in `GenerationInfo` |
| State publication | `to_loop_state(..., page_data=...)` in `ai_strategy_loop/controller/state.py` |
| Closed telemetry contract | `ai_strategy_loop/controller/telemetry.py` |
| `/status` telemetry attachment | `_current_state_payload` uses `attach_telemetry_to_status` in `dashboard/app.py` |
| Evolution UI routes | `/ui/evolution` and subtab aliases in `dashboard/app.py` |
| Frontend seams | `dashboard-pages.jsx`, `research-index.jsx` |
| Telemetry regression tests | `tests/unit/dashboard/test_dashboard_telemetry.py` |

## Verification

| Command | Result |
|---|---|
| `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py -q` | `5 passed in 11.33s` |

Raw command artifact: `artifact://363`

## Decision

G001 passes after explicitly classifying the tracked `.omx/reports` baseline reference. Backend contract/policy work can proceed in the clean `wt-evo-governance` worktree under the approved no-live/export/operating-DB/V3K/KHOPENAPI/Transformer constraints.
