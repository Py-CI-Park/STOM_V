# Codex AI Agent Brief — STOM AI Dashboard Frontend

## Objective

Turn this static HTML/CSS/JS prototype into the production frontend for `STOM AI · 조건식 AI 연구 대시보드`, preserving every existing function and information architecture shown in the design references.

## Non-negotiable Safety Contract

Do not add any of the following:

- Live order button
- Broker login
- Account balance/trading controls
- Automatic production export
- Hidden export path that bypasses human approval
- Mutable decision audit editing/deleting

Keep these cues visible across the app:

- REST + WebSocket local backend contract
- Research-only / control-plane-only wording
- Human Approval Gate
- Append-Only Audit
- Final strategy export approval separate from Decision Audit

## Current Prototype Entry Points

- `index.html`: app shell and runtime entry.
- `styles/theme.css`: design tokens, layouts, dense dashboard component styling.
- `src/data.js`: `window.STOM_DATA` dummy data used by the app.
- `src/app.js`: complete renderer for all tabs.
- `data/stom-dummy-data.json`: equivalent JSON payload for backend/API replacement.

## Suggested Production Refactor

Recommended stack if converting to a maintainable web app:

```text
Vite + React + TypeScript
Zustand or Redux Toolkit for run state
TanStack Query for REST data
native WebSocket or Socket.IO client for live stream
Monaco Editor or CodeMirror for strategy code inspection/editing
Lightweight Charts / ECharts for dense charts
Playwright for smoke/e2e
```

Suggested component tree:

```text
App
├── GlobalShell
│   ├── HeaderStatusBar
│   ├── BoundaryStrip
│   ├── PrimaryTabs
│   ├── NestedTabs
│   └── RunControlStrip
├── pages/
│   ├── ConditionOverviewPage
│   ├── ProcessPage
│   ├── HistoryPage
│   ├── LabPage
│   ├── AnalysisWorkbenchPage
│   ├── DecisionAuditPage
│   ├── BacktestPage
│   └── ChartReplayPage
├── components/
│   ├── Panel
│   ├── MetricCard
│   ├── DataTable
│   ├── SvgLineChart
│   ├── Heatmap
│   ├── CandleReplayChart
│   ├── StrategyInspector
│   ├── SettingsModal
│   └── HumanApprovalDialog
└── data/
    ├── restClient.ts
    ├── websocketClient.ts
    └── schema.ts
```

## Backend Contract Targets

Initial REST endpoints to map from dummy data:

```http
GET /health
GET /api/system/status
GET /api/runs/live
GET /api/runs/{run_id}
GET /api/condition-ai/overview?run_id=...
GET /api/condition-ai/generations?run_id=...
GET /api/process/map?run_id=...
GET /api/history/runs
GET /api/lab/edge-ratio
GET /api/workbench/candidates
GET /api/audit/decisions
GET /api/backtest/jobs
GET /api/replay/session
```

Initial WebSocket channels:

```text
/ws/state          run status, progress, phase, active generation
/ws/process        process node/edge updates and logs
/ws/backtest       job progress and log tail
/ws/replay         replay cursor, candle updates, signal log
/ws/audit          append-only ledger notification only
```

## Implementation Notes

- Keep Korean labels as the primary UI language.
- Use monospace for numeric metrics, code, IDs, run IDs, timestamps, API URLs.
- Semantic colors must remain consistent:
  - Green/teal: success/gains
  - Red: risk/loss/error
  - Amber: running/warning/pending
  - Violet: winner/approval
  - Blue: gate-passed/info
- Avoid crypto/gamified UI metaphors. This is a professional research workstation.
- Preserve dense data layout, but enforce consistent spacing and card hierarchy.
- Any save/export/decision action must expose clear confirmation and audit implications.

## Work Items for Codex

1. Split `src/app.js` into page modules.
2. Convert dummy-data lookups to typed data selectors.
3. Add route-aware URL state such as `?tab=condition&sub=lab&run_id=...`.
4. Add API client that can fall back to `data/stom-dummy-data.json` when backend is unavailable.
5. Replace SVG helper charts with a production chart library if needed.
6. Add Playwright tests for all tabs, modal opening, theme toggle, and safety cues.
7. Add snapshot/regression tests to ensure no live-order/broker/account controls are introduced.

## Acceptance Checklist

- All top-level and nested tabs render.
- Global shell remains visible on every page.
- Settings modal opens.
- Strategy Inspector modal opens.
- Human Approval dialog opens.
- Backtest page contains edit/result sections.
- Chart Replay page contains source/day/stock/strategy/replay controls and websocket status.
- Decision Audit page contains append-only decision ledger and decision form.
- There is no live order, broker login, account trading, or automatic production export UI.
