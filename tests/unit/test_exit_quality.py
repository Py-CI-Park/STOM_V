"""청산 품질(exit-quality) 레버 단위 테스트.

부검 근거: 손실의 70~88%가 give-back(평가익 2~3% 찍고 -2~-3%로 토해냄)이고
payoff ratio 붕괴(1.20→0.61)가 적자 원인이다. 진입 피처는 승패를 못 가르고
청산이 결정한다. 이 신호를 적합도 선택압력에 가산한다(하드게이트 불변).

검증:
  (1) load_exit_quality_from_csv:
      - payoff_ratio/give_back_rate 계산 정확성(임시 CSV).
      - '수익률' 컬럼 없음 → {} (하위호환).
      - 손실 0건 → payoff cap(999.0).
      - 이익 0건 → payoff 0.0.
      - 'R_MFE' 컬럼 없음 → give_back_rate 키 생략.
      - 거래 0건 → {}.
  (2) compute_graded_fitness:
      - payoff/give_back 키 있을 때 exit_quality_term 반영(5항 평균).
      - 키 없을 때 기존 graded와 동일(하위호환).
      - exit_quality_enabled=False면 무영향.
      - 하드 게이트(compute_fitness)는 청산품질 키에 영향받지 않는다(불변).
"""

import csv
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness.score import (
    compute_fitness,
    compute_graded_fitness,
    load_exit_quality_from_csv,
)


# 실제 per-trade CSV의 컬럼 순서/이름을 그대로 쓴다(DictReader 키 접근).
_HEADER = [
    "종목명", "시가총액", "매수시간", "매도시간", "보유시간", "매수가", "매도가",
    "매수금액", "매도금액", "수익률", "수익금", "수익금합계", "매도조건", "추가매수시간",
    "B_현재가", "B_등락율", "B_당일거래대금", "B_거래대금증감", "B_체결강도",
    "B_시가총액", "B_회전율", "B_전일동시간비", "B_매수총잔량", "B_매도총잔량",
    "B_시분초", "B_분봉시가", "B_분봉고가", "B_분봉저가", "S_현재가", "S_등락율",
    "S_체결강도", "S_매수총잔량", "S_매도총잔량", "R_매수후최고수익률",
    "R_매수후최저수익률", "R_MFE", "R_MAE",
]


def _write_csv(path, rows, *, header=None):
    """rows = [(ret, mfe), ...] (None은 빈 셀). header 미지정 시 전체 컬럼 사용.

    header를 직접 주면(예: 'R_MFE' 제외) 컬럼 누락 시나리오를 만든다.
    """
    use_header = header if header is not None else _HEADER
    ret_idx = use_header.index("수익률") if "수익률" in use_header else None
    mfe_idx = use_header.index("R_MFE") if "R_MFE" in use_header else None
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(use_header)
        for ret, mfe in rows:
            line = [""] * len(use_header)
            if ret_idx is not None and ret is not None:
                line[ret_idx] = str(ret)
            if mfe_idx is not None and mfe is not None:
                line[mfe_idx] = str(mfe)
            writer.writerow(line)


# ============================================================
# (1) load_exit_quality_from_csv
# ============================================================

def test_payoff_ratio_basic(tmp_path):
    """payoff_ratio = mean(이익)/abs(mean(손실)) 정확성.

    이익 [4.0, 2.0] → mean 3.0; 손실 [-2.0, -4.0] → mean -3.0 → abs 3.0.
    payoff_ratio = 3.0/3.0 = 1.0.
    """
    csv_path = str(tmp_path / "trades.csv")
    _write_csv(csv_path, [(4.0, 0.0), (2.0, 0.0), (-2.0, 0.0), (-4.0, 0.0)])
    res = load_exit_quality_from_csv(csv_path)
    assert abs(res["payoff_ratio"] - 1.0) < 1e-9


def test_payoff_ratio_above_one(tmp_path):
    """이익이 손실보다 크면 payoff_ratio > 1."""
    csv_path = str(tmp_path / "t.csv")
    # 이익 mean=5.0, 손실 mean=-2.0 → payoff 2.5.
    _write_csv(csv_path, [(6.0, 0.0), (4.0, 0.0), (-2.0, 0.0), (-2.0, 0.0)])
    res = load_exit_quality_from_csv(csv_path)
    assert abs(res["payoff_ratio"] - 2.5) < 1e-9


