"""챔피언 RR8_12 매수식 39 유니크 절 — 정의·족·티어·벡터 술어 (사전등록 §3).

봉인 원문: strategy.db stockbuy 'ALP_V4_RR8_12' 전략코드,
buy_code_sha256 348c518145cbf91e7123f9a8f3498fc35b36d269cce3e3e57154bd191d3ea97a
(출처 정본 condition_passports/rr8_12_turnover_min_902_1.5.md). 902/905 병합
다분기 원자 50절을 정확-문자열 중복제거해 39 유니크(사전등록 §3.1 표 그대로).

절 극성(polarity) 규약: "절 만족" = 그 온셋이 해당 가드를 통과한다(매수-우호 방향).
- `elif not (P): 매수=False` 형태 → 만족 = P 참(#4 제외 전부 이 형태).
- `elif 라운드피겨위5호가이내: 매수=False` (#4) → 만족 = 라운드피겨위5호가이내 거짓.
이 규약이 Δ(c)≥+0.10%p 를 "이 필터를 통과하면 출구 손익이 더 낫다"로 해석 가능케 한다
(사전등록 §7 순-load-bearing 방향). 각 절 spec.polarity_note 에 명기.

절 값 = 온셋 시점 엔진 네임스페이스에서 각 술어를 평가한 불리언(사전등록 §6).
파생 함수 의미론(trade/base_strategy.py 실측):
- 당일거래대금각도(30)/누적초당매수수량(30)/누적초당매도수량(30) = avg_list=[30]이므로
  add_rolling_data 사전계산 파생 컬럼을 그대로 읽음(_Parameter_Area/_Parameter_Angle).
  alpha_lab.dataset.derived.compute_derived_tick 와 원소 동치(parity.py 검증 완료).
- 초당거래대금평균(30) = int(사전계산 초당거래대금평균)(_초당거래대금평균 의 int() 래핑).
- 초당거래대금N(1) = 직전 관측 행 초당거래대금(_Parameter_Previous, indexn-1; 첫 행 0).
- 시분초 = index % 1_000_000 (engine backengine_kiwoom_tick.py:26).
- 로컬 정의(전일종가/시가등락율/시가대비등락율/초당순매수금액/VI아래5호가) = 원문 헤더
  same-row 산술(build_local_definitions).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Sequence, Tuple

import numpy as np

__all__ = [
    "CHAMPION_BUY_SHA256",
    "CHAMPION_BUY_STRATEGY_NAME",
    "CLAUSE_SPECS",
    "FAMILIES",
    "LOCAL_DEF_SPECS",
    "NAMESPACE_SYMBOLS",
    "PURE_DUPLICATE_PAIRS",
    "RAW_EXPR",
    "ClauseSpec",
    "build_local_definitions",
    "evaluate_clause_bits",
    "spec_by_num",
]

CHAMPION_BUY_SHA256 = (
    "348c518145cbf91e7123f9a8f3498fc35b36d269cce3e3e57154bd191d3ea97a"
)
CHAMPION_BUY_STRATEGY_NAME = "ALP_V4_RR8_12"

Array = np.ndarray
Predicate = Callable[[Mapping[str, Array]], Array]

# 온셋 네임스페이스가 제공해야 하는 심볼(온셋 피처 행렬 컬럼). onset_features 가 채운다.
NAMESPACE_SYMBOLS: Tuple[str, ...] = (
    # 저장 원천 컬럼(직접 판독).
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금", "체결강도",
    "초당매수수량", "초당매도수량", "전일비", "회전율", "전일동시간비", "시가총액",
    "라운드피겨위5호가이내", "VI가격", "VI호가단위", "초당거래대금",
    "고저평균대비등락율", "매도총잔량", "매수총잔량", "관심종목",
    # 루프 파생.
    "시분초",
    # 엔진 파생 18항(avg=30) 중 매수식 사용분.
    "당일거래대금각도30", "초당거래대금평균30", "누적초당매수수량30", "누적초당매도수량30",
    # N 지연.
    "초당거래대금N1",
    # 로컬 정의(build_local_definitions 가 채움).
    "전일종가", "시가등락율", "시가대비등락율", "초당순매수금액", "VI아래5호가",
)

# 순수 중복 쌍(정확-문자열은 다르나 술어 동치) — 사전등록 §8 게이트에서 1절로 병합.
PURE_DUPLICATE_PAIRS: Tuple[Tuple[int, int], ...] = ((15, 39),)


# ---------------------------------------------------------------------------
# 로컬 정의(원문 헤더 same-row 산술) — F2 게이트의 패리티 대상.
# ---------------------------------------------------------------------------

def _prev_close(ns: Mapping[str, Array]) -> Array:
    """전일종가 = 현재가 / (1 + 등락율/100). 원문 헤더 line 4."""
    return ns["현재가"] / (1.0 + ns["등락율"] / 100.0)


def _open_change(ns: Mapping[str, Array]) -> Array:
    """시가등락율 = ((시가 - 전일종가) / 전일종가) * 100. 원문 헤더 line 5."""
    prev = _prev_close(ns)
    return ((ns["시가"] - prev) / prev) * 100.0


def _open_vs_change(ns: Mapping[str, Array]) -> Array:
    """시가대비등락율 = ((현재가 - 시가) / 시가) * 100. 원문 헤더 line 6."""
    return ((ns["현재가"] - ns["시가"]) / ns["시가"]) * 100.0


def _net_buy_amount(ns: Mapping[str, Array]) -> Array:
    """초당순매수금액 = (초당매수수량 - 초당매도수량) * 현재가 / 1_000_000. 헤더 line 7."""
    return (ns["초당매수수량"] - ns["초당매도수량"]) * ns["현재가"] / 1_000_000.0


def _vi_below5(ns: Mapping[str, Array]) -> Array:
    """VI아래5호가 = VI가격 - VI호가단위 * 5. 원문 line 18."""
    return ns["VI가격"] - ns["VI호가단위"] * 5.0


# F2 게이트 대상: 이름 → (재현식, 원문 참조, 사용하는 저장 심볼).
LOCAL_DEF_SPECS: Tuple[Tuple[str, Predicate, str, Tuple[str, ...]], ...] = (
    ("전일종가", _prev_close, "현재가 / (1 + 등락율/100)", ("현재가", "등락율")),
    ("시가등락율", _open_change, "((시가 - 전일종가)/전일종가)*100",
     ("시가", "현재가", "등락율")),
    ("시가대비등락율", _open_vs_change, "((현재가 - 시가)/시가)*100", ("현재가", "시가")),
    ("초당순매수금액", _net_buy_amount,
     "(초당매수수량 - 초당매도수량)*현재가/1_000_000",
     ("초당매수수량", "초당매도수량", "현재가")),
    ("VI아래5호가", _vi_below5, "VI가격 - VI호가단위*5", ("VI가격", "VI호가단위")),
)


def build_local_definitions(ns: Dict[str, Array]) -> Dict[str, Array]:
    """저장 심볼이 채워진 ns 에 로컬 정의 5종을 원문 그대로 추가한다(제자리 갱신 후 반환).

    나눗셈 분모 0(등락율=-100·시가=0·전일종가=0)은 numpy 규약대로 inf/nan 을 낳고,
    하위 절 비교에서 nan 은 False 로 평가된다(엔진 raise 대신 정직 미충족). 온셋 행은
    유효 호가·양의 가격이라 실측상 발생하지 않으며, 발생 시 그 절만 미충족 처리한다.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        ns["전일종가"] = _prev_close(ns)
        ns["시가등락율"] = _open_change(ns)
        ns["시가대비등락율"] = _open_vs_change(ns)
        ns["초당순매수금액"] = _net_buy_amount(ns)
        ns["VI아래5호가"] = _vi_below5(ns)
    return ns


