"""alpha_lab.distill.ledger_wiring 단위 테스트 — P5 Phase 0 챔피언 원장 배선.

실DB 불필요(전부 tmp_path 합성 CSV). 실행:
    python -m pytest tests/unit/test_alpha_distill.py -q

합성 CSV는 게이트런 per-trade CSV의 실측 37컬럼 스키마(utf-8-sig,
backtest/back_static.py 헤더)를 그대로 미러링한다. 실측 근거:
  - wt-alpha  backtest/csv/stock_bt___AUTO_TMP__*.csv (매수시간 12자리 min 형식)
  - wt-dev    backtest/csv/stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_*.csv
              (매수시간 14자리 tick 형식, R_MFE/R_MAE 존재, 종목코드·전략명 컬럼 부재)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from alpha_lab.distill.ledger_wiring import (
    GATE_CSV_B_COLUMNS,
    GATE_CSV_COLUMNS,
    GATE_CSV_R_COLUMNS,
    GATE_CSV_S_COLUMNS,
    LEDGER_SCHEMA_VERSION,
    dedup_records,
    identity,
    normalize_trade_row,
    read_ledger,
    scan_csvs,
    strategy_from_csv_name,
    write_ledger,
)

# ---------------------------------------------------------------------------
# 합성 행 빌더 — 실측 37컬럼 순서 그대로.
# ---------------------------------------------------------------------------

# 실측 매도조건 원문 형태(쉼표·따옴표 포함) — CSV 인용 왕복 검증용.
_SELL_CLAUSE = '        if 5 < 최고수익률 and 현재가N(1) >= 이동평균(60, 1) and 이동평균(60) > 현재가:'


def _gate_row(
    name: str,
    buy_time: str,
    return_pct: str,
    *,
    mfe: str = "6.84",
    mae: str = "-0.96",
) -> list:
    """실측 37컬럼 순서의 합성 거래행 1개 (전부 문자열 — csv 왕복 그대로)."""
    base = [
        name, "1641", buy_time, "20250103090829", "266",
        "6650", "7050", "997500", "1055307", return_pct,
        "57807", "57807", _SELL_CLAUSE, "",
    ]
    b_cols = [
        "6640.0", "7.97", "8320.0", "-50945751800.0", "174.42",
        "1545.0", "5.55", "82.48", "28986.0", "84706.0",
        "90403", "0", "0", "0",
    ]
    s_cols = ["7050.0", "14.63", "162.75", "59320.0", "79366.0"]
    r_cols = ["6.84", "-0.96", mfe, mae]
    row = base + b_cols + s_cols + r_cols
    assert len(row) == len(GATE_CSV_COLUMNS)
    return row


def _row_as_mapping(row: list) -> dict:
    return dict(zip(GATE_CSV_COLUMNS, row))


def _write_gate_csv(path: Path, rows: list) -> None:
    """게이트런 CSV 재현 — utf-8-sig(BOM), 실측 헤더 그대로."""
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(GATE_CSV_COLUMNS)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# 봉인 스키마 — 엔진 원천(analyze.py / trade_ledger.py)과의 대조(드리프트 방지).
# ---------------------------------------------------------------------------

def test_columns_match_engine_sources():
    """봉인된 게이트런 스키마(37컬럼)와 현재 엔진 컬럼의 계약.

    B_* 는 **등가가 아니라 접두**여야 한다. QSP1 P1(737d3cde)이 엔진 B_* 를
    14 → 31 로 확장했는데, 그건 **추가**이지 기존 열의 순서·의미 변경이 아니다
    (back_static: 구버전 행은 normalize_trade_result_rows 가 0-패딩).
    등가를 요구하면 엔진이 열을 하나 더 기록할 때마다 과거 원장이 깨진 것처럼
    보인다 — 실제로 지켜야 할 불변식은 "봉인된 열이 같은 자리에 같은 의미로
    남아 있는가"다.
    """
    from ai_strategy_loop.autopsy.analyze import B_COLUMNS, MAE_COLUMN, MFE_COLUMN
    from ai_strategy_loop.autopsy.trade_ledger import R_COLUMNS, S_COLUMNS

    sealed_b = tuple(GATE_CSV_B_COLUMNS)
    assert sealed_b == tuple(B_COLUMNS)[: len(sealed_b)], (
        "봉인된 B_* 열이 현재 엔진 열의 접두가 아니다 — 열 순서/의미가 바뀌었다"
    )
    assert tuple(GATE_CSV_S_COLUMNS) == tuple(S_COLUMNS)
    assert tuple(GATE_CSV_R_COLUMNS) == tuple(R_COLUMNS)
    assert GATE_CSV_R_COLUMNS[0] == MFE_COLUMN
    assert GATE_CSV_R_COLUMNS[1] == MAE_COLUMN
    assert len(GATE_CSV_COLUMNS) == 37


def test_gate_csv_columns_head_matches_measured_header():
    # 실측 헤더 선두 14컬럼(기본 거래 컬럼) 순서 봉인.
    assert GATE_CSV_COLUMNS[:14] == (
        "종목명", "시가총액", "매수시간", "매도시간", "보유시간",
        "매수가", "매도가", "매수금액", "매도금액", "수익률",
        "수익금", "수익금합계", "매도조건", "추가매수시간",
    )


# ---------------------------------------------------------------------------
# strategy_from_csv_name — 파일명 → 전략명 파생.
# ---------------------------------------------------------------------------

def test_strategy_from_csv_name_gate_run():
    name = "stock_bt_GATE_rr8_12_turnover_min_902_1_5_B_20260701234829.csv"
    assert strategy_from_csv_name(name) == "GATE_rr8_12_turnover_min_902_1_5_B"


def test_strategy_from_csv_name_auto_tmp():
    name = (
        "stock_bt___AUTO_TMP__Auto_B_TestRun_20260315_"
        "1773540931561_0_20260315111609.csv"
    )
    assert strategy_from_csv_name(name) == (
        "__AUTO_TMP__Auto_B_TestRun_20260315_1773540931561_0"
    )


def test_strategy_from_csv_name_fallback_is_stem():
    assert strategy_from_csv_name("champion_trades.csv") == "champion_trades"
    assert strategy_from_csv_name("stock_bt_only_prefix.csv") == "only_prefix"


# ---------------------------------------------------------------------------
# normalize_trade_row.
# ---------------------------------------------------------------------------

def test_normalize_tick_row_full():
    row = _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8"))
    rec = normalize_trade_row(row, source="GATE_synth_champ_B")
    assert rec is not None
    assert rec["schema_version"] == LEDGER_SCHEMA_VERSION
    assert rec["source"] == "GATE_synth_champ_B"
    assert rec["전략명"] == "GATE_synth_champ_B"
    assert rec["종목코드"] == "아톤"          # 실측: 종목코드 컬럼 부재 → 종목명 폴백
    assert rec["진입일자"] == "20250103"
    assert rec["진입시각"] == "090403"
    assert rec["수익률"] == pytest.approx(5.8)
    # B_*·R_MFE/R_MAE 있으면 통과(float 강제).
    assert rec["B_체결강도"] == pytest.approx(174.42)
    assert rec["B_시분초"] == pytest.approx(90403.0)
    assert rec["R_MFE"] == pytest.approx(6.84)
    assert rec["R_MAE"] == pytest.approx(-0.96)
    assert rec["R_매수후최고수익률"] == pytest.approx(6.84)
    # 문자 passthrough — 매도조건은 절 어트리뷰션 파싱용 원문 보존(공백 포함).
    assert rec["종목명"] == "아톤"
    assert rec["매도조건"] == _SELL_CLAUSE


def test_normalize_min_row_12_digit_buy_time():
    row = _row_as_mapping(_gate_row("오파스넷", "202504071000", "2.84"))
    rec = normalize_trade_row(row, source="S")
    assert rec is not None
    assert rec["진입일자"] == "20250407"
    assert rec["진입시각"] == "100000"      # HHMM → HHMMSS(+'00') 정규화


def test_normalize_row_strategy_column_precedence():
    row = _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8"))
    row = {**row, "전략명": "row_strategy"}
    rec = normalize_trade_row(row, source="file_strategy")
    assert rec is not None
    assert rec["전략명"] == "row_strategy"
    assert rec["source"] == "file_strategy"


def test_normalize_drops_bad_rows():
    good = _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8"))
    # 수익 지표 결측 → drop.
    assert normalize_trade_row({**good, "수익률": ""}, source="S") is None
    assert normalize_trade_row({**good, "수익률": "abc"}, source="S") is None
    # 매수시간 자릿수 불량(13자리) → drop.
    assert normalize_trade_row({**good, "매수시간": "2025010309040"}, source="S") is None
    # 종목 식별자 전무 → drop.
    no_name = {k: v for k, v in good.items() if k != "종목명"}
    assert normalize_trade_row(no_name, source="S") is None


def test_normalize_prefers_explicit_code_over_name():
    row = _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8"))
    row = {**row, "종목코드": "096240"}
    rec = normalize_trade_row(row, source="S")
    assert rec is not None
    assert rec["종목코드"] == "096240"
    assert rec["종목명"] == "아톤"


def test_normalize_source_contract():
    row = _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8"))
    with pytest.raises(ValueError):
        normalize_trade_row(row, source="")
    with pytest.raises(ValueError):
        normalize_trade_row(row, source="   ")
    with pytest.raises(ValueError):
        normalize_trade_row("not-a-mapping", source="S")  # type: ignore[arg-type]


def test_normalize_reingest_of_normalized_record():
    """read_ledger 산출 레코드를 재정규화해도 identity 불변(진입일자/진입시각 직접 필드)."""
    row = _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8"))
    rec = normalize_trade_row(row, source="S")
    assert rec is not None
    again = normalize_trade_row(
        {k: v for k, v in rec.items() if k != "매수시간"}, source="S"
    )
    assert again is not None
    assert identity(again) == identity(rec)


# ---------------------------------------------------------------------------
# identity / dedup_records.
# ---------------------------------------------------------------------------

def test_identity_tuple():
    row = _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8"))
    rec = normalize_trade_row(row, source="GATE_synth_champ_B")
    assert identity(rec) == ("GATE_synth_champ_B", "아톤", "20250103", "090403")


def test_identity_missing_field_raises():
    with pytest.raises(ValueError):
        identity({"전략명": "S", "종목코드": "아톤", "진입일자": "20250103"})


def test_dedup_first_wins_and_count():
    def rec(name: str, tm: str, ret: str) -> dict:
        row = _row_as_mapping(_gate_row(name, tm, ret))
        out = normalize_trade_row(row, source="S")
        assert out is not None
        return out

    first = rec("아톤", "20250103090403", "5.8")
    dup_of_first = rec("아톤", "20250103090403", "-9.9")  # 동일 identity, 값 상이
    other = rec("테스트A", "20250106090100", "0.5")
    records = [first, dup_of_first, other, dict(first), dict(other)]
    unique, dup_count = dedup_records(records)
    assert dup_count == 3
    assert [identity(r) for r in unique] == [identity(first), identity(other)]
    # first-wins: 나중 중복의 값이 아닌 최초 값 유지.
    assert unique[0]["수익률"] == pytest.approx(5.8)
    # 입력 불변(원본 리스트 훼손 금지).
    assert len(records) == 5


# ---------------------------------------------------------------------------
# write_ledger / read_ledger — JSONL 왕복.
# ---------------------------------------------------------------------------

def test_write_read_roundtrip(tmp_path):
    rows = [
        _row_as_mapping(_gate_row("아톤", "20250103090403", "5.8")),
        _row_as_mapping(_gate_row("테스트A", "202501061000", "-1.2")),
    ]
    records = [normalize_trade_row(r, source="S") for r in rows]
    assert all(r is not None for r in records)
    out = tmp_path / "nested" / "champion_ledger.jsonl"
    written = write_ledger(records, out)
    assert written == 2
    loaded = read_ledger(out)
    assert loaded == records
    # JSONL 형식: 한 줄 = 한 레코드, 유효 JSON.
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["종목코드"] == "아톤"


def test_read_ledger_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_ledger(tmp_path / "absent.jsonl")


# ---------------------------------------------------------------------------
# scan_csvs — 명시 경로 스캔 + dedup 통합 흐름 (합성 CSV 2벌, 중복 3건).
# ---------------------------------------------------------------------------

def _build_two_gate_csvs(tmp_path: Path) -> tuple[Path, Path]:
    """같은 전략의 게이트런 2회분 — CSV B에 A와 동일 거래 3건 재등장."""
    csv_a = tmp_path / "stock_bt_GATE_synth_champ_B_20260628014938.csv"
    csv_b = tmp_path / "stock_bt_GATE_synth_champ_B_20260628095000.csv"
    shared = [
        _gate_row("아톤", "20250103090403", "5.8"),
        _gate_row("테스트A", "20250106090100", "0.5"),
        _gate_row("테스트B", "20250106092230", "2.84"),
    ]
    _write_gate_csv(csv_a, shared + [_gate_row("오파스넷", "20250103091000", "-1.2")])
    _write_gate_csv(
        csv_b,
        shared
        + [
            _gate_row("신규C", "202501071005", "1.1"),   # 12자리 min 형식
            _gate_row("신규D", "20250107091533", "-0.5"),
            _gate_row("불량행", "20250107091534", ""),    # 수익률 결측 → dropped
        ],
    )
    return csv_a, csv_b


def test_scan_csvs_two_files_dedup_roundtrip(tmp_path):
    csv_a, csv_b = _build_two_gate_csvs(tmp_path)
    records, report = scan_csvs([csv_a, csv_b])

    assert report["total_rows"] == 10
    assert report["kept"] == 9
    assert report["dropped"] == 1
    assert [f["source"] for f in report["files"]] == [
        "GATE_synth_champ_B", "GATE_synth_champ_B",
    ]
    assert report["files"][0]["path"] == str(csv_a)
    assert report["files"][1]["rows"] == 6
    assert report["files"][1]["dropped"] == 1

    # scan 단계는 정규화만 — dedup은 별도 함수(중복 3건 정확 검출).
    unique, dup_count = dedup_records(records)
    assert dup_count == 3
    assert len(unique) == 6
    assert all(r["전략명"] == "GATE_synth_champ_B" for r in unique)

    # 12자리 min 형식 행의 시각 정규화 확인.
    by_code = {r["종목코드"]: r for r in unique}
    assert by_code["신규C"]["진입일자"] == "20250107"
    assert by_code["신규C"]["진입시각"] == "100500"

    # write → read 왕복 동등.
    out = tmp_path / "ledger.jsonl"
    assert write_ledger(unique, out) == 6
    assert read_ledger(out) == unique


def test_scan_csvs_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_csvs([tmp_path / "no_such.csv"])


def test_scan_csvs_requires_sequence_of_paths():
    with pytest.raises(ValueError):
        scan_csvs("not-a-sequence-of-paths")  # type: ignore[arg-type]
