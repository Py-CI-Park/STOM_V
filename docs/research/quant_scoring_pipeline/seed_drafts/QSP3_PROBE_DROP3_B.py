# ============================================================
# QSP2_T_ANCH_900_920_B — anchor 이식 계층형 v1  [QSP2 시드]
#  유래: GATE_r8_4_strength_max_250_B (CLW30 실증 승자 계열, 3년 +0.61%/거래)
#  이식 원칙: anchor 엣지 코어(매수압·체결강도 250 상한·폭발배수·고가근접)는
#  공통 그물에 유지, 시간 4밴드×시총 4단계 리프에 표준 조절절 8종(완화 출발값).
#  anchor 미커버 영역(09:07 이후·시총>=3000억)은 솔버가 데이터로 판정한다.
# ============================================================
전일종가       = 현재가 / (1 + (등락율 / 100))
시가등락율     = ((시가 - 전일종가) / 전일종가) * 100 if 전일종가 != 0 else 0
시가대비등락율 = ((현재가 - 시가) / 시가) * 100 if 시가 != 0 else 0
초당순매수금액 = (초당매수수량 - 초당매도수량) * 현재가 / 1_000_000
거래대금비율   = 초당거래대금 / 초당거래대금평균(30) if 데이터길이 >= 31 and 초당거래대금평균(30) > 0 else 1.0
고가근접율     = (현재가 - (고가 - (고가 - 저가) * 0.20)) if (고가 - 저가) > 0 else 1
VI아래5호가    = VI가격 - VI호가단위 * 5

매수 = True

# ---------- 공통 그물 = anchor 엣지 코어 ----------
if not (관심종목 == 1):
    매수 = False
elif not (1000 < 현재가 <= 50000):        # anchor 가격대
    매수 = False
elif not (고저평균대비등락율 > 0):
    매수 = False
elif not (현재가 < VI아래5호가):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False
elif not (당일거래대금 > 300):            # anchor 902(500)의 완화
    매수 = False
elif not (체결강도 <= 250):               # anchor 상한 — 과열 배제(엣지 코어)
    매수 = False
elif not (초당매수수량 > 매도총잔량 * 0.15):  # anchor 매수압(0.2~0.3)의 완화
    매수 = False

# ---------- B1_초기2분 ----------
elif 시분초 < 90200:
    if 시가총액 < 3000:  # 소형_3000미만
        if True:  # DROP_LEAF 프로브 — B1×소형(<3000억) 진입 차단
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (0.5 <= 등락율 <= 20.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 3.53):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False

# ---------- B2_2_5분 ----------
elif 90200 <= 시분초 < 90500:
    if 시가총액 < 3000:  # 소형_3000미만
        if True:  # DROP_LEAF 프로브 — B2×소형(<3000억) 진입 차단
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 61.5):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (4.13 <= 등락율 <= 20.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 97.9):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False

# ---------- B3_5_10분 ----------
elif 90500 <= 시분초 < 91000:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (5.21 <= 등락율 <= 25.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (4.26 <= 등락율 <= 20.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 5.05):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False

# ---------- B4_10_20분 ----------
elif 91000 <= 시분초 < 92000:
    if 시가총액 < 3000:  # 소형_3000미만
        if True:  # DROP_LEAF 프로브 — B4×소형(<3000억) 진입 차단
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 3000 <= 시가총액 < 5000:  # 중소_3000_5000
        if not (0.5 <= 등락율 <= 22.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 5000 <= 시가총액 < 10000:  # 중형_5000_10000
        if not (0.5 <= 등락율 <= 20.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False
    elif 시가총액 >= 10000:  # 대형_10000이상
        if not (0.5 <= 등락율 <= 15.0):
            매수 = False
        elif not (-2.0 <= 시가등락율 < 8.0):    # anchor 2~4 의 완화
            매수 = False
        elif not (0.0 <= 시가대비등락율 < 10.0): # anchor 0.5~6/3~8 의 완화
            매수 = False
        elif not (초당순매수금액 > 0.5):         # anchor 1 의 완화
            매수 = False
        elif not (거래대금비율 > 1.5):           # anchor 2.0~2.5 의 완화
            매수 = False
        elif not (체결강도 >= 60):               # anchor 70 의 완화
            매수 = False
        elif not (고가근접율 > 0):               # anchor 0.20 고가근접 유지
            매수 = False
        elif not (전일동시간비 > 0):             # anchor 유지
            매수 = False

# ---------- 09:20 이후 ----------
else:
    매수 = False

if 매수:
    self.Buy()
