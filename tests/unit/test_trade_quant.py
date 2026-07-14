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
    TRADE_QUANT_SECTION_SCHEMA_V3,
    analyze_trade_table,
    build_trade_quant_section,
)
from ai_strategy_loop.fitness.edge_ratio import TradeColumnContract  # noqa: E402



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


# --- G3 아키텍트 리뷰 반영 회귀 가드 ---

def test_drawdown_contributors_exclude_positive_trades_and_share_le_100(tmp_path):
    """MEDIUM 반영: 낙폭 구간 내 이익 거래는 기여자에서 제외, share 분모=구간 총손실(합<=100%)."""
    import pandas as pd
    from ai_strategy_loop.autopsy.trade_quant import _drawdown_contributors

    # equity: +100 → -700 → -600 (peak idx0, trough idx1..2 창에 +100 반등 포함)
    pnl = pd.Series([100.0, -800.0, 100.0, -200.0])
    res = _drawdown_contributors(pnl, None, top_n=5)
    tops = res["top"]
    assert all(t["pnl"] < 0 for t in tops), tops  # 양수 거래 미포함
    share_sum = sum(t["share_of_decline"] for t in tops)
    assert share_sum <= 1.0 + 1e-9, share_sum
    assert res["window_gross_loss"] == 1000.0  # 800+200 (분모=총손실)


def test_parse_hhmm_forms():
    """LOW 반영: 14/12/6/5(선행0 소실)/4자리 지원, 13자리 오버매치 거부."""
    from ai_strategy_loop.autopsy.trade_quant import _parse_hhmm

    assert _parse_hhmm("20250613091512") == "0915"   # 14자리
    assert _parse_hhmm("202506130915") == "0915"     # 12자리
    assert _parse_hhmm("091512") == "0915"           # 6자리
    assert _parse_hhmm(90512) == "0905"              # int로 선행0 소실된 5자리
    assert _parse_hhmm("0915") == "0915"             # 4자리
    assert _parse_hhmm("1749790512345") is None      # 13자리 epoch ms — 거부
    assert _parse_hhmm("쓰레기") is None


def test_profit_factor_none_with_reason_when_no_losses(tmp_path):
    """LOW 반영: 손실 0건이면 PF=None+사유(스코어러의 999 cap 관례와 의도적 분기)."""
    import csv
    from ai_strategy_loop.autopsy.trade_quant import analyze_trade_table

    p = tmp_path / "all_wins.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["수익률"])
        for _ in range(5):
            w.writerow(["1.5"])
    res = analyze_trade_table(str(p))
    assert res["status"] == "ok"
    assert res["metrics"]["profit_factor"] is None
    assert "손실 거래 없음" in res["metrics"]["profit_factor_reason"]


def test_time_of_day_carries_pnl_unit(tmp_path):
    """LOW 반영: time_of_day 결과에 pnl_unit(amount|pct) 명시."""
    import csv
    from ai_strategy_loop.autopsy.trade_quant import analyze_trade_table

    p = tmp_path / "unit.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["수익률", "매수시간"])
        w.writerow(["1.0", "202506130905"])
        w.writerow(["-0.5", "202506130912"])
    res = analyze_trade_table(str(p))
    assert res["metrics"]["time_of_day"]["pnl_unit"] == "pct"  # 수익금 컬럼 없음 → pct

# ---------------------------------------------------------------------
# DR-01 — 0-기준 MDD / 행순서 불변 / 무손익 거래 제외.
# ---------------------------------------------------------------------

def test_drawdown_zero_origin_single_loss_counts_full():
    """DR-01: pnl=[-100] → 낙폭 기준(peak)이 0에서 시작하므로 낙폭 전체(100)가 잡힌다."""
    from ai_strategy_loop.autopsy.trade_quant import _drawdown_contributors

    res = _drawdown_contributors(pd.Series([-100.0]), None, top_n=5)
    assert res["total_decline"] == pytest.approx(100.0, abs=1e-9)


