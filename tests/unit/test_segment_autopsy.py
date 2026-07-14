"""P1 세그먼트 강화 부검 단위 테스트 (네트워크/실백테스트 없음).

검증:
  - 합성 CSV에서 특정 시총밴드·시간대에 손실이 몰리면 그 세그먼트가 손실 집중으로
    잡히고 summarize_segments가 그 세그먼트를 구체 수치와 함께 언급한다.
  - 구체 임계값(분위수/t검정 경계)이 산출되고 NL에 포함된다.
  - 거래 0건/min 미만 → insufficient_trades + 세그먼트 비어 있음(무예외).
  - is_holdout=True → ValueError (analyze.py와 동일 계약).
  - to_page_data가 JSON-직렬화 가능한 작은 dict를 낸다(LIVE 패널용).
  - 토큰 회귀 게이트: cap_feedback이 절대 문자 상한을 적용한다.
  - 루프 와이어링: 세그먼트 피드백이 진입/청산 피드백에 합성되고, page_data["autopsy"]가
    발행된다.
"""

import json
import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy import (  # noqa: E402
    analyze_segments,
    cap_feedback,
    summarize_segments,
    to_page_data,
)
from ai_strategy_loop.autopsy.segment import (  # noqa: E402
    SEGMENT_CARD_SECTION_SCHEMA_V3,
    to_card_section_v3,
)

from ai_strategy_loop.autopsy.analyze import (  # noqa: E402
    STATUS_INSUFFICIENT,
    STATUS_OK,
)
from ai_strategy_loop.config import LoopConfig  # noqa: E402

B_COLS = [
    "B_현재가", "B_등락율", "B_당일거래대금", "B_거래대금증감", "B_체결강도",
    "B_시가총액", "B_회전율", "B_전일동시간비", "B_매수총잔량", "B_매도총잔량",
    "B_시분초", "B_분봉시가", "B_분봉고가", "B_분봉저가",
]


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)


def _make_segmented_rows():
    """두 세그먼트로 손익이 갈리는 합성 데이터.

    - 장초반(09:10:00) + 소형주(시총 1500억) → 전부 손실(-1.0), MAE 깊음.
    - 오전(10:00:00) + 대형주(시총 12000억) → 전부 수익(+1.0).
    체결강도도 손실 그룹은 낮고(80), 수익 그룹은 높게(140) 둬 임계값이 잡히게 한다.
    각 그룹 25건 = 총 50건(세그먼트 min 표본 충족).
    """
    rows = []
    for i in range(50):
        loss = i < 25
        row = {
            "수익률": -1.0 if loss else 1.0,
            "수익금": -1000.0 if loss else 1000.0,
            "R_MFE": 0.3 if loss else 2.0,
            "R_MAE": -2.5 if loss else -0.2,
            "보유시간": 30 if loss else 10,
            "매도조건": "손절" if loss else "익절",
            "매수시간": 202501010910 if loss else 202501011000,
        }
        for c in B_COLS:
            if c == "B_시분초":
                row[c] = 91000 if loss else 100000
            elif c == "B_시가총액":
                row[c] = 1500 if loss else 12000
            elif c == "B_체결강도":
                row[c] = 80.0 + (i % 5) if loss else 140.0 + (i % 5)
            else:
                row[c] = 50.0 + (i % 7)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------
# analyze_segments — 세그먼트 + 임계값 산출.
# ---------------------------------------------------------------------
def test_segments_detect_loss_concentration(tmp_path):
    csv = _write_csv(tmp_path / "seg.csv", _make_segmented_rows())
    result = analyze_segments(csv, min_trades=10)

    assert result.status == STATUS_OK
    assert result.trade_count == 50
    # 시총 밴드 / 시간대 세그먼트가 둘 다 잡혀야 한다.
    assert result.market_cap_segments, "시총 세그먼트가 비면 안 된다"
    assert result.time_segments, "시간대 세그먼트가 비면 안 된다"

    # 손실 집중 세그먼트(소형, 장초반)는 return_diff가 음수여야 한다.
    worst_mcap = min(result.market_cap_segments, key=lambda s: s.return_diff)
    assert worst_mcap.return_diff < 0
    assert worst_mcap.win_rate == 0.0  # 소형=전부 손실.

    worst_time = min(result.time_segments, key=lambda s: s.return_diff)
    assert worst_time.return_diff < 0
    assert worst_time.win_rate == 0.0


