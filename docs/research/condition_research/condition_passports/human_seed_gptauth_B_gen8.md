# Condition Passport — GPTGen8_HighCoverage_FailedProfitContext

| Field | Value |
|---|---|
| condition_id | `human_seed_gptauth_B_gen8` |
| human_name | `GPTGen8_HighCoverage_FailedProfitContext` |
| role | `failure_coverage_context` |
| buy_strategy_id | `AILOOP_follow12_gptauth_B_seeded64_20260628_g8_buy` |
| sell_strategy_id | `AILOOP_follow12_gptauth_B_seeded64_20260628_g8_sell` |
| buy_code_sha256 | `83e7322e2efd540d18e960ad2128d57d01f4d4d061f62c91bb352312ab514e73` |
| sell_code_sha256 | `4ed51bb1a051bec150789e89257d4b623ef800567d64d2d9bf86359df59992a9` |
| prior_profit | `1772126` |
| prior_mdd | `15.14` |
| prior_trades | `550` |
| promotion_status | `research_only / not_promoted` |

## Core hypothesis

이 passport는 개선된 process-research v2 검증의 입력이다. LLM에는 id만 전달하지 않고 buy/sell 조건식 전문과 sha256을 함께 전달한다.

## Buy condition full code

```python
매수 = True

if not (관심종목 == 1):
    매수 = False
elif not (90500 <= 시분초 < 91000):
    매수 = False
elif not (초당거래대금 > 20):
    매수 = False
elif not (당일거래대금 > 5000):
    매수 = False
elif not (80 <= 체결강도 <= 260):
    매수 = False
elif not (1000 <= 시가총액 < 5000):
    매수 = False
elif not (1000 < 현재가 <= 40000):
    매수 = False
elif not (3.0 < 등락율 <= 13.0):
    매수 = False
elif not (0.0 <= ((시가 - (현재가 / (1 + 등락율 / 100))) / (현재가 / (1 + 등락율 / 100))) * 100 < 7.0):
    매수 = False
elif not (1.5 <= ((현재가 - 시가) / 시가) * 100 < 8.0):
    매수 = False
elif not (고저평균대비등락율 > 0 and 현재가 < VI가격 - VI호가단위 * 5):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False
elif not (당일거래대금각도(30) > 8 and 당일거래대금각도(30) < 32):
    매수 = False
elif not (초당거래대금 / 초당거래대금평균(30) > 1.8 and 초당거래대금 > 초당거래대금N(1) * 1.25):
    매수 = False
elif not (현재가 > 최고현재가(20, 1) and 초당매수수량 > 매도총잔량 * 0.22):
    매수 = False

if 매수:
    self.Buy()
```

## Sell condition full code

```python
매도 = False

if 등락율 > 29.5:
    매도 = True
elif 시분초 >= 92800:
    매도 = True
elif 수익률 >= 9:
    매도 = True
elif 수익률 <= -2.0:
    매도 = True
elif 최저수익률 <= -1.8 and 수익률 <= -1.2:
    매도 = True
elif 최고수익률 >= 6 and 수익률 <= 최고수익률 * 0.70:
    매도 = True
elif 최고수익률 >= 3 and 수익률 <= 최고수익률 * 0.55:
    매도 = True
elif 최고수익률 >= 1.5 and 수익률 <= 0 and 체결강도 < 체결강도N(1):
    매도 = True
elif 보유시간 >= 240:
    매도 = True
elif 보유시간 >= 120 and 수익률 < 0.3:
    매도 = True
elif 시분초 < 93000:
    if 최고수익률 > 2 and 체결강도 < 체결강도평균(20) and 수익률 <= 최고수익률 * 0.65:
        매도 = True
    elif 보유시간 > 60 and 수익률 < -0.8 and 현재가 < 이동평균(60):
        매도 = True
    elif 수익률 > 1 and 체결강도 < 85 and 초당매도수량 > 초당매수수량 * 1.2:
        매도 = True
    elif 시가총액 < 10000:
        if 등락율각도(30) >= 5 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.7 and (현재가 / 현재가N(1) - 1) * 100 < -0.5:
            매도 = True

if 매도:
    self.Sell()
```
