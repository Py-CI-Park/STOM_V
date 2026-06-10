# P4 Dashboard Research Analysis

## Scope
- Run: `tick_oos_dash_p3_train_2023_2025_20260604`
- Selected gen: `4`, fixed by P3 pre-OOS graded-score rule.
- Period: `2023-01-01 ~ 2025-12-31`, timeframe `tick`, window `09:00~09:30`.
- Dashboard base used for evidence: `http://127.0.0.1:8799` (owned PID 48668).
- No new training run, no `final_approval`, no `export_winner`.

## Candidate State
- gen4 graded_score=0.35558047094767675, gate_passed=False, gate_reason=`total_profit -6.719e+04 <= 0`
- profit=-67,190, total_profit_pct=-1.34, MDD=23.52, trades=287, daily_avg_trades=0.4
- Winner is `null`; this is not a promotion candidate from training alone.

## Global Edge
- pooled_trades=7967, win_rate=0.4672, avg_return=-0.1820, total_profit=-72,411,833
- mean_mfe=1.2523, mean_mae=1.2403, edge_ratio=1.0097, mae_efficiency=-0.1453
- Interpretation: edge_ratio is near 1, but avg_return and total_profit remain negative, so exit/entry timing does not yet produce a durable positive edge.

## Losing Segments
- cross / 0910-0915×소형: count=1116, win_rate=0.4409, avg_return=-0.3367, total_profit=-18,787,429, edge_ratio=0.8740
- change / 초급등: count=755, win_rate=0.4821, avg_return=-0.3080, total_profit=-11,622,718, edge_ratio=1.0096
- time / 0910-0915: count=2344, win_rate=0.4492, avg_return=-0.2982, total_profit=-34,921,215, edge_ratio=0.8531
- cross / 0910-0915×중형: count=1228, win_rate=0.4568, avg_return=-0.2632, total_profit=-16,133,786, edge_ratio=0.8328
- change / 급등: count=3172, win_rate=0.4530, avg_return=-0.2027, total_profit=-32,082,361, edge_ratio=0.9992

## Least-Bad / Winning Segments
- No segment in the captured top list has positive avg_return; entries below are least negative, not true winners.
- change / 약상승: count=873, win_rate=0.4754, avg_return=-0.1067, total_profit=-4,653,501, edge_ratio=1.0063
- cross / 0905-0910×중형: count=2914, win_rate=0.4780, avg_return=-0.1327, total_profit=-19,295,763, edge_ratio=1.0940
- time / 0905-0910: count=5623, win_rate=0.4747, avg_return=-0.1335, total_profit=-37,490,618, edge_ratio=1.0861
- cross / 0905-0910×소형: count=2709, win_rate=0.4710, avg_return=-0.1345, total_profit=-18,194,855, edge_ratio=1.0786
- change / 상승: count=3167, win_rate=0.4755, avg_return=-0.1520, total_profit=-24,053,253, edge_ratio=1.0227

## Variable Signals
- Top outcome correlations from `/variable_correlation?method=spearman`:
  - B_회전율: corr=-0.0715, abs=0.0715, n=7967
  - B_체결강도: corr=0.0674, abs=0.0674, n=7967
  - B_시분초: corr=-0.0526, abs=0.0526, n=7967
  - B_당일거래대금: corr=-0.0475, abs=0.0475, n=7967
  - B_등락율: corr=-0.0430, abs=0.0430, n=7967
- Top feature-importance differences from `/feature_importance?axis=change&fine_time=true`:
  - B_시분초: cohens_d=-0.0773, win_rate_top_q=0.4447, win_rate_bot_q=0.5005, n=7967
  - B_체결강도: cohens_d=0.0642, win_rate_top_q=0.4789, win_rate_bot_q=0.4431, n=7967
  - B_거래대금증감: cohens_d=-0.0634, win_rate_top_q=0.4478, win_rate_bot_q=0.4804, n=7967
  - B_시가총액: cohens_d=0.0472, win_rate_top_q=0.4807, win_rate_bot_q=0.4558, n=7967
  - B_매도총잔량: cohens_d=-0.0222, win_rate_top_q=0.4588, win_rate_bot_q=0.4553, n=7967
- Signal strength is weak: largest absolute Spearman correlation is about 0.072, and largest |Cohen d| is about 0.077.

## Prompt And Feedback
- prompt_count=2, segment-feedback classification=`observed`.
- prompt_id=193 kind=buy has_segment_avoid=True has_few_shot=True require_filter_gates=True time_window_bounds=[90500, 90800]
- prompt_id=194 kind=sell has_segment_avoid=False has_few_shot=True require_filter_gates=True time_window_bounds=[92800, None]
- Segment feedback is observed on the buy prompt only; sell prompt does not show `has_segment_avoid=true`.

## Strategy / Context Availability
- strategy_diff: HTTP 200, bytes=9755, path `.omo\evidence\tick-oos-dashboard-validation-20260604\p4-raw\strategy_diff.json`
- ai_context_pack: period=2023-01-01 ~ 2025-12-31, prompt_count=2, verdict_note=`Final Verdict: REJECT_CANDIDATE; prior candidate remains rejected.`
- research_docs count=66; wiki and reference docs are available through `/research_docs`.

## Next-Run Implications
- Do not claim human-level or seed-superior performance from this P3/P4 evidence.
- The current rule family reduced loss from gen1 to gen4 and found a sparse positive gen5, but the fixed candidate gen4 is still training-negative.
- A future plan update could test a selection rule that considers gate distance and positive-profit sparse candidates, but this plan must keep gen4 fixed for OOS because P3 already selected it by the declared graded-score rule.
- The main failure modes to feed back are overtrading in weak segments, late 09:10~09:15 drawdown, weak variable edge, and insufficient segment feedback on sell logic.
