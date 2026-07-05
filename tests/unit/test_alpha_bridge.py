"""alpha_lab.bridge 단위 테스트 — 전략 DB 등록(INSERT-only) + provenance 영수증.

전부 tmp_path 사기(fake) 전략 DB로만 검증한다. 실 전략 DB(_database/strategy.db)
는 절대 접근하지 않는다. 사기 DB 스키마는 utility/database_check.py 실측 DDL을
그대로 미러: CREATE TABLE "stockbuy" ( "index" TEXT, "전략코드" TEXT ) + name 인덱스.

실행: python -m pytest tests/unit/test_alpha_bridge.py -q
"""

import copy
import datetime as dt
import sqlite3

import pytest

from alpha_lab.bridge import append_receipt, read_receipts, register_conditions
from alpha_lab.bridge.receipts import ALLOWED_SOURCE_KINDS
from alpha_lab.bridge.registrar import NAME_PREFIX

NOW = dt.datetime(2026, 7, 5, 12, 0, 0)

SEED_ROWS = {
    "stockbuy": [("기존매수전략", "if 등락율 > 1: 매수")],
    "stocksell": [("기존매도전략", "if 수익률 > 2: 매도")],
}


def _make_fake_strategy_db(path) -> None:
    """실측 DDL 미러로 사기 전략 DB를 만들고 기존(비 ALP_) 행을 시드한다."""
    con = sqlite3.connect(str(path))
    try:
        con.execute('CREATE TABLE "stockbuy" ( "index" TEXT, "전략코드" TEXT )')
        con.execute('CREATE INDEX "ix_stockbuy_index"ON "stockbuy" ("index")')
        con.execute('CREATE TABLE "stocksell" ( "index" TEXT, "전략코드" TEXT )')
        con.execute('CREATE INDEX "ix_stocksell_index" ON "stocksell" ("index")')
        for table, rows in SEED_ROWS.items():
            for name, code in rows:
                con.execute(
                    'INSERT INTO "%s" ("index", "전략코드") VALUES (?, ?)' % table,
                    (name, code),
                )
        con.commit()
    finally:
        con.close()


def _all_rows(db_path, table: str) -> list:
    con = sqlite3.connect(str(db_path))
    try:
        sql = 'SELECT "index", "전략코드" FROM "%s" ORDER BY rowid' % table
        return con.execute(sql).fetchall()
    finally:
        con.close()


def _item(name: str = "ALP_P1_leaf_001", **overrides) -> dict:
    base = {
        "name": name,
        "buy_expr": "if 등락율 > 2 and 체결강도 > 120: 매수",
        "sell_expr": "if 수익률 > 3 or 수익률 < -2: 매도",
        "meta": {"origin": "P1", "leaf_id": 7},
    }
    return {**base, **overrides}


@pytest.fixture()
def fake_db(tmp_path):
    db_path = tmp_path / "strategy.db"
    _make_fake_strategy_db(db_path)
    return db_path


@pytest.fixture()
def backup_dir(tmp_path):
    return tmp_path / "backups"


class TestNamePrefixEnforcement:
    def test_rejects_name_without_prefix(self, fake_db, backup_dir):
        with pytest.raises(ValueError):
            register_conditions(
                fake_db, [_item(name="P1_leaf_001")],
                backup_dir=backup_dir, now=NOW,
            )

    def test_rejects_mixed_batch_before_any_write(self, fake_db, backup_dir):
        """배치에 위반 1건이라도 있으면 전체 거부 — DB·백업 모두 미발생."""
        before_buy = _all_rows(fake_db, "stockbuy")
        with pytest.raises(ValueError):
            register_conditions(
                fake_db,
                [_item(), _item(name="BAD_name")],
                backup_dir=backup_dir, now=NOW,
            )
        assert _all_rows(fake_db, "stockbuy") == before_buy
        assert not backup_dir.exists() or not list(backup_dir.iterdir())

    def test_rejects_duplicate_names_in_batch(self, fake_db, backup_dir):
        with pytest.raises(ValueError):
            register_conditions(
                fake_db, [_item(), _item()],
                backup_dir=backup_dir, now=NOW,
            )

    def test_rejects_empty_exprs(self, fake_db, backup_dir):
        with pytest.raises(ValueError):
            register_conditions(
                fake_db, [_item(buy_expr="")],
                backup_dir=backup_dir, now=NOW,
            )
        with pytest.raises(ValueError):
            register_conditions(
                fake_db, [_item(sell_expr=None)],
                backup_dir=backup_dir, now=NOW,
            )

    def test_missing_db_file_raises(self, tmp_path, backup_dir):
        with pytest.raises(FileNotFoundError):
            register_conditions(
                tmp_path / "no_such.db", [_item()],
                backup_dir=backup_dir, now=NOW,
            )


