# P3 Preflight Smoke Summary

## Run

- Run ID: `tick_p7_preflight_observable_20260605`
- Config: `.omo/evidence/tick-p7-observability-bounded-training-20260605/p3-preflight-config.json`
- Period: `2025-01-01..2025-01-31`
- Time window: `09:00:00..09:30:00`
- Timeframe: `tick`
- Engine mode: `warm`
- Warm engine count: `8`
- Max generations: `1`
- Warm per-run timeout: `300s`
- Loop wall clock: `383.2s` reported by loop, `392.2s` observed by wrapper.

## Result

- Warm prepare completed with `back_count=400`.
- gen0 seed evaluation used `C_T_900_920_U2_B` / `C_T_900_920_U2_S`.
- gen0 warm backtest timed out after `300s`.
- CSV was not produced.
- DB row was recorded with `status=error`, `score=0.0`, `trade_count=0`, and reason:
  `backtest failed/timeout: warm backtest non-success: status=error message=백테스트 시간 초과 (300초) csv=no`
- Loop reached `max_generations=1` and published final status `complete`.

## Observability Result

The preflight did prove that the dashboard status path now exposes the important bounded-run fields:

- `progress_source=generation_level`
- `timeout_sec=300`
- `bt_engine_mode=warm`
- `bt_timeframe=tick`
- `effective_engine_count=8`
- `cpu_count=64`
- `bt_full_start=20250101`
- `bt_full_end=20250131`
- `bt_universe_start_time=90000`
- `bt_universe_end_time=93000`
- recent logs for warm prepare, backtest start, backtest end, and completion.

## Decision

P3 is complete as an observability smoke, but it is also a blocker for the long P4 run.

Per plan rule, because preflight timed out, P4 2023-2025 training must not start in this execution.

Terminal path: `blocked_with_timeout_evidence_no_oos`.

## Evidence Files

- `p3-preflight-config.json`
- `p3-preflight-log.txt`
- `p3-preflight-err.txt`
- `p3-status-snapshots.jsonl`
- `p3-status-snapshot.json`
- `p3-dashboard-server.out.txt`
- `p3-dashboard-server.err.txt`
- `p3-preflight-blocked.md`

## Guardrail

- No 2022/2026 OOS was run.
- No `final_approval`, `export_winner`, production DB write, live broker action, V3K action, or blanket `taskkill` was used.
- Official engines and hard-gate semantics were not edited.
