# 2026-07-05 P5 official min chunk02 handoff

## Scope

Selected range: `P5-official-min-chunk02-only`.
Only official min warm64 chunk02 was executed. Chunk03+, full min export, P6/P7, Plan D, OOS, survivor promotion, and DB UPDATE/DELETE were not executed.

## Inputs

| Item | Value |
| --- | --- |
| manifest | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_full_run_protocol_after_preflight_20260705.json` |
| chunk02 pair file | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_min_official_full_warm64_chunk02_20260705.json` |
| run_id | `lat_min_official_full_warm64_chunk02_20260705` |
| config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json` |
| receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunk02_official_full_warm64_20260705_receipt.json` |

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
| warm elapsed | `124s` |
| total runtime | `13.3m` |
| DB run status | `complete` |
| recorded rows | `24/24` |
| status_counts | `{'ok': 24}` |
| gate_passed | `0` |
| coverage | `48/288` |
| profit_range | `-45,128,636~-803,608` |
| mdd_range | `23.29~151.41` |
| daily_avg_trades_range | `0.5~10.8` |

## Failure decomposition

| Primary reason | Count |
| --- | ---: |
| mdd_excess | 22 |
| low_daily_trades | 0 |
| nonpositive_profit | 2 |
| other | 0 |

## Row summary

| gen | official_index | status | gate | profit | mdd | trades | daily | reason |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 0 | 24 | `ok` | `False` | -803,608 | 23.29 | 116 | 0.5 | `total_profit -8.036e+05 <= 0` |
| 1 | 25 | `ok` | `False` | -16,630,691 | 56.08 | 782 | 3.7 | `mdd 56.08 > mdd_cap 35` |
| 2 | 26 | `ok` | `False` | -5,020,163 | 52.25 | 171 | 0.8 | `mdd 52.25 > mdd_cap 35` |
| 3 | 27 | `ok` | `False` | -7,040,950 | 46.56 | 306 | 1.4 | `mdd 46.56 > mdd_cap 35` |
| 4 | 28 | `ok` | `False` | -5,290,987 | 40.1 | 299 | 1.4 | `mdd 40.1 > mdd_cap 35` |
| 5 | 29 | `ok` | `False` | -28,626,727 | 83.5 | 1140 | 5.4 | `mdd 83.5 > mdd_cap 35` |
| 6 | 30 | `ok` | `False` | -16,257,000 | 81.56 | 592 | 2.8 | `mdd 81.56 > mdd_cap 35` |
| 7 | 31 | `ok` | `False` | -10,448,164 | 69.82 | 462 | 2.2 | `mdd 69.82 > mdd_cap 35` |
| 8 | 32 | `ok` | `False` | -11,175,970 | 79.38 | 474 | 2.2 | `mdd 79.38 > mdd_cap 35` |
| 9 | 33 | `ok` | `False` | -45,128,636 | 151.41 | 1364 | 6.4 | `mdd 151.4 > mdd_cap 35` |
| 10 | 34 | `ok` | `False` | -22,638,115 | 119.06 | 826 | 3.9 | `mdd 119.1 > mdd_cap 35` |
| 11 | 35 | `ok` | `False` | -14,049,260 | 102.04 | 610 | 2.9 | `mdd 102 > mdd_cap 35` |
| 12 | 36 | `ok` | `False` | -12,437,574 | 43.57 | 718 | 3.4 | `mdd 43.57 > mdd_cap 35` |
| 13 | 37 | `ok` | `False` | -40,793,955 | 55.82 | 2304 | 10.8 | `mdd 55.82 > mdd_cap 35` |
| 14 | 38 | `ok` | `False` | -16,523,129 | 38.36 | 1079 | 5.1 | `mdd 38.36 > mdd_cap 35` |
| 15 | 39 | `ok` | `False` | -17,444,935 | 44.87 | 1009 | 4.7 | `mdd 44.87 > mdd_cap 35` |
| 16 | 40 | `ok` | `False` | -12,011,469 | 33.38 | 1065 | 5.0 | `total_profit -1.201e+07 <= 0` |
| 17 | 41 | `ok` | `False` | -32,464,038 | 47.22 | 2220 | 10.4 | `mdd 47.22 > mdd_cap 35` |
| 18 | 42 | `ok` | `False` | -18,925,639 | 37.31 | 1681 | 7.9 | `mdd 37.31 > mdd_cap 35` |
| 19 | 43 | `ok` | `False` | -12,679,260 | 36.33 | 1105 | 5.2 | `mdd 36.33 > mdd_cap 35` |
| 20 | 44 | `ok` | `False` | -10,605,243 | 56.45 | 543 | 2.5 | `mdd 56.45 > mdd_cap 35` |
| 21 | 45 | `ok` | `False` | -23,723,669 | 80.97 | 1035 | 4.9 | `mdd 80.97 > mdd_cap 35` |
| 22 | 46 | `ok` | `False` | -15,174,799 | 53.28 | 809 | 3.8 | `mdd 53.28 > mdd_cap 35` |
| 23 | 47 | `ok` | `False` | -11,734,953 | 83.42 | 521 | 2.4 | `mdd 83.42 > mdd_cap 35` |

## Decision

Decision: `clean_coverage_no_survivor`.

Chunk02 is clean coverage evidence: `24/24 ok`, no raw error, no missing row. It does not create a survivor because `gate_passed=0`. Official min coverage is now `48/288`. The next allowed action is chunk03 only. P6/P7/Plan D remain blocked until official min 288 coverage and export exist.

## Next allowed command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

??? P5-official-min-chunk03-only?? ????.
??? ?? min warm64 chunk03? ??? min 72/288 coverage? ????, chunk04 ?? ?? ??? ???? ???.

??:
- chunk04+ ?? ??
- P6/P7/Plan D ?? ??
- OOS ?? ??
- DB UPDATE/DELETE ??
- git add -A ??
```
