"""T3.2 라운드 후보 수·레인 쿼터 확장(opt-in) 단위 테스트.

핵심 검증 (LLM 실호출 없음 — provider 는 mock 콜러블 주입):
  - 기본값(None)이면 기존 4슬롯 정책 경로가 그대로다 (byte-동일 계약).
  - candidate_slots_override(2..12) + candidate_lane_quota(합계 일치)가
    라운드 후보 수 / LLM 팩 생산 lanes / 결정론 폴백 후보 수에 일관 적용된다.
  - 경계 위반(1, 13, 쿼터 합 불일치, 미지 레인, 쿼터 단독 설정)은
    fail-closed 로 반복 시작을 거부한다 (조용한 축소/보정 금지).
  - promotion-review / fast-discovery 레인에는 영향이 없다
    (promotion 은 여전히 zero-generation 차단, fast 는 candidate_count 유지).
"""

from dataclasses import asdict, fields
import json
import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.prompt import (  # noqa: E402
    DISCOVERY_RESEARCH_PROMPT_VERSION,
    REPAIR_RESEARCH_PROMPT_VERSION,
)
from ai_strategy_loop.controller.condition_discovery import (  # noqa: E402
    resolve_hybrid_research_slots,
)
from cli import research_loop  # noqa: E402
from cli.research_loop import (  # noqa: E402
    RESEARCH_SLOTS_OVERRIDE_MAX,
    RESEARCH_SLOTS_OVERRIDE_MIN,
    ResearchLoopConfig,
    run_research_iteration,
    validate_research_iteration_config,
)

PARENT_BUY_CODE = "if 현재가 > 시가 and 거래대금 > 10000:\n    self.Buy()"
PARENT_SELL_CODE = "if 수익률 < -1:\n    self.Sell()"
CREATED_AT = "2026-07-02T09:00:00"


def _repair_code(index):
    return f"if 현재가 > 시가 and 거래대금 > {30000 + 1000 * index}:\n    self.Buy()"


def _discovery_code(index):
    return f"if 등락율 > 3 and 회전율 > {index + 1}:\n    self.Buy()"


def _response(metadata, code):
    return (
        f"```python\n{code}\n```\n"
        f"```json\n{json.dumps(metadata, ensure_ascii=False)}\n```"
    )


def _repair_response(index):
    metadata = {
        "schema_version": 1,
        "lane": "repair",
        "prompt_version": REPAIR_RESEARCH_PROMPT_VERSION,
        "kind": "buy",
        "timeframe": "min",
        "parent_id": "BaseBuy",
        "analysis_card_id": "analysis-1",
        "intended_hypothesis": f"turnover 임계 조정 #{index}",
        "risk_note": "노이즈 진입 증가 위험",
        "mutation_axis": f"turnover_min_902 -> {30000 + 1000 * index}",
        "expected_effect": "거래수 변화 기대",
        "hypothesis_id": f"rh{index}",
    }
    return _response(metadata, _repair_code(index))


def _discovery_response(index):
    metadata = {
        "schema_version": 1,
        "lane": "discovery",
        "prompt_version": DISCOVERY_RESEARCH_PROMPT_VERSION,
        "kind": "buy",
        "timeframe": "min",
        "coverage_gap_id": "gap-1",
        "discovery_target_coverage": ["cap:small|time:0900"],
        "intended_hypothesis": f"회전율 계열 신규 탐색 #{index}",
        "novelty_rationale": "기존 팩과 다른 feature family",
        "risk_note": "한산장 미체결 위험",
        "mutation_axis": f"feature_family:회전율_{index}",
        "expected_effect": "커버리지 공백 채움",
        "hypothesis_id": f"dh{index}",
        "novelty": {"feature_family": f"회전율_{index}"},
    }
    return _response(metadata, _discovery_code(index))


class QueueProvider:
    """레인별 응답 큐 mock provider — 호출 메시지를 기록한다."""

    def __init__(self, repair=(), discovery=()):
        self.queues = {"repair": list(repair), "discovery": list(discovery)}
        self.calls = []

    def __call__(self, messages):
        user_text = messages[1]["content"]
        lane = "repair" if "repair 후보" in user_text else "discovery"
        self.calls.append({"lane": lane, "user_text": user_text})
        queue = self.queues[lane]
        assert queue, f"unexpected extra {lane} provider call"
        return queue.pop(0)


class DummyController:
    def __init__(self, baseline_csv=None, metrics=None):
        self.baseline_csv = baseline_csv
        self.metrics = metrics or {}
        self.runs = []

    def run(self, config_dict):
        self.runs.append(config_dict)
        result = {"status": "success", "metrics": dict(self.metrics)}
        if self.baseline_csv is not None:
            result["csv_path"] = self.baseline_csv
        return result