# ---------------------------------------------------------------------------
# 절 spec + 벡터 술어(만족 = 가드 통과 = 매수-우호 방향).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClauseSpec:
    """39 유니크 절 하나의 정의·메타·벡터 술어."""

    num: int                       # 사전등록 §3.1 표 # (1..39).
    text: str                      # 정규화 술어 텍스트(만족 방향).
    cat: str                       # W5 카테고리.
    tier: str                      # M-direct | M-derived | M-namespace | U-hold.
    family: str                    # 밑변수 족(§8).
    mult: int                      # 원자 50절 중 등장 횟수.
    symbols: Tuple[str, ...]       # 사용하는 네임스페이스 심볼.
    predicate: Predicate = field(repr=False)  # ns -> bool array(만족).
    polarity_note: str = ""        # 극성 설명.


def _between(x: Array, lo: float, hi: float, *, lo_inc: bool, hi_inc: bool) -> Array:
    """lo (< or <=) x (< or <=) hi 대역 — 원문 부등호 포함성 그대로."""
    left = x >= lo if lo_inc else x > lo
    right = x <= hi if hi_inc else x < hi
    return left & right


def _ratio_gt(num: Array, denom: Array, thr: float) -> Array:
    """num/denom > thr — 분모<=0 은 미충족(False). 단독 술어 나눗셈 가드(§6)."""
    out = np.zeros(num.shape, dtype=bool)
    ok = denom > 0.0
    out[ok] = (num[ok] / denom[ok]) > thr
    return out


