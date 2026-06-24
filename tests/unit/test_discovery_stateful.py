"""P2 (2026-06-15) — 야간 발굴 하네스 유상태 코어 테스트 (결정론, 백테/LLM 미실행).

build_feedback(ledger→회피/선호) + generate의 --feedback-file 전달 + build_prompt 주입을
모킹/순수함수로 검증. 무상태 degrade(빈 ledger→빈 피드백)도 확인.

실행:
  PYTHONUTF8=1 python -m pytest tests/unit/test_discovery_stateful.py -q
"""
from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401

from ai_strategy_loop.scripts import tmap_multiband_discovery as disc  # noqa: E402
from ai_strategy_loop.scripts.gen_template_hypothesis import (  # noqa: E402
    build_prompt, registry_summary,
)


def _rec(it, verdict, template, robust=None):
    ev = {"verdict": verdict}
    if robust:
        ev["robust"] = robust
    return {"iter": it, "track": "tick_new", "template": template, "eval": ev}


class TestBuildFeedback:
    def test_empty_ledger_degrades_to_stateless(self) -> None:
        """빈 ledger → 빈 피드백(무상태 degrade — 에러 없이)."""
        assert disc.build_feedback([]) == ""

    def test_avoid_lines_from_nogo(self) -> None:
        """no-go 템플릿이 회피-홍수 라인에 들어가야(같은 골격 재제출 금지)."""
        recs = [_rec(0, "no-go", "llmgen_flood_a"), _rec(1, "no-go", "llmgen_flood_b")]
        fb = disc.build_feedback(recs)
        assert "[회피-홍수]" in fb
        assert "llmgen_flood_a" in fb and "llmgen_flood_b" in fb
        assert "no-go(홍수) 2" in fb

    def test_smokepass_goes_to_avoid_overfit_not_prefer(self) -> None:
        """★smoke-pass(2분기 흑자·전체기간 과적합)는 *회피-과적합*에 — 선호 아님(결함 수정)."""
        recs = [_rec(0, "smoke-pass", "llmgen_sp",
                     robust={"label": "TMAP b1_cap_max=1800", "q1": 200000, "q2": 390000})]
        fb = disc.build_feedback(recs)
        assert "[회피-과적합]" in fb
        assert "b1_cap_max=1800" in fb
        assert "[선호] 전체기간 생존" not in fb  # 생존 아님 → 선호 라인 없음
        assert "2분기과적합 1" in fb

    def test_survivor_goes_to_prefer(self) -> None:
        """전체기간 생존(train-pass)만 선호 라인에."""
        recs = [_rec(0, "train-pass", "llmgen_surv",
                     robust={"label": "TMAP b1_cap_max=2200", "q1": 300000, "q2": 410000})]
        fb = disc.build_feedback(recs)
        assert "[선호] 전체기간 생존" in fb
        assert "b1_cap_max=2200" in fb

    def test_anchor_line_when_no_prefer(self) -> None:
        """전체기간 생존 코너 없으면 검증앵커(THETA) 고정 + 과적합 회피 지시."""
        recs = [_rec(0, "no-go", "llmgen_x")]
        fb = disc.build_feedback(recs)
        assert "검증앵커" in fb and "THETA" in fb
        assert "과적합" in fb  # 과적합 추구 금지 핵심 메시지

    def test_feedback_deterministic(self) -> None:
        """동일 ledger → 동일 피드백(결정론)."""
        recs = [_rec(0, "no-go", "llmgen_x"), _rec(1, "no-go", "llmgen_y")]
        assert disc.build_feedback(recs) == disc.build_feedback(recs)


class TestPromptInjection:
    def test_build_prompt_includes_feedback(self) -> None:
        """build_prompt에 feedback_text 주면 환류 블록이 프롬프트에 출현."""
        p = build_prompt("원리", registry_summary(), "", feedback_text="회피: llmgen_flood_a")
        assert "직전 결과 환류" in p
        assert "회피: llmgen_flood_a" in p

    def test_build_prompt_no_feedback_omits_block(self) -> None:
        """feedback 없으면 환류 블록 없음(무상태 = 기존 동작)."""
        p = build_prompt("원리", registry_summary(), "")
        assert "직전 결과 환류" not in p


class TestGeneratePassesFeedback:
    def test_generate_passes_feedback_file(self, monkeypatch) -> None:
        """feedback 주면 --feedback-file 인자가 subprocess에 전달."""
        captured = {}

        def fake_run(args_list, timeout):
            captured["args"] = args_list
            return 0, "[저장] /x/llmgen_test.json"

        monkeypatch.setattr(disc, "run_cmd", fake_run)
        name, _ = disc.generate("원리", feedback_text="회피: a")
        assert name == "llmgen_test"
        assert "--feedback-file" in captured["args"]

    def test_generate_no_feedback_omits_flag(self, monkeypatch) -> None:
        """feedback 없으면 --feedback-file 없음(무상태)."""
        captured = {}

        def fake_run(args_list, timeout):
            captured["args"] = args_list
            return 0, "[저장] /x/llmgen_test.json"

        monkeypatch.setattr(disc, "run_cmd", fake_run)
        disc.generate("원리")
        assert "--feedback-file" not in captured["args"]
