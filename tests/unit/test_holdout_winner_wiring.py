"""P5/M5 — loop.py winner 배선(graduation_holdout) 단위 테스트.

검증(백테/루프 실행 없음, tmp DB + monkeypatch):
  - graduation_holdout=ON: train 게이트 통과 + holdout 통과 → winner 갱신.
  - graduation_holdout=ON: train 게이트 통과 + holdout 실패 → winner 갱신 안 됨
    (best=graded는 그대로 갱신되어 진행은 막지 않는다).
  - graduation_holdout=OFF(기본): holdout 판정을 호출조차 하지 않고 기존 동작 유지
    (train 통과 = winner).

전략: 백테는 항상 성공으로, _score_outcome은 항상 게이트 통과 fit을 돌려주도록
monkeypatch한다. holdout 판정은 _compute_holdout_verdict를 직접 패치해 pass/fail을
결정론적으로 제어한다(CSV 의존 제거 — 배선만 검증).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.fitness.holdout import HoldoutVerdict  # noqa: E402
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402


def _neutralize(monkeypatch):
    """provider/생성/엔진호환/CSV 의존을 무력화(네트워크/DB/CSV 미사용)."""
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(
        L, "_generate_pair",
        lambda provider, cfg, rid, gen, fb, history_summary=None, sell_feedback=None,
        **kw: {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 1,
        },
    )
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")
    # 부검/피드백 비활성(CSV 안 읽음).
    monkeypatch.setattr(L, "_build_feedback", lambda *a, **k: (None, None, None))
    # 성공 백테(가짜 csv_path) — _compute_holdout_verdict는 별도 패치로 결과 제어.
    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, b, s: L.BacktestOutcome(
            True, "success", "fake.csv",
            {"cagr": 5.0, "mdd_pct": 10.0, "trade_count": 40, "total_profit_krw": 100000},
            "ok",
        ),
    )
    # train 게이트는 항상 통과(하드 composite=2.0).
    def _fake_score(outcome, cfg):
        fit = FitnessResult(score=2.0, calmar=2.0, uptrend_r2=1.0, gate_passed=True,
                            reason="ok", cagr=5.0, mdd=10.0, trade_count=40,
                            total_profit=100000.0)
        graded = GradedResult(
            graded=3.0, gate_passed=True, composite=2.0,
            trades_term=1.0, mdd_term=1.0, profit_term=1.0, uptrend_term=1.0,
            gate_distance="ok", cagr=5.0, mdd=10.0, trade_count=40,
            total_profit=100000.0, uptrend_r2=1.0,
        )
        return (fit, graded, None)
    monkeypatch.setattr(L, "_score_outcome", _fake_score)


def _run(monkeypatch, tmp_path, *, graduation_holdout, holdout_passed=None):
    """1세대 루프를 돌리고 (summary, holdout_call_count)를 돌려준다.

    holdout_passed가 None이면 _compute_holdout_verdict를 패치하지 않는다(OFF 검증용).
    값이 주어지면 그 통과여부를 돌려주는 verdict로 패치하고 호출 횟수를 센다.
    """
    _neutralize(monkeypatch)
    calls = {"n": 0}
    if holdout_passed is not None:
        def _fake_verdict(outcome, cfg):
            calls["n"] += 1
            return HoldoutVerdict(
                passed=holdout_passed, status="ok", trade_count=12,
                total_profit=5000.0 if holdout_passed else -5000.0,
                mdd_pct=8.0, reason="ok" if holdout_passed else "total_profit -5000 <= 0",
                holdout_days=[20260104, 20260105], train_trade_count=28,
            )
        monkeypatch.setattr(L, "_compute_holdout_verdict", _fake_verdict)

    config = LoopConfig(provider="openrouter", max_generations=1,
                        bt_engine_mode="cold", graduation_holdout=graduation_holdout,
                        autopsy_enabled=False,
                        cost_cap_generations=100, cost_cap_tokens=None)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        summary = L.run_loop(config, run_id="hwrun", state=st)
    finally:
        st.close()
    return summary, calls["n"]


def test_holdout_on_pass_promotes_winner(monkeypatch, tmp_path):
    """ON + train 통과 + holdout 통과 → winner 갱신."""
    summary, n_calls = _run(monkeypatch, tmp_path,
                            graduation_holdout=True, holdout_passed=True)
    assert n_calls == 1  # holdout 판정이 호출됨.
    assert summary["winner_gen"] == 0
    assert summary["winner_buy"] == "AILOOP_hwrun_g0_buy"
    assert summary["winner_score"] == 2.0


def test_holdout_on_fail_blocks_winner_but_keeps_best(monkeypatch, tmp_path):
    """ON + train 통과 + holdout 실패 → winner 미갱신, best(graded)는 그대로."""
    summary, n_calls = _run(monkeypatch, tmp_path,
                            graduation_holdout=True, holdout_passed=False)
    assert n_calls == 1
    # winner 없음(졸업 거절).
    assert summary["winner_gen"] == -1
    assert summary["winner_buy"] is None
    assert summary["winner_score"] is None
    # best=graded는 통과/holdout과 무관하게 갱신(진행은 막지 않는다).
    assert summary["best_gen"] == 0
    assert summary["best_score"] == 3.0


def test_holdout_off_keeps_legacy_winner_and_skips_check(monkeypatch, tmp_path):
    """OFF(기본): holdout 판정 호출 없이 train 통과 = winner(하위호환)."""
    _neutralize(monkeypatch)
    # holdout 판정이 호출되면 실패시키는 감시 패치(OFF면 호출되면 안 됨).
    called = {"n": 0}

    def _should_not_call(outcome, cfg):
        called["n"] += 1
        return HoldoutVerdict(passed=False, status="ok", trade_count=0,
                              total_profit=0.0, mdd_pct=0.0, reason="x")
    monkeypatch.setattr(L, "_compute_holdout_verdict", _should_not_call)

    config = LoopConfig(provider="openrouter", max_generations=1,
                        bt_engine_mode="cold", graduation_holdout=False,
                        autopsy_enabled=False,
                        cost_cap_generations=100, cost_cap_tokens=None)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    try:
        summary = L.run_loop(config, run_id="offrun", state=st)
    finally:
        st.close()

    assert called["n"] == 0  # OFF면 holdout 판정을 아예 호출하지 않는다.
    assert summary["winner_gen"] == 0
    assert summary["winner_score"] == 2.0
