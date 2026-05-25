"""US-006 Phase 3 — 부검 분석기 + 다음세대 피드백 단위 테스트 (네트워크 없음).

검증:
  - 합성 CSV에서 한 B_ 컬럼이 수익/손실을 깨끗이 가르면 그 컬럼이 최상위
    변별 변수가 되고 summarize가 그 변수를 방향과 함께 언급한다.
  - 거래 0건/min 미만 → insufficient_trades + summary가 '완화하라'를 말한다.
  - 전부 수익 → single_class.
  - is_holdout=True → ValueError.
  - 실제 204거래 CSV(있으면) 스모크.
  - 루프 와이어링: gen-N 부검 요약이 gen-(N+1) generate_strategy의
    autopsy_feedback 인자로 전달된다. autopsy_fn=None 경로(US-005)도 유지.
"""

import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy import analyze_trades, summarize  # noqa: E402
from ai_strategy_loop.autopsy.analyze import (  # noqa: E402
    STATUS_INSUFFICIENT,
    STATUS_OK,
    STATUS_SINGLE_CLASS,
)
from ai_strategy_loop.config import LoopConfig  # noqa: E402

REAL_CSV = os.path.join(
    PROJECT_ROOT, "backtest", "csv", "stock_bt_AILOOP_min_buy_20260525060100.csv"
)

# 14개 B_ 컬럼 (back_static.py 와 동일).
B_COLS = [
    "B_현재가", "B_등락율", "B_당일거래대금", "B_거래대금증감", "B_체결강도",
    "B_시가총액", "B_회전율", "B_전일동시간비", "B_매수총잔량", "B_매도총잔량",
    "B_시분초", "B_분봉시가", "B_분봉고가", "B_분봉저가",
]


def _write_csv(path, rows):
    """rows(list of dict) → utf-8-sig CSV (실데이터와 동일 인코딩)."""
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)


def _make_rows(n_win, n_loss, separating_col=None):
    """n_win 수익 + n_loss 손실 거래 행 생성.

    separating_col이 주어지면 그 컬럼만 수익(높음)/손실(낮음)으로 깨끗이 가르고,
    나머지 B_ 컬럼은 두 그룹 동일 분포(변별력 0)로 둔다.
    """
    rows = []
    for i in range(n_win + n_loss):
        is_win = i < n_win
        row = {"수익률": (0.5 if is_win else -0.5)}
        for c in B_COLS:
            if c == separating_col:
                # 수익=높은 값(100±), 손실=낮은 값(10±) — 깨끗이 분리.
                row[c] = (100.0 + (i % 5)) if is_win else (10.0 + (i % 5))
            else:
                # 두 그룹 공통 분포 — 약간의 변동만, 변별력 거의 0.
                row[c] = 50.0 + (i % 7)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------
# analyze_trades — status ok / 변별 변수 랭킹.
# ---------------------------------------------------------------------
def test_clean_separator_is_top_discriminator(tmp_path):
    """B_체결강도만 수익/손실을 가르면 그 컬럼이 최상위 변별 변수."""
    csv = _write_csv(
        tmp_path / "clean.csv",
        _make_rows(n_win=20, n_loss=20, separating_col="B_체결강도"),
    )
    result = analyze_trades(csv)

    assert result.status == STATUS_OK
    assert result.trade_count == 40
    assert result.win_count == 20
    assert result.loss_count == 20
    assert result.discriminators, "변별 변수가 비어 있으면 안 된다"

    top = result.discriminators[0]
    assert top.column == "B_체결강도"
    # 수익 거래가 더 높았으므로 std_mean_diff > 0, 효과크기는 커야 한다.
    assert top.std_mean_diff > 0
    assert abs(top.std_mean_diff) > 1.0
    assert top.win_mean > top.loss_mean

    # 다른 컬럼들은 변별력이 훨씬 작아야 한다.
    others = [d for d in result.discriminators if d.column != "B_체결강도"]
    assert all(abs(d.std_mean_diff) < abs(top.std_mean_diff) for d in others)

    # summarize가 그 변수를 방향과 함께 언급해야 한다.
    text = summarize(result, LoopConfig())
    assert "B_체결강도" in text
    assert "체결강도" in text
    assert "높여라" in text  # 손실이 낮았으니 기준을 높이라고 지시.