# 각 술어(만족 = 매수-우호). 인덱스 주석 = 저장 컬럼(setting_base list_stock_tick).
def _c1(ns):   return _between(ns["초당순매수금액"], 1.0, 1000.0, lo_inc=False, hi_inc=False)
def _c2(ns):   return ns["고저평균대비등락율"] > 0.0
def _c3(ns):   return ns["당일거래대금각도30"] < 30.0
def _c4(ns):   return ns["라운드피겨위5호가이내"] == 0.0   # 만족 = 라운드피겨 밖(§ 극성).
def _c5(ns):   return ns["시가총액"] < 3000.0
def _c6(ns):   return ns["시분초"] < 90200
def _c7(ns):   return ns["전일동시간비"] > 0.0
def _c8(ns):   return ns["체결강도"] <= 300.0
def _c9(ns):   return ns["체결강도"] >= 70.0
def _c10(ns):  return ns["현재가"] < ns["VI아래5호가"]
def _c11(ns):  return ns["현재가"] > (ns["고가"] - (ns["고가"] - ns["저가"]) * 0.20)
def _c12(ns):  return _between(ns["시가등락율"], 0.0, 8.0, lo_inc=True, hi_inc=False)
def _c13(ns):  return _between(ns["시가대비등락율"], 0.5, 6.0, lo_inc=True, hi_inc=False)
def _c14(ns):  return _between(ns["등락율"], 1.0, 8.0, lo_inc=False, hi_inc=True)
def _c15(ns):  return ns["회전율"] > 1.5              # 1.5 < 회전율 ≡ #39.
def _c16(ns):  return _between(ns["현재가"], 1000.0, 30000.0, lo_inc=False, hi_inc=True)
def _c17(ns):  return _between(ns["현재가"], 1000.0, 50000.0, lo_inc=False, hi_inc=True)
def _c18(ns):  return _between(ns["등락율"], 2.0, 15.0, lo_inc=False, hi_inc=True)
def _c19(ns):  return _between(ns["시가등락율"], 2.0, 4.0, lo_inc=True, hi_inc=False)
def _c20(ns):  return _between(ns["시가대비등락율"], 3.0, 8.0, lo_inc=True, hi_inc=False)
def _c21(ns):  return _between(ns["시분초"], 90200, 90700, lo_inc=True, hi_inc=False)
def _c22(ns):  return ns["관심종목"] == 1
def _c23(ns):  return ns["누적초당매도수량30"] * 1.0 < ns["누적초당매수수량30"] * 1.0
def _c24(ns):  return ns["누적초당매수수량30"] * 0.5 < ns["누적초당매도수량30"] * 1.0
def _c25(ns):  return ns["당일거래대금"] > 5 * 100
def _c26(ns):  return ns["당일거래대금"] > 50 * 100
def _c27(ns):  return ns["당일거래대금각도30"] > 10.0
def _c28(ns):  return ns["당일거래대금각도30"] > 5.0
def _c29(ns):  return ns["매도총잔량"] * 0.10 < ns["매수총잔량"] * 1.0
def _c30(ns):  return ns["매도총잔량"] < ns["매수총잔량"] * 2.0
def _c31(ns):  return ns["매도총잔량"] > ns["매수총잔량"] * 0.10
def _c32(ns):  return ns["전일비"] > 0.0
def _c33(ns):  return ns["전일비"] > 5.0
def _c34(ns):  return _ratio_gt(ns["초당거래대금"], ns["초당거래대금평균30"], 2.0)
def _c35(ns):  return _ratio_gt(ns["초당거래대금"], ns["초당거래대금평균30"], 2.5)
def _c36(ns):  return ns["초당거래대금"] > ns["초당거래대금N1"] * 1.0
def _c37(ns):  return ns["초당매수수량"] > ns["매도총잔량"] * 0.20
def _c38(ns):  return ns["초당매수수량"] > ns["매도총잔량"] * 0.30
def _c39(ns):  return ns["회전율"] > 1.5              # #15 와 동일 술어.


