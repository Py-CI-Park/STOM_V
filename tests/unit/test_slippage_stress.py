"""V5 슬리피지 스트레스 advisory 단위 테스트 (tests/unit/test_slippage_stress.py).

합성 per-trade 결과 CSV(한국어 컬럼, utf-8-sig)를 tmp_path에 만들어
ai_strategy_loop/fitness/slippage_stress.py 의 계약을 검증한다.
DB/엔진/런타임 접근 없음 — 순수 파일 기반.
"""
from __future__ import annotations

import csv
import math

import pytest

from ai_strategy_loop.fitness.slippage_stress import (
    krx_tick_size,
    stress_report_from_csvs,
)

_COLUMNS = ["종목명", "매수시간", "매도시간", "매수가", "매도가", "매수금액", "매도금액", "수익률", "수익금"]


def _write_csv(path, rows):
    """합성 결과 CSV를 utf-8-sig(BOM)로 기록한다 — 실제 결과 파일 인코딩과 동일."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _trade(buy_price, sell_price, qty, *, sell_day="20250102", name="테스트"):
    """수량을 지정하면 수익금=(매도가-매수가)×수량으로 역산 가능한 정합 행을 만든다."""
    profit = (sell_price - buy_price) * qty
    return {
        "종목명": name,
        "매수시간": f"{sell_day}090000",
        "매도시간": f"{sell_day}100000",
        "매수가": buy_price,
        "매도가": sell_price,
        "매수금액": buy_price * qty,
        "매도금액": sell_price * qty,
        "수익률": round((sell_price / buy_price - 1) * 100, 2),
        "수익금": profit,
    }


def _scenario(report, tick, fee_bps):
    for sc in report["scenarios"]:
        if sc["tick"] == tick and sc["fee_bps"] == fee_bps:
            return sc
    raise AssertionError(f"시나리오 없음: tick={tick} fee={fee_bps}")


# ── (c) krx_tick_size 경계값 ─────────────────────────────────────────────


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        (1999, 1.0),
        (2000, 5.0),
        (4999, 5.0),
        (5000, 10.0),
        (19999, 10.0),
        (20000, 50.0),
        (49999, 50.0),
        (50000, 100.0),
        (199999, 100.0),
        (200000, 500.0),
        (499999, 500.0),
        (500000, 1000.0),
    ],
)
def test_krx_tick_size_boundaries(price, expected):
    assert krx_tick_size(price) == expected


# ── (a) 0틱·0bps == 원본 총수익 ──────────────────────────────────────────


def test_zero_tick_zero_fee_matches_original_total(tmp_path):
    rows = [
        _trade(10000, 10500, 10, sell_day="20250102"),
        _trade(50000, 49000, 5, sell_day="20250103"),  # 손실 거래(수량>0 역산 가능: 수익금<0, spread<0).
        _trade(3000, 3100, 100, sell_day="20250106"),
    ]
    path = tmp_path / "trades.csv"
    _write_csv(path, rows)

    report = stress_report_from_csvs([str(path)], tick_levels=(0, 1), extra_fee_bps=(0.0,))
    expected_total = sum(r["수익금"] for r in rows)

    assert report["trade_count"] == 3
    assert report["skipped_trades"] == 0
    base = _scenario(report, 0, 0.0)
    assert base["total_profit"] == pytest.approx(expected_total)
    assert base["profit_delta"] == pytest.approx(0.0)
    assert base["profit_retention_ratio"] == pytest.approx(1.0)
    assert base["trade_count"] == 3


# ── (b) 틱 증가 시 수익 단조감소 ─────────────────────────────────────────


def test_profit_monotonically_decreases_with_ticks(tmp_path):
    rows = [
        _trade(10000, 10500, 10),
        _trade(3000, 3200, 50),
        _trade(250000, 260000, 2),
    ]
    path = tmp_path / "trades.csv"
    _write_csv(path, rows)

    ticks = (0, 1, 2, 3)
    report = stress_report_from_csvs([str(path)], tick_levels=ticks, extra_fee_bps=(0.0,))
    totals = [_scenario(report, t, 0.0)["total_profit"] for t in ticks]
    for prev, cur in zip(totals, totals[1:]):
        assert cur < prev  # 모든 거래 수량>0 + 틱>0 → 엄격 단조감소.

    # 추가 수수료도 수익을 깎는다.
    report_fee = stress_report_from_csvs([str(path)], tick_levels=(0,), extra_fee_bps=(0.0, 5.0))
    assert (
        _scenario(report_fee, 0, 5.0)["total_profit"]
        < _scenario(report_fee, 0, 0.0)["total_profit"]
    )


# ── (d) 수량 역산 불가 행 → skipped 정직 공시 ───────────────────────────


def test_unrecoverable_quantity_rows_counted_as_skipped(tmp_path):
    good = _trade(10000, 10500, 10)
    flat = dict(_trade(10000, 10000, 0), **{"수익금": -500})  # 매도가==매수가 → 0 나눗셈.
    negative_qty = dict(_trade(10000, 9000, 1), **{"수익금": 500})  # 수익금/spread < 0.
    path = tmp_path / "trades.csv"
    _write_csv(path, [good, flat, negative_qty])

    report = stress_report_from_csvs([str(path)], tick_levels=(0,), extra_fee_bps=(0.0,))
    assert "skipped_trades" in report
    assert report["skipped_trades"] == 2
    assert report["trade_count"] == 1
    assert _scenario(report, 0, 0.0)["total_profit"] == pytest.approx(good["수익금"])


# ── (e) 빈 CSV / 결측 컬럼 안전 처리 ─────────────────────────────────────


def test_empty_csv_and_missing_columns_are_safe(tmp_path):
    header_only = tmp_path / "header_only.csv"
    _write_csv(header_only, [])

    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")

    missing_cols = tmp_path / "missing_cols.csv"
    missing_cols.write_text("종목명,수익금\n테스트,1000\n", encoding="utf-8-sig")

    nonexistent = tmp_path / "no_such_file.csv"

    report = stress_report_from_csvs(
        [str(header_only), str(empty_file), str(missing_cols), str(nonexistent)],
        tick_levels=(0, 1),
        extra_fee_bps=(0.0,),
    )
    assert report["trade_count"] == 0
    assert report["skipped_trades"] == 0
    assert report["base_total_profit"] == 0.0
    for sc in report["scenarios"]:
        assert sc["total_profit"] == 0.0
        assert sc["profit_retention_ratio"] is None  # base<=0 → 정의 불가.
        assert sc["breakeven_tick"] is None  # 거래 없음 → 기울기 미정의.
        assert sc["mdd_amount"] == 0.0


# ── JSON 직렬화 안전성(비유한수 금지) + breakeven 선형추정 ───────────────


def test_report_is_json_serializable_and_breakeven_linear(tmp_path):
    import json

    rows = [_trade(10000, 10500, 10)]  # 수익 5000, 틱당 비용 (10+10)×10=200/틱.
    path = tmp_path / "trades.csv"
    _write_csv(path, rows)

    report = stress_report_from_csvs([str(path)], tick_levels=(0, 1, 2), extra_fee_bps=(0.0,))
    text = json.dumps(report, ensure_ascii=False)  # 비유한수 있으면 여기서 실패.
    assert "NaN" not in text and "Infinity" not in text

    base = _scenario(report, 0, 0.0)
    # 선형추정: 5000 / 200 = 25틱에서 수익 0.
    assert base["breakeven_tick"] == pytest.approx(25.0)
    # 검산: 1틱 손실분으로 외삽해도 동일해야 한다(정확 선형).
    one = _scenario(report, 1, 0.0)
    slope = base["total_profit"] - one["total_profit"]
    assert base["breakeven_tick"] == pytest.approx(base["total_profit"] / slope)
    for sc in report["scenarios"]:
        for key in ("total_profit", "profit_delta", "mdd_amount"):
            assert math.isfinite(sc[key])


# ── MDD: 일별 집계 후 누적곡선 최대낙폭 금액 ─────────────────────────────


def test_mdd_amount_uses_daily_cumulative_curve(tmp_path):
    rows = [
        _trade(10000, 10500, 10, sell_day="20250102"),   # +5000 → cum 5000 (peak)
        _trade(10000, 9700, 10, sell_day="20250103"),    # -3000 → cum 2000
        _trade(10000, 9900, 10, sell_day="20250106"),    # -1000 → cum 1000 (dd 4000)
        _trade(10000, 10200, 10, sell_day="20250107"),   # +2000 → cum 3000
    ]
    path = tmp_path / "trades.csv"
    _write_csv(path, rows)

    report = stress_report_from_csvs([str(path)], tick_levels=(0,), extra_fee_bps=(0.0,))
    assert _scenario(report, 0, 0.0)["mdd_amount"] == pytest.approx(4000.0)
