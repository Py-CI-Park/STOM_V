"""P0a (2026-06-15) — refine_gate.decide 오프라인 픽스처 회귀 테스트.

게이트 *판정 로직*이 옳은지 백테 없이 결정론으로 검증한다(해금 게이트 아님 — P0b가 해금).
백테 0회: 픽스처는 문서화된 H사례 숫자 암기(사후슬라이스 +1.07M → 재백테 −1.15M).

실행:
  PYTHONUTF8=1 python -m pytest tests/unit/test_refine_gate.py -q
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401

from ai_strategy_loop.tmap.refine_gate import decide  # noqa: E402

_FIXTURE = Path(PROJECT_ROOT) / "tests" / "fixtures" / "refine_gate" / "hcase_post_hoc.json"


def _fixture() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


# =====================================================================
# ★핵심 통과조건 (P0a): H사례 기각 ∧ known-good 채택
# =====================================================================

class TestRefineGateDecide:
    def test_hcase_post_hoc_is_refused(self) -> None:
        """사후슬라이스 착시(in-sample +1.07M → 재백테 −1.15M) → 반드시 기각."""
        h = _fixture()["hcase_post_hoc"]
        passed, reason = decide(h["in_sample_lift"], h["rebacktest_profit"])
        assert passed is h["expected_passed"] is False, f"H사례 기각 실패: {reason}"
        assert "기각" in reason

    def test_known_good_is_accepted(self) -> None:
        """재백테가 흑자 재현(엣지 유지) → 채택."""
        g = _fixture()["known_good"]
        passed, reason = decide(g["in_sample_lift"], g["rebacktest_profit"])
        assert passed is g["expected_passed"] is True, f"known-good 채택 실패: {reason}"
        assert "채택" in reason

    # ----- 로직 경계 -----
    def test_missing_rebacktest_refused(self) -> None:
        """재백테 결측 → 채택 불가(게이트 규율)."""
        passed, reason = decide(1_000_000.0, None)
        assert passed is False
        assert "결측" in reason

    def test_sign_reversal_reason_mentions_illusion(self) -> None:
        """부호반전 사유에 '사후슬라이스 착시' 명시(진단 가독성)."""
        passed, reason = decide(500_000.0, -300_000.0)
        assert passed is False
        assert "사후슬라이스 착시" in reason

    def test_zero_rebacktest_refused_by_default(self) -> None:
        """재백테 0(소멸)도 기본 임계(>0)서 기각."""
        passed, _ = decide(800_000.0, 0.0)
        assert passed is False

    def test_positive_rebacktest_accepted_even_with_low_insample(self) -> None:
        """재백테가 진실원 — in-sample 결측이어도 재백테 흑자면 채택."""
        passed, reason = decide(None, 1_500_000.0)
        assert passed is True
        assert "채택" in reason

    @pytest.mark.parametrize("min_thr,profit,expected", [
        (0.0, 1.0, True),
        (500_000.0, 400_000.0, False),   # 임계 미달 → 기각
        (500_000.0, 600_000.0, True),
    ])
    def test_min_threshold(self, min_thr: float, profit: float, expected: bool) -> None:
        passed, _ = decide(1_000_000.0, profit, min_rebacktest_profit=min_thr)
        assert passed is expected
