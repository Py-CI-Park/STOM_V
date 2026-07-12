# 2026-07-05 P5 official min preflight4 handoff

## Scope

Selected range: `P5-official-min-preflight4-readiness`.
Only min official warm64 preflight4 was executed. Full min 288, P6/P7, Plan D, OOS, survivor promotion, and DB UPDATE/DELETE were not executed.

## Inputs

| Item | Value |
| --- | --- |
| pair file | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_min_preflight4_official_full_warm64_20260705.json` |
| run_id | `lat_min_preflight4_official_full_warm64_20260705` |
| config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json` |
| log | `artifacts/p5_min_preflight4_20260705.log` |
| receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_preflight4_official_full_warm64_20260705_receipt.json` |

## Official profile check

| Field | Value |
| --- | --- |
| lane | `min` |
| DB full period | `20250407~20260227` |
| warm engines | `64` |
| time window | `90000~151900` |
| warm timeout | `1200s` |
| per-run timeout | `14400s` |

## Pair selection

The min preflight file uses the same boundary sample policy as official tick preflight4: source indices `0, 96, 192, 287` from `pairs_min.json`.

| index | label |
| ---: | --- |
| 0 | `lattice_v1:min_09h_small_low:momentum_breakout` |
| 96 | `lattice_v1:min_11h_small_low:momentum_breakout` |
| 192 | `lattice_v1:min_14h_small_low:momentum_breakout` |
| 287 | `lattice_v1:min_1430p_large_high:volume_surge` |

## Runtime result

| Metric | Value |
| --- | --- |
| exit_code | `0` |
| warm prepare | `ok` |
| warm back_count | `1379` |
| warm elapsed | `129s` |
| total runtime | `4.8m` |
| stderr | `empty` |
| DB run status | `complete` |
| recorded rows | `4/4` |
| honest rows | `True` |
| status_counts | `{'ok': 3, 'error': 1}` |
| gate_passed | `0` |

## Row summary

| gen | status | gate | profit | mdd | trades | daily | reason |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 0 | `ok` | `False` | 709,986 | 5.74 | 15 | 0.1 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| 1 | `ok` | `False` | -150,190 | 3.0 | 1 | 0.0 | `daily_avg_trades 0 < min_daily_trades 0.5` |
| 2 | `error` | `False` | 0 | 0.0 | 0 | 0.0 | `[lattice_v1:min_14h_small_low:momentum_breakout] backtest failed: warm backtest non-success: status=error message=backtest completed without metrics csv=no metrics=no` |
| 3 | `ok` | `False` | -6,842,267 | 36.37 | 508 | 2.4 | `mdd 36.37 > mdd_cap 35` |

## Decision

Decision: `possible_but_chunked_only`.

Reason: official min warm64 prepare succeeded and 4/4 rows were recorded, so the min execution surface is usable. But one row is a raw `csv=no/metrics=no` error and no row passed the gate. Therefore do not start a monolithic 288 run. If continuing, create a 24-pair min chunk manifest and run chunk01 only first, with per-chunk status/error monitoring.

## Next allowed command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 P5-official-min-chunk01-only까지 진행한다.
목표는 공식 min warm64 24-pair chunk manifest를 생성하고 chunk01만 실행해 min full coverage batch를 열 수 있는지 재확인하는 것이다.

금지:
- chunk02+ 선행 금지
- P6/P7/Plan D 실행 금지
- OOS 실행 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
```
