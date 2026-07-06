# Plan D R1 Rank01 Context Pack Draft (2026-07-06)

## Scope

- seed_id: `plan_d_rcs_oos_20260706_rank01`
- condition_id: `repair_v3_20260706_13_top_four_plus_l14_sell_default_tp3_sl3_hold60`
- source: `repair_composite_selected_oos`
- label: `hypothesis_seed`
- run_id template: `seedref_plan_d_rcs_oos_20260706_rank01_r1_20260706`
- candidate quota: repair 5 / discovery 3
- current decision: `open_r_c_generation_dry_run_next_scope`

## Parent Evidence

| metric | value |
|---|---:|
| profit_krw | 1079768.0 |
| mdd_pct | 4.06 |
| daily_avg_trades | 0.5 |
| trade_count | 19 |
| score | 10.302048909853827 |

## R-a Static Ablation Summary

- buy clauses: 5
- sell clauses: 4
- static duplicate/ineffective candidates: 0
- data-backed ineffective verdict: not produced in this scope
- reason: no per-trade pool or replay was opened

## R-b Axis Readiness

- axis ledger: `docs/research/condition_research/generated_conditions/axis_ledger.jsonl`
- exists: `False`
- rows: 0
- readiness: `ready_with_empty_priors`
- banned_axes: []

## R-c Guardrails

- research lane only
- `hypothesis_seed` label required
- dry-run before any INSERT-only DB registration
- no UPDATE/DELETE
- no OOS without freeze/preregistration
- no portfolio/export/live/final promotion

## Caveat

The selected 16 were chosen from a full-period min preflight that included 2026-01-01~2026-02-27, so this is a fixed OOS-style robustness replay, not a fully blind discovery OOS.
