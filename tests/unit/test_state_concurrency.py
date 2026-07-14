"""US-005 Phase 2b — 루프 상태(state) 동시성 + resume 단위 테스트.

검증:
  (a) WAL 모드에서 쓰기 트랜잭션이 열린 상태에서도 별도 reader 연결이
      락 에러 없이 동시 읽기 가능하다.
  (b) resume: gen 0,1 기록 후 재오픈하면 get_last_completed_gen==1 이고
      다음 세대는 2 (중복 없음).
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401  (env-before-import 계약)
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


def test_wal_allows_concurrent_reader_during_write_txn(tmp_path):
    """WAL: writer가 미커밋 트랜잭션을 들고 있어도 별도 reader가 읽을 수 있다."""
    db = str(tmp_path / "loop_runs.db")
    snap = str(tmp_path / "snaps")
    st = LoopState(db_path=db, snapshot_dir=snap)
    rid = st.start_run(LoopConfig())

    # WAL 모드가 실제로 설정됐는지 확인.
    mode = st._con.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"

    # writer 연결에서 명시적 쓰기 트랜잭션을 연다 (커밋 보류).
    writer = sqlite3.connect(db)
    try:
        writer.isolation_level = None  # 수동 트랜잭션 제어.
        writer.execute("BEGIN IMMEDIATE")
        writer.execute(
            "INSERT INTO generations (run_id, gen_no, status, score, created_at) "
            "VALUES (?, ?, 'ok', 1.0, 0.0)",
            (rid, 99),
        )

        # writer 트랜잭션이 열린 채로, 별도 reader가 락 없이 읽는다.
        reader = sqlite3.connect(db)
        try:
            reader.execute("PRAGMA busy_timeout=2000")
            rows = reader.execute(
                "SELECT run_id, status FROM runs WHERE run_id = ?", (rid,)
            ).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == rid
        finally:
            reader.close()

        writer.execute("COMMIT")
    finally:
        writer.close()
        st.close()


def test_resume_continues_from_last_gen_without_duplicates(tmp_path):
    """gen 0,1 기록 → 재오픈 → last_completed==1, 다음 세대=2 (중복 없음)."""
    db = str(tmp_path / "loop_runs.db")
    snap = str(tmp_path / "snaps")
    config = LoopConfig()

    # --- 1차 세션: gen 0, 1 기록 ---
    st1 = LoopState(db_path=db, snapshot_dir=snap)
    rid = st1.start_run(config, run_id="run_test")
    for g in (0, 1):
        st1.record_generation(
            rid, g, buy_name=f"b{g}", sell_name=f"s{g}",
            status="ok", score=float(g), gate_passed=False, reason="ok",
            trade_count=0,
        )
    assert st1.get_last_completed_gen(rid) == 1
    assert st1.get_cumulative_generation_count(rid) == 2
    st1.close()

    # --- 2차 세션: 재오픈 + resume ---
    st2 = LoopState(db_path=db, snapshot_dir=snap)
    rid2 = st2.resume_or_start(config, run_id="run_test")
    assert rid2 == "run_test"
    assert st2.get_last_completed_gen(rid2) == 1
    next_gen = st2.get_last_completed_gen(rid2) + 1
    assert next_gen == 2

    # gen 2를 기록해도 0,1,2 만 존재 (중복 세대 없음).
    st2.record_generation(
        rid2, next_gen, buy_name="b2", sell_name="s2",
        status="ok", score=2.0, gate_passed=False, reason="ok", trade_count=0,
    )
    gens = st2.get_generations(rid2)
    gen_nos = [g["gen_no"] for g in gens]
    assert gen_nos == [0, 1, 2]
    assert len(gen_nos) == len(set(gen_nos))  # 중복 없음.
    st2.close()


def test_record_generation_upsert_no_duplicate_gen(tmp_path):
    """같은 (run_id, gen_no)를 두 번 기록하면 UPSERT — 행이 늘지 않는다."""
    db = str(tmp_path / "loop_runs.db")
    st = LoopState(db_path=db, snapshot_dir=str(tmp_path / "snaps"))
    rid = st.start_run(LoopConfig(), run_id="r")
    st.record_generation(rid, 0, buy_name="b", sell_name="s",
                         status="ok", score=1.0)
    st.record_generation(rid, 0, buy_name="b", sell_name="s",
                         status="ok", score=5.0)  # 같은 gen_no 재기록.
    gens = st.get_generations(rid)
    assert len(gens) == 1
    assert gens[0]["score"] == 5.0  # 최신 값으로 갱신.
    st.close()


# =====================================================================
# DR-03 — deterministic crash/resume for prompt identity: the content-addressed
#   rendered_prompt_id/content_sha256 for "the next prompt" after an interrupted
#   +resumed run MUST equal what an uninterrupted run would have produced for
#   that same generation, since the id is a pure function of already-persisted
#   deterministic content (not wall-clock time / row-count / sequence position).
# =====================================================================
def test_deterministic_next_prompt_identity_across_interrupted_and_uninterrupted_runs(tmp_path):
    config = LoopConfig()

    # --- uninterrupted run: gen0 then gen1 prompts recorded in one open session ---
    db_uninterrupted = str(tmp_path / "uninterrupted.db")
    st_u = LoopState(db_path=db_uninterrupted, snapshot_dir=str(tmp_path / "snaps_u"))
    rid_u = st_u.start_run(config, run_id="run_u")
    st_u.record_prompt(
        rid_u, 0, "buy", 1, system_text="sys-gen0", user_text="usr-gen0",
    )
    next_prompt_uninterrupted = st_u.record_prompt(
        rid_u, 1, "buy", 1, system_text="sys-gen1", user_text="usr-gen1",
    )
    st_u.close()

    # --- interrupted+resumed run: gen0 recorded, "crash" (close), reopen/resume,
    #     THEN gen1 (the next prompt) recorded — identical content to the run above.
    db_resumed = str(tmp_path / "resumed.db")
    st_r1 = LoopState(db_path=db_resumed, snapshot_dir=str(tmp_path / "snaps_r"))
    rid_r = st_r1.start_run(config, run_id="run_r")
    st_r1.record_prompt(
        rid_r, 0, "buy", 1, system_text="sys-gen0", user_text="usr-gen0",
    )
    st_r1.close()  # simulated crash/interruption

    st_r2 = LoopState(db_path=db_resumed, snapshot_dir=str(tmp_path / "snaps_r"))
    resumed_rid = st_r2.resume_or_start(config, run_id="run_r")
    assert resumed_rid == "run_r"
    next_prompt_resumed = st_r2.record_prompt(
        resumed_rid, 1, "buy", 1, system_text="sys-gen1", user_text="usr-gen1",
    )
    st_r2.close()

    # The next-prompt identity/hash is identical across both scenarios.
    assert next_prompt_resumed["rendered_prompt_id"] == next_prompt_uninterrupted["rendered_prompt_id"]
    assert next_prompt_resumed["content_sha256"] == next_prompt_uninterrupted["content_sha256"]
