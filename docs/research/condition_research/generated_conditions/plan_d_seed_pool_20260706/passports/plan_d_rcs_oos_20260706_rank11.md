# Plan D Seed Passport ? plan_d_rcs_oos_20260706_rank11

- seed_id: `plan_d_rcs_oos_20260706_rank11`
- label: `hypothesis_seed`
- source: `plan_b/repair_composite_selected_oos`
- condition_id: `repair_v3_20260706_15_top_four_plus_l13_l14_sell_default_tp3_sl3_hold60`
- source_run_id: `lat_repair_composite_selected16_oos_min_warm64_20260706`
- priority_rank: 11
- priority_basis: `selected_oos_score_desc_then_profit_desc`
- buy_name: `LAT_repair_v3_20260706_15_top_four_plus_l13_l14_sell_default_tp3_sl3_hold60_B`
- sell_name: `LAT_repair_v3_20260706_15_top_four_plus_l13_l14_sell_default_tp3_sl3_hold60_S`
- buy_sha256: `e347cd23d07dc0bc0b3559e2f8f68b0af4ea23238f8e65f8796844a4de2b80ec`
- sell_sha256: `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309`
- source_result: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json`
- source_survivors: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_survivors_20260706.jsonl`
- created_at: `2026-07-06T11:28:38+09:00`

## Best Evidence

| metric | value |
|---|---:|
| profit_krw | 725284.0 |
| mdd_pct | 4.32 |
| daily_avg_trades | 2.0 |
| trade_count | 75 |
| score | 3.2179768393848214 |
| calmar | 7.650462962962962 |
| payoff_ratio | 1.145836800170402 |

## Caveat

The selected 16 were chosen from a full-period min preflight that included 2026-01-01~2026-02-27, so this is a fixed OOS-style robustness replay, not a fully blind discovery OOS.

## Buy Code

```text
composite_signal = False

# component 1: S09_PMAX
e15_part1 = True

if not (관심종목 == 1):
    e15_part1 = False
elif 90000 <= 시분초 < 100000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e15_part1 = False
    elif not (0.0 <= 등락율 < 3.0):
        e15_part1 = False
    elif not (체결강도 >= 109.0):
        e15_part1 = False
else:
    e15_part1 = False

if e15_part1:
    composite_signal = True

# component 2: S10_PMAX
e15_part2 = True

if not (관심종목 == 1):
    e15_part2 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e15_part2 = False
    elif not (0.0 <= 등락율 < 3.0):
        e15_part2 = False
    elif not (체결강도 >= 107.0):
        e15_part2 = False
else:
    e15_part2 = False

if e15_part2:
    composite_signal = True

# component 3: M09_POS
e15_part3 = True

if not (관심종목 == 1):
    e15_part3 = False
elif 90000 <= 시분초 < 100000:
    if not (시가총액 < 1500.0):
        e15_part3 = False
    elif not (0.0 <= 등락율 < 3.0):
        e15_part3 = False
    elif not (현재가 >= 고가 * 0.994):
        e15_part3 = False
else:
    e15_part3 = False

if e15_part3:
    composite_signal = True

# component 4: M10_POS
e15_part4 = True

if not (관심종목 == 1):
    e15_part4 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e15_part4 = False
    elif not (0.0 <= 등락율 < 3.0):
        e15_part4 = False
    elif not (현재가 >= 고가 * 0.994):
        e15_part4 = False
else:
    e15_part4 = False

if e15_part4:
    composite_signal = True

# component 5: L13_NEAR
e15_part5 = True

if not (관심종목 == 1):
    e15_part5 = False
elif 130000 <= 시분초 < 140000:
    if not (시가총액 >= 10000.0):
        e15_part5 = False
    elif not (8.0 <= 등락율 < 29.0):
        e15_part5 = False
    elif not (현재가 >= 고가 * 1.0):
        e15_part5 = False
else:
    e15_part5 = False

if e15_part5:
    composite_signal = True

# component 6: L14_NEAR
e15_part6 = True

if not (관심종목 == 1):
    e15_part6 = False
elif 140000 <= 시분초 < 143000:
    if not (시가총액 >= 10000.0):
        e15_part6 = False
    elif not (8.0 <= 등락율 < 29.0):
        e15_part6 = False
    elif not (현재가 >= 고가 * 1.0):
        e15_part6 = False
else:
    e15_part6 = False

if e15_part6:
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
