"""X1 — 매수식 역생산 절 삭제 엔진 A/B (봉인본 2026-07-17_x1_buy_clause_drop_ab_preregistration.md, cb8a9d6a).

후보 4종(DROP5·DROP15·DROP29·DROP31)의 변형 매수식을 생성·검증(엔진 0)하고,
scratch strategy.db 등록·엔진 A/B 오케스트레이션·판정(C1~C4)을 담당한다.
기존 파일 무수정 — clause_lab(원문 로드)·bridge.registrar·hillclimb.engine_eval 재사용.
"""
from __future__ import annotations

__all__ = ["variants", "judge_x1", "orchestrate"]