def test_segments_produce_concrete_thresholds(tmp_path):
    csv = _write_csv(tmp_path / "seg2.csv", _make_segmented_rows())
    result = analyze_segments(csv, min_trades=10)
    assert result.thresholds, "구체 임계값이 비면 안 된다"
    # 임계값은 경계값을 가져야 한다(분위수 또는 t검정 중앙값).
    for t in result.thresholds:
        has_bound = (t.threshold is not None
                     or t.lower_bound is not None
                     or t.upper_bound is not None)
        assert has_bound, f"임계값에 경계가 없다: {t}"
        assert t.source in ("quantile", "ttest")


def test_summarize_segments_mentions_segment_and_threshold(tmp_path):
    csv = _write_csv(tmp_path / "seg3.csv", _make_segmented_rows())
    result = analyze_segments(csv, min_trades=10)
    text = summarize_segments(result, LoopConfig())
    assert text, "세그먼트 NL 피드백이 비면 안 된다"
    assert "세그먼트 부검" in text
    # 손실 집중 세그먼트 라벨(소형 또는 장초반)이 언급돼야 한다.
    assert ("소형" in text) or ("장초반" in text)
    # 손실 집중 구간(구체 임계값) framing이 들어가야 한다.
    assert ("손실 집중" in text)


# ---------------------------------------------------------------------
# insufficient / holdout 계약.
# ---------------------------------------------------------------------
def test_zero_trades_is_insufficient(tmp_path):
    path = str(tmp_path / "empty.csv")
    pd.DataFrame(columns=["수익률"] + B_COLS).to_csv(
        path, index=False, encoding="utf-8-sig"
    )
    result = analyze_segments(path, min_trades=10)
    assert result.status == STATUS_INSUFFICIENT
    assert result.trade_count == 0
    assert result.market_cap_segments == []
    # insufficient면 NL 요약은 빈 문자열(피드백 토큰 절약).
    assert summarize_segments(result, LoopConfig()) == ""


def test_below_min_trades_is_insufficient(tmp_path):
    csv = _write_csv(tmp_path / "few.csv", _make_segmented_rows()[:6])
    result = analyze_segments(csv, min_trades=10)
    assert result.status == STATUS_INSUFFICIENT
    assert result.trade_count == 6


def test_missing_return_column_is_insufficient(tmp_path):
    csv = _write_csv(tmp_path / "noret.csv", [{"B_체결강도": 100} for _ in range(20)])
    result = analyze_segments(csv, min_trades=10)
    assert result.status == STATUS_INSUFFICIENT


def test_holdout_raises(tmp_path):
    csv = _write_csv(tmp_path / "h.csv", _make_segmented_rows())
    with pytest.raises(ValueError):
        analyze_segments(csv, is_holdout=True)


# ---------------------------------------------------------------------
# to_page_data — LIVE 패널용 직렬화.
# ---------------------------------------------------------------------
def test_to_page_data_is_json_serializable(tmp_path):
    csv = _write_csv(tmp_path / "pd.csv", _make_segmented_rows())
    result = analyze_segments(csv, min_trades=10)
    page = to_page_data(result)
    # JSON 직렬화 가능해야 한다(대시보드 current_state.json에 실림).
    blob = json.dumps(page, ensure_ascii=False)
    assert blob
    assert page["status"] == STATUS_OK
    assert page["trade_count"] == 50
    assert isinstance(page["market_cap_segments"], list)
    assert isinstance(page["thresholds"], list)
    # 상위 top개만(작게 유지) — 세그먼트 행이 과도하게 많지 않아야 한다.
    assert len(page["market_cap_segments"]) <= 3
    assert len(page["thresholds"]) <= 3


# ---------------------------------------------------------------------
# 토큰 회귀 게이트.
# ---------------------------------------------------------------------
def test_cap_feedback_enforces_char_limit():
    long_text = "가" * 5000
    capped = cap_feedback(long_text, max_chars=1400)
    assert len(capped) <= 1400
    assert "상한 적용" in capped


def test_cap_feedback_passthrough_short():
    short = "짧은 피드백"
    assert cap_feedback(short, max_chars=1400) == short
    assert cap_feedback(None) is None
    assert cap_feedback("") == ""


