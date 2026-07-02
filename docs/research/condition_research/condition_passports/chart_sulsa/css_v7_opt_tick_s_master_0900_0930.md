# Condition Passport — CSS_V7_OPT_TICK_S_MASTER_0900_0930

| Field | Value |
|---|---|
| condition_id | `CSS_V7_OPT_TICK_S_MASTER_0900_0930` |
| human_name | `1tick 최적화형 매도식` |
| role | `hypothesis_seed` |
| lane | `tick` |
| side | `sell` |
| principle_ids | `P7, P10, P11` |
| time_window | `09:00:00-09:30:00` |
| buy_strategy_id | `CSS_V7_OPT_TICK_B_MASTER_0900_0930` |
| sell_strategy_id | `CSS_V7_OPT_TICK_S_MASTER_0900_0930` |
| buy_code_sha256 | `c4775e12f4db4e7f54580c024202d7f8446ce304504c158b36bfcf9718a85179` |
| sell_code_sha256 | `72549be977ecf17e434b1c671c74180c7409ac3d187c467a3362b811cdaad16b` |
| oos_status | `none` |
| prior_profit | `none` |
| prior_mdd | `none` |
| prior_trades | `none` |
| promotion_status | `research_only / not_promoted` |
| source | `chart_sulsa_v7_0` (원문 6.2절) |

## Core hypothesis

이 passport는 차트술사 구조론 보고서 v7.0에서 추출한 **무근거 가설 시드**다.
관련 원리: P7, P10, P11. 이 조건식 자체는 `sell` 측이며, 반대 측 코드는 같은 레인의
통합(OPT MASTER) 조건식으로 페어링했다. 모든 임계값은 백테스트로 검증되지 않은
가설이며 검증된 사실로 취급하면 안 된다. oos_status=`none` — OOS 검증 이력이 없다.

## Buy condition full code

```python
# =============================================================================
# CSS_V7_OPT_TICK_B_MASTER_0900_0930
# 1tick 최적화형 매수식: CSS_V7_OPT_VARS_TICK_0900_0930 사용
# =============================================================================
매수 = False

if 데이터길이 >= int(self.vars[0]) + int(self.vars[1]) + 30 and 90000 <= 시분초 < 93000 and 관심종목 == 1:
    박스틱수 = int(self.vars[0])
    기준틱수 = int(self.vars[1])
    돌파확인틱수 = int(self.vars[2])
    평균틱수 = int(self.vars[3])

    미세상단 = 최고현재가(박스틱수, 1)
    미세하단 = 최저현재가(박스틱수, 1)
    미세폭율 = ((미세상단 - 미세하단) / 미세하단) * 100 if 미세하단 > 0 else 999
    미세돌파율 = ((현재가 - 미세상단) / 미세상단) * 100 if 미세상단 > 0 else -999
    기준상단 = 최고현재가(기준틱수, 돌파확인틱수)
    기준하단 = 최저현재가(기준틱수, 돌파확인틱수)
    기준폭율 = ((기준상단 - 기준하단) / 기준하단) * 100 if 기준하단 > 0 else 999
    최근돌파율 = ((최고현재가(돌파확인틱수, 1) - 기준상단) / 기준상단) * 100 if 기준상단 > 0 else -999
    현재위치율 = ((현재가 - 기준상단) / 기준상단) * 100 if 기준상단 > 0 else -999
    거래대금비율 = 초당거래대금 / 초당거래대금평균(평균틱수) if 초당거래대금평균(평균틱수) > 0 else 0
    체결강도비율 = 체결강도 / 체결강도평균(평균틱수) if 체결강도평균(평균틱수) > 0 else 0
    호가압력 = 매수총잔량 / (매수총잔량 + 매도총잔량) if (매수총잔량 + 매도총잔량) > 0 else 0.5

    기본필터 = self.vars[4] <= 등락율 <= self.vars[5] and 1000 <= 현재가 <= 100000 and 현재가 < VI가격 and not 라운드피겨위5호가이내
    미세돌파 = 미세폭율 <= self.vars[6] and 미세돌파율 >= self.vars[7] and 거래대금비율 >= self.vars[8]
    리테스트 = 기준폭율 <= self.vars[9] and 최근돌파율 >= self.vars[10] and -self.vars[11] <= 현재위치율 <= self.vars[12] and 현재가 >= 기준상단 * (1 - self.vars[11] / 100)
    수급 = 체결강도 >= self.vars[13] and 체결강도비율 >= self.vars[14] and 호가압력 >= self.vars[15] and 초당매수수량 >= 초당매도수량 * self.vars[16]

    if 기본필터 and 수급 and (미세돌파 or 리테스트):
        매수 = True

if 매수:
    self.Buy()
```

## Sell condition full code

```python
# =============================================================================
# CSS_V7_OPT_TICK_S_MASTER_0900_0930
# 1tick 최적화형 매도식: CSS_V7_OPT_VARS_TICK_0900_0930 사용
# =============================================================================
매도 = False

if 시분초 >= 93000:
    매도 = True
elif 수익률 <= self.vars[20]:
    매도 = True
elif 데이터길이 >= int(self.vars[3]):
    평균틱수 = int(self.vars[3])
    체결강도비율 = 체결강도 / 체결강도평균(평균틱수) if 체결강도평균(평균틱수) > 0 else 0
    매도우위 = 초당매도수량 > 초당매수수량 * self.vars[21] and 체결강도비율 <= self.vars[22]
    기능선이탈 = 현재가 < 매수가 * self.vars[23]
    단기이탈 = 보유시간 >= self.vars[24] and 현재가 < 최저현재가(20, 1) * self.vars[25]
    트레일링 = 최고수익률 >= self.vars[26] and 수익률 <= 최고수익률 * self.vars[27]
    시간정체 = 보유시간 >= self.vars[28] and 수익률 < self.vars[29]

    if 기능선이탈 and 매도우위:
        매도 = True
    elif 단기이탈 and 매도우위:
        매도 = True
    elif 트레일링 or 시간정체:
        매도 = True

if 매도:
    self.Sell()
```