def test_negative_direction_separator(tmp_path):
    """손실 거래에서 더 큰 컬럼이면 '낮춰라' 지시가 나와야 한다."""
    rows = _make_rows(n_win=15, n_loss=15)
    # B_매수총잔량을 손실에서 높게 만든다(수익은 낮게).
    for i, row in enumerate(rows):
        is_win = i < 15
        row["B_매수총잔량"] = (10.0 + (i % 4)) if is_win else (100.0 + (i % 4))
    csv = _write_csv(tmp_path / "neg.csv", rows)

    result = analyze_trades(csv)
    assert result.status == STATUS_OK
    top = result.discriminators[0]
    assert top.column == "B_매수총잔량"
    assert top.std_mean_diff < 0
    text = summarize(result, LoopConfig())
    assert "B_매수총잔량" in text
    assert "낮춰라" in text


# ---------------------------------------------------------------------
# insufficient_trades (0건 + min 미만).
# ---------------------------------------------------------------------
def test_zero_trades_is_insufficient(tmp_path):
    # 실제 0거래 백테스트 CSV는 헤더만 있고 행이 없다.
    path = str(tmp_path / "empty.csv")
    pd.DataFrame(columns=["수익률"] + B_COLS).to_csv(
        path, index=False, encoding="utf-8-sig"
    )
    result = analyze_trades(path)
    assert result.status == STATUS_INSUFFICIENT
    assert result.trade_count == 0
    text = summarize(result, LoopConfig())
    assert "완화" in text  # 진입 조건을 완화하라.


def test_below_min_trades_is_insufficient(tmp_path):
    csv = _write_csv(
        tmp_path / "few.csv", _make_rows(n_win=2, n_loss=3, separating_col="B_체결강도")
    )
    # 기본 min=10, 거래 5건 < 10 → insufficient.
    result = analyze_trades(csv)
    assert result.status == STATUS_INSUFFICIENT
    assert result.trade_count == 5
    text = summarize(result, LoopConfig())
    assert "5건" in text
    assert "완화" in text


def test_custom_min_trades(tmp_path):
    """min_trades를 낮추면 같은 데이터가 ok로 분석된다."""
    csv = _write_csv(
        tmp_path / "few2.csv", _make_rows(n_win=3, n_loss=3, separating_col="B_체결강도")
    )
    result = analyze_trades(csv, min_trades=4)  # 6건 >= 4 → ok.
    assert result.status == STATUS_OK
    assert result.discriminators[0].column == "B_체결강도"


# ---------------------------------------------------------------------
# single_class (전부 수익).
# ---------------------------------------------------------------------
def test_all_wins_is_single_class(tmp_path):
    csv = _write_csv(tmp_path / "allwin.csv", _make_rows(n_win=15, n_loss=0))
    result = analyze_trades(csv)
    assert result.status == STATUS_SINGLE_CLASS
    assert result.win_count == 15
    assert result.loss_count == 0
    text = summarize(result, LoopConfig())
    assert "변별" in text
    assert "다양성" in text


def test_all_losses_is_single_class(tmp_path):
    csv = _write_csv(tmp_path / "allloss.csv", _make_rows(n_win=0, n_loss=15))
    result = analyze_trades(csv)
    assert result.status == STATUS_SINGLE_CLASS
    assert result.loss_count == 15


# ---------------------------------------------------------------------
# is_holdout 가드.
# ---------------------------------------------------------------------
def test_holdout_raises(tmp_path):
    csv = _write_csv(
        tmp_path / "h.csv", _make_rows(n_win=20, n_loss=20, separating_col="B_체결강도")
    )
    with pytest.raises(ValueError):
        analyze_trades(csv, is_holdout=True)


