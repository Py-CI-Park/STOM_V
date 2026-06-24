"""P5 — 앵커 변이(mutator) 단위 테스트.

propose_mutations: 현재 최적 θ(anchor)에서 출발해, 각 슬롯의 ParamSpec.values 중
**anchor 값의 정렬상 인접(좌/우)** 후보로 한 슬롯씩만 바꾼 변이 θ를 제안한다.
백테/게이트 호출 없음(제안만) — 순수·advisory·무예외. 신규 컬럼/횡단면 항 0.
"""

from __future__ import annotations

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.tmap.template import load_template, render  # noqa: E402
from ai_strategy_loop.tmap.mutator import (  # noqa: E402
    propose_mutations,
    render_mutation,
)


def _seed():
    return load_template("seed_902905")


class TestProposeMutationsBasic:
    def test_defaults_anchor_produces_adjacent_per_slot(self) -> None:
        t = _seed()
        muts = propose_mutations(t, {})  # 빈 dict → defaults 앵커.
        assert muts, "변이가 하나도 생성되지 않음"
        # 각 변이는 단 한 슬롯만 anchor와 다르다.
        defaults = t.defaults()
        for m in muts:
            diff = [k for k in m["theta"] if m["theta"][k] != defaults[k]]
            assert diff == [m["param"]], f"한 슬롯만 변해야 함: {diff}"

    def test_neighbor_values_are_adjacent_in_spec_values(self) -> None:
        t = _seed()
        muts = propose_mutations(t, {})
        defaults = t.defaults()
        for m in muts:
            spec = t.param(m["param"])
            vals = list(spec.values)
            anchor_val = defaults[m["param"]]
            idx = vals.index(anchor_val)
            neighbors = set()
            if idx - 1 >= 0:
                neighbors.add(vals[idx - 1])
            if idx + 1 < len(vals):
                neighbors.add(vals[idx + 1])
            assert m["value"] in neighbors, f"{m['param']}={m['value']} 인접 아님"
            assert m["from"] == anchor_val

    def test_max_per_param_limits_two_each(self) -> None:
        t = _seed()
        muts = propose_mutations(t, {}, max_per_param=2)
        per_param: dict = {}
        for m in muts:
            per_param[m["param"]] = per_param.get(m["param"], 0) + 1
        for name, count in per_param.items():
            assert count <= 2, f"{name} 변이 {count}개 > 2"

    def test_max_per_param_one_keeps_only_one_side(self) -> None:
        t = _seed()
        muts = propose_mutations(t, {}, max_per_param=1)
        per_param: dict = {}
        for m in muts:
            per_param[m["param"]] = per_param.get(m["param"], 0) + 1
        for count in per_param.values():
            assert count <= 1

    def test_label_format(self) -> None:
        t = _seed()
        for m in propose_mutations(t, {}):
            assert m["label"] == f"MUT {m['param']}={m['value']}"


class TestProposeMutationsRender:
    def test_every_mutation_renders_without_keyerror(self) -> None:
        t = _seed()
        for m in propose_mutations(t, {}):
            buy, sell = render_mutation(t, m["theta"])
            assert "{" not in buy or "{name}" not in buy  # 모든 슬롯 치환됨.
            assert isinstance(buy, str) and isinstance(sell, str)

    def test_no_new_identifiers_introduced(self) -> None:
        t = _seed()
        base = "\n".join(render(t, {}))
        base_tokens = set(re.findall(r"[가-힣A-Za-z_]+", base))
        for m in propose_mutations(t, {}):
            toks = set(re.findall(r"[가-힣A-Za-z_]+", "\n".join(render_mutation(t, m["theta"]))))
            assert toks - base_tokens == set(), f"신규 식별자 유입: {toks - base_tokens}"

    def test_render_mutation_matches_template_render(self) -> None:
        t = _seed()
        m = propose_mutations(t, {})[0]
        assert render_mutation(t, m["theta"]) == render(t, m["theta"])


