"""P5 — 얇은 자율 부검 폐루프 오케스트레이터.

plan_candidates(순수: 변이 제안→렌더→가드) + run_autopsy_loop(주입 gate_fn으로 P0b 채택).
백테/실게이트 없이 모킹으로 '게이트 통과분만 채택·게이트 우회 0' 오케스트레이션을 검증한다.
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.scripts.tmap_autopsy_loop import (  # noqa: E402
    _anchor_from_summary,
    plan_candidates,
    run_autopsy_loop,
)
from ai_strategy_loop.tmap.template import load_template  # noqa: E402


def _summary(scores: dict) -> dict:
    return {
        "run_id": "x",
        "params": {
            name: {"plateau_score": s, "plateau": {"center_value": 2000, "width": 3}}
            for name, s in scores.items()
        },
    }


class TestPlanCandidates:
    def test_renders_validated_candidates_and_recommends_grid(self) -> None:
        t = load_template("seed_902905")
        plan = plan_candidates(t, _summary({"cap_max": 8.0, "take_hard": 7.0}), {})
        assert plan["candidates"], "변이 후보가 있어야 한다"
        for c in plan["candidates"]:
            assert isinstance(c["buy_code"], str) and isinstance(c["sell_code"], str)
            assert "{cap_max}" not in c["buy_code"]  # 슬롯 전부 치환됨.
            assert c["theta"]
        assert plan["recommended_grid"] == ("cap_max", "take_hard")

    def test_graceful_empty_template_summary(self) -> None:
        t = load_template("seed_902905")
        plan = plan_candidates(t, {}, {})
        # 요약 없어도 변이 제안은 가능(refine_grid만 None).
        assert plan["recommended_grid"] is None
        assert isinstance(plan["candidates"], list)


class TestRunAutopsyLoop:
    def test_adopts_only_gate_passed_no_bypass(self) -> None:
        t = load_template("seed_902905")
        summary = _summary({"cap_max": 8.0, "take_hard": 7.0})
        calls = []

        def fake_gate(buy, sell, config_path, *, label, in_sample_lift=None):
            calls.append(label)
            passed = "cap_max" in label  # 임의 규칙: cap_max 변이만 통과.
            return {"passed": passed, "profit": 1_000 if passed else -1_000, "reason": "mock"}

        out = run_autopsy_loop(t, summary, "cfg.json", gate_fn=fake_gate, max_candidates=6)
        # 후보당 정확히 1회 게이트 호출(게이트 우회 0).
        assert out["n_candidates"] == len(calls)
        assert len(out["adopted"]) + len(out["rejected"]) == out["n_candidates"]
        # 채택은 통과분뿐, 기각은 비통과뿐.
        assert all(a["gate"]["passed"] for a in out["adopted"])
        assert all(not r["gate"]["passed"] for r in out["rejected"])
        # cap_max 변이가 첫 후보들에 있으므로 채택이 1건 이상.
        assert len(out["adopted"]) >= 1
        assert all("cap_max" in a["label"] for a in out["adopted"])

    def test_max_candidates_caps_gate_calls(self) -> None:
        t = load_template("seed_902905")
        summary = _summary({"cap_max": 5.0})
        seen = []

        def fake_gate(buy, sell, config_path, *, label, in_sample_lift=None):
            seen.append(label)
            return {"passed": False, "profit": -1.0}

        out = run_autopsy_loop(t, summary, "cfg.json", gate_fn=fake_gate, max_candidates=3)
        assert out["n_candidates"] == 3
        assert len(seen) == 3  # 상한 초과 게이트 호출 없음(백테 예산 보호).


def test_anchor_from_summary_collects_plateau_centers() -> None:
    anchor = _anchor_from_summary(_summary({"cap_max": 8.0, "take_hard": 7.0}))
    assert anchor == {"cap_max": 2000, "take_hard": 2000}
    assert _anchor_from_summary({}) == {}
