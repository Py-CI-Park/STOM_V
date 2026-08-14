"""HOF3 — 챔피언 매수식에 **밴드 3(09:05~09:20) 전용 절 집합**을 붙인다.

## 왜 외삽인가

챔피언은 이미 2밴드 전략이고, 밴드 1→2 사이에 문턱이 **일관된 방향**으로
움직인다: 누적 활동량(당일거래대금·전일비·시가대비등락율) 요구는 오르고,
순간 급등(초당거래대금 배수·체결강도) 요구는 내린다. 장이 진행될수록 누적은
자연히 커지고 급등은 드물어지기 때문이다.

밴드 3 문턱을 그 이동의 **한 걸음 더**에 두는 것이 HOF3 의 가설이다.
자유도는 **스칼라 `k` 하나** — 무작위 탐색이 아니다.

사전 등록: `docs/research/quant_scoring_pipeline/2026-08-10_HOF3_사전등록.md`

## 규율

- 밴드 1·2 는 **한 글자도 바꾸지 않는다**(헌법 7항). 바뀌는 것은 밴드 3 뿐이다.
- 원본 코드는 수정하지 않는다 — 항상 새 문자열을 만든다.
- 시간창 상한 92000 을 넘길 수 없다(사용자 확정 2026-08-10).
"""

from __future__ import annotations

from typing import Final

#: 밴드 3 이 붙을 자리 — 챔피언 원문의 "09:05:00 이후" 차단 절.
TAIL_ANCHOR: Final = "else:\n    매수 = False"

#: 삽입 표식 — 이미 밴드 3 이 붙은 코드를 다시 붙이는 것을 막는다.
MARKER: Final = "# HOF3 밴드 3"

#: 사용자 확정(2026-08-10): 09:20 이 최대.
BAND3_START: Final = 90500
BAND3_END: Final = 92000


def band3_params(k: float) -> dict:
    """외삽 계수 `k` → 밴드 3 문턱. `k=0` 이면 밴드 2 문턱과 같다.

    사전 등록 §3 의 식을 그대로 옮긴 것이다. 여기서 식을 바꾸면 사후 조정이다.
    """
    if k < 0:
        raise ValueError("k 는 0 이상이어야 한다 — 음수는 밴드 1 방향 역행이다")
    return {
        "k": float(k),
        "거래대금하한": 5000.0 * (10.0 ** k),
        "전일비하한": 5.0 + 5.0 * k,
        "시가대비등락율하한": 3.0 + 2.5 * k,
        "거래대금각도하한": 5.0 + 4.0 * k,
        "등락율하한": 2.0 + 1.0 * k,
        "초당매수비": 0.30 + 0.10 * k,
        "초당거래대금배수": max(1.0, 2.0 - 1.0 * k),
        "체결강도하한": max(20.0, 50.0 - 50.0 * k),
        "회전율하한": max(0.5, 1.5 - 0.5 * k),
        "현재가상한": 30000.0,
    }


def render_band3_block(k: float, *, start: int = BAND3_START,
                       end: int = BAND3_END) -> str:
    """밴드 3 절 블록을 만든다(들여쓰기 포함, 앞뒤 개행 없음)."""
    if not (BAND3_START <= start < end <= BAND3_END):
        raise ValueError(
            f"밴드 3 창 {start}~{end} 은 허용 범위 [{BAND3_START}, {BAND3_END}] 밖이다 "
            "— 사용자 확정: 09:20 이 최대")
    p = band3_params(k)
    return f"""# ---------- 09:05:00 ~ 09:20:00 (밴드 3 · {MARKER} k={p['k']:g}) ----------
elif {start} <= 시분초 < {end}:
    if not (1000 < 현재가 <= {p['현재가상한']:g}):
        매수 = False
    elif not ({p['등락율하한']:g} < 등락율 <= 15.0):
        매수 = False
    elif not (고저평균대비등락율 > 0):
        매수 = False
    elif not (현재가 < VI아래5호가):
        매수 = False
    elif 라운드피겨위5호가이내:
        매수 = False
    elif not (초당거래대금 > 초당거래대금N(1) * 1.0):
        매수 = False
    else:
        if 시가총액 < 3000:
            if not (0.0 <= 시가등락율 < 8.0):
                매수 = False
            elif not ({p['시가대비등락율하한']:g} <= 시가대비등락율 < 8.0):
                매수 = False
            elif not (1 < 초당순매수금액 < 1000):
                매수 = False
            elif not (현재가 > (고가 - (고가 - 저가) * 0.20)):
                매수 = False
            elif not (전일비 > {p['전일비하한']:g} and 전일동시간비 > 0):
                매수 = False
            elif not (회전율 > {p['회전율하한']:g}):
                매수 = False
            elif not (당일거래대금 > {p['거래대금하한']:g}):
                매수 = False
            elif not (당일거래대금각도(30) > {p['거래대금각도하한']:g} and 당일거래대금각도(30) < 30):
                매수 = False
            elif not (초당거래대금 / 초당거래대금평균(30) > {p['초당거래대금배수']:g}):
                매수 = False
            elif not (초당매수수량 > 매도총잔량 * {p['초당매수비']:g}):
                매수 = False
            elif not (매도총잔량 * 0.10 < 매수총잔량 * 1.0):
                매수 = False
            elif not (누적초당매수수량(30) * 0.5 < 누적초당매도수량(30) < 누적초당매수수량(30) * 1.0):
                매수 = False
            elif not (체결강도 >= {p['체결강도하한']:g} and 체결강도 <= 300):
                매수 = False
        else:
            매수 = False


"""


