"""QSP10 P1 — 라벨 v2(다지평 봉투 + 배리어 도달 시각) 계약과 불변식.

핵심: 봉투는 체크포인트별 **그때까지의 누적** 최고/최저이고, 도달 시각은
**실현 가능 경로**(매도호가1 진입 → 매수호가1 청산) 기준 최초 교차다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from ai_strategy_loop.labeling.label_factory import build_day_labels
from ai_strategy_loop.labeling.lanes import TICK

DAY = 20250403
NO_HIT = TICK.barrier_horizon  # 미도달 표기값


def _row(hhmmss: int, price: float, *, spread: float = 10.0) -> dict:
    return {
        "index": DAY * 1_000_000 + hhmmss,
        "현재가": price, "시가": 1000.0, "고가": price, "저가": 1000.0, "등락율": 5.0,
        "당일거래대금": 100.0, "체결강도": 100.0, "초당매수수량": 10.0, "초당매도수량": 5.0,
        "거래대금증감": 0.0, "전일비": 1.0, "회전율": 1.0, "전일동시간비": 1.0,
        "시가총액": 2000.0, "라운드피겨위5호가이내": 0.0, "VI해제시간": 0.0,
        "VI가격": 5000.0, "VI호가단위": 10.0, "초당거래대금": 10.0,
        "고저평균대비등락율": 1.0, "저가대비고가등락율": 1.0,
        "초당매수금액": 1.0, "초당매도금액": 1.0,
        "당일매수금액": 1.0, "최고매수금액": 1.0, "최고매수가격": price,
        "당일매도금액": 1.0, "최고매도금액": 1.0, "최고매도가격": price,
        **{f"매도호가{i}": price + spread * i for i in range(1, 6)},
        **{f"매수호가{i}": price - spread * i for i in range(1, 6)},
        **{f"매도잔량{i}": 100.0 for i in range(1, 6)},
        **{f"매수잔량{i}": 100.0 for i in range(1, 6)},
        "매도총잔량": 500.0, "매수총잔량": 500.0, "매도수5호가잔량합": 400.0, "관심종목": 1.0,
    }


def _seconds(start: int, count: int, price: float) -> list[dict]:
    h, m, s = start // 10000, (start // 100) % 100, start % 100
    base = h * 3600 + m * 60 + s
    out = []
    for k in range(count):
        t = base + k
        out.append(_row(t // 3600 * 10000 + (t % 3600) // 60 * 100 + t % 60, price))
    return out


def _make(path: Path, rows: list[dict]) -> str:
    con = sqlite3.connect(path)
    pd.DataFrame(rows).to_sql("005930", con, index=False)
    con.close()
    return str(path)


def test_envelope_is_cumulative_and_monotone(tmp_path: Path) -> None:
    # Given: 1000 유지 60초 → 1050 (+5%) 60초 → 950 (-5%) 나머지.
    rows = _seconds(90000, 60, 1000.0) + _seconds(90100, 60, 1050.0) + _seconds(90200, 200, 950.0)
    out = build_day_labels(_make(tmp_path / "t.db", rows), day=DAY, lane=TICK)
    first = out[out["시분초"] == 90000].iloc[0]

    # Then: 봉투는 체크포인트가 길수록 넓어지기만 한다(단조).
    mfes = [first[f"mfe_{h}"] for h in TICK.checkpoints]
    maes = [first[f"mae_{h}"] for h in TICK.checkpoints]
    assert mfes == sorted(mfes), "MFE 봉투가 단조 증가가 아니다"
    assert maes == sorted(maes, reverse=True), "MAE 봉투가 단조 감소가 아니다"
    # 30초 시점엔 아직 평평 → 0 근처, 120초 시점엔 +5% 를 이미 봤다.
    assert first["mfe_30"] == pytest.approx(0.0, abs=1e-6)
    assert first["mfe_120"] == pytest.approx(5.0, abs=0.01)
    assert first["mae_300"] == pytest.approx(-5.0, abs=0.01)


def test_barrier_hit_times_are_ordered_and_use_executable_path(tmp_path: Path) -> None:
    # Given: 1000 에서 30초 후 1030(+3%), 60초 후 1060(+6%).
    rows = _seconds(90000, 30, 1000.0) + _seconds(90030, 30, 1030.0) + _seconds(90100, 300, 1060.0)
    out = build_day_labels(_make(tmp_path / "t.db", rows), day=DAY, lane=TICK)
    first = out[out["시분초"] == 90000].iloc[0]

    # Then: 낮은 배리어가 먼저 닿는다(단조).
    assert first["hit_up_1"] <= first["hit_up_2"] <= first["hit_up_3"] <= first["hit_up_5"]
    # 진입은 매도호가1(1010), 청산은 매수호가1 기준 — 30초 시점 bid=1020 → +0.99% (아직 +1% 미만)
    assert first["hit_up_1"] == 60          # 60초 시점 bid=1050 → +3.96%
    assert first["hit_up_3"] == 60
    assert first["hit_up_5"] == NO_HIT      # bid 기준 +5% 는 못 넘음(1060-10=1050 → +3.96%)


def test_down_barriers_and_no_hit_marker(tmp_path: Path) -> None:
    rows = _seconds(90000, 60, 1000.0) + _seconds(90100, 300, 970.0)
    out = build_day_labels(_make(tmp_path / "t.db", rows), day=DAY, lane=TICK)
    first = out[out["시분초"] == 90000].iloc[0]

    # 진입 순간엔 팔 수 없다 — 최초 도달은 t+1. bid(990) vs 매수가(1010) = −1.98%.
    assert first["hit_dn_1"] == 1
    assert first["hit_dn_3"] == 60         # 970-10=960 → −4.95%
    assert first["hit_up_1"] == NO_HIT     # 오른 적 없음


def test_fixed_horizon_never_exceeds_envelope(tmp_path: Path) -> None:
    """불변식: 고정 h 수익률(비용 차감)은 같은 h 봉투(원가격) 안에 있어야 한다.

    봉투는 원가격 기준이고 frB 는 왕복 비용 차감 후라, 하한은 비용만큼 낮아진다.
    """
    from ai_strategy_loop.labeling import label_spec as spec
    cost = (spec.COST_IN + spec.COST_OUT) * 100 + 1e-6

    rows = _seconds(90000, 30, 1000.0) + _seconds(90030, 30, 1020.0) + _seconds(90100, 300, 990.0)
    out = build_day_labels(_make(tmp_path / "t.db", rows), day=DAY, lane=TICK)
    row = out[out["시분초"] == 90000].iloc[0]
    for h in TICK.checkpoints:
        if f"frB_{h}" in out.columns and not pd.isna(row[f"frB_{h}"]):
            assert row[f"frB_{h}"] <= row[f"mfe_{h}"] + 1e-6
            assert row[f"frB_{h}"] >= row[f"mae_{h}"] - cost
