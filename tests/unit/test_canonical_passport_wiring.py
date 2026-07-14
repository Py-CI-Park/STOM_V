"""CL-R04 todo10 — canonical controller passport/manifest/run-receipt wiring.

run_loop을 EvidenceStore(CL-R03)/evidence_contract(CL-R02)에 배선하는 계약을
검증한다. DEFAULT-OFF(getattr(config, "evidence_ledger_enabled", False))이
핵심 계약이라, OFF 경로가 기존 루프 테스트와 완전히 동일하게 동작함(zero
evidence writes)도 함께 확인한다. 네트워크/실제 backtest 없음 — 전부 monkeypatch.
"""

import json
import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.evidence_contract import (  # noqa: E402
    FEEDBACK_CONSUMPTION_SCHEMA,
    OUTCOME_GO,
    OUTCOME_INDETERMINATE_EXTERNAL_EFFECT,
    RUN_RECEIPT_SCHEMA,
    FeedbackConsumption,
    RunReceipt,
    build_manifest_v2,
    compute_consumption_id,
    compute_receipt_id,
    manifest_v2_content_hash,
)
from ai_strategy_loop.controller.evidence_store import (  # noqa: E402
    EvidenceOrphanError,
    EvidenceStore,
)
from ai_strategy_loop.controller.phase_contract import (  # noqa: E402
    EXECUTION_KIND_FIXED_BATCH,
    EXECUTION_KIND_RUN_LOOP,
    canonical_phase_owner_ok,
)
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402



def _seed_strategy_db(tmp_path, buy_codes=None, sell_codes=None):
    """namespaced buy/sell 코드를 tmp 전략 DB에 심는다(_read_strategy_code 경로)."""
    strat_db = str(tmp_path / "loop_strategies.db")
    con = sqlite3.connect(strat_db)
    con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    for name, code in (buy_codes or {}).items():
        con.execute('INSERT INTO stockbuy ("index", "전략코드") VALUES (?, ?)', (name, code))
    for name, code in (sell_codes or {}).items():
        con.execute('INSERT INTO stocksell ("index", "전략코드") VALUES (?, ?)', (name, code))
    con.commit()
    con.close()
    return strat_db


def _add_strategy(strat_db, buy_name=None, buy_code=None, sell_name=None, sell_code=None):
    con = sqlite3.connect(strat_db)
    if buy_name is not None:
        con.execute('INSERT INTO stockbuy ("index", "전략코드") VALUES (?, ?)', (buy_name, buy_code))
    if sell_name is not None:
        con.execute('INSERT INTO stocksell ("index", "전략코드") VALUES (?, ?)', (sell_name, sell_code))
    con.commit()
    con.close()


def _neutralize(monkeypatch):
    """provider 기동/전략 생성/엔진 호환을 무력화 (네트워크/DB 미사용)."""
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))

    def fake_generate_pair(provider, cfg, run_id, gen, feedback, **kwargs):
        return {
            "status": "ok",
            "buy_name": f"AILOOP_{run_id}_g{gen}_buy",
            "sell_name": f"AILOOP_{run_id}_g{gen}_sell",
            "tokens": 10,
        }

    monkeypatch.setattr(L, "_generate_pair", fake_generate_pair)
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")

    def fake_backtest(cfg, buy, sell):
        return L.BacktestOutcome(
            True, "success", "fake.csv",
            {"cagr": 1.0, "mdd_pct": 1.0, "trade_count": 5,
             "total_profit_krw": 1000.0, "total_profit_pct": 1.0},
            "ok",
        )

    monkeypatch.setattr(L, "run_backtest_for", fake_backtest)

    def fake_score(outcome, cfg):
        fit = FitnessResult(score=1.0, calmar=1.0, uptrend_r2=1.0, gate_passed=True,
                             reason="ok", cagr=1.0, mdd=1.0, trade_count=5, total_profit=1000.0)
        graded = GradedResult(
            graded=1.0, gate_passed=True, composite=1.0,
            trades_term=1.0, mdd_term=1.0, profit_term=1.0, uptrend_term=1.0,
            gate_distance="ok", cagr=1.0, mdd=1.0, trade_count=5, total_profit=1000.0,
            uptrend_r2=1.0,
        )
        return (fit, graded, None)

    monkeypatch.setattr(L, "_score_outcome", fake_score)


def _base_config(**overrides):
    kwargs = dict(
        provider="openrouter", max_generations=2, bt_engine_mode="cold",
        cost_cap_generations=100, cost_cap_tokens=None, bt_refine_from_best=False,
    )
    kwargs.update(overrides)
    return LoopConfig(**kwargs)


