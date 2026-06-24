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
    _CALLABLE_WHITELIST,
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
# 다밴드(여러 시간대×시총) 생성 역량 — 2026-06-14
# =====================================================================

class TestMultiBandGeneration:
    """검증기·프롬프트가 시간대×시총 이산 분기(다밴드) 조건식을 지원하는지.

    근거: 챔피언 THETA·T2C3(seed_902905 계열)가 곧 다밴드 구조다. 검증기가
    이를 통과시켜야 생성기가 다밴드 시드를 재현·확장할 수 있다(2026-06-14
    감사: 화이트리스트 누락으로 검증된 시드조차 재현 못 하던 것을 보강).
    """

    @pytest.mark.parametrize("tmpl_name", [
        "seed_902905",          # 2밴드(902/905)
        "seed_902905_t2late",   # 3밴드(T2C3 — 후반 시총 반전)
        "seed_902905_r2full",
    ])
    def test_proven_multiband_seed_passes(self, tmpl_name: str) -> None:
        """검증된 다밴드 시드를 LLM payload로 위장 → 오류 0(구조·어휘 통과)."""
        t = load_template(tmpl_name)
        payload = {
            "name": f"llmgen_probe_{tmpl_name}",
            "timeframe": t.timeframe,
            "buy_template": t.buy_code,
            "sell_template": t.sell_code,
            "params": [
                {"name": p.name, "default": p.default, "values": list(p.values),
                 "side": p.side, "note": p.note}
                for p in t.params
            ],
        }
        errors = validate_hypothesis(payload)
        assert errors == [], f"{tmpl_name} 다밴드 검증 실패: {errors}"

    def test_shifted_scalar_accessors_whitelisted(self) -> None:
        """검증된 시드가 쓰는 <스칼라>N(시프트) 접근자가 화이트리스트에 있어야."""
        for name in ("초당거래대금N", "매수총잔량N", "매도총잔량N", "현재가N"):
            assert name in _CALLABLE_WHITELIST, f"{name} 누락 — 검증된 시드 어휘"

    def test_prompt_instructs_multiband(self) -> None:
        """p5 프롬프트가 다밴드 생성을 지시하고 시드/T2C3 샘플·build_v5 실패를 포함."""
        p = build_prompt("테스트 원리", registry_summary(), lessons_text="")
        assert "시간대×시가총액 이산" in p           # 다밴드 과제 지시
        assert "T2C3" in p                           # 다밴드 성공 예시
        assert ("점수합산(build_v5)" in p or "점수 합산" in p)  # 합산 실패 예시
        assert "self.Buy()" in p                     # 골격 샘플


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

