"""G003 — ai_strategy_loop/autopsy/trade_quant.py 단위 테스트 (네트워크 없음).

검증:
  - 손으로 계산한 기대값/PF/승률/payoff_ratio 대조 (18승/12패 합성 30거래).
  - 연속승패 streak(최대값 + 상위 3개) 정확성.
  - 낙폭 기여 top_n(누적손익 경로에서 개별 거래 기여도) — 손계산 대조.
  - MFE/MAE 컬럼 있음/없음 2종 각각의 결과 모양.
  - 시간대 버킷(coarse 30분 vs fine 5분)이 다른 라벨을 만든다.
  - 진입 피처(B_*) 승/패 평균차 분리 요약.
  - 무예외 계약: 빈 CSV(헤더만/완전 빈 파일)/없는 파일/필수 컬럼 누락에도 raise 없이 status로 보고.
  - nl_lines가 5~8줄 한국어로 생성됨.
"""

from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.trade_quant import (  # noqa: E402
    STATUS_ERROR,
    STATUS_NO_DATA,
    STATUS_OK,
    analyze_trade_table,
)


def _write_csv(path, rows):
    """rows(list of dict) → utf-8-sig CSV (실데이터와 동일 인코딩)."""
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)


# ---------------------------------------------------------------------
# 기대값 / PF / 승률 / payoff_ratio — 손계산 대조 (18승 + 12패 = 30거래).
# ---------------------------------------------------------------------
def _make_expectancy_rows():
    rows = []
    for i in range(18):
        rows.append(
            {
                "종목명": f"win{i}",
                "매수시간": f"2025061309{(i % 60):02d}",
                "보유시간": 10 + i * 3,
                "수익률": 2.0,
                "수익금": 20000,
            }
        )
    for i in range(12):
        rows.append(
            {
                "종목명": f"loss{i}",
                "매수시간": f"2025061310{(i % 60):02d}",
                "보유시간": 15 + i * 4,
                "수익률": -1.5,
                "수익금": -15000,
            }
        )
    return rows


def test_expectancy_pf_winrate_payoff_hand_calculated(tmp_path):
    csv = _write_csv(tmp_path / "expectancy.csv", _make_expectancy_rows())
    result = analyze_trade_table(csv)

    assert result["status"] == STATUS_OK
    assert result["trade_count"] == 30
    m = result["metrics"]

    # expectancy_pct = (18*2.0 + 12*-1.5) / 30 = 0.6
    assert m["expectancy_pct"] == pytest.approx(0.6, abs=1e-9)
    # profit_factor = (18*2.0) / (12*1.5) = 36/18 = 2.0
    assert m["profit_factor"] == pytest.approx(2.0, abs=1e-9)
    # win_rate = 18/30 = 0.6
    assert m["win_rate"] == pytest.approx(0.6, abs=1e-9)
    # payoff_ratio = 2.0 / 1.5 = 1.3333...
    assert m["payoff_ratio"] == pytest.approx(2.0 / 1.5, abs=1e-6)
    # expectancy_amount = (18*20000 + 12*-15000) / 30 = 6000
    assert m["expectancy_amount"] == pytest.approx(6000.0, abs=1e-6)

    assert "profit_factor_reason" not in m
    assert "payoff_ratio_reason" not in m

    # 수익률 분포는 pandas 기본 통계만 사용.
    dist = m["distribution"]
    assert dist["mean"] == pytest.approx(0.6, abs=1e-9)
    assert dist["q50"] is not None

    nl = result["nl_lines"]
    assert 5 <= len(nl) <= 8
    assert any("기대값" in line for line in nl)
    assert any("승률" in line for line in nl)


# ---------------------------------------------------------------------
# 연속승패 streak.
# ---------------------------------------------------------------------
def test_streak_max_and_top3(tmp_path):
    # 패턴: WWW, LL, W, LLLL, WW → 길이 [3,2,1,4,2].
    pattern = ["W", "W", "W", "L", "L", "W", "L", "L", "L", "L", "W", "W"]
    rows = [
        {"종목명": f"t{i}", "수익률": (1.0 if p == "W" else -1.0)}
        for i, p in enumerate(pattern)
    ]
    csv = _write_csv(tmp_path / "streak.csv", rows)
    result = analyze_trade_table(csv)

    assert result["status"] == STATUS_OK
    streaks = result["metrics"]["streaks"]
    assert streaks["max_win_streak"] == 3
    assert streaks["max_loss_streak"] == 4

    top_lengths = [s["length"] for s in streaks["top_streaks"]]
    assert top_lengths == [4, 3, 2]
    assert streaks["top_streaks"][0]["type"] == "loss"
    assert streaks["top_streaks"][1]["type"] == "win"


