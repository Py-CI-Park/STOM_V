# -*- coding: utf-8 -*-
"""S6 계약 테스트 — 매도축 응답면 고원/절벽 판정.

로드맵 §2.4 의 규율을 코드로 고정한다: 최적화는 "더 좋은 값 찾기"가 아니라
"지금 값이 고원 위인지 확인하기"다. 절벽 위의 최고점은 표본 밖에서 사라진다.

계약:
  1. 격자 모서리는 **고원으로 승격되지 않는다** — 한쪽을 못 봤을 뿐이다.
  2. 이웃 중 하나라도 0 이하면 절벽이다(성적이 얼마든).
  3. 권고는 "가장 높은 셀"이 아니라 **가장 높은 고원 셀**이다.
  4. 최고점이 절벽이면 그 격차(overfit_gap)를 반드시 보고한다.
  5. 트레일링이 아닌 셀은 축을 오염시키지 않고 조용히 빠진다.
"""
from __future__ import annotations

import pytest

from ai_strategy_loop.controller import response_surface as rs


def _cell(arm, give, value):
    return {"rule": f"trailing(arm+{arm:g}/give{give:g})", "expectancy_pct": value}


def _plane(values):
    """values[i][j] → arm 2..(2+i), give 1..(1+j) 격자."""
    return [_cell(2 + i, 1 + j, v)
            for i, row in enumerate(values) for j, v in enumerate(row)]


# ---------------------------------------------------------------------------
# 축 만들기
# ---------------------------------------------------------------------------

def test_non_trailing_cells_do_not_pollute_the_axes():
    cells = _plane([[1.0, 1.0], [1.0, 1.0]]) + [
        {"rule": "mfe_capture(60s)", "expectancy_pct": 9.9},
        {"rule": "time_stop(30s)", "expectancy_pct": -0.2},
    ]
    surface = rs.build_surface(cells)
    assert surface["cells"] == 4
    assert surface["arms"] == [2.0, 3.0] and surface["gives"] == [1.0, 2.0]


def test_parse_rejects_other_families():
    assert rs.parse_trailing("trailing(arm+3/give1.5)") == (3.0, 1.5)
    assert rs.parse_trailing("barrier(TP+1/SL-1, 60s)") is None


# ---------------------------------------------------------------------------
# 판정
# ---------------------------------------------------------------------------

def test_edge_cell_is_never_promoted_to_plateau():
    """★ 2x2 격자는 모든 칸의 이웃이 2개다 — 판정은 되지만 3면을 못 본다."""
    assert rs.classify(1.0, [0.9], retain=0.5) == "가장자리"      # 이웃 1개
    assert rs.classify(1.0, [], retain=0.5) == "가장자리"


def test_any_non_positive_neighbour_makes_it_a_cliff():
    """★ 성적이 아무리 좋아도 이웃이 0 이하면 절벽이다."""
    assert rs.classify(5.0, [4.9, 4.8, 0.0], retain=0.5) == "절벽"
    assert rs.classify(5.0, [4.9, 4.8, -0.1], retain=0.5) == "절벽"


def test_plateau_needs_neighbours_to_retain_the_score():
    assert rs.classify(1.0, [0.6, 0.7, 0.8], retain=0.5) == "고원"
    assert rs.classify(1.0, [0.2, 0.7, 0.8], retain=0.5) == "경사"


def test_negative_centre_is_not_a_candidate():
    assert rs.classify(-0.1, [1.0, 1.0, 1.0]) == "음수"


# ---------------------------------------------------------------------------
# 권고
# ---------------------------------------------------------------------------

def test_recommends_the_plateau_peak_not_the_global_peak():
    """★ 최고점이 절벽이면 고원 최고를 권하고 그 격차를 보고한다.

    가운데(2,2)가 9.0 으로 가장 높지만 이웃에 0.0 이 있어 절벽이다.
    (3,2)=2.0 은 이웃이 전부 양수이고 절반 이상을 유지하므로 고원이다.
    """
    report = rs.analyze(_plane([
        [1.0, 0.0, 1.0],
        [1.5, 9.0, 1.6],
        [1.4, 2.0, 1.5],
        [1.3, 1.4, 1.3],
    ]))
    assert report["best"]["expectancy_pct"] == 9.0
    assert report["best_is_plateau"] is False
    assert report["best_plateau"]["expectancy_pct"] == 2.0
    assert report["overfit_gap"] == pytest.approx(7.0)
    assert "고원 셀 중에서" in report["recommendation"]


def test_when_the_peak_is_flat_it_is_simply_adopted():
    report = rs.analyze(_plane([
        [1.0, 1.1, 1.0],
        [1.1, 1.4, 1.1],
        [1.0, 1.1, 1.0],
    ]))
    assert report["best_is_plateau"] is True
    assert report["overfit_gap"] is None
    # 지도는 채택을 권고하지 않는다 — 안전 영역만 말하고 승자는 엔진이 고른다.
    assert "엔진으로" in report["recommendation"]
    assert "채택 가능" not in report["recommendation"]


def test_all_negative_surface_recommends_nothing():
    report = rs.analyze(_plane([[-1.0, -1.0, -1.0]] * 3))
    assert report["best_plateau"] is None
    assert "안전한 영역이 없다" in report["recommendation"]


def test_empty_surface_says_so():
    assert rs.analyze([{"rule": "time_stop(30s)", "expectancy_pct": 1.0}])["available"] is False


def test_counts_cover_every_cell():
    report = rs.analyze(_plane([[1.0, 0.0, 1.0], [1.5, 9.0, 1.6], [1.4, 2.0, 1.5]]))
    assert sum(report["verdict_counts"].values()) == 9


# ---------------------------------------------------------------------------
# 표시
# ---------------------------------------------------------------------------

def test_ascii_map_marks_every_verdict():
    report = rs.analyze(_plane([[1.0, 0.0, 1.0], [1.5, 9.0, 1.6], [1.4, 2.0, 1.5]]))
    art = rs.render_ascii(report)
    assert "!" in art and "범례" in art
    # 행은 무장 축, 열은 되돌림 축 — 뒤바뀌면 격자를 잘못 읽는다.
    assert art.splitlines()[0].startswith("무장\\되돌림")


def test_ascii_handles_empty_report():
    assert rs.render_ascii({"available": False}) == "(응답면 없음)"
