"""T3.1w LLM 후보팩 생산 실배선 + 축 원장 배선 단위 테스트.

핵심 검증 (LLM 실호출 없음 — provider 는 mock 콜러블 주입):
  - llm_candidate_pack_enabled=True + provider 주입이면 mock provider 로
    팩 생산 → analysis_result['research_candidate_pack'] 주입 → 소비 →
    prompt_maturity_credit 인정 경로가 동작한다 (4슬롯 캡 유지).
  - 생산 실패(provider 예외 terminal)면 기존 결정론 폴백 + credit 0.
  - provider 미주입 + 토글 ON 은 llm_pack_provider_missing 사유 기록 후 폴백.
  - axis_ledger_path 설정 시 (a) 사전확률 라인이 repair 프롬프트에 주입되고,
    (b) 라운드 평가 완료 후 부모 대비 delta 가 원장에 기록된다 (왕복).
    recorded_at 은 analysis_result 의 기존 created_at 재사용 (시계 금지 규약).
  - 필수 필드 미확보 후보는 기록을 스킵하고 사유만 남긴다 (집계 오염 금지).
  - 토글 OFF(기본)면 기존 동작 불변 — provider 는 호출되지 않고 additive
    키(research_candidate_pack_wiring/axis_ledger_recording)도 생기지 않는다.
"""

from dataclasses import asdict, fields
import json
import os
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.prompt import (  # noqa: E402
    DISCOVERY_RESEARCH_PROMPT_VERSION,
    REPAIR_RESEARCH_PROMPT_VERSION,
)
from ai_strategy_loop.controller.axis_ledger import AxisLedger  # noqa: E402
from cli import research_loop  # noqa: E402
from cli.research_loop import ResearchLoopConfig, run_research_iteration  # noqa: E402

PARENT_BUY_CODE = "if 현재가 > 시가 and 거래대금 > 10000:\n    self.Buy()"
PARENT_SELL_CODE = "if 수익률 < -1:\n    self.Sell()"
REPAIR_CODE_1 = "if 현재가 > 시가 and 거래대금 > 30000:\n    self.Buy()"
REPAIR_CODE_2 = "if 현재가 > 시가 and 체결강도 > 120:\n    self.Buy()"
DISCOVERY_CODE_1 = "if 등락율 > 3 and 회전율 > 1.5:\n    self.Buy()"
DISCOVERY_CODE_2 = "if 고가 > 시가 * 1.02 and 전일비 > 150:\n    self.Buy()"
REPAIR_AXIS = "turnover_min_902 1.5 -> 3.0"
DISCOVERY_AXIS = "feature_family:회전율"
CREATED_AT = "2026-07-02T09:00:00"


def _response(metadata, code):
    return (
        f"```python\n{code}\n```\n"
        f"```json\n{json.dumps(metadata, ensure_ascii=False)}\n```"
    )


def _repair_metadata(**extra):
    payload = {
        "schema_version": 1,
        "lane": "repair",
        "prompt_version": REPAIR_RESEARCH_PROMPT_VERSION,
        "kind": "buy",
        "timeframe": "min",
        "parent_id": "BaseBuy",
        "analysis_card_id": "analysis-1",
        "intended_hypothesis": "turnover 임계만 완화",
        "risk_note": "노이즈 진입 증가 위험",
        "mutation_axis": REPAIR_AXIS,
        "expected_effect": "거래수 +20% 기대",
        "hypothesis_id": "rh1",
    }
    payload.update(extra)
    return payload


def _discovery_metadata(**extra):
    payload = {
        "schema_version": 1,
        "lane": "discovery",
        "prompt_version": DISCOVERY_RESEARCH_PROMPT_VERSION,
        "kind": "buy",
        "timeframe": "min",
        "coverage_gap_id": "gap-1",
        "discovery_target_coverage": ["cap:small|time:0900"],
        "intended_hypothesis": "회전율 반전 계열 신규 탐색",
        "novelty_rationale": "기존 팩과 다른 feature family",
        "risk_note": "한산장 미체결 위험",
        "mutation_axis": DISCOVERY_AXIS,
        "expected_effect": "커버리지 공백 채움",
        "hypothesis_id": "dh1",
        "novelty": {"feature_family": "회전율_reversal"},
    }
    payload.update(extra)
    return payload


