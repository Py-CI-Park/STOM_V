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
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from alpha_lab.bridge import (
    append_receipt,
    inspect_promotion_journal_v2,
    read_receipts,
    register_conditions,
)
from alpha_lab.bridge.receipts import ALLOWED_SOURCE_KINDS
from alpha_lab.bridge.registrar import NAME_PREFIX
from alpha_lab.bridge.registrar import (
    register_conditions_v2,
    verify_promotion_manifest,
)
from alpha_lab.catalog import builder
from alpha_lab.discipline.evidence import sha256_canonical
from alpha_lab.discipline.ledger import append_trial_v2
from alpha_lab.discipline.measure_gate import (
    claim_gate_receipt_v2,
    issue_gate_receipt_v2,
)
from alpha_lab.discipline.prereg import finalize_prereg

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
    if shutil.which("git") is None:
        pytest.skip("git is required for authoritative v2 receipt fixtures")

    prereg, code = tmp_path / "prereg.md", tmp_path / "measure.py"
    source, artifact = tmp_path / "source.json", tmp_path / "result.json"
    code.write_text("MEASURE = 1\n", encoding="utf-8")
    prereg.write_text(
        "> 지위: **SEALED**\n"
        "```json prereg-contract-v2\n"
        + json.dumps({
            "schema_version": 2,
            "hypothesis_id": "H-bridge",
            "discovery_window": {"start": "2022-03-23", "end": "2023-12-31"},
            "primary_estimand": "mean spread",
            "sample_floors": {"qualified": 2},
            "multiplicity_family": "bridge fixture",
            "kill_rule": "non-positive effect",
            "dependency_roots": ["measure.py"],
            "dynamic_python_dependencies": [],
            "non_python_dependencies": [],
        }, sort_keys=True)
        + "\n```\n",
        encoding="utf-8",
    )
    source.write_text('{"source":"fixture"}\n', encoding="utf-8")
    artifact.write_text('{"result":"pass"}\n', encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "prereg.md", "measure.py"],
        check=True,
    )
    subprocess.run(
        [
            "git", "-C", str(tmp_path), "-c", "user.name=tester",
            "-c", "user.email=t@example.com", "commit", "-q", "-m", "fixture",
        ],
        check=True,
    )

    def file_ref(path):
        return {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    finalize_prereg(
        prereg,
        repo_root=tmp_path,
        code_files=(code,),
        manifest_path=tmp_path / "seal.json",
        sealed_at="2026-07-14T00:00:00+00:00",
    )
    receipt = issue_gate_receipt_v2(
        tmp_path,
        tmp_path / "seal.json",
        issued_at="2026-07-14T00:01:00+00:00",
        nonce="bridge-run",
    )
    receipt_path = tmp_path / "receipts" / f"{receipt['receipt_id']}.json"
    usage = claim_gate_receipt_v2(
        receipt_path,
        repo_root=tmp_path,
        consumer="bridge-test",
        consumed_at="2026-07-14T00:02:00+00:00",
    )
    usage_path = tmp_path / Path(usage["claim"]["path"])
    candidates = [{
        "name": item["name"],
        "buy_sha256": hashlib.sha256(item["buy_expr"].encode("utf-8")).hexdigest(),
        "sell_sha256": hashlib.sha256(item["sell_expr"].encode("utf-8")).hexdigest(),
    }]
    ledger_path = tmp_path / "n_trials_ledger.jsonl"
    row = append_trial_v2(
        ts="2026-07-14T00:03:00+00:00",
        series="B",
        window="2022-03-23~2023-12-31(발견창)",
        trial_type="b(test)",
        target="candidate",
        result="pass",
        session="test",
        repo_root=tmp_path,
        gate_receipt_path=receipt_path,
        gate_usage_path=usage_path,
        input_artifacts=[file_ref(source)],
        result_artifacts=[file_ref(artifact)],
        candidate_set=candidates,
        path=ledger_path,
    )
    manifest = {
        "schema_version": 2,
        "kind": "promotion_manifest",
        "status": "PRE",
        "created_at": "2026-07-14T00:04:00+00:00",
        "evidence_id": row["evidence_id"],
        "ledger": {
            **file_ref(ledger_path),
            "record_sha256": sha256_canonical(row),
        },
        "gate_receipt": file_ref(receipt_path),
        "gate_claim": file_ref(usage_path),
        "input_artifacts": row["evidence"]["input_artifacts"],
        "result_artifacts": row["evidence"]["result_artifacts"],
        "candidate_set": row["evidence"]["candidate_set"],
        "candidate_set_sha256": row["evidence"]["candidate_set_sha256"],
    }
    manifest_path = tmp_path / "promotion.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    for rel in builder._SHARED_RELS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    for name in ("load_assets", "load_clauses", "load_strategies", "load_cells", "load_judgments"):
        monkeypatch.setattr(builder, name, lambda *args, **kwargs: None)
    catalog_path = tmp_path / "catalog.json"
    builder.build_all(
        tmp_path,
        db_path=tmp_path / "catalog.db",
        receipt_path=catalog_path,
        repo_root=tmp_path,
        promotion_manifest_path=manifest_path,
    )
    return {
        "manifest": manifest_path,
        "ledger": ledger_path,
        "receipt": receipt_path,
        "usage": usage_path,
        "catalog": catalog_path,
        "evidence_id": row["evidence_id"],
    }


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
        assert result["journal_pre_anchor_path"] == (
            f"promotion_journal/{chain['evidence_id']}.pre.sha256"
        )
        assert (tmp_path / result["journal_pre_anchor_path"]).read_bytes() == hashlib.sha256(
            (tmp_path / result["journal_pre_path"]).read_bytes()
        ).hexdigest().encode("ascii")
    def test_canonical_post_is_catalog_direct_input(self, fake_db, backup_dir, tmp_path, monkeypatch):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            fake_db, [item], manifest_path=chain["manifest"], repo_root=tmp_path,
            ledger_path=chain["ledger"], gate_receipt_path=chain["receipt"],
            gate_usage_path=chain["usage"], catalog_receipt_path=chain["catalog"],
            journal_dir="promotion_journal", backup_dir=backup_dir, now=NOW,
        )
        receipt = builder.build_all(
            tmp_path, db_path=tmp_path / "catalog-post.db",
            receipt_path=tmp_path / "catalog-post.json", repo_root=tmp_path,
            promotion_result_path=tmp_path / result["journal_post_path"],
        )
        assert receipt["promotion_receipt"]["upstream"]["path"] == result["journal_post_path"]

    def test_crash_after_db_before_post_requires_reconciliation(
        self, fake_db, backup_dir, tmp_path, monkeypatch,
    ):
        import alpha_lab.bridge.registrar as registrar

        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        write = registrar._write_exclusive_json

        def crash_post(path, value):
            if path.name.endswith(".post.json"):
                raise OSError("simulated crash after DB mutation")
            write(path, value)

        monkeypatch.setattr(registrar, "_write_exclusive_json", crash_post)
        with pytest.raises(OSError, match="simulated crash"):
            register_conditions_v2(
                fake_db, [item], manifest_path=chain["manifest"], repo_root=tmp_path,
                ledger_path=chain["ledger"], gate_receipt_path=chain["receipt"],
                gate_usage_path=chain["usage"], catalog_receipt_path=chain["catalog"],
                journal_dir="promotion_journal", backup_dir=backup_dir, now=NOW,
            )
        inspected = inspect_promotion_journal_v2(
            repo_root=tmp_path, journal_dir="promotion_journal",
            evidence_id=chain["evidence_id"],
        )
        assert inspected["status"] == "INCOMPLETE_REQUIRES_RECONCILIATION"
        assert inspected["current_db_matches_pre"] is False
        assert inspected["pre_anchor_path"] == (
            f"promotion_journal/{chain['evidence_id']}.pre.sha256"
        )
        assert (tmp_path / inspected["pre_anchor_path"]).exists()
        with pytest.raises(ValueError, match="refuses rerun"):
            register_conditions_v2(
                fake_db, [item], manifest_path=chain["manifest"], repo_root=tmp_path,
                ledger_path=chain["ledger"], gate_receipt_path=chain["receipt"],
                gate_usage_path=chain["usage"], catalog_receipt_path=chain["catalog"],
                journal_dir="promotion_journal", backup_dir=backup_dir, now=NOW,
            )

    def test_one_sided_conflict_is_a_pair_level_skip(self, fake_db, backup_dir, tmp_path, monkeypatch):
        item = _item()
        con = sqlite3.connect(str(fake_db))
        try:
            con.execute(
                'INSERT INTO "stockbuy" ("index", "전략코드") VALUES (?, ?)',
                (item["name"], "existing"),
            )
            con.commit()
        finally:
            con.close()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            fake_db, [item], manifest_path=chain["manifest"], repo_root=tmp_path,
            ledger_path=chain["ledger"], gate_receipt_path=chain["receipt"],
            gate_usage_path=chain["usage"], catalog_receipt_path=chain["catalog"],
            journal_dir="promotion_journal", backup_dir=backup_dir, now=NOW,
        )
        assert result["inserted"] == []
        assert result["conflicts"] == [{
            "name": item["name"], "reason": "name_exists",
            "existing_tables": ["stockbuy"],
        }]
        assert item["name"] not in {name for name, _ in _all_rows(fake_db, "stocksell")}

    def test_tampered_post_pre_and_orphan_post_fail_closed(
        self, fake_db, backup_dir, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            fake_db, [item], manifest_path=chain["manifest"], repo_root=tmp_path,
            ledger_path=chain["ledger"], gate_receipt_path=chain["receipt"],
            gate_usage_path=chain["usage"], catalog_receipt_path=chain["catalog"],
            journal_dir="promotion_journal", backup_dir=backup_dir, now=NOW,
        )
        post_path = tmp_path / result["journal_post_path"]
        post = json.loads(post_path.read_text(encoding="utf-8"))
        original_post = copy.deepcopy(post)
        post["inserted"].append(copy.deepcopy(post["inserted"][0]))
        post_path.write_text(json.dumps(post), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, journal_dir="promotion_journal",
                evidence_id=chain["evidence_id"],
            )
        post = copy.deepcopy(original_post)
        post["target_db"]["post_sha256"] = "0" * 64
        post_path.write_text(json.dumps(post), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, journal_dir="promotion_journal",
                evidence_id=chain["evidence_id"],
            )
        post = copy.deepcopy(original_post)
        post["backup_ref"]["sha256"] = "0" * 64
        post_path.write_text(json.dumps(post), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, journal_dir="promotion_journal",
                evidence_id=chain["evidence_id"],
            )
        anchor_path = tmp_path / result["journal_pre_anchor_path"]
        anchor_path.unlink()
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, journal_dir="promotion_journal",
                evidence_id=chain["evidence_id"],
            )
        anchor_path.write_bytes(hashlib.sha256(
            (tmp_path / result["journal_pre_path"]).read_bytes()
        ).hexdigest().encode("ascii"))
        post_path.unlink()
        pre_path = tmp_path / result["journal_pre_path"]
        pre = json.loads(pre_path.read_text(encoding="utf-8"))
        pre["target_db"]["pre_sha256"] = "0" * 64
        pre_path.write_text(json.dumps(pre), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, journal_dir="promotion_journal",
                evidence_id=chain["evidence_id"],
            )
        orphan_dir = tmp_path / "orphan"
        orphan_dir.mkdir()
        (orphan_dir / f"{chain['evidence_id']}.post.json").write_text("{}", encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, journal_dir="orphan", evidence_id=chain["evidence_id"],
            )


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
