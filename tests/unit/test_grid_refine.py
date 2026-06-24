"""P4 — grid 2차패스 coarse-to-fine.

refine_candidates(1-D 경향성 요약 → 2차 grid 추천) + INTERACTION_PAIRS 사전선언
+ identity/신규-컬럼-금지 계약. 모두 순수·advisory(엔진·게이트·선택 규율 무변경).
"""

from __future__ import annotations

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.tmap.template import (  # noqa: E402
    grid_points,
    load_template,
    render,
)
from ai_strategy_loop.tmap.tendency import (  # noqa: E402
    INTERACTION_PAIRS,
    refine_candidates,
)


def _summary(scores: dict) -> dict:
    """plateau_score만 채운 최소 summarize_tendency 형태."""
    return {
        "run_id": "x",
        "baseline": {"profit": 1.0},
        "params": {
            name: {"plateau_score": s, "plateau": {"center_value": 0, "width": 1}}
            for name, s in scores.items()
        },
        "count": len(scores),
    }


class TestInteractionPairs:
    def test_pairs_declared_and_distinct(self) -> None:
        assert len(INTERACTION_PAIRS) >= 1
        for a, b in INTERACTION_PAIRS:
            assert a != b, "자기쌍 금지"

    def test_pairs_reference_seed_902905_params(self) -> None:
        names = {p.name for p in load_template("seed_902905").params}
        for a, b in INTERACTION_PAIRS:
            assert a in names and b in names, f"{a},{b} not in seed params"


class TestRefineCandidates:
    def test_ranks_by_plateau_score(self) -> None:
        out = refine_candidates(_summary({"cap_max": 8.0, "take_hard": 3.0, "strength_min": 0.5}))
        assert [n for n, _ in out["ranked"]][:2] == ["cap_max", "take_hard"]

    def test_prefers_declared_interaction_pair(self) -> None:
        out = refine_candidates(_summary({"cap_max": 8.0, "take_hard": 7.0, "strength_min": 6.0}))
        assert out["recommended_grid"] == ("cap_max", "take_hard")
        assert out["source"] == "interaction_pair"

    def test_fallback_to_top2_when_no_pair(self) -> None:
        out = refine_candidates(_summary({"strength_min": 8.0, "window_end": 7.0}))
        assert out["recommended_grid"] == ("strength_min", "window_end")
        assert out["source"] == "top2"
        assert out["passed_threshold"] is True

    def test_graceful_when_insufficient(self) -> None:
        out = refine_candidates(_summary({"cap_max": 1.0}))
        assert out["recommended_grid"] is None
        assert out["passed_threshold"] is False

    def test_empty_summary(self) -> None:
        out = refine_candidates({})
        assert out["recommended_grid"] is None
        assert out["ranked"] == []

    def test_only_positive_scores_are_strong(self) -> None:
        # plateau_score<=0(고원 없음/적자)인 변수는 grid 후보가 아니다.
        out = refine_candidates(_summary({"cap_max": 5.0, "take_hard": -2.0, "strength_min": 0.0}))
        assert out["recommended_grid"] is None  # strong 1개뿐 → 쌍 불가.
        assert out["passed_threshold"] is False

    def test_recommended_pair_is_gridable(self) -> None:
        t = load_template("seed_902905")
        out = refine_candidates(_summary({"cap_max": 8.0, "take_hard": 7.0}))
        a, b = out["recommended_grid"]
        pts = grid_points(t, a, b)  # 추천 쌍은 템플릿에 존재 → KeyError 없음.
        assert len(pts) == 1 + len(t.param(a).values) * len(t.param(b).values)

    def test_tie_break_is_deterministic_by_name(self) -> None:
        # 동률 plateau_score는 이름 오름차순으로 결정론적 — 입력 dict 순서와 무관.
        out1 = refine_candidates(_summary({"window_end": 5.0, "strength_min": 5.0}))
        out2 = refine_candidates(_summary({"strength_min": 5.0, "window_end": 5.0}))
        assert [n for n, _ in out1["ranked"]] == ["strength_min", "window_end"]
        assert out1["ranked"] == out2["ranked"]
        assert out1["recommended_grid"] == ("strength_min", "window_end")

    def test_template_filter_drops_unknown_params(self) -> None:
        # template 주어지면 템플릿에 없는 슬롯은 추천에서 배제 → grid_points KeyError 차단.
        t = load_template("seed_902905")
        summary = _summary({"cap_max": 9.0, "ghost_param": 8.0, "take_hard": 7.0})
        out = refine_candidates(summary, template=t)
        names = {n for n, _ in out["ranked"]}
        assert "ghost_param" not in names
        a, b = out["recommended_grid"]
        assert a in {p.name for p in t.params} and b in {p.name for p in t.params}


class TestGridByteIdentical:
    def test_default_render_is_seed_identity(self) -> None:
        buy, _sell = render(load_template("seed_902905"), {})
        assert "{cap_max}" not in buy
        assert "시가총액 < 3000" in buy  # cap_max 기본값 치환.

    def test_grid_points_introduce_no_new_columns(self) -> None:
        t = load_template("seed_902905")
        base = "\n".join(render(t, {}))
        base_tokens = set(re.findall(r"[가-힣A-Za-z_]+", base))
        for p in grid_points(t, "cap_max", "take_hard")[1:5]:
            toks = set(re.findall(r"[가-힣A-Za-z_]+", "\n".join(render(t, p["theta"]))))
            assert toks - base_tokens == set(), f"신규 식별자 유입: {toks - base_tokens}"
