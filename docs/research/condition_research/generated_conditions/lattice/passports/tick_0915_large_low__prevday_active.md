# Condition Passport — Lattice_tick_0915_large_low_prevday_active

| Field | Value |
|---|---|
| condition_id | `lattice_v1:tick_0915_large_low:prevday_active` |
| human_name | `Lattice_tick_0915_large_low_prevday_active` |
| role | `lattice_seed` |
| buy_strategy_id | `LATTICE_tick_0915_large_low_prevday_active_B` |
| sell_strategy_id | `LATTICE_tick_0915_large_low_prevday_active_S` |
| buy_code_sha256 | `aaa429d6d9e0678d592d0fb665b553bd570d2fb1d71ad4689e0696285be77196` |
| sell_code_sha256 | `73508f1391ad582377eb5fb29aeee502dcb880acd944eb66c1ef98a2bd8027b2` |
| prior_profit | `n/a` |
| prior_mdd | `n/a` |
| prior_trades | `n/a` |
| promotion_status | `research_only / not_promoted` |

## Core hypothesis

격자 시드 — 셀 `tick_0915_large_low` × 패밀리 `prevday_active` (params: force_exit=92900, max_hold=180, prev_ratio_min=50.0, stop_loss=2.0, take_profit=2.0). 첫 돌파/활성 계열 커버리지 지도 측정용 시드로, 셀당 train 거래 >= 300건 목표의 완화 임계 기본값을 쓴다. 생성 사유: `lattice_v1:tick_0915_large_low:prevday_active`.

## Buy condition full code

```python
매수 = True

if not (관심종목 == 1):
    매수 = False
elif 91500 <= 시분초 < 92000:
    if not (시가총액 >= 10000.0):
        매수 = False
    elif not (0.0 <= 등락율 < 3.0):
        매수 = False
    elif not (전일동시간비 >= 50.0):
        매수 = False
else:
    매수 = False

if 매수:
    self.Buy()
```

## Sell condition full code

```python
매도 = False
if 수익률 >= 2.0:
    매도 = True
elif 수익률 <= -2.0:
    매도 = True
elif 보유시간 >= 180:
    매도 = True
elif 시분초 >= 92900:
    매도 = True
if 매도:
    self.Sell()
```