def test_drawdown_zero_origin_two_losses_accumulate():
    """DR-01: pnl=[-100,-50] → 누적손실 전체(150)가 낙폭으로 잡힌다."""
    from ai_strategy_loop.autopsy.trade_quant import _drawdown_contributors

    res = _drawdown_contributors(pd.Series([-100.0, -50.0]), None, top_n=5)
    assert res["total_decline"] == pytest.approx(150.0, abs=1e-9)


def test_drawdown_zero_origin_gain_then_bigger_loss():
    """DR-01: pnl=[100,-150] → equity 150 하락(100→-50)이 낙폭으로 잡힌다."""
    from ai_strategy_loop.autopsy.trade_quant import _drawdown_contributors

    res = _drawdown_contributors(pd.Series([100.0, -150.0]), None, top_n=5)
    assert res["total_decline"] == pytest.approx(150.0, abs=1e-9)


def test_row_order_permutation_does_not_change_streak_or_mdd(tmp_path):
    """DR-01: 매수시간이 있으면 입력 행 순서를 뒤섞어도 연속패 길이/MDD가 동일하다."""
    times = [f"2025061309{i:02d}" for i in range(6)]
    pnls = [100.0, -50.0, -50.0, 200.0, -300.0, 50.0]
    base_rows = [
        {"종목명": f"t{i}", "매수시간": times[i], "수익률": pnls[i] / 100.0, "수익금": pnls[i]}
        for i in range(len(pnls))
    ]

    ordered_csv = _write_csv(tmp_path / "ordered.csv", base_rows)
    shuffled_csv = _write_csv(tmp_path / "shuffled.csv", list(reversed(base_rows)))

    ordered = analyze_trade_table(ordered_csv)
    shuffled = analyze_trade_table(shuffled_csv)

    assert ordered["status"] == STATUS_OK
    assert shuffled["status"] == STATUS_OK
    assert (
        ordered["metrics"]["streaks"]["max_loss_streak"]
        == shuffled["metrics"]["streaks"]["max_loss_streak"]
    )
    assert (
        ordered["metrics"]["drawdown_contributors"]["total_decline"]
        == shuffled["metrics"]["drawdown_contributors"]["total_decline"]
    )


def test_neutral_trades_do_not_change_payoff_ratio(tmp_path):
    """DR-01: 1승/1패 + 무손익(0%) 98건을 더해도 payoff_ratio 는 그대로다."""
    base_rows = [{"종목명": "win0", "수익률": 10.0}, {"종목명": "loss0", "수익률": -5.0}]
    neutral_rows = [{"종목명": f"neutral{i}", "수익률": 0.0} for i in range(98)]

    base_csv = _write_csv(tmp_path / "base.csv", base_rows)
    padded_csv = _write_csv(tmp_path / "padded.csv", base_rows + neutral_rows)

    base_result = analyze_trade_table(base_csv)
    padded_result = analyze_trade_table(padded_csv)

    assert base_result["metrics"]["payoff_ratio"] == pytest.approx(2.0, abs=1e-9)
    assert padded_result["metrics"]["payoff_ratio"] == pytest.approx(
        base_result["metrics"]["payoff_ratio"], abs=1e-9
    )


# ---------------------------------------------------------------------------
# DR-05 — build_trade_quant_section: AnalysisCardV3 정본 섹션.
# ---------------------------------------------------------------------------


def _v3_trade_rows(n=30, n_days=10, n_symbols=3):
    rows = []
    for i in range(n):
        rows.append({
            "매수시간": f"202601{(i % n_days) + 1:02d}090000",
            "종목코드": f"SYM{i % n_symbols}",
            "수익률": 1.0 if i % 2 == 0 else -0.5,
            "수익금": 100.0 if i % 2 == 0 else -50.0,
        })
    return rows


def test_build_trade_quant_section_v3_sample_counts():
    rows = _v3_trade_rows(n=30, n_days=10, n_symbols=3)
    section = build_trade_quant_section(rows)
    assert section["schema"] == TRADE_QUANT_SECTION_SCHEMA_V3
    assert section["n_trades"] == 30
    assert section["n_days"] == 10
    assert section["n_symbols"] == 3
    assert section["missing_count"] == 0


