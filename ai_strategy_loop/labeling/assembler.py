"""M-3 조립기 — 지도의 흑자 영역을 902/905 문법의 매수식으로 번역한다.

- 임계는 **분위 격자 경계로 스냅**(임의 미세조정 금지 규율).
- 렌더는 902/905 실코드의 6층 문법(시간창→가드→절→호출)을 따른다.
- 누출 차단은 프롬프트가 아니라 여기(정적 검사)에서 한다 — AI 프롬프트 6원칙 #6.
"""

from __future__ import annotations

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
