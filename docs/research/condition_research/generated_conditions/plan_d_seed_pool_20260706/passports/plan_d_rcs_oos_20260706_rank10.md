# Plan D Seed Passport ? plan_d_rcs_oos_20260706_rank10

- seed_id: `plan_d_rcs_oos_20260706_rank10`
- label: `hypothesis_seed`
- source: `plan_b/repair_composite_selected_oos`
- condition_id: `repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_loose_tp4_sl3_hold90`
- source_run_id: `lat_repair_composite_selected16_oos_min_warm64_20260706`
- priority_rank: 10
- priority_basis: `selected_oos_score_desc_then_profit_desc`
- buy_name: `LAT_repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_loose_tp4_sl3_hold90_B`
- sell_name: `LAT_repair_v3_20260706_20_all_positive_plus_l14_l1430_sell_loose_tp4_sl3_hold90_S`
- buy_sha256: `7e8bfbd4c2bceaba03868658c8242e31c00c303efea82e44e2682c5328b95716`
- sell_sha256: `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6`
- source_result: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json`
- source_survivors: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_survivors_20260706.jsonl`
- created_at: `2026-07-06T11:28:38+09:00`

## Best Evidence

| metric | value |
|---|---:|
| profit_krw | 985556.0 |
| mdd_pct | 6.64 |
| daily_avg_trades | 0.8 |
| trade_count | 31 |
| score | 3.9314843632123484 |
| calmar | 20.05722891566265 |
| payoff_ratio | 1.6742936544696616 |

## Caveat

The selected 16 were chosen from a full-period min preflight that included 2026-01-01~2026-02-27, so this is a fixed OOS-style robustness replay, not a fully blind discovery OOS.

## Buy Code

```text
composite_signal = False

# component 1: S09_D03
e20_part1 = True

if not (관심종목 == 1):
    e20_part1 = False
elif 90000 <= 시분초 < 100000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e20_part1 = False
    elif not (0.0 <= 등락율 < 3.0):
        e20_part1 = False
    elif not (체결강도 >= 108.0):
        e20_part1 = False
else:
    e20_part1 = False

if e20_part1:
    composite_signal = True

# component 2: S10_PMAX
e20_part2 = True

if not (관심종목 == 1):
    e20_part2 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e20_part2 = False
    elif not (0.0 <= 등락율 < 3.0):
        e20_part2 = False
    elif not (체결강도 >= 107.0):
        e20_part2 = False
else:
    e20_part2 = False

if e20_part2:
    composite_signal = True

# component 3: M09_POS
e20_part3 = True

if not (관심종목 == 1):
    e20_part3 = False
elif 90000 <= 시분초 < 100000:
    if not (시가총액 < 1500.0):
        e20_part3 = False
    elif not (0.0 <= 등락율 < 3.0):
        e20_part3 = False
    elif not (현재가 >= 고가 * 0.994):
        e20_part3 = False
else:
    e20_part3 = False

if e20_part3:
    composite_signal = True

# component 4: M10_POS
e20_part4 = True

if not (관심종목 == 1):
    e20_part4 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e20_part4 = False
    elif not (0.0 <= 등락율 < 3.0):
        e20_part4 = False
    elif not (현재가 >= 고가 * 0.994):
        e20_part4 = False
else:
    e20_part4 = False

if e20_part4:
    composite_signal = True

# component 5: L14_NEAR
e20_part5 = True

if not (관심종목 == 1):
    e20_part5 = False
elif 140000 <= 시분초 < 143000:
    if not (시가총액 >= 10000.0):
        e20_part5 = False
    elif not (8.0 <= 등락율 < 29.0):
        e20_part5 = False
    elif not (현재가 >= 고가 * 1.0):
        e20_part5 = False
else:
    e20_part5 = False

if e20_part5:
    composite_signal = True

# component 6: L1430_NEAR
e20_part6 = True

if not (관심종목 == 1):
    e20_part6 = False
elif 143000 <= 시분초 < 144500:
    if not (시가총액 >= 10000.0):
        e20_part6 = False
    elif not (8.0 <= 등락율 < 29.0):
        e20_part6 = False
    elif not (현재가 >= 고가 * 1.0):
        e20_part6 = False
else:
    e20_part6 = False

if e20_part6:
    composite_signal = True

if composite_signal:
    self.Buy()
```

## Sell Code

```text
매도 = False
if 수익률 >= 4.0:
    매도 = True
elif 수익률 <= -3.0:
    매도 = True
elif 보유시간 >= 90:
    매도 = True
elif 시분초 >= 145900:
    매도 = True
if 매도:
    self.Sell()
```