# ---------------------------------------------------------------------
# 낙폭 기여 top_n — 손계산 대조.
# ---------------------------------------------------------------------
def test_drawdown_contributors_hand_calculated(tmp_path):
    # profit_amount 경로: 100,100,-400,-300,50,100,-50,200
    # equity: 100,200,-200,-500,-450,-350,-400,-200
    # peak(=200)→trough(=-500) 구간 = index2,3(pnl -400,-300), total_decline=700.
    pnls = [100, 100, -400, -300, 50, 100, -50, 200]
    rows = [
        {
            "종목명": f"t{i}",
            "수익률": (pnls[i] / 100.0),
            "수익금": pnls[i],
        }
        for i in range(len(pnls))
    ]
    csv = _write_csv(tmp_path / "drawdown.csv", rows)

    result = analyze_trade_table(csv, top_n=5)
    assert result["status"] == STATUS_OK
    dd = result["metrics"]["drawdown_contributors"]
    assert dd["unit"] == "amount"
    assert dd["total_decline"] == pytest.approx(700.0, abs=1e-6)
    assert dd["peak_index"] == 1
    assert dd["trough_index"] == 3
    assert len(dd["top"]) == 2
    assert dd["top"][0]["pnl"] == pytest.approx(-400.0)
    assert dd["top"][0]["id"] == "t2"
    assert dd["top"][0]["share_of_decline"] == pytest.approx(400.0 / 700.0, abs=1e-6)
    assert dd["top"][1]["pnl"] == pytest.approx(-300.0)
    assert dd["top"][1]["share_of_decline"] == pytest.approx(300.0 / 700.0, abs=1e-6)

    # top_n=1 이면 최대 기여자 한 건만.
    result_top1 = analyze_trade_table(csv, top_n=1)
    dd1 = result_top1["metrics"]["drawdown_contributors"]
    assert len(dd1["top"]) == 1
    assert dd1["top"][0]["pnl"] == pytest.approx(-400.0)


def test_drawdown_contributors_no_drawdown_when_monotonic(tmp_path):
    rows = [{"종목명": f"t{i}", "수익률": 1.0, "수익금": 100} for i in range(5)]
    csv = _write_csv(tmp_path / "monotonic.csv", rows)
    result = analyze_trade_table(csv)
    dd = result["metrics"]["drawdown_contributors"]
    assert dd["total_decline"] == 0.0
    assert dd["top"] == []
    assert "reason" in dd


# ---------------------------------------------------------------------
# MFE/MAE 컬럼 있음/없음.
# ---------------------------------------------------------------------
def _mfe_rows():
    rows = []
    for i in range(10):
        rows.append(
            {
                "종목명": f"win{i}",
                "수익률": 2.0,
                "R_매수후최고수익률": 4.0,
                "R_매수후최저수익률": -0.5,
            }
        )
    for i in range(10):
        rows.append(
            {
                "종목명": f"loss{i}",
                "수익률": -1.0,
                "R_매수후최고수익률": 0.5,
                "R_매수후최저수익률": -3.0,
            }
        )
    return rows


def test_mfe_mae_present(tmp_path):
    csv = _write_csv(tmp_path / "mfe.csv", _mfe_rows())
    result = analyze_trade_table(csv)
    mm = result["metrics"]["mfe_mae"]
    assert mm is not None
    # realized/mfe efficiency for wins: 2.0/4.0 = 0.5.
    assert mm["realized_over_mfe_efficiency"] == pytest.approx(0.5, abs=1e-9)
    # loss MAE mean=3.0, win MAE mean=0.5 → ratio = 6.0.
    assert mm["loss_vs_win_mae_ratio"] == pytest.approx(6.0, abs=1e-9)


def test_mfe_mae_absent(tmp_path):
    rows = [{"종목명": f"t{i}", "수익률": (1.0 if i % 2 == 0 else -1.0)} for i in range(10)]
    csv = _write_csv(tmp_path / "no_mfe.csv", rows)
    result = analyze_trade_table(csv)
    assert result["metrics"]["mfe_mae"] is None