# (num, text, cat, tier, family, mult, symbols, predicate, polarity_note)
_ROWS: Tuple[tuple, ...] = (
    (1, "1 < 초당순매수금액 < 1000", "quote_qty", "M-namespace", "초당순매수금액", 2,
     ("초당순매수금액",), _c1, "not(P)→만족=P"),
    (2, "고저평균대비등락율 > 0", "change_band", "M-direct", "고저평균대비등락율", 2,
     ("고저평균대비등락율",), _c2, "not(P)→만족=P"),
    (3, "당일거래대금각도(30) < 30", "surge_value", "M-derived", "당일거래대금각도(30)", 2,
     ("당일거래대금각도30",), _c3, "not(P)→만족=P"),
    (4, "라운드피겨위5호가이내 == False", "vi_round", "M-direct", "라운드피겨", 2,
     ("라운드피겨위5호가이내",), _c4, "bare-truthy 제외 가드 → 만족=거짓"),
    (5, "시가총액 < 3000", "cap_price", "M-direct", "시가총액", 2,
     ("시가총액",), _c5, "분기 if 시가총액<3000 → 만족=참"),
    (6, "시분초 < 90200", "time_gate", "M-namespace", "시분초", 2,
     ("시분초",), _c6, "분기·재확인 → 만족=참"),
    (7, "전일동시간비 > 0", "cap_price", "M-direct", "전일동시간비", 2,
     ("전일동시간비",), _c7, "not(P)→만족=P"),
    (8, "체결강도 <= 300", "exec_strength", "M-direct", "체결강도", 2,
     ("체결강도",), _c8, "not(P)→만족=P"),
    (9, "체결강도 >= 70", "exec_strength", "M-direct", "체결강도", 2,
     ("체결강도",), _c9, "not(P)→만족=P"),
    (10, "현재가 < VI아래5호가", "vi_round", "U-hold", "VI 상대가", 2,
     ("현재가", "VI아래5호가"), _c10, "not(P)→만족=P"),
    (11, "현재가 > 고가 - (고가 - 저가) * 0.2", "breakout_ma", "M-direct", "고저 돌파", 2,
     ("현재가", "고가", "저가"), _c11, "not(P)→만족=P"),
    (12, "0.0 <= 시가등락율 < 8.0", "change_band", "U-hold", "시가등락율", 1,
     ("시가등락율",), _c12, "not(P)→만족=P"),
    (13, "0.5 <= 시가대비등락율 < 6.0", "change_band", "U-hold", "시가대비등락율", 1,
     ("시가대비등락율",), _c13, "not(P)→만족=P"),
    (14, "1.0 < 등락율 <= 8.0", "change_band", "M-direct", "등락율", 1,
     ("등락율",), _c14, "not(P)→만족=P"),
    (15, "1.5 < 회전율", "cap_price", "M-direct", "회전율", 1,
     ("회전율",), _c15, "not(P)→만족=P (#39 와 순수 중복)"),
    (16, "1000 < 현재가 <= 30000", "cap_price", "M-direct", "현재가 대역", 1,
     ("현재가",), _c16, "not(P)→만족=P"),
    (17, "1000 < 현재가 <= 50000", "cap_price", "M-direct", "현재가 대역", 1,
     ("현재가",), _c17, "not(P)→만족=P"),
    (18, "2.0 < 등락율 <= 15.0", "change_band", "M-direct", "등락율", 1,
     ("등락율",), _c18, "not(P)→만족=P"),
    (19, "2.0 <= 시가등락율 < 4.0", "change_band", "U-hold", "시가등락율", 1,
     ("시가등락율",), _c19, "not(P)→만족=P"),
    (20, "3.0 <= 시가대비등락율 < 8.0", "change_band", "U-hold", "시가대비등락율", 1,
     ("시가대비등락율",), _c20, "not(P)→만족=P"),
    (21, "90200 <= 시분초 < 90700", "time_gate", "M-namespace", "시분초", 1,
     ("시분초",), _c21, "분기 → 만족=참"),
    (22, "관심종목 == 1", "time_gate", "M-direct", "관심종목", 1,
     ("관심종목",), _c22, "not(P)→만족=P (유니버스 조건부 §4.1)"),
    (23, "누적초당매도수량(30)*1.0 < 누적초당매수수량(30)*1.0", "quote_qty", "M-derived",
     "누적초당(30) 비", 1, ("누적초당매도수량30", "누적초당매수수량30"), _c23, "not(P)→만족=P"),
    (24, "누적초당매수수량(30)*0.5 < 누적초당매도수량(30)*1.0", "quote_qty", "M-derived",
     "누적초당(30) 비", 1, ("누적초당매수수량30", "누적초당매도수량30"), _c24, "not(P)→만족=P"),
    (25, "당일거래대금 > 5 * 100", "surge_value", "M-direct", "당일거래대금(수준)", 1,
     ("당일거래대금",), _c25, "not(P)→만족=P"),
    (26, "당일거래대금 > 50 * 100", "surge_value", "M-direct", "당일거래대금(수준)", 1,
     ("당일거래대금",), _c26, "not(P)→만족=P"),
    (27, "당일거래대금각도(30) > 10", "surge_value", "M-derived", "당일거래대금각도(30)", 1,
     ("당일거래대금각도30",), _c27, "not(P)→만족=P"),
    (28, "당일거래대금각도(30) > 5", "surge_value", "M-derived", "당일거래대금각도(30)", 1,
     ("당일거래대금각도30",), _c28, "not(P)→만족=P"),
    (29, "매도총잔량*0.1 < 매수총잔량*1.0", "quote_qty", "M-direct", "잔량비(매도총/매수총)", 1,
     ("매도총잔량", "매수총잔량"), _c29, "not(P)→만족=P"),
    (30, "매도총잔량 < 매수총잔량*2.0", "quote_qty", "M-direct", "잔량비(매도총/매수총)", 1,
     ("매도총잔량", "매수총잔량"), _c30, "not(P)→만족=P"),
    (31, "매도총잔량 > 매수총잔량*0.1", "quote_qty", "M-direct", "잔량비(매도총/매수총)", 1,
     ("매도총잔량", "매수총잔량"), _c31, "not(P)→만족=P"),
    (32, "전일비 > 0", "cap_price", "M-direct", "전일비", 1,
     ("전일비",), _c32, "not(P)→만족=P"),
    (33, "전일비 > 5", "cap_price", "M-direct", "전일비", 1,
     ("전일비",), _c33, "not(P)→만족=P"),
    (34, "초당거래대금 / 초당거래대금평균(30) > 2.0", "surge_value", "M-derived", "초당거래대금비", 1,
     ("초당거래대금", "초당거래대금평균30"), _c34, "not(P)→만족=P; 분모<=0 미충족"),
    (35, "초당거래대금 / 초당거래대금평균(30) > 2.5", "surge_value", "M-derived", "초당거래대금비", 1,
     ("초당거래대금", "초당거래대금평균30"), _c35, "not(P)→만족=P; 분모<=0 미충족"),
    (36, "초당거래대금 > 초당거래대금N(1) * 1.0", "surge_value", "U-hold", "초당거래대금비", 1,
     ("초당거래대금", "초당거래대금N1"), _c36, "not(P)→만족=P"),
    (37, "초당매수수량 > 매도총잔량*0.2", "quote_qty", "M-direct", "초당매수수량 vs 매도총잔량", 1,
     ("초당매수수량", "매도총잔량"), _c37, "not(P)→만족=P"),
    (38, "초당매수수량 > 매도총잔량*0.3", "quote_qty", "M-direct", "초당매수수량 vs 매도총잔량", 1,
     ("초당매수수량", "매도총잔량"), _c38, "not(P)→만족=P"),
    (39, "회전율 > 1.5", "cap_price", "M-direct", "회전율", 1,
     ("회전율",), _c39, "not(P)→만족=P (#15 와 순수 중복)"),
)

