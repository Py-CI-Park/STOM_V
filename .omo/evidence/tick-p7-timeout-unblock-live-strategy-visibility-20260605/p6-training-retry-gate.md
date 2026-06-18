# P6 Training Retry Gate

Verdict: `blocked`

The next 2023-2025 training retry is not allowed from this page.

## Reason

The first timeout diagnostic gate failed:

- Run ID: `tick_p7_seed_diag_5m_20260605`
- Period: `2025-01-01..2025-01-03`
- Window: `09:00:00..09:05:00`
- Warm timeout: `120s`
- Result: timeout after `133.2s`, no CSV

This means the blocker is not just the full January 09:00-09:30 workload. The seed itself can still overrun a very small TICK diagnostic window in warm mode.

## Gate Decision

| Candidate Next Step | Allowed? | Reason |
|---|---:|---|
| 10m diagnostic | no | 5m gate failed |
| January retry | no | 5m gate failed |
| 2023-2025 training | no | no passing preflight |
| 2022/2026 OOS | no | no frozen promotion candidate |
| Timeout/root-cause plan | yes | next work should inspect seed/warm timeout mechanics |

## Required Before Training

One of these must happen before retrying 2023-2025:

- reduce seed diagnostic work further to isolate the overrun cause;
- add explicit warm-session timeout/root-cause instrumentation outside official engine internals;
- compare warm vs cold seed execution on the same tiny period/window;
- inspect whether seed condition over-fires within `09:00:00..09:05:00`.

## Next Recommended Command

```text
$ulw-plan tick seed warm timeout root-cause plan: use .omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-timeout-diagnostic-ladder.md as primary evidence. Diagnose why C_T_900_920_U2_B/S times out even on 2025-01-01..2025-01-03 tick 09:00-09:05 warm mode, compare smaller window and cold/warm behavior if safe, preserve official backtest engines and hard gates, and do not start 2023-2025 training or OOS until a passing preflight exists.
```
