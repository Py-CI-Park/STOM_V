# Final Verification

Status: `complete`

## Commands

| Gate | Command | Result |
|---|---|---|
| F1 plan compliance | `rg -n "2023-2025|2022/2026|final_approval|export_winner|taskkill|KHOPENAPI|V3K" .omo/evidence/ct-seed-tick-preflight-repair-20260605` | pass; hits are blocked/guard/next-command text only |
| F2 focused tests | `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_tick_seed_timeout_probe.py tests/unit/test_warm_session_window.py tests/unit/test_dashboard_engine_progress_contract.py -q` | `22 passed in 9.28s` |
| F3 runner timeout guards | `$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_runner_helpers.py::test_runner_attaches_protocol_diagnostics_on_timeout tests/unit/test_runner_helpers.py::test_runner_records_timeout_checkpoint_fields -q` | `2 passed in 0.59s` |
| F4 protected paths | `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json` | no output |
| F4 process cleanup | filtered process query for `ct_preflight`, `ai_strategy_loop.controller.loop`, `stom_backtest.py` | no output |
| F5 nonrelease | `python scripts/verify_nonrelease_sync.py` | pass |
| F5 diff | `git diff --check` | pass; line-ending warnings only |

## Final Page Progress

| Step | Status | Artifact |
|---|---|---|
| P0 Safety baseline | complete | `p0-safety-baseline.md` |
| P1 Coverage preflight | complete | `p1-window-coverage-preflight.md` |
| P2 Strategy inspect | complete | `p2-strategy-timefilter-inspect.md` |
| P3 Same-window control | complete | `p3-same-window-active-control.md` |
| P4 C_T preflight | complete | `p4-ct-bounded-preflight.md` |
| P5 Dashboard/context | complete | `p5-dashboard-ai-context-check.md` |
| P6 Decision | complete | `p6-decision-card.md` |
| P7 Next command | complete | `p7-next-command.md` |
| Final verification | complete | this file |

## Outcome

Verdict: `CT_SEED_WINDOW_BLOCKER`

The page found a fair active same-window comparison:

- `2025-01-03 09:02..09:05` has tick coverage.
- Control `Tick_B_902_905_Update_2/S` passes in that exact window.
- C_T `C_T_900_920_U2_B/S` times out/no CSV in warm mode.
- C_T also times out/no CSV in cold mode after data load.

Immediate January retry, 2023-2025 training, and 2022/2026 OOS remain blocked until a repaired C_T preflight produces CSV+metrics.

Next command:

```text
$ulw-plan C_T seed branch workload isolation plan: use .omo/evidence/ct-seed-tick-preflight-repair-20260605/p6-decision-card.md, p4-ct-bounded-preflight.md, p3-same-window-active-control.md, and p2-strategy-timefilter-inspect.md as primary evidence. Isolate which C_T buy/sell branch or condition family causes the 2025-01-03 09:02..09:05 tick timeout by using diagnostic strategy copies and bounded warm/cold preflights only, without editing official backtest engines, hard gates, protected paths, backtest_graph, final_approval/export_winner/live/V3K paths. Keep new toggles default OFF, require CSV+metrics before any January retry, and keep 2023-2025 training plus 2022/2026 OOS blocked until a repaired C_T preflight passes.
```

## Notes

- No official backtest engine or hard gate was edited.
- No `final_approval`, `export_winner`, live broker, V3K gate, January retry, 2023-2025 training, or 2022/2026 OOS run was executed.
- Runtime DB/CSV outputs from owned diagnostics are evidence only and must not be staged unless explicitly requested.
