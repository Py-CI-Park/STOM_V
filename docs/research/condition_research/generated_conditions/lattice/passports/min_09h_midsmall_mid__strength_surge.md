# Condition Passport — Lattice_min_09h_midsmall_mid_strength_surge

| Field | Value |
|---|---|
| condition_id | `lattice_v1:min_09h_midsmall_mid:strength_surge` |
| human_name | `Lattice_min_09h_midsmall_mid_strength_surge` |
| role | `lattice_seed` |
| buy_strategy_id | `LATTICE_min_09h_midsmall_mid_strength_surge_B` |
| sell_strategy_id | `LATTICE_min_09h_midsmall_mid_strength_surge_S` |
| buy_code_sha256 | `b2c32f6d6221d3c062128d7d44c2ba50f1c2190ce42a256bd347f282b3198320` |
| sell_code_sha256 | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` |
| prior_profit | `n/a` |
| prior_mdd | `n/a` |
| prior_trades | `n/a` |
| promotion_status | `research_only / not_promoted` |

## Core hypothesis

격자 시드 — 셀 `min_09h_midsmall_mid` × 패밀리 `strength_surge` (params: force_exit=145900, max_hold=60, stop_loss=3.0, strength_min=110.0, take_profit=3.0). 첫 돌파/활성 계열 커버리지 지도 측정용 시드로, 셀당 train 거래 >= 300건 목표의 완화 임계 기본값을 쓴다. 생성 사유: `lattice_v1:min_09h_midsmall_mid:strength_surge`.

## Buy condition full code

```python
매수 = True

if not (관심종목 == 1):
    매수 = False
elif 90000 <= 시분초 < 100000:
    if not (1500.0 <= 시가총액 < 3000.0):
        매수 = False
    elif not (3.0 <= 등락율 < 8.0):
        매수 = False
    elif not (체결강도 >= 110.0):
        매수 = False
else:
    매수 = False

if 매수:
    self.Buy()
```

## Sell condition full code

```python
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
