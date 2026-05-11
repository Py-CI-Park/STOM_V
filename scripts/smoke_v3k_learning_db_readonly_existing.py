from __future__ import annotations

import json
import sqlite3
from contextlib import closing
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from apply_v3k_shadow_db import expanded_table_names
from init_v3k_shadow_db import LEARNING_DBS, create_table_sql
from strategy.v3k_analyzer_adapter import (
    ANALYZER_MODULE_CONTRACTS,
    FLAG_BACKTEST_LEARNING,
    LEARNING_DB_CONTRACTS,
    LearningLoadRequest,
    V3KLearningDataAdapter,
)

STRATEGY_GUBUN = "stock"
SMOKE_PREFIX = "_v3kshadow_smokeA_"
SMOKE_CODE = f"{SMOKE_PREFIX}CODE"
BACKTEST_DATE = 20260509
ELIGIBLE_LAST_UPDATE = 20260508
OLDER_ELIGIBLE_LAST_UPDATE = 20260507
EQUAL_LAST_UPDATE = BACKTEST_DATE
FUTURE_LAST_UPDATE = 20260510


def learning_requests() -> tuple[LearningLoadRequest, ...]:
    requests: list[LearningLoadRequest] = []
    for kind in LEARNING_DB_CONTRACTS:
        tick_modes = (False,) if kind == "candle_pattern" else (True, False)
        for is_tick in tick_modes:
            requests.append(
                LearningLoadRequest(
                    kind=kind,
                    code=SMOKE_CODE,
                    backtest_date=BACKTEST_DATE,
                    strategy_gubun=STRATEGY_GUBUN,
                    is_tick=is_tick,
                )
            )
    return tuple(requests)


def enabled_flags(kind: str) -> dict[str, bool]:
    contract = ANALYZER_MODULE_CONTRACTS[kind]
    return {
        FLAG_BACKTEST_LEARNING: True,
        contract.feature_flag: True,
    }


def table_schema_for_request(request: LearningLoadRequest) -> dict[str, Any]:
    contract = LEARNING_DB_CONTRACTS[request.kind]
    db_spec = LEARNING_DBS[contract.db_name]
    expected_table = contract.table_name(request.strategy_gubun, request.is_tick)
    for table_template, table in db_spec["tables"].items():
        for table_name in expanded_table_names(table_template, request.strategy_gubun):
            if table_name == expected_table:
                return table
    raise AssertionError(f"{request.kind}: schema not found for {expected_table}")


def column_name(column_sql: str) -> str:
    return column_sql.split()[0]


def column_names(table: dict[str, Any]) -> list[str]:
    return [column_name(column) for column in table["columns"]]


def row_value(column: str, *, row_no: int, last_update: int, request: LearningLoadRequest) -> Any:
    if column == "code":
        return SMOKE_CODE
    if column == "last_update":
        return last_update
    if column == "confidence_score":
        if last_update == ELIGIBLE_LAST_UPDATE:
            return 0.91
        if last_update == OLDER_ELIGIBLE_LAST_UPDATE:
            return 0.81
        return 0.99
    if column == "sample_count":
        return 10 + row_no
    if column == "setting_hash":
        return f"{SMOKE_PREFIX}setting_{request.kind}_{'tick' if request.is_tick else 'min'}_{row_no}"
    if column == "pattern_name":
        return f"{SMOKE_PREFIX}pattern"
    if column in {"market", "analysis_period", "rate_threshold", "is_tick"}:
        if column == "is_tick":
            return int(request.is_tick)
        return 1
    if column.endswith("_level"):
        return float(row_no)
    if column.endswith("_strength"):
        return float(row_no) / 10
    if column.startswith("avg_") or column.startswith("max_") or column.startswith("min_"):
        return float(row_no)
    if column.startswith("std_"):
        return float(row_no) / 100
    if column in {"level_stop", "level_take", "win_rate"}:
        return float(row_no) / 10
    return f"{SMOKE_PREFIX}{column}_{row_no}"


def fixture_rows(request: LearningLoadRequest, table: dict[str, Any]) -> list[dict[str, Any]]:
    updates = [
        ELIGIBLE_LAST_UPDATE,
        OLDER_ELIGIBLE_LAST_UPDATE,
        EQUAL_LAST_UPDATE,
        FUTURE_LAST_UPDATE,
    ]
    rows = []
    for row_no, last_update in enumerate(updates, start=1):
        rows.append(
            {
                column: row_value(column, row_no=row_no, last_update=last_update, request=request)
                for column in column_names(table)
            }
        )
    return rows


