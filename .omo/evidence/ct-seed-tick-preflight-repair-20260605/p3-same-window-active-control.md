# P3 Same-Window Active Control

Status: `complete`

## Selected Window

- Date: `2025-01-03`
- Window: `09:02:00..09:05:00`
- Timeframe: `tick`
- Reason: P1 shows coverage, P2 shows control buy static hints for `09:02..09:05`, and C_T also has surrounding active time branches.

## Control Runtime

Artifacts:

- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p3-control-902-905-config.json`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p3-control-902-905-result.json`
- `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p3-control-902-905-result.stdout.txt`

Observed:

| Field | Value |
|---|---:|
| run id | `ct_preflight_control_902_905_warm_20260605` |
| wrapper status | `ok` |
| timeout | `false` |
| wall cap | `210s` |
| wrapper elapsed | `51.454s` |
| warm prepare | `completed` |
| back_count | `43` |
| backtest status | `success` |
| backtest elapsed | `11.3s` |
| gate_passed | `true` |
| profit | `149,567` |
| trades | `1` |
| mdd | `2.99` |

## Decision

This is a valid same-window active control for `2025-01-03 09:02..09:05`. It is diagnostic only and not a performance/OOS claim.

P4 may run C_T on this exact same date/window.

## QA

| Scenario | Result |
|---|---|
| Same-window control passes | pass; CSV/metrics-producing control runtime recorded |
| No fair active control | not applicable; a fair active control was found |

## Adversarial Notes

- Hung/long command: inner warm timeout `90s`, outer wall cap `210s`, run completed under cap.
- Misleading success: control success is only an environment/window sanity check.
- Dirty worktree: runtime DB/CSV is evidence only and must not be staged.
