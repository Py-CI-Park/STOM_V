"""P4 — 메타분석 엔진 단위 테스트 (집계 + 영속 + 환류 주입 토글).

검증:
  - aggregate_meta_insights: 통과 전략 공통 변수 / 개선 변경 / 실패 패턴 집계.
  - save/load_meta_insights: JSON 영속 라운드트립.
  - build_meta_seed_text: 인사이트 → NL 가이드(신호 없으면 None).
  - build_messages(meta_seed=...): 토글 ON이면 user 메시지에 주입, OFF(None)면 미주입.
  - to_page_data: LIVE 메타 패널 직렬화.

합성 누적 generations만 사용(백테/루프/실DB 없음).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.meta import (  # noqa: E402
    MetaInsights,
    aggregate_meta_insights,
    build_meta_seed_text,
    load_meta_insights,
    save_meta_insights,
)
from ai_strategy_loop.meta.seed import to_page_data  # noqa: E402


def _synthetic_generations():
    """여러 run에 걸친 합성 누적 generations.

    통과 세대 3개(체결강도 공통, 일부 등락율). 개선 세대 2개(parent 대비 graded↑).
    실패: 0거래 1개, 과매매 1개, 고MDD 1개.
    """
    return [
        # run1 — 통과 + 개선 체인.
        {"run_id": "r1", "gen_no": 0, "status": "ok", "score": 1.0, "gate_passed": 1,
         "trade_count": 40, "mdd": 15.0, "profit": 100000.0,
         "strategy_gist": "if 체결강도 > 120:", "parent_gen": None, "diff_from_parent": None},
        {"run_id": "r1", "gen_no": 1, "status": "ok", "score": 1.3, "gate_passed": 1,
         "trade_count": 38, "mdd": 12.0, "profit": 150000.0,
         "strategy_gist": "if 체결강도 > 130 and 등락율 > 3:", "parent_gen": 0,
         "diff_from_parent": "손절 강화로 MDD 감소"},
        # run1 실패: 과매매.
        {"run_id": "r1", "gen_no": 2, "status": "ok", "score": 0.7, "gate_passed": 0,
         "trade_count": 220, "mdd": 25.0, "profit": -10000.0,
         "strategy_gist": "if 분당거래대금 > 1:", "parent_gen": 0,
         "diff_from_parent": "진입 완화(과매매)"},
        # run2 — 통과 + 개선.
        {"run_id": "r2", "gen_no": 0, "status": "ok", "score": 0.9, "gate_passed": 0,
         "trade_count": 0, "mdd": 0.0, "profit": 0.0,
         "strategy_gist": "if 체결강도 > 200:", "parent_gen": None, "diff_from_parent": None},
        {"run_id": "r2", "gen_no": 1, "status": "ok", "score": 1.5, "gate_passed": 1,
         "trade_count": 45, "mdd": 35.0, "profit": 200000.0,
         "strategy_gist": "if 체결강도 > 110:", "parent_gen": 0,
         "diff_from_parent": "진입 문턱 낮춤(거래 발생)"},
    ]


class TestAggregate:
    def test_common_pass_vars(self):
        ins = aggregate_meta_insights(_synthetic_generations())
        # 통과 세대 3개(r1g0, r1g1, r2g1) 모두 체결강도 사용 → 최상위 공통 변수.
        var_names = [v[0] for v in ins.common_pass_vars]
        assert "체결강도" in var_names
        top = ins.common_pass_vars[0]
        assert top[0] == "체결강도"
        assert top[1] == 3  # 통과 세대 3개에서 출현.
        assert ins.passing_count == 3

    def test_improving_changes(self):
        ins = aggregate_meta_insights(_synthetic_generations())
        phrases = [c[0] for c in ins.improving_changes]
        # r1g1(1.3>1.0)·r2g1(1.5>0.9)는 개선. r1g2(0.7<1.0)는 개선 아님 → 제외.
        assert any("MDD 감소" in p for p in phrases)
        assert any("거래 발생" in p for p in phrases)
        assert not any("과매매" in p for p in phrases)

    def test_failure_patterns(self):
        ins = aggregate_meta_insights(_synthetic_generations())
        fp = ins.failure_patterns
        assert fp["overtrade"] == 1   # r1g2 (220건).
        assert fp["zero_trade"] == 1  # r2g0 (0건).
        assert fp["high_mdd"] == 1    # r2g1 (35 > 30).

    def test_empty_generations(self):
        ins = aggregate_meta_insights([])
        assert ins.total_generations == 0
        assert ins.common_pass_vars == []
        assert "메타분석 불가" in ins.note

    def test_small_passing_sample_skips_common_vars(self):
        # 통과 세대 1개뿐이면(MIN_PASSING_FOR_COMMON 미만) 공통 변수를 신뢰 안 함.
        gens = [
            {"run_id": "r", "gen_no": 0, "status": "ok", "score": 1.0, "gate_passed": 1,
             "trade_count": 40, "mdd": 10.0, "profit": 1.0, "strategy_gist": "if 체결강도 > 1:",
             "parent_gen": None, "diff_from_parent": None},
        ]
        ins = aggregate_meta_insights(gens)
        assert ins.passing_count == 1
        assert ins.common_pass_vars == []


class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path):
        path = str(tmp_path / "meta.json")
        ins = aggregate_meta_insights(_synthetic_generations())
        save_meta_insights(ins, path)
        loaded = load_meta_insights(path)
        assert loaded is not None
        assert loaded.total_generations == ins.total_generations
        assert loaded.passing_count == ins.passing_count
        assert loaded.common_pass_vars == ins.common_pass_vars

    def test_load_missing_returns_none(self, tmp_path):
        assert load_meta_insights(str(tmp_path / "nope.json")) is None


class TestMetaSeedText:
    def test_seed_text_includes_common_vars(self):
        ins = aggregate_meta_insights(_synthetic_generations())
        text = build_meta_seed_text(ins)
        assert text is not None
        assert "체결강도" in text
        assert "누적 메타분석" in text

    def test_seed_text_none_when_no_signal(self):
        # 공통 변수도·개선 변경도 없으면 None(주입 안 함).
        empty = MetaInsights(total_generations=5, passing_count=0)
        assert build_meta_seed_text(empty) is None

    def test_seed_text_none_when_insights_none(self):
        assert build_meta_seed_text(None) is None


class TestMetaSeedPromptInjection:
    def _user_text(self, messages):
        return next(m["content"] for m in messages if m["role"] == "user")

    def test_meta_seed_on_injects_into_prompt(self):
        meta_seed = "누적 메타분석(과거 여러 run에서 학습한 공통 신호):\n- 공통 변수: 체결강도"
        messages = build_messages("buy", timeframe="min", meta_seed=meta_seed)
        user = self._user_text(messages)
        assert "누적 메타분석" in user
        assert "체결강도" in user

    def test_meta_seed_off_not_injected(self):
        # meta_seed=None(기본/토글 OFF) → 메타 섹션 미주입(하위호환).
        messages = build_messages("buy", timeframe="min")
        user = self._user_text(messages)
        assert "누적 메타분석" not in user

    def test_meta_seed_coexists_with_history_and_autopsy(self):
        messages = build_messages(
            "buy", timeframe="min",
            history_summary="이력: gen3 MDD 초과",
            meta_seed="누적 메타분석: 공통 변수 체결강도",
            autopsy_feedback="진입 완화",
        )
        user = self._user_text(messages)
        assert "누적 진화 이력" in user
        assert "누적 메타분석" in user
        assert "직전 백테스트 부검 피드백" in user


class TestMetaPageData:
    def test_to_page_data_json_safe(self):
        import json
        ins = aggregate_meta_insights(_synthetic_generations())
        pd = to_page_data(ins)
        assert pd["status"] == "ok"
        assert pd["passing_count"] == 3
        json.dumps(pd)

    def test_to_page_data_empty(self):
        assert to_page_data(None)["status"] == "empty"