class TestRegisterInserts:
    def test_inserts_pair_into_both_tables(self, fake_db, backup_dir):
        item = _item()
        result = register_conditions(
            fake_db, [item], backup_dir=backup_dir, now=NOW,
        )
        assert [entry["name"] for entry in result["inserted"]] == [item["name"]]
        assert result["conflicts"] == []
        assert (item["name"], item["buy_expr"]) in _all_rows(fake_db, "stockbuy")
        assert (item["name"], item["sell_expr"]) in _all_rows(fake_db, "stocksell")

    def test_result_shape(self, fake_db, backup_dir):
        result = register_conditions(
            fake_db, [_item()], backup_dir=backup_dir, now=NOW,
        )
        assert set(result.keys()) == {"inserted", "conflicts", "backup_path"}
        entry = result["inserted"][0]
        assert entry["tables"] == ["stockbuy", "stocksell"]
        assert len(entry["buy_sha256"]) == 64
        assert len(entry["sell_sha256"]) == 64
        assert entry["meta"] == {"origin": "P1", "leaf_id": 7}


class TestBackup:
    def test_backup_created_before_write_with_prewrite_bytes(
        self, fake_db, backup_dir,
    ):
        before_bytes = fake_db.read_bytes()
        result = register_conditions(
            fake_db, [_item()], backup_dir=backup_dir, now=NOW,
        )
        backup_path = result["backup_path"]
        assert backup_path is not None
        from pathlib import Path

        backup = Path(backup_path)
        assert backup.exists()
        assert backup.parent == backup_dir
        assert backup.read_bytes() == before_bytes
        assert fake_db.read_bytes() != before_bytes

    def test_no_backup_when_nothing_to_insert(self, fake_db, backup_dir):
        register_conditions(fake_db, [_item()], backup_dir=backup_dir, now=NOW)
        result2 = register_conditions(
            fake_db, [_item()], backup_dir=backup_dir, now=NOW,
        )
        assert result2["backup_path"] is None
        assert len(list(backup_dir.iterdir())) == 1


class TestIdempotency:
    def test_rerun_inserts_zero_and_reports_conflicts(self, fake_db, backup_dir):
        item = _item()
        first = register_conditions(
            fake_db, [item], backup_dir=backup_dir, now=NOW,
        )
        assert len(first["inserted"]) == 1
        rows_after_first = {
            table: _all_rows(fake_db, table) for table in ("stockbuy", "stocksell")
        }
        second = register_conditions(
            fake_db, [item], backup_dir=backup_dir, now=NOW,
        )
        assert second["inserted"] == []
        assert [c["name"] for c in second["conflicts"]] == [item["name"]]
        for table in ("stockbuy", "stocksell"):
            assert _all_rows(fake_db, table) == rows_after_first[table]


