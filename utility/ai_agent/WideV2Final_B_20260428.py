매수 = True

if 관심종목 != 1:
    매수 = False
elif not (0 < 현재가 <= 50000):
    매수 = False
elif not (90000 <= 시분초 <= 92800):
    매수 = False
elif not (0 < 등락율 <= 25):
    매수 = False
elif not (당일거래대금 > 100):
    매수 = False
elif 라운드피겨위5호가이내:
    매수 = False

# WideV1RetentionCand5_20260422__cand003 - 자동 생성 필터 결합
# 생성일: 2026-04-22 21:35:43
if 매수:
    if 66.999 <= 현재가 < 2_580:
        매수 = False

# WideV1IterationV2_20260423__cand005 - 자동 생성 필터 결합
# 생성일: 2026-04-23 10:35:12
if 매수:
    if 66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4:
        매수 = False

# WideV1Final_B_20260425 - 자동 생성 필터 결합
# 생성일: 2026-04-26 07:53:10
if 매수:
    if 66.999 <= 시가총액 < 2_580 and 등락율 > 4.83:
        매수 = False

# WideV2Final_B_20260428 - 자동 생성 필터 결합
# 생성일: 2026-04-28 21:58:09
if 매수:
    if 66.999 <= 시가총액 < 2_580 and 등락율 > 3.535:
        매수 = False

if 매수:
    self.Buy()
