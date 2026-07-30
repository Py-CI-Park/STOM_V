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


# ------------------------------------------------------ QSP2 홀드아웃 동반 판정
def test_overfit_divergence_design_up_holdout_down():
    # 설계 +20%/+15% 개선인데 홀드아웃 -10%/-12% 악화 2연속 → 과최적 발산.
    h = _h(-100, -80, -68)
    j = judge(h, seed_trades=1000, holdout=[-50.0, -55.0, -62.0])
    assert j.state == "diverged" and "과최적 괴리" in j.reason


def test_convergence_requires_holdout_not_net_worse():
    # 설계 정체(ε 미만 3연속)인데 홀드아웃 순악화 → 수렴이 아니라 과최적 정체(발산).
    h = _h(100, 101, 101.5, 101.7)
    j = judge(h, seed_trades=1000, holdout=[50.0, 49.0, 47.0, 44.0])
    assert j.state == "diverged" and "과최적 정체" in j.reason


def test_convergence_with_holdout_held():
    h = _h(100, 101, 101.5, 101.7)
    j = judge(h, seed_trades=1000, holdout=[50.0, 50.5, 51.0, 51.2])
    assert j.state == "converged" and "홀드아웃 순유지" in j.reason


def test_holdout_none_entries_are_tolerated():
    h = _h(-100, -80, -70)
    j = judge(h, seed_trades=1000, holdout=[None, -55.0, -50.0])
    assert j.state == "continue"
