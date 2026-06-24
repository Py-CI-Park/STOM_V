"""P0b (2026-06-15) — refine_gate.gate_candidate 배선 계약 테스트 (모킹, 백테 미실행).

드라이버(claude_candidate_batch_eval) 호출 인터페이스 + [m2] 서브스텝0 결정론/반복안정
분기를 모킹으로 검증한다. 실백테 1건 검증은 통합표식(별도 라이브 실행)으로 분리.

실행:
  PYTHONUTF8=1 python -m pytest tests/unit/test_refine_gate_wire.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401

from ai_strategy_loop.tmap import refine_gate  # noqa: E402

_BUY = "매수 = True\nif not (관심종목 == 1):\n    매수 = False\nif 매수:\n    self.Buy()"
_SELL = "매도 = False\nif 수익률 >= 5:\n    매도 = True\nif 매도:\n    self.Sell()"


@pytest.fixture()
def _no_materialize(monkeypatch):
    """재료화(DB 저장) 모킹 — 전략명만 반환, DB·검증 미접촉."""
    monkeypatch.setattr(refine_gate, "materialize_candidate",
                        lambda label, b, s, tf="tick": (f"GATE_{label}_B", f"GATE_{label}_S"))


def _mock_rebacktest(monkeypatch, profits):
    """_rebacktest_once가 profits 리스트를 순차 반환하도록 모킹(반복 호출 대응)."""
    seq = iter(profits)
    monkeypatch.setattr(refine_gate, "_rebacktest_once",
                        lambda *a, **k: next(seq, None))


class TestGateCandidateWire:
    def test_accepts_positive_rebacktest(self, monkeypatch, _no_materialize) -> None:
        """재백테 흑자 → 채택(passed True)."""
        _mock_rebacktest(monkeypatch, [2_000_000.0])
        r = refine_gate.gate_candidate(_BUY, _SELL, "cfg.json", label="good",
                                       in_sample_lift=2_100_000.0)
        assert r["passed"] is True
        assert r["profit"] == 2_000_000.0
        assert "채택" in r["reason"]

    def test_refuses_post_hoc_negative(self, monkeypatch, _no_materialize) -> None:
        """사후슬라이스(in-sample +, 재백테 −) → 기각 + 착시 사유."""
        _mock_rebacktest(monkeypatch, [-1_152_966.0])
        r = refine_gate.gate_candidate(_BUY, _SELL, "cfg.json", label="hcase",
                                       in_sample_lift=1_070_000.0)
        assert r["passed"] is False
        assert "사후슬라이스 착시" in r["reason"]

    def test_determinism_equal_marks_deterministic(self, monkeypatch, _no_materialize) -> None:
        """repeats=2 동일 profit → deterministic True (서브스텝0 (a)분기)."""
        _mock_rebacktest(monkeypatch, [1_000_000.0, 1_000_000.0])
        r = refine_gate.gate_candidate(_BUY, _SELL, "cfg.json", label="det",
                                       repeats=2)
        assert r["deterministic"] is True
        assert r["passed"] is True

    def test_sign_instability_refused(self, monkeypatch, _no_materialize) -> None:
        """repeats=2 부호 불안정 + noise_margin → 거짓기각 가드로 기각 (서브스텝0 (b))."""
        _mock_rebacktest(monkeypatch, [300_000.0, -200_000.0])
        r = refine_gate.gate_candidate(_BUY, _SELL, "cfg.json", label="noisy",
                                       repeats=2, noise_margin=100_000.0)
        assert r["passed"] is False
        assert "부호 불안정" in r["reason"] or "마진부족" in r["reason"]

    def test_conservative_min_profit_used(self, monkeypatch, _no_materialize) -> None:
        """반복시 보수적으로 min(profit)으로 게이트 — 노이즈하 거짓통과 방지."""
        _mock_rebacktest(monkeypatch, [2_000_000.0, -50_000.0])
        r = refine_gate.gate_candidate(_BUY, _SELL, "cfg.json", label="cons", repeats=2)
        assert r["profit"] == -50_000.0
        assert r["passed"] is False  # min이 음수라 기각

    def test_all_rebacktest_fail_refused(self, monkeypatch, _no_materialize) -> None:
        """드라이버 결과 없음 → 기각(채택 불가)."""
        _mock_rebacktest(monkeypatch, [None])
        r = refine_gate.gate_candidate(_BUY, _SELL, "cfg.json", label="fail")
        assert r["passed"] is False
        assert "재백테 실패" in r["reason"]
