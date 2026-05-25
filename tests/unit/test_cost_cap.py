"""US-005 Phase 2b — 종료(termination) / 비용 cap 단위 테스트 (네트워크 없음).

검증:
  (a) 세대-수 cap: gpt_auth처럼 토큰 비용 불투명 → gen_count >= cost_cap_generations
      에서 종료.
  (b) 토큰 cap: config.cost_cap_tokens 설정 시 누적 토큰 >= cap 에서 종료.
  (c) target_score 도달 시 종료.
  (d) 아무 조건도 안 맞으면 계속.
  (e) 토큰 cap 미설정(None)이면 토큰이 아무리 커도 토큰 사유로 종료하지 않는다
      (gpt_auth 기본 경로 — 세대-수 cap만 적용).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.termination import should_terminate  # noqa: E402


def test_generation_count_cap_stops_loop():
    """토큰 비용 불투명(gpt_auth 기본) → 세대-수 cap에서 종료."""
    config = LoopConfig(
        provider="gpt_auth",
        target_score=None,
        max_generations=1000,        # max-gen으로는 안 멈추게 크게.
        cost_cap_generations=5,
        cost_cap_tokens=None,        # 토큰 cap 미사용.
    )
    # 4세대: 아직 cap 미만 → 계속.
    stop, _ = should_terminate({"best_score": 0.0, "gen_count": 4, "tokens": 0}, config)
    assert stop is False
    # 5세대: cap 도달 → 종료.
    stop, reason = should_terminate({"best_score": 0.0, "gen_count": 5, "tokens": 0}, config)
    assert stop is True
    assert "cost_cap_generations" in reason


def test_token_cap_stops_loop_when_configured():
    """cost_cap_tokens 설정 시 누적 토큰 >= cap 에서 종료."""
    config = LoopConfig(
        provider="openrouter",
        target_score=None,
        max_generations=1000,
        cost_cap_generations=1000,   # 세대-수로는 안 멈추게.
        cost_cap_tokens=10_000,
    )
    stop, _ = should_terminate({"best_score": 0.0, "gen_count": 2, "tokens": 9_999}, config)
    assert stop is False
    stop, reason = should_terminate(
        {"best_score": 0.0, "gen_count": 2, "tokens": 10_000}, config
    )
    assert stop is True
    assert "cost_cap_tokens" in reason


def test_token_cap_ignored_when_not_configured():
    """cost_cap_tokens=None(gpt_auth 기본) → 토큰이 커도 토큰 사유로 종료 안 함."""
    config = LoopConfig(
        provider="gpt_auth",
        target_score=None,
        max_generations=1000,
        cost_cap_generations=1000,
        cost_cap_tokens=None,
    )
    stop, reason = should_terminate(
        {"best_score": 0.0, "gen_count": 1, "tokens": 10_000_000}, config
    )
    assert stop is False
    assert reason == "continue"


def test_target_score_stops_loop():
    """best_score >= target_score 면 종료."""
    config = LoopConfig(target_score=2.5, max_generations=1000, cost_cap_generations=1000)
    stop, _ = should_terminate({"best_score": 2.4, "gen_count": 1, "tokens": 0}, config)
    assert stop is False
    stop, reason = should_terminate({"best_score": 2.5, "gen_count": 1, "tokens": 0}, config)
    assert stop is True
    assert "target_score" in reason


def test_max_generations_stops_loop():
    """gen_count >= max_generations 면 종료."""
    config = LoopConfig(target_score=None, max_generations=3, cost_cap_generations=1000)
    stop, _ = should_terminate({"best_score": 0.0, "gen_count": 2, "tokens": 0}, config)
    assert stop is False
    stop, reason = should_terminate({"best_score": 0.0, "gen_count": 3, "tokens": 0}, config)
    assert stop is True
    assert "max_generations" in reason


def test_no_condition_met_continues():
    """아무 종료 조건도 안 맞으면 계속."""
    config = LoopConfig(target_score=10.0, max_generations=20, cost_cap_generations=50)
    stop, reason = should_terminate({"best_score": 1.0, "gen_count": 3, "tokens": 100}, config)
    assert stop is False
    assert reason == "continue"


def test_loop_stops_at_generation_cap_with_mock_provider(monkeypatch, tmp_path):
    """run_loop 통합: mock provider/backtest로 세대-수 cap에서 깔끔히 종료.

    네트워크/실백테스트 없이, 생성과 백테스트를 모두 가짜로 대체한다.
    cost_cap_generations=2, max_generations 크게 → cap이 먼저 작동하는지 확인.
    """
    from ai_strategy_loop.controller import loop as L
    from ai_strategy_loop.controller.state import LoopState

    config = LoopConfig(
        provider="openrouter",         # 프록시 안 띄움.
        target_score=None,
        max_generations=100,
        cost_cap_generations=2,        # 2세대에서 멈춰야 함.
        cost_cap_tokens=None,
    )

    # provider/프록시 기동을 무력화.
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    # 전략 생성도 무력화 (토큰만 약간 누적).
    monkeypatch.setattr(
        L, "_generate_pair",
        lambda provider, cfg, rid, gen, fb, history_summary=None: {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 100,
        },
    )
    # 백테스트는 항상 성공 + 가짜 메트릭.
    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, b, s: L.BacktestOutcome(True, "success", "fake.csv",
                                            {"cagr": 1.0, "mdd_pct": 1.0,
                                             "trade_count": 0, "total_profit_krw": 0},
                                            "ok"),
    )
    # fitness도 단순화 (CSV 안 읽음). _score_outcome은 이제 (fit, graded, err) 3-tuple.
    from ai_strategy_loop.fitness.score import FitnessResult, GradedResult
    monkeypatch.setattr(
        L, "_score_outcome",
        lambda outcome, cfg: (
            FitnessResult(score=0.0, calmar=0.0, uptrend_r2=0.0, gate_passed=False,
                          reason="gate fail", cagr=0.0, mdd=0.0, trade_count=0,
                          total_profit=0.0),
            GradedResult(graded=0.0, gate_passed=False, composite=0.0,
                         trades_term=0.0, mdd_term=1.0, profit_term=0.5,
                         uptrend_term=0.0, gate_distance="gate failed",
                         cagr=0.0, mdd=0.0, trade_count=0, total_profit=0.0,
                         uptrend_r2=0.0),
            None,
        ),
    )
    # gist 조회(루프 DB)도 무력화.
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")
    # 엔진 호환/스냅샷은 no-op로 둬도 무방 (loop DB 안 건드림).
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)

    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="caprun", state=st)

    assert summary["generations"] == 2
    assert "cost_cap_generations" in summary["stop_reason"]
    st.close()
