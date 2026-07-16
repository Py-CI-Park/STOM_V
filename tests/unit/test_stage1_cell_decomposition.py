"""cli.stage1_cell_decomposition 계약 테스트 (G005 slice B).

합성 per-trade CSV(tmp_path)만 사용한다 -- 백테스트 재실행 없음, DB 쓰기 없음.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from cli.condition_history_schema import (
    ExitProfileReceiptV1,
    SeedBoundaryIntentReceiptV1,
    validate_research_node,
)
from cli.stage1_cell_decomposition import (
    CAMPAIGN_NAME,
    REASON_BUY_TIME_OUT_OF_WINDOW,
    REASON_CAP_OUT_OF_BAND,
    REASON_INVALID_CAP,
    REASON_MISSING_BUY_TIME,
    REASON_MISSING_CAP,
    REASON_UNPARSEABLE_BUY_TIME,
    cells_to_history_evaluations,
    compute_csv_sha256,
    decompose_cells,
    publish_stage1,
)
from cli.wide_seed_trial_planner import TrialSpecV1, build_default_plan

_CSV_FIELDS = ["종목명", "종목코드", "시가총액", "매수시간", "매도시간", "수익률", "수익금"]


def _write_csv(path: Path, rows: list[dict]) -> Path:
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in _CSV_FIELDS})
    return path


def _tick_spec() -> TrialSpecV1:
    boundary_sha = SeedBoundaryIntentReceiptV1.frozen_default().sha256
    exit_sha = ExitProfileReceiptV1.frozen_default().sha256
    specs = build_default_plan(boundary_sha, exit_sha)
    (tick_spec,) = [s for s in specs if s.lane == "tick"]
    return tick_spec


def _row(name, code, cap, buy_time, sell_time="20250110090100", ret="", amt="") -> dict:
    return {
        "종목명": name,
        "종목코드": code,
        "시가총액": cap,
        "매수시간": buy_time,
        "매도시간": sell_time,
        "수익률": ret,
        "수익금": amt,
    }


# ---------------------------------------------------------------------------
# decompose_cells -- 경계 라우팅
# ---------------------------------------------------------------------------


def test_decompose_cells_time_and_cap_boundary_routing(tmp_path):
    spec = _tick_spec()
    rows = [
        _row("A", "005930", "1000", "20250110090000"),  # window0 [90000,90500), cap band0 -> ordinal 0
        _row("B", "005931", "1000", "20250110090459"),  # window0, cap band0 -> ordinal 0
        _row("C", "005932", "1000", "20250110090500"),  # window1 [90500,91000), cap band0 -> ordinal 4
        _row("D", "005933", "2999.9", "20250110090000"),  # window0, cap band0 (<3000) -> ordinal 0
        _row("E", "005934", "3000", "20250110090000"),  # window0, cap band1 [3000,6000) -> ordinal 1
    ]
    csv_path = _write_csv(tmp_path / "trades.csv", rows)

    result = decompose_cells(csv_path, spec)

    by_ordinal = {c["ordinal"]: c for c in result["cells"]}
    assert by_ordinal[0]["trade_count"] == 3  # A, B, D
    assert by_ordinal[1]["trade_count"] == 1  # E
    assert by_ordinal[4]["trade_count"] == 1  # C
    assert result["unassigned"]["count"] == 0
    assert result["total_rows"] == 5
    assert result["parity_ok"] is True
    assert sum(c["trade_count"] for c in result["cells"]) + result["unassigned"]["count"] == result["total_rows"]


def test_decompose_cells_iso_datetime_format_parses_same_as_compact(tmp_path):
    spec = _tick_spec()
    rows = [
        _row("A", "005930", "1000", "2025-01-10 09:00:00"),
        _row("B", "005931", "1000", "20250110090000"),
    ]
    csv_path = _write_csv(tmp_path / "trades.csv", rows)

    result = decompose_cells(csv_path, spec)
    by_ordinal = {c["ordinal"]: c for c in result["cells"]}
    assert by_ordinal[0]["trade_count"] == 2
    assert result["unassigned"]["count"] == 0


# ---------------------------------------------------------------------------
# unassigned 사유
# ---------------------------------------------------------------------------


def test_decompose_cells_unassigned_reasons_are_typed_and_never_zero_cap(tmp_path):
    spec = _tick_spec()
    rows = [
        _row("A", "005930", "1000", ""),  # missing buy time
        _row("B", "005931", "1000", "not-a-time"),  # unparseable buy time
        _row("C", "005932", "", "20250110090000"),  # missing cap
        _row("D", "005933", "not-a-cap", "20250110090000"),  # invalid cap
        _row("E", "005934", "1000", "20250110230000"),  # 23:00:00 -> out of any tick window
        _row("F", "005935", "-500", "20250110090000"),  # negative cap -> out of band
        _row("G", "005936", "1000", "20250110090000"),  # valid, routes to ordinal 0
    ]
    csv_path = _write_csv(tmp_path / "trades.csv", rows)

    result = decompose_cells(csv_path, spec)

    assert result["unassigned"]["count"] == 6
    assert result["unassigned"]["reasons"] == {
        REASON_MISSING_BUY_TIME: 1,
        REASON_UNPARSEABLE_BUY_TIME: 1,
        REASON_MISSING_CAP: 1,
        REASON_INVALID_CAP: 1,
        REASON_BUY_TIME_OUT_OF_WINDOW: 1,
        REASON_CAP_OUT_OF_BAND: 1,
    }
    by_ordinal = {c["ordinal"]: c for c in result["cells"]}
    assert by_ordinal[0]["trade_count"] == 1  # only G
    # cap==0 밴드(ordinal 0)에 unassigned 행이 절대 흘러들지 않았는지 확인.
    assert sum(c["trade_count"] for c in result["cells"]) == 1
    assert result["parity_ok"] is True
    assert sum(c["trade_count"] for c in result["cells"]) + result["unassigned"]["count"] == result["total_rows"]


# ---------------------------------------------------------------------------
# None-vs-0 시맨틱스
# ---------------------------------------------------------------------------


def test_decompose_cells_none_vs_zero_semantics(tmp_path):
    spec = _tick_spec()
    rows = [
        _row("A", "005930", "1000", "20250110090000", ret="", amt=""),  # no pnl info at all
        _row("A", "005930", "1000", "20250110090100", ret="1.5", amt="1000"),  # winning
        _row("B", "005931", "1000", "20250110090200", ret="-2.0", amt="-500"),  # losing
    ]
    csv_path = _write_csv(tmp_path / "trades.csv", rows)

    result = decompose_cells(csv_path, spec)
    by_ordinal = {c["ordinal"]: c for c in result["cells"]}

    populated = by_ordinal[0]  # window0/cap0
    assert populated["trade_count"] == 3
    assert populated["traded_symbol_count"] == 2  # distinct 종목코드: 005930, 005931
    assert populated["winning_count"] == 1
    assert populated["losing_count"] == 1
    assert populated["gross_profit"] == pytest.approx(1000.0)
    assert populated["gross_loss"] == pytest.approx(-500.0)
    assert populated["net_profit"] == pytest.approx(500.0)
    assert populated["win_rate"] == pytest.approx(1 / 3)

    empty_cell = by_ordinal[1]  # window0/cap band1 -- no trades at all
    assert empty_cell["trade_count"] == 0
    assert empty_cell["traded_symbol_count"] is None
    assert empty_cell["win_rate"] is None
    assert empty_cell["gross_profit"] is None
    assert empty_cell["gross_loss"] is None
    assert empty_cell["net_profit"] is None

    totals = result["totals"]
    assert totals["trade_count"] == 3
    assert totals["win_rate"] == pytest.approx(1 / 3)


def test_decompose_cells_missing_profit_columns_entirely_yields_none_not_zero(tmp_path):
    spec = _tick_spec()
    fields = ["종목명", "시가총액", "매수시간"]  # 수익률/수익금 컬럼 자체가 없음

    csv_path = tmp_path / "no_profit_cols.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"종목명": "A", "시가총액": "1000", "매수시간": "20250110090000"})

    result = decompose_cells(csv_path, spec)
    by_ordinal = {c["ordinal"]: c for c in result["cells"]}
    populated = by_ordinal[0]
    assert populated["trade_count"] == 1
    assert populated["gross_profit"] is None
    assert populated["gross_loss"] is None
    assert populated["net_profit"] is None
    # win_rate은 trade_count>0 이므로 None이 아니라 0.0(승리 0건)이어야 한다.
    assert populated["win_rate"] == pytest.approx(0.0)


def test_decompose_cells_missing_required_columns_sends_all_rows_to_unassigned(tmp_path):
    spec = _tick_spec()
    fields = ["종목명"]
    csv_path = tmp_path / "missing_required.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"종목명": "A"})
        writer.writerow({"종목명": "B"})

    result = decompose_cells(csv_path, spec)
    assert result["unassigned"]["count"] == 2
    assert result["unassigned"]["reasons"] == {REASON_MISSING_BUY_TIME: 2}
    assert sum(c["trade_count"] for c in result["cells"]) == 0
    assert result["parity_ok"] is True


# ---------------------------------------------------------------------------
# cells_to_history_evaluations -- 트리 조립 + 검증
# ---------------------------------------------------------------------------


def test_cells_to_history_evaluations_builds_13_conditions_and_validates(tmp_path):
    spec = _tick_spec()
    rows = [_row("A", "005930", "1000", "20250110090000")]
    csv_path = _write_csv(tmp_path / "trades.csv", rows)
    csv_sha = compute_csv_sha256(csv_path)

    result = decompose_cells(csv_path, spec)
    node = cells_to_history_evaluations(result, spec, csv_path, csv_sha)

    assert validate_research_node(node) == []
    assert node["research_id"] == "campaign:wide_seed_v1_stage1"
    assert len(node["stages"]) == 1
    stage = node["stages"][0]
    assert stage["stage_id"] == "stage1_exploratory_full_history"
    assert len(stage["conditions"]) == 13  # 12 리프 셀 + overall 1개

    condition_ids = [c["condition_id"] for c in stage["conditions"]]
    assert len(condition_ids) == len(set(condition_ids))  # 중복 없음

    populated = next(c for c in stage["conditions"] if c["condition_id"].endswith(":cell:00"))
    assert populated["coverage_status"] == "success"
    assert populated["evaluations"][0]["status"] == "success"
    assert populated["evaluations"][0]["metrics"]["trade_count"] == 1.0

    empty_leaf = next(c for c in stage["conditions"] if c["condition_id"].endswith(":cell:01"))
    assert empty_leaf["coverage_status"] == "no_trades"
    assert empty_leaf["evaluations"][0]["metrics"]["trade_count"] == 0.0
    assert empty_leaf["evaluations"][0]["metrics"]["win_rate"] is None

    overall = next(c for c in stage["conditions"] if c["condition_id"].endswith(":overall"))
    assert overall["evaluations"][0]["metrics"]["unassigned_count"] == 0.0
    assert overall["evaluations"][0]["metrics"]["parity_ok"] == 1.0


def test_cells_to_history_evaluations_no_trades_status_when_all_cells_empty(tmp_path):
    spec = _tick_spec()
    csv_path = _write_csv(tmp_path / "empty.csv", [])
    csv_sha = compute_csv_sha256(csv_path)

    result = decompose_cells(csv_path, spec)
    node = cells_to_history_evaluations(result, spec, csv_path, csv_sha)

    assert validate_research_node(node) == []
    assert node["coverage_status"] == "no_trades"
    for condition in node["stages"][0]["conditions"]:
        assert condition["coverage_status"] == "no_trades"


# ---------------------------------------------------------------------------
# publish_stage1 -- roundtrip
# ---------------------------------------------------------------------------


def test_publish_stage1_writes_readable_json_roundtrip(tmp_path):
    spec = _tick_spec()
    rows = [_row("A", "005930", "1000", "20250110090000")]
    csv_path = _write_csv(tmp_path / "trades.csv", rows)
    csv_sha = compute_csv_sha256(csv_path)

    result = decompose_cells(csv_path, spec)
    node = cells_to_history_evaluations(result, spec, csv_path, csv_sha)

    evidence_dir = tmp_path / "evidence"
    target = publish_stage1(node, evidence_dir)

    assert target.exists()
    assert target.name == f"{CAMPAIGN_NAME}_condition_history_v1.json"

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == node
    assert validate_research_node(loaded) == []


def test_parse_buy_hhmmss_min_lane_12_digit():
    """min 레인 YYYYMMDDHHMM(12자리)은 HHMM*100으로 파싱되고 유효성도 검사된다."""
    from cli.stage1_cell_decomposition import _parse_buy_hhmmss
    assert _parse_buy_hhmmss("202504070929") == 92900
    assert _parse_buy_hhmmss(202602271359) == 135900
    assert _parse_buy_hhmmss("202504072461") is None  # 24시/61분 불가
    assert _parse_buy_hhmmss("20250407092959") == 92959  # 14자리 유지
    assert _parse_buy_hhmmss("20250407256161") is None  # 14자리 유효성
