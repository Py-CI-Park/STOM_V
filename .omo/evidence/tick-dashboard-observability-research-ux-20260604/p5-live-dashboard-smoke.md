# P5 Fresh Dashboard Live Smoke Evidence

Date: 2026-06-04 KST
Session: codex:tick-dashboard-observability-research-ux-20260604

## Owned Server

Started a fresh dashboard server on an alternate port, without touching the existing `8770` process:

- Command: `python -m ai_strategy_loop --host 127.0.0.1 --port 8792`
- Final smoke PID: `122172`
- Shutdown: owned exec session stopped with `Ctrl+C`
- No blanket `taskkill`; no live broker, `final_approval`, or `export_winner` action.

## Route Smoke

All expected read-only routes returned HTTP 200 on the fresh source app:

| Route | Status |
|---|---:|
| `/health` | 200 |
| `/openapi.json` | 200 |
| `/strategy_diff?gen_no=0` | 200 |
| `/prompts` | 200 |
| `/ai_context_pack` | 200 |
| `/research_docs` | 200 |
| `/research_doc` | 200 |
| `/variable_correlation` | 200 |
| `/hall_of_fame` | 200 |
| `/reference_screenshots` | 200 |
| `/status` | 200 |
| `/ui/` | 200 |

OpenAPI also contained:

- `/strategy_diff`
- `/prompts`
- `/ai_context_pack`
- `/research_docs`
- `/research_doc`
- `/index_compare`
- `/variable_correlation`
- `/hall_of_fame`
- `/reference_screenshots`

## Status Payload

Fresh `/status` response exposed dashboard observability fields, even for the existing legacy current-state snapshot:

- `run_id`: `tick_oosrob_p5_train_2023_2025_20260604`
- `loop_status`: `complete`
- `current_gen/max_generations`: `10/10`
- `progress_source`: `loop_generation`
- `progress_percent`: `100.0`
- `progress_units`: `10/10`
- `progress_timeframe`: `tick`
- `engine_cpu_count`: `64`
- `engine_mode`: `warm`
- `engine_timeframe`: `tick`
- `engine_effective_count`: `32`
- `period`: `20230101~20251231`
- `buy_window`: `90000~93000`
- `recent_log_count`: `50`

## P5 Regression Fix

During live smoke, old `current_state.json` payloads were found to omit `latest.backtest_progress` and `latest.engine_state`.

Red test:

- `python -m pytest tests/unit/test_dashboard_engine_progress_contract.py::test_status_route_normalizes_legacy_current_state_observability_fields -q`
  - failed with missing `backtest_progress`.

Fix:

- `ai_strategy_loop/dashboard/app.py`
  - `/status` now normalizes readable current-state snapshots through `C.LoopState`.
  - It fills dashboard-only observability fields with `build_backtest_progress` and `build_engine_state`.
  - It does not rewrite `current_state.json`, DB rows, engine logic, hard gates, protected paths, or promotion behavior.

Green tests:

- `python -m pytest tests/unit/test_dashboard_engine_progress_contract.py::test_status_route_normalizes_legacy_current_state_observability_fields -q`
  - `1 passed`
- `python -m pytest tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_dashboard_route_parity.py -q`
  - `9 passed`

## Browser Smoke

Playwright CLI was available:

- `npx --yes playwright --version`
  - `Version 1.60.0`

First browser screenshot showed the static UI rendered but defaulted to BASE `http://127.0.0.1:8770`, so it was not sufficient as an alternate-port backend connection proof:

- `.omo/evidence/tick-dashboard-observability-research-ux-20260604/p5-dashboard-ui-8792.png`

Then Playwright storage state injected `localStorage.stom_base_url=http://127.0.0.1:8792`:

- `.omo/evidence/tick-dashboard-observability-research-ux-20260604/p5-playwright-storage-8792.json`

Connected browser artifacts:

- Screenshot: `.omo/evidence/tick-dashboard-observability-research-ux-20260604/p5-dashboard-ui-connected-8792.png`
- HAR: `.omo/evidence/tick-dashboard-observability-research-ux-20260604/p5-dashboard-ui-connected-8792.har`

HAR confirmed frontend calls to the owned `8792` backend:

- `http://127.0.0.1:8792/health`
- `http://127.0.0.1:8792/config/spec`
- `http://127.0.0.1:8792/status`
- `http://127.0.0.1:8792/runs`
- `http://127.0.0.1:8792/hall_of_fame`
- `http://127.0.0.1:8792/research_docs`
- `http://127.0.0.1:8792/research_doc`
- `http://127.0.0.1:8792/ai_context_pack`

## Safety

- Owned PID `122172` was stopped with `Ctrl+C`.
- No protected runtime path was edited intentionally.
- No official backtest engine math, hard gate, `backtest/graph`, live broker, `final_approval`, or winner export path was changed.

## Next

Continue with Final verification:

- focused dashboard/research regression suite
- `git diff --check`
- `python scripts/verify_nonrelease_sync.py`
- protected-path status audit
