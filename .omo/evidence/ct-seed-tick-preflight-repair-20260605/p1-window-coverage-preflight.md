# P1 Exact Tick Window Coverage Preflight

Status: `complete`

Raw artifact: `.omo/evidence/ct-seed-tick-preflight-repair-20260605/p1-window-coverage-preflight.json`

## Method

- DB: `_database/stock_tick_back.db`
- Access: SQLite URI `mode=ro`
- Dates scanned: `2025-01-02`, `2025-01-03`, `2025-01-06`, `2025-01-07`
- Windows scanned: `09:00..09:01`, `09:00..09:03`, `09:00..09:05`, `09:01..09:02`, `09:02..09:03`, `09:02..09:05`, `09:03..09:05`, `09:04..09:05`

## Key Findings

| Date | Window | moneytop rows | distinct codes | Candidate |
|---|---|---:|---:|---|
| `2025-01-02` | `09:00..09:05` | `0` | `0` | no |
| `2025-01-03` | `09:00..09:01` | `60` | `134` | data-covered but prior control/C_T no-metrics |
| `2025-01-03` | `09:02..09:05` | `181` | `43` | yes |
| `2025-01-06` | `09:02..09:05` | `181` | `62` | backup |
| `2025-01-07` | `09:02..09:05` | `181` | `59` | backup |

## Selected Runtime Candidate

`2025-01-03 09:02:00..09:05:00`

Reason:

- It is data-covered.
- The prior control strategy has static buy-window hints for `09:02..09:05`.
- The previous page already showed the same active-window control can produce CSV/metrics on this day.
- C_T has static buy-window hints covering this interval through its `09:05..09:10` branch and surrounding segments.

## QA

| Scenario | Result |
|---|---|
| Covered active windows found | pass; raw JSON lists per-window moneytop/code facts |
| Empty window remains explicit | pass; `2025-01-02 09:00..09:05` remains zero coverage |

## Adversarial Notes

- Malformed input: not applicable; fixed dates/windows were generated from prior evidence.
- Stale state: current DB was read directly in `mode=ro`.
- Misleading success: data coverage is not counted as a trading preflight pass.
