# Condition Passport — Lattice_min_1430p_small_high_strength_surge

| Field | Value |
|---|---|
| condition_id | `lattice_v1:min_1430p_small_high:strength_surge` |
| human_name | `Lattice_min_1430p_small_high_strength_surge` |
| role | `lattice_seed` |
| buy_strategy_id | `LATTICE_min_1430p_small_high_strength_surge_B` |
| sell_strategy_id | `LATTICE_min_1430p_small_high_strength_surge_S` |
| buy_code_sha256 | `b0073b7b01e6992f37d65b05a979982ad794911b03c1cb5de02c7b1d8c4c5ea3` |
| sell_code_sha256 | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` |
| prior_profit | `n/a` |
| prior_mdd | `n/a` |
| prior_trades | `n/a` |
| promotion_status | `research_only / not_promoted` |

## Core hypothesis

격자 시드 — 셀 `min_1430p_small_high` × 패밀리 `strength_surge` (params: force_exit=145900, max_hold=60, stop_loss=3.0, strength_min=110.0, take_profit=3.0). 첫 돌파/활성 계열 커버리지 지도 측정용 시드로, 셀당 train 거래 >= 300건 목표의 완화 임계 기본값을 쓴다. 생성 사유: `lattice_v1:min_1430p_small_high:strength_surge`.

## Buy condition full code

```python
매수 = True

if not (관심종목 == 1):
    매수 = False
elif 143000 <= 시분초 < 144500:
    if not (시가총액 < 1500.0):
        매수 = False
    elif not (8.0 <= 등락율 < 29.0):
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