def _valid_repair_responses():
    return [
        _response(_repair_metadata(hypothesis_id="rh1"), REPAIR_CODE_1),
        _response(_repair_metadata(hypothesis_id="rh2"), REPAIR_CODE_2),
    ]


def _valid_discovery_responses():
    return [
        _response(_discovery_metadata(hypothesis_id="dh1"), DISCOVERY_CODE_1),
        _response(_discovery_metadata(hypothesis_id="dh2"), DISCOVERY_CODE_2),
    ]


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
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ExplodingProvider:
    """호출되면 안 되는 provider — 토글 OFF 불변 검증용."""

    def __call__(self, messages):
        raise AssertionError("provider must not be called")


class FailingProvider:
    """호출 즉시 예외 — pack_producer terminal 실패 경로."""

    def __init__(self):
        self.call_count = 0

    def __call__(self, messages):
        self.call_count += 1
        raise RuntimeError("provider down")


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
        name="LlmWiring",
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


def _patch_common(monkeypatch, analysis_extra=None):
    analysis = {
        "status": "ok",
        "recommended_candidates": [{"feature": "B_체결강도"}],
        "created_at": CREATED_AT,
    }
    if analysis_extra:
        analysis.update(analysis_extra)
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


_DEFAULT_COMPARISON = {
    "baseline_summary": {"trade_count": 10, "win_rate": 0.5, "total_profit": 1000000.0},
    "candidate_summary": {"trade_count": 8, "win_rate": 0.625, "total_profit": 1500000.0},
    "trade_count_retention": 0.8,
}


def _install_fake_execute(
    monkeypatch,
    executed_specs,
    *,
    comparison=None,
    candidate_metrics=None,
    promotion=None,
):
    comparison = _DEFAULT_COMPARISON if comparison is None else comparison
    candidate_metrics = {"mdd": 7.5, "trade_count": 8} if candidate_metrics is None else candidate_metrics
    promotion = {"status": "ok", "passed": True, "score": 2.0} if promotion is None else promotion

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
            "candidate_result": {"status": "success", "metrics": dict(candidate_metrics)},
            "comparison": {key: (dict(value) if isinstance(value, dict) else value) for key, value in comparison.items()},
            "promotion": dict(promotion),
            "cleanup": None,
            "rank": None,
            "rank_score": None,
            "selected_as_best": False,
        }

    monkeypatch.setattr(research_loop, "_execute_candidate_spec", fake_execute)


def _fallback_expression_result(count=4):
    return {
        "status": "ok",
        "expressions": ["체결강도 < 90", "등락율 < 5", "거래대금 > 1000", "회전율 > 1"][:count],
        "selected_candidates": [
            {"source": "quantile", "feature": f"B_f{index}"} for index in range(count)
        ],
        "candidate_count": count,
    }


# ------------------------------------------------------ config fields


def test_research_loop_config_has_llm_pack_wiring_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert "llm_candidate_pack_enabled" in names
    assert "axis_ledger_path" in names

    config = ResearchLoopConfig()
    assert config.llm_candidate_pack_enabled is False
    assert config.axis_ledger_path == ""

    snapshot = asdict(config)
    assert snapshot["llm_candidate_pack_enabled"] is False
    assert snapshot["axis_ledger_path"] == ""


# ------------------------------------------------- production -> credit


def test_llm_pack_production_to_consumption_grants_prompt_credit(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    executed = []
    _install_fake_execute(monkeypatch, executed)
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())

    result = run_research_iteration(
        _config(baseline_csv=str(baseline), llm_candidate_pack_enabled=True),
        DummyController(),
        provider=provider,
    )

    assert result["status"] == "ok"
    wiring = result["analysis_result"]["research_candidate_pack_wiring"]
    assert wiring["status"] == "ok"
    assert wiring["failure_reason"] == ""
    assert wiring["authority"] == "research_only_no_export_live_or_final_promotion"

    pack = result["analysis_result"]["research_candidate_pack"]
    assert pack["candidate_pack_version"] == "multi_hypothesis_candidate_pack_v1"
    assert len(pack["candidates"]) == 4
    assert pack["mode_authority"] == "research_only"

    expression_result = result["expression_result"]
    assert expression_result["source"] == "llm_multi_hypothesis_candidate_pack"
    assert expression_result["prompt_maturity_credit_allowed"] is True
    assert expression_result["fallback_used"] is False
    # 4슬롯 캡: process-research 정책의 slots_total=4 그대로.
    assert expression_result["candidate_count"] == 4
    assert len(executed) == 4
    lanes = [spec["research_lane"] for spec in executed]
    assert lanes.count("repair") == 2
    assert lanes.count("discovery") == 2
    assert len(provider.calls) == 4

    for spec in result["candidate_specs"]:
        assert spec["prompt_maturity_credit_allowed"] is True
        assert spec["research_contract"]["prompt_maturity_credit_allowed"] is True
        assert spec["prompt_receipt"]["prompt_score"] > 0
        assert spec["candidate_pack_id"] == pack["candidate_pack_id"]


