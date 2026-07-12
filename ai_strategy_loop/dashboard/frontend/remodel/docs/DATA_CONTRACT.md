# Data Contract Draft

## Global Shell

```json
{
  "backendUrl": "http://127.0.0.1:9200",
  "restHealth": "UP",
  "websocket": "connected",
  "runStatus": "running",
  "provider": "STOM-AI Engine v2.3.1",
  "timeframe": "1D",
  "runId": "R-250518-1421-7XQ9",
  "generationProgress": 68.5,
  "mode": "research-only",
  "contract": "REST + WebSocket (Local)"
}
```

## Condition AI Overview

Use `/api/condition-ai/overview?run_id=...`.

Required blocks:

- live generation phase/checkpoint/message
- active strategy
- phase timeline
- research criteria
- active config
- engine summary
- cost/tokens
- charts: fitness, profit, equity, backtest detail, GUI parity, quality
- hall of fame
- generation table
- winner approval/export state
- feedback/autopsy
- right-side analytics tiles
- strategy inspector code payloads

## WebSocket Events

```json
{
  "type": "generation_progress",
  "run_id": "R-...",
  "generation": 137,
  "phase": "backtest",
  "progress": 64,
  "checkpoint": "7/10",
  "message": "백테스트 실행 중"
}
```

```json
{
  "type": "append_log",
  "scope": "process|backtest|replay|audit",
  "level": "INFO|WARN|ERROR|DEBUG",
  "timestamp": "2025-05-19T14:32:18+09:00",
  "message": "..."
}
```

## Mutating Endpoints

These must require explicit human confirmation and append-only audit where applicable.

```http
POST /api/strategies/{strategy_id}/save
POST /api/winner/export-request
POST /api/audit/decision
POST /api/backtest/job/cancel
```

Do not create any live order endpoint in the frontend contract.
