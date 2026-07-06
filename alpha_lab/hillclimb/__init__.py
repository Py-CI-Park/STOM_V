"""alpha_lab.hillclimb — v3 P3 결정론 힐클라임 패키지.

봉인 근거: docs/research/condition_research/research_runs/alpha_lab_v3_20260706/
preregistration_v3.json (sha 50d3d38a) hillclimb 절.

구성:
  - mutator: Rule/Clause/Metrics 타입, 분위 임계 이동 수학, 이웃 생성, 수락 규칙.
  - features_v3: 파생 18항(annex 통과분) 포함 43피처 화이트리스트 번역기
    (기존 alpha_lab.translate.{codegen,idioms} 재사용 + 추가, 무수정).
  - seeds: ALP_V2SEED_01~10 실명 규칙(시드 인수인계 문서 동결값) + 번역 헬퍼.
  - loop: 시드 1개에 대한 힐클라임 실행(엔진 평가 함수는 호출측 주입 — 테스트는 mock).
"""
from __future__ import annotations

from alpha_lab.hillclimb.loop import (
    DEFAULT_PER_SEED_MAX,
    TRAIN_GATE_DAILY_MIN,
    TRAIN_GATE_MDD_MAX,
    SeedResult,
    run_seed_hillclimb,
    train_gate_pass,
)
from alpha_lab.hillclimb.mutator import (
    Clause,
    Metrics,
    Move,
    Rule,
    accept,
    generate_moves,
)

__all__ = [
    "DEFAULT_PER_SEED_MAX",
    "TRAIN_GATE_DAILY_MIN",
    "TRAIN_GATE_MDD_MAX",
    "Clause",
    "Metrics",
    "Move",
    "Rule",
    "SeedResult",
    "accept",
    "generate_moves",
    "run_seed_hillclimb",
    "train_gate_pass",
]
