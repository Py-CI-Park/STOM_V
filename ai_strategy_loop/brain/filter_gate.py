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

from typing import Dict, Set, Tuple

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