# ---------------------------------------------------------------------
# 실제 204거래 CSV 스모크 (있을 때만).
# ---------------------------------------------------------------------
@pytest.mark.skipif(not os.path.exists(REAL_CSV), reason="실제 부검 CSV 없음")
def test_real_csv_smoke(capsys):
    result = analyze_trades(REAL_CSV)
    assert result.status == STATUS_OK
    assert result.trade_count == 204
    assert result.win_count + result.loss_count == 204
    assert len(result.discriminators) >= 3
    text = summarize(result, LoopConfig())
    assert text  # 비어 있지 않은 NL 피드백.

    # 검증 가시성: 실데이터 부검 결과를 출력 (pytest -s 로 확인 가능).
    # Windows 콘솔(cp949) 인코딩 한계로 깨지는 글자가 있어도 테스트가 죽지
    # 않도록 인코딩-세이프하게 출력한다.
    lines = ["\n[REAL CSV AUTOPSY]",
             f"  trade_count={result.trade_count} "
             f"win={result.win_count} loss={result.loss_count}"]
    for d in result.discriminators[:3]:
        lines.append(f"  {d.column}: win_mean={d.win_mean:.4g} "
                     f"loss_mean={d.loss_mean:.4g} smd={d.std_mean_diff:+.4f}")
    lines.append("  --- SUMMARY ---")
    lines.append(text)
    blob = "\n".join(lines)
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe = blob.encode(enc, errors="replace").decode(enc, errors="replace")
    with capsys.disabled():
        print(safe)


# ---------------------------------------------------------------------
# 루프 와이어링 — gen-N 부검 요약이 gen-(N+1) 프롬프트에 전달된다.
# ---------------------------------------------------------------------
def test_loop_feeds_autopsy_summary_into_next_generation(monkeypatch, tmp_path):
    """MOCK provider + stub 백테스트로 gen0의 부검 요약이 gen1 generate_strategy의
    autopsy_feedback 인자로 들어가는지 검증한다 (네트워크/실백테스트 없음)."""
    from ai_strategy_loop.controller import loop as L
    from ai_strategy_loop.controller.state import LoopState
    from ai_strategy_loop.fitness.score import FitnessResult, GradedResult

    # gen0이 분석할 CSV: B_체결강도가 수익/손실을 가르는 합성 데이터.
    gen0_csv = _write_csv(
        tmp_path / "gen0.csv",
        _make_rows(n_win=20, n_loss=20, separating_col="B_체결강도"),
    )

    # provider/엔진/strategy-head 무력화.
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")

    # _generate_pair가 받은 autopsy_feedback(fb)을 세대별로 기록 — 이게 곧
    # generate_strategy(autopsy_feedback=fb)로 흘러가는 값이다.
    captured = {}

    def fake_generate_pair(provider, cfg, rid, gen, fb, history_summary=None):
        captured[gen] = fb
        return {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 10,
        }

    monkeypatch.setattr(L, "_generate_pair", fake_generate_pair)

    # 백테스트는 항상 gen0_csv를 반환(성공).
    monkeypatch.setattr(
        L, "run_backtest_for",
        lambda cfg, b, s: L.BacktestOutcome(
            True, "success", gen0_csv,
            {"cagr": 1.0, "mdd_pct": 1.0, "trade_count": 40, "total_profit_krw": 100},
            "ok",
        ),
    )
    # fitness는 결정론적으로 stub (CSV equity 로드 회피). (fit, graded, err) 3-tuple.
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
                        autopsy_enabled=True)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    L.run_loop(config, run_id="wirerun", state=st)
    st.close()

    # gen0은 피드백 없음(첫 세대), gen1은 gen0 부검 요약을 받아야 한다.
    assert captured.get(0) is None
    fb1 = captured.get(1)
    assert fb1 is not None and isinstance(fb1, str) and fb1
    # gen0 CSV 부검의 최상위 변별 변수(B_체결강도)가 gen1 피드백에 들어 있어야 한다.
    assert "B_체결강도" in fb1
    assert "부검" in fb1


def test_loop_autopsy_fn_none_path_still_works(monkeypatch, tmp_path):
    """US-005 보존: autopsy_enabled=False면 부검 피드백 없이 None 경로로 돈다."""
    from ai_strategy_loop.controller import loop as L
    from ai_strategy_loop.controller.state import LoopState
    from ai_strategy_loop.fitness.score import FitnessResult, GradedResult

    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")

    captured = {}

    def fake_generate_pair(provider, cfg, rid, gen, fb, history_summary=None):
        captured[gen] = fb
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

    # autopsy_enabled=False → 기본 부검 훅 비활성. autopsy_fn도 안 넘김.
    config = LoopConfig(provider="openrouter", max_generations=2,
                        cost_cap_generations=100, cost_cap_tokens=None,
                        autopsy_enabled=False)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    summary = L.run_loop(config, run_id="noautopsy", state=st)
    st.close()

    # 모든 세대가 피드백 None (US-005 동작과 동일).
    assert captured.get(0) is None
    assert captured.get(1) is None
    assert summary["generations"] == 2
