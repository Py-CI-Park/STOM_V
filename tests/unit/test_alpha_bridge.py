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

from alpha_lab.bridge import inspect_promotion_journal_v2
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
    finalize_prereg(
        prereg,
        repo_root=tmp_path,
        code_files=(code,),
        manifest_path=seal_path,
        sealed_at="2026-07-14T00:00:00+00:00",
    )
    receipt = issue_gate_receipt_v2(
        tmp_path,
        seal_path,
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
        builder, "_strict_source_hashes", lambda *args, **kwargs: [file_ref(source)])
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

        import alpha_lab.bridge.registrar as registrar
        monkeypatch.setattr(registrar.sqlite3, "connect", lambda *args, **kwargs: pytest.fail("sqlite write/read invoked"))

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
    def test_rejects_bare_inner_catalog_receipt_before_db_access(
        self, fake_db, tmp_path, monkeypatch,
    ):
        item = _item()
        chain = _write_v2_promotion_chain(tmp_path, item, monkeypatch)
        outer = json.loads(chain["catalog"].read_text(encoding="utf-8"))
        chain["catalog"].write_text(
            json.dumps(outer["promotion_receipt"]), encoding="utf-8",
        )
        before = fake_db.read_bytes()

        verdict = verify_promotion_manifest(chain["manifest"], repo_root=tmp_path)

        assert verdict["pass"] is False
        assert "outer builder receipt" in verdict["reasons"][0]
        assert fake_db.read_bytes() == before
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

        with pytest.raises(Exception, match="WAL/SHM sidecar"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )

        assert fake_db.read_bytes() == before
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
        with pytest.raises(Exception, match="changed after PRE intent"):
            register_conditions_v2(
                [item], manifest_path=chain["manifest"], repo_root=tmp_path, now=NOW,
            )
        assert not backup_dir.exists()

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
        with pytest.raises(Exception, match="target DB SHA-256"):
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
