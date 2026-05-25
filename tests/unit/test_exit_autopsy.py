"""US-006 PROFITABILITY — 청산(EXIT) 부검 + 매도(SELL) 피드백 단위 테스트.

검증:
  - 합성 CSV(고 MFE / 저 실현 = give-back, 깊은 MAE = 손절 느슨)에서
    analyze_exits가 give-back gap과 손실 MAE를 잡아낸다.
  - summarize_exits가 익절/손절을 언급하는 매도(SELL)용 가이드를 만든다.
  - 보유시간/매도규칙 분포가 손실 집중 규칙을 지목한다.
  - 엣지 케이스(거래 0건, 전부 수익, MFE 컬럼 없음)를 깔끔히 처리한다.
  - is_holdout=True → ValueError.
  - 루프 와이어링: 매도(sell) 세대는 청산 피드백, 매수(buy) 세대는 진입 피드백을
    받는다(mock provider). autopsy_fn=None 경로(US-005)도 유지.
"""

import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy import analyze_exits, summarize_exits  # noqa: E402
from ai_strategy_loop.autopsy.analyze import (  # noqa: E402
    HOLD_COLUMN,
    MAE_COLUMN,
    MFE_COLUMN,
    RETURN_COLUMN,
    SELL_RULE_COLUMN,
    STATUS_INSUFFICIENT,
    STATUS_OK,
    STATUS_SINGLE_CLASS,
)
from ai_strategy_loop.config import LoopConfig  # noqa: E402


def _write_csv(path, rows):
    """rows(list of dict) → utf-8-sig CSV (실데이터와 동일 인코딩)."""
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)


def _giveback_rows(n_win=20, n_loss=20):
    """give-back + 깊은 MAE를 가진 합성 거래.

    - 수익 거래: MFE 3.0% 근처로 올랐지만 실현 0.8% (약 2.2%p 반납).
      손절 룰 '익절'로 닫힘.
    - 손실 거래: MAE -4.5% 까지 깊이 물린 뒤 실현 -1.5%. 손절 룰 '손절'로 닫힘.
      손실 거래는 보유시간을 길게(수익의 ~2배) 둬 시간청산 신호도 만든다.
    """
    rows = []
    for i in range(n_win):
        rows.append({
            RETURN_COLUMN: 0.8 + (i % 3) * 0.05,
            MFE_COLUMN: 3.0 + (i % 4) * 0.1,
            MAE_COLUMN: -0.2,
            HOLD_COLUMN: 3 + (i % 2),
            SELL_RULE_COLUMN: "if 분당매도수량 > 분당매수수량:",
        })
    for i in range(n_loss):
        rows.append({
            RETURN_COLUMN: -1.5 - (i % 3) * 0.1,
            MFE_COLUMN: 0.1,
            MAE_COLUMN: -4.5 - (i % 4) * 0.2,
            HOLD_COLUMN: 12 + (i % 3),
            SELL_RULE_COLUMN: "if 수익률 <= -1.0:",
        })
    return rows


# ---------------------------------------------------------------------
# analyze_exits — give-back + MAE depth.
# ---------------------------------------------------------------------
def test_giveback_and_mae_are_flagged(tmp_path):
    csv = _write_csv(tmp_path / "gb.csv", _giveback_rows(n_win=20, n_loss=20))
    r = analyze_exits(csv)

    assert r.status == STATUS_OK
    assert r.trade_count == 40
    assert r.win_count == 20 and r.loss_count == 20

    # give-back: 수익 거래 평균 MFE(~3.15%) >> 실현(~0.85%) → gap이 크다.
    assert r.avg_mfe_winners > 2.5
    assert r.avg_realized_winners < 1.5
    assert r.giveback_gap_winners > 1.5  # 명백한 반납.
    assert r.giveback_eligible == 20     # 모든 수익 거래가 MFE>=1% (익절 기회).

    # MAE depth: 손실 거래가 -4% 이상 깊이 물렸다.
    assert r.avg_mae_losers < -3.0
    assert r.worst_mae_losers <= r.avg_mae_losers

    # 보유시간: 손실 거래가 수익 거래보다 길다.
    assert r.avg_hold_losers > r.avg_hold_winners

    # 매도규칙: 손실 집중 규칙이 '손절' 룰로 지목된다.
    assert r.worst_sell_rule == "if 수익률 <= -1.0:"
    assert len(r.sell_rules) == 2