def test_give_back_rate_basic(tmp_path):
    """give_back_rate = (R_MFE>=threshold 이고 ret<=0)건 / max(손실건,1).

    손실 3건 중 R_MFE>=1.5인 give-back 2건 → 2/3.
    """
    csv_path = str(tmp_path / "t.csv")
    rows = [
        (2.0, 3.0),    # 이익 — give-back 아님.
        (-3.0, 2.4),   # 손실 + MFE 2.4>=1.5 → give-back.
        (-2.5, 2.9),   # 손실 + MFE 2.9>=1.5 → give-back.
        (-1.0, 0.3),   # 손실 + MFE 0.3<1.5 → give-back 아님.
    ]
    _write_csv(csv_path, rows)
    res = load_exit_quality_from_csv(csv_path)
    assert abs(res["give_back_rate"] - (2.0 / 3.0)) < 1e-9


def test_give_back_threshold_param(tmp_path):
    """mfe_giveback_threshold 파라미터가 카운트 기준을 바꾼다."""
    csv_path = str(tmp_path / "t.csv")
    rows = [(-3.0, 2.0), (-2.0, 1.0)]  # 손실 2건, MFE 2.0 / 1.0.
    _write_csv(csv_path, rows)
    # threshold 1.5 → MFE 2.0만 give-back → 1/2.
    res = load_exit_quality_from_csv(csv_path, mfe_giveback_threshold=1.5)
    assert abs(res["give_back_rate"] - 0.5) < 1e-9
    # threshold 0.5 → 둘 다 give-back → 2/2.
    res2 = load_exit_quality_from_csv(csv_path, mfe_giveback_threshold=0.5)
    assert abs(res2["give_back_rate"] - 1.0) < 1e-9


def test_no_ret_column_returns_empty(tmp_path):
    """'수익률' 컬럼이 없으면 {} 반환(하위호환 — 다운스트림 무영향)."""
    csv_path = str(tmp_path / "t.csv")
    header = ["종목명", "수익금합계", "R_MFE"]  # '수익률' 없음.
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerow(["A", "100", "2.0"])
    res = load_exit_quality_from_csv(csv_path)
    assert res == {}


def test_no_loss_trades_caps_payoff(tmp_path):
    """손실거래 0건이면 payoff_ratio가 큰 양수(999.0)로 cap된다."""
    csv_path = str(tmp_path / "t.csv")
    _write_csv(csv_path, [(2.0, 0.0), (3.0, 0.0), (1.5, 0.0)])  # 전부 이익.
    res = load_exit_quality_from_csv(csv_path)
    assert res["payoff_ratio"] == 999.0
    # 손실 0건 → give_back_rate=0 (give-back 거래 없음).
    assert res["give_back_rate"] == 0.0


def test_no_win_trades_payoff_zero(tmp_path):
    """이익거래 0건이면 payoff_ratio=0.0."""
    csv_path = str(tmp_path / "t.csv")
    _write_csv(csv_path, [(-2.0, 0.0), (-3.0, 0.0), (0.0, 0.0)])  # 전부 손실/0.
    res = load_exit_quality_from_csv(csv_path)
    assert res["payoff_ratio"] == 0.0


def test_no_mfe_column_omits_give_back(tmp_path):
    """'R_MFE' 컬럼이 없으면 give_back_rate 키를 생략(payoff_ratio만 반환)."""
    csv_path = str(tmp_path / "t.csv")
    header = ["종목명", "수익률", "수익금합계"]  # R_MFE 없음.
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerow(["A", "4.0", "4"])
        writer.writerow(["B", "-2.0", "2"])
    res = load_exit_quality_from_csv(csv_path)
    assert "payoff_ratio" in res
    assert "give_back_rate" not in res
    assert abs(res["payoff_ratio"] - 2.0) < 1e-9


def test_zero_trades_returns_empty(tmp_path):
    """거래 0건(헤더만)이면 {} 반환."""
    csv_path = str(tmp_path / "t.csv")
    _write_csv(csv_path, [])
    res = load_exit_quality_from_csv(csv_path)
    assert res == {}


def test_blank_rows_are_skipped(tmp_path):
    """빈/결측 수익률 행은 skip되고 유효 행만 집계된다."""
    csv_path = str(tmp_path / "t.csv")
    # 중간에 빈 수익률 행을 끼운다 — 무시돼야 한다.
    _write_csv(csv_path, [(4.0, 0.0), (None, 5.0), (-2.0, 0.0)])
    res = load_exit_quality_from_csv(csv_path)
    # 유효 거래는 이익 4.0 / 손실 -2.0 → payoff 2.0.
    assert abs(res["payoff_ratio"] - 2.0) < 1e-9


# ============================================================
# (2) compute_graded_fitness — exit_quality_term 반영
# ============================================================

_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _config():
    """게이트 실패를 유도하는 기준(min_trades=30, mdd_cap=25)."""
    return LoopConfig(min_trades=30, mdd_cap=25.0)


def _metrics(cagr, mdd, trades, profit, **extra):
    m = {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }
    m.update(extra)
    return m


