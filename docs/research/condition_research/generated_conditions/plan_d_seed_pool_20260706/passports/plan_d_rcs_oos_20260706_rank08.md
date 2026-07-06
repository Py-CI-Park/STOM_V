# Plan D Seed Passport ? plan_d_rcs_oos_20260706_rank08

- seed_id: `plan_d_rcs_oos_20260706_rank08`
- label: `hypothesis_seed`
- source: `plan_b/repair_composite_selected_oos`
- condition_id: `repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60`
- source_run_id: `lat_repair_composite_selected16_oos_min_warm64_20260706`
- priority_rank: 8
- priority_basis: `selected_oos_score_desc_then_profit_desc`
- buy_name: `LAT_repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60_B`
- sell_name: `LAT_repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60_S`
- buy_sha256: `2ef5f5be3e8a7332efec2e80338a5acd95afc72386c1e9f081b9ee7783491e52`
- sell_sha256: `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309`
- source_result: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json`
- source_survivors: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_survivors_20260706.jsonl`
- created_at: `2026-07-06T11:28:38+09:00`

## Best Evidence

| metric | value |
|---|---:|
| profit_krw | 826691.0 |
| mdd_pct | 4.29 |
| daily_avg_trades | 1.8 |
| trade_count | 67 |
| score | 3.971153697765492 |
| calmar | 8.787878787878789 |
| payoff_ratio | 1.19013256006628 |

## Caveat

The selected 16 were chosen from a full-period min preflight that included 2026-01-01~2026-02-27, so this is a fixed OOS-style robustness replay, not a fully blind discovery OOS.

## Buy Code

```text
composite_signal = False

# component 1: S09_PMAX
e14_part1 = True

if not (관심종목 == 1):
    e14_part1 = False
elif 90000 <= 시분초 < 100000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e14_part1 = False
    elif not (0.0 <= 등락율 < 3.0):
        e14_part1 = False
    elif not (체결강도 >= 109.0):
        e14_part1 = False
else:
    e14_part1 = False

if e14_part1:
    composite_signal = True

# component 2: S10_PMAX
e14_part2 = True

if not (관심종목 == 1):
    e14_part2 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e14_part2 = False
    elif not (0.0 <= 등락율 < 3.0):
        e14_part2 = False
    elif not (체결강도 >= 107.0):
        e14_part2 = False
else:
    e14_part2 = False

if e14_part2:
    composite_signal = True

# component 3: M09_POS
e14_part3 = True

if not (관심종목 == 1):
    e14_part3 = False
elif 90000 <= 시분초 < 100000:
    if not (시가총액 < 1500.0):
        e14_part3 = False
    elif not (0.0 <= 등락율 < 3.0):
        e14_part3 = False
    elif not (현재가 >= 고가 * 0.994):
        e14_part3 = False
else:
    e14_part3 = False

if e14_part3:
    composite_signal = True

# component 4: M10_POS
e14_part4 = True

if not (관심종목 == 1):
    e14_part4 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e14_part4 = False
    elif not (0.0 <= 등락율 < 3.0):
        e14_part4 = False
    elif not (현재가 >= 고가 * 0.994):
        e14_part4 = False
else:
    e14_part4 = False

if e14_part4:
    composite_signal = True

# component 5: L13_NEAR
e14_part5 = True

if not (관심종목 == 1):
    e14_part5 = False
elif 130000 <= 시분초 < 140000:
    if not (시가총액 >= 10000.0):
        e14_part5 = False
    elif not (8.0 <= 등락율 < 29.0):
        e14_part5 = False
    elif not (현재가 >= 고가 * 1.0):
        e14_part5 = False
else:
    e14_part5 = False

if e14_part5:
    composite_signal = True

if composite_signal:
    self.Buy()
```

## Sell Code

```text
매도 = False
if 수익률 >= 3.0:
    매도 = True
elif 수익률 <= -3.0:
    매도 = True
elif 보유시간 >= 60:
    매도 = True
elif 시분초 >= 145900:
    매도 = True
if 매도:
    self.Sell()
```