# ------------------------------------------- failure -> fallback credit 0


def test_llm_pack_production_failure_falls_back_credit_zero(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        "generate_condition_expressions_from_analysis",
        lambda *a, **k: _fallback_expression_result(),
    )
    executed = []
    _install_fake_execute(monkeypatch, executed)
    provider = FailingProvider()

    result = run_research_iteration(
        _config(baseline_csv=str(baseline), llm_candidate_pack_enabled=True),
        DummyController(),
        provider=provider,
    )

    assert provider.call_count == 1  # provider 예외는 terminal — 재시도 없음.
    wiring = result["analysis_result"]["research_candidate_pack_wiring"]
    assert wiring["status"] == "error"
    assert wiring["failure_reason"] == "llm_pack_production_failed"
    assert "research_candidate_pack" not in result["analysis_result"]

    expression_result = result["expression_result"]
    assert expression_result["fallback_used"] is True
    assert expression_result["prompt_maturity_credit_allowed"] is False
    assert expression_result["fallback_reason"] == "llm_pack_production_failed"

    assert result["status"] == "ok"
    for spec in result["candidate_specs"]:
        assert spec["prompt_maturity_credit_allowed"] is False
        assert spec["prompt_receipt"]["prompt_score"] == 0


def test_llm_pack_provider_missing_records_reason_then_falls_back(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        "generate_condition_expressions_from_analysis",
        lambda *a, **k: _fallback_expression_result(),
    )
    executed = []
    _install_fake_execute(monkeypatch, executed)

    result = run_research_iteration(
        _config(baseline_csv=str(baseline), llm_candidate_pack_enabled=True),
        DummyController(),
    )

    wiring = result["analysis_result"]["research_candidate_pack_wiring"]
    assert wiring["status"] == "skipped"
    assert wiring["failure_reason"] == "llm_pack_provider_missing"

    expression_result = result["expression_result"]
    assert expression_result["fallback_used"] is True
    assert expression_result["fallback_reason"] == "llm_pack_provider_missing"
    assert expression_result["prompt_maturity_credit_allowed"] is False
    for spec in result["candidate_specs"]:
        assert spec["prompt_receipt"]["prompt_score"] == 0


def test_apply_llm_candidate_pack_keeps_externally_injected_pack():
    analysis = {"status": "ok", "research_candidate_pack": {"candidates": []}}
    out = research_loop._apply_llm_candidate_pack(
        _config(llm_candidate_pack_enabled=True),
        analysis,
        None,
        ExplodingProvider(),
    )
    assert out is analysis


# --------------------------------------------------- axis ledger 왕복


def _seed_ledger(path):
    ledger = AxisLedger(path)
    for index, delta_profit in enumerate((1500000.0, 900000.0), start=1):
        ledger.record({
            "run_id": f"seed-{index}",
            "parent_id": "BaseBuy",
            "candidate_id": f"seed-cand-{index}",
            "axis": "entry_strength",
            "param": "entry_strength",
            "from_value": 90,
            "to_value": 100,
            "delta_profit": delta_profit,
            "delta_mdd": -1.0,
            "delta_trades": -3,
            "delta_win_rate": 0.05,
            "slippage_profile": "tick2",
            "window": "0-0",
            "verdict": "improved",
            "recorded_at": "2026-07-01T00:00:00",
        })
    return ledger


