"""P5 (2026-06-12) — gen_template_hypothesis 단위 테스트.

네트워크 없이 실행 가능:
  - validate_hypothesis: 유효 payload → [], 접두 누락 → 오류, 스코프 위반 → 오류.
  - dry-run 전체 흐름: 가짜 LLM 함수 주입, 파일 미생성 확인.

실행:
  PYTHONUTF8=1 python -m pytest tests/unit/test_template_hypothesis.py -q
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401

from ai_strategy_loop.scripts.gen_template_hypothesis import (  # noqa: E402
    validate_hypothesis,
    build_prompt,
    registry_summary,
    main,
)
from ai_strategy_loop.tmap.template import TEMPLATE_DIR, load_template, render  # noqa: E402


# =====================================================================
# 헬퍼: orderflow_f07_ignition 코드를 재활용한 유효 payload 생성
# =====================================================================

def _valid_payload() -> Dict[str, Any]:
    """orderflow_f07_ignition.json에서 buy/sell 코드를 읽어 유효 payload를 만든다.

    실제 가드를 통과함이 이미 증명된 코드를 재활용하므로, 테스트가 가드 변경에
    자동으로 추종한다.
    """
    t = load_template("orderflow_f07_ignition")
    buy, sell = render(t)  # 기본값 렌더 — 슬롯 없는 완전 코드

    # 슬롯을 다시 뚫어 template 형태로 만든다: 숫자 리터럴 하나를 {cap_max}로 교체
    # (단순성 우선 — 슬롯 1개짜리 최소 템플릿)
    buy_tmpl = buy.replace("시가총액 < 3000", "시가총액 < {cap_max}")
    sell_tmpl = sell  # 매도는 슬롯 없이 그대로

    # sell_tmpl에 dummy 슬롯 없으므로 params는 buy 슬롯만
    params = [
        {
            "name": "cap_max",
            "default": 3000,
            "values": [1500, 2000, 3000, 5000],
            "side": "buy",
            "note": "시총 상한(억) — 테스트용",
        }
    ]

    return {
        "name": "llmgen_test_valid",
        "buy_template": buy_tmpl,
        "sell_template": sell_tmpl,
        "params": params,
    }


# =====================================================================
# validate_hypothesis 테스트
# =====================================================================

class TestValidateHypothesis:
    def test_valid_payload_returns_empty(self) -> None:
        """유효 payload(스코프 통과 보장 코드) → 오류 없음."""
        payload = _valid_payload()
        errors = validate_hypothesis(payload)
        assert errors == [], f"예상치 못한 오류: {errors}"

    def test_missing_llmgen_prefix_returns_error(self) -> None:
        """llmgen_ 접두 누락 → 오류 메시지 반환."""
        payload = _valid_payload()
        payload["name"] = "no_prefix_template"
        errors = validate_hypothesis(payload)
        assert any("llmgen_" in e for e in errors), (
            f"접두 오류가 감지되지 않음. 오류 목록: {errors}"
        )

    def test_nonexistent_variable_in_buy_returns_scope_error(self) -> None:
        """존재하지 않는 변수(미래참조/스코프 위반) → 오류 검출.

        'tick' timeframe 스코프에 없는 변수를 buy 코드에 삽입.
        variable_scope.check_variable_scope가 이를 차단한다.
        """
        payload = _valid_payload()
        # 존재하지 않는 변수명을 buy 코드에 삽입
        payload["buy_template"] = (
            payload["buy_template"]
            + "\nif 절대존재하지않는변수명_테스트용XYZ > 0:\n    매수 = False\n"
        )
        errors = validate_hypothesis(payload)
        assert errors, "스코프 위반이 감지되지 않음 (오류 목록이 비어 있음)"
        # scope 오류가 포함돼 있어야 한다
        assert any("scope" in e.lower() or "scope" in e for e in errors), (
            f"scope 오류 키워드 없음. 오류 목록: {errors}"
        )

    def test_missing_required_key_returns_error(self) -> None:
        """필수 키(sell_template) 누락 → 오류."""
        payload = _valid_payload()
        del payload["sell_template"]
        errors = validate_hypothesis(payload)
        assert any("sell_template" in e or "누락" in e for e in errors)

    def test_params_missing_note_key_returns_error(self) -> None:
        """params 항목에 note 키 누락 → 오류."""
        payload = _valid_payload()
        del payload["params"][0]["note"]
        errors = validate_hypothesis(payload)
        assert errors, "params 키 누락이 감지되지 않음"


# =====================================================================
# dry-run 전체 흐름 테스트 (가짜 LLM 주입)
# =====================================================================

class TestDryRunFlow:
    def test_dry_run_with_fake_llm_no_file_created(self, tmp_path: Path) -> None:
        """가짜 LLM(고정 JSON 반환) 주입 → dry-run이면 파일 미생성."""
        valid_payload = _valid_payload()

        def _fake_llm(prompt: str) -> str:
            """고정 JSON 문자열을 반환하는 가짜 LLM."""
            return json.dumps(valid_payload, ensure_ascii=False)

        # dry-run 실행 (--dry-run 기본값)
        result = main(
            llm_fn=_fake_llm,
            argv=["--dry-run", "--max-retries", "1"],
        )
        assert result == 0, f"main() 반환값 비정상: {result}"

        # 파일이 생성되지 않아야 한다
        generated = TEMPLATE_DIR / "llmgen_test_valid.json"
        assert not generated.exists(), (
            f"dry-run인데 파일이 생성됨: {generated}"
        )

    def test_dry_run_with_fake_llm_bad_prefix_returns_nonzero(self) -> None:
        """접두 오류 payload → main() 비정상 종료코드."""
        bad_payload = _valid_payload()
        bad_payload["name"] = "bad_prefix_template"

        def _fake_llm(prompt: str) -> str:
            return json.dumps(bad_payload, ensure_ascii=False)

        result = main(
            llm_fn=_fake_llm,
            argv=["--dry-run", "--max-retries", "1"],
        )
        assert result != 0, "오류 payload인데 0 반환됨"


# =====================================================================
# build_prompt / registry_summary 연기 테스트
# =====================================================================

class TestBuildPrompt:
    def test_registry_summary_contains_known_template(self) -> None:
        """registry_summary가 orderflow_f07_ignition을 포함해야 한다."""
        summary = registry_summary()
        assert "orderflow_f07_ignition" in summary

    def test_build_prompt_contains_principle_text(self) -> None:
        """build_prompt 결과에 전달된 원리 텍스트가 포함돼야 한다."""
        prompt = build_prompt("테스트 원리 텍스트", registry_summary())
        assert "테스트 원리 텍스트" in prompt

    def test_build_prompt_contains_failure_lesson(self) -> None:
        """build_prompt 결과에 실패 교훈(임계 이식 금지) 문구가 포함돼야 한다."""
        prompt = build_prompt("원리", registry_summary())
        assert "임계 이식 금지" in prompt

# ---------------------------------------------------------------------------
# 2026-06-12 추가: timeframe(tick|min) 지원 + 교훈 컨텍스트 주입
# ---------------------------------------------------------------------------

class TestTimeframeSupport:
    def test_min_timeframe_valid_payload_passes(self) -> None:
        """min 템플릿 코드 + timeframe='min' payload가 min 스코프로 통과한다."""
        spec = json.loads(
            (TEMPLATE_DIR / "min_morning_momentum.json").read_text(encoding="utf-8")
        )
        payload = {
            "name": "llmgen_min_probe",
            "buy_template": spec["buy_code"],
            "sell_template": spec["sell_code"],
            "params": spec["params"],
            "timeframe": "min",
        }
        assert validate_hypothesis(payload) == []

    def test_min_code_with_tick_timeframe_fails_scope(self) -> None:
        """분당 변수 코드를 tick 스코프로 검증하면 scope 오류가 나야 한다."""
        spec = json.loads(
            (TEMPLATE_DIR / "min_morning_momentum.json").read_text(encoding="utf-8")
        )
        payload = {
            "name": "llmgen_min_probe",
            "buy_template": spec["buy_code"],
            "sell_template": spec["sell_code"],
            "params": spec["params"],
            "timeframe": "tick",
        }
        errors = validate_hypothesis(payload)
        assert errors, "tick 스코프에서 분당 변수가 통과하면 안 된다"

    def test_invalid_timeframe_rejected(self) -> None:
        payload = _valid_payload()
        payload["timeframe"] = "day"
        errors = validate_hypothesis(payload)
        assert any("timeframe" in e for e in errors)

    def test_default_timeframe_is_tick(self) -> None:
        """timeframe 미지정 payload는 기존(tick) 동작 그대로 통과한다."""
        payload = _valid_payload()
        payload.pop("timeframe", None)
        assert validate_hypothesis(payload) == []


class TestLessonsInjection:
    def test_build_prompt_includes_lessons_when_given(self) -> None:
        out = build_prompt("원리", "템플릿목록", lessons_text="교훈본문XYZ")
        assert "교훈본문XYZ" in out
        assert "누적 기각 이력" in out

    def test_build_prompt_without_lessons_unchanged(self) -> None:
        out = build_prompt("원리", "템플릿목록")
        assert "누적 기각 이력" not in out

class TestTypeGuards:
    def test_params_as_string_list_returns_error_not_crash(self) -> None:
        """실전 LLM이 params를 문자열 배열로 보낸 사고의 회귀 테스트."""
        payload = _valid_payload()
        payload["params"] = ["cap_max", "take_hard"]
        errors = validate_hypothesis(payload)
        assert any("객체 배열" in e for e in errors)

    def test_buy_template_as_list_returns_error_not_crash(self) -> None:
        payload = _valid_payload()
        payload["buy_template"] = ["라인1", "라인2"]
        errors = validate_hypothesis(payload)
        assert any("문자열" in e for e in errors)


class TestSchemaInPrompt:
    def test_build_prompt_contains_output_schema(self) -> None:
        out = build_prompt("원리", "목록")
        assert "출력 형식" in out and "객체 배열" in out

