"""QSP1 P3 — 수렴/발산 판정기 단위 테스트 (마스터플랜 §2 규격 고정)."""

from __future__ import annotations

from ai_strategy_loop.revision.convergence import RoundStat, judge


def _h(*objs, trades=1000):
    return [RoundStat(i, float(o), trades) for i, o in enumerate(objs)]


def test_empty_history_continues():
    assert judge([], seed_trades=1000).state == "continue"


def test_improving_rounds_continue():
    j = judge(_h(-100, -80, -50), seed_trades=1000)
    assert j.state == "continue"
    assert j.improvement_pct and j.improvement_pct > 0


def test_converged_after_three_flat_rounds():
    # 개선 +1%·+0.5%·+0.2% — 3연속 < ε(2%) → 수렴.
    j = judge(_h(100, 101, 101.5, 101.7), seed_trades=1000)
    assert j.state == "converged", j.reason


def test_two_flat_rounds_not_yet_converged():
    j = judge(_h(100, 101, 101.5), seed_trades=1000)
    assert j.state == "continue"


def test_trade_collapse_diverges():
    # 과조임: 시드 1000건 → 베스트 200건(<30%).
    h = _h(-100, -60)
    h[-1] = RoundStat(1, -60.0, 200)
    j = judge(h, seed_trades=1000)
    assert j.state == "diverged" and "과조임" in j.reason


def test_oscillation_diverges():
    # 개선율 +100%/-50%/+80%/-40% 큰 진폭 교대 → 진동 발산.
    j = judge(_h(100, 200, 100, 180, 108), seed_trades=1000)
    assert j.state == "diverged" and "진동" in j.reason


def test_negative_objective_uses_relative_improvement():
    # 손실 축소(-100 → -50)는 +50% 개선으로 계산돼야 한다.
    j = judge(_h(-100, -50), seed_trades=1000)
    assert j.state == "continue"
    assert j.improvement_pct is not None and abs(j.improvement_pct - 50.0) < 1e-6


def test_near_zero_baseline_falls_back_to_absolute():
    j = judge(_h(0.0, 5.0), seed_trades=1000)
    assert j.state == "continue"  # 0 나눗셈 폭주 없이 판정.
