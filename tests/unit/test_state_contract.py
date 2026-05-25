"""US-007 — 상태 계약 단위 테스트 (LoopState 스키마 + to_loop_state 빌더).

검증:
  - 샘플 루프 요약/세대에서 LoopState를 빌드 → 스키마 검증 통과.
  - contract_version == 1.
  - 루프 to_loop_state() 출력이 LoopState 스키마로 검증된다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller.state import LoopState, to_loop_state  # noqa: E402


def _sample_summary():
    return {
        "run_id": "run_test_007",
        "generations": 3,
        "max_generations": 5,
        "best_gen": 2,
        "best_score": 1.75,
        "best_buy": "AILOOP_run_test_007_g2_buy",
        "best_sell": "AILOOP_run_test_007_g2_sell",
        "winner_gen": 2,
        "winner_score": 2.1,
        "winner_buy": "AILOOP_run_test_007_g2_buy",
        "winner_sell": "AILOOP_run_test_007_g2_sell",
        "stop_reason": "target_score",
    }


def _sample_generations():
    return [
        {"gen_no": 0, "status": "error", "score": 0.0, "gate_passed": 0,
         "reason": "no trades", "trade_count": 0, "mdd": 0.0, "profit": 0.0},
        {"gen_no": 1, "status": "ok", "score": 0.9, "gate_passed": 0,
         "reason": "gate failed", "trade_count": 12, "mdd": 18.0, "profit": 50000.0},
        {"gen_no": 2, "status": "ok", "score": 1.75, "gate_passed": 1,
         "reason": "ok", "trade_count": 40, "mdd": 12.0, "profit": 200000.0},
    ]


class TestContractVersion:
    """계약 버전 고정 검증."""

    def test_contract_version_is_1(self):
        assert C.CONTRACT_VERSION == 1

    def test_loop_state_default_carries_contract_version(self):
        assert C.LoopState().contract_version == 1


class TestLoopStateValidation:
    """샘플 데이터에서 LoopState가 스키마 검증을 통과하는지."""

    def test_default_loop_state_is_idle(self):
        ls = C.LoopState()
        assert ls.status == C.STATUS_IDLE
        assert ls.winner is None
        assert ls.generations == []

    def test_build_loop_state_from_sample_validates(self):
        ls = to_loop_state(
            _sample_summary(), _sample_generations(),
            config=LoopConfig(provider="openrouter", max_generations=5),
            status="running", current_gen=2,
        )
        # pydantic 인스턴스 → 재검증(round-trip) 으로 스키마 적합성 확인.
        revalidated = C.LoopState.model_validate(ls.model_dump())
        assert revalidated.contract_version == 1
        assert revalidated.run_id == "run_test_007"
        assert revalidated.status == "running"
        assert revalidated.current_gen == 2
        assert revalidated.provider == "openrouter"
        assert revalidated.max_generations == 5

    def test_best_info_populated(self):
        ls = to_loop_state(
            _sample_summary(), _sample_generations(),
            config=LoopConfig(provider="openrouter", max_generations=5),
        )
        assert ls.best.gen == 2
        assert ls.best.graded_score == 1.75
        # best 세대(2)는 gate_passed=True 행에서 보강됨.
        assert ls.best.gate_passed is True
        assert ls.best.buy_name == "AILOOP_run_test_007_g2_buy"

    def test_winner_info_populated(self):
        ls = to_loop_state(
            _sample_summary(), _sample_generations(),
            config=LoopConfig(),
        )
        assert ls.winner is not None
        assert ls.winner.gen == 2
        assert ls.winner.score == 2.1

    def test_winner_null_when_no_gate_pass(self):
        summary = _sample_summary()
        summary["winner_gen"] = -1
        summary["winner_score"] = None
        ls = to_loop_state(summary, _sample_generations(), config=LoopConfig())
        assert ls.winner is None

    def test_generations_rows_mapped(self):
        ls = to_loop_state(
            _sample_summary(), _sample_generations(), config=LoopConfig(),
        )
        assert len(ls.generations) == 3
        g2 = ls.generations[2]
        assert g2.gen_no == 2
        assert g2.status == "ok"
        assert g2.graded_score == 1.75
        assert g2.gate_passed is True
        assert g2.trade_count == 40

    def test_latest_and_cumulative(self):
        ls = to_loop_state(
            _sample_summary(), _sample_generations(), config=LoopConfig(),
            latest={"phase": "backtest_end", "last_checkpoint": "csv_detected",
                    "message": "done"},
            cumulative_tokens=1234,
        )
        assert ls.latest.phase == "backtest_end"
        assert ls.latest.last_checkpoint == "csv_detected"
        assert ls.cumulative.tokens == 1234
        assert ls.cumulative.cost_or_count == 3
        assert ls.updated_at > 0


class TestToLoopStateOutputValidates:
    """to_loop_state() 출력이 JSON 직렬화 + 재검증을 통과하는지."""

    def test_model_dump_json_roundtrips(self):
        ls = to_loop_state(
            _sample_summary(), _sample_generations(),
            config=LoopConfig(provider="gpt_auth", max_generations=5, bt_timeframe="min"),
            status="complete", current_gen=2,
        )
        text = ls.model_dump_json()
        import json
        data = json.loads(text)
        revalidated = C.LoopState.model_validate(data)
        assert revalidated.contract_version == 1
        assert revalidated.status == "complete"
        assert revalidated.bt_timeframe == "min"

    def test_idle_state_validates(self):
        ls = C.idle_state(provider="gpt_auth", bt_timeframe="min", max_generations=20)
        revalidated = C.LoopState.model_validate(ls.model_dump())
        assert revalidated.status == "idle"
        assert revalidated.provider == "gpt_auth"
        assert revalidated.max_generations == 20


class TestGenerationMddProfitGistPersisted:
    """MEDIUM-1: mdd/profit/strategy_gist가 DB에 저장되고 to_loop_state로 실값이 읽힌다."""

    def test_record_and_read_back_real_values(self, tmp_path):
        db_path = str(tmp_path / "loop_runs.db")
        snap_dir = str(tmp_path / "snaps")
        st = LoopState(db_path=db_path, snapshot_dir=snap_dir)
        try:
            rid = st.start_run(LoopConfig(provider="openrouter", max_generations=3))
            st.record_generation(
                rid, 0,
                buy_name="AILOOP_x_g0_buy", sell_name="AILOOP_x_g0_sell",
                status="ok", score=1.5, gate_passed=True, reason="ok",
                trade_count=42, mdd=13.5, profit=275000.0,
                strategy_gist="if 분당거래대금 >= 50 and 등락율 > 3:",
            )
            gens = st.get_generations(rid)
        finally:
            st.close()

        assert len(gens) == 1
        row = gens[0]
        # DB 행에 실값이 들어왔다(0/"" 아님).
        assert row["mdd"] == 13.5
        assert row["profit"] == 275000.0
        assert row["strategy_gist"] == "if 분당거래대금 >= 50 and 등락율 > 3:"

        # to_loop_state가 그 실값을 GenerationInfo로 넘긴다.
        summary = {"run_id": rid, "best_gen": 0, "best_score": 1.5}
        ls = to_loop_state(summary, gens, config=LoopConfig(), status="running")
        g0 = ls.generations[0]
        assert g0.mdd == 13.5
        assert g0.profit == 275000.0
        assert g0.strategy_gist == "if 분당거래대금 >= 50 and 등락율 > 3:"