def _write_trade_csv(path):
    pd.DataFrame([
        {
            "종목명": "A",
            "매수시간": 202501010900,
            "매도시간": 202501010910,
            "매수가": 1000,
            "수익률": -1.0,
            "수익금": -1000,
            "R_MFE": 0.2,
            "R_MAE": -2.0,
        },
    ]).to_csv(path, index=False, encoding="utf-8-sig")


def _config(**overrides):
    base = dict(
        name="SlotsOverride",
        base_buy_strategy="BaseBuy",
        sell_strategy="BaseSell",
        is_tick=False,
        run_candidate=False,
        run_candidates=True,
        candidate_count=4,
        condition_discovery_process="process-research",
        condition_discovery_preset="research",
    )
    base.update(overrides)
    return ResearchLoopConfig(**base)


def _fast_config(**overrides):
    base = dict(
        name="FastLane",
        base_buy_strategy="BaseBuy",
        sell_strategy="BaseSell",
        is_tick=False,
        run_candidate=False,
        run_candidates=True,
        candidate_count=5,
        condition_discovery_preset="fast",
    )
    base.update(overrides)
    return ResearchLoopConfig(**base)


def _patch_common(monkeypatch):
    analysis = {
        "status": "ok",
        "recommended_candidates": [{"feature": "B_체결강도"}],
        "created_at": CREATED_AT,
    }
    monkeypatch.setattr(research_loop, "analyze_result_csv", lambda *a, **k: dict(analysis))

    def fake_load(db_path, name, strategy_type):
        codes = {"BaseBuy": PARENT_BUY_CODE, "BaseSell": PARENT_SELL_CODE}
        if name in codes:
            return {"status": "ok", "code": codes[name], "name": name}
        return {"status": "error", "message": "strategy not found", "name": name}

    monkeypatch.setattr(research_loop, "load_strategy_from_db", fake_load)

    def fake_annotate(candidates, *a, **k):
        return [
            {
                **candidate,
                "retention_estimate": {"estimated_retention": 1.0},
                "retention_filter_passed": True,
                "retention_fallback_used": False,
            }
            for candidate in candidates
        ]

    monkeypatch.setattr(research_loop, "annotate_candidate_retention", fake_annotate)
    monkeypatch.setattr(
        research_loop,
        "select_retention_aware_candidates",
        lambda candidates, **k: (candidates, {"status": "ok", "selected_count": len(candidates)}),
    )
    monkeypatch.setattr(
        research_loop,
        "delete_strategy_from_db",
        lambda *a, **k: {"status": "ok"},
    )


def _install_fake_execute(monkeypatch, executed_specs):
    comparison = {
        "baseline_summary": {"trade_count": 10, "win_rate": 0.5, "total_profit": 1000000.0},
        "candidate_summary": {"trade_count": 8, "win_rate": 0.625, "total_profit": 1500000.0},
        "trade_count_retention": 0.8,
    }

    def fake_execute(config, spec, controller, baseline_csv):
        executed_specs.append(dict(spec))
        return {
            "index": spec["index"],
            "strategy_name": spec["strategy_name"],
            "expression": spec["expression"],
            **{key: spec[key] for key in research_loop._RESEARCH_METADATA_KEYS if key in spec},
            "status": "ok",
            "phase": "candidate_evaluated",
            "candidate_csv": baseline_csv,
            "candidate_result": {"status": "success", "metrics": {"mdd": 7.5, "trade_count": 8}},
            "comparison": {key: (dict(value) if isinstance(value, dict) else value) for key, value in comparison.items()},
            "promotion": {"status": "ok", "passed": True, "score": 2.0},
            "cleanup": None,
            "rank": None,
            "rank_score": None,
            "selected_as_best": False,
        }

    monkeypatch.setattr(research_loop, "_execute_candidate_spec", fake_execute)


def _fallback_expression_result(count):
    return {
        "status": "ok",
        "expressions": [f"체결강도 < {200 + index}" for index in range(count)],
        "selected_candidates": [
            {"source": "quantile", "feature": f"B_f{index}"} for index in range(count)
        ],
        "candidate_count": count,
    }


# ------------------------------------------------------ config fields


def test_research_loop_config_has_slots_override_fields_default_none():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert "candidate_slots_override" in names
    assert "candidate_lane_quota" in names

    config = ResearchLoopConfig()
    assert config.candidate_slots_override is None
    assert config.candidate_lane_quota is None

    snapshot = asdict(config)
    assert snapshot["candidate_slots_override"] is None
    assert snapshot["candidate_lane_quota"] is None

    assert RESEARCH_SLOTS_OVERRIDE_MIN == 2
    assert RESEARCH_SLOTS_OVERRIDE_MAX == 12


# ------------------------------------------------------ 기본 불변 (4슬롯)