def insert_sql(table_name: str, row: dict[str, Any]) -> str:
    columns = ", ".join(row)
    placeholders = ", ".join(f":{column}" for column in row)
    return f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"


def create_fixture_table(base_dir: Path, request: LearningLoadRequest) -> tuple[Path, str]:
    contract = LEARNING_DB_CONTRACTS[request.kind]
    table_name = contract.table_name(request.strategy_gubun, request.is_tick)
    table = table_schema_for_request(request)
    db_path = base_dir / contract.db_name
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rows = fixture_rows(request, table)
    with closing(sqlite3.connect(db_path)) as con:
        con.executescript(create_table_sql(table_name, table))
        con.executemany(insert_sql(table_name, rows[0]), rows)
        con.commit()
    return db_path, table_name


def count_rows(db_path: Path, table_name: str) -> int:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as con:
        return int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def assert_readonly_write_rejected(db_path: Path, table_name: str, sample_row: dict[str, Any]) -> None:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as con:
            con.execute(insert_sql(table_name, sample_row), sample_row)
    except sqlite3.OperationalError as exc:
        if "readonly" in str(exc).lower() or "read-only" in str(exc).lower():
            return
        raise
    raise AssertionError(f"{table_name}: read-only connection accepted a write")


def actual_shadow_snapshot() -> dict[str, Any]:
    shadow_dir = ROOT / "_database_v3k_shadow"
    if not shadow_dir.exists():
        return {"exists": False}

    meta_db = shadow_dir / "v3k_meta.db"
    code_meta_db = shadow_dir / "v3k_code_meta.db"
    snapshot: dict[str, Any] = {"exists": True}
    with closing(sqlite3.connect(meta_db.resolve().as_uri() + "?mode=ro", uri=True)) as con:
        snapshot["feature_flags"] = con.execute("SELECT COUNT(*) FROM v3k_feature_flags").fetchone()[0]
        manifest_rows = con.execute(
            "SELECT db_name, table_name, schema_hash FROM v3k_schema_manifest"
        ).fetchall()
        snapshot["schema_manifest"] = len(manifest_rows)
        snapshot["schema_hashes"] = {
            f"{db_name}:{table_name}": schema_hash
            for db_name, table_name, schema_hash in manifest_rows
        }
    with closing(sqlite3.connect(code_meta_db.resolve().as_uri() + "?mode=ro", uri=True)) as con:
        snapshot["listed_shares"] = con.execute("SELECT COUNT(*) FROM v3k_listed_shares").fetchone()[0]
    return snapshot


def assert_manifest_hashes_match_snapshot(snapshot: dict[str, Any]) -> None:
    if not snapshot.get("exists"):
        print("actual shadow DB absent; manifest hash comparison skipped")
        return
    manifest_path = ROOT / ".omx" / "reports" / "v3k-shadow-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_hashes: dict[str, str] = {}
    for db_name, db_spec in manifest["dbs"].items():
        for table_template, table in db_spec["tables"].items():
            for table_name in expanded_table_names(table_template, STRATEGY_GUBUN):
                expected_hashes[f"{db_name}:{table_name}"] = table["schema_hash"]

    actual_hashes = snapshot["schema_hashes"]
    missing = sorted(set(expected_hashes) - set(actual_hashes))
    mismatched = sorted(
        key
        for key, expected in expected_hashes.items()
        if key in actual_hashes and actual_hashes[key] != expected
    )
    if missing or mismatched:
        raise AssertionError(
            f"actual shadow schema manifest mismatch: missing={missing}, mismatched={mismatched}"
        )
    if snapshot["feature_flags"] != 0 or snapshot["listed_shares"] != 0:
        raise AssertionError(
            "actual shadow DB should remain data-empty for feature/listed-share rows: "
            f"feature_flags={snapshot['feature_flags']} listed_shares={snapshot['listed_shares']}"
        )


def assert_disabled_existing_db_noop(base_dir: Path, request: LearningLoadRequest) -> None:
    result = V3KLearningDataAdapter(base_dir=base_dir).load_before_backtest(request)
    if result.rows:
        raise AssertionError(f"{request.kind}: disabled existing DB path returned rows")
    if "disabled" not in " ".join(result.diagnostics):
        raise AssertionError(f"{request.kind}: disabled diagnostic missing: {result.diagnostics}")


