# Condition Passport — Lattice_min_09h_midlarge_high_volume_surge

| Field | Value |
|---|---|
| condition_id | `lattice_v1:min_09h_midlarge_high:volume_surge` |
| human_name | `Lattice_min_09h_midlarge_high_volume_surge` |
| role | `lattice_seed` |
| buy_strategy_id | `LATTICE_min_09h_midlarge_high_volume_surge_B` |
| sell_strategy_id | `LATTICE_min_09h_midlarge_high_volume_surge_S` |
| buy_code_sha256 | `652981790c4b2100abd51df4f2cf1e58810cef57333bdbeffbbe26964d9b92e2` |
| sell_code_sha256 | `400f5decf168fbaa2f39a5bc769fd737ccd8e5341d1ba8219d6bfe745c4ac309` |
| prior_profit | `n/a` |
| prior_mdd | `n/a` |
| prior_trades | `n/a` |
| promotion_status | `research_only / not_promoted` |

## Core hypothesis

격자 시드 — 셀 `min_09h_midlarge_high` × 패밀리 `volume_surge` (params: avg_win=30, force_exit=145900, max_hold=60, stop_loss=3.0, surge_mult=2.0, take_profit=3.0). 첫 돌파/활성 계열 커버리지 지도 측정용 시드로, 셀당 train 거래 >= 300건 목표의 완화 임계 기본값을 쓴다. 생성 사유: `lattice_v1:min_09h_midlarge_high:volume_surge`.

## Buy condition full code

```python
매수 = True

if not (관심종목 == 1):
    매수 = False
elif 90000 <= 시분초 < 100000:
    if not (3000.0 <= 시가총액 < 10000.0):
        매수 = False
    elif not (8.0 <= 등락율 < 29.0):
        매수 = False
    elif not (분당거래대금 >= 분당거래대금평균(30) * 2.0):
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