def render_swap_block(*, start: int = BAND3_START, end: int = BAND3_END) -> str:
    """대조군 — **밴드 1(902) 절 집합**을 밴드 3 시간대에 그대로 적용한다.

    외삽 가설이 맞다면 이것은 나빠야 한다(밴드 1 문턱은 장 시작 2분용이다).
    가설이 틀린 방향까지 재는 것이 대조군의 값이다.
    """
    return f"""# ---------- 09:05:00 ~ 09:20:00 (밴드 3 · {MARKER} swap=902) ----------
elif {start} <= 시분초 < {end}:
    if not (1000 < 현재가 <= 50000):
        매수 = False
    elif not (1.0 < 등락율 <= 8.0):
        매수 = False
    elif not (고저평균대비등락율 > 0):
        매수 = False
    elif not (현재가 < VI아래5호가):
        매수 = False
    elif 라운드피겨위5호가이내:
        매수 = False
    else:
        if 시가총액 < 3000:
            if not (1.0 <= 시가등락율 < 4.0):
                매수 = False
            elif not (0.5 <= 시가대비등락율 < 6.0):
                매수 = False
            elif not (1 < 초당순매수금액 < 1000):
                매수 = False
            elif not (현재가 > (고가 - (고가 - 저가) * 0.20)):
                매수 = False
            elif not (전일비 > 0 and 전일동시간비 > 0):
                매수 = False
            elif not (회전율 > 2):
                매수 = False
            elif not (당일거래대금 > 5 * 100):
                매수 = False
            elif not (당일거래대금각도(30) > 1 and 당일거래대금각도(30) < 30):
                매수 = False
            elif not (초당거래대금 / 초당거래대금평균(30) > 3.0):
                매수 = False
            elif not (초당매수수량 > 매도총잔량 * 0.20):
                매수 = False
            elif not (매도총잔량 > 매수총잔량 * 0.10 and 매도총잔량 < 매수총잔량 * 2.0):
                매수 = False
            elif not (체결강도 >= 100 and 체결강도 <= 300):
                매수 = False
        else:
            매수 = False


"""


def attach_band3(code: str, cell: str, *, start: int = BAND3_START,
                 end: int = BAND3_END) -> str:
    """챔피언 코드에 밴드 3 을 붙인 **새 코드**를 돌려준다.

    `cell` 은 `"swap"` 이거나 외삽 계수 문자열(`"0.5"`, `"1"` …)이다.
    밴드 1·2 는 손대지 않는다 — 마지막 차단 절 앞에 밴드 3 을 끼워 넣을 뿐이다.
    """
    if MARKER in code:
        raise ValueError("이미 밴드 3 이 붙은 코드다 — 원본 챔피언 코드를 넣어라")
    count = code.count(TAIL_ANCHOR)
    if count != 1:
        raise ValueError(
            f"차단 절이 {count}회 발견됐다(정확히 1회여야 한다): {TAIL_ANCHOR!r}")
    block = (render_swap_block(start=start, end=end) if cell == "swap"
             else render_band3_block(float(cell), start=start, end=end))
    return code.replace(TAIL_ANCHOR, block + TAIL_ANCHOR)


def cell_name(cell: str) -> str:
    """격자 셀 → 전략 이름 조각. `0.5` → `K05`, `swap` → `SWAP`."""
    if cell == "swap":
        return "SWAP"
    value = float(cell)
    if value < 0:
        raise ValueError("k 는 0 이상이어야 한다")
    return f"K{value:g}".replace(".", "p")
