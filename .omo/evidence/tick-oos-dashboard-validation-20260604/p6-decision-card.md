# P6 Decision Card

## Executive Verdict
- Final Verdict: `REJECT_CANDIDATE`
- Reason: the fixed AI candidate failed the predeclared 2022/2026 OOS superiority rule. AI_2022 is negative, combined AI profit is below seed, and AI max MDD is above seed max MDD.
- This is a research validation result, not production promotion.

## Candidate Identity
- Training run: `tick_oos_dash_p3_train_2023_2025_20260604`
- Selected generation: `4` by pre-OOS graded-score rule only
- Buy: `AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g4_buy`
- Sell: `AILOOP_tick_oos_dash_p3_train_2023_2025_20260604_g4_sell`
- Training gate_passed=False, training_profit=-67,190, MDD=23.52, trades=287
- Candidate was fixed before OOS and was not reselected after OOS.

## Training Evidence
- P3 completed 6 generations over `2023-01-01 ~ 2025-12-31`, tick `09:00~09:30`, official loop exit 0.
- Winner is `null`. The selected gen4 is training-negative and gate false.
- gen5 was sparse-positive in training but was not selected by the declared P3 graded-score rule; changing to gen5 now would be OOS/after-the-fact reselection.

## Dashboard Analysis
- P4 global pooled trades=7967, win_rate=0.4672, avg_return=-0.1820, total_profit=-72,411,833, edge_ratio=1.0097.
- Largest absolute Spearman correlation=0.0715 on `B_회전율`; variable signal strength is weak.
- Segment feedback classification: `observed`. Buy prompt observed segment avoid; sell prompt did not.
- Research docs/wiki and strategy diff were available through dashboard APIs, but they do not change the OOS verdict.

## OOS Evidence
| row | gate | profit | pct | MDD | trades | reason |
|---|---:|---:|---:|---:|---:|---|
| seed_2022 | True | 2,223,554 | 44.36 | 13.02 | 58 | `ok` |
| seed_2026 | False | -191,109 | -3.82 | 15.63 | 10 | `total_profit -1.911e+05 <= 0` |
| ai_2022 | False | -531,523 | -10.63 | 16.77 | 99 | `total_profit -5.315e+05 <= 0` |
| ai_2026 | True | 126,238 | 2.52 | 2.52 | 2 | `ok` |

## Seed Comparison
- combined_seed_profit=2,032,445
- combined_ai_profit=-405,285
- seed_max_mdd=15.63
- ai_max_mdd=16.77
- seed_total_trades=68
- ai_total_trades=101
- ai_positive_both_oos_years: False
- combined_ai_profit_gte_seed: False
- combined_ai_max_mdd_lte_seed: False
- candidate_identity_matches_p3: True
- no_oos_reselection: True
- superiority_rule_passed=False

## Human Reference Corridor
- Not satisfied. The AI candidate does not beat the seed reference across fixed OOS splits, so no human-level or seed-superior claim is allowed.
- AI_2026 has only 2 trades and payoff_ratio 999.0, which is too sparse to support robust execution claims even though that single split passed.

## Overfit Risk
- High. P3 selected candidate is training-negative, P4 global edge is negative, and OOS behavior is split-inconsistent: negative in 2022, positive but extremely sparse in 2026.
- The selection rule optimized graded score under pre-OOS training, but this did not transfer to OOS superiority.

## PBO/DSR Status
- PBO/DSR was not computed in this plan. Because P5 already fails, unavailable PBO/DSR is not the deciding blocker; it remains required before any future promotion claim.

## Slippage / Execution Stress
- Slippage-stressed OOS was not run in this plan. Promotion is impossible without positive slippage-stressed OOS in both 2022 and 2026.
- Current unstressed OOS already fails, so slippage would only worsen the decision margin.

## Forbidden Actions Check
- `final_approval`: not invoked.
- `export_winner`: not invoked.
- Production strategy DB/write boundary: not invoked.
- V3K/USER_ACK/KHOPENAPI/live order wiring: not invoked.
- Engine/hard-gate/backtest_graph changes: not performed by this plan.

## Final Verdict
- Final Verdict: `REJECT_CANDIDATE`
- Next practical research direction: do not promote this candidate; update the next plan to investigate selection criteria that penalize training-negative gen4 and evaluate sparse-positive gen5-style ideas only through a fresh predeclared training/OOS split.
