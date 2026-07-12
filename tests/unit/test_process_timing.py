"""#64 — 프로세스별 진행률·진행시간·완료시간 단위 테스트.

대시보드에 각 프로세스 단계(생성→백테→채점→부검→반복)의 이산 진행 + 단계별 경과초 +
세대 경과/완료시각을 표시하기 위한 발행 계약을 검증한다. 정직 범위: 백테는 블로킹
subprocess라 단계 *내부* 연속%(N/M 종목)는 LIVE 수신 불가 — 이산 단계 진행 + 단계별
경과초 + 세대 경과까지만 발행한다(가짜 N/M 미약속).

검증:
  1) contract.LatestInfo: phase_started_at/gen_started_at/step_timings 3필드 기본값 +
     구 상태(미발행) 하위호환.
  2) to_loop_state: latest dict의 timing 필드를 LatestInfo로 정규화 운반(+잘못된 타입 방어).
  3) loop._phase_step_name: phase → 이산 단계명 매핑(complete/stopping=None).
  4) loop._publish_live: phase 경계에서 _timing 컨텍스트를 갱신해 발행한다
     (time.time monkeypatch로 결정론 검증) — *_start가 phase_t0 리셋, *_done/*_end가
     step_timings 누적, generate_start가 gen_t0 리셋. _timing 무인자면 미발행(하위호환).
  5) app._generation_durations_payload: 인접 created_at 차분 + started_at 보정으로
     세대 소요초 산출(과거 run retroactive). 음수/None 방어.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.state import LoopState, to_loop_state  # noqa: E402
from ai_strategy_loop.fitness.score import FitnessResult, GradedResult  # noqa: E402


# =====================================================================
# 1) contract.LatestInfo — 3 신규 필드 기본값 + 하위호환.
# =====================================================================
class TestLatestInfoTimingFields:
    def test_defaults_are_backward_compatible(self):
        # 신규 필드는 기본값(0.0/빈 dict)이라 발행하지 않던 구 상태도 검증 통과.
        li = C.LatestInfo()
        assert li.phase_started_at == 0.0
        assert li.gen_started_at == 0.0
        assert li.step_timings == {}

    def test_old_state_without_timing_fields_validates(self):
        # 구 current_state.json(타이밍 필드 미포함)도 검증 통과 → 기본값.
        old_latest = {
            "phase": "backtest_start",
            "last_checkpoint": "csv",
            "message": "running",
            "recent_logs": ["[backtest_start]"],
            "current_step": 1,
        }
        li = C.LatestInfo.model_validate(old_latest)
        assert li.phase_started_at == 0.0
        assert li.gen_started_at == 0.0
        assert li.step_timings == {}

    def test_timing_fields_roundtrip_in_json(self):
        li = C.LatestInfo(
            phase="score_done", phase_started_at=1000.0, gen_started_at=900.0,
            step_timings={"generate": 12.5, "backtest": 60.0},
        )
        revalidated = C.LatestInfo.model_validate(li.model_dump())
        assert revalidated.phase_started_at == 1000.0
        assert revalidated.gen_started_at == 900.0
        assert revalidated.step_timings == {"generate": 12.5, "backtest": 60.0}


# =====================================================================
# 2) to_loop_state — latest timing 필드 정규화 운반.
# =====================================================================
class TestToLoopStateCarriesTiming:
    def _summary(self):
        return {"run_id": "r64", "best_gen": -1}

    def test_carries_timing_fields(self):
        ls = to_loop_state(
            self._summary(), [], config=LoopConfig(), status="running",
            latest={
                "phase": "backtest_end", "current_step": 1,
                "phase_started_at": 2000.0, "gen_started_at": 1950.0,
                "step_timings": {"generate": 10.0, "backtest": 50.0},
            },
        )
        assert ls.latest.phase_started_at == 2000.0
        assert ls.latest.gen_started_at == 1950.0
        assert ls.latest.step_timings == {"generate": 10.0, "backtest": 50.0}

    def test_timing_defaults_when_latest_omits(self):
        # latest에 timing 키가 없으면(기존 호출부) 0.0/빈 dict(하위호환).
        ls = to_loop_state(
            self._summary(), [], config=LoopConfig(), status="running",
            latest={"phase": "loop_start", "current_step": 0},
        )
        assert ls.latest.phase_started_at == 0.0
        assert ls.latest.gen_started_at == 0.0
        assert ls.latest.step_timings == {}

    def test_step_timings_bad_types_are_filtered(self):
        # 잘못된 값(문자열 등)은 float 변환 실패 시 건너뛴다(방어).
        ls = to_loop_state(
            self._summary(), [], config=LoopConfig(), status="running",
            latest={
                "phase": "score_done",
                "step_timings": {"generate": "oops", "backtest": 42.0},
            },
        )
        assert ls.latest.step_timings == {"backtest": 42.0}

    def test_step_timings_non_dict_is_empty(self):
        ls = to_loop_state(
            self._summary(), [], config=LoopConfig(), status="running",
            latest={"phase": "score_done", "step_timings": ["not", "a", "dict"]},
        )
        assert ls.latest.step_timings == {}


# =====================================================================
# 3) _phase_step_name — phase → 이산 단계명.
# =====================================================================
class TestPhaseStepName:
    def test_active_phases_map_to_step_names(self):
        assert L._phase_step_name("generate_start") == "generate"
        assert L._phase_step_name("generate_done") == "generate"
        assert L._phase_step_name("backtest_start") == "backtest"
        assert L._phase_step_name("backtest_end") == "backtest"
        assert L._phase_step_name("score_start") == "score"
        assert L._phase_step_name("score_done") == "score"
        assert L._phase_step_name("autopsy_start") == "autopsy"
        assert L._phase_step_name("autopsy_done") == "autopsy"
        assert L._phase_step_name("generation_done") == "iterate"

    def test_complete_and_stopping_are_none(self):
        # 활성 단계가 아닌 phase는 None(단계 경과초 미기록).
        assert L._phase_step_name("complete") is None
        assert L._phase_step_name("stopping") is None
        assert L._phase_step_name("unknown_phase") is None

    def test_warm_prepare_and_loop_start_are_generate(self):
        # 준비/시작은 생성 단계(0)로 묶인다.
        assert L._phase_step_name("warm_prepare_start") == "generate"
        assert L._phase_step_name("loop_start") == "generate"


# =====================================================================
# 4) _publish_live — phase 경계에서 _timing 갱신·발행(결정론: time monkeypatch).
# =====================================================================
def _make_state_with_one_gen(tmp_path):
    st = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "snaps"))
    rid = st.start_run(LoopConfig(provider="gpt_auth", max_generations=3), run_id="t64")
    st.record_generation(
        rid, 0,
        buy_name="AILOOP_t64_g0_buy", sell_name="AILOOP_t64_g0_sell",
        status="ok", score=1.2, gate_passed=True, reason="ok",
        trade_count=42, mdd=12.0, profit=150000.0, strategy_gist="gist",
    )
    return st, rid


def _run_one_generation_with_snapshots(monkeypatch, tmp_path):
    snapshots = []
    monkeypatch.setattr(L, "_make_provider_with_proxy", lambda _cfg: (object(), False))
    monkeypatch.setattr(
        L,
        "_generate_pair",
        lambda _provider, _cfg, rid, gen, _feedback, **_kwargs: {
            "status": "ok",
            "buy_name": f"AILOOP_{rid}_g{gen}_buy",
            "sell_name": f"AILOOP_{rid}_g{gen}_sell",
            "tokens": 1,
        },
    )
    monkeypatch.setattr(L.bootstrap, "ensure_loop_db_engine_compat", lambda: None)
    monkeypatch.setattr(L, "_print_strategy_head", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(L, "_strategy_gist", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(L, "clear_stop_flag", lambda: None)
    monkeypatch.setattr(L, "stop_requested", lambda: False)
    monkeypatch.setattr(L, "publish_loop_state", snapshots.append)
    monkeypatch.setattr(
        L,
        "run_backtest_for",
        lambda _cfg, _buy, _sell: L.BacktestOutcome(
            True,
            "success",
            "offline.csv",
            {
                "cagr": 1.0,
                "mdd_pct": 5.0,
                "trade_count": 20,
                "total_profit_krw": 1000.0,
            },
            "ok",
        ),
    )
    fit = FitnessResult(
        score=0.0,
        calmar=0.5,
        uptrend_r2=0.5,
        gate_passed=False,
        reason="MDD cap",
        cagr=1.0,
        mdd=20.0,
        trade_count=20,
        total_profit=1000.0,
    )
    graded = GradedResult(
        graded=0.7,
        gate_passed=False,
        composite=0.0,
        trades_term=1.0,
        mdd_term=0.5,
        profit_term=1.0,
        uptrend_term=0.5,
        gate_distance="MDD 20 > cap",
        cagr=1.0,
        mdd=20.0,
        trade_count=20,
        total_profit=1000.0,
        uptrend_r2=0.5,
    )
    monkeypatch.setattr(L, "_score_outcome", lambda _outcome, _cfg: (fit, graded, None))

    config = LoopConfig(
        provider="openrouter",
        max_generations=1,
        bt_engine_mode="cold",
        cost_cap_generations=100,
        cost_cap_tokens=None,
        autopsy_enabled=False,
        mdd_cap=10.0,
        min_trades=10,
    )
    state = LoopState(db_path=str(tmp_path / "runs.db"), snapshot_dir=str(tmp_path / "snaps"))
    try:
        L.run_loop(config, run_id="timing-order", state=state)
    finally:
        state.close()
    return snapshots


def test_loop_phase_event_order_is_stable(monkeypatch, tmp_path):
    # Given: a one-generation offline research loop with all state publishes captured.
    # When: the loop completes normally.
    snapshots = _run_one_generation_with_snapshots(monkeypatch, tmp_path)

    # Then: the existing public phase ordering remains the compatibility contract.
    assert [snapshot.latest.phase for snapshot in snapshots] == [
        "loop_start",
        "generate_start",
        "generate_done",
        "backtest_start",
        "backtest_end",
        "score_start",
        "score_done",
        "autopsy_start",
        "autopsy_done",
        "generation_done",
        "complete",
    ]


def test_fresh_run_serializes_not_started_until_generation_exists(monkeypatch, tmp_path):
    # Given: a fresh one-generation run whose public snapshots are captured.
    snapshots = _run_one_generation_with_snapshots(monkeypatch, tmp_path)
    by_phase = {snapshot.latest.phase: snapshot for snapshot in snapshots}

    # When: snapshots cross the first generation boundary.
    loop_start = by_phase["loop_start"]
    generate_start = by_phase["generate_start"]
    complete = by_phase["complete"]

    # Then: -1 remains truthful before generation 0 exists and survives JSON round-trip.
    assert loop_start.current_gen == -1
    assert C.LoopState.model_validate_json(loop_start.model_dump_json()).current_gen == -1
    assert generate_start.current_gen == 0
    assert "generate" not in generate_start.latest.step_timings
    assert complete.current_gen == 0


class _Clock:
    """monkeypatch용 단조 가짜 시계 — call마다 지정한 시각을 차례로 돌려준다."""

    def __init__(self, values):
        self._values = list(values)
        self._i = 0

    def __call__(self):
        v = self._values[min(self._i, len(self._values) - 1)]
        self._i += 1
        return v


class TestPublishLiveTiming:
    def test_start_resets_phase_t0_and_publishes(self, monkeypatch, tmp_path):
        st, rid = _make_state_with_one_gen(tmp_path)
        captured = {}
        monkeypatch.setattr(L, "publish_loop_state",
                            lambda snap: captured.update(snap=snap))
        # generate_start 발행 시각 = 1000.0.
        monkeypatch.setattr(L.time, "time", lambda: 1000.0)

        timing = {"phase_t0": 0.0, "gen_t0": 0.0, "timings": {}}
        L._publish_live(
            st, rid, LoopConfig(), status="running", current_gen=0,
            cumulative_tokens=0, phase="generate_start", _timing=timing,
        )
        st.close()
        snap = captured["snap"]
        # generate_start는 세대 시작 → gen_t0와 phase_t0 둘 다 1000.0으로 리셋.
        assert snap.latest.phase_started_at == 1000.0
        assert snap.latest.gen_started_at == 1000.0
        assert timing["phase_t0"] == 1000.0
        assert timing["gen_t0"] == 1000.0

    def test_done_records_step_elapsed(self, monkeypatch, tmp_path):
        st, rid = _make_state_with_one_gen(tmp_path)
        captured = {}
        monkeypatch.setattr(L, "publish_loop_state",
                            lambda snap: captured.update(snap=snap))

        timing = {"phase_t0": 0.0, "gen_t0": 0.0, "timings": {}}
        # backtest_start(t=1000) → backtest_end(t=1060) ⇒ backtest 소요 60s.
        monkeypatch.setattr(L.time, "time", lambda: 1000.0)
        L._publish_live(st, rid, LoopConfig(), status="running", current_gen=0,
                        cumulative_tokens=0, phase="backtest_start", _timing=timing)
        monkeypatch.setattr(L.time, "time", lambda: 1060.0)
        L._publish_live(st, rid, LoopConfig(), status="running", current_gen=0,
                        cumulative_tokens=0, phase="backtest_end", _timing=timing)
        st.close()
        snap = captured["snap"]
        assert snap.latest.step_timings.get("backtest") == 60.0
        timings = timing["timings"]
        assert isinstance(timings, dict)
        assert timings["backtest"] == 60.0

    def test_gen_t0_persists_across_phases_within_generation(self, monkeypatch, tmp_path):
        st, rid = _make_state_with_one_gen(tmp_path)
        captured = {}
        monkeypatch.setattr(L, "publish_loop_state",
                            lambda snap: captured.update(snap=snap))

        timing = {"phase_t0": 0.0, "gen_t0": 0.0, "timings": {}}
        # generate_start(t=500)에서 gen_t0=500. 이후 backtest_start(t=520)에서도 gen_t0 유지.
        monkeypatch.setattr(L.time, "time", lambda: 500.0)
        L._publish_live(st, rid, LoopConfig(), status="running", current_gen=0,
                        cumulative_tokens=0, phase="generate_start", _timing=timing)
        monkeypatch.setattr(L.time, "time", lambda: 520.0)
        L._publish_live(st, rid, LoopConfig(), status="running", current_gen=0,
                        cumulative_tokens=0, phase="backtest_start", _timing=timing)
        st.close()
        snap = captured["snap"]
        # 세대 시작 시각은 generate_start(500)에서 고정, phase_t0는 backtest_start(520)로 갱신.
        assert snap.latest.gen_started_at == 500.0
        assert snap.latest.phase_started_at == 520.0

    def test_iterate_starts_at_generation_done_and_ends_at_next_generate(
        self, monkeypatch, tmp_path,
    ):
        # Given: autopsy ends at t=110 after starting at t=100.
        st, rid = _make_state_with_one_gen(tmp_path)
        snapshots = []
        monkeypatch.setattr(L, "publish_loop_state", snapshots.append)
        timing = {"phase_t0": 0.0, "gen_t0": 0.0, "timings": {}}

        for phase, now in (
            ("autopsy_start", 100.0),
            ("autopsy_done", 110.0),
            ("generation_done", 112.0),
            ("generate_start", 115.0),
        ):
            monkeypatch.setattr(L.time, "time", lambda now=now: now)
            L._publish_live(
                st,
                rid,
                LoopConfig(),
                status="running",
                current_gen=0,
                cumulative_tokens=0,
                phase=phase,
                _timing=timing,
            )
        st.close()

        # When: generation_done opens the inter-generation iterate phase.
        generation_done = snapshots[-2]

        # Then: autopsy and iterate each use their own explicit interval.
        assert generation_done.latest.phase_started_at == 112.0
        assert generation_done.latest.step_timings == {"autopsy": 10.0}
        assert snapshots[-1].latest.step_timings == {
            "autopsy": 10.0,
            "iterate": 3.0,
        }

    def test_complete_closes_an_open_iterate_interval(self, monkeypatch, tmp_path):
        # Given: generation_done opens iterate at t=112.
        st, rid = _make_state_with_one_gen(tmp_path)
        captured = {}
        monkeypatch.setattr(
            L,
            "publish_loop_state",
            lambda snapshot: captured.update(snapshot=snapshot),
        )
        timing = {"phase_t0": 0.0, "gen_t0": 0.0, "timings": {}}
        monkeypatch.setattr(L.time, "time", lambda: 112.0)
        L._publish_live(
            st,
            rid,
            LoopConfig(),
            status="running",
            current_gen=0,
            cumulative_tokens=0,
            phase="generation_done",
            _timing=timing,
        )

        # When: the run completes at t=120 without another generation.
        monkeypatch.setattr(L.time, "time", lambda: 120.0)
        L._publish_live(
            st,
            rid,
            LoopConfig(),
            status="complete",
            current_gen=0,
            cumulative_tokens=0,
            phase="complete",
            _timing=timing,
        )
        st.close()

        # Then: the terminal event closes iterate without inventing a complete step.
        assert captured["snapshot"].latest.step_timings == {"iterate": 8.0}

    def test_no_timing_context_emits_defaults(self, monkeypatch, tmp_path):
        # _timing 무인자(GA/테스트/기존 호출부) → 진행시간 미발행(0.0/빈 dict, 하위호환).
        st, rid = _make_state_with_one_gen(tmp_path)
        captured = {}
        monkeypatch.setattr(L, "publish_loop_state",
                            lambda snap: captured.update(snap=snap))
        L._publish_live(st, rid, LoopConfig(), status="running", current_gen=0,
                        cumulative_tokens=0, phase="backtest_end")
        st.close()
        snap = captured["snap"]
        assert snap.latest.phase_started_at == 0.0
        assert snap.latest.gen_started_at == 0.0
        assert snap.latest.step_timings == {}

    def test_complete_phase_records_no_step_timing(self, monkeypatch, tmp_path):
        # complete는 활성 단계가 아니므로 step_timings에 키를 만들지 않는다.
        st, rid = _make_state_with_one_gen(tmp_path)
        captured = {}
        monkeypatch.setattr(L, "publish_loop_state",
                            lambda snap: captured.update(snap=snap))
        timing = {"phase_t0": 1000.0, "gen_t0": 900.0, "timings": {}}
        monkeypatch.setattr(L.time, "time", lambda: 2000.0)
        L._publish_live(st, rid, LoopConfig(), status="complete", current_gen=1,
                        cumulative_tokens=0, phase="complete", _timing=timing)
        st.close()
        snap = captured["snap"]
        # complete는 단계명 None → step_timings 누적 없음(complete 키 부재).
        assert "complete" not in snap.latest.step_timings


# =====================================================================
# 5) app._generation_durations_payload — 인접 created_at 차분 + started_at 보정.
# =====================================================================
class TestGenerationDurations:
    def _seed_run(self, tmp_path, monkeypatch):
        """tmp DB에 created_at가 통제된 run 1개(3세대)를 만든다.

        record_generation은 내부적으로 state._now()로 created_at를 박으므로,
        state._now를 차례로 패치해 결정론적 created_at(1000, 1100, 1180)을 만든다.
        run started_at는 start_run 시점의 _now()다(여기선 980).
        """
        from ai_strategy_loop.controller import state as S
        clock = _Clock([980.0, 1000.0, 1100.0, 1180.0])
        monkeypatch.setattr(S, "_now", clock)
        st = LoopState(db_path=str(tmp_path / "d.db"), snapshot_dir=str(tmp_path / "s"))
        rid = st.start_run(LoopConfig(provider="gpt_auth"), run_id="durrun")  # started_at=980
        for g in range(3):
            st.record_generation(
                rid, g, buy_name=f"b{g}", sell_name=f"s{g}",
                status="ok", score=1.0, gate_passed=True, reason="ok",
            )  # created_at = 1000, 1100, 1180
        st.close()
        return rid

    def test_durations_from_adjacent_created_at(self, tmp_path, monkeypatch):
        rid = self._seed_run(tmp_path, monkeypatch)
        # state DB 경로를 tmp로 가리키도록 LOOP_RUNS_DB를 패치(payload가 기본 DB를 연다).
        from ai_strategy_loop.controller import state as S
        monkeypatch.setattr(S, "LOOP_RUNS_DB", str(tmp_path / "d.db"))
        from ai_strategy_loop.dashboard import app as A
        res = A._generation_durations_payload(rid)
        rows = {r["gen_no"]: r for r in res["durations"]}
        assert res["count"] == 3
        # gen0: created_at(1000) - started_at(980) = 20.
        assert rows[0]["duration_sec"] == 20.0
        # gen1: 1100 - 1000 = 100.
        assert rows[1]["duration_sec"] == 100.0
        # gen2: 1180 - 1100 = 80.
        assert rows[2]["duration_sec"] == 80.0

    def test_missing_db_returns_empty(self, tmp_path, monkeypatch):
        from ai_strategy_loop.controller import state as S
        monkeypatch.setattr(S, "LOOP_RUNS_DB", str(tmp_path / "nonexistent.db"))
        from ai_strategy_loop.dashboard import app as A
        res = A._generation_durations_payload("whatever")
        # 빈 DB는 run/gen 없음 → 빈 목록(무예외).
        assert res["durations"] == []
        assert res["count"] == 0

    def test_negative_delta_is_none(self, tmp_path, monkeypatch):
        # created_at가 역행하면(재기록/시계 역행) duration=None(잘못된 소요 표시 방지).
        from ai_strategy_loop.controller import state as S
        clock = _Clock([1000.0, 1100.0, 1050.0])  # started=1000, g0=1100, g1=1050(<g0).
        monkeypatch.setattr(S, "_now", clock)
        st = LoopState(db_path=str(tmp_path / "n.db"), snapshot_dir=str(tmp_path / "ns"))
        rid = st.start_run(LoopConfig(), run_id="negrun")
        st.record_generation(rid, 0, buy_name="b", sell_name="s",
                             status="ok", score=1.0, gate_passed=True, reason="ok")
        st.record_generation(rid, 1, buy_name="b", sell_name="s",
                             status="ok", score=1.0, gate_passed=True, reason="ok")
        st.close()
        monkeypatch.setattr(S, "LOOP_RUNS_DB", str(tmp_path / "n.db"))
        from ai_strategy_loop.dashboard import app as A
        res = A._generation_durations_payload(rid)
        rows = {r["gen_no"]: r for r in res["durations"]}
        assert rows[0]["duration_sec"] == 100.0   # 1100 - 1000.
        assert rows[1]["duration_sec"] is None     # 1050 - 1100 < 0 → None.

    def test_gen0_not_mislabeled_as_minus_one(self, tmp_path, monkeypatch):
        # 회귀 가드: gen_no=0(유효값)이 `or -1` falsy-zero 버그로 -1이 되면 안 된다.
        rid = self._seed_run(tmp_path, monkeypatch)
        from ai_strategy_loop.controller import state as S
        monkeypatch.setattr(S, "LOOP_RUNS_DB", str(tmp_path / "d.db"))
        from ai_strategy_loop.dashboard import app as A
        res = A._generation_durations_payload(rid)
        gen_nos = sorted(r["gen_no"] for r in res["durations"])
        assert gen_nos == [0, 1, 2]


# =====================================================================
# 6) backend ↔ frontend 단계명 정합(step_timings 키 ↔ FLOW_STEPS timingKey).
# =====================================================================
from pathlib import Path  # noqa: E402

import re  # noqa: E402

_FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


class TestStepNameAlignment:
    def test_step_name_map_covers_all_active_indices(self):
        # _PHASE_STEP의 모든 활성(>=0) 인덱스는 _STEP_NAME_BY_INDEX에 이름이 있어야 한다.
        active = {idx for idx in L._PHASE_STEP.values() if idx >= 0}
        for idx in active:
            assert idx in L._STEP_NAME_BY_INDEX, f"단계 인덱스 {idx} 이름 누락"

    def test_frontend_flow_steps_timing_keys_match_backend(self):
        # phase-detail.jsx FLOW_STEPS의 timingKey 집합 = backend _STEP_NAME_BY_INDEX 값 집합.
        #   (완료 배지가 step_timings[timingKey]로 조회하므로 키가 정확히 일치해야 한다.)
        src = (_FRONTEND / "phase-detail.jsx").read_text(encoding="utf-8")
        keys = set(re.findall(r'timingKey:\s*"([a-z]+)"', src))
        backend = set(L._STEP_NAME_BY_INDEX.values())
        assert keys == backend, f"프론트 timingKey {keys} != backend 단계명 {backend}"


class TestProcessFlowTimingFrontend:
    """phase-detail.jsx ProcessFlowPanel 진행시간 UI 구조 계약(정적 검증)."""

    def _src(self):
        return (_FRONTEND / "phase-detail.jsx").read_text(encoding="utf-8")

    def test_reads_timing_fields(self):
        src = self._src()
        assert "phase_started_at" in src
        assert "gen_started_at" in src
        assert "step_timings" in src

    def test_live_tick_is_running_gated(self):
        # setInterval(1s) 라이브 경과 증가는 running일 때만(정지/완료는 멈춤).
        src = self._src()
        pf = src[src.find("function ProcessFlowPanel("):]
        assert "setInterval" in pf
        assert "if (!running) return" in pf

    def test_discrete_progress_not_continuous_percent(self):
        # 정직: 연속% 금지 — (current_step+1)/5 이산 진행 + 'N/5 단계' 텍스트.
        src = self._src()
        assert "/{totalSteps} 단계" in src
        assert "currentStep + 1" in src

    def test_completion_clock_from_updated_at(self):
        # complete면 완료시각(updated_at) 표기 + 헬퍼 노출.
        src = self._src()
        assert "updated_at" in src
        assert "fmtClockFromEpoch" in src
        tail = src[src.rfind("Object.assign(window"):]
        assert "fmtElapsedSec" in tail
        assert "fmtClockFromEpoch" in tail

    def test_zero_started_at_omits_elapsed(self):
        # 가드: phase_started_at/gen_started_at=0이면(구 상태/미발행) 경과 표시 생략.
        src = self._src()
        pf = src[src.find("function ProcessFlowPanel("):]
        assert "phaseStartedAt > 0" in pf
        assert "genStartedAt > 0" in pf
