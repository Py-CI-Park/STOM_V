# P7 Decision Card

## Executive Verdict
No candidate is eligible for fixed 2022/2026 OOS. P5 produced 10 training generations, but yearly_sparse_robust_v1 selected no candidate. The workflow correctly blocked P6 instead of running OOS after a failed training-only selector.

## Selector Version
- selector_version: yearly_sparse_robust_v1
- base selector: sparse_positive_v1
- policy_hash: ae50a063b0945abaab6669c3498ec90200964018d60b76a4a4fed954fd500f73
- config_hash: 62c8786c719544f0d6bdbfa887105383bf6e66a46ec57b26c29f21acf13b1132
- selected: false
- blocker: no candidate qualified for yearly_sparse_robust_v1

## Candidate Identity
No frozen candidate identity exists.

Notable near misses:
- gen6: profit 1,343,705, MDD 7.6, trades 136; rejected because trade_count < 150.
- gen7: profit 1,378,444, MDD 10.32, trades 91; rejected because mdd > 10.0.

## Training Yearly Evidence
No selected candidate means there is no qualifying yearly breakdown artifact. The selector did not reach OOS eligibility because all generations failed aggregate sparse-positive plus robust pre-OOS checks.

## OOS Evidence
P6 fixed 2022/2026 OOS was not executed. This is required behavior because p5-selected-candidate.json has selected=false.

Predeclared P6 run-id check:
- tick_oosrob_p6_seed_2022_20260604: generation_count=0
- tick_oosrob_p6_seed_2026_20260604: generation_count=0
- tick_oosrob_p6_ai_2022_20260604: generation_count=0
- tick_oosrob_p6_ai_2026_20260604: generation_count=0

## Seed Comparison
No fresh seed-vs-AI comparison exists in this plan because OOS was correctly blocked. Prior rejected-candidate OOS remains historical lesson only and was not used for selector tuning.

## Trade Sufficiency
Trade sufficiency failed before OOS. The strongest positive-MDD candidate, gen6, had only 136 trades against the robust selector's minimum 150 total training trades. Gen7 had only 91 trades and MDD above the cap.

## Slippage Status
Slippage stress was not run because there is no frozen candidate and no fixed OOS result to stress. Lowercase audit term: slippage remains unresolved. Slippage remains an advisory blocker for any future promotion. No 0.1%, 0.2%, or 0.3% haircut can be interpreted as pass/fail without a selected OOS candidate.

## PBO/DSR Status
PBO/DSR tooling was searched. The repository currently has PBO/DSR documentation and advisory blocker policy, but no promotion-ready read-only PBO/DSR execution evidence for this candidate path. PBO/DSR remains an advisory blocker.

## Forbidden Actions Check
- final_approval invoked: false
- export_winner invoked: false
- production strategy DB write: false
- hard gate edited: false
- official engine edited: false
- backtest/graph edited: false
- OOS-after-the-fact reselection: false
- blanket taskkill: false
- V3K gate/live/KHOPENAPI action: false

## Final Verdict
NEEDS_MORE_EVIDENCE

Reason: no candidate satisfied yearly_sparse_robust_v1, so P6 OOS was correctly skipped. There is no basis for a human-level, seed-superior, or production-promotion claim.