def test_summarize_exits_mentions_takeprofit_and_stoploss(tmp_path):
    csv = _write_csv(tmp_path / "gb2.csv", _giveback_rows(n_win=20, n_loss=20))
    r = analyze_exits(csv)
    text = summarize_exits(r, LoopConfig())

    assert text  # 비어 있지 않은 매도(SELL)용 가이드.
    assert "매도" in text          # 매도 전략을 겨냥.
    assert "익절" in text          # give-back → 익절 기준 추가.
    assert "손절" in text          # 깊은 MAE → 손절을 조여라.
    assert "반납" in text          # give-back 표현.
    # 시간 청산 신호(손실 거래가 더 오래 보유).
    assert "보유시간" in text or "시간" in text
    # 손실 집중 매도규칙 지목.
    assert "매도규칙" in text


# ---------------------------------------------------------------------
# 엣지 케이스.
# ---------------------------------------------------------------------
def test_zero_trades_is_insufficient(tmp_path):
    path = str(tmp_path / "empty.csv")
    pd.DataFrame(columns=[RETURN_COLUMN, MFE_COLUMN, MAE_COLUMN]).to_csv(
        path, index=False, encoding="utf-8-sig"
    )
    r = analyze_exits(path)
    assert r.status == STATUS_INSUFFICIENT
    assert r.trade_count == 0
    text = summarize_exits(r, LoopConfig())
    assert "완화" in text  # 거래 빈도 먼저 확보하라.


def test_below_min_trades_is_insufficient(tmp_path):
    csv = _write_csv(tmp_path / "few.csv", _giveback_rows(n_win=2, n_loss=3))
    r = analyze_exits(csv)  # 5건 < 기본 min 10.
    assert r.status == STATUS_INSUFFICIENT
    assert r.trade_count == 5
    text = summarize_exits(r, LoopConfig())
    assert text


def test_all_wins_handled_cleanly(tmp_path):
    """전부 수익 → single_class지만 give-back 통계는 채워지고 요약은 안전."""
    rows = _giveback_rows(n_win=15, n_loss=0)
    csv = _write_csv(tmp_path / "allwin.csv", rows)
    r = analyze_exits(csv)
    assert r.status == STATUS_SINGLE_CLASS
    assert r.win_count == 15 and r.loss_count == 0
    # 손실이 없으니 MAE/손실집중규칙은 비어 있어야 한다(0 나눗셈 없이).
    assert r.avg_mae_losers == 0.0
    assert r.worst_sell_rule is None
    # give-back은 여전히 계산된다(수익 거래 존재).
    assert r.giveback_gap_winners > 1.5
    text = summarize_exits(r, LoopConfig())
    assert text  # 예외 없이 가이드 생성.


def test_missing_mfe_column_is_safe(tmp_path):
    """MFE/MAE 컬럼이 없어도 give-back/MAE는 0으로 두고 깨지지 않는다."""
    rows = []
    for i in range(20):
        is_win = i < 10
        rows.append({
            RETURN_COLUMN: 0.5 if is_win else -0.5,
            HOLD_COLUMN: 5,
            SELL_RULE_COLUMN: "if 수익률 >= 0.5:" if is_win else "if 수익률 <= -0.5:",
        })
    csv = _write_csv(tmp_path / "nomfe.csv", rows)
    r = analyze_exits(csv)
    assert r.status == STATUS_OK
    assert r.avg_mfe_winners == 0.0
    assert r.giveback_gap_winners == 0.0
    # 매도규칙 분포는 여전히 동작.
    assert len(r.sell_rules) == 2
    text = summarize_exits(r, LoopConfig())
    assert text


def test_holdout_raises(tmp_path):
    csv = _write_csv(tmp_path / "h.csv", _giveback_rows(n_win=20, n_loss=20))
    with pytest.raises(ValueError):
        analyze_exits(csv, is_holdout=True)


# ---------------------------------------------------------------------
# 실제 최근 소규모 CSV 스모크 (있을 때만) — PROFITABILITY 신호를 실데이터로 출력.
# ---------------------------------------------------------------------
_REAL_CANDIDATES = [
    "stock_bt_AILOOP_run_1779672477_g7_buy_20260525104541.csv",
    "stock_bt_AILOOP_run_1779672477_g13_buy_20260525105452.csv",
]


def _find_real_csv():
    base = os.path.join(PROJECT_ROOT, "backtest", "csv")
    for name in _REAL_CANDIDATES:
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


