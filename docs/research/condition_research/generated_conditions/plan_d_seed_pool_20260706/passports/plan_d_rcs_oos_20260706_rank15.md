# Plan D Seed Passport ? plan_d_rcs_oos_20260706_rank15

- seed_id: `plan_d_rcs_oos_20260706_rank15`
- label: `hypothesis_seed`
- source: `plan_b/repair_composite_selected_oos`
- condition_id: `repair_v3_20260706_17_balanced_plus_l14_sell_tight_tp3_sl2p5_hold60`
- source_run_id: `lat_repair_composite_selected16_oos_min_warm64_20260706`
- priority_rank: 15
- priority_basis: `selected_oos_score_desc_then_profit_desc`
- buy_name: `LAT_repair_v3_20260706_17_balanced_plus_l14_sell_tight_tp3_sl2p5_hold60_B`
- sell_name: `LAT_repair_v3_20260706_17_balanced_plus_l14_sell_tight_tp3_sl2p5_hold60_S`
- buy_sha256: `045cc07ee3d87a11e2aceaacc01132b2057ac78e373dee770099028a21fb184d`
- sell_sha256: `01c800b9d64fa573fd823487d7e88e33b611ba818ca3b390b0904bb9464b35ce`
- source_result: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_result_20260706.json`
- source_survivors: `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_selected_oos_20260706/repair_composite_selected_oos_survivors_20260706.jsonl`
- created_at: `2026-07-06T11:28:38+09:00`

## Best Evidence

| metric | value |
|---|---:|
| profit_krw | 624603.0 |
| mdd_pct | 9.09 |
| daily_avg_trades | 0.5 |
| trade_count | 19 |
| score | 1.0240867309619435 |
| calmar | 9.286028602860286 |
| payoff_ratio | 1.6651226158038148 |

## Caveat

The selected 16 were chosen from a full-period min preflight that included 2026-01-01~2026-02-27, so this is a fixed OOS-style robustness replay, not a fully blind discovery OOS.

## Buy Code

```text
composite_signal = False

# component 1: S09_D03
e17_part1 = True

if not (관심종목 == 1):
    e17_part1 = False
elif 90000 <= 시분초 < 100000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e17_part1 = False
    elif not (0.0 <= 등락율 < 3.0):
        e17_part1 = False
    elif not (체결강도 >= 108.0):
        e17_part1 = False
else:
    e17_part1 = False

if e17_part1:
    composite_signal = True

# component 2: S10_BAL
e17_part2 = True

if not (관심종목 == 1):
    e17_part2 = False
elif 100000 <= 시분초 < 110000:
    if not (1500.0 <= 시가총액 < 3000.0):
        e17_part2 = False
    elif not (0.0 <= 등락율 < 3.0):
        e17_part2 = False
    elif not (체결강도 >= 107.0):
        e17_part2 = False
else:
    e17_part2 = False

if e17_part2:
    composite_signal = True

# component 3: M09_POS
e17_part3 = True

if not (관심종목 == 1):
    e17_part3 = False
elif 90000 <= 시분초 < 100000:
    if not (시가총액 < 1500.0):
        e17_part3 = False
    elif not (0.0 <= 등락율 < 3.0):
        e17_part3 = False
    elif not (현재가 >= 고가 * 0.994):
        e17_part3 = False
else:
    e17_part3 = False

if e17_part3:
    composite_signal = True

# component 4: L14_NEAR
e17_part4 = True

if not (관심종목 == 1):
    e17_part4 = False
elif 140000 <= 시분초 < 143000:
    if not (시가총액 >= 10000.0):
        e17_part4 = False
    elif not (8.0 <= 등락율 < 29.0):
        e17_part4 = False
    elif not (현재가 >= 고가 * 1.0):
        e17_part4 = False
else:
    e17_part4 = False

if e17_part4:
    composite_signal = True

if composite_signal:
    self.Buy()
```

## Sell Code

```text
매도 = False
if 수익률 >= 3.0:
    매도 = True
elif 수익률 <= -2.5:
    매도 = True
elif 보유시간 >= 60:
    매도 = True
elif 시분초 >= 145900:
    매도 = True
if 매도:
    self.Sell()
```
