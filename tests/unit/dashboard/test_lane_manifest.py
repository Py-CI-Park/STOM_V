"""QSP7 레인 manifest 계약(P6) — 기간 비중첩·레인 분리·전략 드리프트 감지."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ai_strategy_loop.dashboard.lane_manifest import (
    LANE_MANIFESTS,
    lane_manifest_payload,
)


def test_both_lanes_have_non_overlapping_design_and_oos_periods() -> None:
    # Given/When: 정본 manifest 두 레인.
    for lane, manifest in LANE_MANIFESTS.items():
        # Then: 설계와 OOS 는 겹치지 않고, 설계가 먼저 온다.
        assert manifest.design.end < manifest.oos.start, lane
        assert manifest.design.start < manifest.design.end, lane
        assert manifest.oos.start < manifest.oos.end, lane


def test_lanes_are_fully_separated_baselines_and_sessions() -> None:
    tick, min_lane = LANE_MANIFESTS["tick"], LANE_MANIFESTS["min"]
    # Then: 기준선·세션이 레인 간 섞이지 않는다.
    assert tick.baseline_buy != min_lane.baseline_buy
    assert tick.baseline_sell != min_lane.baseline_sell
    assert tick.session_end == 92800      # tick DB 는 09:30 까지만 존재
    assert min_lane.session_end == 152800
    assert tick.timeframe == "tick" and min_lane.timeframe == "min"


def test_payload_reports_strategy_hash_from_actual_db(tmp_path: Path, monkeypatch) -> None:
    # Given: 기준선 매수식만 등록된 임시 strategy DB.
    db = tmp_path / "strategy.db"
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE stockbuy ("index" TEXT, 전략코드 TEXT)')
        connection.execute('CREATE TABLE stocksell ("index" TEXT, 전략코드 TEXT)')
        connection.execute(
            'INSERT INTO stockbuy VALUES (?, ?)',
            (LANE_MANIFESTS["min"].baseline_buy, "매수 = False"),
        )
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(db))

    # When: min manifest payload 를 요청한다.
    payload = lane_manifest_payload("min")

    # Then: 실물 DB 기준 해시가 계산되고, 매도식 부재는 미등록으로 드러난다.
    assert payload["available"] is True
    assert payload["design_oos_overlap"] is False
    assert len(payload["baseline_buy_sha256"]) == 64
    assert payload["baseline_sell_sha256"] == ""
    assert payload["baseline_registered"] is False


def test_unknown_lane_is_rejected_with_known_lanes() -> None:
    payload = lane_manifest_payload("hour")
    assert payload["available"] is False
    assert payload["lanes"] == ["min", "tick"]
