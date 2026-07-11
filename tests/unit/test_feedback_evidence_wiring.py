"""CL-R05 todo11 — durable feedback envelope, resume restoration, and
consumption proof wiring (DEFAULT-OFF, additive).

run_loop을 FeedbackEnvelope/FeedbackConsumption(evidence_contract, CL-R02)과
EvidenceStore.append_feedback/append_consumption/unconsumed_feedback(CL-R03)에
배선하는 계약을 검증한다.

핵심 계약:
  1. gen N의 autopsy가 만든 렌더 피드백은 gen N의 CandidatePassport를 source로
     하는 FeedbackEnvelope로 동결된다(record_generation commit 이후 seam).
  2. gen N+1은 그 봉투를 실제로 소비했다는 FeedbackConsumption을 gen N+1의
     CandidatePassport(target)가 실제로 존재한 뒤에만 남긴다.
  3. provider/생성 실패나 코드 확보 실패로 target passport가 못 생기면 소비를
     남기지 않는다 — 봉투는 unconsumed로 남고, 다음 성공한 세대가 정확히 한 번
     소비한다(이중 소비 없음).
  4. evidence_ledger_enabled=False(기본)면 두 테이블 모두 0행 — transient
     next_autopsy_feedback/next_sell_feedback 경로는 기존과 완전히 동일하다.

네트워크/실제 backtest 없음 — 전부 monkeypatch.
"""

import os
import re
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.evidence_store import EvidenceStore  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402

_NO_UPDATE_DELETE_ON_EVIDENCE = re.compile(
    r"^\s*(UPDATE|DELETE)\s+.*\b"
    r"(feedback_envelopes|feedback_consumptions|candidate_passports)\b",
    re.IGNORECASE,
)


# =====================================================================
# shared fixtures/helpers
# =====================================================================
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


def _neutralize_common(monkeypatch):
    """provider 기동/엔진 호환/출력을 무력화 (네트워크/DB 미사용)."""
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda cfg: (object(), False))
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda *a, **k: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *a, **k: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *a, **k: "")


def _ok_backtest(cfg, buy, sell):
    return L.BacktestOutcome(
        True, "success", "fake.csv",
        {"cagr": 1.0, "mdd_pct": 1.0, "trade_count": 5,
         "total_profit_krw": 1000.0, "total_profit_pct": 1.0},
        "ok",
    )


def _ok_score(outcome, cfg):
    fit = FitnessResult(score=1.0, calmar=1.0, uptrend_r2=1.0, gate_passed=True,
                         reason="ok", cagr=1.0, mdd=1.0, trade_count=5, total_profit=1000.0)
    graded = GradedResult(
        graded=1.0, gate_passed=True, composite=1.0,
        trades_term=1.0, mdd_term=1.0, profit_term=1.0, uptrend_term=1.0,
        gate_distance="ok", cagr=1.0, mdd=1.0, trade_count=5, total_profit=1000.0,
        uptrend_r2=1.0,
    )
    return (fit, graded, None)


def _base_config(**overrides):
    kwargs = dict(
        provider="openrouter", max_generations=1, bt_engine_mode="cold",
        cost_cap_generations=100, cost_cap_tokens=None, autopsy_enabled=True,
    )
    kwargs.update(overrides)
    return LoopConfig(**kwargs)


def _install_ok_generation_pipeline(monkeypatch, captured, feedback_text="LOSS: avoid pattern X",
                                     fail_gens=None):
    """정상 생성+백테+채점 파이프라인 + gen별 강제 실패(fail_gens)를 설치한다.

    fail_gens에 속한 gen_no는 _generate_pair가 status='error'를 돌려(provider/생성
    실패를 흉내) target passport가 생기지 않게 한다.
    """
    fail_gens = fail_gens or set()

    def fake_generate_pair(provider, cfg, run_id, gen, feedback, **kwargs):
        captured.append({"gen": gen, "feedback": feedback})
        if gen in fail_gens:
            return {"status": "error", "reason": "simulated provider failure"}
        return {
            "status": "ok",
            "buy_name": f"AILOOP_{run_id}_g{gen}_buy",
            "sell_name": f"AILOOP_{run_id}_g{gen}_sell",
            "tokens": 1,
        }

    monkeypatch.setattr(L, "_generate_pair", fake_generate_pair)
    monkeypatch.setattr(L, "run_backtest_for", _ok_backtest)
    monkeypatch.setattr(L, "_score_outcome", _ok_score)
    monkeypatch.setattr(
        L, "_build_feedback",
        lambda *a, **k: (feedback_text, None, None),
    )


