# 2026-06-29 Ultragoal G003 interactive chart primitives

## Scope
G003 replaces static/dummy-feeling SVG charts in the V3 remodel frontend with data-aware interactive primitives for condition, history, lab, workbench, backtest, chart replay, and the quality/profit/equity/fitness chart set.

## Implementation evidence
- `ai_strategy_loop/dashboard/frontend/remodel/src/app.js`
  - Adds a chart registry and data-normalization path for every rendered chart.
  - Adds hover/crosshair tooltip updates with nearest datum lookup.
  - Adds keyboard focus support using `Home`, `End`, `ArrowLeft`, and `ArrowRight`.
  - Adds accessible `aria-label` and `aria-live` active-datum text so values remain available without hover.
  - Adds source/freshness labels in each datum (`reference fixture`, `backend/read-only`, or `sim read-only payload`).
  - Adds explicit empty-state rendering for missing line/bar/candle data instead of silently drawing fake geometry.
  - Extends replay candlesticks with the same hover/keyboard/value primitive.
  - Adds legend hover/focus/click highlighting with linked series dimming so multi-series charts are not static legends.
  - Adds run_id/freshness/status/malformed chart-state badges and includes the same provenance in tooltip/ARIA labels.
- `ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css`
  - Adds crosshair, tooltip, active datum, focus ring, and empty-state styling.
- `tests/unit/test_dashboard_remodel_static.py`
  - Locks the G003 primitive markers and CSS affordances.

## Browser evidence
- `artifacts/ultragoal-g003-interactive-charts/browser-transcript.json`
  - 8 V3 routes were loaded.
  - 37 interactive charts were found across condition, history, lab, workbench, audit, backtest, and chart replay.
  - Condition hover tooltip and keyboard navigation passed.
  - Chart replay candlestick hover tooltip and keyboard navigation passed.
  - Current live probe confirms legend highlight state, state badges, and run/freshness/malformed provenance on the condition page.
  - Live-mode fallback probe confirms default charts and replay candles explicitly label `STALE/FALLBACK` instead of claiming backend/sim payload ownership when fixture data drives the graph.
  - Process is marked not-applicable for chart count because G004 owns the process monitoring cockpit rebuild.
- `artifacts/ultragoal-g003-interactive-charts/image-evidence.json`
  - 8 captured route screenshots exist, are non-empty, valid-dimensioned, and non-uniform.

## Commands run
```powershell
node --check ai_strategy_loop/dashboard/frontend/remodel/src/app.js
pytest tests/unit/test_dashboard_remodel_static.py tests/unit/test_dashboard_route_parity.py -q
git diff --check -- ai_strategy_loop/dashboard/frontend/remodel/src/app.js ai_strategy_loop/dashboard/frontend/remodel/styles/theme.css tests/unit/test_dashboard_remodel_static.py artifacts/ultragoal-g003-interactive-charts
```

## Result
G003 is implementation-complete pending Ultragoal review gates: charts no longer act as passive poster images, mouse hover and keyboard navigation expose datum values, and chart replay candlesticks now show data provenance and accessible active values.
