# P2 Frontend Dashboard UX Repair Evidence

Date: 2026-06-04 KST
Session: codex:tick-dashboard-observability-research-ux-20260604

## Scope

P2 repaired frontend-only dashboard UX contracts that were blocking operator review:

- `StrategyInspectorTabs` no longer treats `/strategy_diff` and `/prompts` as one fatal `Promise.all` group.
- Strategy inspector now has a `Current Code` tab and AI context includes `buy_code` / `sell_code`.
- `EnginePanel` consumes P1's `latest.backtest_progress` and `latest.engine_state` contract.
- `LivePending` now names the state as `Live data pending` and explains that it is waiting for a fresh live snapshot.
- `HallOfFamePanel` can sort by `total_return_krw` and forces a horizontally scrollable wide table.

No official backtest engine math, hard gates, `backtest/graph`, protected runtime paths, approval/export routes, or live broker paths were touched.

## Red Tests

The new contracts failed before implementation:

- `python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py -q`
  - `1 failed, 4 passed`
  - Missing `diffError`, `promptsError`, partial-route failure labels, and current-code visibility contract.
- `python -m pytest tests/unit/test_dashboard_phase_mapping.py -q`
  - `2 failed, 14 passed`
  - `engine.jsx` did not consume `backtest_progress` / `engine_state`; `phase-detail.jsx` did not contain the clear pending label.
- `python -m pytest tests/unit/test_dashboard_hall_of_fame.py -q`
  - `1 failed, 32 passed`
  - Missing `total_return_krw` sort and wide-table scroll contract.

## Implementation Notes

- `ai_strategy_loop/dashboard/frontend/strategy-inspector.jsx`
  - Replaced fatal combined fetch behavior with independent `diffError` and `promptsError` handling.
  - Added `Current Code` tab showing current `buy_code` and `sell_code`.
  - Added current strategy code to copied AI context for operator/agent review.
- `ai_strategy_loop/dashboard/frontend/engine.jsx`
  - Reads `latest.backtest_progress` for percent, elapsed, ETA, units, phase, and progress source.
  - Reads `latest.engine_state` for `bt_timeframe`, engine mode, CPU count, effective engine count, active config, and recent logs.
  - Labels `gen = generation` unless `evolutionMode === "ga"`.
- `ai_strategy_loop/dashboard/frontend/phase-detail.jsx`
  - Clarified live-empty state as `Live data pending`.
- `ai_strategy_loop/dashboard/frontend/chart.jsx`
  - Added `total_return_krw` sort button.
  - Added `hof-scroll` wrapper and `minWidth: 1180`.

## Green Tests

- `python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py -q`
  - `5 passed in 0.62s`
- `python -m pytest tests/unit/test_dashboard_phase_mapping.py -q`
  - `16 passed in 8.91s`
- `python -m pytest tests/unit/test_dashboard_hall_of_fame.py -q`
  - `33 passed in 3.48s`
- Combined P0/P1/P2 dashboard contract suite:
  - `python -m pytest tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_engine_progress_contract.py tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_dashboard_hall_of_fame.py tests/unit/test_dashboard_phase_mapping.py tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_prompts.py tests/unit/test_dashboard_ai_context_pack.py tests/unit/test_dashboard_research_docs.py tests/unit/test_variable_correlation.py tests/unit/test_state_contract.py tests/unit/test_process_timing.py tests/unit/test_publish_live_page_data.py -q`
  - `135 passed in 17.70s`

## Safety

- `git diff --check`: exit 0. Git reported CRLF normalization warnings only.
- Protected path audit:
  - `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`
  - no output.

## Next

Continue with P3: research analytics and human-reference artifacts.