class TestCanonicalEvidenceWiringOn:
    def test_manifest_passports_and_receipts_two_generations(self, monkeypatch, tmp_path):
        rid = "evrun"
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0", f"AILOOP_{rid}_g1_buy": "R2 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0", f"AILOOP_{rid}_g1_sell": "S2 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize(monkeypatch)

        config = _base_config()
        config.evidence_ledger_enabled = True

        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(config, run_id=rid, state=st)
        assert summary["generations"] == 2

        # exactly 1 EvaluationManifest for the run.
        manifest_rows = st._con.execute(
            "SELECT manifest_id FROM evaluation_manifests WHERE run_id = ?", (rid,)
        ).fetchall()
        assert len(manifest_rows) == 1
        manifest_id_first_run = manifest_rows[0][0]

        ev = EvidenceStore(st)
        passports = ev.passports_for_run(rid)
        assert len(passports) == 2  # every recorded gen has a passport (no unlinked gen).

        gen0 = next(p for p in passports if p["gen_no"] == 0)
        gen1 = next(p for p in passports if p["gen_no"] == 1)
        assert gen0["parent_passport_id"] is None  # seed/gen0 root.
        assert gen1["parent_passport_id"] == gen0["passport_id"]  # linked lineage.
        assert gen0["manifest_id"] == manifest_id_first_run
        assert gen1["manifest_id"] == manifest_id_first_run

        receipts = ev.receipts_for_run(rid)
        outcomes = [r["outcome"] for r in receipts]
        assert outcomes.count("backtest_outcome") == 2
        assert outcomes.count("run_finished") == 1

        gens = st.get_generations(rid)
        assert len(gens) == 2
        for g in gens:
            assert g["status"] == "ok"

        st.close()

        # stable hashes across a re-run (resume): manifest_id must be identical
        # (idempotent freeze — same run_id + same config -> same content -> same id).
        _add_strategy(strat_db, buy_name=f"AILOOP_{rid}_g2_buy", buy_code="R3 > 0",
                      sell_name=f"AILOOP_{rid}_g2_sell", sell_code="S3 > 0")
        st2 = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        config2 = _base_config(max_generations=3)
        config2.evidence_ledger_enabled = True
        summary2 = L.run_loop(config2, run_id=rid, state=st2)
        assert summary2["generations"] == 3

        manifest_rows2 = st2._con.execute(
            "SELECT manifest_id FROM evaluation_manifests WHERE run_id = ?", (rid,)
        ).fetchall()
        assert len(manifest_rows2) == 1  # append_manifest was idempotent no-op on resume.
        assert manifest_rows2[0][0] == manifest_id_first_run

        ev2 = EvidenceStore(st2)
        passports2 = ev2.passports_for_run(rid)
        assert len(passports2) == 3
        # true idempotency (not merely a UNIQUE-swallowed insert): every passport,
        # including the post-resume gen, must reference the SAME existing
        # manifest_id -- no dangling manifest_id reference is allowed.
        for p in passports2:
            assert p["manifest_id"] == manifest_id_first_run, p
        gen2 = next(p for p in passports2 if p["gen_no"] == 2)
        assert gen2["manifest_id"] == manifest_id_first_run
        st2.close()

    def test_generated_code_missing_fails_candidate_before_backtest(self, monkeypatch, tmp_path):
        rid = "missrun"
        # empty 전략 DB -> _read_strategy_code always returns None for any name.
        strat_db = _seed_strategy_db(tmp_path)
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize(monkeypatch)

        backtest_calls = {"n": 0}

        def counting_backtest(cfg, buy, sell):
            backtest_calls["n"] += 1
            return L.BacktestOutcome(
                True, "success", "fake.csv",
                {"cagr": 1.0, "mdd_pct": 1.0, "trade_count": 5,
                 "total_profit_krw": 1000.0, "total_profit_pct": 1.0},
                "ok",
            )

        monkeypatch.setattr(L, "run_backtest_for", counting_backtest)

        config = _base_config(max_generations=1)
        config.evidence_ledger_enabled = True
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(config, run_id=rid, state=st)
        assert summary["generations"] == 1

        # backtest was never reached for the code-missing candidate.
        assert backtest_calls["n"] == 0

        ev = EvidenceStore(st)
        assert ev.passports_for_run(rid) == []  # no passport for a bodyless candidate.

        gens = st.get_generations(rid)
        assert len(gens) == 1
        assert gens[0]["status"] == "error"
        assert gens[0]["score"] == 0.0
        assert "evidence" in gens[0]["reason"]
        st.close()

    def test_seed_root_passport_has_no_parent(self, monkeypatch, tmp_path):
        rid = "seedrun"
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={"seedbuy": "R1 > 0"},
            sell_codes={"seedsell": "S1 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize(monkeypatch)

        config = _base_config(max_generations=1)
        config.evidence_ledger_enabled = True
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(
            config, run_id=rid, state=st, seed_buy="seedbuy", seed_sell="seedsell",
        )
        assert summary["generations"] == 1

        ev = EvidenceStore(st)
        passports = ev.passports_for_run(rid)
        assert len(passports) == 1
        assert passports[0]["mode"] == "seed"
        assert passports[0]["parent_passport_id"] is None
        st.close()


class TestCanonicalEvidenceWiringOff:
    def test_default_off_zero_evidence_writes(self, monkeypatch, tmp_path):
        rid = "offrun"
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize(monkeypatch)

        # evidence_ledger_enabled left unset -> getattr default False.
        config = _base_config(max_generations=1)
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(config, run_id=rid, state=st)
        assert summary["generations"] == 1

        for table in ("candidate_passports", "evaluation_manifests", "run_receipts"):
            count = st._con.execute(
                f"SELECT COUNT(*) FROM {table} WHERE run_id = ?", (rid,)
            ).fetchone()[0]
            assert count == 0, f"{table} must stay empty when evidence_ledger_enabled is off"

        gens = st.get_generations(rid)
        assert len(gens) == 1
        assert gens[0]["status"] == "ok"
        st.close()

    def test_explicit_false_also_writes_nothing(self, monkeypatch, tmp_path):
        rid = "offrun2"
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize(monkeypatch)

        config = _base_config(max_generations=1)
        config.evidence_ledger_enabled = False
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        L.run_loop(config, run_id=rid, state=st)

        count = st._con.execute(
            "SELECT COUNT(*) FROM candidate_passports WHERE run_id = ?", (rid,)
        ).fetchone()[0]
        assert count == 0
        st.close()


class TestFixedBatchCannotAdvanceCanonicalLineage:
    def test_phase_owner_guard(self):
        assert canonical_phase_owner_ok(EXECUTION_KIND_RUN_LOOP) is True
        assert canonical_phase_owner_ok(EXECUTION_KIND_FIXED_BATCH) is False

    def test_batch_script_asserts_guard_before_evaluating(self, monkeypatch, tmp_path):
        from ai_strategy_loop.controller import state as S
        from ai_strategy_loop.scripts import claude_candidate_batch_eval as B

        monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "loop_runs.db")
        monkeypatch.setattr(S, "_SNAPSHOT_DIR", tmp_path / "snaps")
        monkeypatch.setattr(B.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)

        class _FakeSession:
            def __init__(self, *a, **k):
                pass

            def prepare(self):
                # short-circuit before touching any real engine — the guard
                # assertion (right after start_run) must already have run by now.
                return {"status": "error", "message": "test short-circuit"}

        monkeypatch.setattr(B, "WarmBacktestSession", _FakeSession)

        pairs_path = tmp_path / "pairs.json"
        pairs_path.write_text("[]", encoding="utf-8")
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(json.dumps({}), encoding="utf-8")

        monkeypatch.setattr(sys, "argv", [
            "prog", "--pairs-json", str(pairs_path),
            "--config-json", str(cfg_path), "--run-id", "batchrun",
        ])
        rc = B.main()
        assert rc == 2  # reached prepare-failure branch -> guard assert didn't fire.

        # batch script never imports EvidenceStore / append_passport-capable objects.
        assert not hasattr(B, "EvidenceStore")

        count = None
        con = sqlite3.connect(str(tmp_path / "loop_runs.db"))
        try:
            count = con.execute(
                "SELECT COUNT(*) FROM candidate_passports WHERE run_id = ?", ("batchrun",)
            ).fetchone()[0]
        finally:
            con.close()
        assert count == 0


