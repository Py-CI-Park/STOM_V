# ============================================================
# C_M_900_1500_W1_B — min 넓은 그물(Wide-net) 계층형 v1  [시드]
#  구조: 시간 4밴드(09:00-09:30 / 09:30-10:30 / 10:30-13:00 / 13:00-15:00)
#        × 시총 4단계(<3000 / 3000~5000 / 5000~10000 / >=10000 — 전체 커버)
#        × 등락율(시총별 상한 차등) — tick W1 과 동일한 조절 변수 세트의 min 판.
#  min 규칙: 분당* 변수 사용 · 평균함수는 데이터길이 가드 · 보유시간 단위=분.
# ============================================================
전일종가       = 현재가 / (1 + (등락율 / 100))
시가등락율     = ((시가 - 전일종가) / 전일종가) * 100 if 전일종가 != 0 else 0
시가대비등락율 = ((현재가 - 시가) / 시가) * 100 if 시가 != 0 else 0
분당순매수금액 = (분당매수수량 - 분당매도수량) * 현재가 / 1_000_000
거래대금비율   = 분당거래대금 / 분당거래대금평균(20) if 데이터길이 >= 21 and 분당거래대금평균(20) > 0 else 1.0
고가근접율     = (현재가 - (고가 - (고가 - 저가) * 0.30)) if (고가 - 저가) > 0 else 1

매수 = True

# ---------- 공통 그물(넓게) ----------
if not (관심종목 == 1):
    매수 = False
elif not (500 <= 현재가 <= 100000):
    매수 = False
elif not (고저평균대비등락율 > -1.0):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False
elif not (당일거래대금 > 100):
    매수 = False

# ---------- B1_장초반 (09:00~09:30) ----------
elif 시분초 < 93000:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- B2_오전추세 (09:30~10:30) ----------
elif 93000 <= 시분초 < 103000:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- B3_중간한산 (10:30~13:00) ----------
elif 103000 <= 시분초 < 130000:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- B4_오후 (13:00~15:00) ----------
elif 130000 <= 시분초 < 150000:
    if 시가총액 < 3000:  # 소형_3000미만
        if not (0.5 <= 등락율 <= 25.0):
            매수 = False
        elif not (-3.0 <= 시가등락율 < 12.0):
            매수 = False
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
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
        elif not (-1.0 <= 시가대비등락율 < 15.0):
            매수 = False
        elif not (분당순매수금액 > 1.0):
            매수 = False
        elif not (거래대금비율 > 1.0):
            매수 = False
        elif not (체결강도 >= 40):
            매수 = False
        elif not (고가근접율 > 0):
            매수 = False
        elif not (전일동시간비 > 0):
            매수 = False

# ---------- 15:00 이후 신규 진입 금지 ----------
else:
    매수 = False

if 매수:
    self.Buy()
