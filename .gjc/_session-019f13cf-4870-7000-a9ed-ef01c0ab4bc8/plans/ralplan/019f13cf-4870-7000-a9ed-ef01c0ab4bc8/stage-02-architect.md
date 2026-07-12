# G003 interactive chart re-review

## Summary
REQUEST CHANGES. Legend highlight, keyboard and hover interactions, state badges, malformed counts, and reference-mode browser evidence are present, but live-mode chart provenance still overstates fixture charts as live payload once any backend payload exists. The blocker is provenance accuracy, not interaction coverage.

## Analysis
- `app.js` lines 346-361 centralize chart provenance and badges. The fallback with no payload is explicit as `fixture fallback · backend not driving chart`, `stale-fixture-fallback`, `STALE/FALLBACK`, plus `run_id` and `malformed` badges.
- Legend highlight is implemented in `app.js` lines 478-516 using legend hover, focus, click, Enter, Space, `aria-pressed`, and class toggles for `series-highlighted` and `series-dimmed`. CSS lines 269-285 style the dim, highlight, and active legend states.
- Browser artifacts show 37 interactive charts across reviewed routes, hover plus keyboard probes passing, and the current probe records legend active state with 56 highlighted and 168 dimmed elements plus badges `status=CURRENT`, `run_id=R-250518-1421-7XQ9`, `freshness=reference-static`, `malformed=0`.
- The verification artifacts are reference-mode only: browser transcript URLs and current probe URLs all include `demo=reference`. They do not exercise live-mode fallback or partial live payload provenance.
- `mapLoopState` updates only selected overview series at lines 925 and 980-982, and `mapRuns` updates only history table rows at lines 987-990. Many chart inputs remain fixture/static.
- `chartProvenance` lines 346-350 treats any `state.latestLoopPayload` or `state.latestRunsPayload` as enough to label default charts `backend/read-only payload`, `live-read`, and `CURRENT`. That means lab, workbench, audit, some overview charts, and backtest charts can be labeled live despite fixture data.
- Replay charts are stronger evidence of the same defect: `renderReplay` renders `DATA.replay` candles through `candleSvg` at line 1304, while `candleSvg` lines 1318-1321 hard-codes live mode to `source=sim read-only payload`, `freshness=sim-live-read`, and `status=CURRENT` even though `ReplayAdapter.ensurePageEvidence` only records endpoint evidence and never maps `/sim` data into the candle arrays.
- Safety boundaries remain intact in the inspected files: reference and demo modes are inert, no project edits or project-wide gates were run, and cleanup/static-test artifacts confirm no broker, order, account, or auto-export affordance was introduced.

## Root Cause
The chart provenance primitive is keyed to global mode and presence of any backend payload, not to the actual data source of each chart series. This creates a broad compatibility-style fallback that hides fixture usage behind live-looking labels in partial-live or replay-live scenarios.

## Findings
1. HIGH - `ai_strategy_loop/dashboard/frontend/remodel/src/app.js:346` - Live-mode chart provenance can mislabel fixture/static chart data as `backend/read-only payload`, `sim read-only payload`, `live-read`, and `CURRENT`. This violates the G003 requirement for explicit non-misleading source, run, freshness, malformed, loading, and stale state labels. Fix by passing per-chart source metadata from the adapter or data mapper, and keep un-mapped fixture charts labeled `fixture fallback`, `stale-fixture-fallback`, or route-specific `not live-driven` until that specific chart series is actually populated from backend or sim payload. Add browser evidence for live disconnected and partial-live paths.

## Recommendations
1. Make `chartProvenance` per-chart or per-data-source instead of global. A live payload for overview must not mark lab, workbench, audit, backtest, or replay fixture charts as live.
2. For replay, either map verified `/sim` data into `DATA.replay` before using `sim-live-read`, or retain `reference replay fixture` with stale or fallback status in live mode until the candle series is actually backend-derived.
3. Add focused evidence for live-mode no-backend and partial-backend cases, in addition to the current reference-mode interaction evidence.

## Architectural Status
BLOCK

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
- Per-chart provenance metadata: highest correctness, more callsite annotations.
- Global provenance: low code churn, but keeps the current misleading labels and should not be accepted.
- Adapter-owned data source tags: good long-term boundary, requires mapping each adapter output to chart inputs.