class TestEngineCostRules:
    """2026-06-12 대조실험으로 확정된 엔진 실측 규칙의 정적 차단."""

    def test_bare_function_variable_rejected(self) -> None:
        payload = _valid_payload()
        payload["buy_template"] = payload["buy_template"].replace(
            "if 매수:", "매수 = 매수 and 호가갭발생 == 1\nif 매수:"
        )
        errors = validate_hypothesis(payload)
        assert any("무인자" in e for e in errors)

    def test_bare_cumulative_variable_rejected(self) -> None:
        payload = _valid_payload()
        payload["buy_template"] = payload["buy_template"].replace(
            "if 매수:", "매수 = 매수 and 누적초당매수수량 >= 누적초당매도수량\nif 매수:"
        )
        errors = validate_hypothesis(payload)
        assert any("누적초당매수수량" in e for e in errors)

    def test_called_form_not_rejected(self) -> None:
        """(N) 호출형은 규칙에 걸리지 않아야 한다 — 기존 유효 payload 회귀."""
        assert validate_hypothesis(_valid_payload()) == []

    def test_depth_call_overuse_rejected(self) -> None:
        payload = _valid_payload()
        cond = " and ".join(f"매도잔량{i}(1) > 0" for i in (1, 2, 3, 4, 5))
        payload["buy_template"] = payload["buy_template"].replace(
            "if 매수:", f"매수 = 매수 and {cond}\nif 매수:"
        )
        errors = validate_hypothesis(payload)
        assert any("잔량i(N)" in e for e in errors)

    def test_depth_shift_form_allowed(self) -> None:
        """잔량iN(1) 시프트형은 비용 규칙에 안 걸린다(v5 실측 81초 정상)."""
        from ai_strategy_loop.scripts.gen_template_hypothesis import _engine_cost_errors
        code = "매수 = 매도잔량1N(1) > 매도잔량1 and 매수잔량1N(1) > 0"
        assert _engine_cost_errors(code) == []

    def test_scalar_called_as_function_rejected(self) -> None:
        """4세대 실측 회귀: 스칼라 초당매수수량(N) 호출형 → 정적 거부."""
        from ai_strategy_loop.scripts.gen_template_hypothesis import _engine_cost_errors
        code = "매수 = 초당매수수량(5) >= 초당매도수량(5) * 1.2"
        errors = _engine_cost_errors(code)
        assert any("검증되지 않은 호출형" in e for e in errors)

    def test_whitelisted_calls_pass(self) -> None:
        from ai_strategy_loop.scripts.gen_template_hypothesis import _engine_cost_errors
        code = "매수 = 이동평균(20, 1) < 현재가 and 누적초당매수수량(10) > 0 and 매도잔량1N(1) > 매도잔량1"
        assert _engine_cost_errors(code) == []

    # --- 윈도우 시프트 규칙 (14a/14b 회귀: shift -1 = 비용폭탄 356s) ---
    def test_window_shift_negative_literal_rejected(self) -> None:
        """윈도우함수 시프트 리터럴 -1은 정적 거부(14a/14b 타임아웃 회귀)."""
        from ai_strategy_loop.scripts.gen_template_hypothesis import _engine_cost_errors
        code = "현재가 > 최고현재가(30, -1) and 초당거래대금 >= 초당거래대금평균(8, -1) * 8"
        errors = _engine_cost_errors(code)
        assert any("시프트" in e and "1 이상" in e for e in errors), errors

    def test_window_shift_zero_literal_rejected(self) -> None:
        """시프트 0도 1 미만이므로 거부."""
        from ai_strategy_loop.scripts.gen_template_hypothesis import _window_shift_errors
        assert _window_shift_errors("이동평균(20, 0) < 현재가") != []

    def test_window_shift_one_literal_allowed(self) -> None:
        """시프트 1은 정상(gen8/gen9/THETA 관례, 18~33초)."""
        from ai_strategy_loop.scripts.gen_template_hypothesis import _window_shift_errors
        assert _window_shift_errors("현재가 > 최고현재가(30, 1) and 등락율각도(9, 2) >= 5") == []

    def test_window_one_arg_call_not_flagged(self) -> None:
        """1-인자 호출형(당일거래대금각도(30))은 시프트가 없어 검사 대상 아님."""
        from ai_strategy_loop.scripts.gen_template_hypothesis import _window_shift_errors
        assert _window_shift_errors("당일거래대금각도(30) > 5") == []

    def test_window_shift_slot_negative_value_rejected(self) -> None:
        """시프트 슬롯 후보값에 -1이 있으면 validate_hypothesis가 거부(슬롯 경로)."""
        payload = {
            "name": "llmgen_shift_slot_probe",
            "buy_template": "if 시분초 >= 90000 and 현재가 > 최고현재가({bw}, {bsh}):\n    self.Buy()",
            "sell_template": "if 수익률 >= {tp}:\n    self.Sell()",
            "params": [
                {"name": "bw", "default": 30, "values": [20, 30], "side": "buy", "note": "윈도우"},
                {"name": "bsh", "default": 1, "values": [1, 2, -1], "side": "buy", "note": "시프트"},
                {"name": "tp", "default": 5, "values": [5, 7], "side": "sell", "note": "익절"},
            ],
        }
        errors = validate_hypothesis(payload)
        assert any("시프트 슬롯" in e for e in errors), errors

    def test_window_shift_slot_all_positive_passes(self) -> None:
        """시프트 슬롯 값이 모두 1 이상이면 통과(캐너리 — 최소 템플릿 자체는 유효)."""
        payload = {
            "name": "llmgen_shift_slot_ok",
            "buy_template": "if 시분초 >= 90000 and 현재가 > 최고현재가({bw}, {bsh}):\n    self.Buy()",
            "sell_template": "if 수익률 >= {tp}:\n    self.Sell()",
            "params": [
                {"name": "bw", "default": 30, "values": [20, 30], "side": "buy", "note": "윈도우"},
                {"name": "bsh", "default": 1, "values": [1, 2, 3], "side": "buy", "note": "시프트"},
                {"name": "tp", "default": 5, "values": [5, 7], "side": "sell", "note": "익절"},
            ],
        }
        assert validate_hypothesis(payload) == []

