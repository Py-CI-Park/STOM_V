"""CL-R03 — append-only EvidenceStore + LoopState schema v11 단위 테스트.

design spec: docs/research/condition_research/generated_conditions/
lattice_v3_design_20260709/lattice_v3_design_spec_20260709.md §9(append-only 규칙),
§7(스키마 -> payload_json 저장).

증명 대상:
  - passport -> feedback -> consumption -> receipt 체인 append + run/gen/ID 조회.
  - v11 스키마를 두 번 열어도(fresh, 재오픈) get_schema_version()==11로 멱등.
  - 테스트 전체에 걸친 SQL 트레이스에 5개 evidence 테이블 대상 UPDATE/DELETE가 전혀 없음.
  - readonly LoopState는 WAL/DDL을 만들지 않고 쓰기를 거부한다.
  - 동일 PK+다른 payload 재삽입 -> EvidenceCorruptionError. 동일 PK+동일 payload -> no-op.
  - FK(feedback_envelopes.source_passport_id) 위반 -> IntegrityError(foreign_keys=ON).
  - 커밋 전 크래시(monkeypatch)는 부분 행을 하나도 남기지 않는다(rollback).
  - 커밋 후에는 DB에서 체인을 복원할 수 있고, 매칭되는 스냅샷 파일이 존재한다.

tmp_path SQLite만 사용한다 — 운영 _database/, ai_strategy_loop/state/의 실제 DB는
절대 건드리지 않는다.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401  (env-before-import 계약)
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.controller.evidence_store import (  # noqa: E402
    EvidenceCorruptionError,
    EvidenceStore,
)
from ai_strategy_loop.controller.evidence_contract import (  # noqa: E402
    CANDIDATE_PASSPORT_SCHEMA,
    EVALUATION_MANIFEST_SCHEMA,
    FEEDBACK_CONSUMPTION_SCHEMA,
    FEEDBACK_ENVELOPE_SCHEMA,
    ID_PREFIX_EVALUATION_MANIFEST,
    ID_PREFIX_FEEDBACK_CONSUMPTION,
    ID_PREFIX_FEEDBACK_ENVELOPE,
    ID_PREFIX_RUN_RECEIPT,
    RUN_RECEIPT_SCHEMA,
    CandidateMode,
    CandidatePassport,
    EvaluationManifest,
    FeedbackConsumption,
    FeedbackEnvelope,
    FeedbackSide,
    RunReceipt,
    compute_candidate_id,
    compute_passport_id,
    sha256_hex,
    text_sha256,
)

EVIDENCE_TABLES = (
    "candidate_passports",
    "feedback_envelopes",
    "feedback_consumptions",
    "evaluation_manifests",
    "run_receipts",
)


def _sha(payload: str = "x") -> str:
    return sha256_hex(payload)


def _ts() -> str:
    return "2026-07-11T00:00:00Z"


def make_passport(**overrides) -> CandidatePassport:
    kwargs = dict(
        schema=CANDIDATE_PASSPORT_SCHEMA,
        passport_id=compute_passport_id("run-1", 0, 0, 0),
        candidate_id=compute_candidate_id(_sha("buy"), _sha("sell"), "min_primary", "min"),
        run_id="run-1",
        round_no=0,
        gen_no=0,
        slot_no=0,
        parent_passport_id=None,
        mode=CandidateMode.SEED.value,
        lane="min",
        family="breakout",
        timeframe="min",
        buy_strategy_name="BuyA",
        sell_strategy_name="SellA",
        buy_sha256=_sha("buy"),
        sell_sha256=_sha("sell"),
        ast_fingerprint="ast-fp-1",
        rowset_fingerprint="rowset-fp-1",
        evidence_ids=("ev-1", "ev-2"),
        threshold_provenance={"source": "seed", "value": 1},
        manifest_id=f"{ID_PREFIX_EVALUATION_MANIFEST}{_sha('manifest')}",
        created_at=_ts(),
    )
    kwargs.update(overrides)
    return CandidatePassport(**kwargs)


def make_feedback(source_passport_id: str, **overrides) -> FeedbackEnvelope:
    rendered_text = "buy leg underperformed on segment X"
    kwargs = dict(
        schema=FEEDBACK_ENVELOPE_SCHEMA,
        feedback_id=f"{ID_PREFIX_FEEDBACK_ENVELOPE}{_sha('feedback')}",
        source_passport_id=source_passport_id,
        autopsy_kind="buy_autopsy",
        side=FeedbackSide.BUY.value,
        source_result_sha256=_sha("result"),
        directives=("tighten_entry", "widen_stop"),
        rendered_text=rendered_text,
        rendered_sha256=text_sha256(rendered_text),
        created_at=_ts(),
    )
    kwargs.update(overrides)
    return FeedbackEnvelope(**kwargs)


def make_consumption(feedback_id: str, target_passport_id: str, **overrides) -> FeedbackConsumption:
    kwargs = dict(
        schema=FEEDBACK_CONSUMPTION_SCHEMA,
        consumption_id=f"{ID_PREFIX_FEEDBACK_CONSUMPTION}{_sha('consumption')}",
        feedback_id=feedback_id,
        prompt_id="prompt-1",
        target_passport_id=target_passport_id,
        created_at=_ts(),
    )
    kwargs.update(overrides)
    return FeedbackConsumption(**kwargs)


def make_manifest(**overrides) -> EvaluationManifest:
    kwargs = dict(
        schema=EVALUATION_MANIFEST_SCHEMA,
        manifest_id=f"{ID_PREFIX_EVALUATION_MANIFEST}{_sha('manifest')}",
        run_id="run-1",
        profile="official_replay_v1_20260702",
        data="stock_min_back",
        universe="stock",
        methodology="min_primary",
        timeframe="min",
        scope="single_stock",
        session={"start_time": 90000, "end_time": 152800},
        period={"start_date": 20260101, "end_date": 20260630},
        capital=5000000,
        cost="engine_builtin",
        fill="engine_builtin_hoga_sweep",
        role="train",
        code_hash=_sha("code"),
        config_hash=_sha("config"),
        created_at=_ts(),
    )
    kwargs.update(overrides)
    return EvaluationManifest(**kwargs)


def make_receipt(**overrides) -> RunReceipt:
    kwargs = dict(
        schema=RUN_RECEIPT_SCHEMA,
        receipt_id=f"{ID_PREFIX_RUN_RECEIPT}{_sha('receipt')}",
        run_id="run-1",
        phase_id="CL-R07",
        outcome="go",
        stop_reason=None,
        budget_counters={"provider_calls": 1, "official_evaluations": 4},
        predecessor_ids=("prev-receipt-1",),
        artifact_hashes={"ledger": _sha("ledger"), "manifest": _sha("manifest")},
        created_at=_ts(),
    )
    kwargs.update(overrides)
    return RunReceipt(**kwargs)


def _open(tmp_path: Path, name: str = "loop_runs.db") -> LoopState:
    return LoopState(db_path=str(tmp_path / name), snapshot_dir=str(tmp_path / "snaps"))


# ---------------------------------------------------------------------
# 1) full chain append + query by run/gen/ID
# ---------------------------------------------------------------------
def test_append_full_chain_and_query_by_run_gen_id(tmp_path):
    st = _open(tmp_path)
    try:
        store = EvidenceStore(st)
        passport = make_passport()
        store.append_passport(passport)

        feedback = make_feedback(source_passport_id=passport.passport_id)
        store.append_feedback(feedback, run_id=passport.run_id)

        target = make_passport(
            passport_id=compute_passport_id("run-1", 0, 1, 0), gen_no=1
        )
        store.append_passport(target)
        consumption = make_consumption(
            feedback_id=feedback.feedback_id, target_passport_id=target.passport_id
        )
        store.append_consumption(consumption, run_id=passport.run_id)

        manifest = make_manifest(manifest_id=passport.manifest_id)
        store.append_manifest(manifest)

        receipt = make_receipt()
        store.append_receipt(receipt)

        assert store.get_passport(passport.passport_id) == passport.to_dict()
        by_run = store.passports_for_run("run-1")
        assert {p["passport_id"] for p in by_run} == {passport.passport_id, target.passport_id}
        by_gen = store.passports_for_gen("run-1", 0)
        assert [p["passport_id"] for p in by_gen] == [passport.passport_id]

        fb = store.feedback_for_passport(passport.passport_id)
        assert len(fb) == 1 and fb[0]["feedback_id"] == feedback.feedback_id

        # 이미 소비 기록(consumption)까지 남긴 뒤라 파생 쿼리에서 제외된다(UPDATE 없음).
        unconsumed_after = store.unconsumed_feedback("run-1")
        assert feedback.feedback_id not in {f["feedback_id"] for f in unconsumed_after}

        receipts = store.receipts_for_run("run-1")
        assert [r["receipt_id"] for r in receipts] == [receipt.receipt_id]
    finally:
        st.close()


def test_unconsumed_feedback_excludes_consumed(tmp_path):
    st = _open(tmp_path)
    try:
        store = EvidenceStore(st)
        passport = make_passport()
        store.append_passport(passport)
        feedback = make_feedback(source_passport_id=passport.passport_id)
        store.append_feedback(feedback, run_id=passport.run_id)
        assert len(store.unconsumed_feedback("run-1")) == 1

        consumption = make_consumption(
            feedback_id=feedback.feedback_id, target_passport_id=passport.passport_id
        )
        store.append_consumption(consumption, run_id=passport.run_id)
        assert store.unconsumed_feedback("run-1") == []
    finally:
        st.close()


# ---------------------------------------------------------------------
# 2) schema v11 migration idempotency
# ---------------------------------------------------------------------
def test_schema_v11_stable_across_repeated_opens(tmp_path):
    db = tmp_path / "loop_runs.db"
    st1 = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        assert st1.get_schema_version() == 11
    finally:
        st1.close()
    # 재오픈(기존 DB) — 멱등해야 하고 버전은 그대로 11.
    st2 = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        assert st2.get_schema_version() == 11
    finally:
        st2.close()
    # 세 번째 오픈도 안정적으로 11.
    st3 = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        assert st3.get_schema_version() == 11
        tables = {
            row[0]
            for row in st3._con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert set(EVIDENCE_TABLES).issubset(tables)
    finally:
        st3.close()


# ---------------------------------------------------------------------
# 3) SQL trace — never UPDATE/DELETE the 5 evidence tables
# ---------------------------------------------------------------------
def test_sql_trace_has_no_update_delete_on_evidence_tables(tmp_path):
    st = _open(tmp_path)
    traced = []
    st._con.set_trace_callback(traced.append)
    try:
        store = EvidenceStore(st)
        passport = make_passport()
        store.append_passport(passport)
        # 동일 payload 재삽입(no-op) 경로도 트레이스에 포함시킨다.
        store.append_passport(passport)
        feedback = make_feedback(source_passport_id=passport.passport_id)
        store.append_feedback(feedback, run_id=passport.run_id)
        consumption = make_consumption(
            feedback_id=feedback.feedback_id, target_passport_id=passport.passport_id
        )
        store.append_consumption(consumption, run_id=passport.run_id)
        manifest = make_manifest(manifest_id=passport.manifest_id)
        store.append_manifest(manifest)
        receipt = make_receipt()
        store.append_receipt(receipt)

        store.get_passport(passport.passport_id)
        store.passports_for_run("run-1")
        store.unconsumed_feedback("run-1")
        store.receipts_for_run("run-1")
    finally:
        st._con.set_trace_callback(None)
        st.close()

    offending = [
        sql
        for sql in traced
        if sql.strip().upper().startswith(("UPDATE", "DELETE"))
        and any(table in sql for table in EVIDENCE_TABLES)
    ]
    assert offending == [], f"unexpected UPDATE/DELETE on evidence tables: {offending}"


# ---------------------------------------------------------------------
# 4) readonly LoopState — no WAL/DDL, cannot write
# ---------------------------------------------------------------------
def test_readonly_loopstate_evidence_store_cannot_write(tmp_path):
    db = tmp_path / "loop_runs.db"
    st = _open(tmp_path)
    try:
        store = EvidenceStore(st)
        store.append_manifest(make_manifest())
    finally:
        st.close()

    ro_snaps = tmp_path / "ro_snaps"
    ro = LoopState(db_path=str(db), snapshot_dir=str(ro_snaps), readonly=True)
    try:
        assert ro.readonly is True
        ro_store = EvidenceStore(ro)
        # 읽기는 정상.
        manifests_before = ro._con.execute(
            "SELECT COUNT(*) FROM evaluation_manifests"
        ).fetchone()[0]
        assert manifests_before == 1
        # 쓰기 시도는 sqlite가 거부한다(읽기 전용 DB).
        with pytest.raises(sqlite3.OperationalError):
            ro_store.append_receipt(make_receipt())
    finally:
        ro.close()
    # readonly는 스냅샷 디렉토리를 만들지 않는다(쓰기 경로 전부 스킵).
    assert not ro_snaps.exists()


# ---------------------------------------------------------------------
# 5) idempotent duplicate vs conflicting duplicate
# ---------------------------------------------------------------------
def test_identical_duplicate_append_is_noop(tmp_path):
    st = _open(tmp_path)
    try:
        store = EvidenceStore(st)
        passport = make_passport()
        store.append_passport(passport)
        store.append_passport(passport)  # 동일 PK + 동일 payload — no-op.
        count = st._con.execute(
            "SELECT COUNT(*) FROM candidate_passports WHERE passport_id = ?",
            (passport.passport_id,),
        ).fetchone()[0]
        assert count == 1
    finally:
        st.close()


def test_conflicting_duplicate_append_raises_corruption_error(tmp_path):
    st = _open(tmp_path)
    try:
        store = EvidenceStore(st)
        # 동일 (run_id, round_no, gen_no, slot_no) -> 동일 passport_id, 다른 내용.
        p1 = make_passport(buy_strategy_name="BuyA")
        p2 = make_passport(buy_strategy_name="BuyB")
        assert p1.passport_id == p2.passport_id
        store.append_passport(p1)
        with pytest.raises(EvidenceCorruptionError):
            store.append_passport(p2)
        count = st._con.execute(
            "SELECT COUNT(*) FROM candidate_passports WHERE passport_id = ?",
            (p1.passport_id,),
        ).fetchone()[0]
        assert count == 1
        stored = store.get_passport(p1.passport_id)
        assert stored["buy_strategy_name"] == "BuyA"
    finally:
        st.close()


# ---------------------------------------------------------------------
# 6) broken FK -> IntegrityError (foreign_keys=ON in write-mode connection)
# ---------------------------------------------------------------------
def test_broken_foreign_key_raises_integrity_error(tmp_path):
    st = _open(tmp_path)
    try:
        fk_state = st._con.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_state == 1
        store = EvidenceStore(st)
        missing_passport_id = compute_passport_id("run-missing", 0, 0, 0)
        feedback = make_feedback(source_passport_id=missing_passport_id)
        with pytest.raises(sqlite3.IntegrityError):
            store.append_feedback(feedback, run_id="run-missing")
        count = st._con.execute("SELECT COUNT(*) FROM feedback_envelopes").fetchone()[0]
        assert count == 0
    finally:
        st.close()


# ---------------------------------------------------------------------
# 7) crash mid-transaction (before commit) leaves zero partial rows
# ---------------------------------------------------------------------
class _CrashOnCommitConnection(sqlite3.Connection):
    """commit()에서 항상 예외를 낸다 — 커밋 직전 크래시를 재현하는 테스트 전용 연결."""

    def commit(self):
        raise RuntimeError("simulated crash before commit")


def test_crash_before_commit_leaves_zero_partial_rows(tmp_path):
    db = tmp_path / "loop_runs.db"
    # 먼저 정상(쓰기) LoopState로 v11 스키마를 만든다.
    seed = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    seed.close()

    # EvidenceStore는 raw sqlite3.Connection도 받는다 — commit()이 항상 실패하는
    # 서브클래스 연결로 열어 "INSERT는 성공했지만 commit 직전 크래시"를 재현한다.
    con = sqlite3.connect(str(db), factory=_CrashOnCommitConnection)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        store = EvidenceStore(con, snapshot_dir=str(tmp_path / "snaps"))
        passport = make_passport()
        with pytest.raises(RuntimeError):
            store.append_passport(passport)

        count = con.execute(
            "SELECT COUNT(*) FROM candidate_passports WHERE passport_id = ?",
            (passport.passport_id,),
        ).fetchone()[0]
        assert count == 0
    finally:
        con.close()


# ---------------------------------------------------------------------
# 8) after commit: chain reconstructs from DB, matching snapshot exists
# ---------------------------------------------------------------------
def test_after_commit_chain_reconstructs_and_snapshot_exists(tmp_path):
    st = _open(tmp_path)
    try:
        store = EvidenceStore(st)
        passport = make_passport()
        store.append_passport(passport)
        feedback = make_feedback(source_passport_id=passport.passport_id)
        store.append_feedback(feedback, run_id=passport.run_id)
    finally:
        st.close()

    passport_snapshot = (
        Path(tmp_path / "snaps") / passport.run_id / "evidence" / "passport" / f"{passport.passport_id}.json"
    )
    feedback_snapshot = (
        Path(tmp_path / "snaps") / passport.run_id / "evidence" / "feedback" / f"{feedback.feedback_id}.json"
    )
    assert passport_snapshot.exists()
    assert feedback_snapshot.exists()
    assert json.loads(passport_snapshot.read_text(encoding="utf-8")) == passport.to_dict()
    assert json.loads(feedback_snapshot.read_text(encoding="utf-8")) == feedback.to_dict()

    # 재오픈해도 DB에서 그대로 복원된다(스냅샷은 거울일 뿐, DB가 정본).
    st2 = _open(tmp_path)
    try:
        store2 = EvidenceStore(st2)
        restored_passport = CandidatePassport.from_dict(store2.get_passport(passport.passport_id))
        assert restored_passport == passport
        fb = store2.feedback_for_passport(passport.passport_id)
        assert len(fb) == 1
        restored_feedback = FeedbackEnvelope.from_dict(fb[0])
        assert restored_feedback == feedback
    finally:
        st2.close()

# ---------------------------------------------------------------------
# 9) F2 — non-IntegrityError at INSERT rolls back (no stranded transaction)
# ---------------------------------------------------------------------
class _InsertFailCursor(sqlite3.Cursor):
    """INSERT에서 OperationalError를 낸다(IntegrityError 아님) — F2 재현용."""

    def execute(self, sql, *args, **kwargs):
        if sql.lstrip().upper().startswith("INSERT"):
            raise sqlite3.OperationalError("simulated non-integrity insert failure")
        return super().execute(sql, *args, **kwargs)


class _RollbackTrackingConnection(sqlite3.Connection):
    """cursor()가 INSERT-실패 커서를 내고 rollback 호출을 센다 — F2 검증용."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rollback_count = 0

    def cursor(self, *args, **kwargs):
        return super().cursor(factory=_InsertFailCursor)

    def rollback(self):
        self.rollback_count += 1
        return super().rollback()


def test_non_integrity_insert_error_rolls_back_no_stranded_txn(tmp_path):
    db = tmp_path / "loop_runs.db"
    seed = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    seed.close()

    con = sqlite3.connect(str(db), factory=_RollbackTrackingConnection)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        store = EvidenceStore(con, snapshot_dir=str(tmp_path / "snaps"))
        with pytest.raises(sqlite3.OperationalError):
            store.append_passport(make_passport())
        # F2: IntegrityError가 아닌 오류에서도 rollback이 실행돼 공유 커넥션에
        #   미완료 트랜잭션을 남기지 않는다.
        assert con.rollback_count >= 1
        assert con.in_transaction is False
        # 커넥션은 이후에도 정상 조회 가능(다음 writer가 막히지 않는다).
        assert con.execute("SELECT COUNT(*) FROM candidate_passports").fetchone()[0] == 0
    finally:
        con.close()
