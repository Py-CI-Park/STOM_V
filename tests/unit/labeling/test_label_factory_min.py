"""min 레인 라벨 공장 — 분 해상도 시각 산술·분당 컬럼 매핑·전일장 창 계약."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.label_factory import build_day_labels
from ai_strategy_loop.labeling.lanes import MIN


DAY = 20250915


def _row(hhmm: int, price: float, *, rate: float = 5.0, tv: float = 10.0) -> dict:
    return {
        "index": DAY * 10_000 + hhmm,
        "현재가": price, "시가": 1000.0, "고가": price, "저가": 1000.0, "등락율": rate,
        "당일거래대금": 100.0, "체결강도": 100.0, "분당매수수량": 10.0, "분당매도수량": 5.0,
        "거래대금증감": 0.0, "전일비": 1.0, "회전율": 1.0, "전일동시간비": 1.0,
        "시가총액": 2000.0, "라운드피겨위5호가이내": 0.0, "VI해제시간": 0.0,
        "VI가격": 2000.0, "VI호가단위": 10.0, "분당거래대금": tv,
        "고저평균대비등락율": 1.0, "저가대비고가등락율": 1.0,
        "분당매수금액": 1.0, "분당매도금액": 1.0,
        "당일매수금액": 1.0, "최고매수금액": 1.0, "최고매수가격": price,
        "당일매도금액": 1.0, "최고매도금액": 1.0, "최고매도가격": price,
        "분봉시가": price, "분봉고가": price, "분봉저가": price,
        **{f"매도호가{i}": price + 10.0 * i for i in range(1, 6)},
        **{f"매수호가{i}": price - 10.0 * i for i in range(1, 6)},
        **{f"매도잔량{i}": 100.0 for i in range(1, 6)},
        **{f"매수잔량{i}": 100.0 for i in range(1, 6)},
        "매도총잔량": 500.0, "매수총잔량": 500.0, "매도수5호가잔량합": 400.0, "관심종목": 1.0,
    }


def _minutes(start_hhmm: int, count: int, price: float = 1000.0) -> list[dict]:
    h, m = start_hhmm // 100, start_hhmm % 100
    mod = h * 60 + m
    return [_row((mod + k) // 60 * 100 + (mod + k) % 60, price) for k in range(count)]


def _make_db(path: Path, rows: list[dict]) -> str:
    con = sqlite3.connect(path)
    pd.DataFrame(rows).to_sql("005930", con, index=False)
    con.close()
    return str(path)


def test_min_lane_fixed_horizon_and_hour_boundary(tmp_path: Path) -> None:
    # Given: 09:55 부터 20분 — 10:00 경계(시 산술 함정)를 걸친다. 10분 뒤 1100 도달.
    rows = _minutes(955, 10) + _minutes(1005, 15, price=1100.0)
    db = _make_db(tmp_path / "min.db", rows)

    out = build_day_labels(db, day=DAY, lane=MIN)

    first = out[out["시분초"] == 955].iloc[0]
    expect = (1090.0 * (1 - spec.COST_OUT)) / (1010.0 * (1 + spec.COST_IN)) - 1
    assert first["frA_10"] == pytest.approx(expect * 100, abs=1e-6)


def test_min_lane_entry_window_and_close(tmp_path: Path) -> None:
    # Given: 14:50~15:28 — 진입은 15:00 까지만, close 는 마지막 관측.
    rows = _minutes(1450, 39)
    db = _make_db(tmp_path / "min.db", rows)

    out = build_day_labels(db, day=DAY, lane=MIN)

    assert out["시분초"].max() <= MIN.entry_end
    last_entry = out[out["시분초"] == 1500].iloc[0]
    assert not pd.isna(last_entry["frA_close"])
    # 15:28 까지 있으므로 절단 아님.
    assert last_entry["close_truncated"] == 0


def test_min_lane_uses_bunland_flow_columns(tmp_path: Path) -> None:
    rows = _minutes(900, 90)
    db = _make_db(tmp_path / "min.db", rows)

    out = build_day_labels(db, day=DAY, lane=MIN)

    # 분당 계열이 스냅샷으로 실리고, 파생 순매수금액은 902/905 원식대로 **현재가** 기준.
    assert "분당거래대금" in out.columns and "분당매수수량" in out.columns
    assert out.iloc[0]["분당순매수금액"] == pytest.approx((10.0 - 5.0) * 1000.0 / 1_000_000)