def test_axis_ledger_round_trip_prompt_injection_and_recording(monkeypatch, tmp_path):
    ledger_path = tmp_path / "axis_ledger.jsonl"
    _seed_ledger(ledger_path)
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    executed = []
    # 실 컨트롤러 run metrics 키('mdd_pct', cli/runner.py) 그대로 사용 —
    # 회귀 재현: 구형 키('mdd')만 조회하면 전 후보가 missing_delta_mdd 스킵된다.
    _install_fake_execute(
        monkeypatch,
        executed,
        candidate_metrics={"mdd_pct": 7.5, "trade_count": 8},
    )
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())
    controller = DummyController(baseline_csv=str(baseline), metrics={"mdd_pct": 10.0})

    result = run_research_iteration(
        _config(llm_candidate_pack_enabled=True, axis_ledger_path=str(ledger_path)),
        controller,
        provider=provider,
    )

    assert result["status"] == "ok"
    # (a) 사전확률 라인 주입 — repair 프롬프트 분석 컨텍스트에 나타난다.
    wiring = result["analysis_result"]["research_candidate_pack_wiring"]
    assert wiring["status"] == "ok"
    assert wiring["axis_prompt_line_count"] > 0
    assert wiring["axis_priors_error"] == ""
    repair_calls = [call for call in provider.calls if call["lane"] == "repair"]
    assert repair_calls
    assert any("변이축 사전확률" in call["user_text"] for call in repair_calls)
    assert any("entry_strength" in call["user_text"] for call in repair_calls)

    # (b) 라운드 평가 완료 후 부모 대비 delta 기록.
    recording = result["axis_ledger_recording"]
    assert recording["path"] == str(ledger_path)
    assert recording["recorded_count"] == 4
    assert recording["skipped"] == []
    assert recording["error"] == ""

    entries = list(AxisLedger(ledger_path).iter_entries())
    assert len(entries) == 2 + 4
    new_entries = entries[2:]
    for entry in new_entries:
        # recorded_at 은 analysis_result 의 기존 created_at 재사용 (시계 금지).
        assert entry["recorded_at"] == CREATED_AT
        assert entry["run_id"] == "LlmWiring"
        assert entry["parent_id"] in {"BaseBuy"}
        assert entry["delta_profit"] == 500000.0
        assert entry["delta_trades"] == -2.0
        assert abs(entry["delta_win_rate"] - 0.125) < 1e-9
        assert entry["delta_mdd"] == -2.5
        assert entry["verdict"] == "improved"
        assert entry["window"] == "0-0"
        assert isinstance(entry["slippage_profile"], str) and entry["slippage_profile"]
        assert entry["schema_version"] == 1
    axes = {entry["axis"] for entry in new_entries}
    assert REPAIR_AXIS in axes
    assert DISCOVERY_AXIS in axes

    # 왕복: 기록된 원장이 다시 결정론 집계로 읽힌다.
    priors = AxisLedger(ledger_path).aggregate_axis_priors()
    assert priors["entry_strength"]["n"] == 2
    assert priors[REPAIR_AXIS]["n"] == 2
    assert priors[REPAIR_AXIS]["improve_rate"] == 1.0


def test_axis_ledger_entry_accepts_legacy_mdd_keys():
    # 'mdd_pct'(실 컨트롤러) 외에 합성/구형 페이로드 키('mdd'/'max_drawdown')도
    # 폴백으로 계속 해석된다.
    for key in ("mdd", "max_drawdown"):
        candidate = {
            "status": "ok",
            "strategy_name": f"cand_{key}",
            "mutation_axis": REPAIR_AXIS,
            "comparison": dict(_DEFAULT_COMPARISON),
            "candidate_result": {"status": "success", "metrics": {key: 7.5}},
            "promotion": {"status": "ok", "passed": True, "score": 2.0},
        }
        entry, skipped = research_loop._axis_ledger_entry_for_candidate(
            _config(),
            candidate,
            recorded_at=CREATED_AT,
            baseline_metrics={key: 10.0},
        )
        assert skipped == []
        assert entry is not None
        assert entry["delta_mdd"] == -2.5


def test_axis_ledger_skips_candidates_missing_required_fields(monkeypatch, tmp_path):
    ledger_path = tmp_path / "axis_ledger.jsonl"
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        "generate_condition_expressions_from_analysis",
        lambda *a, **k: _fallback_expression_result(),
    )
    executed = []
    # mutation_axis 없음(결정론 폴백) + baseline_summary/MDD 미확보.
    _install_fake_execute(
        monkeypatch,
        executed,
        comparison={"candidate_summary": {"trade_count": 8}, "trade_count_retention": 1.0},
        candidate_metrics={"trade_count": 8},
    )

    result = run_research_iteration(
        _config(baseline_csv=str(baseline), axis_ledger_path=str(ledger_path)),
        DummyController(),
    )

    assert result["status"] == "ok"
    recording = result["axis_ledger_recording"]
    assert recording["recorded_count"] == 0
    assert len(recording["skipped"]) == 4
    reasons = {reason for item in recording["skipped"] for reason in item["reasons"]}
    assert "missing_mutation_axis" in reasons
    assert "missing_delta_mdd" in reasons
    # 기록이 없으면 원장 파일도 만들지 않는다 (집계 오염 금지).
    assert not ledger_path.exists()


