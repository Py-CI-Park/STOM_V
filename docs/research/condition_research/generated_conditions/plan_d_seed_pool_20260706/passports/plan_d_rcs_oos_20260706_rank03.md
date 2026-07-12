# Plan D Seed Passport ? plan_d_rcs_oos_20260706_rank03

- seed_id: `plan_d_rcs_oos_20260706_rank03`
- label: `hypothesis_seed`
- source: `plan_b/repair_composite_selected_oos`
- condition_id: `repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90`
- source_run_id: `lat_repair_composite_selected16_oos_min_warm64_20260706`
- priority_rank: 3
- priority_basis: `selected_oos_score_desc_then_profit_desc`
- buy_name: `LAT_repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90_B`
- sell_name: `LAT_repair_v3_20260706_26_daily_boost_core_l1430_sell_loose_tp4_sl3_hold90_S`
- buy_sha256: `8bc41fe1cead5449625dc6daf7b675fdc23009237d382a32028b6c10c413feb4`
- sell_sha256: `0b38c51567b12e8c1df6b18b2491ab71845394ac452787470d24dd11c1bb79b6`
- source_result: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json`
- source_survivors: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_survivors_20260706.jsonl`
- created_at: `2026-07-06T11:28:38+09:00`

## Best Evidence

| metric | value |
|---|---:|
| profit_krw | 865831.0 |
| mdd_pct | 6.28 |
| daily_avg_trades | 0.5 |
| trade_count | 19 |
| score | 8.405463678617608 |
| calmar | 18.630573248407643 |
| payoff_ratio | 2.4264705882352944 |

## Caveat

The selected 16 were chosen from a full-period min preflight that included 2026-01-01~2026-02-27, so this is a fixed OOS-style robustness replay, not a fully blind discovery OOS.

## Buy Code

```text
composite_signal = False

# component 1: S09_D03
e26_part1 = True

if not (관심종목 == 1):
    e26_part1 = False
elif 90000 <= 시분초 < 100000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e26_part1 = False
    elif not (0.0 <= 등락율 < 3.0):
        e26_part1 = False
    elif not (체결강도 >= 108.0):
        e26_part1 = False
else:
    e26_part1 = False

if e26_part1:
    composite_signal = True

# component 2: S10_PMAX
e26_part2 = True

if not (관심종목 == 1):
    e26_part2 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e26_part2 = False
    elif not (0.0 <= 등락율 < 3.0):
        e26_part2 = False
    elif not (체결강도 >= 107.0):
        e26_part2 = False
else:
    e26_part2 = False

if e26_part2:
    composite_signal = True

# component 3: M09_POS
e26_part3 = True

if not (관심종목 == 1):
    e26_part3 = False
elif 90000 <= 시분초 < 100000:
    if not (시가총액 < 1500.0):
        e26_part3 = False
    elif not (0.0 <= 등락율 < 3.0):
        e26_part3 = False
    elif not (현재가 >= 고가 * 0.994):
        e26_part3 = False
else:
    e26_part3 = False

if e26_part3:
    composite_signal = True

# component 4: M10_POS
e26_part4 = True

if not (관심종목 == 1):
    e26_part4 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e26_part4 = False
    elif not (0.0 <= 등락율 < 3.0):
        e26_part4 = False
    elif not (현재가 >= 고가 * 0.994):
        e26_part4 = False
else:
    e26_part4 = False

if e26_part4:
    composite_signal = True

# component 5: L1430_NEAR
e26_part5 = True

if not (관심종목 == 1):
    e26_part5 = False
elif 143000 <= 시분초 < 144500:
    if not (시가총액 >= 10000.0):
        e26_part5 = False
    elif not (8.0 <= 등락율 < 29.0):
        e26_part5 = False
    elif not (현재가 >= 고가 * 1.0):
        e26_part5 = False
else:
    e26_part5 = False

if e26_part5:
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