@pytest.mark.skipif(_find_real_csv() is None, reason="실제 부검 CSV 없음")
def test_real_csv_exit_autopsy_smoke(capsys):
    path = _find_real_csv()
    r = analyze_exits(path)
    assert r.status in (STATUS_OK, STATUS_SINGLE_CLASS)
    text = summarize_exits(r, LoopConfig())
    assert text

    lines = ["\n[REAL CSV EXIT AUTOPSY]",
             f"  trade_count={r.trade_count} win={r.win_count} loss={r.loss_count}",
             f"  giveback_gap(winners)={r.giveback_gap_winners:.4g}%p "
             f"avg_mfe_w={r.avg_mfe_winners:.4g} avg_realized_w={r.avg_realized_winners:.4g}",
             f"  avg_mae_losers={r.avg_mae_losers:.4g}% worst_mae={r.worst_mae_losers:.4g}%",
             f"  hold_win={r.avg_hold_winners:.4g} hold_loss={r.avg_hold_losers:.4g}",
             f"  worst_sell_rule={r.worst_sell_rule!r}",
             "  --- SELL FEEDBACK ---", text]
    blob = "\n".join(lines)
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe = blob.encode(enc, errors="replace").decode(enc, errors="replace")
    with capsys.disabled():
        print(safe)


# ---------------------------------------------------------------------
# 루프 와이어링 — sell 세대는 청산 피드백, buy 세대는 진입 피드백.
# ---------------------------------------------------------------------
def test_loop_routes_exit_feedback_to_sell_and_entry_to_buy(monkeypatch, tmp_path):
    """gen0 백테스트 CSV(give-back+MAE+B_체결강도 변별)를 부검해, gen1의 buy 전략엔
    진입(부검) 피드백이, sell 전략엔 청산(익절/손절) 피드백이 전달되는지 검증한다."""
    from ai_strategy_loop.brain import prompt as P
    from ai_strategy_loop.controller import loop as L
    from ai_strategy_loop.controller.state import LoopState
    from ai_strategy_loop.fitness.score import FitnessResult, GradedResult

    # gen0 CSV: give-back + 깊은 MAE + 진입 변별(B_체결강도)을 한 데이터에 담는다.
    rows = _giveback_rows(n_win=20, n_loss=20)
    for i, row in enumerate(rows):
        is_win = i < 20
        # B_체결강도가 수익/손실을 깨끗이 가른다(진입 부검 신호).
        row["B_체결강도"] = (120.0 + (i % 5)) if is_win else (40.0 + (i % 5))
    gen0_csv = _write_csv(tmp_path / "gen0.csv", rows)

    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")

    # _generate_pair에 도달한 buy/sell 피드백을 세대별로 분리 기록한다.
    captured = {}

    def fake_generate_pair(provider, cfg, rid, gen, fb, history_summary=None,
                           sell_feedback=None):
        captured[gen] = {"buy": fb, "sell": sell_feedback}
        return {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 10,
        }

    monkeypatch.setattr(L, "_generate_pair", fake_generate_pair)
    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, b, s: L.BacktestOutcome(
            True, "success", gen0_csv,
            {"cagr": 1.0, "mdd_pct": 1.0, "trade_count": 40, "total_profit_krw": -100},
            "ok",
        ),
    )
    # 게이트 실패(손익 음수)로 두어 게이트 지시 + 부검이 함께 붙도록 한다.
    monkeypatch.setattr(
        L, "_score_outcome",
        lambda outcome, cfg: (
            FitnessResult(score=0.0, calmar=0.0, uptrend_r2=0.0, gate_passed=False,
                          reason="profit<0", cagr=1.0, mdd=1.0, trade_count=40,
                          total_profit=-100.0),
            GradedResult(graded=0.5, gate_passed=False, composite=0.5,
                         trades_term=1.0, mdd_term=1.0, profit_term=0.0,
                         uptrend_term=0.0, gate_distance="profit<0",
                         cagr=1.0, mdd=1.0, trade_count=40, total_profit=-100.0,
                         uptrend_r2=0.0),
            None,
        ),
    )

    config = LoopConfig(provider="openrouter", max_generations=2,
                        cost_cap_generations=100, cost_cap_tokens=None,
                        autopsy_enabled=True)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    L.run_loop(config, run_id="exitwire", state=st)
    st.close()

    # gen0은 피드백 없음(첫 세대).
    assert captured.get(0) == {"buy": None, "sell": None}

    g1 = captured.get(1)
    assert g1 is not None
    buy_fb, sell_fb = g1["buy"], g1["sell"]
    assert buy_fb and sell_fb

    # BUY 측: 진입 부검(변별 변수)이 들어 있어야 한다.
    assert "B_체결강도" in buy_fb
    assert "부검" in buy_fb
    # BUY 측엔 청산 전용 표현(익절/반납)이 끼지 않아야 한다(라우팅 분리 확인).
    assert "익절" not in buy_fb

    # SELL 측: 청산 부검(익절/손절/반납)이 들어 있어야 한다.
    assert "매도" in sell_fb
    assert ("익절" in sell_fb) or ("손절" in sell_fb)
    assert "반납" in sell_fb or "MFE" in sell_fb
    # SELL 측엔 진입 변별 변수(B_체결강도)가 끼지 않아야 한다.
    assert "B_체결강도" not in sell_fb

    # 둘 다 게이트 지시(손익 음수)를 공유해야 한다.
    assert "손익" in buy_fb and "손익" in sell_fb


