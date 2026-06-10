# P0 Route Parity And Stale Server Evidence

## Scope
- Plan: `.omo/plans/tick-dashboard-observability-research-ux-20260604.md`
- Task: P0 - Safety snapshot, route parity, stale-server diagnosis, and evidence capture.
- Branch: `lazycodex/tick-sparse-positive-generation-improvement-20260604`
- HEAD short: `84acb6cb`
- Date: 2026-06-04 KST

## Canonical Docs Read
- `docs/AGENT_HANDOFF.md`
- `docs/update_log/2026-06-03_tick_program_complete_handoff.md`
- `docs/research/2026-06-04_condition_research_rereview_human_reference_graphs.md`

Note: console output showed Korean mojibake in PowerShell, but the docs were read from the expected files. The plan constraints remain unchanged: no protected runtime edits, no hard-gate/engine changes, no live broker/export actions.

## Baseline Tests
Command:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_prompts.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_docs.py tests/unit/test_variable_correlation.py -q
```

Result:

```text
18 passed in 13.56s
```

## Added Route Parity Test
File:

- `tests/unit/test_dashboard_route_parity.py`

Red check:

```text
1 failed, 2 passed
Failure: frontend owner for /index_compare was incorrectly assumed as index-compare.jsx.
```

Correction:

- Keep `/index_compare` in backend/OpenAPI/non-404 route probes.
- Remove it from frontend string parity because no frontend caller exists today.

Green check:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_route_parity.py -q
```

```text
3 passed in 3.12s
```

Focused P0 regression:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_prompts.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_docs.py tests/unit/test_variable_correlation.py -q
```

```text
21 passed in 13.21s
```

## Live 8770 Diagnostic
HTTP probe:

```text
200 http://127.0.0.1:8770/health
200 http://127.0.0.1:8770/openapi.json
404 http://127.0.0.1:8770/strategy_diff?run_id=tick_oosrob_p5_train_2023_2025_20260604&gen_no=1
404 http://127.0.0.1:8770/ai_context_pack?run_id=tick_oosrob_p5_train_2023_2025_20260604
404 http://127.0.0.1:8770/research_docs
404 http://127.0.0.1:8770/variable_correlation
```

OpenAPI route presence on 8770:

```text
/strategy_diff: False
/prompts: False
/ai_context_pack: False
/research_docs: False
/research_doc: False
/index_compare: False
/variable_correlation: False
```

Process ownership probe:

```text
LocalPort     : 8770
OwningProcess : 0
ProcessName   : System Idle Process
CommandLine   :
```

Conclusion: the live `8770` surface is stale or wrong-process relative to the current source app. Ownership was not proven, so no restart or kill was attempted.

## Fresh Owned Server QA
Command:

```powershell
python -m ai_strategy_loop --host 127.0.0.1 --port 8791
```

Owned server PID from uvicorn log:

```text
Started server process [17012]
```

HTTP probe:

```text
200 http://127.0.0.1:8791/health
200 http://127.0.0.1:8791/openapi.json
200 http://127.0.0.1:8791/strategy_diff?run_id=tick_oosrob_p5_train_2023_2025_20260604&gen_no=1
200 http://127.0.0.1:8791/prompts?run_id=tick_oosrob_p5_train_2023_2025_20260604&gen_no=1
200 http://127.0.0.1:8791/ai_context_pack?run_id=tick_oosrob_p5_train_2023_2025_20260604
200 http://127.0.0.1:8791/research_docs
200 http://127.0.0.1:8791/research_doc?id=docs/update_log/2026-06-03_tick_program_complete_handoff.md
200 http://127.0.0.1:8791/index_compare?run_id=tick_oosrob_p5_train_2023_2025_20260604
200 http://127.0.0.1:8791/variable_correlation?run_id=tick_oosrob_p5_train_2023_2025_20260604
200 http://127.0.0.1:8791/hall_of_fame
200 http://127.0.0.1:8791/reference_screenshots
```

Cleanup:

```text
Ctrl+C sent to owned exec session.
Uvicorn logged shutdown, application shutdown complete, and finished server process [17012].
Get-NetTCPConnection -LocalPort 8791 returned no listener.
```

## Protected Path Status
Command:

```powershell
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

Result:

```text
<empty>
```

## P0 Verdict
P0 is complete.

- Current source app route parity is locked by `tests/unit/test_dashboard_route_parity.py`.
- Fresh owned dashboard server exposes all planned read-only routes with HTTP 200.
- Current `8770` remains stale/wrong-process and should not be killed without proven ownership.
- No protected runtime path was touched.

Next task: P1 backtest progress and engine state contract.
