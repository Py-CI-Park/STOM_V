"""alpha_lab.bridge 단위 테스트 — 전략 DB 등록(INSERT-only) + provenance 영수증.

전부 tmp_path 사기(fake) 전략 DB로만 검증한다. 실 전략 DB(_database/strategy.db)
는 절대 접근하지 않는다. 사기 DB 스키마는 utility/database_check.py 실측 DDL을
그대로 미러: CREATE TABLE "stockbuy" ( "index" TEXT, "전략코드" TEXT ) + name 인덱스.

실행: python -m pytest tests/unit/test_alpha_bridge.py -q
"""

import copy
import datetime as dt
import hashlib
import json
import sqlite3
from pathlib import Path
import pytest

from alpha_lab.bridge import append_receipt, read_receipts, register_conditions
from alpha_lab.bridge.receipts import ALLOWED_SOURCE_KINDS
from alpha_lab.bridge.registrar import NAME_PREFIX
from alpha_lab.bridge.registrar import (
    register_conditions_v2,
    verify_promotion_manifest,
)
from alpha_lab.discipline.evidence import build_evidence_identity, sha256_canonical
from alpha_lab.catalog import builder

NOW = dt.datetime(2026, 7, 14, 0, 5, 0, tzinfo=dt.timezone.utc)

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


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }



