# 2026-07-05 P5 official tick export summary and min readiness

## Scope

Selected range: `P5-official-tick-export-summary-and-min-readiness`.
No min run, P6, P7, Plan D, OOS, promotion, or DB UPDATE/DELETE was executed.

## Source evidence

- row export JSONL: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.jsonl`
- summary JSON: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json`
- coverage receipt: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_coverage_20260705_receipt.json`

## Overall result

| Metric | Value |
| --- | --- |
| `rows` | `288` |
| `unique_pairs` | `288` |
| `status_counts` | `{'ok': 288}` |
| `gate_passed_count` | `0` |
| `mdd_excess_count` | `287` |
| `low_daily_trades_count` | `9` |
| `negative_profit_count` | `288` |
| `payoff_below_target_count` | `286` |
| `profit_range` | `-692,611,103 ~ -899,093` |
| `mdd_range` | `16.88 ~ 1558.72` |
| `daily_avg_trades_range` | `0.1 ~ 29.3` |

## Primary failure decomposition

| Primary fail | Count |
| --- | ---: |
| `mdd_excess` | 279 |
| `mdd_excess_and_low_daily_trades` | 8 |
| `low_daily_trades` | 1 |

## Axis summary: time_bucket

| time_bucket | count | gate_passed | mdd_excess_count | low_daily_trades_count | negative_profit_count | avg_profit | avg_mdd | avg_daily_trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0900 | 48 | 0 | 48 | 0 | 48 | -230,679,601 | 714.3225 | 8.7 |
| 0905 | 48 | 0 | 48 | 0 | 48 | -187,524,416 | 594.4494 | 7.5333 |
| 0910 | 48 | 0 | 48 | 1 | 48 | -166,897,690 | 542.444 | 6.6437 |
| 0915 | 48 | 0 | 48 | 1 | 48 | -143,739,890 | 466.0485 | 6.0729 |
| 0920 | 48 | 0 | 48 | 2 | 48 | -136,895,150 | 453.475 | 5.7833 |
| 0925 | 48 | 0 | 47 | 5 | 48 | -72,988,353 | 302.5979 | 3.1583 |

## Axis summary: size

| size | count | gate_passed | mdd_excess_count | low_daily_trades_count | negative_profit_count | avg_profit | avg_mdd | avg_daily_trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| large | 72 | 0 | 72 | 0 | 72 | -189,985,544 | 380.5468 | 9.3486 |
| midlarge | 72 | 0 | 72 | 0 | 72 | -154,796,180 | 498.1585 | 6.2583 |
| midsmall | 72 | 0 | 72 | 2 | 72 | -129,984,672 | 547.1064 | 4.8486 |
| small | 72 | 0 | 71 | 7 | 72 | -151,050,337 | 623.0799 | 4.8056 |

## Axis summary: strength

| strength | count | gate_passed | mdd_excess_count | low_daily_trades_count | negative_profit_count | avg_profit | avg_mdd | avg_daily_trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high | 96 | 0 | 96 | 0 | 96 | -145,237,639 | 654.9718 | 4.974 |
| low | 96 | 0 | 95 | 8 | 96 | -157,685,300 | 403.3342 | 6.9854 |
| mid | 96 | 0 | 96 | 1 | 96 | -166,439,611 | 478.3627 | 6.9865 |

## Axis summary: family

| family | count | gate_passed | mdd_excess_count | low_daily_trades_count | negative_profit_count | avg_profit | avg_mdd | avg_daily_trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| momentum_breakout | 72 | 0 | 71 | 6 | 72 | -62,581,283 | 330.8535 | 3.2167 |
| prevday_active | 72 | 0 | 72 | 0 | 72 | -227,926,003 | 620.8604 | 8.7236 |
| strength_surge | 72 | 0 | 72 | 3 | 72 | -113,525,579 | 483.5815 | 4.7639 |
| volume_surge | 72 | 0 | 72 | 0 | 72 | -221,783,868 | 613.5961 | 8.5569 |

## Best and worst diagnostics

### Least loss rows

| strategy_gist | profit | mdd | daily_avg_trades | primary_fail |
| --- | --- | --- | --- | --- |
| lattice_v1:tick_0925_small_low:momentum_breakout | -899,093 | 16.88 | 0.1 | low_daily_trades |
| lattice_v1:tick_0920_small_low:momentum_breakout | -2,497,875 | 53.41 | 0.1 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0925_midsmall_low:momentum_breakout | -4,664,038 | 94.36 | 0.3 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0925_small_low:strength_surge | -5,605,509 | 112.33 | 0.2 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0915_small_low:momentum_breakout | -5,690,521 | 116.59 | 0.2 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0925_small_mid:momentum_breakout | -6,566,559 | 131.69 | 0.3 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0910_small_low:momentum_breakout | -9,158,599 | 181.44 | 0.4 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0920_midsmall_low:momentum_breakout | -9,309,338 | 192.73 | 0.5 | mdd_excess |

### Lowest MDD rows

| strategy_gist | profit | mdd | daily_avg_trades | primary_fail |
| --- | --- | --- | --- | --- |
| lattice_v1:tick_0925_small_low:momentum_breakout | -899,093 | 16.88 | 0.1 | low_daily_trades |
| lattice_v1:tick_0920_small_low:momentum_breakout | -2,497,875 | 53.41 | 0.1 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0925_midsmall_low:momentum_breakout | -4,664,038 | 94.36 | 0.3 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0925_small_low:strength_surge | -5,605,509 | 112.33 | 0.2 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0915_small_low:momentum_breakout | -5,690,521 | 116.59 | 0.2 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0925_small_mid:momentum_breakout | -6,566,559 | 131.69 | 0.3 | mdd_excess_and_low_daily_trades |
| lattice_v1:tick_0925_large_high:momentum_breakout | -14,777,556 | 149.78 | 0.8 | mdd_excess |
| lattice_v1:tick_0910_small_low:momentum_breakout | -9,158,599 | 181.44 | 0.4 | mdd_excess_and_low_daily_trades |

## Root-cause judgment

Verdict: `condition_structure_is_primary_with_strict_gate_and_tick_lane_as_secondary_filters`.

- Backtest/export path is healthy: `ok=288`, unique pairs `288`, no missing rows.
- Gate criteria are strict, but not the only issue: `negative_profit_count=288`, so relaxing MDD/daily-trade alone would not create a promotion candidate.
- MDD is the dominant hard failure: `mdd_excess_count=287`. Low daily trades is secondary: `low_daily_trades_count=9`.
- Current tick lattice should be treated as coverage/failure-regime evidence, not survivor evidence.

## Min readiness

| Item | Value |
| --- | --- |
| decision | `possible_but_preflight_first` |
| should_run_min_now | `False` |
| min_pair_count | `288` |
| min_config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json` |
| min_pairs | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_min.json` |
| profile | `{'bt_timeframe': 'min', 'bt_full_start': 20250407, 'bt_full_end': 20260227, 'bt_warm_engine_count': 64, 'bt_universe_start_time': 90000, 'bt_min_universe_end_time': 151900, 'bt_warm_run_timeout': 1200, 'bt_timeout': 14400}` |

Recommendation: min is technically ready, but do not start full 288 directly. Start with an official warm64 min preflight4, then decide chunking. The preferred full-run pattern after a clean preflight is 24-pair chunks, not a monolithic 288 run.

## Next command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md


Range: P5-official-min-preflight4-readiness only.
Goal: create the official min warm64 preflight4 pair file, run only min preflight4,
and judge whether full min 288 execution can be opened.

Forbidden:
- Do not run full min 288.
- Do not run P6/P7/Plan D.
- Do not run OOS.
- Do not use DB UPDATE/DELETE.
- Do not use git add -A.
```
