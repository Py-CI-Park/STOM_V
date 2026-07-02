"""T4.3 — 원리 일관성 게이트 단위 테스트 (네트워크/실LLM 없음).

검증 대상:
  1) 순수 함수 check_principle_consistency 의 규칙별 위반/통과:
     - CSC-06: 거래량/거래대금 조건 없는 돌파성 매수 (reject)
     - CSC-07: 매수식에 대응 손절 매도조건 부재 (reject)
     - CSC-10: tick 조건식 시간창 09:00~09:30 위반 (reject)
     - PG-META-01: metadata.principle_ids 부재 (advisory)
     - None 코드(모름)에 대한 판정 보류(skip)
  2) generator 배선: 토글 OFF(기본) 시 게이트 미작동(byte-동일),
     ON 시 reject 위반 → 저장 거부→재시도, advisory 만으로는 저장 차단 없음.
  3) config: principle_gate_enabled 토글 기본 OFF + from_dict/to_dict 왕복 유지.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# generator 는 cli.* 를 지연 import 한다. bootstrap 먼저 import (env-before-import 계약).
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.brain.principle_gate import (  # noqa: E402
    SEVERITY_ADVISORY,
    SEVERITY_REJECT,
    check_principle_consistency,
)
from ai_strategy_loop.config import LoopConfig  # noqa: E402


def _rule_ids(violations):
    return [v["rule_id"] for v in violations]


def _by_rule(violations, rule_id):
    return [v for v in violations if v["rule_id"] == rule_id]


# 판정 보류/advisory 잡음을 배제하기 위한 공통 metadata (원리 표시 있음).
_META_OK = {"timeframe": "min", "principle_ids": ["P4", "P8"]}
_META_TICK_OK = {"timeframe": "tick", "principle_ids": ["P4"]}


# ===================================================================
# CSC-06 — 거래량/거래대금 조건 없는 돌파성 매수
# ===================================================================

_BREAKOUT_NO_VOLUME_BUY = (
    "매수 = False\n"
    "if 90000 <= 시분초 < 93000 and 현재가 >= 최고현재가(30, 1):\n"
    "    매수 = True\n"
)
_BREAKOUT_WITH_VOLUME_BUY = (
    "매수 = False\n"
    "if 90000 <= 시분초 < 93000 and 현재가 >= 최고현재가(30, 1) "
    "and 분당거래대금 > 30000000 and 체결강도 > 100:\n"
    "    매수 = True\n"
)
_NON_BREAKOUT_BUY = (
    "매수 = False\n"
    "if 3 <= 등락율 <= 25 and 체결강도 >= 100:\n"
    "    매수 = True\n"
)


def test_csc06_breakout_without_volume_is_reject():
    violations = check_principle_consistency(_BREAKOUT_NO_VOLUME_BUY, None, _META_OK)
    hits = _by_rule(violations, "CSC-06")
    assert len(hits) == 1
    assert hits[0]["severity"] == SEVERITY_REJECT
    assert hits[0]["message"]


def test_csc06_breakout_with_volume_passes():
    violations = check_principle_consistency(_BREAKOUT_WITH_VOLUME_BUY, None, _META_OK)
    assert _by_rule(violations, "CSC-06") == []


def test_csc06_non_breakout_buy_not_judged():
    # 돌파성이 아니면 거래량 조건이 없어도 CSC-06 은 아니다.
    violations = check_principle_consistency(_NON_BREAKOUT_BUY, None, _META_OK)
    assert _by_rule(violations, "CSC-06") == []


def test_csc06_skipped_when_buy_code_unknown():
    violations = check_principle_consistency(None, None, _META_OK)
    assert _by_rule(violations, "CSC-06") == []


# ===================================================================
# CSC-07 — 매수식에 대응 손절 매도조건 부재
# ===================================================================

_SELL_TRAILING_ONLY = (
    "매도 = False\n"
    "if 최고수익률 >= 3 and 수익률 <= 최고수익률 * 0.6:\n"
    "    매도 = True\n"
)
_SELL_WITH_HARD_STOP = (
    "매도 = False\n"
    "if 수익률 <= -2.0:\n"
    "    매도 = True\n"
    "elif 최고수익률 >= 3 and 수익률 <= 최고수익률 * 0.6:\n"
    "    매도 = True\n"
)
_SELL_WITH_ENTRY_BREAK = (
    "매도 = False\n"
    "if 현재가 < 매수가 * 0.98:\n"
    "    매도 = True\n"
)
# 중간변수 경유 구조 하단 이탈 (chart_sulsa DOJI_LOWER_BREAKDOWN 꼴).
_SELL_STRUCT_LOWER_VIA_VAR = (
    "매도 = False\n"
    "도지하단 = 분봉저가N(1)\n"
    "if 현재가 < 도지하단 * 0.997:\n"
    "    매도 = True\n"
)
# 하단이탈율 계열 손절 (chart_sulsa MICRO_DOJI_FAIL / BOX_LOWER_BREAKDOWN 꼴).
_SELL_LOWER_BREAK_RATE = (
    "매도 = False\n"
    "박스하단 = 최저현재가(60, 1)\n"
    "하단이탈율 = ((현재가 - 박스하단) / 박스하단) * 100 if 박스하단 > 0 else 0\n"
    "if 하단이탈율 <= -0.25:\n"
    "    매도 = True\n"
)
# self.vars 하드 스톱 (음수 기본값 관용구 — idiom_dictionary §10, OPT 매도식 꼴).
_SELL_VARS_HARD_STOP = (
    "매도 = False\n"
    "if 수익률 <= self.vars[20]:\n"
    "    매도 = True\n"
)


def test_csc07_sell_without_stop_loss_is_reject():
    violations = check_principle_consistency(_NON_BREAKOUT_BUY, _SELL_TRAILING_ONLY, _META_OK)
    hits = _by_rule(violations, "CSC-07")
    assert len(hits) == 1
    assert hits[0]["severity"] == SEVERITY_REJECT


def test_csc07_hard_stop_passes():
    violations = check_principle_consistency(_NON_BREAKOUT_BUY, _SELL_WITH_HARD_STOP, _META_OK)
    assert _by_rule(violations, "CSC-07") == []


def test_csc07_entry_price_break_passes():
    violations = check_principle_consistency(_NON_BREAKOUT_BUY, _SELL_WITH_ENTRY_BREAK, _META_OK)
    assert _by_rule(violations, "CSC-07") == []


def test_csc07_skipped_when_sell_code_unknown():
    # generator 가 buy 만 생성할 때 sell=None(모름) → 판정 보류.
    violations = check_principle_consistency(_NON_BREAKOUT_BUY, None, _META_OK)
    assert _by_rule(violations, "CSC-07") == []


def test_csc07_trailing_only_not_confused_by_choego_suikryul():
    # `최고수익률` 부분문자열이 `수익률 <= -k` 로 오인되지 않아야 한다(경계 가드).
    assert _by_rule(
        check_principle_consistency(None, "if 최고수익률 <= -1:\n    매도 = True\n", _META_OK),
        "CSC-07",
    ) != []  # 최고수익률 조건은 손절로 인정되지 않는다 → 위반 유지.


def test_csc07_structural_lower_break_via_intermediate_var_passes():
    # `현재가 < 도지하단*k` — 중간변수 경유 구조 하단 이탈은 CSC-07 손절로 인정.
    violations = check_principle_consistency(None, _SELL_STRUCT_LOWER_VIA_VAR, _META_OK)
    assert _by_rule(violations, "CSC-07") == []


def test_csc07_lower_breakdown_rate_passes():
    # `하단이탈율 <= -0.25` — 하단이탈율 계열 구조 손절은 CSC-07 손절로 인정.
    violations = check_principle_consistency(None, _SELL_LOWER_BREAK_RATE, _META_OK)
    assert _by_rule(violations, "CSC-07") == []


def test_csc07_self_vars_hard_stop_passes():
    # `수익률 <= self.vars[i]` — 최적화 변수 하드 스톱은 CSC-07 손절로 인정.
    violations = check_principle_consistency(None, _SELL_VARS_HARD_STOP, _META_OK)
    assert _by_rule(violations, "CSC-07") == []


# ===================================================================
# CSC-10 — tick 시간창 09:00~09:30
# ===================================================================

_TICK_BUY_IN_WINDOW = (
    "매수 = False\n"
    "if 90000 <= 시분초 < 93000 and 체결강도 > 120 and 초당거래대금 > 30000000:\n"
    "    매수 = True\n"
)
_TICK_BUY_WIDE_WINDOW = (
    "매수 = False\n"
    "if 90000 <= 시분초 < 100000 and 체결강도 > 120:\n"
    "    매수 = True\n"
)
_TICK_BUY_NO_WINDOW = (
    "매수 = False\n"
    "if 체결강도 > 120 and 초당거래대금 > 30000000:\n"
    "    매수 = True\n"
)
_TICK_SELL_WITH_CLOSE = (
    "매도 = False\n"
    "if 수익률 <= -2.0 or 시분초 >= 93000:\n"
    "    매도 = True\n"
)
_TICK_SELL_NO_CLOSE = (
    "매도 = False\n"
    "if 수익률 <= -2.0:\n"
    "    매도 = True\n"
)
# 임계값 152000(15:20) — 09:30 이후 보유를 허용하는 무효 강제 종료 분기.
_TICK_SELL_LATE_CLOSE = (
    "매도 = False\n"
    "if 수익률 <= -2.0 or 시분초 >= 152000:\n"
    "    매도 = True\n"
)
# 임계값 92000(09:20) — 09:30 이내 청산을 보장하는 유효한 조기 강제 종료 분기.
_TICK_SELL_EARLY_CLOSE = (
    "매도 = False\n"
    "if 수익률 <= -2.0 or 시분초 >= 92000:\n"
    "    매도 = True\n"
)


def test_csc10_tick_buy_in_window_passes():
    violations = check_principle_consistency(_TICK_BUY_IN_WINDOW, None, _META_TICK_OK)
    assert _by_rule(violations, "CSC-10") == []


def test_csc10_tick_buy_beyond_0930_is_reject():
    violations = check_principle_consistency(_TICK_BUY_WIDE_WINDOW, None, _META_TICK_OK)
    hits = _by_rule(violations, "CSC-10")
    assert len(hits) == 1
    assert hits[0]["severity"] == SEVERITY_REJECT


def test_csc10_tick_buy_without_time_gate_is_reject():
    violations = check_principle_consistency(_TICK_BUY_NO_WINDOW, None, _META_TICK_OK)
    assert len(_by_rule(violations, "CSC-10")) == 1


def test_csc10_min_timeframe_not_judged():
    # 같은 (창 없는) 매수식도 min 이면 CSC-10 대상이 아니다.
    violations = check_principle_consistency(_TICK_BUY_NO_WINDOW, None, _META_OK)
    assert _by_rule(violations, "CSC-10") == []


def test_csc10_tick_sell_requires_session_close_exit():
    with_close = check_principle_consistency(None, _TICK_SELL_WITH_CLOSE, _META_TICK_OK)
    assert _by_rule(with_close, "CSC-10") == []

    without_close = check_principle_consistency(None, _TICK_SELL_NO_CLOSE, _META_TICK_OK)
    hits = _by_rule(without_close, "CSC-10")
    assert len(hits) == 1
    assert hits[0]["severity"] == SEVERITY_REJECT


def test_csc10_tick_sell_late_close_threshold_is_reject():
    # `시분초 >= 152000`(15:20까지 보유 허용)은 유효 강제 종료가 아니다 → 위반.
    violations = check_principle_consistency(None, _TICK_SELL_LATE_CLOSE, _META_TICK_OK)
    hits = _by_rule(violations, "CSC-10")
    assert len(hits) == 1
    assert hits[0]["severity"] == SEVERITY_REJECT


def test_csc10_tick_sell_early_close_threshold_passes():
    # `시분초 >= 92000`(09:20 조기청산)은 09:30 이내 청산을 보장 → 위반 없음.
    violations = check_principle_consistency(None, _TICK_SELL_EARLY_CLOSE, _META_TICK_OK)
    assert _by_rule(violations, "CSC-10") == []


# ===================================================================
# PG-META-01 — principle_ids 부재 advisory
# ===================================================================

def test_meta_missing_principle_ids_is_advisory_only():
    violations = check_principle_consistency(_NON_BREAKOUT_BUY, _SELL_WITH_HARD_STOP, None)
    hits = _by_rule(violations, "PG-META-01")
    assert len(hits) == 1
    assert hits[0]["severity"] == SEVERITY_ADVISORY
    # advisory 외 reject 는 없어야 한다(전 규칙 통과 케이스).
    assert [v for v in violations if v["severity"] == SEVERITY_REJECT] == []


def test_meta_with_principle_ids_no_advisory_and_clean_pair_is_empty():
    violations = check_principle_consistency(
        _BREAKOUT_WITH_VOLUME_BUY, _SELL_WITH_HARD_STOP, _META_OK
    )
    assert violations == []


def test_violation_dict_shape():
    violations = check_principle_consistency(_BREAKOUT_NO_VOLUME_BUY, _SELL_TRAILING_ONLY, None)
    assert set(_rule_ids(violations)) == {"CSC-06", "CSC-07", "PG-META-01"}
    for v in violations:
        assert set(v.keys()) == {"rule_id", "severity", "message"}
        assert v["severity"] in (SEVERITY_REJECT, SEVERITY_ADVISORY)


# ===================================================================
# 레퍼런스 자기일관성 — chart_sulsa_v7_conditions.json 이 게이트를 통과해야 한다
# ===================================================================

_CHART_SULSA_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ai_strategy_loop", "brain", "data", "chart_sulsa_v7_conditions.json",
)

# 순수 익절식(손절 분기 없음) — constraints_checklist.md CSC-07 문언상
# "손절 매도조건 부재" reject 가 정당하므로 자기일관성 검사에서 명시 제외.
_PURE_PROFIT_EXIT_IDS = {
    "CSS_V7_MIN_S_TARGET_TRAILING_0900_1518",
}


def _load_chart_sulsa_conditions():
    with open(_CHART_SULSA_JSON, encoding="utf-8") as f:
        return json.load(f)["conditions"]


def test_reference_tick_buy_conditions_pass_csc06_and_csc10():
    # 레퍼런스 tick 매수식은 CSC-06(거래량)/CSC-10(시간창) 오탐이 없어야 한다.
    conditions = _load_chart_sulsa_conditions()
    tick_buys = [c for c in conditions if c["lane"] == "tick" and c["side"] == "buy"]
    assert tick_buys, "레퍼런스 JSON 에 tick 매수식이 없다 — 데이터/필터 확인"
    for cond in tick_buys:
        meta = {"timeframe": "tick", "principle_ids": cond.get("principle_ids") or ["P0"]}
        violations = check_principle_consistency(cond["code"], None, meta)
        offending = [v for v in violations if v["rule_id"] in ("CSC-06", "CSC-10")]
        assert offending == [], f"{cond['id']}: {offending}"


def test_reference_sell_conditions_pass_csc07_except_pure_profit_exits():
    # 레퍼런스 매도식(도지/하단 구조 손절 포함)은 CSC-07 오탐 reject 가 없어야
    # 한다. DOJI_FAIL/LOWER_BREAKDOWN 항목이 실제 존재하는지 함께 확인한다.
    conditions = _load_chart_sulsa_conditions()
    sells = [c for c in conditions if c["side"] == "sell"]
    structural_ids = [
        c["id"] for c in sells
        if "DOJI_FAIL" in c["id"] or "LOWER_BREAKDOWN" in c["id"]
    ]
    assert structural_ids, "레퍼런스 JSON 에 DOJI_FAIL/LOWER_BREAKDOWN 매도식이 없다"
    for cond in sells:
        if cond["id"] in _PURE_PROFIT_EXIT_IDS:
            continue  # 순수 익절식 — 체크리스트 문언상 정당한 reject.
        meta = {"timeframe": cond["lane"], "principle_ids": cond.get("principle_ids") or ["P0"]}
        violations = check_principle_consistency(None, cond["code"], meta)
        offending = _by_rule(violations, "CSC-07")
        assert offending == [], f"{cond['id']}: {offending}"


# ===================================================================
# generator 배선 (opt-in) — mock provider, TEMP DB
# ===================================================================

_FENCED_VIOLATING_BUY = (
    "```python\n" + _BREAKOUT_NO_VOLUME_BUY + "if 매수:\n    self.Buy()\n```"
)
_FENCED_COMPLIANT_BUY = (
    "```python\n" + _BREAKOUT_WITH_VOLUME_BUY + "if 매수:\n    self.Buy()\n```"
)


class _FakeUsage:
    prompt_tokens = 10
    completion_tokens = 20
    total_tokens = 30


class _FakeResult:
    def __init__(self, text):
        self.text = text
        self.usage = _FakeUsage()


class _ScriptedProvider:
    """미리 정해진 응답을 순서대로 돌려주는 mock provider."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def chat(self, messages, model=None, **kw):
        self.calls.append(messages)
        return _FakeResult(self._responses.pop(0))