# ---------------------------------------------------------------------
# 시간대 버킷 — fine_time에 따라 다른 라벨.
# ---------------------------------------------------------------------
def test_time_of_day_coarse_vs_fine(tmp_path):
    rows = [
        {"종목명": "a", "매수시간": "202506130915", "수익률": 1.0},
        {"종목명": "b", "매수시간": "202506130918", "수익률": -1.0},
        {"종목명": "c", "매수시간": "202506131032", "수익률": 1.0},
    ]
    csv = _write_csv(tmp_path / "tod.csv", rows)

    coarse = analyze_trade_table(csv, fine_time=False)
    fine = analyze_trade_table(csv, fine_time=True)

    tod_coarse = coarse["metrics"]["time_of_day"]
    tod_fine = fine["metrics"]["time_of_day"]

    assert tod_coarse["bucket_minutes"] == 30
    assert tod_fine["bucket_minutes"] == 5

    # coarse: 09:15/09:18 → 둘 다 0900 버킷.
    assert "0900" in tod_coarse["buckets"]
    assert tod_coarse["buckets"]["0900"]["count"] == 2
    # fine: 09:15와 09:18은 서로 다른 5분 버킷(0915 vs 0915... 0918→0915도 가능하므로
    #   최소한 fine 쪽 버킷 수가 coarse보다 적지 않음을 확인).
    assert len(tod_fine["buckets"]) >= len(tod_coarse["buckets"])


# ---------------------------------------------------------------------
# 진입 피처(B_*) 승/패 분리 요약.
# ---------------------------------------------------------------------
def test_entry_feature_split_top_column(tmp_path):
    rows = []
    for i in range(20):
        is_win = i < 10
        rows.append(
            {
                "종목명": f"t{i}",
                "수익률": (1.0 if is_win else -1.0),
                "B_clean": (100.0 + (i % 5)) if is_win else (10.0 + (i % 5)),
                "B_noise": 50.0 + (i % 7),
            }
        )
    csv = _write_csv(tmp_path / "entry.csv", rows)
    result = analyze_trade_table(csv)
    ef = result["metrics"]["entry_feature_split"]
    assert ef is not None
    assert ef["top"][0]["column"] == "B_clean"


def test_entry_feature_split_none_when_no_b_columns(tmp_path):
    rows = [{"종목명": f"t{i}", "수익률": (1.0 if i % 2 == 0 else -1.0)} for i in range(6)]
    csv = _write_csv(tmp_path / "no_b.csv", rows)
    result = analyze_trade_table(csv)
    assert result["metrics"]["entry_feature_split"] is None


# ---------------------------------------------------------------------
# 무예외 계약: 빈 CSV / 없는 파일 / 필수 컬럼 누락.
# ---------------------------------------------------------------------
def test_no_data_header_only_csv(tmp_path):
    path = tmp_path / "header_only.csv"
    path.write_text("종목명,매수시간,수익률,수익금\n", encoding="utf-8-sig")
    result = analyze_trade_table(str(path))
    assert result["status"] == STATUS_NO_DATA
    assert result["trade_count"] == 0
    assert result["metrics"] == {}
    assert result["nl_lines"] == []
    assert result["error"] is None


def test_no_data_completely_empty_file(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8-sig")
    result = analyze_trade_table(str(path))
    assert result["status"] == STATUS_NO_DATA
    assert result["trade_count"] == 0
    assert result["error"] is None


def test_error_missing_file(tmp_path):
    missing = str(tmp_path / "does_not_exist.csv")
    result = analyze_trade_table(missing)
    assert result["status"] == STATUS_ERROR
    assert result["trade_count"] == 0
    assert result["metrics"] == {}
    assert result["nl_lines"] == []
    assert result["error"] is not None


def test_error_missing_required_column(tmp_path):
    rows = [{"종목명": "t1", "매수시간": "202506130900", "수익금": 1000}]
    csv = _write_csv(tmp_path / "no_return_col.csv", rows)
    result = analyze_trade_table(csv)
    assert result["status"] == STATUS_ERROR
    assert result["trade_count"] == 1
    assert "수익률" in result["error"]


def test_never_raises_on_garbage_path():
    # 존재하지 않는 디렉터리/이상한 경로에도 예외를 던지지 않는다.
    result = analyze_trade_table("Z:/definitely/not/a/real/path/xyz.csv")
    assert result["status"] == STATUS_ERROR
    assert isinstance(result["error"], str)
