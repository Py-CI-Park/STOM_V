# P7 Decision Card

## Executive Verdict
- Final Verdict: `REJECT_CANDIDATE`
- Reason: the frozen sparse-positive candidate failed the predeclared 2022/2026 OOS pass rule.
- This is research validation only, not production promotion and not a human-superiority claim.

## Generation Toggle
- Toggle: `sparse_positive_prompt_enabled`
- Default: `false`
- P5 training config: `true`
- Function: advisory prompt guidance only; hard gates and selector thresholds were not weakened.

## Candidate Identity
- Training run: `tick_spgen_p5_train_2023_2025_20260604`
- Selected generation: `4`
- Selected bucket: `sparse_positive`
- Buy: `AILOOP_tick_spgen_p5_train_2023_2025_20260604_g4_buy`
- Sell: `AILOOP_tick_spgen_p5_train_2023_2025_20260604_g4_sell`
- Candidate was frozen before OOS and was not mutated/reselected after OOS.

## Training Evidence
- Profit: `1,155,715`
- MDD: `9.12`
- Trades: `124`
- Daily avg trades: `0.2`
- Payoff ratio: `1.5523029966703663`
- Gate reason: `daily_avg_trades 0.2 < min_daily_trades 0.3`

## OOS Evidence
| row | gate | profit | MDD | trades | reason |
|---|---:|---:|---:|---:|---|
| seed_2022 | True | 2,223,554 | 13.02 | 58 | `ok` |
| seed_2026 | False | -191,109 | 15.63 | 10 | `total_profit -1.911e+05 <= 0` |
| ai_2022 | False | -222,400 | 9.0 | 24 | `total_profit -2.224e+05 <= 0` |
| ai_2026 | True | 356,664 | 1.36 | 7 | `ok` |

## Seed Comparison
- combined_seed_profit: `2,032,445`
- combined_ai_profit: `134,264`
- seed_max_mdd: `15.63`
- ai_max_mdd: `9.0`
- seed_total_trades: `68`
- ai_total_trades: `31`
- ai_positive_both_oos_years: `false`
- combined_ai_profit_gte_seed: `false`
- combined_ai_max_mdd_lte_seed: `true`
- each_ai_oos_year_trade_count_gte_20: `false`
- combined_ai_oos_trade_count_gte_50: `false`
- candidate_identity_matches_p5: `true`
- no_oos_reselection: `true`

## Trade-Count Sufficiency
- Failed. AI 2022 has 24 trades, AI 2026 has 7 trades, and combined AI OOS trades are 31, below the predeclared 50-trade combined minimum.

## Slippage Status
- Not run. Promotion requires slippage-stressed positive OOS in both 2022 and 2026.
- Because unstressed AI 2022 OOS profit is already negative, slippage stress is not the deciding blocker for rejection; it remains mandatory for any future promotion claim.

## PBO/DSR Status
- Not run. Repository search found PBO/DSR documented as an advisory blocker and future work, not as an implemented promotion gate/tool in this path.
- Because this candidate already fails fixed OOS, missing PBO/DSR does not change the rejection; it still blocks any future human-level or promotion claim.

## Forbidden Actions Check
- `final_approval`: not invoked.
- `export_winner`: not invoked.
- Production strategy DB writes: not invoked.
- Live broker / KHOPENAPI / V3K gate advancement: not invoked.
- `taskkill`: not used.
- Official backtest engine edits: not performed.
- Hard-gate edits: not performed.
- `backtest/graph` edits: not performed.

## Final Verdict
- Final Verdict: `REJECT_CANDIDATE`
- The prompt improvement produced a genuine OOS-blind sparse-positive training candidate, which is a meaningful process improvement.
- The candidate does not beat the human seed/reference across fixed OOS and must not be promoted.

## Next Research Direction
- Keep `sparse_positive_prompt_enabled` default OFF.
- Use the P5 gen4/gen5 shape as evidence that generation guidance can find sparse-positive training rows.
- Next plan should improve OOS robustness, especially 2022 regime transfer and minimum trade sufficiency, without changing hard gates or selecting after OOS.