def test_default_path_keeps_four_slot_policy_unchanged():
    config = _config()
    assert research_loop._resolve_candidate_slots_override(config) is None
    assert research_loop._research_candidate_count(config) == 4

    plan = research_loop._build_hybrid_research_plan(config)
    assert plan["enabled"] is True
    assert plan["candidate_count"] == 4
    assert "candidate_slots_override" not in plan
    assert plan["slots"] == resolve_hybrid_research_slots()
    assert plan["slots"]["slots_by_lane"] == {"repair": 2, "discovery": 2}

    assert research_loop._llm_pack_lanes(config) == {"repair": 2, "discovery": 2}
    assert validate_research_iteration_config(config) == {"status": "ok"}


# ------------------------------------------------------ 8/12 슬롯 적용


def test_eight_slot_override_with_lane_quota_applies_consistently():
    config = _config(
        candidate_slots_override=8,
        candidate_lane_quota={"repair": 5, "discovery": 3},
    )
    assert validate_research_iteration_config(config) == {"status": "ok"}
    assert research_loop._research_candidate_count(config) == 8

    plan = research_loop._build_hybrid_research_plan(config)
    assert plan["candidate_count"] == 8
    assert plan["candidate_slots_override"] == {
        "slots_total": 8,
        "slots_by_lane": {"repair": 5, "discovery": 3},
    }
    slots = plan["slots"]
    assert slots["slots_total"] == 8
    assert slots["slots_by_lane"] == {"repair": 5, "discovery": 3}
    assert slots["decision_reason"] == "config_candidate_slots_override"
    assert slots["shift_applied"] == {"from": None, "to": None, "count": 0}
    assert slots["authority"] == "research_budget_steering_only"
    # 기본 정책 문서(slots_total=4)는 그대로다 — 오버라이드는 config 소유.
    assert plan["policy"]["slots_total"] == 4

    assert research_loop._llm_pack_lanes(config) == {"repair": 5, "discovery": 3}

    sequence = research_loop._hybrid_lane_sequence(slots)
    assert len(sequence) == 8
    assert sequence.count("repair") == 5
    assert sequence.count("discovery") == 3


def test_twelve_slot_override_without_quota_splits_evenly():
    config = _config(candidate_slots_override=12)
    assert validate_research_iteration_config(config) == {"status": "ok"}
    assert research_loop._research_candidate_count(config) == 12
    resolution = research_loop._resolve_candidate_slots_override(config)
    assert resolution == {
        "slots_total": 12,
        "slots_by_lane": {"repair": 6, "discovery": 6},
    }
    assert research_loop._llm_pack_lanes(config) == {"repair": 6, "discovery": 6}

    # 하한(2)과 홀수 분할(repair 우선)도 결정론이다.
    assert research_loop._resolve_candidate_slots_override(
        _config(candidate_slots_override=2)
    )["slots_by_lane"] == {"repair": 1, "discovery": 1}
    assert research_loop._resolve_candidate_slots_override(
        _config(candidate_slots_override=5)
    )["slots_by_lane"] == {"repair": 3, "discovery": 2}


# ------------------------------------------------------ 경계 거부 (fail-closed)


@pytest.mark.parametrize(
    "overrides, reason_fragment",
    [
        ({"candidate_slots_override": 1}, "between 2 and 12"),
        ({"candidate_slots_override": 13}, "between 2 and 12"),
        (
            {"candidate_slots_override": 8, "candidate_lane_quota": {"repair": 4, "discovery": 3}},
            "must equal candidate_slots_override",
        ),
        ({"candidate_lane_quota": {"repair": 2, "discovery": 2}}, "requires candidate_slots_override"),
        (
            {"candidate_slots_override": 8, "candidate_lane_quota": {"repair": 4, "discovery": 3, "sell_only": 1}},
            "unsupported lanes: sell_only",
        ),
        (
            {"candidate_slots_override": 3, "candidate_lane_quota": {"repair": 3, "discovery": 0}},
            "must be >= 1",
        ),
        (
            {"candidate_slots_override": 4, "candidate_lane_quota": {"repair": 4}},
            "must include lane discovery",
        ),
        ({"candidate_slots_override": True}, "must be an integer"),
    ],
)
def test_boundary_rejection_is_fail_closed(overrides, reason_fragment):
    config = _config(**overrides)
    validation = validate_research_iteration_config(config)
    assert validation["status"] == "error"
    assert validation["phase"] == "invalid_candidate_slots_override"
    assert reason_fragment in validation["message"]
    # 방어선: 해석기도 조용한 폴백 없이 즉시 중단한다.
    with pytest.raises(ValueError, match="candidate_slots_override_invalid"):
        research_loop._resolve_candidate_slots_override(config)


