## Summary
The G003 implementation is a real move away from static SVG posters: chart registry, shared normalization, hover tooltip, crosshair, keyboard focus, aria-live active values, route coverage, and screenshot/browser artifacts are present. I do not approve the gate because three acceptance items are still missing or under-proven: malformed/stale state handling, run/freshness provenance, and legend highlight.

## Analysis
- Chart primitives are centralized in app.js lines 321-469 with chartRegistry, registerChart, lineSvg, barLineChart, datumLabel, and attachChartEvents. CSS support for focus rings, crosshair, tooltip, active datum, and empty states is in theme.css lines 260-277.
- Required route application is broadly present: condition quality/profit/equity/fitness/backtest charts at app.js lines 1046-1055, history at 1108-1115, lab at 1132 and 1135, workbench at 1145-1146, backtest at 1192, and chart replay candlesticks at 1224 and 1230-1262.
- Browser evidence reports 37 interactive charts and hover plus keyboard probes across condition, history, lab, workbench, audit, backtest, and chart replay in browser-transcript.json and verification-summary.json. It does not probe legend highlighting or malformed/stale data states.
- Safety constraints look preserved in the inspected scope: explicit no live order, broker login, and account trading cues exist at app.js line 1080; backtest POST endpoints are manual-gated in contract rows at lines 63-81 and evidence marking at 693-694; replay /sim/ws and actions are user-gated at 99-105 and 778. No hidden live order, broker login, account trading, or auto /sim/ws mutation was found in the scoped files. The existing live /ws state socket at lines 963 and 1288 is a state bridge, not a G003 replay/action stream.

## Root Cause
The primitive was implemented primarily as a drawable SVG interaction layer. It normalizes/filter-coerces data to make charts render and derives provenance from global mode instead of carrying a first-class per-chart/per-datum contract for validity, run id, freshness, fallback, and stale state.

## Findings
1. HIGH - app.js lines 353-358, 399-401, and 1232-1234 silently drop malformed numeric points or candles and only show an empty state when all data disappears. Impact: malformed backend or fixture data can be hidden as a normal chart, which violates the malformed/loading/stale state requirement and weakens data integrity review. Fix: return a normalization result with valid points, invalid counts, original indexes, and status; show a visible malformed state or gap markers when any values are discarded, and add stale/loading states separately.
2. HIGH - app.js lines 223-307, 368, 413, and 1245 do not carry run id or freshness in datum labels and can label live-mode fallback/fixture baseline as backend/read-only. Impact: charts are not data-provenance aware enough for the G003 gate; users cannot tell which run and freshness produced a datum, and fallback fixtures can look backend-derived. Fix: include source, run_id, fetched_at/as_of age, freshness state, and fallback/stale state in chart metadata and datumLabel; derive source from actual payload evidence, not only isLiveBackendMode.
3. MEDIUM - app.js lines 394 and 425 plus theme.css lines 275-277 render static legends only. attachChartEvents at app.js lines 427-469 has no legend event path, active-series state, aria-pressed control, or series dimming/highlight style. Impact: the legend highlight acceptance item is not implemented. Fix: render legend items as buttons tied to series identity, update active series on hover/focus/click/keyboard, dim non-active series, and prove it in static and browser tests.
4. MEDIUM - tests/unit/test_dashboard_remodel_static.py lines 128-154 and artifacts browser-transcript.json verify primitive markers, hover, keyboard, and screenshots, but not legend highlight, malformed/stale states, live fallback provenance, run id, or freshness. Impact: the evidence can pass while important G003 acceptance criteria remain absent. Fix: add focused static and browser probes for those criteria.

## Recommendations
1. Block checkpoint approval until malformed/stale/freshness/run provenance is implemented and proven.
2. Implement legend highlight as an accessible primitive instead of static legend text.
3. Extend browser evidence to exercise malformed input, stale/loading/fallback labels, legend highlight, and live-mode fallback provenance on at least one line, bar-line, and replay candle chart.
4. Keep the existing safety posture: safe GET probes may remain, but mutating endpoints and /sim/ws must stay manual-gated.

## Architectural Status
WATCH

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
- Central primitive with richer metadata: best maintainability and consistent accessibility, but requires touching all chart construction callsites.
- Per-chart ad hoc fixes: faster short-term, but risks divergent provenance and malformed behavior.
- Artifact-only acceptance: fastest, but insufficient because current artifacts miss required failure and legend paths.
