"""A-3 — 정본 연구 프로파일/토글 배선 계약 테스트.

1) 연구 프리셋(_COMMON_DISCOVERY)이 정본 ON-세트를 포함한다.
2) 프리셋의 모든 config 키는 LoopConfig 선언 필드다(오타/ad-hoc 키 차단).
3) run_loop 경로(_generate_pair)가 principle_gate/structure_principles 토글을
   config에서 읽어 generate_strategy로 전달한다(소스 계약 — config.py 주석의
   "루프가 읽지 않는다" 상태로 되돌아가는 회귀 차단).
"""
import dataclasses
import inspect

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.scripts.research_presets import PresetName, preset_payload

_CANONICAL_ON_KEYS = (
    # 생성 품질/탐색
    "sparse_positive_prompt_enabled",
    "exec_budget_prompt_enabled",
    "report_principles_enabled",
    "structure_principles_prompt_enabled",
    "require_filter_gates",
    "few_shot_enabled",
    # 청산/리스크
    "sell_exec_budget_guard_enabled",
    "mdd_control_enabled",
    "exit_edge_feedback_enabled",
    # 게이트/증거
    "principle_gate_enabled",
    "evidence_ledger_enabled",
    # 환류
    "segment_feedback_enabled",
    "quantile_feedback_enabled",
    "counterfactual_feedback_enabled",
    "hypothesis_tracking_enabled",
    "feature_importance_feedback_enabled",
    "exit_forensics_feedback_enabled",
    "meta_seed_enabled",
    # 분산
    "dispersion_prompt_enabled",
    "dispersion_enabled",
)


def test_both_presets_carry_canonical_on_set():
    for name in PresetName:
        config = preset_payload(name)["config"]
        for key in _CANONICAL_ON_KEYS:
            assert config.get(key) is True, f"{name.value}: {key} 가 ON이 아님"


def test_preset_keys_are_declared_loopconfig_fields():
    declared = {f.name for f in dataclasses.fields(LoopConfig)}
    for name in PresetName:
        config = preset_payload(name)["config"]
        unknown = sorted(set(config) - declared)
        assert not unknown, f"{name.value}: LoopConfig 미선언 키 {unknown}"


def test_loop_wires_gate_and_structure_toggles_into_generation():
    from ai_strategy_loop.controller import loop as loop_mod

    src = inspect.getsource(loop_mod._generate_pair)
    assert 'structure_principles_prompt_enabled=getattr(config, "structure_principles_prompt_enabled"' in src
    assert 'principle_gate_enabled=getattr(config, "principle_gate_enabled"' in src