# --------------------------------------------------- 토글 OFF 불변


def test_toggle_off_keeps_existing_behavior_and_four_slot_cap(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        "generate_condition_expressions_from_analysis",
        lambda *a, **k: _fallback_expression_result(),
    )
    executed = []
    _install_fake_execute(monkeypatch, executed)

    result = run_research_iteration(
        _config(baseline_csv=str(baseline)),
        DummyController(),
        provider=ExplodingProvider(),
    )

    assert result["status"] == "ok"
    # additive 키가 전혀 생기지 않는다 (기존 결과 스키마 불변).
    assert "research_candidate_pack_wiring" not in result["analysis_result"]
    assert "research_candidate_pack" not in result["analysis_result"]
    assert "axis_ledger_recording" not in result
    # 4슬롯 캡 회귀: process-research 는 여전히 4슬롯 고정.
    research_plan = result["iteration_plan"]["research_loop"]
    assert research_plan["candidate_count"] == 4
    assert research_plan["policy"]["slots_total"] == 4
    assert len(executed) == 4
    # 기존 폴백 사유 그대로.
    assert result["expression_result"]["fallback_reason"] == "llm_candidate_pack_missing"


def test_apply_llm_candidate_pack_off_returns_identical_object():
    analysis = {"status": "ok"}
    out = research_loop._apply_llm_candidate_pack(_config(), analysis, None, ExplodingProvider())
    assert out is analysis
    out_no_provider = research_loop._apply_llm_candidate_pack(_config(), analysis, None, None)
    assert out_no_provider is analysis


# ------------------------------------------------- DR-04 final-owner wiring
# ===================================================================
# final_owner_selection_enabled is opt-in (default OFF) and layered strictly
# on top of the already-opt-in llm_candidate_pack_enabled -- flipping it on
# alone (without llm_candidate_pack_enabled) has zero effect, since pack
# production itself is skipped.
# ===================================================================


def test_research_loop_config_has_final_owner_selection_field():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert "final_owner_selection_enabled" in names
    config = ResearchLoopConfig()
    assert config.final_owner_selection_enabled is False
    assert asdict(config)["final_owner_selection_enabled"] is False


def test_final_owner_selection_enabled_end_to_end_selects_official_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    executed = []
    _install_fake_execute(monkeypatch, executed)
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())

    result = run_research_iteration(
        _config(
            baseline_csv=str(baseline),
            llm_candidate_pack_enabled=True,
            final_owner_selection_enabled=True,
        ),
        DummyController(),
        provider=provider,
    )

    assert result["status"] == "ok"
    pack = result["analysis_result"]["research_candidate_pack"]
    assert "final_owner_selection" in pack
    selection = pack["final_owner_selection"]
    assert selection["selected"] is not None
    assert selection["pool_blockers"] == []
    hypothesis_ids = {c["hypothesis_id"] for c in pack["candidates"]}
    assert selection["selected"]["candidate_id"] in hypothesis_ids


def test_final_owner_selection_enabled_without_llm_pack_has_no_effect(monkeypatch, tmp_path):
    baseline = tmp_path / "baseline.csv"
    _write_trade_csv(baseline)
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        "generate_condition_expressions_from_analysis",
        lambda *a, **k: _fallback_expression_result(),
    )
    executed = []
    _install_fake_execute(monkeypatch, executed)

    result = run_research_iteration(
        _config(baseline_csv=str(baseline), final_owner_selection_enabled=True),
        DummyController(),
        provider=ExplodingProvider(),
    )

    assert result["status"] == "ok"
    # llm_candidate_pack_enabled stays False (default), so pack production is
    # skipped entirely regardless of final_owner_selection_enabled -- byte-동일
    # to the OFF/OFF path.
    assert "research_candidate_pack_wiring" not in result["analysis_result"]
    assert "research_candidate_pack" not in result["analysis_result"]
