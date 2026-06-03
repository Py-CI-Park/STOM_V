"""생성 품질 (A) — 필터 범주 게이트 검출 (순수 함수).

배경(§3.22 over-firing): AI refine가 빈도를 올릴 때 LLM이 진입 필터를 느슨하게/
적게 만들어 과발화한다(예: `매수 = True` 또는 단일/항상참 조건 → 750+ 거래·
OOM·타임아웃). 반면 인간 시드(Tick_B_902_905_Update_2)는 ~20개 필터 범주를
AND로 결합하고 09:00~09:05 시초 시간창에 한정해 307 거래로 적정 게이트된다.

R7.4·§3.14·§3.15 ground-truth: "좋은 전략인가?"를 정적으로 판별하는 품질
판정기는 불가능(정적 코드로 흑/적을 가를 수 없음). 그러나 이 모듈은 품질
판정기가 **아니다** — 더 거친 "충분히 게이트됐는가?"라는 **구조적** 검사이며,
그건 정적으로 달성 가능하다. 서로 다른 필터 범주가 몇 개나 비교 조건으로
함께 쓰였는지 세는 것뿐이다(논리 평가·시뮬레이션 없음).

설계(liquidity_gate.py 스타일을 그대로 따른다):
  - 부작용 없는 순수 함수(단위테스트 가능). 코드 텍스트만 본다. 엔진 import 없음.
  - (a) 라인 단위로 `#` 주석을 제거하고(_strip_comments),
  - (b) 비교 연산자(`<`,`>`,`<=`,`>=` — _COMPARISON_RE)가 있는 줄에서만,
  - (c) 각 범주의 토큰이 등장하면 그 범주를 '존재'로 카운트한다.
  단순 대입/주석에만 등장하는 경우는 게이트로 보지 않는다(비교 문맥 필수).

substring 매칭에 대한 주의(false-positive 아님, 의도된 동작):
  - change_band 토큰 `등락율`은 `시가등락율`/`시가대비등락율`/`고저평균대비등락율`의
    부분문자열이지만 전부 같은 change_band 범주라 카운트가 부풀지 않는다.
  - 한 줄이 `당일거래대금각도(30) > 5`처럼 liquidity의 `당일거래대금`과
    volume_surge의 `당일거래대금각도`를 동시에 포함하면 그 줄이 두 범주를
    동시에 충족한다 — 한 줄이 여러 범주를 만족하는 것은 허용한다(단순·보수적).
  - 의도적 토큰 선택(범주 오염 회피): price_band에 시초가 `시가`를 넣지 않는다.
    `시가`는 `시가총액`(market_cap)·`시가등락율`/`시가대비등락율`(change_band)의
    부분문자열이라 `시가총액 < 3000` 한 줄이 price_band로도 잘못 카운트된다.
    price_band는 `현재가`/`고가`/`저가`로 충분히(시드 실측 포함) 검출되므로
    `시가`는 제외해 범주 간 오염을 막는다.

한계(중요): 이 검사는 범주 *폭*만 보고 조건의 *선별성*은 못 본다. 다중 토큰 항상참
조합(예: 현재가>0 and 등락율>0 and 시가총액<9e9 and 당일거래대금>0)은
min_filter_categories를 채워도 과발화할 수 있다(구조 검사의 본질적 한계 — R7.4: 정적
품질판정 불가). 프롬프트 가드레일(prompt.build_messages의 require_filter_gates 블록)이
"항상참 금지·이벤트 성립 순간 진입"을 가르쳐 보완한다. 둘은 짝으로 쓴다.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Set, Tuple

# liquidity_gate의 검출 보조함수를 재사용(동일 의미 — 주석 제거 + 부등호 검출).
from ai_strategy_loop.brain.liquidity_gate import _COMPARISON_RE, _strip_comments

# 범주 → 그 범주를 가리키는 토큰들. 시드 게이팅 구조(시총·가격/등락율 밴드·
#   거래대금 바닥/각도·체결강도·호가압력·시초 시간창·회전율 계열)를 반영한다.
#   한 줄에 어떤 범주의 토큰이라도 (비교와 함께) 나타나면 그 범주가 '존재'한다.
_FILTER_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "liquidity":     ("당일거래대금",),
    "market_cap":    ("시가총액",),
    "price_band":    ("현재가", "고가", "저가"),  # `시가`는 시가총액/시가등락율과 충돌 → 제외
    "change_band":   ("등락율", "시가등락율", "시가대비등락율", "고저평균대비등락율"),
    "exec_strength": ("체결강도",),
    "orderbook":     ("매도총잔량", "매수총잔량", "초당매수수량", "초당매도수량", "매도잔량", "매수잔량"),
    "volume_surge":  ("초당거래대금", "초당거래대금평균", "당일거래대금각도", "거래대금각도"),
    "time_window":   ("시분초",),
    "turnover":      ("회전율", "전일비", "전일동시간비"),
}


def categories_present(code: str) -> Set[str]:
    """주석 제거 후, (범주 토큰 + 비교 연산자)가 함께 나타나는 범주 집합을 돌려준다.

    각 줄은 부등호 비교(`<`/`>`/`<=`/`>=`)를 포함할 때만 검사한다(단순 대입·주석
    제외). 한 줄이 여러 범주 토큰을 포함하면 그 범주들을 모두 카운트한다.

    Args:
        code: 전략 코드 문자열.

    Returns:
        비교 조건과 함께 등장한 필터 범주 이름들의 집합.
    """
    if not code:
        return set()
    stripped = _strip_comments(code)
    found: Set[str] = set()
    for line in stripped.splitlines():
        if not _COMPARISON_RE.search(line):
            continue
        for cat, tokens in _FILTER_CATEGORIES.items():
            if cat in found:
                continue
            if any(tok in line for tok in tokens):
                found.add(cat)
    return found


def count_filter_categories(code: str) -> int:
    """비교 조건과 함께 등장한 서로 다른 필터 범주의 개수를 돌려준다.

    과발화 방지용 구조적 게이트의 척도다(클수록 진입이 더 충분히 게이트됨).
    품질(흑/적) 판정이 아니라 "충분히 게이트됐는가?"의 거친 구조 검사다.

    Args:
        code: 전략 코드 문자열.

    Returns:
        서로 다른 필터 범주의 개수(0 이상).
    """
    return len(categories_present(code))


# ===================================================================
# T3 (넓은 생성 강화): 시간창을 '토큰 존재'가 아니라 '값 범위(시분초 lo/hi)'로 측정
# ===================================================================
#
# 배경(사용자 T3): 지금까지 time_window 범주는 `시분초` 토큰이 비교와 함께
#   등장하는지(존재 유무)만 봤다. 그러나 '넓은 창에 분산 생성하는가?'는 토큰
#   존재가 아니라 **값 범위**로 측정해야 한다. 시드 Tick_902는 09:02~09:05(3분)
#   좁은 창이고, 분류축 유도가 노리는 건 09:00~09:30 전체에 분산된 생성이다.
#   _temp_band_structure.extract_bands(등락률 -30~30 no-op 통찰)와 동형으로,
#   `시분초`의 lo/hi(HHMMSS)를 추출해 span(초)·전범위(no-op=사실상 시간게이트
#   없음)를 정적으로 측정·가시화한다(추가 백테 0·코드 텍스트 파싱만).
#
# **과도강제 금지(중요)**: 좁은 창(902)은 다년강건 골드다. 이 모듈은 측정기이지
#   '넓은 창 강제기'가 아니다. is_noop_time_window는 '전범위=게이트 없음'만
#   탐지하며, 좁은 창은 절대 no-op으로 보지 않는다(좁은-good을 reject하면 안 됨).
#
# 설계(extract_bands 스타일을 그대로 따른다 — 순수·graceful):
#   - `#` 주석 제거 후(_strip_comments),
#   - 체인비교 `lo <= 시분초 < hi`(양끝 숫자) 및 단일비교(`시분초 < B`/`시분초 > A`/
#     `A < 시분초`/`B > 시분초`)를 합성한다.
#   - lo는 하한들의 max, hi는 상한들의 min(가장 좁은 교집합). 토큰 경계 가드로
#     `시분초` 뒤에 한글/영숫자/언더스코어가 오면 매칭하지 않는다(부분일치 방지).

# `시분초` 시간창 값 패턴 — HHMMSS 정수(예: 90200=09:02:00, 153000=15:30:00).
#   소수/부호도 허용하되(견고성) 실전은 정수 HHMMSS다.
_TIME_TOKEN = "시분초"
_TIME_NUM = r"-?\d+(?:\.\d+)?"
# 토큰 경계: `시분초` 바로 뒤에 한글/영숫자/_가 오면 다른 식별자의 일부 → 매칭 제외.
_TIME_BOUNDARY = r"(?![가-힣A-Za-z0-9_])"
# 체인: A <(=) 시분초 <(=) B
_TIME_CHAIN_RE = re.compile(
    rf"({_TIME_NUM})\s*<=?\s*{_TIME_TOKEN}{_TIME_BOUNDARY}\s*<=?\s*({_TIME_NUM})"
)
# 단일(시분초 좌변): 시분초 <(=) B  /  시분초 >(=) A
_TIME_LEFT_RE = re.compile(
    rf"{_TIME_TOKEN}{_TIME_BOUNDARY}\s*(<=?|>=?)\s*({_TIME_NUM})"
)
# 단일(시분초 우변): A <(=) 시분초  /  B >(=) 시분초
_TIME_RIGHT_RE = re.compile(
    rf"({_TIME_NUM})\s*(<=?|>=?)\s*{_TIME_TOKEN}{_TIME_BOUNDARY}"
)


def _hhmmss_to_sec(hhmmss: int) -> int:
    """HHMMSS 정수(예: 90200=09:02:00)를 자정 기준 초로 환산한다.

    분/초 필드가 60+ 같은 비정상 값이어도 산술적으로 환산만 한다(검증 안 함 —
    전략 코드의 시간 비교는 엔진이 그대로 정수 비교하므로, 여기선 측정만 한다).
    """
    h = hhmmss // 10000
    m = (hhmmss // 100) % 100
    s = hhmmss % 100
    return h * 3600 + m * 60 + s


def time_window_bounds(code: str) -> Optional[Tuple[Optional[int], Optional[int]]]:
    """`시분초` 시간 게이트의 (lo, hi) HHMMSS 경계를 추출한다(없으면 None).

    체인비교 `lo <= 시분초 < hi`와 단일비교(`시분초 < hi`·`시분초 > lo`·`lo < 시분초`·
    `hi > 시분초`)를 모두 합성한다. tick 전략은 902/905처럼 여러 시간 분기(OR)로
    구성되므로 전체 '거래 창'을 모든 시간 게이트의 **합집합(envelope)**으로 잡는다
    (lo=하한들의 min=가장 이른 진입, hi=상한들의 max=가장 늦은 진입). 한쪽만 있으면
    그쪽만 채운다. (단일 AND 경로의 중복 경계는 envelope가 약간 넓게 볼 수 있으나,
    실측 다분기 생성물에서 교집합이 분기경계서 반전[09:15~09:05 붕괴]하는 것을
    피하는 게 측정 목적상 우선이다.)

    하한만/상한만 있는 반열림 게이트(예: `시분초 < 93000`만 있고 하한 없음)는
    빠진 쪽을 세션 경계로 보지 않고 그대로 None을 채워, 호출부(span/no-op)가
    세션 기본값으로 보정하게 한다(여기선 코드에 적힌 사실만 돌려준다).

    Args:
        code: 전략 코드 문자열.

    Returns:
        (lo_hhmmss, hi_hhmmss) — 각 항목은 int 또는 None. 어떤 시간 게이트도
        없으면 None(튜플이 아니라 None 자체).
    """
    if not code:
        return None
    stripped = _strip_comments(code)
    los: list[int] = []
    his: list[int] = []

    # 체인: A <(=) 시분초 <(=) B → A=하한, B=상한.
    for m in _TIME_CHAIN_RE.finditer(stripped):
        los.append(int(float(m.group(1))))
        his.append(int(float(m.group(2))))
    # 단일(좌변): 시분초 < B(상한) / 시분초 > A(하한).
    for m in _TIME_LEFT_RE.finditer(stripped):
        op, val = m.group(1), int(float(m.group(2)))
        if op.startswith("<"):
            his.append(val)
        else:
            los.append(val)
    # 단일(우변): A < 시분초(하한) / B > 시분초(상한).
    for m in _TIME_RIGHT_RE.finditer(stripped):
        val, op = int(float(m.group(1))), m.group(2)
        if op.startswith("<"):
            los.append(val)   # A < 시분초 → A는 하한
        else:
            his.append(val)   # B > 시분초 → B는 상한

    if not los and not his:
        return None
    # 전체 '거래 창'은 모든 시간 게이트의 합집합이다(교집합 아님). tick 전략은
    #   902/905처럼 여러 시간 분기(OR)로 구성되므로, 교집합(max los·min his)을 쓰면
    #   분기 경계가 서로 반전돼 빈/역전 창이 나온다(예 09:15~09:05). 따라서 가장
    #   이른 하한 ~ 가장 늦은 상한으로 잡아 '이 전략이 거래하는 시간 범위'를 측정한다.
    #   (902_905 → 09:00~09:05, 다분기 생성물 → 09:00~09:20 등으로 올바르게 측정.)
    lo = min(los) if los else None  # 거래 창 시작(가장 이른 하한 = 합집합)
    hi = max(his) if his else None  # 거래 창 끝(가장 늦은 상한 = 합집합)
    return (lo, hi)


def time_window_span_sec(
    code: str, *, session_lo: int = 90000, session_hi: int = 153000
) -> Optional[int]:
    """`시분초` 시간창의 폭(hi-lo)을 **초**로 돌려준다(없으면 None).

    time_window_bounds로 (lo,hi) HHMMSS를 얻고 각각 초로 환산해 hi-lo를 잰다.
    반열림 게이트는 빠진 쪽을 세션 경계(session_lo/session_hi)로 보정해 폭을
    잰다(예: `시분초 < 93000`만 있으면 [09:00, 09:30) 폭). 음수 폭(역전 경계)은
    0으로 클램프한다(graceful — 비정상 입력이 음수 span을 만들지 않게).

    Args:
        code: 전략 코드 문자열.
        session_lo: 하한 미지정 시 보정할 세션 시작(HHMMSS; 기본 09:00:00).
        session_hi: 상한 미지정 시 보정할 세션 종료(HHMMSS; 기본 15:30:00).

    Returns:
        시간창 폭(초, 0 이상) 또는 시간 게이트가 없으면 None.
    """
    bounds = time_window_bounds(code)
    if bounds is None:
        return None
    lo, hi = bounds
    lo_sec = _hhmmss_to_sec(lo if lo is not None else session_lo)
    hi_sec = _hhmmss_to_sec(hi if hi is not None else session_hi)
    span = hi_sec - lo_sec
    return span if span > 0 else 0


def is_noop_time_window(
    code: str, *, session_lo: int = 90000, session_hi: int = 153000
) -> bool:
    """시간창이 세션 전범위를 덮어 '사실상 게이트 없음(no-op)'인지 판정한다.

    등락률 -30~30 no-op 통찰과 동형: 시간 게이트가 있더라도 그 경계가 세션
    전체([session_lo, session_hi])를 덮으면 아무 시각도 거르지 못하므로 시간
    게이트를 안 쓴 것과 같다(no-op=True).

    판정: (lo가 없거나 lo<=session_lo) AND (hi가 없거나 hi>=session_hi) → True.
    한쪽만 지정한 반열림 게이트는 지정 안 한 쪽이 세션 경계와 같으므로, 지정한
    쪽이 세션을 못 좁히면 no-op이다(예: `시분초 < 153000`만 = no-op).

    **좁은 창은 절대 no-op이 아니다**: 시드 902(`90200<=시분초<90500`)는 lo>
    session_lo 또는 hi<session_hi라 False다(측정만 — reject 강제는 호출부 토글).

    시간 게이트가 아예 없으면(bounds=None) no-op으로 본다(시간 분산 측정 관점에서
    '전범위=시간 무게이트'와 동치). 호출부가 require_meaningful_time_window 토글
    ON일 때만 이 결과로 reject하며, 기본 OFF면 측정·가시화 전용이다.

    Args:
        code: 전략 코드 문자열.
        session_lo: 세션 시작(HHMMSS; 기본 09:00:00).
        session_hi: 세션 종료(HHMMSS; 기본 15:30:00).

    Returns:
        시간창이 세션 전범위를 덮으면(=사실상 시간 게이트 없음) True.
    """
    bounds = time_window_bounds(code)
    if bounds is None:
        return True  # 시간 게이트 자체가 없음 = 전범위 = no-op.
    lo, hi = bounds
    lo_covers = lo is None or lo <= session_lo
    hi_covers = hi is None or hi >= session_hi
    return lo_covers and hi_covers
