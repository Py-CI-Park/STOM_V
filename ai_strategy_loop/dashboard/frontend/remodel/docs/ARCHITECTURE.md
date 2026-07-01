# Architecture

## Runtime Model

This prototype is a no-build, offline static SPA:

```text
index.html
  ├─ styles/theme.css
  ├─ src/data.js      -> window.STOM_DATA
  └─ src/app.js       -> renderer, state, events, chart helpers
```

The prototype intentionally avoids external dependencies so it can be opened directly and inspected by a Codex AI Agent without package installation.

## State Model

Current app state is minimal:

```js
state = {
  primary: 'condition' | 'backtest' | 'replay',
  sub: 'overview' | 'process' | 'history' | 'lab' | 'workbench' | 'audit',
  runStatus: 'idle' | 'running' | 'stopping' | 'complete' | 'error',
  liveMode: 'LIVE' | 'ARCHIVE'
}
```

## Rendering Principles

- Shell renders first, then page body renders into `#page`.
- All tabs use the same `Panel`, `MetricCard`, `DataTable`, `SVG chart`, `Heatmap`, and modal primitives.
- Data is read from `window.STOM_DATA`, which mirrors `data/stom-dummy-data.json`.

## Production Migration

For production, use the static prototype as a UI/IA reference and migrate in this order:

1. Build shared theme tokens and shell.
2. Build panel/data-table/chart primitives.
3. Implement page components one by one.
4. Replace static data with REST query hooks.
5. Add WebSocket stream store.
6. Add action APIs only after approval/audit semantics are fully implemented.
