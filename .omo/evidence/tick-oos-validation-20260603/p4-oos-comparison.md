# P4 OOS Comparison

- timestamp: 2026-06-03T21:20:33.624113+09:00
- fixed_ai_candidate: gen 4 `AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_buy` / `AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_sell`
- classification: `fails_seed`
- superiority_rule_passed: `False`

## OOS Rows

| Label | Period | Time | Gate | Final Profit | MDD % | Max Drawdown | Trades | Daily Avg | Peak Holdings | Edge Ratio | Source Config |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| seed_2022 | 20220101~20221231 | 90000-92800 | True | 2,223,554 | 13.02 | 745,152 | 58 | 0.3 | 2 | 1.7746 | `.omo/evidence/tick-oos-validation-20260603/p4-seed-2022-config.json` |
| seed_2026 | 20260101~20260228 | 90000-92800 | False | -191,109 | 15.63 | 891,842 | 10 | 0.3 | 1 | 0.9722 | `.omo/evidence/tick-oos-validation-20260603/p4-seed-2026-config.json` |
| ai_2022 | 20220101~20221231 | 90000-93000 | True | 248,274 | 3.22 | 168,967 | 10 | 0.1 | 1 | 2.1036 | `.omo/evidence/tick-oos-validation-20260603/p4-ai-2022-config.json` |
| ai_2026 | 20260101~20260228 | 90000-93000 | False | -80,344 | 1.61 | 0 | 1 | 0.0 | 1 | 0.0000 | `.omo/evidence/tick-oos-validation-20260603/p4-ai-2026-config.json` |

## Combined Rule Check

- seed_combined_final_profit: 2,032,445
- ai_combined_final_profit: 167,930
- seed_max_drawdown_max: 891,842
- ai_max_drawdown_max: 168,967
- ai_all_positive: False
- ai_profit_ge_seed: False
- ai_drawdown_le_seed: True

## Classification

`fails_seed`

The AI candidate fails the predeclared seed-superiority rule: 2026 OOS is negative and combined AI OOS profit is materially below seed combined OOS profit. Candidate identity remained locked to the P2 selected gen4 pair.

## Caveats

- Seed configs preserve existing seed profile universe end 09:28; AI configs use the requested 09:00~09:30 universe from the P2 objective.
- 2026 window is partial: 20260101~20260228 from the seed profile config.
- P2 selected candidate was gate-false and negative-profit in training; OOS was still run only as fixed audit evidence.
