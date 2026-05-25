"""US-005 Phase 2b — 루프 robustness backstop 단위 테스트 (네트워크 없음).

검증:
  (a) 백테스트가 RAISE 하는 세대 → 그 세대 score=0으로 기록하고 루프가
      크래시/행 없이 다음 세대로 계속하며 깔끔히 종료한다.
  (b) 백테스트가 timeout-status(또는 status!=success)를 반환하는 세대 →
      동일하게 score=0 기록 후 계속.
  (c) 일부 세대는 정상 성공해도 전체 루프가 끝까지 돌고 종료한다.
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
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402


def _neutralize_provider_and_generation(monkeypatch):
    """provider 기동/전략 생성/엔진 호환을 무력화 (네트워크/DB 미사용)."""
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(
        L, "_generate_pair",
        lambda provider, cfg, rid, gen, fb, history_summary=None: {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 10,
        },
    )
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)


def test_loop_continues_when_backtest_raises(monkeypatch, tmp_path):
    """(a) 한 세대 백테스트가 예외를 던져도 score=0 기록 후 계속, 깔끔히 종료."""
    _neutralize_provider_and_generation(monkeypatch)

    raised = {"count": 0}

    def boom(cfg, buy, sell):
        raised["count"] += 1
        raise RuntimeError("simulated backtest crash")

    monkeypatch.setattr(L, "run_backtest_for", boom)

    config = LoopConfig(provider="openrouter", max_generations=3,
                        cost_cap_generations=100, cost_cap_tokens=None)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="boomrun", state=st)

    # 3세대 모두 시도 + 백테스트가 매번 호출됨 (행 없음).
    assert raised["count"] == 3
    assert summary["generations"] == 3
    assert "max_generations" in summary["stop_reason"]

    # 모든 세대가 score=0 / error 로 기록됨.
    gens = st.get_generations("boomrun")
    assert len(gens) == 3
    for g in gens:
        assert g["score"] == 0.0
        assert g["gate_passed"] == 0
        assert "backtest failed/timeout" in g["reason"]
    # 우승 없음.
    assert summary["best_score"] is None or summary["best_score"] == 0.0
    st.close()


def test_loop_continues_on_timeout_status(monkeypatch, tmp_path):
    """(b) 백테스트가 timeout/비성공 status를 반환해도 score=0 기록 후 계속."""
    _neutralize_provider_and_generation(monkeypatch)

    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, b, s: L.BacktestOutcome(
            False, "timeout", None, None, "backtest timeout (>360s)"
        ),
    )

    config = LoopConfig(provider="openrouter", max_generations=2,
                        cost_cap_generations=100, cost_cap_tokens=None)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="torun", state=st)

    assert summary["generations"] == 2
    gens = st.get_generations("torun")
    assert all(g["score"] == 0.0 for g in gens)
    assert all("timeout" in g["reason"] for g in gens)
    assert "max_generations" in summary["stop_reason"]
    st.close()


def test_loop_builds_summary_before_closing_own_state(monkeypatch, tmp_path):
    """run_loop이 자체 생성한 state(owns_state=True)를 닫기 전에 summary를 구성한다.

    회귀 가드: 예전엔 summary를 finally(=state.close()) 이후에 만들어
    sqlite3.ProgrammingError(Cannot operate on a closed database)로 크래시했다.
    state를 주입하지 않고(state=None) 기본 경로를 타게 해 이 경로를 검증한다.
    LOOP_RUNS_DB를 tmp로 리다이렉트해 운영 상태 파일을 건드리지 않는다.
    """
    _neutralize_provider_and_generation(monkeypatch)
    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, b, s: L.BacktestOutcome(False, "error", None, None, "no trades"),
    )

    # 기본 state 경로(owns_state=True)가 tmp DB를 쓰도록 LoopState 기본값을 패치.
    from ai_strategy_loop.controller import state as S
    monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "loop_runs.db")
    monkeypatch.setattr(S, "_SNAPSHOT_DIR", tmp_path / "snaps")

    config = LoopConfig(provider="openrouter", max_generations=2,
                        cost_cap_generations=100, cost_cap_tokens=None)
    # state 인자 없음 → run_loop이 자체 LoopState를 만들고 finally에서 닫는다.
    summary = L.run_loop(config, run_id="ownsrun")

    # 크래시 없이 summary가 정상 반환되고 generations 카운트가 채워져 있어야 한다.
    assert summary is not None
    assert summary["run_id"] == "ownsrun"
    assert summary["generations"] == 2
    assert "max_generations" in summary["stop_reason"]


def test_loop_mixes_success_and_failure_and_terminates(monkeypatch, tmp_path):
    """(c) 일부 성공 + 일부 실패 세대가 섞여도 루프가 끝까지 돌고 종료한다."""
    _neutralize_provider_and_generation(monkeypatch)

    calls = {"n": 0}

    def flaky(cfg, buy, sell):
        calls["n"] += 1
        if calls["n"] == 2:
            # 두 번째 세대만 실패(timeout).
            return L.BacktestOutcome(False, "timeout", None, None, "timeout")
        return L.BacktestOutcome(True, "success", "fake.csv",
                                 {"cagr": 1.0, "mdd_pct": 1.0,
                                  "trade_count": 0, "total_profit_krw": 0}, "ok")

    monkeypatch.setattr(L, "run_backtest_for", flaky)
    # 성공 세대의 graded: gen0 점수 1.5, 나머지 성공 세대 0.5 → best=gen0(graded).
    # 루프는 best를 GRADED 점수로 선택하므로 graded 값으로 best가 결정된다.
    score_map = {1: 1.5, 3: 0.5}

    def fake_score(outcome, cfg):
        n = calls["n"]
        sc = score_map.get(n, 0.0)
        fit = FitnessResult(score=sc, calmar=sc, uptrend_r2=1.0, gate_passed=sc > 0,
                            reason="ok" if sc > 0 else "gate", cagr=1.0, mdd=1.0,
                            trade_count=5, total_profit=100.0)
        graded = GradedResult(
            graded=sc, gate_passed=sc > 0, composite=sc if sc > 0 else 0.0,
            trades_term=1.0, mdd_term=1.0, profit_term=1.0, uptrend_term=1.0,
            gate_distance="ok" if sc > 0 else "gate failed",
            cagr=1.0, mdd=1.0, trade_count=5, total_profit=100.0, uptrend_r2=1.0,
        )
        return (fit, graded, None)

    monkeypatch.setattr(L, "_score_outcome", fake_score)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")

    config = LoopConfig(provider="openrouter", max_generations=3,
                        cost_cap_generations=100, cost_cap_tokens=None)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="mixrun", state=st)

    assert summary["generations"] == 3
    assert "max_generations" in summary["stop_reason"]
    # gen0(성공, graded 1.5)이 best.
    assert summary["best_gen"] == 0
    assert summary["best_score"] == 1.5
    assert summary["best_buy"] == "AILOOP_mixrun_g0_buy"

    gens = st.get_generations("mixrun")
    assert len(gens) == 3
    # gen1(인덱스1)은 timeout 실패.
    assert gens[1]["score"] == 0.0
    assert "timeout" in gens[1]["reason"]
    st.close()


def test_run_backtest_for_returns_outcome_when_stock_select_fails(monkeypatch):
    """MEDIUM-3: _select_single_stock가 raise해도 run_backtest_for는 절대 raise하지
    않고 구체 사유를 담은 실패 BacktestOutcome을 반환한다(never-raises 계약)."""

    def boom(*a, **k):
        raise RuntimeError("no moneytop rows")

    monkeypatch.setattr(L, "_select_single_stock", boom)

    # bt_one_code/bt_start/bt_end 미지정 → 런타임 자동 선택 경로를 타고 raise.
    config = LoopConfig(provider="openrouter", bt_timeframe="min")
    outcome = L.run_backtest_for(config, "buy_x", "sell_x")

    assert isinstance(outcome, L.BacktestOutcome)
    assert outcome.ok is False
    assert outcome.status == "error"
    assert "stock selection failed" in outcome.reason
    assert "no moneytop rows" in outcome.reason