def _write_v2_promotion_chain(tmp_path, item: dict, monkeypatch) -> dict:
    """Create a complete authoritative v2 chain entirely under tmp_path."""
    prereg, code = tmp_path / "prereg.md", tmp_path / "measure.py"
    source, artifact = tmp_path / "source.json", tmp_path / "result.json"
    prereg.write_text("> 지위: **SEALED**\n", encoding="utf-8")
    code.write_text("MEASURE = 1\n", encoding="utf-8")
    source.write_text("source", encoding="utf-8")
    artifact.write_text("result", encoding="utf-8")
    def file_ref(path):
        return {"path": path.relative_to(tmp_path).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    seal = {
        "schema_version": 2, "kind": "prereg_seal", "status": "SEALED",
        "sealed_at": "2026-07-14T00:00:00+00:00",
        "sealed_doc": file_ref(prereg), "code_manifest": [file_ref(code)],
    }
    seal_path = tmp_path / "seal.json"
    seal_path.write_text(json.dumps(seal), encoding="utf-8")
    absolute_code = str(code)
    receipt = {
        "schema_version": 2, "kind": "measure_gate_receipt", "status": "PASS",
        "issued_at": "2026-07-14T00:01:00+00:00", "nonce": "run-1",
        "repo_head": "a" * 40,
        "seal_manifest": {"path": "seal.json", "sha256": sha256_canonical(seal)},
        "prereg": file_ref(prereg), "code_manifest_sha256": sha256_canonical(seal["code_manifest"]),
        "code_manifest": seal["code_manifest"],
        "checks": {
            "repo": {"pass": True, "detail": "true", "reason": ""},
            "sealed_doc": {"pass": True, "rel": "prereg.md", "last_commit": "b" * 40},
            "code_clean": {"pass": True, "reasons": [], "files": {
                absolute_code: {"tracked": True, "clean": True, "last_commit": "c" * 40, "reason": ""}}},
            "sha_seal": {"pass": True, "checked": True, "files": {
                absolute_code: {"expected": file_ref(code)["sha256"], "actual": file_ref(code)["sha256"],
                                "match": True, "reason": ""}}},
        },
    }
    receipt["receipt_id"] = sha256_canonical({key: receipt[key] for key in (
        "issued_at", "nonce", "repo_head", "seal_manifest", "prereg", "code_manifest_sha256")})
    (tmp_path / "receipts").mkdir()
    receipt_path = tmp_path / "receipts" / f"{receipt['receipt_id']}.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    usage = {
        "schema_version": 2, "kind": "measure_gate_usage",
        "issuer": {"receipt_id": receipt["receipt_id"], "receipt_sha256": sha256_canonical(receipt),
                   "issued_at": receipt["issued_at"], "repo_head": receipt["repo_head"]},
        "claim": {"receipt_id": receipt["receipt_id"], "path": f"claims/{receipt['receipt_id']}.json"},
        "consumer": "test-run", "consumed_at": "2026-07-14T00:02:00+00:00",
    }
    (tmp_path / "claims").mkdir()
    usage_path = tmp_path / "claims" / f"{receipt['receipt_id']}.json"
    usage_path.write_text(json.dumps(usage), encoding="utf-8")
    candidates = [{
        "name": item["name"],
        "buy_sha256": hashlib.sha256(item["buy_expr"].encode("utf-8")).hexdigest(),
        "sell_sha256": hashlib.sha256(item["sell_expr"].encode("utf-8")).hexdigest(),
    }]
    evidence_id, evidence = build_evidence_identity(
        receipt, usage, input_artifacts=[file_ref(source)], result_artifacts=[file_ref(artifact)],
        candidate_set=candidates, negative_or_kill=False, repo_root=tmp_path)
    row = {"ts": "2026-07-14T00:03:00+00:00", "series": "B", "window": "window",
           "trial_type": "b(test)", "target": "candidate", "result": "pass", "session": "test",
           "schema_version": 2, "evidence_id": evidence_id, "evidence": evidence}
    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 2, "kind": "promotion_manifest", "status": "PRE",
        "created_at": "2026-07-14T00:04:00+00:00", "evidence_id": evidence_id,
        "ledger": {**file_ref(ledger_path), "record_sha256": sha256_canonical(row)}, "gate_receipt": file_ref(receipt_path),
        "gate_claim": file_ref(usage_path), "input_artifacts": [file_ref(source)],
        "result_artifacts": [file_ref(artifact)], "candidate_set": candidates,
        "candidate_set_sha256": sha256_canonical(candidates),
    }
    manifest_path = tmp_path / "promotion.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for name in ("load_assets", "load_ledger_mirror", "load_clauses", "load_strategies",
                 "load_cells", "load_judgments"):
        monkeypatch.setattr(builder, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(builder, "_strict_source_hashes",
                        lambda receipt, run_dir, root: [file_ref(source)])
    monkeypatch.setattr(builder, "ensure_gitignore",
                        lambda run_dir: {"path": "", "action": "test", "pattern": ""})
    catalog_path = tmp_path / "catalog.json"
    builder.build_all(
        tmp_path, db_path=tmp_path / "catalog.db", receipt_path=catalog_path,
        repo_root=tmp_path, promotion_manifest_path=manifest_path,
    )
    return {"manifest": manifest_path, "ledger": ledger_path, "receipt": receipt_path,
            "usage": usage_path, "catalog": catalog_path, "evidence_id": evidence_id}


class TestPromotionV2:
    def test_verifies_complete_synthetic_chain_read_only(self, tmp_path, monkeypatch):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        before = _file_snapshot(tmp_path)

        import alpha_lab.bridge.registrar as registrar
        monkeypatch.setattr(registrar.sqlite3, "connect", lambda *args, **kwargs: pytest.fail("sqlite write/read invoked"))
        monkeypatch.setattr(registrar, "_backup_db", lambda *args, **kwargs: pytest.fail("backup invoked"))

        result = verify_promotion_manifest(
            chain["manifest"], repo_root=tmp_path, ledger_path=chain["ledger"],
            gate_receipt_path=chain["receipt"], gate_usage_path=chain["usage"],
            catalog_receipt_path=chain["catalog"],
        )
        assert result == {
            "pass": True, "schema_version": 2, "status": "PRE",
            "evidence_id": chain["evidence_id"],
            "candidates": [{
                "name": item["name"],
                "buy_sha256": hashlib.sha256(item["buy_expr"].encode("utf-8")).hexdigest(),
                "sell_sha256": hashlib.sha256(item["sell_expr"].encode("utf-8")).hexdigest(),
            }],
            "checks": {"manifest": True, "ledger": True, "evidence_chain": True, "catalog_pre": True},
            "reasons": [],
        }
        assert _file_snapshot(tmp_path) == before

    def test_register_rejects_invalid_evidence_before_db_or_backup(self, fake_db, backup_dir, tmp_path):
        before = fake_db.read_bytes()
        with pytest.raises(ValueError, match="promotion verification failed"):
            register_conditions_v2(
                fake_db, [_item()], manifest_path=tmp_path / "missing.json", repo_root=tmp_path,
                ledger_path=tmp_path / "ledger.jsonl", gate_receipt_path=tmp_path / "receipt.json",
                gate_usage_path=tmp_path / "usage.json", catalog_receipt_path=tmp_path / "catalog.json",
                journal_dir="promotion_journal", backup_dir=backup_dir, now=NOW,
            )
        assert fake_db.read_bytes() == before
        assert not backup_dir.exists()

    def test_registers_verified_manifest_with_legacy_insert_semantics(
        self, fake_db, backup_dir, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            fake_db, [item], manifest_path=chain["manifest"], repo_root=tmp_path,
            ledger_path=chain["ledger"], gate_receipt_path=chain["receipt"],
            gate_usage_path=chain["usage"], catalog_receipt_path=chain["catalog"],
            journal_dir="promotion_journal", backup_dir=backup_dir,
            now=NOW.replace(tzinfo=dt.timezone.utc),
        )
        assert result["status"] == "POST"
        assert result["evidence_id"] == chain["evidence_id"]
        assert result["promotion_manifest"] == {
            "path": "promotion.json",
            "sha256": hashlib.sha256(chain["manifest"].read_bytes()).hexdigest(),
        }
        assert [entry["name"] for entry in result["inserted"]] == [item["name"]]


class TestHistoricalAuthorityDocuments:
    def test_b_ext_and_o4_are_legacy_v1_without_promotion_authority(self):
        root = Path(__file__).resolve().parents[2]
        for name in (
            "2026-07-14_b_track_ext_multistrategy_branches_preregistration.md",
            "2026-07-13_o4_generation_grammar_preregistration.md",
        ):
            text = (root / "docs/research/condition_research/plans" / name).read_text(encoding="utf-8")
            assert "evidence_contract: **LEGACY_V1**" in text
            assert "promotion_authority: **NONE**" in text
            assert "no one-use gate receipt may be reconstructed after measurement" in text

class TestLegacyRegistrarBlocked:
    def test_public_legacy_registrar_fails_before_db_access(self, fake_db, backup_dir, monkeypatch):
        import alpha_lab.bridge.registrar as registrar
        before = fake_db.read_bytes()
        monkeypatch.setattr(registrar.sqlite3, "connect", lambda *args, **kwargs: pytest.fail("DB accessed"))
        with pytest.raises(RuntimeError, match="legacy-promotion-blocked"):
            register_conditions(fake_db, [_item()], backup_dir=backup_dir, now=NOW)
        assert fake_db.read_bytes() == before
        assert not backup_dir.exists()

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