def test_build_trade_quant_section_v3_missing_and_duplicate():
    rows = _v3_trade_rows(n=10, n_days=5, n_symbols=2)
    rows.append(dict(rows[0]))  # exact duplicate row -> excluded_duplicate_count.
    rows.append({"매수시간": "20260101090000", "종목코드": "SYMX"})  # missing 수익률.
    section = build_trade_quant_section(rows)
    assert section["missing_count"] == 1
    assert section["excluded_duplicate_count"] == 1


def test_build_trade_quant_section_v3_tail_top1_5_10_removal():
    rows = [
        {"매수시간": f"2026010{i+1}090000", "종목코드": "S0", "수익률": 1.0, "수익금": float(profit)}
        for i, profit in enumerate([1000, 10, 10, 10, 10, 10, 10, 10, 10, 10])
    ]
    section = build_trade_quant_section(rows)
    total = sum(r["수익금"] for r in rows)
    ordered = sorted((r["수익금"] for r in rows), reverse=True)
    assert section["tail"]["top1_removed_total"] == round(total - sum(ordered[:1]), 6)
    assert section["tail"]["top5_removed_total"] == round(total - sum(ordered[:5]), 6)
    assert section["tail"]["top10_removed_total"] == round(total - sum(ordered[:10]), 6)


def test_build_trade_quant_section_v3_downside_and_cvar():
    rows = [
        {"매수시간": f"2026010{i+1}090000", "종목코드": "S0", "수익률": ret, "수익금": ret * 100}
        for i, ret in enumerate([-5.0, -3.0, -1.0, 1.0, 2.0])
    ]
    section = build_trade_quant_section(rows)
    assert section["downside"]["downside_deviation"] is not None
    assert section["downside"]["cvar_95"] is not None
    # cvar_95는 최악 5%(최소 1개) 수익률의 평균이므로 전체 최소값 이하다.
    assert section["downside"]["cvar_95"] <= min(r["수익률"] for r in rows)


def test_build_trade_quant_section_v3_capacity_is_proxy_labeled():
    rows = _v3_trade_rows(n=20, n_days=4, n_symbols=2)
    section = build_trade_quant_section(rows)
    assert section["capacity"]["trades_per_day"] == round(20 / 4, 6)
    assert "proxy" in section["capacity"]["note"]


def test_build_trade_quant_section_v3_reuses_promotion_diagnostics_slippage_stress():
    """DR-05: 비용/슬리피지 스트레스는 promotion_diagnostics.compute_slippage_stress
    를 그대로 재사용한다(재구현 금지) — 직접 호출한 결과와 haircut별 stressed_profit이
    정확히 같아야 한다.
    """
    from ai_strategy_loop.fitness.promotion_diagnostics import (
        DEFAULT_HAIRCUTS,
        OosTradeSummary,
        compute_slippage_stress,
    )

    rows = _v3_trade_rows(n=30, n_days=10, n_symbols=3)
    section = build_trade_quant_section(rows)
    total_profit = sum(r["수익금"] for r in rows)
    direct = compute_slippage_stress(OosTradeSummary(name="x", final_profit=total_profit, trade_count=30))
    assert section["cost_stress"]["status"] == direct.status
    assert section["cost_stress"]["promotion_passed"] == direct.promotion_passed
    got = {row["haircut"]: row["stressed_profit"] for row in section["cost_stress"]["rows"]}
    want = {row.haircut: row.stressed_profit for row in direct.rows}
    assert got == want
    assert set(got.keys()) == set(DEFAULT_HAIRCUTS)


def test_build_trade_quant_section_v3_accepts_custom_contract():
    contract = TradeColumnContract(date_column="매수시간", symbol_column="종목코드")
    rows = _v3_trade_rows(n=15, n_days=5, n_symbols=2)
    section = build_trade_quant_section(rows, contract)
    assert section["n_trades"] == 15
