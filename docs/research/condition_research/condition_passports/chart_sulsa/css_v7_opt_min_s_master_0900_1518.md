# Condition Passport — CSS_V7_OPT_MIN_S_MASTER_0900_1518

| Field | Value |
|---|---|
| condition_id | `CSS_V7_OPT_MIN_S_MASTER_0900_1518` |
| human_name | `1분봉 최적화형 매도식` |
| role | `hypothesis_seed` |
| lane | `min` |
| side | `sell` |
| principle_ids | `P7, P10, P11` |
| time_window | `09:00:00-15:18:00` |
| buy_strategy_id | `CSS_V7_OPT_MIN_B_MASTER_0900_1518` |
| sell_strategy_id | `CSS_V7_OPT_MIN_S_MASTER_0900_1518` |
| buy_code_sha256 | `fed494cac9aab1b4e388458d5a996f275bec254f1cdf260e19a3876d3a27196b` |
| sell_code_sha256 | `4a3e7575bc3ac7397f2543ae3e8a9b58408749e33e28f2f11b338b19d4490db1` |
| oos_status | `none` |
| prior_profit | `none` |
| prior_mdd | `none` |
| prior_trades | `none` |
| promotion_status | `research_only / not_promoted` |
| source | `chart_sulsa_v7_0` (원문 6.5절) |

## Core hypothesis

이 passport는 차트술사 구조론 보고서 v7.0에서 추출한 **무근거 가설 시드**다.
관련 원리: P7, P10, P11. 이 조건식 자체는 `sell` 측이며, 반대 측 코드는 같은 레인의
통합(OPT MASTER) 조건식으로 페어링했다. 모든 임계값은 백테스트로 검증되지 않은
가설이며 검증된 사실로 취급하면 안 된다. oos_status=`none` — OOS 검증 이력이 없다.

## Buy condition full code

```python
# =============================================================================
# CSS_V7_OPT_MIN_B_MASTER_0900_1518
# 1분봉 최적화형 매수식: CSS_V7_OPT_VARS_MIN_0900_1518 사용
# =============================================================================
매수 = False

if 데이터길이 >= int(self.vars[0]) + int(self.vars[2]) + 20 and 90000 <= 시분초 <= 151800 and 관심종목 == 1:
    박스봉수 = int(self.vars[0])
    평균봉수 = int(self.vars[1])
    돌파확인봉수 = int(self.vars[2])
    박스상단 = 최고현재가(박스봉수, 1)
    박스하단 = 최저현재가(박스봉수, 1)
    박스폭율 = ((박스상단 - 박스하단) / 박스하단) * 100 if 박스하단 > 0 else 999
    하단근접율 = ((현재가 - 박스하단) / 박스하단) * 100 if 박스하단 > 0 else 999
    상단돌파율 = ((현재가 - 박스상단) / 박스상단) * 100 if 박스상단 > 0 else -999
    거래대금비율 = 분당거래대금 / 분당거래대금평균(평균봉수) if 분당거래대금평균(평균봉수) > 0 else 0
    체결강도비율 = 체결강도 / 체결강도평균(평균봉수) if 체결강도평균(평균봉수) > 0 else 0

    기준상단 = 최고현재가(박스봉수, 돌파확인봉수)
    기준하단 = 최저현재가(박스봉수, 돌파확인봉수)
    기준폭율 = ((기준상단 - 기준하단) / 기준하단) * 100 if 기준하단 > 0 else 999
    최근돌파율 = ((최고현재가(돌파확인봉수, 1) - 기준상단) / 기준상단) * 100 if 기준상단 > 0 else -999
    현재위치율 = ((현재가 - 기준상단) / 기준상단) * 100 if 기준상단 > 0 else -999

    기본필터 = self.vars[3] <= 등락율 <= self.vars[4] and 1000 <= 현재가 <= 100000 and 당일거래대금 >= self.vars[5] and not 라운드피겨위5호가이내
    박스하단지지 = 박스폭율 <= self.vars[6] and -self.vars[7] <= 하단근접율 <= self.vars[8] and 현재가 >= 박스하단 and 거래대금비율 <= self.vars[9]
    박스상단돌파 = 박스폭율 <= self.vars[10] and 상단돌파율 >= self.vars[11] and 거래대금비율 >= self.vars[12]
    리테스트 = 기준폭율 <= self.vars[13] and 최근돌파율 >= self.vars[14] and -self.vars[15] <= 현재위치율 <= self.vars[16] and 현재가 >= 기준상단 * (1 - self.vars[15] / 100)
    수급 = 체결강도 >= self.vars[17] and 체결강도비율 >= self.vars[18] and 분당매수수량 >= 분당매도수량 * self.vars[19]

    if 기본필터 and 수급 and (박스하단지지 or 박스상단돌파 or 리테스트):
        매수 = True

if 매수:
    self.Buy()
```

## Sell condition full code

```python
# =============================================================================
# CSS_V7_OPT_MIN_S_MASTER_0900_1518
# 1분봉 최적화형 매도식: CSS_V7_OPT_VARS_MIN_0900_1518 사용
# =============================================================================
매도 = False

if 시분초 >= 151800:
    매도 = True
elif 수익률 <= self.vars[25]:
    매도 = True
elif 데이터길이 >= int(self.vars[1]) + 10:
    평균봉수 = int(self.vars[1])
    체결강도비율 = 체결강도 / 체결강도평균(평균봉수) if 체결강도평균(평균봉수) > 0 else 0
    매도우위 = 분당매도수량 > 분당매수수량 * self.vars[26] and 체결강도비율 <= self.vars[27]
    기능선이탈 = 현재가 < 매수가 * self.vars[28]
    단기이탈 = 보유시간 >= self.vars[29] and 현재가 < 최저현재가(10, 1) * self.vars[30]
    트레일링 = 최고수익률 >= self.vars[31] and 수익률 <= 최고수익률 * self.vars[32]
    시간정체 = 보유시간 >= self.vars[33] and 수익률 < self.vars[34]
    이평이탈 = 현재가 < 이동평균(20) and 이동평균(5) < 이동평균(20) and 수익률 <= self.vars[35]

    if 기능선이탈 and 매도우위:
        매도 = True
    elif 단기이탈 and 매도우위:
        매도 = True
    elif 이평이탈:
        매도 = True
    elif 트레일링 or 시간정체:
        매도 = True

if 매도:
    self.Sell()
```
