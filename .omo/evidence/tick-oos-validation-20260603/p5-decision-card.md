# P5 Decision Card

- timestamp: 2026-06-03T21:23:11.788286+09:00
- scope: TICK toggles-ON multiyear run plus fixed 2022/2026 OOS audit

## Executive Verdict

The fixed AI candidate is rejected by evidence. The infrastructure can run the loop and dashboard analysis, but this candidate does not prove human-level or seed-superior condition generation.

## Candidate Identity

- source: `.omo/evidence/tick-oos-validation-20260603/p2-selected-candidate.json`
- selected_generation: 4
- buy_name: `AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_buy`
- sell_name: `AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_sell`
- selection_rule: highest completed P2 graded score before OOS
- training_gate_passed: False
- training_gate_reason: total_profit -6.971e+05 <= 0

## Training Evidence

- P2 2023~2025 selected gen 4 score 0.282929, profit -697,147, MDD 19.75, trades 182.
- P2 produced no winner. The selected candidate was gate-false and negative-profit in training.
- P3 confirmed analysis endpoints work, but stored prompt/log evidence did not prove segment-feedback avoid guidance was actually injected in P2 prompts.

## OOS Evidence

| Candidate | Period | Gate | Final Profit | MDD % | Max Drawdown | Trades | Peak Holdings |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| seed_2022 | 20220101~20221231 | True | 2,223,554 | 13.02 | 745,152 | 58 | 2 |
| seed_2026 | 20260101~20260228 | False | -191,109 | 15.63 | 891,842 | 10 | 1 |
| ai_2022 | 20220101~20221231 | True | 248,274 | 3.22 | 168,967 | 10 | 1 |
| ai_2026 | 20260101~20260228 | False | -80,344 | 1.61 | 0 | 1 | 1 |

## Seed Comparison

- p4_classification: `fails_seed`
- seed_combined_final_profit: 2,032,445
- ai_combined_final_profit: 167,930
- ai_all_positive: False
- ai_profit_ge_seed: False
- ai_drawdown_le_seed: True
- Result: the AI candidate fails the fixed seed-superiority rule because 2026 AI OOS is negative and combined AI OOS profit is far below seed combined OOS profit.

## Human Reference Corridor

- Reference condition: Tick_902 seed pair `Tick_B_902_905_Update_2` / `Tick_S_902_905_Update_2`.
- Seed OOS corridor observed here: 2022 positive and gate-true, 2026 partial negative and gate-false, combined profit still materially positive.
- AI profile: fewer trades and lower drawdown, but lower combined profit and a negative 2026 OOS row. This is not human-reference superiority.
- Caveat: seed configs preserve the existing 09:00~09:28 universe; AI configs use requested 09:00~09:30. This does not rescue the AI result because it fails on profit and 2026 sign under its own fixed evaluation.

## Overfit Risk

- PBO/DSR status: `advisory_blocker`; existing evidence did not include a formal PBO or DSR implementation run.
- Overfit indicators: P1 short-window success did not survive multiyear training, P2 selected candidate was training-negative, and P3 could not prove segment-feedback prompt injection.
- OOS split was respected: 2022 and 2026 were not used to choose a new candidate after P2.

## Slippage/Execution Stress

- Method: trade-level notional fields were unavailable, so this uses an advisory proxy of 5,000,000 KRW per round-trip from `bt_betting="5"`.
| Haircut | AI 2022 | AI 2026 | AI Combined | Seed 2022 | Seed 2026 | Seed Combined |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.1% | 198,274 | -85,344 | 112,930 | 1,933,554 | -241,109 | 1,692,445 |
| 0.2% | 148,274 | -90,344 | 57,930 | 1,643,554 | -291,109 | 1,352,445 |
| 0.3% | 98,274 | -95,344 | 2,930 | 1,353,554 | -341,109 | 1,012,445 |
- Slippage conclusion: AI 2026 is already negative before stress, so slippage stress cannot support promotion.

## Forbidden Actions Check

- Dashboard/export boundary was not invoked.
- No production strategy DB wiring, V3K gate advancement, USER_ACK, KHOPENAPI login/connect, live order wiring, or blanket taskkill was used.
- Runtime DB changes came from official loop executions only; source engines/hard gates/backtest graph were not edited.

## Final Verdict

Final Verdict: REJECT_CANDIDATE