def test_invalid_override_blocks_iteration_before_baseline_run():
    controller = DummyController()
    result = run_research_iteration(_config(candidate_slots_override=13), controller)
    assert result["status"] == "error"
    assert result["phase"] == "invalid_candidate_slots_override"
    assert controller.runs == []


# ------------------------------------------------ promotion/fast 레인 무영향


def test_fast_lane_ignores_valid_override():
    config = _fast_config(
        candidate_slots_override=8,
        candidate_lane_quota={"repair": 4, "discovery": 4},
    )
    # fast-discovery 는 research 레인이 아니므로 후보 수는 candidate_count 그대로.
    assert research_loop._research_candidate_count(config) == 5

    plan = research_loop._build_hybrid_research_plan(config)
    assert plan["enabled"] is False
    assert plan["slots"] is None
    assert plan["candidate_count"] == 5
    assert "candidate_slots_override" not in plan

    assert research_loop._llm_pack_lanes(config) is None
    assert validate_research_iteration_config(config) == {"status": "ok"}


def test_promotion_review_stays_zero_generation_with_override():
    for slots_override in (8, 13):
        validation = validate_research_iteration_config(
            _config(
                condition_discovery_process="promotion-review",
                candidate_slots_override=slots_override,
            )
        )
        assert validation["status"] == "error"
        # 오버라이드가 promotion-review 의 zero-generation 차단을 풀지 않는다.
        assert validation["phase"] == "promotion_review_generation_blocked"


# ------------------------------------------- LLM 팩 lanes 일관 적용 (E2E)


def test_eight_slot_llm_pack_production_and_consumption(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    executed = []
    _install_fake_execute(monkeypatch, executed)
    provider = QueueProvider(
        repair=[_repair_response(index) for index in range(1, 6)],
        discovery=[_discovery_response(index) for index in range(1, 4)],
    )

    result = run_research_iteration(
        _config(
            baseline_csv=str(baseline),
            llm_candidate_pack_enabled=True,
            candidate_slots_override=8,
            candidate_lane_quota={"repair": 5, "discovery": 3},
        ),
        DummyController(),
        provider=provider,
    )

    assert result["status"] == "ok"
    wiring = result["analysis_result"]["research_candidate_pack_wiring"]
    assert wiring["status"] == "ok"

    # 팩 생산 lanes 가 쿼터 그대로 provider 호출에 반영된다.
    assert len(provider.calls) == 8
    lanes_called = [call["lane"] for call in provider.calls]
    assert lanes_called.count("repair") == 5
    assert lanes_called.count("discovery") == 3

    pack = result["analysis_result"]["research_candidate_pack"]
    assert len(pack["candidates"]) == 8
    assert pack["lane_accepted_counts"] == {"repair": 5, "discovery": 3}

    expression_result = result["expression_result"]
    assert expression_result["source"] == "llm_multi_hypothesis_candidate_pack"
    assert expression_result["prompt_maturity_credit_allowed"] is True
    assert expression_result["candidate_count"] == 8

    assert len(executed) == 8
    lanes_executed = [spec["research_lane"] for spec in executed]
    assert lanes_executed.count("repair") == 5
    assert lanes_executed.count("discovery") == 3

    research_plan = result["iteration_plan"]["research_loop"]
    assert research_plan["candidate_count"] == 8
    assert research_plan["candidate_slots_override"]["slots_total"] == 8


# ------------------------------------- 결정론 폴백 후보 수 일관 적용 (E2E)


def test_eight_slot_deterministic_fallback_uses_expanded_count(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    generation_calls = []

    def fake_generate(analysis_result, top_n):
        generation_calls.append(top_n)
        return _fallback_expression_result(count=top_n)

    monkeypatch.setattr(
        research_loop,
        "generate_condition_expressions_from_analysis",
        fake_generate,
    )
    executed = []
    _install_fake_execute(monkeypatch, executed)

    result = run_research_iteration(
        _config(
            baseline_csv=str(baseline),
            candidate_slots_override=8,
            candidate_lane_quota={"repair": 5, "discovery": 3},
        ),
        DummyController(),
    )

    assert result["status"] == "ok"
    # 폴백 풀 요청 크기도 확장 후보 수 기준(8 * multiplier)으로 커진다.
    assert generation_calls == [8 * 3]
    # 폴백 경로도 확장 후보 수(8)만큼 실행하고 credit 0 규약을 유지한다.
    assert len(executed) == 8
    lanes_executed = [spec["research_lane"] for spec in executed]
    assert lanes_executed.count("repair") == 5
    assert lanes_executed.count("discovery") == 3
    expression_result = result["expression_result"]
    assert expression_result["fallback_used"] is True
    assert expression_result["prompt_maturity_credit_allowed"] is False
    for spec in result["candidate_specs"]:
        assert spec["prompt_receipt"]["prompt_score"] == 0
