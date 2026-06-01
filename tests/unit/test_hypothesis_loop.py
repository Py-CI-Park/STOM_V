"""P2a — 가정(Hypothesis) 루프 코어 단위 테스트 (백테/루프 실행 없음, tmp DB).

검증:
  - build_hypotheses: gate 통과 시 refine baseline만, gate 실패 시 원인별 가정 생성,
    is_refine=False면 baseline 없음.
  - adjudicate: 기대 방향 일치=accepted / 반대=rejected / delta 0=inconclusive /
    target 키 없음=inconclusive / 입력 리스트 불변(immutability).
  - to_dict/from_dict 라운드트립.
  - record_generation hypotheses_json 저장/조회 round-trip, 부모 없는 세대 NULL.
  - SCHEMA_VERSION==9, generations에 hypotheses_json 컬럼 존재.
  - config.hypothesis_tracking_enabled 기본 False.
  - 토글 OFF 경로(_build_next_hypotheses/_adjudicate_and_serialize)에서 None 반환.
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.hypothesis import (  # noqa: E402
    VERDICT_ACCEPTED,
    VERDICT_INCONCLUSIVE,
    VERDICT_REJECTED,
    VERDICT_UNTESTED,
    Hypothesis,
    adjudicate,
    build_hypotheses,
)
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


def _cols(st, table="generations"):
    return {row[1] for row in st._con.execute(f"PRAGMA table_info({table})")}


def _row(st, rid, gen_no):
    r = st._con.execute(
        "SELECT * FROM generations WHERE run_id = ? AND gen_no = ?", (rid, gen_no)
    ).fetchone()
    return dict(r) if r is not None else None


# =====================================================================
# build_hypotheses — 부검 분기와 동일 조건으로 가정 방출.
# =====================================================================
class TestBuildHypotheses:
    def test_gate_passed_refine_yields_only_baseline(self):
        hyps = build_hypotheses(
            gate_passed=True, mdd=5.0, mdd_cap=12.0,
            total_profit=100000.0, trade_count=300, min_trades=30,
            is_refine=True,
        )
        assert len(hyps) == 1
        h = hyps[0]
        assert h.source == "refine_baseline"
        assert h.target_metric == "graded"
        assert h.expected_direction == +1
        assert h.side == "both"
        assert h.verdict == VERDICT_UNTESTED

    def test_gate_passed_not_refine_yields_nothing(self):
        hyps = build_hypotheses(
            gate_passed=True, mdd=5.0, mdd_cap=12.0,
            total_profit=100000.0, trade_count=300, min_trades=30,
            is_refine=False,
        )
        assert hyps == []

    def test_gate_failed_generates_cause_hypotheses(self):
        # MDD 초과 + 손익 음수 + 거래 부족 → 세 원인 가정(+ refine baseline).
        hyps = build_hypotheses(
            gate_passed=False, mdd=18.2, mdd_cap=12.0,
            total_profit=-50000.0, trade_count=10, min_trades=30,
            is_refine=True,
        )
        sources = {h.source for h in hyps}
        assert "refine_baseline" in sources
        assert "gate_trades" in sources
        assert "gate_mdd" in sources
        assert "gate_profit" in sources
        assert len(hyps) == 4

        by_source = {h.source: h for h in hyps}
        assert by_source["gate_trades"].target_metric == "daily_avg_trades"
        assert by_source["gate_trades"].expected_direction == +1
        assert by_source["gate_trades"].side == "buy"
        assert by_source["gate_mdd"].target_metric == "mdd"
        assert by_source["gate_mdd"].expected_direction == -1
        assert by_source["gate_mdd"].side == "sell"
        assert by_source["gate_profit"].target_metric == "profit"
        assert by_source["gate_profit"].expected_direction == +1
        assert by_source["gate_profit"].side == "buy"

    def test_gate_failed_not_refine_has_no_baseline(self):
        hyps = build_hypotheses(
            gate_passed=False, mdd=18.2, mdd_cap=12.0,
            total_profit=-50000.0, trade_count=10, min_trades=30,
            is_refine=False,
        )
        sources = {h.source for h in hyps}
        assert "refine_baseline" not in sources
        # 세 게이트 원인만(거래 부족 + MDD 초과 + 손익 음수).
        assert sources == {"gate_trades", "gate_mdd", "gate_profit"}

    def test_gate_failed_only_mdd(self):
        # 빈도·손익 통과, MDD만 초과 → gate_mdd 한 개만(is_refine=False).
        hyps = build_hypotheses(
            gate_passed=False, mdd=20.0, mdd_cap=12.0,
            total_profit=500000.0, trade_count=300, min_trades=30,
            is_refine=False,
        )
        assert len(hyps) == 1
        assert hyps[0].source == "gate_mdd"
        assert hyps[0].target_metric == "mdd"

    def test_mdd_cap_zero_skips_mdd_hypothesis(self):
        # mdd_cap<=0이면 MDD 가정을 세우지 않는다(부검 분기와 동일).
        hyps = build_hypotheses(
            gate_passed=False, mdd=99.0, mdd_cap=0.0,
            total_profit=100.0, trade_count=300, min_trades=30,
            is_refine=False,
        )
        assert all(h.source != "gate_mdd" for h in hyps)

    def test_min_trades_zero_skips_trades_hypothesis(self):
        hyps = build_hypotheses(
            gate_passed=False, mdd=5.0, mdd_cap=12.0,
            total_profit=100.0, trade_count=0, min_trades=0,
            is_refine=False,
        )
        assert all(h.source != "gate_trades" for h in hyps)


# =====================================================================
# adjudicate — 부모 대비 델타로 채택/기각.
# =====================================================================
class TestAdjudicate:
    def _hyp(self, target, direction):
        return Hypothesis(
            side="sell", text="t", target_metric=target,
            expected_direction=direction, source="gate_mdd",
        )

    def test_mdd_decrease_matches_expected_minus_accepted(self):
        h = self._hyp("mdd", -1)
        out = adjudicate([h], {"d_mdd": -3.0})
        assert out[0].verdict == VERDICT_ACCEPTED
        assert out[0].observed_delta == -3.0

    def test_mdd_increase_against_expected_minus_rejected(self):
        h = self._hyp("mdd", -1)
        out = adjudicate([h], {"d_mdd": +2.5})
        assert out[0].verdict == VERDICT_REJECTED
        assert out[0].observed_delta == 2.5

    def test_zero_delta_inconclusive(self):
        h = self._hyp("mdd", -1)
        out = adjudicate([h], {"d_mdd": 0.0})
        assert out[0].verdict == VERDICT_INCONCLUSIVE
        assert out[0].observed_delta == 0.0

    def test_missing_target_key_inconclusive(self):
        h = self._hyp("profit", +1)
        out = adjudicate([h], {"d_mdd": -3.0})  # d_profit 키 없음.
        assert out[0].verdict == VERDICT_INCONCLUSIVE
        assert out[0].observed_delta is None

    def test_none_deltas_inconclusive(self):
        h = self._hyp("mdd", -1)
        out = adjudicate([h], None)
        assert out[0].verdict == VERDICT_INCONCLUSIVE
        assert out[0].observed_delta is None

    def test_profit_increase_matches_expected_plus_accepted(self):
        h = Hypothesis(side="buy", text="t", target_metric="profit",
                       expected_direction=+1, source="gate_profit")
        out = adjudicate([h], {"d_profit": 120000.0})
        assert out[0].verdict == VERDICT_ACCEPTED

    def test_daily_trades_uses_d_daily_trades_key(self):
        h = Hypothesis(side="buy", text="t", target_metric="daily_avg_trades",
                       expected_direction=+1, source="gate_trades")
        out = adjudicate([h], {"d_daily_trades": 0.5})
        assert out[0].verdict == VERDICT_ACCEPTED
        out2 = adjudicate([h], {"d_daily_trades": -0.5})
        assert out2[0].verdict == VERDICT_REJECTED

    def test_graded_baseline_judged_by_d_graded(self):
        h = Hypothesis(side="both", text="t", target_metric="graded",
                       expected_direction=+1, source="refine_baseline")
        out = adjudicate([h], {"d_graded": -0.81})
        assert out[0].verdict == VERDICT_REJECTED  # graded 악화 → baseline 기각.

    def test_input_list_not_mutated(self):
        """입력 hyps의 verdict/observed_delta가 변하지 않아야 한다(immutability)."""
        h = self._hyp("mdd", -1)
        original_verdict = h.verdict
        original_obs = h.observed_delta
        out = adjudicate([h], {"d_mdd": -3.0})
        # 입력 객체는 untested 그대로, 반환 객체만 판정됨.
        assert h.verdict == original_verdict == VERDICT_UNTESTED
        assert h.observed_delta == original_obs is None
        assert out[0] is not h
        assert out[0].verdict == VERDICT_ACCEPTED

    def test_empty_list_returns_empty(self):
        assert adjudicate([], {"d_mdd": -1.0}) == []


# =====================================================================
# Hypothesis dataclass 직렬화 라운드트립.
# =====================================================================
class TestSerialization:
    def test_to_dict_from_dict_roundtrip(self):
        h = Hypothesis(
            side="sell", text="매도 손절 강화로 MDD 감소 기대",
            target_metric="mdd", expected_direction=-1, source="gate_mdd",
            basis="MDD 18.2>cap 12", verdict=VERDICT_ACCEPTED, observed_delta=-3.0,
        )
        d = h.to_dict()
        assert d["side"] == "sell"
        assert d["target_metric"] == "mdd"
        assert d["verdict"] == VERDICT_ACCEPTED
        back = Hypothesis.from_dict(d)
        assert back == h

    def test_from_dict_ignores_unknown_keys(self):
        d = {"side": "buy", "text": "t", "target_metric": "profit",
             "expected_direction": 1, "source": "gate_profit", "extra": "ignored"}
        h = Hypothesis.from_dict(d)
        assert h.side == "buy"
        assert h.target_metric == "profit"

    def test_json_serializable_list(self):
        hyps = build_hypotheses(
            gate_passed=False, mdd=18.0, mdd_cap=12.0,
            total_profit=-1.0, trade_count=5, min_trades=30, is_refine=True,
        )
        judged = adjudicate(hyps, {"d_mdd": -2.0, "d_profit": 1.0,
                                   "d_daily_trades": 0.3, "d_graded": 0.1})
        s = json.dumps([h.to_dict() for h in judged], ensure_ascii=False)
        restored = [Hypothesis.from_dict(d) for d in json.loads(s)]
        assert restored == judged


# =====================================================================
# state.py — SCHEMA_VERSION (>=9, hypotheses_json 도입 버전) + 컬럼 + 저장/조회.
#   주: 이후 스키마 추가(예: v10 equity_points 테이블)로 버전이 올라가도 이 계약
#   (hypotheses_json 컬럼 존재 + 버전 >= 9)은 유지된다. 그래서 정확한 정수 대신
#   '>= 9 그리고 모듈 상수와 일치'로 검증한다(하위호환 — 버전 bump에 강건).
# =====================================================================
class TestSchemaAndPersistence:
    def test_schema_version_at_least_9(self):
        assert S.SCHEMA_VERSION >= 9

    def test_hypotheses_json_column_present(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "hv.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            assert "hypotheses_json" in _cols(st)
            assert st.get_schema_version() == S.SCHEMA_VERSION
            assert st.get_schema_version() >= 9
        finally:
            st.close()

    def test_record_and_read_hypotheses_json_roundtrip(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "rt.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = "rt"
            st.start_run(LoopConfig(), run_id=rid)
            payload = json.dumps(
                [{"side": "sell", "text": "t", "target_metric": "mdd",
                  "expected_direction": -1, "source": "gate_mdd", "basis": "",
                  "verdict": "accepted", "observed_delta": -3.0}],
                ensure_ascii=False,
            )
            st.record_generation(
                rid, 1, buy_name="b1", sell_name="s1", status="ok",
                score=1.96, parent_gen=0, hypotheses_json=payload,
            )
            row = _row(st, rid, 1)
            assert row is not None
            assert row["hypotheses_json"] == payload
            restored = json.loads(row["hypotheses_json"])
            assert restored[0]["verdict"] == "accepted"
        finally:
            st.close()

    def test_parentless_generation_has_null_hypotheses(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "nn.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = "nn"
            st.start_run(LoopConfig(), run_id=rid)
            # hypotheses_json 미전달(부모 없는 세대/토글 OFF) → NULL이어야 한다.
            st.record_generation(
                rid, 0, buy_name="b0", sell_name="s0", status="ok", score=2.77,
            )
            row = _row(st, rid, 0)
            assert row is not None
            assert row["hypotheses_json"] is None
        finally:
            st.close()


# =====================================================================
# config / launch_config 토글 + loop 헬퍼 OFF 경로(byte-동일 보장).
# =====================================================================
class TestToggleDefaultsAndOffPath:
    def test_config_default_is_false(self):
        assert LoopConfig().hypothesis_tracking_enabled is False

    def test_toggle_loadable_from_dict(self):
        cfg = LoopConfig.from_dict({"hypothesis_tracking_enabled": True})
        assert cfg.hypothesis_tracking_enabled is True

    def test_build_next_hypotheses_off_returns_none(self):
        cfg = LoopConfig()  # 기본 OFF.
        fit = _FakeFit(gate_passed=False, trade_count=5, total_profit=-1.0, mdd=20.0)
        graded = _FakeGraded(mdd=20.0, total_profit=-1.0)
        assert L._build_next_hypotheses(cfg, fit, graded, is_refine=True) is None

    def test_adjudicate_and_serialize_off_returns_none(self):
        cfg = LoopConfig()  # 기본 OFF.
        hyps = [Hypothesis(side="sell", text="t", target_metric="mdd",
                           expected_direction=-1, source="gate_mdd")]
        # P2b-1: (json_str, judged) 튜플 반환. OFF면 (None, None).
        json_str, judged = L._adjudicate_and_serialize(cfg, hyps, {"d_mdd": -1.0})
        assert json_str is None
        assert judged is None

    def test_build_next_hypotheses_on_returns_list(self):
        cfg = LoopConfig.from_dict({"hypothesis_tracking_enabled": True,
                                    "mdd_cap": 12.0, "min_trades": 30})
        fit = _FakeFit(gate_passed=False, trade_count=5, total_profit=-1.0, mdd=20.0)
        graded = _FakeGraded(mdd=20.0, total_profit=-1.0)
        hyps = L._build_next_hypotheses(cfg, fit, graded, is_refine=True)
        assert hyps is not None
        assert len(hyps) >= 1

    def test_adjudicate_and_serialize_on_returns_json(self):
        cfg = LoopConfig.from_dict({"hypothesis_tracking_enabled": True})
        hyps = [Hypothesis(side="sell", text="t", target_metric="mdd",
                           expected_direction=-1, source="gate_mdd")]
        # P2b-1: (json_str, judged) 튜플 — json_str은 영속용, judged는 환류용.
        s, judged = L._adjudicate_and_serialize(cfg, hyps, {"d_mdd": -3.0})
        assert s is not None
        restored = json.loads(s)
        assert restored[0]["verdict"] == "accepted"
        # judged 리스트도 함께 노출돼 다음 세대 프롬프트 환류에 쓰인다.
        assert judged is not None and len(judged) == 1
        assert judged[0].verdict == VERDICT_ACCEPTED

    def test_adjudicate_and_serialize_on_no_hypotheses_returns_none(self):
        cfg = LoopConfig.from_dict({"hypothesis_tracking_enabled": True})
        assert L._adjudicate_and_serialize(cfg, None, {"d_mdd": -1.0}) == (None, None)
        assert L._adjudicate_and_serialize(cfg, [], {"d_mdd": -1.0}) == (None, None)


# --- 가벼운 fake (fit/graded 인터페이스 최소 표면만) ---
class _FakeFit:
    def __init__(self, *, gate_passed, trade_count, total_profit, mdd):
        self.gate_passed = gate_passed
        self.trade_count = trade_count
        self.total_profit = total_profit
        self.mdd = mdd


class _FakeGraded:
    def __init__(self, *, mdd, total_profit):
        self.mdd = mdd
        self.total_profit = total_profit
