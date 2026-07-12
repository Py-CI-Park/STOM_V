# 2026-07-05 P5 official min 288 export and P6 no-D handoff

## Scope

Selected range: `P5-official-min-chunk04-to-12-export-and-P6-no-D`.
Plan D/P7 was not executed. OOS and portfolio were not opened because no go/refinement survivor exists.

## Source evidence

- min chunk04~12 receipt: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunks04_12_official_full_warm64_20260705_receipt.json`
- min chunk08 stale/supplement receipt: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_chunk08_stale_partial_official_full_warm64_20260705_receipt.json`
- min coverage receipt: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_coverage_20260705_receipt.json`
- min row export JSONL: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.jsonl`
- min summary JSON: `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json`
- P6 coverage/gaps/batch_plan: `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_coverage_gaps_batch_plan_no_d_20260705.json`
- P6 go/no_go/hold: `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_go_no_go_hold_20260705.json`
- revival registry append-only JSONL: `docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_revival_registry_20260705.jsonl`

## Chunk status

| chunk | run status | rows | status_counts | gate_passed | note |
| --- | --- | ---: | --- | ---: | --- |
| 04 | {'lat_min_official_full_warm64_chunk04_20260705': 'complete'} | 24/24 | {'ok': 24} | 0 |  |
| 05 | {'lat_min_official_full_warm64_chunk05_20260705': 'complete'} | 24/24 | {'ok': 24} | 0 |  |
| 06 | {'lat_min_official_full_warm64_chunk06_20260705': 'complete'} | 24/24 | {'ok': 24} | 0 |  |
| 07 | {'lat_min_official_full_warm64_chunk07_20260705': 'complete'} | 24/24 | {'error': 1, 'ok': 23} | 0 |  |
| 08 | {'lat_min_official_full_warm64_chunk08_20260705': 'running', 'lat_min_official_full_warm64_chunk08_supplement01_20260705': 'complete'} | 24/24 | {'ok': 24} | 0 | original run left as stale partial; supplement01 completed remaining 22 rows |
| 09 | {'lat_min_official_full_warm64_chunk09_20260705': 'complete'} | 24/24 | {'error': 3, 'ok': 21} | 0 |  |
| 10 | {'lat_min_official_full_warm64_chunk10_20260705': 'complete'} | 24/24 | {'ok': 24} | 0 |  |
| 11 | {'lat_min_official_full_warm64_chunk11_20260705': 'complete'} | 24/24 | {'error': 3, 'ok': 21} | 0 |  |
| 12 | {'lat_min_official_full_warm64_chunk12_20260705': 'complete'} | 24/24 | {'ok': 24} | 0 |  |

## Min overall result

| Metric | Value |
| --- | --- |
| rows | `288` |
| unique_pairs | `288` |
| status_counts | `{'ok': 281, 'error': 7}` |
| gate_passed_count | `0` |
| no_metrics_or_error_count | `7` |
| mdd_excess_count | `215` |
| low_daily_trades_count | `58` |
| negative_profit_count | `271` |
| profit_range | `-90894637.0 ~ 819969.0` |
| mdd_range | `0.93 ~ 287.05` |

## Primary failure decomposition

| Primary fail | Count |
| --- | ---: |
| `low_daily_trades` | 43 |
| `mdd_excess` | 200 |
| `mdd_excess_and_low_daily_trades` | 15 |
| `nonpositive_profit` | 23 |
| `no_metrics_or_error` | 7 |

### Axis: time_bucket

| value | count | gate | ok | error | mdd_excess | low_trades | nonpositive_profit | avg_profit | avg_mdd |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 09h | 48 | 0 | 48 | 0 | 41 | 5 | 46 | -15,896,329 | 89.0387 |
| 10h | 48 | 0 | 48 | 0 | 41 | 8 | 45 | -19,115,443 | 84.1206 |
| 11h | 48 | 0 | 48 | 0 | 41 | 10 | 45 | -14,203,563 | 68.7869 |
| 13h | 48 | 0 | 47 | 1 | 31 | 10 | 46 | -16,453,068 | 79.7091 |
| 1430p | 48 | 0 | 45 | 3 | 31 | 13 | 44 | -7,795,713 | 49.3576 |
| 14h | 48 | 0 | 45 | 3 | 30 | 12 | 45 | -11,053,643 | 52.6362 |

### Axis: size

| value | count | gate | ok | error | mdd_excess | low_trades | nonpositive_profit | avg_profit | avg_mdd |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| large | 72 | 0 | 72 | 0 | 54 | 0 | 72 | -16,241,387 | 43.4436 |
| midlarge | 72 | 0 | 72 | 0 | 57 | 13 | 71 | -12,443,006 | 61.0057 |
| midsmall | 72 | 0 | 68 | 4 | 52 | 21 | 62 | -12,848,144 | 89.2659 |
| small | 72 | 0 | 69 | 3 | 52 | 24 | 66 | -15,143,495 | 92.16 |

### Axis: strength

| value | count | gate | ok | error | mdd_excess | low_trades | nonpositive_profit | avg_profit | avg_mdd |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| high | 96 | 0 | 96 | 0 | 84 | 9 | 96 | -21,791,555 | 110.8683 |
| low | 96 | 0 | 89 | 7 | 58 | 26 | 80 | -8,557,678 | 43.3829 |
| mid | 96 | 0 | 96 | 0 | 73 | 23 | 95 | -11,773,215 | 56.7191 |

### Axis: family

| value | count | gate | ok | error | mdd_excess | low_trades | nonpositive_profit | avg_profit | avg_mdd |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| momentum_breakout | 72 | 0 | 67 | 5 | 34 | 31 | 62 | -5,078,873 | 58.9521 |
| prevday_active | 72 | 0 | 72 | 0 | 70 | 0 | 72 | -26,666,065 | 89.0176 |
| strength_surge | 72 | 0 | 70 | 2 | 41 | 27 | 65 | -7,646,313 | 48.532 |
| volume_surge | 72 | 0 | 72 | 0 | 70 | 0 | 72 | -16,505,114 | 86.0162 |

## Tick/min integrated P6 result

| Item | Value |
| --- | --- |
| total coverage | `576/576` |
| by_lane | `{'tick': 288, 'min': 288}` |
| status_by_lane | `{'min': {'ok': 281, 'error': 7}, 'tick': {'ok': 288}}` |
| gate_passed_by_lane | `{'min': 0, 'tick': 0}` |
| classification_counts | `{'go': 0, 'hold': 0, 'no_go': 576}` |
| gaps | `{'missing_lanes': [], 'missing_rows': 0, 'stale_or_supplemented_notes': ['min chunk08 original run_id lat_min_official_full_warm64_chunk08_20260705 remains running/stale with 2 rows; supplement01 completed remaining 22 rows append-only.']}` |

## Decision

- `go` candidates: 0. Refinement was not opened.
- OOS was not opened because preregistered refinement survivors do not exist.
- Portfolio was not produced because OOS survivors do not exist.
- Plan D is blocked: seed research needs surviving seed inputs from Plan B/C, and this run produced none.

## Next command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

Range: Plan-D-readiness-review-only.
Goal: do not execute Plan D; review and document why Plan D input is unavailable
and what repair conditions are required before opening Plan D.

Forbidden:
- Do not execute Plan D/P7.
- Do not run OOS.
- Do not use DB UPDATE/DELETE.
- Do not produce portfolio output without survivors.
```