# =====================================================================
# 1) gen0 loss -> exactly ONE envelope; gen1 -> exactly ONE consumption;
#    append-only (no UPDATE/DELETE on evidence tables).
# =====================================================================
class TestEnvelopeConsumptionChain:
    def test_gen0_envelope_gen1_consumption_chain(self, monkeypatch, tmp_path):
        rid = "fbrun"
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0", f"AILOOP_{rid}_g1_buy": "R2 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0", f"AILOOP_{rid}_g1_sell": "S2 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize_common(monkeypatch)

        captured = []
        _install_ok_generation_pipeline(monkeypatch, captured, feedback_text="LOSS: avoid pattern X")

        config = _base_config(max_generations=2)
        config.evidence_ledger_enabled = True

        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        sql_log = []
        st._con.set_trace_callback(sql_log.append)
        summary = L.run_loop(config, run_id=rid, state=st)
        assert summary["generations"] == 2

        ev = EvidenceStore(st)
        passports = ev.passports_for_run(rid)
        gen0 = next(p for p in passports if p["gen_no"] == 0)
        gen1 = next(p for p in passports if p["gen_no"] == 1)

        # exactly ONE FeedbackEnvelope linked to gen0's passport.
        gen0_envelopes = ev.feedback_for_passport(gen0["passport_id"])
        assert len(gen0_envelopes) == 1
        envelope = gen0_envelopes[0]
        assert envelope["side"] == "buy"
        assert envelope["rendered_text"] == "LOSS: avoid pattern X"
        assert envelope["source_passport_id"] == gen0["passport_id"]

        # exactly ONE FeedbackConsumption linking (source envelope, prompt, gen1 target).
        consumption_rows = st._con.execute(
            "SELECT consumption_id, feedback_id, prompt_id, target_passport_id "
            "FROM feedback_consumptions"
        ).fetchall()
        assert len(consumption_rows) == 1
        _cid, fid, pid, target = consumption_rows[0]
        assert fid == envelope["feedback_id"]
        assert target == gen1["passport_id"]
        assert pid  # non-empty stable prompt-scoped id.

        # the rendered feedback string still flowed transiently into gen1's
        # generation call (same-process path — no behavior change).
        gen1_call = next(c for c in captured if c["gen"] == 1)
        assert gen1_call["feedback"] == "LOSS: avoid pattern X"

        # append-only proof: no UPDATE/DELETE against any evidence table.
        offending = [s for s in sql_log if s and _NO_UPDATE_DELETE_ON_EVIDENCE.search(s)]
        assert offending == [], f"unexpected UPDATE/DELETE on evidence tables: {offending}"

        st.close()

    def test_rendered_string_without_consumption_row_is_not_learning_proof(self, monkeypatch, tmp_path):
        """봉투(rendered_text)만 있고 소비 행이 없으면 학습 증거로 인정하지 않는다 —
        gen0 하나짜리 run은 다음 세대가 없어 소비가 생기지 않아야 한다."""
        rid = "onegen"
        strat_db = _seed_strategy_db(
            tmp_path, buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize_common(monkeypatch)
        captured = []
        _install_ok_generation_pipeline(monkeypatch, captured, feedback_text="LOSS: single gen")

        config = _base_config(max_generations=1)
        config.evidence_ledger_enabled = True
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(config, run_id=rid, state=st)
        assert summary["generations"] == 1

        ev = EvidenceStore(st)
        passports = ev.passports_for_run(rid)
        assert len(passports) == 1
        gen0_envelopes = ev.feedback_for_passport(passports[0]["passport_id"])
        assert len(gen0_envelopes) == 1  # rendered feedback exists...

        consumption_count = st._con.execute(
            "SELECT COUNT(*) FROM feedback_consumptions"
        ).fetchone()[0]
        assert consumption_count == 0  # ...but no consumption row -> not learning proof.
        st.close()


# =====================================================================
# 2) stop/resume safety: pre-passport failures leave the envelope
#    unconsumed; the next successful generation consumes it exactly once.
# =====================================================================
class TestResumeSafety:
    def test_provider_generation_failure_then_resume_consumes_exactly_once(self, monkeypatch, tmp_path):
        rid = "resumeprov"
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0", f"AILOOP_{rid}_g2_buy": "R3 > 0",
                       f"AILOOP_{rid}_g3_buy": "R4 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0", f"AILOOP_{rid}_g2_sell": "S3 > 0",
                        f"AILOOP_{rid}_g3_sell": "S4 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize_common(monkeypatch)

        captured = []
        _install_ok_generation_pipeline(monkeypatch, captured, feedback_text="LOSS: gen0",
                                         fail_gens={1})

        config = _base_config(max_generations=1)
        config.evidence_ledger_enabled = True
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))

        # step 1 — gen0 succeeds, produces exactly one envelope.
        summary1 = L.run_loop(config, run_id=rid, state=st)
        assert summary1["generations"] == 1
        ev = EvidenceStore(st)
        gen0_passport = ev.passports_for_run(rid)[0]
        gen0_envelope_id = ev.feedback_for_passport(gen0_passport["passport_id"])[0]["feedback_id"]
        assert st._con.execute("SELECT COUNT(*) FROM feedback_consumptions").fetchone()[0] == 0

        # step 2 — resume: gen1's _generate_pair fails (crash before prompt/passport).
        #   the envelope must remain unconsumed.
        config2 = _base_config(max_generations=2)
        config2.evidence_ledger_enabled = True
        summary2 = L.run_loop(config2, run_id=rid, state=st)
        assert summary2["generations"] == 2  # gen1 recorded as error, still "completed".
        assert st._con.execute("SELECT COUNT(*) FROM feedback_consumptions").fetchone()[0] == 0
        unconsumed_ids = {row["feedback_id"] for row in ev.unconsumed_feedback(rid)}
        assert gen0_envelope_id in unconsumed_ids

        # step 3 — resume again: gen2 succeeds -> consumes gen0's envelope exactly once.
        config3 = _base_config(max_generations=3)
        config3.evidence_ledger_enabled = True
        summary3 = L.run_loop(config3, run_id=rid, state=st)
        assert summary3["generations"] == 3
        gen2_passport = next(p for p in ev.passports_for_run(rid) if p["gen_no"] == 2)
        rows = st._con.execute(
            "SELECT feedback_id, target_passport_id FROM feedback_consumptions"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == gen0_envelope_id
        assert rows[0][1] == gen2_passport["passport_id"]

        # step 4 — further resume must never double-consume gen0's envelope again.
        config4 = _base_config(max_generations=4)
        config4.evidence_ledger_enabled = True
        summary4 = L.run_loop(config4, run_id=rid, state=st)
        assert summary4["generations"] == 4
        gen0_consumption_count = st._con.execute(
            "SELECT COUNT(*) FROM feedback_consumptions WHERE feedback_id = ?",
            (gen0_envelope_id,),
        ).fetchone()[0]
        assert gen0_consumption_count == 1  # still exactly once, never doubled.
        st.close()

    def test_code_missing_pre_passport_failure_leaves_envelope_unconsumed(self, monkeypatch, tmp_path):
        """crash-after-prompt-before-passport 근사: 생성은 성공했지만(이름 반환) 코드
        본문을 못 읽어(해시 불가) passport가 못 생기는 경우도 소비를 남기지 않는다."""
        rid = "resumecode"
        # gen1 코드는 처음엔 DB에 없음 -> _read_strategy_code가 None -> passport 실패.
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0", f"AILOOP_{rid}_g2_buy": "R3 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0", f"AILOOP_{rid}_g2_sell": "S3 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize_common(monkeypatch)
        captured = []
        _install_ok_generation_pipeline(monkeypatch, captured, feedback_text="LOSS: gen0b")

        config = _base_config(max_generations=1)
        config.evidence_ledger_enabled = True
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary1 = L.run_loop(config, run_id=rid, state=st)
        assert summary1["generations"] == 1

        ev = EvidenceStore(st)
        gen0_passport = ev.passports_for_run(rid)[0]
        gen0_envelope_id = ev.feedback_for_passport(gen0_passport["passport_id"])[0]["feedback_id"]

        # step 2 — gen1: code missing in strat_db -> passport never created -> no consumption.
        config2 = _base_config(max_generations=2)
        config2.evidence_ledger_enabled = True
        summary2 = L.run_loop(config2, run_id=rid, state=st)
        assert summary2["generations"] == 2
        assert st._con.execute("SELECT COUNT(*) FROM feedback_consumptions").fetchone()[0] == 0
        gens = st.get_generations(rid)
        gen1_row = next(g for g in gens if g["gen_no"] == 1)
        assert gen1_row["status"] == "error"
        assert "evidence" in gen1_row["reason"]

        # step 3 — resume: code now present for gen2 -> succeeds -> consumes gen0's
        #   envelope exactly once.
        config3 = _base_config(max_generations=3)
        config3.evidence_ledger_enabled = True
        summary3 = L.run_loop(config3, run_id=rid, state=st)
        assert summary3["generations"] == 3
        rows = st._con.execute(
            "SELECT feedback_id FROM feedback_consumptions"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == gen0_envelope_id
        st.close()


# =====================================================================
# 3) DEFAULT-OFF: zero evidence rows, transient feedback path unchanged.
# =====================================================================
class TestDefaultOff:
    def test_flag_off_zero_rows_and_transient_feedback_unchanged(self, monkeypatch, tmp_path):
        rid = "offfb"
        strat_db = _seed_strategy_db(
            tmp_path,
            buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0", f"AILOOP_{rid}_g1_buy": "R2 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0", f"AILOOP_{rid}_g1_sell": "S2 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize_common(monkeypatch)
        captured = []
        _install_ok_generation_pipeline(monkeypatch, captured, feedback_text="LOSS: off path")

        # evidence_ledger_enabled left unset -> getattr default False.
        config = _base_config(max_generations=2)
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        summary = L.run_loop(config, run_id=rid, state=st)
        assert summary["generations"] == 2

        for table in ("feedback_envelopes", "feedback_consumptions", "candidate_passports"):
            count = st._con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == 0, f"{table} must stay empty when evidence_ledger_enabled is off"

        # transient rendered-text feedback still flows into gen1's generation call
        # exactly as before (byte-identical behavior when the flag is off).
        gen1_call = next(c for c in captured if c["gen"] == 1)
        assert gen1_call["feedback"] == "LOSS: off path"
        st.close()

    def test_explicit_false_also_zero_rows(self, monkeypatch, tmp_path):
        rid = "offfb2"
        strat_db = _seed_strategy_db(
            tmp_path, buy_codes={f"AILOOP_{rid}_g0_buy": "R1 > 0"},
            sell_codes={f"AILOOP_{rid}_g0_sell": "S1 > 0"},
        )
        monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", strat_db)
        _neutralize_common(monkeypatch)
        captured = []
        _install_ok_generation_pipeline(monkeypatch, captured, feedback_text="LOSS: explicit off")

        config = _base_config(max_generations=1)
        config.evidence_ledger_enabled = False
        st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "s"))
        L.run_loop(config, run_id=rid, state=st)

        count = st._con.execute("SELECT COUNT(*) FROM feedback_envelopes").fetchone()[0]
        assert count == 0
        st.close()
