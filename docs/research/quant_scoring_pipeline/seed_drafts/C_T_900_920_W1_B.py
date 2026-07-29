# ============================================================
# C_T_900_920_W1_B — tick 넓은 그물(Wide-net) 계층형 v1  [초안]
#  구조: 시간 4밴드(09:00-02/02-05/05-10/10-20)
#        × 시총 4단계(<3000 / 3000~5000 / 5000~10000 / >=10000 — 전체 커버)
#        × 등락율·시가등락율·시가대비등락율(넓은 경계)
#  목적: 최대한 많은 거래를 발생시켜 '수익률 라벨' 데이터셋을 만들고,
#        세그먼트 분석 결과로 리프(밴드×시총)별 경계를 조여 가는 출발점.
#  모든 리프가 같은 조절 변수 세트를 쓴다(분석→수정 손잡이 통일).
# ============================================================
전일종가       = 현재가 / (1 + (등락율 / 100))
시가등락율     = ((시가 - 전일종가) / 전일종가) * 100 if 전일종가 != 0 else 0
시가대비등락율 = ((현재가 - 시가) / 시가) * 100 if 시가 != 0 else 0
초당순매수금액 = (초당매수수량 - 초당매도수량) * 현재가 / 1_000_000
거래대금비율   = 초당거래대금 / 초당거래대금평균(30) if 데이터길이 >= 31 and 초당거래대금평균(30) > 0 else 1.0
고가근접율     = (현재가 - (고가 - (고가 - 저가) * 0.30)) if (고가 - 저가) > 0 else 1
VI아래5호가    = VI가격 - VI호가단위 * 5

매수 = True

# ---------- 공통 그물(넓게) ----------
if not (관심종목 == 1):
    매수 = False
elif not (500 <= 현재가 <= 100000):
    매수 = False
elif not (고저평균대비등락율 > -1.0):
    매수 = False
elif not (현재가 < VI아래5호가):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False
elif not (당일거래대금 > 100):
    매수 = False

# ---------- B1_초기2분 (09:00:00~09:02:00) ----------
elif 시분초 < 90200:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 10.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 10.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 10.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 10.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (0.5 <= 등락율 <= 20.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 10.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 10.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 10.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 10.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- B2_2~5분 (09:02:00~09:05:00) ----------
elif 90200 <= 시분초 < 90500:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 12.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 12.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (0.5 <= 등락율 <= 20.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 12.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 12.0):
            매수 = False
        elif not (초당순매수금액 > 0.5):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- B3_5~10분 (09:05:00~09:10:00) ----------
elif 90500 <= 시분초 < 91000:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 14.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 14.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (0.5 <= 등락율 <= 20.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 14.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 14.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- B4_10~20분 (09:10:00~09:20:00) ----------
elif 91000 <= 시분초 < 92000:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (0.5 <= 등락율 <= 20.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (초당순매수금액 > 0.3):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 35):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- 09:20:00 이후 ----------
else:
    매수 = False

if 매수:
    self.Buy()