def assert_missing_db_noop(request: LearningLoadRequest) -> None:
    missing_dir = ROOT / "_database_v3k_missing_smoke"
    enabled_request = LearningLoadRequest(
        kind=request.kind,
        code=request.code,
        backtest_date=request.backtest_date,
        strategy_gubun=request.strategy_gubun,
        is_tick=request.is_tick,
        feature_flags=enabled_flags(request.kind),
    )
    result = V3KLearningDataAdapter(base_dir=missing_dir).load_before_backtest(enabled_request)
    if result.rows:
        raise AssertionError(f"{request.kind}: missing DB path returned rows")
    if "missing" not in " ".join(result.diagnostics):
        raise AssertionError(f"{request.kind}: missing diagnostic missing: {result.diagnostics}")
    if result.db_path.exists():
        raise AssertionError(f"{request.kind}: missing DB path was created: {result.db_path}")


def assert_enabled_existing_db_read(base_dir: Path, request: LearningLoadRequest) -> None:
    enabled_request = LearningLoadRequest(
        kind=request.kind,
        code=request.code,
        backtest_date=request.backtest_date,
        strategy_gubun=request.strategy_gubun,
        is_tick=request.is_tick,
        feature_flags=enabled_flags(request.kind),
    )
    result = V3KLearningDataAdapter(base_dir=base_dir).load_before_backtest(enabled_request)
    if len(result.rows) != 2:
        raise AssertionError(f"{request.kind}: expected 2 eligible rows, got {result.rows}")
    last_updates = [row["last_update"] for row in result.rows]
    if last_updates != [ELIGIBLE_LAST_UPDATE, OLDER_ELIGIBLE_LAST_UPDATE]:
        raise AssertionError(f"{request.kind}: cutoff/order mismatch: {last_updates}")
    if any(row["last_update"] >= BACKTEST_DATE for row in result.rows):
        raise AssertionError(f"{request.kind}: future/equal leakage found: {result.rows}")
    if "read-only learning load executed" not in result.diagnostics:
        raise AssertionError(f"{request.kind}: read-only diagnostic missing: {result.diagnostics}")

    limited_request = LearningLoadRequest(
        kind=request.kind,
        code=request.code,
        backtest_date=request.backtest_date,
        strategy_gubun=request.strategy_gubun,
        is_tick=request.is_tick,
        feature_flags=enabled_flags(request.kind),
        limit=1,
    )
    limited = V3KLearningDataAdapter(base_dir=base_dir).load_before_backtest(limited_request)
    if len(limited.rows) != 1 or limited.rows[0]["last_update"] != ELIGIBLE_LAST_UPDATE:
        raise AssertionError(f"{request.kind}: limit=1 did not return newest eligible row: {limited.rows}")


def main() -> int:
    shadow_before = actual_shadow_snapshot()
    assert_manifest_hashes_match_snapshot(shadow_before)

    with tempfile.TemporaryDirectory(prefix="v3k_phase_b_fixture_") as tmp:
        fixture_dir = Path(tmp)
        for request in learning_requests():
            db_path, table_name = create_fixture_table(fixture_dir, request)
            table = table_schema_for_request(request)
            rows = fixture_rows(request, table)
            before_count = count_rows(db_path, table_name)

            assert_disabled_existing_db_noop(fixture_dir, request)
            assert_missing_db_noop(request)
            assert_enabled_existing_db_read(fixture_dir, request)
            assert_readonly_write_rejected(db_path, table_name, rows[0])

            after_count = count_rows(db_path, table_name)
            if after_count != before_count:
                raise AssertionError(
                    f"{request.kind}: fixture row count changed: {before_count} -> {after_count}"
                )
            print(
                "read-only existing learning DB ok: "
                f"{request.kind} {'tick' if request.is_tick else 'min'}"
            )

    shadow_after = actual_shadow_snapshot()
    if shadow_after != shadow_before:
        raise AssertionError(f"actual shadow DB changed: before={shadow_before} after={shadow_after}")

    print("candle_pattern tick skipped: no tick learning DB contract")
    print("v3k Phase B read-only learning DB smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