CLAUSE_SPECS: Tuple[ClauseSpec, ...] = tuple(
    ClauseSpec(num=r[0], text=r[1], cat=r[2], tier=r[3], family=r[4], mult=r[5],
               symbols=r[6], predicate=r[7], polarity_note=r[8])
    for r in _ROWS
)

# 절 # → 만족(매수-우호) 방향 스칼라 평가식(원문 술어). §6 P3 재현 게이트가 온셋별
# 스칼라 exec 경로로 이 식을 평가해 벡터 술어(_cN)와 100% 일치를 검정한다. #4 만
# bare-truthy 제외 가드라 not 로 뒤집는다(만족=라운드피겨 밖); 나머지는 원문 그대로.
RAW_EXPR: Dict[int, str] = {
    1: "1 < 초당순매수금액 < 1000",
    2: "고저평균대비등락율 > 0",
    3: "당일거래대금각도(30) < 30",
    4: "not 라운드피겨위5호가이내",
    5: "시가총액 < 3000",
    6: "시분초 < 90200",
    7: "전일동시간비 > 0",
    8: "체결강도 <= 300",
    9: "체결강도 >= 70",
    10: "현재가 < VI아래5호가",
    11: "현재가 > (고가 - (고가 - 저가) * 0.20)",
    12: "0.0 <= 시가등락율 < 8.0",
    13: "0.5 <= 시가대비등락율 < 6.0",
    14: "1.0 < 등락율 <= 8.0",
    15: "1.5 < 회전율",
    16: "1000 < 현재가 <= 30000",
    17: "1000 < 현재가 <= 50000",
    18: "2.0 < 등락율 <= 15.0",
    19: "2.0 <= 시가등락율 < 4.0",
    20: "3.0 <= 시가대비등락율 < 8.0",
    21: "90200 <= 시분초 < 90700",
    22: "관심종목 == 1",
    23: "누적초당매도수량(30) * 1.0 < 누적초당매수수량(30) * 1.0",
    24: "누적초당매수수량(30) * 0.5 < 누적초당매도수량(30) * 1.0",
    25: "당일거래대금 > 5 * 100",
    26: "당일거래대금 > 50 * 100",
    27: "당일거래대금각도(30) > 10",
    28: "당일거래대금각도(30) > 5",
    29: "매도총잔량 * 0.10 < 매수총잔량 * 1.0",
    30: "매도총잔량 < 매수총잔량 * 2.0",
    31: "매도총잔량 > 매수총잔량 * 0.10",
    32: "전일비 > 0",
    33: "전일비 > 5",
    34: "초당거래대금 / 초당거래대금평균(30) > 2.0",
    35: "초당거래대금 / 초당거래대금평균(30) > 2.5",
    36: "초당거래대금 > 초당거래대금N(1) * 1.0",
    37: "초당매수수량 > 매도총잔량 * 0.20",
    38: "초당매수수량 > 매도총잔량 * 0.30",
    39: "회전율 > 1.5",
}

# 족(밑변수) → 소속 절 # (사전등록 §8 표).
FAMILIES: Dict[str, Tuple[int, ...]] = {}
for _spec in CLAUSE_SPECS:
    FAMILIES.setdefault(_spec.family, tuple())
    FAMILIES[_spec.family] = FAMILIES[_spec.family] + (_spec.num,)


def spec_by_num(num: int) -> ClauseSpec:
    for spec in CLAUSE_SPECS:
        if spec.num == num:
            return spec
    raise KeyError(f"절 #{num} 없음")


def evaluate_clause_bits(
    ns: Mapping[str, Array], specs: Sequence[ClauseSpec] = CLAUSE_SPECS
) -> Dict[int, Array]:
    """네임스페이스 ns 위에서 각 절 술어를 벡터 평가 → {절 # : bool 배열(만족)}.

    ns 는 NAMESPACE_SYMBOLS 를 모두 포함해야 한다(onset_features.build_onset_namespace
    가 채운 뒤 build_local_definitions 통과분).
    """
    return {spec.num: np.asarray(spec.predicate(ns), dtype=bool) for spec in specs}
