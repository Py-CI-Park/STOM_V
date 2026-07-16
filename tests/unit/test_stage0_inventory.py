"""stage0_inventory 계약 테스트 (G004).

읽기 전용(read-only) Stage-0 재고 빌더에 대한 계약 테스트: 파일명 기반 틱 DB
스캔, 메타데이터-only 분봉 DB 스캔(및 sample_limit>0일 때의 READ-ONLY sqlite
열기), 영수증 결정론, 원자적 기록, `_database` 경로 거부, 그리고 스캔 대상
디렉터리에 대한 쓰기 모드 열기가 전혀 없음을 검증한다.
"""

from __future__ import annotations

import builtins
import sqlite3

import pytest

from cli.stage0_inventory import (
    build_stage0_receipt,
    scan_min_db,
    scan_tick_dbs,
    write_receipt,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _touch(path, size: int = 0) -> None:
    path.write_bytes(b"\x00" * size)


# ---------------------------------------------------------------------------
# scan_tick_dbs
# ---------------------------------------------------------------------------


def test_scan_tick_dbs_parses_dates_from_filenames_only(tmp_path):
    _touch(tmp_path / "stock_tick_20260101.db", size=10)
    _touch(tmp_path / "stock_tick_20260103.db", size=20)
    _touch(tmp_path / "stock_tick_20260102.db", size=5)
    _touch(tmp_path / "not_a_tick_db.txt", size=99)

    result = scan_tick_dbs(tmp_path)

    assert result["dates"] == ["20260101", "20260102", "20260103"]
    assert result["count"] == 3
    assert result["bytes"] == 35
    assert result["min"] == "20260101"
    assert result["max"] == "20260103"


def test_scan_tick_dbs_missing_dir_returns_empty_inventory(tmp_path):
    result = scan_tick_dbs(tmp_path / "does-not-exist")

    assert result == {"dates": [], "count": 0, "bytes": 0, "min": None, "max": None}


def test_scan_tick_dbs_never_opens_sqlite(tmp_path, monkeypatch):
    _touch(tmp_path / "stock_tick_20260101.db", size=10)

    def _forbidden_connect(*args, **kwargs):
        raise AssertionError("scan_tick_dbs must not open sqlite connections")

    monkeypatch.setattr(sqlite3, "connect", _forbidden_connect)

    result = scan_tick_dbs(tmp_path)
    assert result["count"] == 1


# ---------------------------------------------------------------------------
# scan_min_db
# ---------------------------------------------------------------------------


def test_scan_min_db_metadata_only_when_sample_limit_zero(tmp_path, monkeypatch):
    db_path = tmp_path / "stom_min.db"
    _touch(db_path, size=42)

    def _forbidden_connect(*args, **kwargs):
        raise AssertionError("sample_limit=0 must not open sqlite connections")

    monkeypatch.setattr(sqlite3, "connect", _forbidden_connect)

    result = scan_min_db(db_path, sample_limit=0)

    assert result == {"exists": True, "bytes": 42, "tables_sampled": None}


def test_scan_min_db_missing_file(tmp_path):
    result = scan_min_db(tmp_path / "missing.db", sample_limit=1)
    assert result["exists"] is False
    assert result["tables_sampled"] is None


def test_scan_min_db_readonly_sample_counts_tables(tmp_path):
    db_path = tmp_path / "stom_min.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE minute_bars (id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()

    result = scan_min_db(db_path, sample_limit=1)

    assert result["exists"] is True
    assert result["tables_sampled"] == 1


def test_scan_min_db_readonly_open_uses_ro_uri(tmp_path, monkeypatch):
    db_path = tmp_path / "stom_min.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.commit()
    finally:
        conn.close()

    seen_uris = []
    real_connect = sqlite3.connect

    def _spy_connect(uri_str, uri=False, **kwargs):
        seen_uris.append((uri_str, uri))
        return real_connect(uri_str, uri=uri, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _spy_connect)

    scan_min_db(db_path, sample_limit=1)

    assert len(seen_uris) == 1
    uri_str, uri_flag = seen_uris[0]
    assert uri_flag is True
    assert "mode=ro" in uri_str


# ---------------------------------------------------------------------------
# build_stage0_receipt
# ---------------------------------------------------------------------------


def _build(tmp_path, tick_dates=("20260101",), min_exists=True, generated_at="2026-01-01T00:00:00+00:00"):
    tick_dir = tmp_path / "tick"
    tick_dir.mkdir(exist_ok=True)
    for date_str in tick_dates:
        _touch(tick_dir / f"stock_tick_{date_str}.db", size=100)

    min_db = tmp_path / "stom_min.db"
    if min_exists:
        _touch(min_db, size=200)

    return build_stage0_receipt(
        tick_dir,
        min_db,
        boundary_sha="boundary-sha-fixed",
        exit_sha="exit-sha-fixed",
        plan_hashes=["plan-a", "plan-b"],
        generated_at=generated_at,
    )


def test_build_stage0_receipt_shape(tmp_path):
    receipt = _build(tmp_path)

    assert receipt["schemaVersion"] == 1
    assert receipt["kind"] == "stage0-inventory-receipt"
    assert receipt["lanes"]["tick"]["dates"] == ["20260101"]
    assert receipt["lanes"]["min"]["exists"] is True
    assert receipt["boundary_receipt_sha"] == "boundary-sha-fixed"
    assert receipt["exit_receipt_sha"] == "exit-sha-fixed"
    assert receipt["trial_plan_hashes"] == ["plan-a", "plan-b"]
    assert receipt["non_common_history"] is False
    assert isinstance(receipt["receipt_sha"], str) and len(receipt["receipt_sha"]) == 64


def test_build_stage0_receipt_non_common_history_when_min_missing(tmp_path):
    receipt = _build(tmp_path, min_exists=False)
    assert receipt["non_common_history"] is True


def test_build_stage0_receipt_non_common_history_when_no_tick_dates(tmp_path):
    receipt = _build(tmp_path, tick_dates=())
    assert receipt["non_common_history"] is True


def test_build_stage0_receipt_deterministic_for_same_inputs(tmp_path):
    receipt_a = _build(tmp_path)
    receipt_b = _build(tmp_path)
    assert receipt_a["receipt_sha"] == receipt_b["receipt_sha"]


def test_build_stage0_receipt_sha_changes_when_date_added(tmp_path_factory):
    tmp_a = tmp_path_factory.mktemp("stage0_a")
    tmp_b = tmp_path_factory.mktemp("stage0_b")

    receipt_a = _build(tmp_a, tick_dates=("20260101",))
    receipt_b = _build(tmp_b, tick_dates=("20260101", "20260102"))

    assert receipt_a["receipt_sha"] != receipt_b["receipt_sha"]


# ---------------------------------------------------------------------------
# write_receipt
# ---------------------------------------------------------------------------


def test_write_receipt_atomic_and_readable(tmp_path):
    receipt = _build(tmp_path)
    out_path = tmp_path / "out" / "stage0_receipt.json"

    written = write_receipt(receipt, out_path)

    assert written == out_path
    assert out_path.is_file()
    # No leftover temp files in the target directory.
    leftovers = [p for p in out_path.parent.iterdir() if p.name != out_path.name]
    assert leftovers == []


def test_write_receipt_refuses_database_path(tmp_path):
    receipt = _build(tmp_path)
    forbidden = tmp_path / "_database" / "stage0_receipt.json"

    with pytest.raises(ValueError):
        write_receipt(receipt, forbidden)

    assert not forbidden.exists()


def test_write_receipt_refuses_database_path_case_insensitive(tmp_path):
    receipt = _build(tmp_path)
    forbidden = tmp_path / "_DATABASE" / "stage0_receipt.json"

    with pytest.raises(ValueError):
        write_receipt(receipt, forbidden)


def test_no_write_mode_open_against_scanned_tick_dir(tmp_path, monkeypatch):
    """스캔 대상 틱 디렉터리 파일에 대해 쓰기 모드 open이 호출되지 않는지 감사한다."""
    tick_dir = tmp_path / "tick"
    tick_dir.mkdir()
    _touch(tick_dir / "stock_tick_20260101.db", size=10)

    real_open = builtins.open

    def _audited_open(file, mode="r", *args, **kwargs):
        if "w" in mode or "a" in mode or "+" in mode:
            file_str = str(file)
            if str(tick_dir) in file_str:
                raise AssertionError(f"unexpected write-mode open against scanned dir: {file_str!r} ({mode!r})")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _audited_open)

    scan_tick_dbs(tick_dir)


