"""백테스트 실패 원인 피드백 단위 테스트 (네트워크 없음).

문제: 세대의 67%가 불투명한 exit=2로 실패하는데 그 '원인'이 다음 세대에
전달되지 않아 모델이 맹목 변이를 한다.

검증:
  (a) no-trades(거래 0건 → metrics 없음) message → no_trades로 분류되고
      '진입 조건을 완화하라' actionable 피드백 + 비어있지 않은 이력 라인.
  (b) runtime-exception(자식 크래시/exec 예외) message → runtime_error로 분류되고
      그 원문을 포함한 '이 오류를 피하라' 피드백 + 비어있지 않은 이력 라인.
  (c) 루프 와이어링: 실패 세대가 분류된 구체 피드백을 next-gen generate에 넘기고,
      이력에 공백이 아닌 구체 사유를 기록한다.
  (d) 성공 세대는 여전히 graded/autopsy 경로(gate_failure_directive 등)를 쓴다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy import (  # noqa: E402
    backtest_error_feedback,
    backtest_error_history_line,
    classify_backtest_error,
)
from ai_strategy_loop.autopsy.summarize import (  # noqa: E402
    ERR_NO_TRADES,
    ERR_OTHER,
    ERR_RUNTIME,
    ERR_TIMEOUT,
)
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402


# Step-1 진단에서 캡처한 실제 errored 결과의 reason (가장 흔한 67% 케이스).
NO_TRADES_REASON = (
    "backtest non-success: exit=2 status=error "
    "message=backtest completed without metrics last_checkpoint=csv_detected csv=no"
)
# 자식 프로세스 크래시(런타임 오류) 케이스.
RUNTIME_REASON = (
    "backtest non-success: exit=1 status=error "
    "message=Backtest child process exited with code 1 last_checkpoint=backtest_started csv=no"
)
# exec 예외(전략 코드 안의 NameError 등) 케이스.
EXEC_EXC_REASON = (
    "backtest non-success: exit=1 status=error message=NameError: name 'xyz' is not defined csv=no"
)
TIMEOUT_REASON = "backtest timeout (>360s)"


# =====================================================================
# (a) no-trades 분류 + actionable 피드백 + 이력 라인.
# =====================================================================
def test_no_trades_classified_and_actionable():
    assert classify_backtest_error(NO_TRADES_REASON) == ERR_NO_TRADES

    fb = backtest_error_feedback(NO_TRADES_REASON, min_trades=10)
    assert fb  # 비어있지 않음.
    # 0거래/진입 과엄격 → 완화하라 가이드.
    assert "0건" in fb or "0거래" in fb or "진입" in fb
    assert "완화" in fb

    line = backtest_error_history_line(NO_TRADES_REASON)
    assert line.strip()  # 비어있지 않은 이력 라인.
    assert "백테스트 실패" in line
    # 공백 placeholder가 아니라 구체 사유가 들어 있다.
    assert "거래 0건" in line


# =====================================================================
# (b) runtime-exception 분류 + 원문 포함 피드백 + 이력 라인.
# =====================================================================
def test_runtime_error_classified_and_carries_message():
    assert classify_backtest_error(RUNTIME_REASON) == ERR_RUNTIME
    assert classify_backtest_error(EXEC_EXC_REASON) == ERR_RUNTIME

    fb = backtest_error_feedback(RUNTIME_REASON)
    assert fb
    assert "런타임 오류" in fb or "오류" in fb
    # 캡처된 구체 message가 피드백에 포함되어야 한다(맹목 변이 차단).
    assert "exited with code 1" in fb
    assert "피하라" in fb

    # exec 예외 원문(NameError 등)도 그대로 전달된다.
    fb2 = backtest_error_feedback(EXEC_EXC_REASON)
    assert "NameError" in fb2

    line = backtest_error_history_line(RUNTIME_REASON)
    assert line.strip()
    assert "런타임 오류" in line
    assert "exited with code 1" in line


def test_timeout_and_other_classified():
    assert classify_backtest_error(TIMEOUT_REASON) == ERR_TIMEOUT
    assert classify_backtest_error("backtest non-success: exit=3 status=error csv=no") == ERR_OTHER
    # timeout은 no_trades보다 우선 분류(오분류 방지).
    assert classify_backtest_error("timeout completed without metrics") == ERR_TIMEOUT


def test_feedback_and_history_never_empty_on_blank_reason():
    """reason이 비거나 None이어도 항상 비어있지 않은 문자열을 낸다."""
    for r in (None, "", "   "):
        assert backtest_error_feedback(r).strip()
        assert backtest_error_history_line(r).strip()


# =====================================================================
# (c) 루프 와이어링: 실패 세대 → 구체 피드백 next-gen 전달 + 구체 이력 라인.
# =====================================================================
def _capture_generation_feedback(monkeypatch):
    """_generate_pair에 전달되는 (autopsy_feedback, history_summary)를 세대별로 캡처."""
    captured = []

    def fake_generate(provider, cfg, rid, gen, fb, history_summary=None, sell_feedback=None):
        captured.append({"gen": gen, "feedback": fb, "history": history_summary,
                         "sell_feedback": sell_feedback})
        return {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 1,
        }

    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(L, "_generate_pair", fake_generate)
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")
    return captured


def test_loop_feeds_specific_error_cause_to_next_generation(monkeypatch, tmp_path):
    """gen0가 no-trades로 실패하면 gen1 generate가 '완화하라' 구체 피드백을 받고,
    이력에는 공백이 아닌 구체 사유가 들어간다."""
    captured = _capture_generation_feedback(monkeypatch)

    # gen0: no-trades 실패, gen1: runtime 실패 (둘 다 metrics 없음 → 실패 경로).
    reasons = {0: NO_TRADES_REASON, 1: RUNTIME_REASON}
    calls = {"n": -1}

    def fake_backtest(cfg, buy, sell):
        calls["n"] += 1
        r = reasons.get(calls["n"], NO_TRADES_REASON)
        return L.BacktestOutcome(False, "error", None, None, r)

    monkeypatch.setattr(L, "run_backtest_for", fake_backtest)

    # autopsy_enabled=True여야 실패-원인 피드백이 next-gen에 주입된다.
    config = LoopConfig(provider="openrouter", max_generations=2,
                        cost_cap_generations=100, cost_cap_tokens=None,
                        autopsy_enabled=True)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="errrun", state=st)

    # gen1 generate가 받은 피드백 = gen0(no-trades) 원인을 겨냥한 '완화하라'.
    gen1 = next(c for c in captured if c["gen"] == 1)
    assert gen1["feedback"], "gen1은 gen0 실패 원인 피드백을 받아야 한다"
    assert "완화" in gen1["feedback"]
    assert "0건" in gen1["feedback"] or "진입" in gen1["feedback"]

    # gen1 history_summary에 gen0의 구체 실패 사유가 보여야 한다(공백 아님).
    assert gen1["history"]
    assert "거래 0건" in gen1["history"] or "백테스트 실패" in gen1["history"]

    # DB 기록: 두 세대 모두 error/score0, reason에 구체 원인 보존.
    gens = st.get_generations("errrun")
    assert len(gens) == 2
    for g in gens:
        assert g["score"] == 0.0
        assert g["gate_passed"] == 0
    assert "without metrics" in gens[0]["reason"]
    assert "exited with code 1" in gens[1]["reason"]
    assert summary["generations"] == 2
    st.close()


# =====================================================================
# (d) 성공 세대는 여전히 graded/autopsy(gate_failure_directive) 경로를 쓴다.
# =====================================================================
def test_success_still_uses_graded_autopsy_path(monkeypatch, tmp_path):
    """성공 세대는 실패-원인 분기가 아니라 graded fitness + gate 피드백 경로를 탄다."""
    captured = _capture_generation_feedback(monkeypatch)

    # 성공 outcome (metrics + csv 보유) — 실패 분기를 타지 않는다.
    def ok_backtest(cfg, buy, sell):
        return L.BacktestOutcome(
            True, "success", "fake.csv",
            {"cagr": 1.0, "mdd_pct": 5.0, "trade_count": 20, "total_profit_krw": 1000},
            "ok",
        )

    monkeypatch.setattr(L, "run_backtest_for", ok_backtest)

    # gate 실패(하드 게이트 미통과)이지만 거래는 발생 → gate_failure_directive 경로.
    def fake_score(outcome, cfg):
        fit = FitnessResult(score=0.0, calmar=0.5, uptrend_r2=0.5, gate_passed=False,
                            reason="MDD 초과", cagr=1.0, mdd=20.0,
                            trade_count=20, total_profit=1000.0)
        graded = GradedResult(
            graded=0.7, gate_passed=False, composite=0.0,
            trades_term=1.0, mdd_term=0.5, profit_term=1.0, uptrend_term=0.5,
            gate_distance="MDD 20 > cap", cagr=1.0, mdd=20.0,
            trade_count=20, total_profit=1000.0, uptrend_r2=0.5,
        )
        return (fit, graded, None)

    monkeypatch.setattr(L, "_score_outcome", fake_score)

    config = LoopConfig(provider="openrouter", max_generations=2,
                        cost_cap_generations=100, cost_cap_tokens=None,
                        autopsy_enabled=True, mdd_cap=10.0, min_trades=10)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="okrun", state=st)

    # gen1이 받은 피드백은 '백테스트 실패 원인'(실패 분기)이 아니라 graded/gate 경로.
    gen1 = next(c for c in captured if c["gen"] == 1)
    fb = gen1["feedback"] or ""
    assert "백테스트 실패 원인" not in fb, "성공 세대는 실패-원인 분기를 타면 안 된다"
    # gate 실패 directive(매도/MDD 등)가 들어 있어야 한다.
    assert fb  # 성공이지만 gate 실패 → directive 존재.

    # DB: 성공 세대는 status=ok, graded 점수 기록.
    gens = st.get_generations("okrun")
    assert all(g["status"] == "ok" for g in gens)
    assert summary["best_score"] == 0.7  # graded로 best 선택.
    st.close()
