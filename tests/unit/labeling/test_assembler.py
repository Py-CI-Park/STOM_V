"""M-3 조립기 — 임계 분위 스냅 + 902/905 문법 렌더링 계약.

규율: 임계는 분위 격자 경계 위에서만(임의 미세조정 금지). 렌더 결과는
파이썬 문법으로 파싱 가능해야 하고(엔진이 exec 하는 DSL), 신규 전략은
가드(VI·라운드피겨)를 기본 탑재한다.
"""

from __future__ import annotations

import ast

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.assembler import render_buy_expression, snap_threshold


def _frame(n: int = 10_000, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"체결강도": rng.uniform(0, 300, n), "일자": 20240304})


def test_snap_threshold_lands_on_quantile_edge_only() -> None:
    frame = _frame()
    snapped = snap_threshold(frame, "체결강도", raw=151.7)
    edges = np.quantile(frame["체결강도"], np.linspace(0, 1, 11))
    assert any(abs(snapped - e) < 1e-9 for e in edges), "분위 경계가 아닌 임계"
    # 원값에서 가장 가까운 경계로 스냅.
    assert abs(snapped - 151.7) == min(abs(e - 151.7) for e in edges)


def test_render_buy_expression_is_parseable_and_follows_grammar() -> None:
    clauses = [
        {"변수": "체결강도", "연산자": ">", "임계": 150.0},
        {"변수": "등락율", "연산자": "<=", "임계": 8.0},
    ]
    code = render_buy_expression(
        name="QSP9_M3_tick_TEST", time_start=90000, time_end=90500, clauses=clauses)
    ast.parse(code)  # 엔진이 exec 하는 DSL — 파이썬 문법이어야 한다
    # 문법 계층: 시간창 게이트 + 가드 + 절 + 매수 호출.
    assert "시분초" in code and "90500" in code
    assert "VI아래5호가" in code and "라운드피겨위5호가이내" in code
    assert "체결강도 > 150.0" in code and "등락율 <= 8.0" in code
    assert code.strip().endswith("self.Buy()")
    # 누출 변수 금지 — R_*, S_* 는 어떤 경로로도 들어가면 안 된다.
    assert "R_" not in code and "S_" not in code


def test_render_rejects_leaky_or_unknown_operator() -> None:
    with pytest.raises(ValueError):
        render_buy_expression(name="X", time_start=90000, time_end=90500,
                              clauses=[{"변수": "R_MFE", "연산자": ">", "임계": 1.0}])
    with pytest.raises(ValueError):
        render_buy_expression(name="X", time_start=90000, time_end=90500,
                              clauses=[{"변수": "체결강도", "연산자": "!=", "임계": 1.0}])
