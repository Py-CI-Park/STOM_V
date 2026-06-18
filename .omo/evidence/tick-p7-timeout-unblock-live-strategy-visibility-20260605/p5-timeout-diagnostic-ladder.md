# P5 Timeout Diagnostic Ladder

Status: `blocked_at_5m_gate`

## Diagnostic 1: 5m Seed Gate

| Item | Value |
|---|---|
| Run ID | `tick_p7_seed_diag_5m_20260605` |
| Config | `p5-seed-diag-5m-config.json` |
| Period | `2025-01-01..2025-01-03` |
| Timeframe | `tick` |
| Window | `09:00:00..09:05:00` |
| Seed buy/sell | `C_T_900_920_U2_B` / `C_T_900_920_U2_S` |
| Engine mode | `warm` |
| Warm engine count | `8` |
| Warm prepare back_count | `58` |
| Warm timeout | `120s` |
| Backtest elapsed | `133.2s` |
| Wrapper elapsed | `176s` |
| CSV | no |
| DB status | `error` |
| DB trade_count | `0` |
| Reason | `backtest failed/timeout: warm backtest non-success: status=error message=백테스트 시간 초과 (120초) csv=no` |

## Result

The first diagnostic gate failed. Even the reduced 3-day, 5-minute tick window timed out before producing a CSV.

Per the plan:

- `tick_p7_seed_diag_10m_20260605` was not started.
- `tick_p7_seed_preflight_jan_retry_20260605` was not started.
- `2023-01-01..2025-12-31` training was not started.
- 2022/2026 OOS remains blocked.

Terminal path for P5/P6: `BLOCKED_WITH_TIMEOUT_EVIDENCE_NO_OOS`.

## Evidence Files

- `p5-seed-diag-5m-config.json`
- `p5-seed-diag-5m-log.txt`
- `p5-seed-diag-5m-err.txt`
- `p5-seed-diag-10m-config.json` (not run)
- `p5-seed-preflight-jan-retry-config.json` (not run)

## Adversarial QA

| Class | Result |
|---|---|
| malformed input | All diagnostic configs parsed through `config_from_dict`; bounds printed correctly. |
| prompt injection | No `final_approval`, `export_winner`, live broker, or V3K route invoked. |
| cancel/resume | The owned loop process exited by itself; no forced kill was needed. |
| stale state | Fresh run ID `tick_p7_seed_diag_5m_20260605` used. |
| dirty worktree | Existing dirty tree preserved; runtime DB writes are run evidence only, not source staging. |
| hung or long commands | 240s wrapper cap used; process exited at 176s. |
| flaky tests | Not applicable; this was a bounded runtime diagnostic. |
| misleading success | Diagnostic is recorded as blocked even though the loop process exited normally. |
| repeated interruptions | This file records the exact first failed gate and stop rule. |

