"""M-3 조립기 — 지도의 흑자 영역을 902/905 문법의 매수식으로 번역한다.

- 임계는 **분위 격자 경계로 스냅**(임의 미세조정 금지 규율).
- 렌더는 902/905 실코드의 6층 문법(시간창→가드→절→호출)을 따른다.
- 누출 차단은 프롬프트가 아니라 여기(정적 검사)에서 한다 — AI 프롬프트 6원칙 #6.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_BUCKETS = 10
_ALLOWED_OPERATORS = {">", ">=", "<", "<="}
_LEAKY_PREFIXES = ("R_", "S_")
_LEAKY_NAMES = {"매도시간", "보유시간", "수익률", "최고수익률", "매도조건"}

#: 라벨 parquet 파생 이름 → 엔진 DSL 표현 (라벨 연구 전용 이름은 엔진에 없다).
_DERIVED_TO_DSL = {
    "시가등락율": "((시가 - (현재가 / (1 + (등락율 / 100)))) / (현재가 / (1 + (등락율 / 100)))) * 100",
    "시가대비등락율": "((현재가 - 시가) / 시가) * 100",
    "초당순매수금액": "(초당매수수량 - 초당매도수량) * 현재가 / 1_000_000",
    "spread_pct": "(매도호가1 - 매수호가1) / 현재가 * 100",
    "일중위치": "((현재가 - 저가) / (고가 - 저가)) if 고가 > 저가 else 0.5",
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