class TestConflictReporting:
    def test_partial_existing_name_blocks_whole_pair(self, fake_db, backup_dir):
        """이름이 한쪽 테이블에만 있어도 쌍 전체를 스킵(부분 삽입 금지)."""
        name = "ALP_P2_cell_009"
        con = sqlite3.connect(str(fake_db))
        con.execute(
            'INSERT INTO "stockbuy" ("index", "전략코드") VALUES (?, ?)',
            (name, "선점된 코드"),
        )
        con.commit()
        con.close()
        result = register_conditions(
            fake_db, [_item(name=name)], backup_dir=backup_dir, now=NOW,
        )
        assert result["inserted"] == []
        conflict = result["conflicts"][0]
        assert conflict["name"] == name
        assert conflict["reason"] == "name_exists"
        assert conflict["tables"] == ["stockbuy"]
        sell_names = [row[0] for row in _all_rows(fake_db, "stocksell")]
        assert name not in sell_names

    def test_mixed_batch_inserts_only_new(self, fake_db, backup_dir):
        old = _item(name="ALP_old")
        register_conditions(fake_db, [old], backup_dir=backup_dir, now=NOW)
        new = _item(name="ALP_new")
        result = register_conditions(
            fake_db, [old, new], backup_dir=backup_dir, now=NOW,
        )
        assert [e["name"] for e in result["inserted"]] == ["ALP_new"]
        assert [c["name"] for c in result["conflicts"]] == ["ALP_old"]


class TestInsertOnly:
    def test_existing_rows_never_modified(self, fake_db, backup_dir):
        before = {
            table: _all_rows(fake_db, table) for table in ("stockbuy", "stocksell")
        }
        register_conditions(
            fake_db,
            [_item(), _item(name="ALP_second", meta=None)],
            backup_dir=backup_dir, now=NOW,
        )
        for table in ("stockbuy", "stocksell"):
            after = _all_rows(fake_db, table)
            assert after[: len(before[table])] == before[table]
            assert len(after) == len(before[table]) + 2


class TestReceipts:
    def _record(self, name: str = "ALP_P1_leaf_001") -> dict:
        return {
            "name": name,
            "source": {"kind": "leaf", "payload": {"rule": "등락율>2", "depth": 3}},
            "prereg_sha": "a" * 64,
            "n_trials_context": 1234,
        }

    def test_round_trip_appends_and_reads_in_order(self, tmp_path):
        path = tmp_path / "receipts.jsonl"
        written1 = append_receipt(path, self._record("ALP_a"), now=NOW)
        written2 = append_receipt(
            path,
            {**self._record("ALP_b"), "source": {"kind": "event_cell", "payload": {}}},
            now=NOW,
        )
        loaded = read_receipts(path)
        assert loaded == [written1, written2]
        assert [r["name"] for r in loaded] == ["ALP_a", "ALP_b"]
        assert loaded[0]["created_at"] == NOW.isoformat()
        assert loaded[1]["source"]["kind"] == "event_cell"

    def test_missing_file_reads_empty(self, tmp_path):
        assert read_receipts(tmp_path / "none.jsonl") == []

    def test_invalid_source_kind_rejected(self, tmp_path):
        record = self._record()
        bad = {**record, "source": {"kind": "oracle", "payload": {}}}
        with pytest.raises(ValueError):
            append_receipt(tmp_path / "r.jsonl", bad, now=NOW)
        assert "leaf" in ALLOWED_SOURCE_KINDS and "event_cell" in ALLOWED_SOURCE_KINDS

    def test_missing_required_key_rejected(self, tmp_path):
        record = self._record()
        del record["prereg_sha"]
        with pytest.raises(ValueError):
            append_receipt(tmp_path / "r.jsonl", record, now=NOW)

    def test_preset_created_at_rejected(self, tmp_path):
        bad = {**self._record(), "created_at": "2020-01-01T00:00:00"}
        with pytest.raises(ValueError):
            append_receipt(tmp_path / "r.jsonl", bad, now=NOW)

    def test_input_record_not_mutated(self, tmp_path):
        record = self._record()
        snapshot = copy.deepcopy(record)
        append_receipt(tmp_path / "r.jsonl", record, now=NOW)
        assert record == snapshot

    def test_name_prefix_enforced_in_receipt(self, tmp_path):
        bad = {**self._record(), "name": "P1_leaf_001"}
        with pytest.raises(ValueError):
            append_receipt(tmp_path / "r.jsonl", bad, now=NOW)
        assert NAME_PREFIX == "ALP_"
