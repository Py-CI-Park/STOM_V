# Lattice Condition Generation V2 Candidate Quota Ledger

Created: 2026-07-08T09:58:26+09:00

| Class | Quota | Purpose |
|---|---:|---|
| coverage_composite | 8 | repair daily coverage without accepting high MDD |
| risk_balanced_composite | 8 | combine low-MDD and coverage fragments |
| survivor_seed_derivative | 8 | borrow components from survivor lineage without copying full survivors |
| negative_control | 4 | detect misleading success output and gate drift |
| holdout_control | 4 | benchmark against frozen survivor controls |

Max next-phase candidates: 32.

Allowed next phase: source read, metadata generation, static gate, DB registration dry-run.
Forbidden next phase: DB INSERT apply, backtest, limited replay, OOS, portfolio, Plan D R3, promotion.