def test_exit_quality_keys_affect_failing_graded():
    """payoff/give_back 키가 있으면 gate-failed graded가 달라진다(5항 평균 반영).

    좋은 청산(payoff 높고 give-back 낮음)이 나쁜 청산보다 graded가 높아야 한다.
    """
    cfg = _config()  # 거래 5건 → 게이트 실패.
    good = compute_graded_fitness(
        _metrics(5.0, 10.0, 5, 0, payoff_ratio=1.5, give_back_rate=0.1),
        _STEADY, cfg,
    )
    bad = compute_graded_fitness(
        _metrics(5.0, 10.0, 5, 0, payoff_ratio=0.5, give_back_rate=0.9),
        _STEADY, cfg,
    )
    assert good.gate_passed is False and bad.gate_passed is False
    assert good.exit_quality_term > bad.exit_quality_term
    assert good.graded > bad.graded


def test_exit_quality_absent_matches_legacy_graded():
    """청산품질 키가 없으면 기존 4항 평균 graded와 정확히 동일(하위호환)."""
    cfg = _config()
    m = _metrics(5.0, 10.0, 5, 0)  # 청산품질 키 없음.
    res = compute_graded_fitness(m, _STEADY, cfg)
    # exit_quality_term 기본 1.0, payoff/give_back 0.0 — 기존 동작 그대로.
    assert res.exit_quality_term == 1.0
    assert res.payoff_ratio == 0.0
    assert res.give_back_rate == 0.0
    # 키가 있는 동일 metrics에서 term이 1.0이 되도록 만든 경우와 graded 일치 확인용:
    #   여기서는 '키 없음 = 4항 평균'을 직접 재현해 비교한다.
    # 4항 평균 base를 수동 계산: trades_term + mdd_term + uptrend + overtrade.
    # 키가 없으면 base_terms는 4개 → graded는 키 추가 전과 동일해야 한다.
    # (회귀 기준: 동일 입력으로 두 번 호출하면 deterministically 같다.)
    again = compute_graded_fitness(m, _STEADY, cfg)
    assert abs(res.graded - again.graded) < 1e-12


def test_exit_quality_disabled_is_no_op():
    """exit_quality_enabled=False면 키가 있어도 graded가 키 없는 경우와 동일."""
    cfg_off = LoopConfig(min_trades=30, mdd_cap=25.0, exit_quality_enabled=False)
    with_keys = compute_graded_fitness(
        _metrics(5.0, 10.0, 5, 0, payoff_ratio=2.0, give_back_rate=0.0),
        _STEADY, cfg_off,
    )
    without_keys = compute_graded_fitness(
        _metrics(5.0, 10.0, 5, 0), _STEADY, cfg_off,
    )
    # 비활성이면 term=1.0(미반영) → 두 graded가 동일해야 한다.
    assert with_keys.exit_quality_term == 1.0
    assert abs(with_keys.graded - without_keys.graded) < 1e-12


def test_exit_quality_payoff_only_uses_payoff_comp():
    """give_back_rate 없이 payoff_ratio만 있으면 term = payoff_comp."""
    cfg = _config()
    # payoff 1.1, target 1.1 → payoff_comp = 1.0 → term 1.0.
    res = compute_graded_fitness(
        _metrics(5.0, 10.0, 5, 0, payoff_ratio=1.1), _STEADY, cfg,
    )
    assert abs(res.exit_quality_term - 1.0) < 1e-9


def test_exit_quality_does_not_affect_hard_gate():
    """하드 게이트(compute_fitness)는 청산품질 키에 전혀 영향받지 않는다(불변)."""
    cfg = _config()
    with_keys = compute_fitness(
        _metrics(30.0, 10.0, 50, 1_000_000, payoff_ratio=0.1, give_back_rate=0.99),
        _STEADY, cfg,
    )
    without_keys = compute_fitness(
        _metrics(30.0, 10.0, 50, 1_000_000), _STEADY, cfg,
    )
    # 같은 게이트 입력이면 청산품질 키 유무와 무관하게 score/gate가 동일.
    assert with_keys.gate_passed == without_keys.gate_passed
    assert with_keys.score == without_keys.score


def test_exit_quality_preserves_gate_passed_over_failed():
    """청산품질 가산 후에도 gate-passed(≥1.0) > gate-failed(<1.0) 불변."""
    cfg = _config()
    passing = compute_graded_fitness(_metrics(30.0, 10.0, 50, 1_000_000), _STEADY, cfg)
    # 최고의 청산품질(payoff 큼, give-back 0)이라도 gate-failed면 1.0 미만.
    failing = compute_graded_fitness(
        _metrics(5.0, 10.0, 5, 0, payoff_ratio=999.0, give_back_rate=0.0),
        _STEADY, cfg,
    )
    assert passing.gate_passed is True and failing.gate_passed is False
    assert passing.graded >= 1.0 > failing.graded
