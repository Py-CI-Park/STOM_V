# Plan D rank01 R2 freeze/preregistration draft

- created_at: 2026-07-06T16:56:17+09:00
- parent scope: plan-d-rank01-rd-freeze-r2-limited-replay-no-portfolio-export
- active parent: `plan_d_r1_rank01_04_repair_l14_liquidity_tight_default`
- coverage watch only: `plan_d_r1_rank01_06_discovery_adjacent_l13_l14_coverage`
- forbidden in this scope: OOS, portfolio, export/live/final, DB UPDATE/DELETE, >24 pairs

## Freeze basis

| item | parent rank01 | slot04 active parent |
|---|---:|---:|
| profit | 1887171 | 2153579 |
| MDD | 19.25 | 18.69 |
| trade_count | 206 | 201 |
| daily_avg_trades | 1.00 | 0.90 |

slot04 is frozen because it is the only R-c candidate with both profit improvement and lower MDD versus the rank01 parent baseline.

## R2 bounded replay preregistration

R2 candidates may mutate only the slot04 L14 gate and sell profile axis. The limited replay is capped at 24 pairs on official min full-period warm64. OOS and portfolio remain closed until this replay produces a preregistered improved candidate set.