class TestDr02ManifestV2Wiring:
    """DR-02 — additive Manifest v2 typed contract (evidence_contract.ManifestV2) plus
    its loop.py wiring (controller.loop._evidence_build_manifest_v2), default OFF."""

    def _sample_payload(self, v1):
        return {
            "effective_profile_hash": "0" * 64,
            "effective_profile_name": "fast",
            "data": {"source": v1.data},
            "universe": {"codes": v1.universe},
            "engine": {"engine": "ai_strategy_loop"},
            "cost": dict(v1.cost),
            "fill": dict(v1.fill),
            "capital": dict(v1.capital),
            "session": dict(v1.session),
            "prompt": {"bundle_identity": v1.manifest_id},
            "seed": {"seed_mode": "fresh"},
            "code": {"code_hash": v1.code_hash},
            "config": {"config_hash": v1.config_hash},
            "created_at": "2026-01-01T00:00:00+00:00",
        }

    def test_build_manifest_v2_binds_every_mandatory_category(self):
        v1 = L._evidence_build_manifest(_base_config(), "run-v2")
        payload = self._sample_payload(v1)

        manifest_v2 = build_manifest_v2(payload)

        assert manifest_v2.manifest_contract == "ManifestV2"
        assert manifest_v2.effective_profile_hash == "0" * 64
        for category in (
            "data", "universe", "engine", "cost", "fill", "capital", "session",
            "prompt", "seed", "code", "config",
        ):
            assert len(getattr(manifest_v2, category)) > 0, f"{category} must be bound"

        # canonical content hash is a deterministic function of the frozen payload.
        assert manifest_v2_content_hash(manifest_v2) == manifest_v2_content_hash(build_manifest_v2(payload))

    def test_build_manifest_v2_blocks_certification_on_missing_mandatory_field(self):
        v1 = L._evidence_build_manifest(_base_config(), "run-v2-missing")
        payload = self._sample_payload(v1)

        for missing_key in ("data", "cost", "session", "code", "prompt"):
            broken = dict(payload)
            broken.pop(missing_key)
            with pytest.raises(ValueError):
                build_manifest_v2(broken)

        empty_category = dict(payload)
        empty_category["fill"] = {}
        with pytest.raises(ValueError):
            build_manifest_v2(empty_category)

    def test_loop_wiring_default_off_builds_nothing(self):
        # Defaults-OFF invariant: config.manifest_v2_enabled defaults False -> the
        # wiring point in loop.py never builds a ManifestV2 (v11 unchanged).
        cfg = _base_config()
        assert cfg.manifest_v2_enabled is False
        v1 = L._evidence_build_manifest(cfg, "run-off")
        assert L._evidence_build_manifest_v2(cfg, "run-off", v1) is None

    def test_loop_wiring_enabled_builds_bound_manifest(self):
        cfg = _base_config()
        cfg.manifest_v2_enabled = True
        v1 = L._evidence_build_manifest(cfg, "run-on")
        manifest_v2 = L._evidence_build_manifest_v2(cfg, "run-on", v1)
        assert manifest_v2 is not None
        assert manifest_v2.manifest_id == v1.manifest_id
        assert len(manifest_v2.effective_profile_hash) == 64


