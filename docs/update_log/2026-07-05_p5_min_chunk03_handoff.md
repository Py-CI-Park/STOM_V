# 2026-07-05 P5 official min chunk03 handoff

## Scope

Selected range: `P5-official-min-chunk03-only`.
Only official min warm64 chunk03 was executed. Chunk04+, full min export, P6/P7, Plan D, OOS, survivor promotion, and DB UPDATE/DELETE were not executed.

## Inputs

| Item | Value |
| --- | --- |
| manifest | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_full_run_protocol_after_preflight_20260705.json` |
| chunk03 pair file | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_min_official_full_warm64_chunk03_20260705.json` |
| run_id | `lat_min_official_full_warm64_chunk03_20260705` |
| config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json` |
| receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunk03_official_full_warm64_20260705_receipt.json` |

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
| warm elapsed | `110s` |
| total runtime | `10.9m` |
| DB run status | `complete` |
| recorded rows | `24/24` |
| status_counts | `{'ok': 24}` |
| gate_passed | `0` |
| coverage | `72/288` |
| profit_range | `-90,894,637~608,514` |
| mdd_range | `6.0~227.57` |
| daily_avg_trades_range | `0.0~8.8` |

## Failure decomposition

| Primary reason | Count |
| --- | ---: |
| mdd_excess | 17 |
| low_daily_trades | 7 |
| nonpositive_profit | 0 |
| other | 0 |

## Row summary

| gen | official_index | status | gate | profit | mdd | trades | daily | reason |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 0 | 48 | `ok` | `False` | 155,985 | 8.41 | 14 | 0.1 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| 1 | 49 | `ok` | `False` | -6,463,446 | 47.55 | 313 | 1.5 | `mdd 47.55 > mdd_cap 35` |
| 2 | 50 | `ok` | `False` | -56,950 | 6.3 | 7 | 0.0 | `daily_avg_trades 0 < min_daily_trades 0.5` |
| 3 | 51 | `ok` | `False` | -9,965,429 | 99.62 | 184 | 0.9 | `mdd 99.62 > mdd_cap 35` |
| 4 | 52 | `ok` | `False` | -4,465,747 | 88.94 | 43 | 0.2 | `daily_avg_trades 0.2 < min_daily_trades 0.5` |
| 5 | 53 | `ok` | `False` | -21,893,330 | 90.56 | 734 | 3.4 | `mdd 90.56 > mdd_cap 35` |
| 6 | 54 | `ok` | `False` | -4,477,751 | 89.86 | 77 | 0.4 | `daily_avg_trades 0.4 < min_daily_trades 0.5` |
| 7 | 55 | `ok` | `False` | -16,198,784 | 111.98 | 394 | 1.8 | `mdd 112 > mdd_cap 35` |
| 8 | 56 | `ok` | `False` | -19,844,724 | 200.21 | 308 | 1.4 | `mdd 200.2 > mdd_cap 35` |
| 9 | 57 | `ok` | `False` | -90,894,637 | 227.57 | 1874 | 8.8 | `mdd 227.6 > mdd_cap 35` |
| 10 | 58 | `ok` | `False` | -22,341,749 | 149.54 | 464 | 2.2 | `mdd 149.5 > mdd_cap 35` |
| 11 | 59 | `ok` | `False` | -47,555,666 | 190.52 | 1001 | 4.7 | `mdd 190.5 > mdd_cap 35` |
| 12 | 60 | `ok` | `False` | 608,514 | 6.0 | 16 | 0.1 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| 13 | 61 | `ok` | `False` | -9,857,855 | 75.66 | 395 | 1.9 | `mdd 75.66 > mdd_cap 35` |
| 14 | 62 | `ok` | `False` | 473,145 | 14.23 | 20 | 0.1 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| 15 | 63 | `ok` | `False` | -6,297,889 | 72.27 | 279 | 1.3 | `mdd 72.27 > mdd_cap 35` |
| 16 | 64 | `ok` | `False` | -2,688,737 | 87.9 | 82 | 0.4 | `daily_avg_trades 0.4 < min_daily_trades 0.5` |
| 17 | 65 | `ok` | `False` | -22,694,791 | 91.12 | 796 | 3.7 | `mdd 91.12 > mdd_cap 35` |
| 18 | 66 | `ok` | `False` | -3,562,603 | 36.97 | 171 | 0.8 | `mdd 36.97 > mdd_cap 35` |
| 19 | 67 | `ok` | `False` | -16,493,556 | 112.44 | 486 | 2.3 | `mdd 112.4 > mdd_cap 35` |
| 20 | 68 | `ok` | `False` | -18,368,712 | 183.04 | 369 | 1.7 | `mdd 183 > mdd_cap 35` |
| 21 | 69 | `ok` | `False` | -61,954,314 | 206.04 | 1440 | 6.8 | `mdd 206 > mdd_cap 35` |
| 22 | 70 | `ok` | `False` | -24,267,662 | 161.38 | 592 | 2.8 | `mdd 161.4 > mdd_cap 35` |
| 23 | 71 | `ok` | `False` | -34,180,538 | 172.21 | 840 | 3.9 | `mdd 172.2 > mdd_cap 35` |

## Decision

Decision: `clean_coverage_no_survivor`.

Chunk03 is clean coverage evidence: `24/24 ok`, no raw error, no missing row. It does not create a survivor because `gate_passed=0`. Official min coverage is now `72/288`. The next allowed action is chunk04 only. P6/P7/Plan D remain blocked until official min 288 coverage and export exist.

## Next allowed command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

??? P5-official-min-chunk04-only?? ????.
??? ?? min warm64 chunk04? ??? min 96/288 coverage? ????, chunk05 ?? ?? ??? ???? ???.

??:
- chunk05+ ?? ??
- P6/P7/Plan D ?? ??
- OOS ?? ??
- DB UPDATE/DELETE ??
- git add -A ??
```
