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

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.evidence_store import EvidenceStore  # noqa: E402
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