class TestDr03FailClosedEvidenceReceipt:
    """DR-03 acceptance #3 — an evidence I/O failure while appending a RunReceipt
    must never let the original (e.g. GO/success) outcome stand as durably
    certified; it must surface OUTCOME_INDETERMINATE_EXTERNAL_EFFECT instead,
    with no automatic retry of the original receipt.
    """

    def _sample_receipt(self, run_id="run-1", phase_id="gen0", outcome=OUTCOME_GO):
        return RunReceipt(
            schema=RUN_RECEIPT_SCHEMA,
            receipt_id=compute_receipt_id(run_id, phase_id, outcome, None),
            run_id=run_id,
            phase_id=phase_id,
            outcome=outcome,
            stop_reason=None,
            budget_counters={"gen_no": 0},
            predecessor_ids=(),
            artifact_hashes={},
            created_at="2026-07-14T00:00:00+00:00",
        )

    def test_successful_append_returns_original_outcome(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "r.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            store = EvidenceStore(st)
            receipt = self._sample_receipt()
            outcome = L._evidence_safe_append_receipt(store, receipt)
            assert outcome == OUTCOME_GO
            rows = store.receipts_for_run("run-1")
            assert len(rows) == 1
            assert rows[0]["outcome"] == OUTCOME_GO
        finally:
            st.close()

    def test_io_failure_never_yields_go_and_appends_indeterminate_no_retry(self, tmp_path, monkeypatch):
        st = LoopState(db_path=str(tmp_path / "r2.db"), snapshot_dir=str(tmp_path / "s2"))
        try:
            store = EvidenceStore(st)
            receipt = self._sample_receipt(run_id="run-2", phase_id="gen1")
            calls = []
            original_append = store.append_receipt

            def flaky_append(r):
                calls.append(r.receipt_id)
                if r.receipt_id == receipt.receipt_id:
                    raise sqlite3.OperationalError("simulated evidence write failure")
                return original_append(r)

            monkeypatch.setattr(store, "append_receipt", flaky_append)
            outcome = L._evidence_safe_append_receipt(store, receipt)
            assert outcome == OUTCOME_INDETERMINATE_EXTERNAL_EFFECT
            # exactly two attempts: the original (failed) + one replacement — no retry loop.
            assert len(calls) == 2
            rows = store.receipts_for_run("run-2")
            assert len(rows) == 1
            assert rows[0]["outcome"] == OUTCOME_INDETERMINATE_EXTERNAL_EFFECT
            assert rows[0]["stop_reason"] == "evidence_io_failure"
            assert all(r["outcome"] != OUTCOME_GO for r in rows)
        finally:
            st.close()

    def test_replacement_also_failing_still_returns_indeterminate_not_go(self, tmp_path, monkeypatch):
        st = LoopState(db_path=str(tmp_path / "r3.db"), snapshot_dir=str(tmp_path / "s3"))
        try:
            store = EvidenceStore(st)
            receipt = self._sample_receipt(run_id="run-3", phase_id="gen2")
            calls = []

            def always_fail(r):
                calls.append(r.receipt_id)
                raise sqlite3.OperationalError("simulated evidence write failure")

            monkeypatch.setattr(store, "append_receipt", always_fail)
            outcome = L._evidence_safe_append_receipt(store, receipt)
            assert outcome == OUTCOME_INDETERMINATE_EXTERNAL_EFFECT
            # original attempt + exactly one replacement attempt — no retry loop.
            assert len(calls) == 2
            assert store.receipts_for_run("run-3") == []
        finally:
            st.close()


class TestDr03RenderedOnlyConsumptionOrphanPropagates:
    """DR-03 acceptance #2/#4 — loop._evidence_safe_append_consumption absorbs
    transient evidence I/O failures (existing robustness contract) but MUST NOT
    absorb EvidenceOrphanError — a consumption referencing a prompt_id that was
    never actually rendered/persisted is a real correctness defect, not a
    transient I/O hiccup, and must surface loudly instead of being swallowed.
    """

    def test_orphan_prompt_id_raises_and_writes_nothing(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "o.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            store = EvidenceStore(st)
            feedback_id = "fe_" + "0" * 64
            target_passport_id = "cp_" + "0" * 64
            prompt_id = "rp_" + "0" * 64  # never actually rendered/persisted.
            consumption = FeedbackConsumption(
                schema=FEEDBACK_CONSUMPTION_SCHEMA,
                consumption_id=compute_consumption_id(feedback_id, prompt_id, target_passport_id),
                feedback_id=feedback_id,
                prompt_id=prompt_id,
                target_passport_id=target_passport_id,
                created_at="2026-07-14T00:00:00+00:00",
            )
            with pytest.raises(EvidenceOrphanError):
                L._evidence_safe_append_consumption(
                    store, consumption, "run-1", require_rendered=True
                )
            count = st._con.execute(
                "SELECT COUNT(*) FROM feedback_consumptions WHERE consumption_id = ?",
                (consumption.consumption_id,),
            ).fetchone()[0]
            assert count == 0
        finally:
            st.close()

    def test_require_rendered_false_default_absorbs_as_before(self, tmp_path):
        # default (require_rendered=False) keeps the pre-DR-03 robustness contract:
        # a bad prompt_id (or any transient issue) is absorbed, returns False, and
        # never raises — existing callers are unaffected.
        st = LoopState(db_path=str(tmp_path / "o2.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            store = EvidenceStore(st)
            feedback_id = "fe_" + "1" * 64
            target_passport_id = "cp_" + "1" * 64
            prompt_id = "rp_" + "1" * 64
            consumption = FeedbackConsumption(
                schema=FEEDBACK_CONSUMPTION_SCHEMA,
                consumption_id=compute_consumption_id(feedback_id, prompt_id, target_passport_id),
                feedback_id=feedback_id,
                prompt_id=prompt_id,
                target_passport_id=target_passport_id,
                created_at="2026-07-14T00:00:00+00:00",
            )
            # feedback_id/target_passport_id don't exist -> FK IntegrityError on
            # write, which IS absorbed (transient/robustness path, not the
            # rendered-only guard).
            ok = L._evidence_safe_append_consumption(store, consumption, "run-1")
            assert ok is False
        finally:
            st.close()