def test_segment_feedback_within_token_gate(tmp_path):
    """세그먼트 강화 피드백이 합성돼도 절대 문자 상한 이내여야 한다(토큰 회귀 게이트)."""
    csv = _write_csv(tmp_path / "gate.csv", _make_segmented_rows())
    result = analyze_segments(csv, min_trades=10)
    seg_fb = summarize_segments(result, LoopConfig())
    # 세그먼트 피드백 자체는 합리적으로 짧아야 한다(상위 N개만).
    assert len(seg_fb) < 1400


# ---------------------------------------------------------------------
# 루프 와이어링 — 세그먼트 피드백 합성 + page_data["autopsy"] 발행.
# ---------------------------------------------------------------------
def test_loop_feeds_segment_autopsy_and_publishes_page_data(monkeypatch, tmp_path):
    """gen0의 세그먼트 부검이 gen1 피드백에 합성되고, page_data["autopsy"]가
    current_state.json에 발행되는지 검증한다(네트워크/실백테 없음)."""
    from ai_strategy_loop.controller import loop as L
    from ai_strategy_loop.controller.state import LoopState
    from ai_strategy_loop.fitness.score import FitnessResult, GradedResult

    gen0_csv = _write_csv(tmp_path / "gen0.csv", _make_segmented_rows())

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
            True, "success", gen0_csv,
            {"cagr": 1.0, "mdd_pct": 1.0, "trade_count": 50, "total_profit_krw": 100},
            "ok",
        ),
    )
    monkeypatch.setattr(
        L, "_score_outcome",
        lambda outcome, cfg: (
            FitnessResult(score=1.0, calmar=1.0, uptrend_r2=1.0, gate_passed=True,
                          reason="ok", cagr=1.0, mdd=1.0, trade_count=50,
                          total_profit=100.0),
            GradedResult(graded=2.0, gate_passed=True, composite=1.0,
                         trades_term=1.0, mdd_term=1.0, profit_term=1.0,
                         uptrend_term=1.0, gate_distance="ok (gate passed)",
                         cagr=1.0, mdd=1.0, trade_count=50, total_profit=100.0,
                         uptrend_r2=1.0),
            None,
        ),
    )

    # _publish_live가 받은 page_data를 가로채 발행 여부 검증.
    published = []
    real_publish = L._publish_live

    def spy_publish(*args, **kwargs):
        published.append(kwargs.get("page_data"))
        return real_publish(*args, **kwargs)

    monkeypatch.setattr(L, "_publish_live", spy_publish)

    config = LoopConfig(provider="openrouter", max_generations=2,
                        bt_engine_mode="cold",
                        cost_cap_generations=100, cost_cap_tokens=None,
                        autopsy_enabled=True)
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
    L.run_loop(config, run_id="segrun", state=st)
    st.close()

    # gen1 buy 피드백에 세그먼트 부검이 합성돼 있어야 한다.
    fb1 = captured.get(1)
    assert fb1 is not None
    assert fb1["buy"] and "세그먼트 부검" in fb1["buy"]
    # 매도 피드백에도 세그먼트가 합성된다.
    assert fb1["sell"] and "세그먼트 부검" in fb1["sell"]

    # generation_done 발행 중 하나에 page_data["autopsy"]가 실려야 한다.
    autopsy_payloads = [p for p in published if p and "autopsy" in p]
    assert autopsy_payloads, "page_data['autopsy']가 한 번도 발행되지 않았다"
    assert autopsy_payloads[0]["autopsy"]["trade_count"] == 50


# ---------------------------------------------------------------------------
# DR-05 — segment.to_card_section_v3: AnalysisCardV3 서술 섹션 어댑터.
# ---------------------------------------------------------------------------


def test_to_card_section_v3_wraps_to_page_data_with_schema_label(tmp_path):
    csv = _write_csv(tmp_path / "seg_v3.csv", _make_segmented_rows())
    result = analyze_segments(csv, min_trades=10)
    page = to_page_data(result)
    section = to_card_section_v3(result)

    assert section["schema"] == SEGMENT_CARD_SECTION_SCHEMA_V3
    # 재구현이 아니라 to_page_data 를 그대로 재사용해야 한다 — schema 제외 나머지 동일.
    for key, value in page.items():
        assert section[key] == value


def test_to_card_section_v3_is_json_serializable(tmp_path):
    csv = _write_csv(tmp_path / "seg_v3b.csv", _make_segmented_rows())
    result = analyze_segments(csv, min_trades=10)
    section = to_card_section_v3(result)
    assert json.dumps(section, ensure_ascii=False)
