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
import os
import shutil
import sqlite3
import subprocess
import stat
from pathlib import Path

import pytest

from alpha_lab.bridge import inspect_promotion_journal_v2
from alpha_lab.bridge import registrar
from alpha_lab.bridge.receipts import (
    ALLOWED_SOURCE_KINDS,
    LEGACY_NON_AUTHORITATIVE,
    LegacyReceiptWriteBlockedError,
    append_receipt,
    read_receipts,
    validate_historical_receipt,
)
from alpha_lab.bridge.registrar import (
    NAME_PREFIX,
    register_conditions,
    register_conditions_v2,
    verify_promotion_manifest,
)
from alpha_lab.catalog import builder
from alpha_lab.discipline.evidence import (
    issue_promotion_manifest_v2,
    verify_promotion_result_v2,
)
from alpha_lab.discipline.ledger import append_trial_v2
from alpha_lab.discipline.measure_gate import (
    claim_gate_receipt_v2,
    finalize_and_issue_gate_receipt_v2,
)

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
            "ledger_path": "n_trials_ledger.jsonl",
            "authority_paths": {
                "seal_dir": "seals",
                "promotions_dir": "promotions",
                "catalog_dir": "promotion_catalogs",
                "target_db": "strategy.db",
                "journal_dir": "promotion_journal",
                "backup_dir": "backups",
            },
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

    strategy_db = tmp_path / "strategy.db"
    if not strategy_db.exists():
        _make_fake_strategy_db(strategy_db)
    seal_path = tmp_path / "seals" / f"{hashlib.sha256(prereg.read_bytes()).hexdigest()}.seal.json"
    receipt = finalize_and_issue_gate_receipt_v2(
        prereg,
        repo_root=tmp_path,
        code_files=(code,),
        manifest_path=seal_path,
        sealed_at="2026-07-14T00:00:00+00:00",
        issued_at="2026-07-14T00:01:00+00:00",
        nonce="bridge-run",
    )
    assert receipt["custody"] == {
        "mode": "continuous-finalizer-v1",
        "launch_authoritative": True,
    }
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
    manifest = issue_promotion_manifest_v2(
        tmp_path,
        gate_receipt_path=receipt_path,
        gate_claim_path=usage_path,
        ledger_path=ledger_path,
        evidence_id=row["evidence_id"],
        created_at="2026-07-14T00:04:00+00:00",
        output_dir=tmp_path / "promotions",
    )
    manifest_path = tmp_path / "promotions" / f"{row['evidence_id']}.pre.json"

    for rel in builder._SHARED_RELS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    for name in ("load_assets", "load_clauses", "load_strategies", "load_cells", "load_judgments"):
        monkeypatch.setattr(builder, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(
        builder,
        "_strict_source_hashes",
        lambda *args, **kwargs: sorted([file_ref(source), file_ref(artifact)], key=lambda item: item["path"]),
    )
    receipt = builder.build_all(
        tmp_path,
        repo_root=tmp_path,
        promotion_manifest_path=manifest_path,
    )
    catalog_path = tmp_path / "promotion_catalogs" / f"{row['evidence_id']}.pre.receipt.json"
    assert catalog_path.is_file()
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

        result = verify_promotion_manifest(chain["manifest"], repo_root=tmp_path)
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
                [_item()], manifest_path=tmp_path / "missing.json", repo_root=tmp_path, now=NOW,
            )
        assert fake_db.read_bytes() == before
        assert not backup_dir.exists()
    def test_unsupported_platform_fails_at_guard_entry_before_any_sqlite_connect(
        self, tmp_path, monkeypatch,
    ):
        item = _item()
        missing_db = tmp_path / "missing.sqlite"
        manifest = {"authority_paths": {"target_db": "strategy.sqlite"}}
        verdict = {
            "pass": True,
            "candidates": [{
                "name": item["name"],
                "buy_sha256": hashlib.sha256(item["buy_expr"].encode("utf-8")).hexdigest(),
                "sell_sha256": hashlib.sha256(item["sell_expr"].encode("utf-8")).hexdigest(),
            }],
        }
        connects: list[object] = []

        def reject_unsupported_platform(*args, **kwargs):
            raise builder.EvidenceSchemaError(
                "authority mutation guard is unsupported on this platform")

        monkeypatch.setattr(registrar, "verify_promotion_manifest", lambda *args, **kwargs: verdict)
        monkeypatch.setattr(registrar, "verify_promotion_manifest_v2", lambda *args, **kwargs: (manifest, "a" * 64))
        monkeypatch.setattr(registrar, "_promotion_destinations", lambda *args: {
            "target_db": missing_db,
            "catalog": tmp_path / "catalog.json",
            "pre": tmp_path / "journal.pre.json",
            "anchor": tmp_path / "journal.pre.sha256",
            "post": tmp_path / "journal.post.json",
            "backup": tmp_path / "backup.sqlite",
        })
        monkeypatch.setattr(registrar, "recheck_authority_paths", lambda *args: manifest["authority_paths"])
        monkeypatch.setattr(registrar, "authority_mutation_guard", reject_unsupported_platform)
        monkeypatch.setattr(
            registrar.sqlite3, "connect",
            lambda *args, **kwargs: connects.append(args) or pytest.fail("SQLite connect must not run"),
        )

        with pytest.raises(builder.EvidenceSchemaError, match="unsupported on this platform"):
            registrar.register_conditions_v2(
                [item], manifest_path=tmp_path / "manifest.json", repo_root=tmp_path, now=NOW,
            )

        assert connects == []

    def test_registers_verified_manifest_with_legacy_insert_semantics(
        self, fake_db, backup_dir, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
        )
        assert result["status"] == "POST"
        assert result["evidence_id"] == chain["evidence_id"]
        assert result["promotion_manifest"] == {
            "path": f"promotions/{chain['evidence_id']}.pre.json",
            "sha256": hashlib.sha256(chain["manifest"].read_bytes()).hexdigest(),
        }
        assert [entry["name"] for entry in result["inserted"]] == [item["name"]]
        post_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.post.json"
        assert result == json.loads(post_path.read_text(encoding="utf-8"))
        pre_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.pre.json"
        anchor_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.pre.sha256"
        assert anchor_path.read_bytes() == hashlib.sha256(pre_path.read_bytes()).hexdigest().encode("ascii")
        for suffix in ("-journal", "-wal", "-shm"):
            assert not Path(f"{fake_db}{suffix}").exists()
    @pytest.mark.skipif(os.name != "nt", reason="Windows SQLite auxiliary reservations")
    def test_reserved_sidecars_block_hot_journal_writer_and_cleanup_on_abort(
        self, fake_db, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        baseline = fake_db.read_bytes()
        write_json = registrar._write_exclusive_json

        def inject_hot_journal_creator(path, value):
            if path.name.endswith(".pre.json"):
                with pytest.raises(OSError):
                    with open(f"{fake_db}-journal", "wb"):
                        pass
                assert fake_db.read_bytes() == baseline
                raise OSError("injected hot-journal creator was blocked")
            return write_json(path, value)

        monkeypatch.setattr(registrar, "_write_exclusive_json", inject_hot_journal_creator)
        with pytest.raises(OSError, match="hot-journal creator"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )

        assert fake_db.read_bytes() == baseline
        for suffix in ("-journal", "-wal", "-shm"):
            assert not Path(f"{fake_db}{suffix}").exists()
    def test_rejects_bare_inner_catalog_receipt_before_db_access(
        self, fake_db, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        outer = json.loads(chain["catalog"].read_text(encoding="utf-8"))
        # Simulate administrative corruption; production receipts remain immutable.
        os.chmod(chain["catalog"], stat.S_IWRITE)
        chain["catalog"].write_text(
            json.dumps(outer["promotion_receipt"]), encoding="utf-8",
        )
        before = fake_db.read_bytes()

        verdict = verify_promotion_manifest(chain["manifest"], repo_root=tmp_path)

        assert verdict["pass"] is False
        assert "outer builder receipt" in verdict["reasons"][0]
        assert fake_db.read_bytes() == before
    @pytest.mark.parametrize("mutation", ("empty", "extra"))
    def test_rejects_forged_self_consistent_catalog_authority_db(
        self, fake_db, tmp_path, monkeypatch, mutation,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        outer = json.loads(chain["catalog"].read_text(encoding="utf-8"))
        catalog_db = tmp_path / outer["promotion_receipt"]["catalog_db"]["path"]
        # Simulate administrative corruption; production catalog DBs remain immutable.
        os.chmod(catalog_db, stat.S_IWRITE)
        con = sqlite3.connect(str(catalog_db))
        try:
            if mutation == "empty":
                con.execute("DELETE FROM catalog_authority")
            else:
                con.execute(
                    "INSERT INTO catalog_authority "
                    "(name, buy_sha256, sell_sha256, phase, outcome, disposition) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    ("ALP_forged", "0" * 64, "0" * 64, "PRE", "authorized", "pending_post"),
                )
            con.commit()
        finally:
            con.close()
        outer["promotion_receipt"]["catalog_db"]["sha256"] = hashlib.sha256(
            catalog_db.read_bytes()).hexdigest()
        # Simulate administrative corruption; production receipts remain immutable.
        os.chmod(chain["catalog"], stat.S_IWRITE)
        chain["catalog"].write_text(json.dumps(outer), encoding="utf-8")

        verdict = verify_promotion_manifest(chain["manifest"], repo_root=tmp_path)

        assert verdict["pass"] is False
        assert "catalog authority DB records are omitted, extra, or misstated" in verdict["reasons"][0]
        assert not (tmp_path / "promotion_journal").exists()

    def test_rejects_wal_mode_before_journal_or_backup(
        self, fake_db, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        con = sqlite3.connect(str(fake_db))
        try:
            assert con.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
        finally:
            con.close()
        before = fake_db.read_bytes()

        with pytest.raises(Exception, match="journal mode"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )

        assert fake_db.read_bytes() == before
        assert not (tmp_path / "promotion_journal").exists()
        assert not (tmp_path / "backups").exists()
    @pytest.mark.parametrize("suffix", ("-wal", "-shm"))
    def test_rejects_sqlite_sidecars_before_journal_or_backup(
        self, fake_db, tmp_path, monkeypatch, suffix,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        Path(f"{fake_db}{suffix}").write_bytes(b"ambiguous")
        before = fake_db.read_bytes()

        with pytest.raises(Exception, match="filesystem auxiliary sidecars"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )

        assert fake_db.read_bytes() == before
        assert not (tmp_path / "promotion_journal").exists()
        assert not (tmp_path / "backups").exists()
    @pytest.mark.skipif(os.name != "nt", reason="Windows retained-handle authority guard")
    def test_rejects_prepositioned_rollback_journal_without_opening_it(
        self, fake_db, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        journal_path = Path(f"{fake_db}-journal")
        sentinel = tmp_path / "protected-rollback-journal"
        sentinel.write_bytes(b"protected rollback journal sentinel")
        os.link(sentinel, journal_path)
        before_db = fake_db.read_bytes()
        before_sentinel = sentinel.read_bytes()
        connect = registrar.sqlite3.connect

        def reject_target_connect(path, *args, **kwargs):
            if Path(path) == fake_db:
                pytest.fail("SQLite target connect must not open a prepositioned sidecar")
            return connect(path, *args, **kwargs)

        monkeypatch.setattr(registrar.sqlite3, "connect", reject_target_connect)

        with pytest.raises(Exception, match="filesystem auxiliary sidecars"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )

        assert fake_db.read_bytes() == before_db
        assert sentinel.read_bytes() == before_sentinel
        assert journal_path.read_bytes() == before_sentinel
        assert not (tmp_path / "promotion_journal").exists()
        assert not (tmp_path / "backups").exists()
    def test_canonical_post_is_catalog_direct_input(self, fake_db, backup_dir, tmp_path, monkeypatch):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
        )
        post_relative = f"promotion_journal/{chain['evidence_id']}.post.json"
        receipt = builder.build_all(
            tmp_path, repo_root=tmp_path,
            promotion_result_path=tmp_path / post_relative,
        )
        assert receipt["promotion_receipt"]["upstream"]["path"] == post_relative
        assert (tmp_path / "promotion_catalogs" / (
            f"{chain['evidence_id']}.post.receipt.json")).is_file()

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
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )
        inspected = inspect_promotion_journal_v2(
            repo_root=tmp_path, manifest_path=chain["manifest"],
        )
        assert inspected["status"] == "INCOMPLETE_REQUIRES_RECONCILIATION"
        assert inspected["current_db_matches_pre"] is False
        assert inspected["pre_anchor_path"] == (
            f"promotion_journal/{chain['evidence_id']}.pre.sha256"
        )
        assert (tmp_path / inspected["pre_anchor_path"]).exists()
        with pytest.raises(ValueError, match="refuses rerun"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
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
            [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
        )
        assert result["inserted"] == []
        assert result["conflicts"] == [{
            "name": item["name"], "reason": "name_exists",
            "existing_tables": ["stockbuy"],
        }]
        assert item["name"] not in {name for name, _ in _all_rows(fake_db, "stocksell")}

    def test_rechecks_pre_bytes_under_the_write_lock(self, fake_db, backup_dir, tmp_path, monkeypatch):
        import alpha_lab.bridge.registrar as registrar

        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        write = registrar._write_exclusive_bytes

        def mutate_after_pre_anchor(path, payload):
            write(path, payload)
            if path.name.endswith(".pre.sha256"):
                con = sqlite3.connect(str(fake_db))
                try:
                    con.execute(
                        'INSERT INTO "stockbuy" ("index", "전략코드") VALUES (?, ?)',
                        ("raced", "mutation"),
                    )
                    con.commit()
                finally:
                    con.close()

        monkeypatch.setattr(registrar, "_write_exclusive_bytes", mutate_after_pre_anchor)
        with pytest.raises(Exception, match="changed after PRE intent|unable to open database file"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )
        assert not (backup_dir / f"{chain['evidence_id']}.pre.sqlite").exists()
    def test_rejects_unauthorized_extra_row_from_logical_delta(
        self, fake_db, tmp_path, monkeypatch,
    ):
        import alpha_lab.bridge.registrar as registrar

        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        apply = registrar._apply_inserts

        def insert_extra(con, planned):
            inserted = apply(con, planned)
            con.execute(
                'INSERT INTO "stockbuy" ("index", "전략코드") VALUES (?, ?)',
                ("ALP_unapproved", "unauthorized"),
            )
            return inserted

        monkeypatch.setattr(registrar, "_apply_inserts", insert_extra)
        with pytest.raises(Exception, match="unauthorized candidate row"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )
        assert not (tmp_path / "promotion_journal" / f"{chain['evidence_id']}.post.json").exists()

    def test_post_binds_exact_logical_delta(self, fake_db, tmp_path, monkeypatch):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)

        result = register_conditions_v2(
            [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
        )

        delta = result["logical_delta"]
        assert set(delta) == {
            "pre_state_sha256", "post_state_sha256", "details", "details_sha256",
        }
        assert delta["details"]["schema_unchanged"] is True
        assert delta["details"]["table_changes"] == [
            {"table": "stockbuy", "inserted": [{
                "name": item["name"],
                "code_sha256": hashlib.sha256(item["buy_expr"].encode("utf-8")).hexdigest(),
            }]},
            {"table": "stocksell", "inserted": [{
                "name": item["name"],
                "code_sha256": hashlib.sha256(item["sell_expr"].encode("utf-8")).hexdigest(),
            }]},
        ]
    def test_rejects_persistent_pragma_mutation_from_logical_delta(
        self, fake_db, tmp_path, monkeypatch,
    ):
        import alpha_lab.bridge.registrar as registrar

        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        apply = registrar._apply_inserts

        def mutate_pragma(con, planned):
            inserted = apply(con, planned)
            con.execute("PRAGMA user_version=7")
            return inserted

        monkeypatch.setattr(registrar, "_apply_inserts", mutate_pragma)
        with pytest.raises(Exception, match="persistent SQLite pragma state"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )
        assert not (tmp_path / "promotion_journal" / f"{chain['evidence_id']}.post.json").exists()

    def test_queued_wal_writer_cannot_wedge_strong_verification(self, fake_db, tmp_path, monkeypatch):
        import alpha_lab.bridge.registrar as registrar

        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        verify = registrar.verify_promotion_result_v2

        def enable_wal_before_strong_verification(*args, **kwargs):
            con = sqlite3.connect(str(fake_db), timeout=0)
            try:
                with pytest.raises(sqlite3.OperationalError, match="database is locked"):
                    con.execute("PRAGMA journal_mode=WAL")
            finally:
                con.close()
            return verify(*args, **kwargs)

        monkeypatch.setattr(registrar, "verify_promotion_result_v2", enable_wal_before_strong_verification)
        result = register_conditions_v2(
            [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
        )

        assert result["target_db"]["post_sha256"] == hashlib.sha256(fake_db.read_bytes()).hexdigest()

    def test_copied_post_and_stale_live_db_fail_strong_verification(
        self, fake_db, backup_dir, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
        )
        post_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.post.json"
        copied = tmp_path / "copied.post.json"
        copied.write_bytes(post_path.read_bytes())
        with pytest.raises(Exception, match="sealed authority paths"):
            verify_promotion_result_v2(copied, repo_root=tmp_path)
        con = sqlite3.connect(str(fake_db))
        try:
            con.execute(
                'INSERT INTO "stockbuy" ("index", "전략코드") VALUES (?, ?)',
                ("stale", "mutation"),
            )
            con.commit()
        finally:
            con.close()
        with pytest.raises(Exception, match="unauthorized candidate row"):
            verify_promotion_result_v2(post_path, repo_root=tmp_path)

    def test_private_complete_writer_is_absent(self):
        import alpha_lab.bridge as bridge
        import alpha_lab.bridge.registrar as registrar

        assert not hasattr(registrar, "_register_conditions")
        assert "register_conditions" not in bridge.__all__
    def test_tampered_post_pre_and_orphan_post_fail_closed(
        self, fake_db, backup_dir, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        result = register_conditions_v2(
            [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
        )
        post_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.post.json"
        post = json.loads(post_path.read_text(encoding="utf-8"))
        original_post = copy.deepcopy(post)
        post["inserted"].append(copy.deepcopy(post["inserted"][0]))
        post_path.write_text(json.dumps(post), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, manifest_path=chain["manifest"],
            )
        post = copy.deepcopy(original_post)
        post["target_db"]["post_sha256"] = "0" * 64
        post_path.write_text(json.dumps(post), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, manifest_path=chain["manifest"],
            )
        post = copy.deepcopy(original_post)
        post["backup_ref"]["sha256"] = "0" * 64
        post_path.write_text(json.dumps(post), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, manifest_path=chain["manifest"],
            )
        anchor_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.pre.sha256"
        anchor_path.unlink()
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, manifest_path=chain["manifest"],
            )
        pre_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.pre.json"
        anchor_path.write_bytes(hashlib.sha256(pre_path.read_bytes()).hexdigest().encode("ascii"))
        post_path.unlink()
        pre_path = tmp_path / "promotion_journal" / f"{chain['evidence_id']}.pre.json"
        pre = json.loads(pre_path.read_text(encoding="utf-8"))
        pre["target_db"]["pre_sha256"] = "0" * 64
        pre_path.write_text(json.dumps(pre), encoding="utf-8")
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(
                repo_root=tmp_path, manifest_path=chain["manifest"],
            )
        with pytest.raises(Exception):
            inspect_promotion_journal_v2(repo_root=tmp_path, manifest_path=tmp_path / "missing.json")


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

    @pytest.mark.parametrize(
        ("script_name", "artifacts"),
        [
            ("register_b1.py", ("b1_registration_receipt.json",)),
            ("finalize_and_ledger.py", ("_ab_verdict.json", "b1_registration_receipt.json")),
        ],
    )
    def test_b1_scripts_are_historical_non_executable_notices(self, script_name, artifacts):
        root = Path(__file__).resolve().parents[2]
        text = (
            root
            / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710/d5r_b1_live"
            / script_name
        ).read_text(encoding="utf-8")
        assert "HISTORICAL EVIDENCE" in text
        assert "NON-EXECUTABLE ARCHIVE" in text
        for artifact in artifacts:
            assert artifact in text
        assert "fresh v2 evidence chain" in text
        assert "authorized non-protected target" in text
        for forbidden in (
            "sqlite3",
            "register_conditions",
            "--write",
            "_database",
            "strategy.db",
            "scratchpad",
            "json.dump",
            "write_text(",
            "open(",
            "append(",
        ):
            assert forbidden not in text
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
            "created_at": NOW.isoformat(),
        }

    def test_append_is_blocked_before_receipt_path_creation(self, tmp_path):
        path = tmp_path / "new" / "receipts.jsonl"

        with pytest.raises(
            LegacyReceiptWriteBlockedError, match="legacy-receipt-write-blocked"
        ):
            append_receipt(path, self._record(), now=NOW)

        assert not path.exists()
        assert not path.parent.exists()
        assert LEGACY_NON_AUTHORITATIVE == "LEGACY_NON_AUTHORITATIVE"

    def test_reads_and_validates_historical_receipt(self, tmp_path):
        path = tmp_path / "receipts.jsonl"
        record = self._record()
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")

        assert validate_historical_receipt(record) is None
        assert read_receipts(path) == [record]

    def test_historical_validation_rejects_invalid_records(self, tmp_path):
        path = tmp_path / "receipts.jsonl"
        record = self._record()
        record["source"] = {"kind": "oracle", "payload": {}}
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match="source.kind"):
            read_receipts(path)
        assert "leaf" in ALLOWED_SOURCE_KINDS and "event_cell" in ALLOWED_SOURCE_KINDS

    def test_missing_file_reads_empty(self, tmp_path):
        assert read_receipts(tmp_path / "none.jsonl") == []
