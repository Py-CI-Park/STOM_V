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

from ai_strategy_loop.labeling.assembler import (
    render_hierarchical_buy,
    render_buy_expression, render_sell_expression, snap_threshold,
)


def _frame(n: int = 10_000, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"체결강도": rng.uniform(0, 300, n), "일자": 20240304})


def test_snap_threshold_lands_on_quantile_edge_only() -> None:
    frame = _frame()
    snapped = snap_threshold(frame, "체결강도", raw=151.7)
    # 격자는 100분위 — 10분위는 꼬리 임계를 파괴한다(C1 0건 실측 결함).
    edges = np.quantile(frame["체결강도"], np.linspace(0, 1, 101))
    assert any(abs(snapped - e) < 1e-9 for e in edges), "분위 경계가 아닌 임계"
    # 원값에서 가장 가까운 경계로 스냅.
    assert abs(snapped - 151.7) == min(abs(e - 151.7) for e in edges)
    # 100분위 해상도면 원값에서 1% 스텝 이상 벗어나지 않는다.
    assert abs(snapped - 151.7) < 10.0


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


def test_render_sell_expression_mirrors_the_map_rule() -> None:
    code = render_sell_expression(name="QSP10_S", tp_pct=2.0, sl_pct=1.0, horizon=300)
    ast.parse(code)
    # 지도에서 쓴 규칙 3종(익절·손절·시간)이 그대로 들어가야 전이율 비교가 성립한다.
    assert "수익률 >= 2.0" in code
    assert "수익률 <= -1.0" in code
    assert "보유시간 >= 300" in code
    assert "시분초 >= 92800" in code
    assert code.strip().endswith("self.Sell()")


def test_render_sell_rejects_nonpositive_barriers() -> None:
    with pytest.raises(ValueError):
        render_sell_expression(name="X", tp_pct=0.0, sl_pct=1.0, horizon=300)


def test_render_hierarchical_buy_branches_and_derived_expansion() -> None:
    branches = [
        {"name": "a", "spec": {"time": [90000, 90200], "cap_max": 3000.0},
         "clauses": [{"변수": "초당거래대금배율_30", "연산자": ">", "임계": 3.0}]},
        {"name": "b", "spec": {"time": [90200, 90500], "cap_min": 3000.0},
         "clauses": [{"변수": "체결강도", "연산자": ">", "임계": 150.0}]},
    ]
    code = render_hierarchical_buy(name="QSP12_T", branches=branches)
    ast.parse(code)

    # 분기별 시간창·시총 게이트가 각각 들어간다.
    assert "90000 <= 시분초 < 90200" in code and "시가총액 < 3000" in code
    assert "90200 <= 시분초 < 90500" in code and "시가총액 >= 3000" in code
    # 파생 이름은 엔진 수식으로 전개되고 분모 0 가드가 붙는다.
    assert "초당거래대금평균(30)" in code and "if 초당거래대금평균(30) > 0 else 0" in code
    assert "초당거래대금배율_30" not in code          # 지도 전용 이름이 남으면 안 된다
    assert code.count("매수 = True") == 2
    assert code.strip().endswith("self.Buy()")


def test_render_hierarchical_buy_rejects_empty_and_leaky() -> None:
    with pytest.raises(ValueError):
        render_hierarchical_buy(name="X", branches=[])
    with pytest.raises(ValueError):
        render_hierarchical_buy(name="X", branches=[
            {"name": "a", "spec": {"time": [90000, 90200]},
             "clauses": [{"변수": "R_MFE", "연산자": ">", "임계": 1.0}]}])
