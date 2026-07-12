# UI Implementation Spec

## Visual System

- Dark quant terminal base.
- Near-black page background.
- Dense modular panels with subtle borders.
- Korean labels; technical English only for field names and industry-standard terms.
- Monospace for run IDs, strategy IDs, code, numeric metrics, timestamps.
- Theme toggle supports light/dark via CSS variables.

## Global Shell

Visible on every page:

- Header title: `STOM AI · 조건식 AI 연구 대시보드`
- Backend Base URL
- Reconnect button
- REST Health badge
- WebSocket status badge
- Run Status badge
- Route owner/boundary strip
- Top tabs: `조건식 AI`, `백테스트`, `차트 리플레이`
- Nested condition tabs
- LIVE/archive selector
- Generation progress
- Provider, timeframe, run_id
- Start/Stop controls
- Settings modal preview
- Safety/contract cues

## Pages

### 조건식 AI

Core evolution dashboard with live generation, active strategy, phase timeline, criteria, glossary, config, engine, cost, charts, Hall of Fame, generation table, winner approval, feedback/autopsy, analytics tiles, strategy inspector.

### 프로세스

React Flow-style process graph: Generation → Backtest → Scoring → Autopsy → Repeat. Current node and active edge highlighted. Logs, catalogs, contract, metadata.

### 히스토리

Run/gen archive, filters, research records, ResultDetail preview, compare launcher, campaign/docs/update_log/registry lineage search.

### 연구실

Active runs, stalled warnings, batch queue, freeze verdict, Edge Ratio heatmap, variable importance, correlation heatmap, combinations, holdout validation, wiki/context/process/glossary/visual quality.

### 분석 워크벤치

Candidate deep-analysis workspace with run/generation selector, HOF workbench, heatmap, candidate cards, evidence notes, review queue, handoff to History/Backtest.

### 결정 감사

Append-only evidence-to-decision ledger. PROMOTE checklist, OOS CI table, alerts, regime decomposition, revival registry, V6/M4 comparisons, decision form, note, history table. Final export approval remains separate.

### 백테스트

API health/demo banner, always-visible run panel, modes, optimize JSON, WFO, sweep, self.vars builder, active job, logs, condition editor, result analysis, A/B compare, portfolio, WFO/sweep tables, standalone report.

### 차트 리플레이

Tick/min source, days, stocks, minimap, strategy selectors, aggregation, playback controls, chart modes, indicators, candle replay charts, signal log, auto-pause, indicator table, variable watch, websocket status/error.