class TestProposeMutationsAnchorVariants:
    def test_interior_anchor_yields_both_sides(self) -> None:
        # cap_max=3000 은 values [1500,2000,2500,3000,4000,6000,10000]의 내부 →
        # 좌(2500)·우(4000) 둘 다 나와야 한다.
        t = _seed()
        muts = propose_mutations(t, {"cap_max": 3000}, params=["cap_max"])
        vals = {m["value"] for m in muts}
        assert vals == {2500, 4000}

    def test_edge_anchor_yields_one_side(self) -> None:
        # cap_max=1500 은 좌측 끝 → 우(2000)만.
        t = _seed()
        muts = propose_mutations(t, {"cap_max": 1500}, params=["cap_max"])
        vals = {m["value"] for m in muts}
        assert vals == {2000}

    def test_right_edge_anchor_yields_one_side(self) -> None:
        t = _seed()
        muts = propose_mutations(t, {"cap_max": 10000}, params=["cap_max"])
        vals = {m["value"] for m in muts}
        assert vals == {6000}

    def test_params_filter_restricts_slots(self) -> None:
        t = _seed()
        muts = propose_mutations(t, {}, params=["take_hard"])
        assert {m["param"] for m in muts} == {"take_hard"}

    def test_anchor_carried_in_unchanged_slots(self) -> None:
        # 비대상 슬롯의 anchor 값이 변이 theta에 그대로 실린다.
        t = _seed()
        anchor = {"cap_max": 2000, "take_hard": 4}
        muts = propose_mutations(t, anchor, params=["cap_max"])
        assert muts
        for m in muts:
            assert m["theta"]["take_hard"] == 4  # 비대상 슬롯 anchor 보존.
            assert m["param"] == "cap_max"


class TestPurityAndEdges:
    def test_anchor_not_mutated(self) -> None:
        t = _seed()
        anchor = {"cap_max": 3000, "take_hard": 5}
        snapshot = dict(anchor)
        propose_mutations(t, anchor)
        assert anchor == snapshot, "anchor_theta 원본이 변형됨"

    def test_no_duplicate_thetas(self) -> None:
        t = _seed()
        seen = []
        for m in propose_mutations(t, {}):
            key = tuple(sorted(m["theta"].items()))
            assert key not in seen, "중복 theta"
            seen.append(key)

    def test_anchor_equal_theta_excluded(self) -> None:
        t = _seed()
        defaults = t.defaults()
        for m in propose_mutations(t, {}):
            assert m["theta"] != defaults, "anchor와 동일한 theta가 제안됨"

    def test_unknown_anchor_key_is_ignored(self) -> None:
        t = _seed()
        muts = propose_mutations(t, {"ghost_param": 999, "cap_max": 3000})
        for m in muts:
            assert "ghost_param" not in m["theta"]
        # 정상 슬롯 변이는 여전히 생성된다.
        assert any(m["param"] == "cap_max" for m in muts)

    def test_anchor_value_not_in_spec_values_skips_slot(self) -> None:
        # anchor가 values에 없는 값(인접 정의 불가)이면 그 슬롯은 graceful skip.
        t = _seed()
        muts = propose_mutations(t, {"cap_max": 12345}, params=["cap_max"])
        assert muts == []

    def test_empty_template_returns_empty(self) -> None:
        from ai_strategy_loop.tmap.template import TemplateSpec  # noqa: PLC0415

        empty = TemplateSpec(
            name="empty", timeframe="tick", buy_code="x=1", sell_code="y=1", params=()
        )
        assert propose_mutations(empty, {}) == []

    def test_non_dict_anchor_returns_empty(self) -> None:
        t = _seed()
        assert propose_mutations(t, None) == []  # type: ignore[arg-type]

    def test_max_per_param_zero_returns_empty(self) -> None:
        t = _seed()
        assert propose_mutations(t, {}, max_per_param=0) == []

    def test_unknown_params_filter_yields_empty(self) -> None:
        t = _seed()
        assert propose_mutations(t, {}, params=["nope"]) == []

    def test_render_mutation_empty_theta_is_identity(self) -> None:
        t = _seed()
        assert render_mutation(t, {}) == render(t, {})