def test_generator_gate_off_by_default_saves_violating_code():
    # 토글 OFF(기본) — CSC-06 위반 코드도 기존 게이트만 통과하면 그대로 저장(byte-동일).
    provider = _ScriptedProvider([_FENCED_VIOLATING_BUY])
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_strategy(
            provider, "buy", "PG_OFF", os.path.join(tmp, "s.db"),
            timeframe="min", retry_max=1,
        )
    assert result["status"] == "ok", result
    assert result["attempts"] == 1
    assert "최고현재가" in result["code"]


def test_generator_gate_on_rejects_then_saves_compliant_code():
    # 토글 ON — 1차 응답(CSC-06 위반) 거부→prior_error 재시도, 2차(준수) 저장.
    provider = _ScriptedProvider([_FENCED_VIOLATING_BUY, _FENCED_COMPLIANT_BUY])
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_strategy(
            provider, "buy", "PG_ON", os.path.join(tmp, "s.db"),
            timeframe="min", retry_max=2,
            principle_gate_enabled=True,
        )
    assert result["status"] == "ok", result
    assert result["attempts"] == 2
    assert "분당거래대금" in result["code"]
    # 두 번째 프롬프트에 reject 사유(rule id)가 prior_error 로 전달됐어야 한다.
    second_user = provider.calls[1][-1]["content"]
    assert "CSC-06" in second_user
    assert "원리 일관성 위반" in second_user