# ---------------------------------------------------------------------
# 0거래 낭비 방지 — 프롬프트 directive (로직 게이팅 없음, 텍스트만).
# ---------------------------------------------------------------------
def test_buy_prompt_has_trade_frequency_directive():
    from ai_strategy_loop.brain.prompt import build_messages

    msgs = build_messages("buy", timeframe="min")
    user = msgs[-1]["content"]
    assert "거래 빈도" in user
    assert "0건" in user  # 0건이면 버려진다는 경고.


def test_buy_prompt_reacts_to_zero_trade_feedback():
    from ai_strategy_loop.brain.prompt import build_messages

    fb = "직전 세대 백테스트 실패 원인 = 거래 0건(진입이 한 번도 발생하지 않음)"
    msgs = build_messages("buy", timeframe="min", autopsy_feedback=fb)
    user = msgs[-1]["content"]
    # 0거래 피드백을 보면 진입 조건을 1~2개 단순 필터로 줄이라고 지시한다.
    assert "1~2개" in user or "단순" in user


def test_sell_prompt_has_no_trade_frequency_directive():
    """거래 빈도 directive는 매수(진입)에만 — 매도엔 붙지 않는다."""
    from ai_strategy_loop.brain.prompt import build_messages

    msgs = build_messages("sell", timeframe="min")
    user = msgs[-1]["content"]
    assert "거래 빈도" not in user


def test_loop_autopsy_fn_none_path_routes_no_feedback(monkeypatch, tmp_path):
    """US-005 보존: autopsy_enabled=False면 buy/sell 모두 피드백 None."""
    from ai_strategy_loop.controller import loop as L
    from ai_strategy_loop.controller.state import LoopState
    from ai_strategy_loop.fitness.score import FitnessResult, GradedResult

    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")

    captured = {}

    def fake_generate_pair(provider, cfg, rid, gen, fb, history_summary=None,
                           sell_feedback=None):
        captured[gen] = {"buy": fb, "sell": sell_feedback}
        return {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 10,
        }

    monkeypatch.setattr(L, "_generate_pair", fake_generate_pair)
    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, b, s: L.BacktestOutcome(
            True, "success", "fake.csv",
            {"cagr": 1.0, "mdd_pct": 1.0, "trade_count": 40, "total_profit_krw": 100},
            "ok",
        ),
    )
    monkeypatch.setattr(
        L, "_score_outcome",
        lambda outcome, cfg: (
            FitnessResult(score=1.0, calmar=1.0, uptrend_r2=1.0, gate_passed=True,
                          reason="ok", cagr=1.0, mdd=1.0, trade_count=40,
                          total_profit=100.0),
            GradedResult(graded=2.0, gate_passed=True, composite=1.0,
                         trades_term=1.0, mdd_term=1.0, profit_term=1.0,
                         uptrend_term=1.0, gate_distance="ok (gate passed)",
                         cagr=1.0, mdd=1.0, trade_count=40, total_profit=100.0,
                         uptrend_r2=1.0),
            None,
        ),
    )

    config = LoopConfig(provider="openrouter", max_generations=2,
                        cost_cap_generations=100, cost_cap_tokens=None,
                        autopsy_enabled=False)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="noautopsy2", state=st)
    st.close()

    assert captured.get(0) == {"buy": None, "sell": None}
    assert captured.get(1) == {"buy": None, "sell": None}
    assert summary["generations"] == 2
