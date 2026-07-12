# 2026-07-05 P5 official min chunk01 handoff

## Scope

Selected range: `P5-official-min-chunk01-only`.
The official min 24-pair chunk manifest was generated and only chunk01 was executed. Chunk02+, full min export, P6/P7, Plan D, OOS, survivor promotion, and DB UPDATE/DELETE were not executed.

## Inputs

| Item | Value |
| --- | --- |
| manifest | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_full_run_protocol_after_preflight_20260705.json` |
| chunk01 pair file | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_min_official_full_warm64_chunk01_20260705.json` |
| run_id | `lat_min_official_full_warm64_chunk01_20260705` |
| config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json` |
| receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunk01_official_full_warm64_20260705_receipt.json` |

## Official profile

| Field | Value |
| --- | --- |
| lane | `min` |
| DB full period | `20250407~20260227` |
| warm engines | `64` |
| time window | `90000~151900` |
| warm timeout | `1200s` |
| per-run timeout | `14400s` |

## Runtime result

| Metric | Value |
| --- | --- |
| exit_code | `0` |
| warm prepare | `ok` |
| warm back_count | `1379` |
| warm elapsed | `121s` |
| total runtime | `11.4m` |
| DB run status | `complete` |
| recorded rows | `24/24` |
| status_counts | `{'ok': 24}` |
| gate_passed | `0` |
| profit_range | `-72,210,271~819,969` |
| mdd_range | `5.74~287.05` |
| daily_avg_trades_range | `0.1~7.1` |

## Failure decomposition

| Primary reason | Count |
| --- | ---: |
| mdd_excess | 18 |
| low_daily_trades | 5 |
| nonpositive_profit | 1 |
| other | 0 |

## Row summary

| gen | official_index | status | gate | profit | mdd | trades | daily | reason |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 0 | 0 | `ok` | `False` | 709,986 | 5.74 | 15 | 0.1 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| 1 | 1 | `ok` | `False` | -8,646,892 | 64.56 | 286 | 1.3 | `mdd 64.56 > mdd_cap 35` |
| 2 | 2 | `ok` | `False` | -1,042,388 | 21.93 | 16 | 0.1 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| 3 | 3 | `ok` | `False` | -2,282,808 | 60.44 | 97 | 0.5 | `mdd 60.44 > mdd_cap 35` |
| 4 | 4 | `ok` | `False` | -2,521,104 | 53.21 | 42 | 0.2 | `daily_avg_trades 0.2 < min_daily_trades 0.5` |
| 5 | 5 | `ok` | `False` | -16,898,674 | 89.89 | 611 | 2.9 | `mdd 89.89 > mdd_cap 35` |
| 6 | 6 | `ok` | `False` | -2,128,091 | 52.37 | 115 | 0.5 | `mdd 52.37 > mdd_cap 35` |
| 7 | 7 | `ok` | `False` | -8,056,433 | 177.42 | 176 | 0.8 | `mdd 177.4 > mdd_cap 35` |
| 8 | 8 | `ok` | `False` | -16,346,965 | 287.05 | 251 | 1.2 | `mdd 287.1 > mdd_cap 35` |
| 9 | 9 | `ok` | `False` | -72,210,271 | 203.36 | 1503 | 7.1 | `mdd 203.4 > mdd_cap 35` |
| 10 | 10 | `ok` | `False` | -21,038,284 | 140.5 | 526 | 2.5 | `mdd 140.5 > mdd_cap 35` |
| 11 | 11 | `ok` | `False` | -26,838,290 | 261.26 | 530 | 2.5 | `mdd 261.3 > mdd_cap 35` |
| 12 | 12 | `ok` | `False` | -973,095 | 22.69 | 24 | 0.1 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| 13 | 13 | `ok` | `False` | -11,426,181 | 86.22 | 377 | 1.8 | `mdd 86.22 > mdd_cap 35` |
| 14 | 14 | `ok` | `False` | 819,969 | 15.91 | 47 | 0.2 | `daily_avg_trades 0.2 < min_daily_trades 0.5` |
| 15 | 15 | `ok` | `False` | -3,611,071 | 102.03 | 105 | 0.5 | `mdd 102 > mdd_cap 35` |
| 16 | 16 | `ok` | `False` | -4,097,595 | 93.64 | 110 | 0.5 | `mdd 93.64 > mdd_cap 35` |
| 17 | 17 | `ok` | `False` | -27,685,302 | 111.94 | 754 | 3.5 | `mdd 111.9 > mdd_cap 35` |
| 18 | 18 | `ok` | `False` | -2,749,462 | 34.04 | 259 | 1.2 | `total_profit -2.749e+06 <= 0` |
| 19 | 19 | `ok` | `False` | -9,363,748 | 94.14 | 270 | 1.3 | `mdd 94.14 > mdd_cap 35` |
| 20 | 20 | `ok` | `False` | -17,103,396 | 167.56 | 333 | 1.6 | `mdd 167.6 > mdd_cap 35` |
| 21 | 21 | `ok` | `False` | -52,213,930 | 201.8 | 1189 | 5.6 | `mdd 201.8 > mdd_cap 35` |
| 22 | 22 | `ok` | `False` | -23,185,140 | 156.01 | 655 | 3.1 | `mdd 156 > mdd_cap 35` |
| 23 | 23 | `ok` | `False` | -26,505,715 | 254.12 | 497 | 2.3 | `mdd 254.1 > mdd_cap 35` |

## Decision

Decision: `clean_coverage_no_survivor`.

Chunk01 is clean coverage evidence: `24/24 ok`, no raw error, no missing row. It does not create a survivor because `gate_passed=0`. The next allowed action is chunk02 only. P6/P7/Plan D remain blocked until official min 288 coverage and export exist.

## Next allowed command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

??? P5-official-min-chunk02-only?? ????.
??? ?? min warm64 chunk02? ??? min 48/288 coverage? ????, chunk03 ?? ?? ??? ???? ???.

??:
- chunk03+ ?? ??
- P6/P7/Plan D ?? ??
- OOS ?? ??
- DB UPDATE/DELETE ??
- git add -A ??
```