def test_min_coverage_and_notes_drive_honest_flag(tmp_path):
    """min_coverage 선언 시 non_common_history를 정직 계산하고 notes를 생성기가 emit한다."""
    from cli.stage0_inventory import build_stage0_receipt
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    (db_dir / "stock_tick_20220323.db").write_bytes(b"")
    (db_dir / "stock_tick_20260227.db").write_bytes(b"")
    min_db = tmp_path / "stock_min_back.db"
    min_db.write_bytes(b"x")
    receipt = build_stage0_receipt(
        db_dir, min_db, "b" * 64, "e" * 64, ["t1"],
        generated_at="2026-07-16T00:00:00+00:00",
        min_coverage={"min": "20250407", "max": "20260227", "source": "lattice docs"},
        notes={"data_root_note": "wt-dev/_database"},
    )
    assert receipt["non_common_history"] is True
    assert receipt["lanes"]["min"]["coverage"]["min"] == "20250407"
    assert receipt["notes"]["data_root_note"] == "wt-dev/_database"
    same = build_stage0_receipt(
        db_dir, min_db, "b" * 64, "e" * 64, ["t1"],
        generated_at="2026-07-16T00:00:00+00:00",
        min_coverage={"min": "20220323", "max": "20260227", "source": "동일 범위 가정"},
    )
    assert same["non_common_history"] is False
