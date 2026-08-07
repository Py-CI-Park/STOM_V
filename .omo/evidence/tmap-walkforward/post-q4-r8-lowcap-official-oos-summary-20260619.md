# Post-Q4 r8 Low-Cap Official OOS Summary

Generated: 2026-06-19

## Verdict

`r8_exclude_cap_lt_1500` completed wrapper-backed official OOS for Q4 stress and 2022-2025 full-year plus 2026 YTD periods. All six runs returned `status=ok` and `gate_passed=true`.

This is **공식 OOS for the r8 low-cap entry filter only**. The combined robust candidate still needs a separately labeled portfolio-layer report for `exit2_skip_after_prior_exit2_loss_500k_else_full`.

## Coverage Caveat

2026 is **YTD through 2026-02-28**, not a full-year 2026 OOS period. The aggregate label is `2022-2025 full-year + 2026 YTD`.

## Results

| Period | Date Window | Status | Gate | Profit KRW | MDD % | Trades | Daily Avg | Payoff | Elapsed s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2025 Q4 stress (2025-10-01~2025-12-31) | 20251001~20251231 | ok | true | 310,886 | 9.25 | 19 | 0.30 | 1.419 | 105.333 |
| 2022 full-year | 20220101~20221231 | ok | true | 1,766,684 | 7.30 | 31 | 0.20 | 1.294 | 158.044 |
| 2023 full-year | 20230101~20231231 | ok | true | 1,931,859 | 12.66 | 74 | 0.30 | 1.613 | 186.133 |
| 2024 full-year | 20240101~20241231 | ok | true | 1,372,394 | 16.15 | 65 | 0.30 | 1.960 | 177.034 |
| 2025 full-year | 20250101~20251231 | ok | true | 1,337,712 | 19.09 | 81 | 0.30 | 1.306 | 181.595 |
| 2026 YTD (2026-01-01~2026-02-28) | 20260101~20260228 | ok | true | 884,212 | 5.29 | 12 | 0.40 | 1.516 | 103.271 |

## Aggregate

- Coverage: 2022-2025 full-year + 2026 YTD
- Total profit: 7,292,861 KRW
- Total trades: 263
- Worst period MDD: 19.09%
- Gates passed: true

## Evidence

- Raw/observed log manifest: `.omo/evidence/tmap-walkforward/post-q4-oos-logs-20260619/manifest.json`
- Process cleanup evidence: `.omo/evidence/tmap-walkforward/post-q4-oos-process-cleanup-20260619.json`
- 2025 Q4 stress (2025-10-01~2025-12-31): `.omo/evidence/tmap-walkforward/post-q4-oos-snapshots-20260619/post_q4_r8_lowcap_oos_2025q4_20260619_g0.json`; runner CSV `backtest/csv\stock_bt_POSTQ4_r8_exclude_cap_lt_1500_B_20260619143831.csv`
- 2022 full-year: `.omo/evidence/tmap-walkforward/post-q4-oos-snapshots-20260619/post_q4_r8_lowcap_oos_2022_20260619_g0.json`; runner CSV `backtest/csv\stock_bt_POSTQ4_r8_exclude_cap_lt_1500_B_20260619144144.csv`
- 2023 full-year: `.omo/evidence/tmap-walkforward/post-q4-oos-snapshots-20260619/post_q4_r8_lowcap_oos_2023_20260619_g0.json`; runner CSV `backtest/csv\stock_bt_POSTQ4_r8_exclude_cap_lt_1500_B_20260619144503.csv`
- 2024 full-year: `.omo/evidence/tmap-walkforward/post-q4-oos-snapshots-20260619/post_q4_r8_lowcap_oos_2024_20260619_g0.json`; runner CSV `backtest/csv\stock_bt_POSTQ4_r8_exclude_cap_lt_1500_B_20260619144816.csv`
- 2025 full-year: `.omo/evidence/tmap-walkforward/post-q4-oos-snapshots-20260619/post_q4_r8_lowcap_oos_2025_20260619_g0.json`; runner CSV `backtest/csv\stock_bt_POSTQ4_r8_exclude_cap_lt_1500_B_20260619145135.csv`
- 2026 YTD (2026-01-01~2026-02-28): `.omo/evidence/tmap-walkforward/post-q4-oos-snapshots-20260619/post_q4_r8_lowcap_oos_2026_20260619_g0.json`; runner CSV `backtest/csv\stock_bt_POSTQ4_r8_exclude_cap_lt_1500_B_20260619145342.csv`

## Next

Build the portfolio-layer report that combines this official r8 OOS evidence with the causal prior-month exit2 rule. Keep the combined candidate labeled as `공식 OOS + 포트폴리오 규칙 조합`.
