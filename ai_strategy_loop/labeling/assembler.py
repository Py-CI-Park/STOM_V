"""M-3 조립기 — 지도의 흑자 영역을 902/905 문법의 매수식으로 번역한다.

- 임계는 **분위 격자 경계로 스냅**(임의 미세조정 금지 규율).
- 렌더는 902/905 실코드의 6층 문법(시간창→가드→절→호출)을 따른다.
- 누출 차단은 프롬프트가 아니라 여기(정적 검사)에서 한다 — AI 프롬프트 6원칙 #6.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

# 스냅 격자는 100분위 — 10분위는 꼬리 임계를 파괴한다(실측: 트리 임계 736.5 가
#   10분위 스냅으로 1.0 이 되어 C1 후보가 엔진에서 0건이 됐다, 2026-08-05).
_BUCKETS = 100
_ALLOWED_OPERATORS = {">", ">=", "<", "<="}
_LEAKY_PREFIXES = ("R_", "S_")
_LEAKY_NAMES = {"매도시간", "보유시간", "수익률", "최고수익률", "매도조건"}

#: 라벨 parquet 파생 이름 → 엔진 DSL 표현 (라벨 연구 전용 이름은 엔진에 없다).
#: v3 파생은 QSP11 에서 **엔진 정의를 역산해 확정**한 것이라 수식이 정확히 대응한다.
#: 분모 0 은 엔진에서 예외가 되므로 조건식에 가드를 넣는다(지도는 NaN 으로 처리했다).
_DERIVED_TO_DSL = {
    "시가등락율": "((시가 - (현재가 / (1 + (등락율 / 100)))) / (현재가 / (1 + (등락율 / 100)))) * 100",
    "시가대비등락율": "((현재가 - 시가) / 시가) * 100",
    "초당순매수금액": "(초당매수수량 - 초당매도수량) * 현재가 / 1_000_000",
    "spread_pct": "(매도호가1 - 매수호가1) / 현재가 * 100",
    "일중위치": "((현재가 - 저가) / (고가 - 저가)) if 고가 > 저가 else 0.5",
    "초당거래대금배율_30": "(초당거래대금 / 초당거래대금평균(30)) if 초당거래대금평균(30) > 0 else 0",
    "초당거래대금배율_60": "(초당거래대금 / 초당거래대금평균(60)) if 초당거래대금평균(60) > 0 else 0",
    "체결강도평균_30": "체결강도평균(30)",
    "체결강도평균_60": "체결강도평균(60)",
    "등락율각도_30": "등락율각도(30)",
    "등락율각도_60": "등락율각도(60)",
    "누적매수매도비_30": "(누적초당매수수량(30) / 누적초당매도수량(30)) if 누적초당매도수량(30) > 0 else 0",
    "누적매수매도비_60": "(누적초당매수수량(60) / 누적초당매도수량(60)) if 누적초당매도수량(60) > 0 else 0",
    "초당거래대금직전비": "(초당거래대금 / 초당거래대금N(1)) if 초당거래대금N(1) > 0 else 0",
    "매수흐름_매도잔량비": "(초당매수수량 / 매도총잔량) if 매도총잔량 > 0 else 0",
    "잔량비": "(매도총잔량 / 매수총잔량) if 매수총잔량 > 0 else 0",
}


def snap_threshold(frame: pd.DataFrame, variable: str, *, raw: float,
                   buckets: int = _BUCKETS) -> float:
    """원시 임계(트리 제안 등)를 가장 가까운 분위 경계로 스냅한다."""
    edges = np.quantile(frame[variable].dropna(), np.linspace(0, 1, buckets + 1))
    return float(edges[np.argmin(np.abs(edges - raw))])


def _validate(clauses: list[dict]) -> None:
    for clause in clauses:
        name = str(clause["변수"])
        if name.startswith(_LEAKY_PREFIXES) or name in _LEAKY_NAMES:
            raise ValueError(f"누출 변수 금지: {name}")
        if clause["연산자"] not in _ALLOWED_OPERATORS:
            raise ValueError(f"허용되지 않은 연산자: {clause['연산자']}")


def _clause_expression(clause: dict) -> str:
    """절 하나 → DSL 조건식 조각. 파생 이름은 엔진 수식으로 전개한다."""
    variable = str(clause["변수"])
    expression = _DERIVED_TO_DSL.get(variable, variable)
    target = expression if expression == variable else f"({expression})"
    return f"{target} {clause['연산자']} {clause['임계']}"


def render_hierarchical_buy(*, name: str, branches: list[dict],
                            price_floor: int = 1000, price_cap: int = 50000) -> str:
    """계층 구조 매수식 — 분기(시간창×시총)마다 다른 절 집합을 OR 로 잇는다.

    QSP12 의 산출물을 엔진 DSL 로 옮긴다. 902/905 와 같은 모양이며,
    지도에서 평가한 것과 **같은 분기·같은 절**이어야 전이율 비교가 성립한다.
    """
    if not branches:
        raise ValueError("분기가 비었다")
    lines = [
        f"# {name} — QSP12 계층 구조 자동 조립 (분기 {len(branches)}개)",
        "시가대비등락율 = ((현재가 - 시가) / 시가) * 100",
        "VI아래5호가 = VI가격 - VI호가단위 * 5",
        "매수 = False",
        "",
        f"if ({price_floor} < 현재가 <= {price_cap}) and (현재가 < VI아래5호가) "
        "and not 라운드피겨위5호가이내:",
    ]
    for index, branch in enumerate(branches):
        spec = branch["spec"]
        start, end = spec["time"]
        parts = [f"{start} <= 시분초 < {end}"]
        if "cap_max" in spec:
            parts.append(f"시가총액 < {spec['cap_max']:g}")
        if "cap_min" in spec:
            parts.append(f"시가총액 >= {spec['cap_min']:g}")
        for clause in branch["clauses"]:
            _validate([clause])
            parts.append(_clause_expression(clause))
        keyword = "if" if index == 0 else "elif"
        lines.append(f"    {keyword} (" + ") and (".join(parts) + "):")
        lines.append("        매수 = True")
    lines += ["", "if 매수:", "    self.Buy()"]
    return "\n".join(lines)


def render_sell_expression(*, name: str, tp_pct: float, sl_pct: float, horizon: int,
                           forced_exit: int = 92800) -> str:
    """배리어 청산 규칙(익절/손절/시간) → STOM 매도 DSL.

    지도에서 평가한 규칙을 **그대로** 엔진에 옮긴다 — 지도와 엔진이 다른 규칙을 쓰면
    전이율 비교가 무의미해진다(QSP10 P5 전이율 기록의 전제).
    """
    if tp_pct <= 0 or sl_pct <= 0:
        raise ValueError("익절·손절은 양수여야 한다")
    return "\n".join([
        f"# {name} — QSP10 배리어 청산 (익절 +{tp_pct}% / 손절 -{sl_pct}% / 시간 {horizon}초)",
        "매도 = False",
        f"if 수익률 >= {tp_pct}:",
        "    매도 = True",
        f"elif 수익률 <= -{sl_pct}:",
        "    매도 = True",
        f"elif 보유시간 >= {horizon}:",
        "    매도 = True",
        f"elif 시분초 >= {forced_exit}:",
        "    매도 = True",
        "",
        "if 매도:",
        "    self.Sell()",
    ])


def render_trailing_sell_expression(*, name: str, arm_pct: float, give_pct: float,
                                    horizon: int, forced_exit: int = 92800) -> str:
    """트레일링 청산 규칙 → STOM 매도 DSL. 지도 `trailing.py` 커널과 같은 규칙이다.

    규칙(양쪽 동일):
      무장 — 최고수익률이 arm 이상이 된 뒤에만 트레일링이 켜진다.
      청산 — 무장 후 최고 대비 give(%p) 이상 되돌린 **첫** 순간.
      만기 — 지평(tick=초 / min=분) 도달 또는 전체청산 시각.

    **지도와 엔진의 남는 차이 2가지**(숨기지 않고 전이율로 흡수한다):
      1. 지도는 매수=매도호가1 / 청산=매수호가1 로 스프레드를 명시적으로 낸다.
         엔진 `수익률` 은 **현재가** 기준이라 보유 중 값이 약간 높게 읽힌다
         → 엔진 쪽이 조금 더 일찍 무장한다.
      2. 엔진 `최고수익률` 은 0 에서 시작한다(음수 최고가 없다). arm 이 양수인
         한 무장 조건은 같지만, 되돌림 폭 계산의 기준점이 물속에서는 다르다.
    비용 모델은 같다 — 매수 0.015% / 매도 0.195%(세금 0.18% 포함).
    """
    if arm_pct <= 0:
        raise ValueError("무장 임계는 양수여야 한다 — 0 이하면 손절로 동작한다")
    if give_pct <= 0:
        raise ValueError("되돌림 폭은 양수여야 한다")
    return "\n".join([
        f"# {name} — 트레일링 청산 (무장 +{arm_pct:g}% / 되돌림 {give_pct:g}%p / 지평 {horizon})",
        "매도 = False",
        "",
        f"if 최고수익률 >= {arm_pct:g} and (최고수익률 - 수익률) >= {give_pct:g}:",
        "    매도 = True",
        f"elif 보유시간 >= {horizon}:",
        "    매도 = True",
        f"elif 시분초 >= {forced_exit}:",
        "    매도 = True",
        "",
        "if 매도:",
        "    self.Sell()",
    ])


#: 자본 회전 교정용 조기 청산 규칙 — **허용 목록**이다.
#:
#: 왜 목록으로 묶는가: 이 렌더 결과는 `strategy.db` 에 등록되어 엔진이 실행한다.
#: 조건식을 문자열로 자유롭게 받으면 임의 코드를 등록하는 통로가 된다. 규칙을
#: 늘리려면 이 표를 고치고 테스트를 추가한다 — 호출부에서 문자열을 넘기지 않는다.
EARLY_EXIT_RULES: Final = {
    # 물속에서 오래 버티지 않는다 — 자본을 묶는 주범이 이 구간이다.
    "time_stop": ("시간손절", "보유시간 > 180 and 수익률 < 0"),
    # 챔피언 ③절을 빌려온다: 최근 60초 최저가를 깨면 추세가 끝난 것으로 본다.
    "trend_break": ("추세이탈", "보유시간 > 60 and 현재가 < 최저현재가(int(60), int(보유시간))"),
    # 단순 하한. 비교군으로 둔다 — 복잡한 규칙이 단순한 것보다 나은지 재려면 필요하다.
    "hard_stop": ("손절", "수익률 <= -3.0"),
    # 합성 — S4 실측이 만든 가설이다. 단독으로는 둘 다 반쪽이었다:
    #   추세이탈: 짝지은 CI [+0.041, +0.536] 로 건당 우위 **확정**, 그러나 동시보유 2
    #   시간손절: 동시보유 1 · 총수익률 296% 로 **자본 통과**, 그러나 건당 미확정
    # 가설: 추세이탈이 우위를 만들고 시간손절이 회전을 만든다 — 둘 다 있으면 둘 다 남는다.
    "trend_then_time": (
        "추세이탈+시간손절",
        "(보유시간 > 60 and 현재가 < 최저현재가(int(60), int(보유시간)))"
        " or (보유시간 > 180 and 수익률 < 0)"),
    # --- W7 교환 곡선 (2026-08-09 사전 등록) ---------------------------------
    #
    # 합성 실험이 밝힌 것: 시간손절 180초가 자본을 고치지만 건당 우위를
    # +0.3582 → +0.1479%p 로 깎는다. 추세이탈을 함께 넣어도 회복되지 않았다.
    # 즉 그 규칙이 자르는 거래에 **되살아났을 거래**가 섞여 있다.
    #
    # 그러면 **덜 자르는** 지점에 둘 다 만족하는 곳이 있는가? 문턱을 올려 본다.
    # 상한 감각: 챔피언은 평균 보유 464초인데도 동시보유가 1이다 —
    # 240·300초는 그 안쪽이므로 자본이 유지될 여지가 있다.
    #
    # 격자는 여기까지가 전부다. 결과를 보고 넣지 않는다(헌법 5항).
    "time_stop_240": ("시간손절240", "보유시간 > 240 and 수익률 < 0"),
    "time_stop_300": ("시간손절300", "보유시간 > 300 and 수익률 < 0"),
}


def render_capital_turnover_sell_expression(*, name: str, arm_pct: float, give_pct: float,
                                            horizon: int, rule_key: str,
                                            forced_exit: int = 92800) -> str:
    """트레일링 + **조기 청산 한 줄** → STOM 매도 DSL.

    ## 왜 필요한가

    트레일링 후보는 건당 수익률에서 챔피언을 이겼지만 **자본 대비로는 졌다**.
    원인은 하나다: 평균 보유가 373초 → 540초로 늘어 최대 동시보유가 1 → 2가 되고,
    필요자금이 2배가 됐다. 총수익률 = 총수익금 / 필요자금 이므로 분모가 2배면
    수익이 1.8배여도 진다.

    그래서 **보유를 끊는 규칙 하나만** 얹는다. 한 번에 하나씩만 얹는 이유는
    헌법 7항(진입과 매도를 동시에 바꾸지 않는다)의 같은 정신이다 — 두 개를 같이
    얹으면 어느 쪽이 효과인지 못 가린다.

    ## 분기 순서

    트레일링 → 조기 청산 → 지평 → 전체청산.

    조기 청산을 트레일링 **뒤**에 두는 이유: 둘 다 참이면 같은 틱에 팔리므로
    손익은 같고 `매도조건` 기록만 달라진다. 트레일링을 앞에 두면 "B3 와 다른 틱에
    팔린 거래 = 새 규칙 때문"이 되어 원인 추적이 깔끔하다.
    """
    if rule_key not in EARLY_EXIT_RULES:
        raise ValueError(f"허용되지 않은 조기 청산 규칙: {rule_key} "
                         f"(가능: {sorted(EARLY_EXIT_RULES)})")
    if arm_pct <= 0:
        raise ValueError("무장 임계는 양수여야 한다 — 0 이하면 손절로 동작한다")
    if give_pct <= 0:
        raise ValueError("되돌림 폭은 양수여야 한다")

    label, condition = EARLY_EXIT_RULES[rule_key]
    return "\n".join([
        f"# {name} — 트레일링(무장 +{arm_pct:g}% / 되돌림 {give_pct:g}%p) + {label}",
        f"#   목적: 보유를 끊어 자본 회전을 올린다(최대동시보유 2 → 1).",
        "매도 = False",
        "",
        f"if 최고수익률 >= {arm_pct:g} and (최고수익률 - 수익률) >= {give_pct:g}:",
        "    매도 = True",
        f"elif {condition}:",                     # ← 이 한 줄만 B3 와 다르다
        "    매도 = True",
        f"elif 보유시간 >= {horizon}:",
        "    매도 = True",
        f"elif 시분초 >= {forced_exit}:",
        "    매도 = True",
        "",
        "if 매도:",
        "    self.Sell()",
    ])


def render_buy_expression(*, name: str, time_start: int, time_end: int,
                          clauses: list[dict], price_floor: int = 1000,
                          price_cap: int = 50000) -> str:
    """절 목록 → STOM 매수 DSL (902/905 문법). 파이썬 파싱 가능성이 계약이다."""
    _validate(clauses)
    lines = [
        f"# {name} — QSP9 M-3 지도 기반 자동 조립 (임계는 분위 격자 스냅)",
        "시가대비등락율 = ((현재가 - 시가) / 시가) * 100",
        "VI아래5호가 = VI가격 - VI호가단위 * 5",
        "매수 = True",
        "",
        # 관심종목 게이트는 넣지 않는다 — 라벨 우주(수집 전 종목)와 어긋나면
        #   엔진 실측이 지도 예측과 비교 불가능해진다.
        f"if not ({time_start} <= 시분초 < {time_end}):",
        "    매수 = False",
        f"elif not ({price_floor} < 현재가 <= {price_cap}):",
        "    매수 = False",
        "elif not (현재가 < VI아래5호가):",
        "    매수 = False",
        "elif 라운드피겨위5호가이내:",
        "    매수 = False",
    ]
    for clause in clauses:
        expr = _DERIVED_TO_DSL.get(str(clause["변수"]), str(clause["변수"]))
        target = expr if expr == clause["변수"] else f"({expr})"
        lines.append(f"elif not ({target} {clause['연산자']} {clause['임계']}):")
        lines.append("    매수 = False")
    lines += ["", "if 매수:", "    self.Buy()"]
    return "\n".join(lines)