def test_generator_gate_on_exhausts_retries_on_persistent_violation():
    provider = _ScriptedProvider([_FENCED_VIOLATING_BUY, _FENCED_VIOLATING_BUY])
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_strategy(
            provider, "buy", "PG_FAIL", os.path.join(tmp, "s.db"),
            timeframe="min", retry_max=2,
            principle_gate_enabled=True,
        )
    assert result["status"] == "error"
    assert result["attempts"] == 2
    assert "CSC-06" in result["reason"]


def test_generator_gate_on_advisory_only_does_not_block_save():
    # metadata 미제공 → PG-META-01 advisory 만 발생. advisory 는 저장을 막지 않는다.
    provider = _ScriptedProvider([_FENCED_COMPLIANT_BUY])
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_strategy(
            provider, "buy", "PG_ADV", os.path.join(tmp, "s.db"),
            timeframe="min", retry_max=1,
            principle_gate_enabled=True,
        )
    assert result["status"] == "ok", result
    assert result["attempts"] == 1


def test_generator_gate_metadata_passthrough_tick_window():
    # tick timeframe 이 metadata 로 자동 보충돼 CSC-10 이 판정된다(시간창 없음 → reject).
    fenced_tick_no_window = "```python\n" + _TICK_BUY_NO_WINDOW + "if 매수:\n    self.Buy()\n```"
    fenced_tick_ok = "```python\n" + _TICK_BUY_IN_WINDOW + "if 매수:\n    self.Buy()\n```"
    provider = _ScriptedProvider([fenced_tick_no_window, fenced_tick_ok])
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_strategy(
            provider, "buy", "PG_TICK", os.path.join(tmp, "s.db"),
            timeframe="tick", retry_max=2,
            principle_gate_enabled=True,
            principle_gate_metadata={"principle_ids": ["P14"]},
        )
    assert result["status"] == "ok", result
    assert result["attempts"] == 2
    assert "CSC-10" in provider.calls[1][-1]["content"]


# ===================================================================
# config 토글 — 기본 OFF + 왕복 유지
# ===================================================================

def test_config_toggle_default_off_and_roundtrip():
    cfg = LoopConfig()
    assert cfg.principle_gate_enabled is False

    restored = LoopConfig.from_dict(cfg.to_dict())
    assert restored.principle_gate_enabled is False

    enabled = LoopConfig.from_dict({"principle_gate_enabled": True})
    assert enabled.principle_gate_enabled is True
    assert enabled.to_dict()["principle_gate_enabled"] is True
