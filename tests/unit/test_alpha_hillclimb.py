"""alpha_lab.hillclimb 단위 테스트 — 뮤테이터 결정성·수락 규칙·예산 준수(엔진 mock).

봉인 근거: docs/research/condition_research/research_runs/alpha_lab_v3_20260706/
preregistration_v3.json (sha 50d3d38a) hillclimb 절.

범위:
  - 뮤테이터 결정성: generate_moves가 같은 입력에 항상 같은 리스트를 반환.
  - 분위 이동 수학: shift_threshold 단조성·경계 clip·빈 분포 거부.
  - 수락 규칙: accept()가 봉인 논리(profit>0 AND ((profit up AND mdd<=) OR
    calmar up))를 정확히 구현.
  - 예산 준수: run_seed_hillclimb의 evaluate_fn 호출 횟수가 per_seed_max를
    절대 넘지 않고, 조기중단(로컬 최적)이 예산 소진 전에 정확히 발동.
  - 43피처 화이트리스트·번역기: 파생 18항 함수형 렌더링 + 10개 시드 번역 왕복.
  - engine_eval 순수 헬퍼: 설정/등록 항목 조립, sqlite generations 판독.

엔진은 어디서도 기동하지 않는다(evaluate_fn은 항상 이 파일이 주입하는 mock).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from alpha_lab.hillclimb import features_v3
from alpha_lab.hillclimb.engine_eval import (
    build_pairs_json,
    build_train_config,
    metrics_from_generation_row,
    read_generation_metrics,
    registration_item,
)
from alpha_lab.hillclimb.loop import (
    TRAIN_GATE_DAILY_MIN,
    TRAIN_GATE_MDD_MAX,
    run_seed_hillclimb,
    train_gate_pass,
)
from alpha_lab.hillclimb.mutator import (
    Metrics,
    Move,
    accept,
    addition_moves,
    generate_moves,
    quantile_rank,
    quantile_value,
    removal_moves,
    shift_threshold,
    threshold_moves,
)
from alpha_lab.hillclimb.seeds import SEED_META, SEED_ORDER, SEED_RULES, translate_seed
from alpha_lab.hillclimb.sell_policy import CHAMPION_SELL_EXPR, CHAMPION_SELL_EXPR_SHA256
from alpha_lab.translate.codegen import SAMPLE_TIME_GUARD, UNIVERSE_GUARD_MONEYTOP_PROXY

# ---------------------------------------------------------------- 공통 픽스처

F1 = np.linspace(0.0, 100.0, 1001)  # 0.0, 0.1, ..., 100.0 (균등)
F2 = np.linspace(0.0, 1000.0, 1001)
DISTRIBUTIONS = {"F1": F1, "F2": F2}
WHITELIST = ("F1", "F2", "F3")  # F3은 분포 없음 — 스킵 경로 검증용
RULE_1 = (("F1", ">", 50.0),)
RULE_2 = (("F1", ">", 50.0), ("F2", "<=", 500.0))


# =============================================================== 분위 수학


class TestQuantileMath:
    def test_quantile_rank_and_value_roundtrip_mid(self):
        rank = quantile_rank(F1, 50.0)
        assert 0.49 < rank < 0.51

    def test_quantile_rank_empty_raises(self):
        with pytest.raises(ValueError):
            quantile_rank(np.array([]), 1.0)

    def test_quantile_value_empty_raises(self):
        with pytest.raises(ValueError):
            quantile_value(np.array([]), 0.5)

    def test_quantile_value_clips_q(self):
        # q<0/q>1 이 에러 없이 clip되어 최솟/최댓값 근방을 반환한다.
        assert quantile_value(F1, -1.0) == pytest.approx(quantile_value(F1, 0.0))
        assert quantile_value(F1, 2.0) == pytest.approx(quantile_value(F1, 1.0))

    @pytest.mark.parametrize("thr", [10.0, 50.0, 90.0])
    def test_shift_threshold_monotonic_in_pp(self, thr):
        """+pp가 클수록(같은 부호) 이동 폭이 단조 비감소, 부호가 다르면 반대쪽."""
        up2 = shift_threshold(F1, thr, +2.0)
        up5 = shift_threshold(F1, thr, +5.0)
        down2 = shift_threshold(F1, thr, -2.0)
        down5 = shift_threshold(F1, thr, -5.0)
        assert up5 >= up2 >= thr - 1e-9
        assert down5 <= down2 <= thr + 1e-9

    def test_shift_threshold_extreme_delta_clips_without_error(self):
        # 극단 delta_pp(분포 밖으로 나가는 크기)도 예외 없이 clip된 값을 낸다.
        hi = shift_threshold(F1, 50.0, +10_000.0)
        lo = shift_threshold(F1, 50.0, -10_000.0)
        assert F1.min() <= lo < hi <= F1.max()


# =============================================================== 이웃 생성


class TestGenerateMovesDeterminism:
    def test_repeat_calls_are_identical(self):
        moves_a = generate_moves(RULE_2, WHITELIST, DISTRIBUTIONS, max_add_candidates=2)
        moves_b = generate_moves(RULE_2, WHITELIST, DISTRIBUTIONS, max_add_candidates=2)
        assert moves_a == moves_b
        assert len(moves_a) > 0

    def test_order_is_threshold_then_remove_then_add(self):
        moves = generate_moves(RULE_2, WHITELIST, DISTRIBUTIONS, max_add_candidates=2)
        kinds = [m.kind for m in moves]
        # 모든 threshold가 모든 remove보다 앞, 모든 remove가 모든 add보다 앞.
        first_remove = kinds.index("remove") if "remove" in kinds else len(kinds)
        first_add = kinds.index("add") if "add" in kinds else len(kinds)
        assert all(k == "threshold" for k in kinds[:first_remove])
        assert all(k == "remove" for k in kinds[first_remove:first_add])
        assert all(k == "add" for k in kinds[first_add:])

    def test_threshold_moves_match_shift_threshold_primitive(self):
        """threshold_moves의 각 후보가 shift_threshold 계산과 정확히 일치(순서 포함)."""
        moves = threshold_moves(RULE_1, DISTRIBUTIONS)
        expected = []
        for pp in (2.0, 5.0):
            for sign in (1.0, -1.0):
                new_thr = shift_threshold(F1, 50.0, sign * pp)
                if new_thr != 50.0:
                    expected.append((("F1", ">", new_thr),))
        assert [m.rule for m in moves] == expected

    def test_removal_moves_empty_for_singleton_rule(self):
        assert removal_moves(RULE_1) == []

    def test_removal_moves_one_per_clause_missing_that_clause(self):
        moves = removal_moves(RULE_2)
        assert len(moves) == 2
        assert moves[0].rule == (RULE_2[1],)
        assert moves[1].rule == (RULE_2[0],)

    def test_addition_moves_skips_used_and_missing_distribution(self):
        moves = addition_moves(RULE_1, WHITELIST, DISTRIBUTIONS, max_candidates=5)
        added_features = {m.rule[-1][0] for m in moves}
        assert "F1" not in added_features  # 이미 규칙에 있음
        assert "F3" not in added_features  # 분포 없음
        assert added_features == {"F2"}

    def test_addition_moves_respects_max_candidates(self):
        wide_whitelist = ("F1", "F2", "F1b", "F2b")
        dists = dict(DISTRIBUTIONS)
        dists["F1b"] = F1
        dists["F2b"] = F2
        moves = addition_moves((), wide_whitelist, dists, max_candidates=1)
        tried = {m.rule[-1][0] for m in moves}
        assert len(tried) == 1  # 화이트리스트 순서상 첫 미사용 피처만.
        assert len(moves) == 2  # hi/lo 2후보.

    def test_addition_moves_never_reuses_feature_already_in_rule(self):
        dists = dict(DISTRIBUTIONS)
        dists["F3"] = F2  # F3에도 분포를 줘 실제 add 후보가 나오게 한다(공허한 통과 방지).
        moves = addition_moves(RULE_2, WHITELIST, dists, max_candidates=5)
        assert len(moves) > 0  # 이 단언이 무의미하게 통과(0개)하지 않는지 자체 검증.
        for move in moves:
            feats = [f for f, _, _ in move.rule]
            assert len(feats) == len(set(feats))

    def test_move_is_frozen_and_comparable(self):
        m1 = Move("threshold", RULE_1, "desc")
        m2 = Move("threshold", RULE_1, "desc")
        assert m1 == m2
        with pytest.raises(Exception):
            m1.kind = "remove"  # frozen dataclass — 대입 불가.


# =============================================================== 수락 규칙


def _m(status="ok", profit_pct=0.0, mdd=0.0, calmar=0.0, **kw) -> Metrics:
    return Metrics(status=status, profit_pct=profit_pct, mdd=mdd, calmar=calmar, **kw)


class TestAcceptRule:
    def test_rejects_non_ok_status(self):
        current = _m(profit_pct=-1.0, mdd=10.0, calmar=-0.1)
        candidate = _m(status="error", profit_pct=5.0, mdd=1.0, calmar=1.0)
        assert accept(current, candidate) is False

    def test_rejects_no_trades_status(self):
        current = _m(profit_pct=-1.0, mdd=10.0, calmar=-0.1)
        candidate = _m(status="no_trades", profit_pct=5.0, mdd=1.0, calmar=1.0)
        assert accept(current, candidate) is False

    def test_rejects_candidate_profit_not_positive(self):
        current = _m(profit_pct=-5.0, mdd=10.0, calmar=-0.5)
        candidate = _m(profit_pct=0.0, mdd=1.0, calmar=5.0)
        assert accept(current, candidate) is False

    def test_accepts_profit_up_and_mdd_not_worse(self):
        current = _m(profit_pct=1.0, mdd=10.0, calmar=0.1)
        candidate = _m(profit_pct=2.0, mdd=10.0, calmar=0.05)  # calmar 하락해도 무방
        assert accept(current, candidate) is True

    def test_rejects_profit_up_but_mdd_worse_and_calmar_not_up(self):
        current = _m(profit_pct=1.0, mdd=10.0, calmar=0.5)
        candidate = _m(profit_pct=2.0, mdd=10.5, calmar=0.5)
        assert accept(current, candidate) is False

    def test_accepts_calmar_up_even_if_profit_down_but_positive(self):
        current = _m(profit_pct=5.0, mdd=10.0, calmar=0.5)
        candidate = _m(profit_pct=3.0, mdd=20.0, calmar=0.6)
        assert accept(current, candidate) is True

    def test_rejects_profit_up_mdd_ok_but_all_equal_is_not_up(self):
        current = _m(profit_pct=1.0, mdd=10.0, calmar=0.1)
        candidate = _m(profit_pct=1.0, mdd=10.0, calmar=0.1)
        assert accept(current, candidate) is False

    def test_train_gate_pass_boundaries(self):
        ok = _m(profit_pct=0.01, mdd=TRAIN_GATE_MDD_MAX, daily_avg_trades=TRAIN_GATE_DAILY_MIN)
        assert train_gate_pass(ok) is True
        bad_mdd = _m(profit_pct=1.0, mdd=TRAIN_GATE_MDD_MAX + 0.01, daily_avg_trades=1.0)
        assert train_gate_pass(bad_mdd) is False
        bad_daily = _m(profit_pct=1.0, mdd=1.0, daily_avg_trades=TRAIN_GATE_DAILY_MIN - 0.01)
        assert train_gate_pass(bad_daily) is False
        bad_profit = _m(profit_pct=0.0, mdd=1.0, daily_avg_trades=1.0)
        assert train_gate_pass(bad_profit) is False
        bad_status = _m(status="error", profit_pct=1.0, mdd=1.0, daily_avg_trades=1.0)
        assert train_gate_pass(bad_status) is False


# =============================================================== 예산 준수


class _ScriptedEngine:
    """rule 시퀀스 계약(호출 순서)만 기록하는 결정론 mock 엔진."""

    def __init__(self, responder):
        self.calls = []
        self._responder = responder

    def __call__(self, rule):
        self.calls.append(rule)
        return self._responder(rule)


class TestBudgetCompliance:
    def test_trials_used_never_exceeds_per_seed_max(self):
        # 매 호출 baseline과 동률(비수락) — 라운드 전부 거부되어야 조기중단하지만,
        # per_seed_max를 아주 작게 잡아 예산이 먼저 끊기는 경로도 검증한다.
        baseline = _m(profit_pct=-1.0, mdd=10.0, calmar=-0.1)
        engine = _ScriptedEngine(lambda rule: baseline)
        result = run_seed_hillclimb(
            "seed", RULE_2, engine, DISTRIBUTIONS, WHITELIST,
            per_seed_max=3, max_add_candidates=2,
        )
        assert result.trials_used <= 3
        assert len(engine.calls) == result.trials_used
        assert result.stopped_reason == "budget_exhausted"

    def test_early_stop_before_budget_when_no_move_improves(self):
        baseline = _m(profit_pct=-1.0, mdd=10.0, calmar=-0.1)
        engine = _ScriptedEngine(lambda rule: baseline)
        result = run_seed_hillclimb(
            "seed", RULE_1, engine, {"F1": F1}, ("F1", "F2"),
            per_seed_max=20, max_add_candidates=1,
        )
        # RULE_1(절 1개)의 라운드1 이웃: threshold 4개 + remove 0개 + add(F2, 분포 없음) 0개.
        assert result.stopped_reason == "converged_local_optimum"
        assert result.trials_used < 20
        assert result.trials_used == 1 + 4

    def test_accepted_improvement_updates_best_and_current(self):
        add_hi = round(quantile_value(F2, 0.70), 6)
        target_rule = RULE_1 + (("F2", ">", add_hi),)
        baseline = _m(profit_pct=-1.0, mdd=10.0, calmar=-0.1)
        improved = _m(profit_pct=2.0, mdd=8.0, calmar=0.3)

        def responder(rule):
            return improved if rule == target_rule else baseline

        engine = _ScriptedEngine(responder)
        result = run_seed_hillclimb(
            "seed", RULE_1, engine, DISTRIBUTIONS, ("F1", "F2"),
            per_seed_max=20, max_add_candidates=1,
        )
        assert result.best_rule == target_rule
        assert result.best_metrics == improved
        # 이력에 정확히 그 시행이 accepted=True로 기록.
        hit = [h for h in result.history if h["rule"] == target_rule]
        assert len(hit) == 1 and hit[0]["accepted"] is True

    def test_duplicate_rule_is_not_re_evaluated(self):
        # F1의 +2pp와 -2pp가 우연히 경계 clip으로 같은 값이 되는 등의 상황을
        # 흉내내지 않고, baseline과 동일한 규칙이 재등장해도 캐시되어 엔진을
        # 다시 부르지 않는지 직접 검증한다.
        calls = []

        def responder(rule):
            calls.append(rule)
            return _m(profit_pct=-1.0, mdd=10.0, calmar=-0.1)

        engine = _ScriptedEngine(responder)
        result = run_seed_hillclimb(
            "seed", RULE_1, engine, {"F1": F1}, ("F1",),
            per_seed_max=20, max_add_candidates=1,
        )
        # 호출된 규칙에 중복이 없어야 한다(캐시가 정확히 동작).
        assert len(calls) == len(set(calls))
        assert result.trials_used == len(calls)

    def test_determinism_across_repeated_runs(self):
        def responder(rule):
            score = sum(t for _, _, t in rule)
            return _m(status="ok", profit_pct=(score % 7) - 3, mdd=5.0, calmar=(score % 3) * 0.1)

        engine_a = _ScriptedEngine(responder)
        engine_b = _ScriptedEngine(responder)
        result_a = run_seed_hillclimb("seed", RULE_2, engine_a, DISTRIBUTIONS, WHITELIST, per_seed_max=12)
        result_b = run_seed_hillclimb("seed", RULE_2, engine_b, DISTRIBUTIONS, WHITELIST, per_seed_max=12)
        assert result_a.trials_used == result_b.trials_used
        assert result_a.best_rule == result_b.best_rule
        assert [h["rule"] for h in result_a.history] == [h["rule"] for h in result_b.history]
        assert engine_a.calls == engine_b.calls

    def test_per_seed_max_below_one_raises(self):
        with pytest.raises(ValueError):
            run_seed_hillclimb("seed", RULE_1, lambda r: _m(), DISTRIBUTIONS, WHITELIST, per_seed_max=0)

    def test_no_moves_stop_reason_for_exhausted_whitelist(self):
        # 화이트리스트가 규칙의 피처로 이미 전부 소진되고 분포도 없으면 이동 0개.
        engine = _ScriptedEngine(lambda rule: _m(profit_pct=-1.0, mdd=1.0, calmar=0.0))
        result = run_seed_hillclimb(
            "seed", (("F1", ">", 1.0),), engine, {}, ("F1",),
            per_seed_max=10,
        )
        assert result.stopped_reason == "no_moves"
        assert result.trials_used == 1


# =============================================================== 43피처 화이트리스트


class TestFeaturesV3Whitelist:
    def test_whitelist_has_43_unique_features(self):
        assert len(features_v3.HILLCLIMB_FEATURE_WHITELIST) == 43
        assert len(set(features_v3.HILLCLIMB_FEATURE_WHITELIST)) == 43

    def test_v3_call_lhs_covers_18_derived_features(self):
        assert len(features_v3.V3_FEATURE_CALL_LHS) == 18

    def test_moving_average_uses_window_specific_function_call(self):
        assert features_v3.V3_FEATURE_CALL_LHS["이동평균60"] == "이동평균(60)"
        assert features_v3.V3_FEATURE_CALL_LHS["이동평균1200"] == "이동평균(1200)"

    def test_avg30_features_use_frozen_window(self):
        assert features_v3.V3_FEATURE_CALL_LHS["최고현재가"] == "최고현재가(30)"
        assert features_v3.V3_FEATURE_CALL_LHS["등락율각도"] == "등락율각도(30)"

    def test_render_condition_43_for_25_feature_matches_idioms(self):
        from alpha_lab.translate.idioms import render_condition

        assert features_v3.render_condition_43("등락율", ">", 1.5) == render_condition(
            "등락율", ">", 1.5
        )

    def test_render_condition_43_for_derived_feature(self):
        expr = features_v3.render_condition_43("최고현재가", ">", 100.0)
        assert expr == "(최고현재가(30)) > 100.0"

    def test_render_condition_43_unknown_feature_raises_keyerror(self):
        with pytest.raises(KeyError):
            features_v3.render_condition_43("존재하지않는피처", ">", 1.0)

    def test_translate_leaf_rule_43_roundtrip_with_derived_feature(self):
        rule = (("등락율", ">", 1.5), ("최고현재가", ">", 100.0))
        result = features_v3.translate_leaf_rule_43(
            rule, time_guard=SAMPLE_TIME_GUARD, universe_guard=UNIVERSE_GUARD_MONEYTOP_PROXY
        )
        assert result.expr is not None, result.reasons
        assert "최고현재가(30)" in result.expr
        assert "관심종목" in result.expr


# =============================================================== 시드 10건


class TestSeeds:
    def test_ten_seeds_declared(self):
        assert len(SEED_ORDER) == 10
        assert set(SEED_ORDER) == set(SEED_RULES) == set(SEED_META)

    @pytest.mark.parametrize("seed_name", list(SEED_RULES))
    def test_each_seed_translates_successfully(self, seed_name):
        result = translate_seed(seed_name)
        assert result.expr is not None, (seed_name, result.reasons)
        assert "and" in result.expr
        assert "self.Buy" not in result.expr  # 번역기는 조건식만 낸다(문장 아님).

    def test_seed_lift_is_descending_by_declared_order(self):
        lifts = [SEED_META[name].lift for name in SEED_ORDER]
        assert lifts == sorted(lifts, reverse=True)

    def test_seed_06_expands_two_sided_range_into_two_clauses(self):
        rule = SEED_RULES["ALP_V2SEED_06"]
        sides = [(f, op) for f, op, _ in rule if f == "전일비"]
        assert ("전일비", ">") in sides and ("전일비", "<=") in sides


# =============================================================== 매도식 고정


class TestSellPolicy:
    def test_sha_matches_sealed_champion_sell_sha(self):
        assert CHAMPION_SELL_EXPR_SHA256 == "8ef01e0ef2087ec95ac6b358b6f5c710414f3eb4dd401b01cc8162877f911c07"

    def test_sell_expr_ends_with_sell_call_no_trailing_newline(self):
        assert CHAMPION_SELL_EXPR.endswith("self.Sell()")
        assert not CHAMPION_SELL_EXPR.endswith("\n")


# =============================================================== engine_eval 순수 헬퍼


class TestEngineEvalHelpers:
    def test_build_pairs_json(self):
        pairs = build_pairs_json([("lbl", "ALP_V3H_01", "ALP_V3H_01")])
        assert pairs == [{"label": "lbl", "buy": "ALP_V3H_01", "sell": "ALP_V3H_01"}]

    def test_registration_item_enforces_alp_prefix(self):
        with pytest.raises(ValueError):
            registration_item("BAD_NAME", "if x:\n    self.Buy()", "if y:\n    self.Sell()")

    def test_registration_item_ok(self):
        item = registration_item("ALP_V3H_01", "if x:\n    self.Buy()", "if y:\n    self.Sell()", {"k": 1})
        assert item["name"] == "ALP_V3H_01"
        assert item["meta"] == {"k": 1}

    def test_build_train_config_overrides_window_only(self, tmp_path: Path):
        base = tmp_path / "base.json"
        base.write_text('{"bt_full_start": 1, "bt_full_end": 2, "other": "x"}', encoding="utf-8")
        cfg = build_train_config(base, bt_full_start=20220323, bt_full_end=20241231)
        assert cfg["bt_full_start"] == 20220323
        assert cfg["bt_full_end"] == 20241231
        assert cfg["other"] == "x"
        assert cfg["_derived"]["changed_fields_only"] == ["bt_full_start", "bt_full_end"]

    def test_metrics_from_generation_row_maps_fields(self):
        row = {
            "status": "ok", "total_profit_pct": 3.2, "mdd": 14.18, "calmar": 0.5,
            "trade_count": 31, "daily_avg_trades": 0.4, "gate_passed": 1, "reason": "ok",
        }
        metrics = metrics_from_generation_row(row)
        assert metrics.status == "ok"
        assert metrics.profit_pct == 3.2
        assert metrics.gate_passed is True

    def test_metrics_from_generation_row_defaults_missing_to_safe_values(self):
        metrics = metrics_from_generation_row({})
        assert metrics.status == "error"
        assert metrics.profit_pct == 0.0
        assert metrics.gate_passed is False

    def test_read_generation_metrics_from_temp_sqlite(self, tmp_path: Path):
        db_path = tmp_path / "loop_runs.db"
        con = sqlite3.connect(str(db_path))
        con.execute(
            "CREATE TABLE generations (run_id TEXT, gen_no INTEGER, status TEXT, "
            "calmar REAL, gate_passed INTEGER, reason TEXT, trade_count INTEGER, "
            "mdd REAL, profit REAL, total_profit_pct REAL, daily_avg_trades REAL, "
            "PRIMARY KEY (run_id, gen_no))"
        )
        con.execute(
            "INSERT INTO generations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("run1", 0, "ok", 0.42, 1, "gate ok", 10, 5.5, 12345.0, 1.23, 0.5),
        )
        con.commit()
        con.close()

        metrics = read_generation_metrics(db_path, "run1", 0)
        assert metrics is not None
        assert metrics.status == "ok"
        assert metrics.profit_pct == pytest.approx(1.23)
        assert metrics.mdd == pytest.approx(5.5)
        assert metrics.calmar == pytest.approx(0.42)
        assert metrics.gate_passed is True

    def test_read_generation_metrics_missing_row_returns_none(self, tmp_path: Path):
        db_path = tmp_path / "loop_runs.db"
        con = sqlite3.connect(str(db_path))
        con.execute("CREATE TABLE generations (run_id TEXT, gen_no INTEGER, status TEXT)")
        con.commit()
        con.close()
        assert read_generation_metrics(db_path, "missing", 0) is None
