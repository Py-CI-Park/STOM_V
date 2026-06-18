# P3 T1/T4 Analysis And Segment Feedback Evidence

- timestamp: 2026-06-03T21:00:07.898434+09:00
- p1_run: `tick_oos_p1_smoke_20260603`
- p2_run: `tick_oos_p2_train_2023_2025_20260603`
- selected_p2_candidate: gen 4 `AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_buy` / `AILOOP_tick_oos_p2_train_2023_2025_20260603_g4_sell`
- feedback_evidence_status: `needs_more_evidence_no_prompt_feedback_records`

## Training Reality Check

- P1 smoke had a short-window winner: graded_score 8.982558, gen 1, gate=True.
- P2 multiyear selected candidate is gate=False with score 0.282929, profit -697,147, MDD 19.75, trades 182.
- P2 selected candidate detail summary: final_profit -697,147.0, max_drawdown 927,371.0, n_days 135, peak_holdings 2.
- P2 produced no winner. Gen5 had positive training profit but was not selected by the predeclared highest-score rule and also failed the daily-trade gate; it must not replace gen4 after the fact.

## P2 Global Edge

- pooled_trades: 4166
- total_profit: -16,153,384.0
- win_rate: 0.4309
- edge_ratio: 1.0582
- mae_efficiency: -0.0484
- mean_mae_losers: 2.1221

## Top Losing Segments

| Axis | Label | Count | Total Profit | Win Rate | Edge Ratio | Avg Return |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| change | 초급등 | 1240 | -12,720,155 | 0.4315 | 0.9553 | -0.2051 |
| time | 0910-0915 | 1309 | -12,710,900 | 0.4011 | 0.9927 | -0.1944 |
| market_cap | 소형 | 2011 | -9,899,426 | 0.4267 | 1.0393 | -0.0985 |
| cross | 0910-0915×소형 | 618 | -7,351,319 | 0.3948 | 0.9691 | -0.2381 |
| market_cap | 중형 | 2155 | -6,253,958 | 0.4348 | 1.0776 | -0.0581 |
| cross | 0910-0915×중형 | 691 | -5,359,581 | 0.4067 | 1.0158 | -0.1552 |
| time | 0915-0920 | 1058 | -2,939,494 | 0.4338 | 1.0249 | -0.0554 |
| cross | 0915-0920×소형 | 525 | -1,479,160 | 0.4343 | 0.9881 | -0.0563 |
| cross | 0915-0920×중형 | 533 | -1,460,334 | 0.4334 | 1.0676 | -0.0546 |
| change | 급등 | 2122 | -1,412,000 | 0.4284 | 1.0924 | -0.0134 |

## Useful B_* Feature Axes

| Feature | Cohens d | Mean Win | Mean Lose | Top-Q Win Rate | Bottom-Q Win Rate | N |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B_거래대금증감 | -0.056471 | -109255909156.1226 | -100633301366.5858 | 0.4031 | 0.4309 | 4166 |
| B_시분초 | -0.055543 | 91112.0897 | 91136.5112 | 0.4362 | 0.4560 | 4166 |
| B_당일거래대금 | 0.042493 | 25557.3476 | 24804.5753 | 0.4464 | 0.4376 | 4166 |
| B_현재가 | 0.042021 | 16531.0836 | 16044.5049 | 0.4556 | 0.4027 | 4166 |
| B_회전율 | 0.030810 | 9.2812 | 9.0426 | 0.4458 | 0.4472 | 4166 |
| B_체결강도 | 0.030294 | 130.0721 | 129.1912 | 0.4347 | 0.4084 | 4166 |
| B_전일동시간비 | -0.029672 | 2245.3479 | 2915.6990 | 0.4376 | 0.4319 | 4166 |
| B_시가총액 | 0.022752 | 3754.2061 | 3704.4205 | 0.4443 | 0.4328 | 4166 |

## Segment Feedback Evidence

- Execution config evidence: `p2-train-config.json` has `segment_feedback_enabled=true`, `classification_generation_enabled=true`, `require_filter_gates=true`, `encourage_time_dispersion=true`, and few-shot seed DB enabled.
- Prompt DB evidence: table counts by run are `{'equity_points': 0, 'generations': 6, 'prompts': 0, 'runs': 1}`; prompt_count for P2 is 0, matches_count is 0.
- P2 log search evidence: no concrete `avoid`/`segment`/`feedback`/Korean segment-feedback marker tied to P2 was found in `p2-train-log.txt`.
- Adaptive timing endpoint returned error: `no csv_path for run_id='tick_oos_p2_train_2023_2025_20260603'`.

Conclusion: T1/T4 analysis endpoints are working and identify concrete losing cells, but this run does not provide concrete stored-prompt evidence that segment feedback guidance was actually injected. This is a `NEEDS_MORE_EVIDENCE` blocker for claiming T4 closed-loop feedback effectiveness, not a reason to fabricate closure.

## Follow-Up Hypotheses Only

- Avoid/tighten exposure in the worst P2 cells above, especially early 09:10-09:15 style time cells and weak market-cap/change crosses, in a future predeclared experiment.
- Because P2 selected gen4 is gate-false and negative-profit, P4 OOS should still use the predeclared selected candidate for audit integrity, but P5 should heavily penalize it unless OOS unexpectedly dominates seed under the fixed rules.
- Do not run additional generations inside this task. Extra generations would need a new predeclared plan because P4 must remain OOS evaluation, not tuning.
