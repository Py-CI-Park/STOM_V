# P3 Research Analytics And Human Reference Evidence

Date: 2026-06-04 KST
Session: codex:tick-dashboard-observability-research-ux-20260604

## Scope

P3 strengthened research-only analysis surfaces for condition development.

Implemented:

- `ai_strategy_loop/fitness/correlation_profile.py`
  - range summaries for buy-time `B_*` variables
  - histogram bins
  - win/loss range contrast
  - time, market-cap, and year segment summaries
  - row-limit/truncation metadata
  - pairwise interaction candidates labelled with `research_score`
  - recency-weighted research lens for 2023/2024/2025 only
- `ai_strategy_loop/fitness/correlation.py`
  - merged the profile into the existing `/variable_correlation` payload
  - applies deterministic row limiting before correlation/profile computation
- `ai_strategy_loop/dashboard/frontend/research-lab.jsx`
  - displays `range_summaries`, histograms, segment summaries, interaction candidates, and recency research labels

Not implemented:

- No generation behavior change.
- No selector, hard gate, score, OOS, export, or backtest engine change.
- No image OCR pipeline yet. Human screenshots remain reference-only and low-confidence unless backed by structured metrics.

## Red Tests

- `python -m pytest tests/unit/test_variable_correlation.py -q`
  - `2 failed, 6 passed`
  - Missing `source`, `range_summaries`, segment metadata, interaction candidates, recency research, and `row_limit`.
- `python -m pytest tests/unit/test_dashboard_research_lab_frontend.py -q`
  - `1 failed, 4 passed`
  - Research Lab did not consume the new analysis fields.

## Green Tests

- `python -m pytest tests/unit/test_variable_correlation.py -q`
  - `8 passed in 5.60s`
- `python -m pytest tests/unit/test_dashboard_research_lab_frontend.py -q`
  - `5 passed in 0.50s`
- Focused P3 suite:
  - `python -m pytest tests/unit/test_variable_correlation.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_hall_of_fame.py -q`
  - `49 passed in 7.96s`

## Human Reference Corridor

Structured source:

- `ai_strategy_loop/dashboard/reference_strategies.json`
- Source report: `docs/reference/STOM_Good_Results/backtest_analysis_report_v2.md`
- Image files: `docs/reference/STOM_Good_Results/STOM_Good_Result_Screenshot (*.png)`

Structured 19-strategy summary:

- `total_return_pct`: min `129.34`, max `254.32`, mean `197.97`, median `202.46`
- `annual_return_pct`: min `134.17`, max `262.05`, mean `203.16`, median `204.92`
- `mdd_pct`: min `1.90`, max `6.75`, mean `4.16`, median `3.80`
- `payoff`: min `1.15`, max `1.47`, mean `1.27`, median `1.26`
- `daily_avg_trades`: min `10.6`, max `23.2`, mean `17.18`, median `16.9`
- `max_holdings`: min `6`, max `12`, mean `8.16`, median `8`
- `win_rate_pct`: min `39.32`, max `51.14`, mean `45.00`, median `44.27`
- `avg_hold_sec`: min `142.33`, max `386.69`, mean `245.81`, median `244.02`

Top structured references:

- Highest total return: `#1 254.32%`, `#8 251.31%`, `#11 250.19%`, `#17 226.05%`, `#2 222.74%`
- Highest annual return: `#17 262.05%`, `#1 255.34%`, `#6 252.55%`, `#11 252.20%`, `#8 243.20%`
- Lowest MDD: `#15 1.90%`, `#3 2.68%`, `#7 2.87%`, `#1 3.17%`, `#13 3.26%`

Interpretation:

- Use these values as research corridors, not as proof that an AI strategy is acceptable.
- A sparse strategy with max holdings near `0/1` is far outside the structured human corridor of `6..12`, so P4 must audit whether the metric or strategy behavior is wrong.
- `2023:1.0`, `2024:1.25`, `2025:1.5` recency weights are report-only; fixed OOS years `2022` and `2026` remain excluded from training/promotion decisions.

## Safety

- `git diff --check`: exit 0. Git reported CRLF normalization warnings only.
- Protected path audit:
  - `git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json`
  - no output.

## Next

Continue with P4: max-hold count and sparse-buy audit.
