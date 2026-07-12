# Plan D rank03 R1 selected OOS preregistration draft

- created_at: 2026-07-07T17:55:13+09:00
- status: draft_only_not_executed
- source_run_id: `lat_plan_d_rank03_r1_8_min_warm64_20260707`
- oos profile: official min warm64 fixed-window robustness/OOS-style replay
- allowed candidates: selected improved candidates only
- forbidden: non-selected OOS, portfolio, export/live/final promotion, DB UPDATE/DELETE, full tick/min 288

## Selected Candidates

| label | profit | MDD | trades | daily | reason |
|---|---:|---:|---:|---:|---|
| `plan_d_r1_rank03_r1_08_parent_buy_default_tp3_sl3_hold90` | 1652322 | 15.79 | 181 | 0.80 | best_profit_and_lower_mdd_vs_rank03_parent_preflight |

## Execution Boundary

This document does not execute OOS. The next scope must recheck this freeze ledger and execute only the listed selected candidate(s).
