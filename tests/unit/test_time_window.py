"""T3 (넓은 생성 강화) — 시간창 값 범위(시분초 lo/hi) 측정 단위 테스트.

검증 대상(네트워크/실LLM 없음):
  1) time_window_bounds 순수 함수: 체인/단일/없음, 토큰 경계, 주석 제외, 교집합.
  2) time_window_span_sec: HHMMSS→초 환산, 반열림 세션 보정, 음수 클램프.
  3) is_noop_time_window: 전범위(=시간 무게이트) 탐지 vs **좁은 902 보호** vs 중간 창.
  4) generate_strategy(require_meaningful_time_window 토글):
     - OFF(기본): no-op 매수코드도 저장(기존 동작 회귀 보존, byte-동일).
     - ON: no-op 매수코드는 reject→재시도, 의미 있는 창은 통과 저장.
     - ON: **좁은 창(902)은 reject 안 함**(과도강제 금지 — 좁은-good 보호).
     - ON: kind=='sell'은 미적용(무영향).
  5) LoopConfig: 기본 OFF + from_dict 안전 파싱.

핵심 불변식: OFF=기존동작 보존, 좁은 창은 절대 reject 안 함(no-op만 reject).
fake provider 패턴은 test_filter_gate.py / test_liquidity_gate.py 와 동일 스타일.
"""

import os
import sqlite3
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# generator는 cli.* 를 지연 import 한다. bootstrap을 먼저 import해 env-before-import 계약 충족.
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.filter_gate import (  # noqa: E402
    is_noop_time_window,
    time_window_bounds,
    time_window_span_sec,
)
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from tests.seed_db_guard import open_seed_database  # noqa: E402

# 실제 시드 매수 코드(좁은 902 창 — 다년강건 골드)를 담은 루프 DB(읽기 전용).
_SEED_DB = os.path.join(PROJECT_ROOT, "ai_strategy_loop", "state", "loop_strategies.db")
_SEED_BUY_INDEX = "Tick_B_902_905_Update_2"


# ============================================================
# 1) time_window_bounds 순수 함수 (시분초 lo/hi 추출)
# ============================================================

def test_bounds_chain_comparison():
    # 체인비교 `lo <= 시분초 < hi` → (lo, hi). 시드 902-905 좁은 창.
    assert time_window_bounds("매수 = (90200 <= 시분초 < 90500)") == (90200, 90500)


def test_bounds_single_upper_only():
    # 단일 상한 `시분초 < B` → (None, B). 하한 미지정.
    assert time_window_bounds("if 시분초 < 90200: pass") == (None, 90200)


def test_bounds_single_lower_only():
    # 단일 하한 `시분초 > A` → (A, None). 상한 미지정.
    assert time_window_bounds("if 시분초 > 90000: pass") == (90000, None)


def test_bounds_reversed_operand_order():
    # 우변 형태도 동일하게 합성: `A < 시분초`(하한), `B > 시분초`(상한).
    assert time_window_bounds("if 90000 < 시분초: pass") == (90000, None)
    assert time_window_bounds("if 93000 > 시분초: pass") == (None, 93000)


def test_bounds_union_envelope():
    # 여러 하한/상한 → 합집합 envelope(lo=하한 min=가장 이른, hi=상한 max=가장 늦은).
    #   다분기(OR) tick 전략의 실제 거래 시간범위 측정용 — 교집합은 분기경계서 반전.
    code = "매수 = (시분초 > 90000) and (시분초 > 91000) and (시분초 < 95000) and (시분초 < 93000)"
    assert time_window_bounds(code) == (90000, 95000)

    # 시드 902/905 다분기(902: 시분초<90200, 905: 90200<=시분초<90500) → 합집합 09:00~09:05.
    multibranch = "if 시분초 < 90200:\n    pass\nelif 90200 <= 시분초 < 90500:\n    pass"
    assert time_window_bounds(multibranch) == (90200, 90500)


def test_bounds_none_when_no_time_gate():
    # 시분초 비교가 전혀 없으면 None.
    assert time_window_bounds("매수 = 등락율 > 3 and 시가총액 < 3000") is None


def test_bounds_comment_excluded():
    # 주석에만 등장하는 시분초는 게이트로 보지 않는다.
    assert time_window_bounds("# 시분초 < 90500 넣고 싶음\n매수 = True") is None


def test_bounds_token_boundary_no_false_match():
    # `시분초` 뒤에 한글/영숫자/_가 붙은 다른 식별자는 매칭하지 않는다(부분일치 방지).
    assert time_window_bounds("if 시분초간격 < 100: pass") is None


def test_bounds_empty_code():
    assert time_window_bounds("") is None
    assert time_window_bounds(None) is None  # type: ignore[arg-type]


# ============================================================
# 2) time_window_span_sec (HHMMSS → 초 환산)
# ============================================================

def test_span_narrow_902_window_is_180s():
    # 09:02:00 ~ 09:05:00 = 3분 = 180초. 좁은 골드 창의 폭.
    assert time_window_span_sec("매수 = (90200 <= 시분초 < 90500)") == 180


def test_span_mid_window_is_1800s():
    # 09:00:00 ~ 09:30:00 = 30분 = 1800초.
    assert time_window_span_sec("if 90000 <= 시분초 < 93000: pass") == 1800


def test_span_half_open_uses_session_bounds():
    # 반열림(상한만) → 빠진 하한을 session_lo(09:00)로 보정해 폭을 잰다.
    #   [09:00:00, 09:30:00) = 1800초.
    assert time_window_span_sec("if 시분초 < 93000: pass") == 1800
    # 반열림(하한만) → 빠진 상한을 session_hi(15:30)로 보정.
    #   [09:00:00, 15:30:00) = 6.5h = 23400초.
    assert time_window_span_sec("if 시분초 > 90000: pass") == 23400


def test_span_none_when_no_time_gate():
    assert time_window_span_sec("매수 = 등락율 > 3") is None


def test_span_negative_clamped_to_zero():
    # 역전 경계(lo > hi)는 음수 폭을 0으로 클램프(graceful).
    assert time_window_span_sec("매수 = (93000 <= 시분초 < 90000)") == 0


def test_span_custom_session_bounds():
    # 세션 경계 커스텀: tick 윈도우(09:00~09:28) 보정 확인.
    #   상한만 09:28(92800)이고 하한 미지정 → session_lo=90000 보정.
    span = time_window_span_sec("if 시분초 < 92800: pass", session_lo=90000, session_hi=92800)
    assert span == 28 * 60  # 28분 = 1680초


# ============================================================
# 3) is_noop_time_window (전범위 = 사실상 시간 무게이트 탐지)
# ============================================================

def test_noop_no_time_gate_is_noop():
    # 시간 게이트 자체가 없으면 전범위와 동치 → no-op.
    assert is_noop_time_window("매수 = 등락율 > 3") is True


def test_noop_full_session_range_is_noop():
    # 명시적으로 세션 전범위(09:00~15:30)를 덮으면 no-op.
    assert is_noop_time_window("if 90000 <= 시분초 < 153000: pass") is True


def test_noop_single_upper_session_end_is_noop():
    # `시분초 < 153000`만 = 하한 09:00부터 종료까지 = 사실상 무게이트.
    assert is_noop_time_window("if 시분초 < 153000: pass") is True


def test_noop_narrow_902_window_is_NOT_noop():
    # ⚠️ 과도강제 금지의 핵심: 좁은 902 창(09:02~09:05)은 절대 no-op이 아니다.
    assert is_noop_time_window("매수 = (90200 <= 시분초 < 90500)") is False


def test_noop_mid_window_is_NOT_noop():
    # 중간 창(09:00~09:30)도 세션을 좁히므로 no-op 아님.
    assert is_noop_time_window("if 90000 <= 시분초 < 93000: pass") is False


def test_noop_real_seed_buy_is_NOT_noop():
    # 실측: 실제 인간 시드(좁은 902/905 창)는 no-op이 아니다(좁은-good 보호).
    with open_seed_database(_SEED_DB, required_tables=("stockbuy",)) as con:
        row = con.execute(
            'SELECT "전략코드" FROM stockbuy WHERE "index" = ?',
            (_SEED_BUY_INDEX,),
        ).fetchone()
    assert row is not None, f"시드 매수 전략 없음: {_SEED_BUY_INDEX}"
    seed_code = row[0]
    assert is_noop_time_window(seed_code) is False, (
        f"좁은 시드 창이 no-op으로 오판됨; bounds={time_window_bounds(seed_code)}"
    )


def test_noop_empty_code_is_noop():
    assert is_noop_time_window("") is True


# ============================================================
# 4) generate_strategy 토글 동작 (fake provider)
# ============================================================

# no-op 매수: 시간 게이트가 전범위(시분초 < 153000) — 사실상 무게이트.
_BUY_NOOP_TIME = (
    "```python\n"
    "매수 = True\n"
    "if not (시분초 < 153000):\n"
    "    매수 = False\n"
    "if not (등락율 > 3):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# no-op 매수(시간 게이트 아예 없음).
_BUY_NO_TIME = (
    "```python\n"
    "매수 = 등락율 > 3\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 의미 있는 중간 창(09:00~09:30) 매수.
_BUY_MID_WINDOW = (
    "```python\n"
    "매수 = True\n"
    "if not (90000 <= 시분초 < 93000):\n"
    "    매수 = False\n"
    "elif not (등락율 > 3):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# **좁은 902 창**(09:02~09:05) 매수 — 다년강건 골드. reject되면 안 됨.
_BUY_NARROW_902 = (
    "```python\n"
    "매수 = True\n"
    "if not (90200 <= 시분초 < 90500):\n"
    "    매수 = False\n"
    "elif not (등락율 > 3):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 매도(시간창 무관).
_SELL_NOOP = (
    "```python\n"
    "매도 = False\n"
    "if 수익률 >= 3:\n"
    "    매도 = True\n"
    "if 매도:\n"
    "    self.Sell()\n"
    "```"
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


def _saved_code(db_path, name, table):
    if not os.path.exists(db_path):
        return None
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        try:
            cur.execute(f'SELECT "전략코드" FROM {table} WHERE "index" = ?', (name,))
        except sqlite3.OperationalError:
            return None
        row = cur.fetchone()
    finally:
        con.close()
    return row[0] if row else None


def test_gen_off_saves_noop_time_buy():
    # OFF(기본): no-op 시간창 매수코드도 그대로 저장(기존 동작 회귀 보존).
    provider = _ScriptedProvider([_BUY_NOOP_TIME])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "OFF_buy", db_path, retry_max=2,
            require_meaningful_time_window=False,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        assert len(provider.calls) == 1
        saved = _saved_code(db_path, "OFF_buy", "stockbuy")
        assert saved is not None and "self.Buy()" in saved


def test_gen_on_rejects_noop_then_succeeds():
    # ON: no-op 매수코드는 reject→재시도, 의미 있는 창은 통과 저장.
    provider = _ScriptedProvider([_BUY_NOOP_TIME, _BUY_MID_WINDOW])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "ON_buy", db_path, retry_max=3,
            require_meaningful_time_window=True,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 2
        # 재시도 프롬프트에 시간창 지시가 prior_error로 들어가야 한다.
        second_user = provider.calls[1][-1]["content"]
        assert "시간창" in second_user or "시분초" in second_user
        saved = _saved_code(db_path, "ON_buy", "stockbuy")
        assert saved is not None and "시분초" in saved


def test_gen_on_rejects_no_time_gate():
    # ON: 시간 게이트가 아예 없는 매수코드도 no-op으로 reject.
    provider = _ScriptedProvider([_BUY_NO_TIME, _BUY_MID_WINDOW])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "ON_buy2", db_path, retry_max=3,
            require_meaningful_time_window=True,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 2


def test_gen_on_does_NOT_reject_narrow_902_window():
    # ⚠️ 과도강제 금지의 핵심 회귀: ON이어도 좁은 902 창은 절대 reject 안 함.
    #   좁은-good 전략을 잃지 않는다(첫 시도에 통과 저장).
    provider = _ScriptedProvider([_BUY_NARROW_902])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "narrow_buy", db_path, retry_max=2,
            require_meaningful_time_window=True,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1, "좁은 창이 reject됨 (과도강제 위반)"
        saved = _saved_code(db_path, "narrow_buy", "stockbuy")
        assert saved is not None and "90200" in saved


def test_gen_on_exhausts_when_always_noop():
    # ON: 매번 no-op 코드만 나오면 retry 소진 후 error(아무것도 저장 안 됨).
    provider = _ScriptedProvider([_BUY_NOOP_TIME, _BUY_NO_TIME])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "X", db_path, retry_max=2,
            require_meaningful_time_window=True,
        )
        assert result["status"] == "error", result
        assert result["attempts"] == 2
        assert "재시도 소진" in result["reason"]
        assert _saved_code(db_path, "X", "stockbuy") is None


def test_gen_on_does_not_apply_to_sell():
    # ON이어도 kind=='sell'은 시간창 게이트 미적용 → 매도 통과 저장(무영향).
    provider = _ScriptedProvider([_SELL_NOOP])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "sell", "SELL_x", db_path, retry_max=2,
            require_meaningful_time_window=True,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        saved = _saved_code(db_path, "SELL_x", "stocksell")
        assert saved is not None and "self.Sell()" in saved


def test_gen_off_byte_identical_default_vs_explicit():
    # OFF 기본 ≡ 명시 OFF: no-op 코드를 둘 다 1회 시도에 저장(동작 동일).
    # (a) 토글 미전달(기본).
    provider_default = _ScriptedProvider([_BUY_NOOP_TIME])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider_default, "buy", "B", db_path, retry_max=2,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        assert len(provider_default.calls) == 1
    # (b) 명시 OFF.
    provider_off = _ScriptedProvider([_BUY_NOOP_TIME])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider_off, "buy", "B", db_path, retry_max=2,
            require_meaningful_time_window=False,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        assert len(provider_off.calls) == 1


# ============================================================
# 4b) 측정·가시화: injected_features에 시간창 값 범위 기록 (on_prompt 콜백)
# ============================================================

def test_on_prompt_records_time_window_measurement_narrow():
    # 좁은 902 창 생성 → injected_features에 bounds/span/noop이 측정·기록된다.
    provider = _ScriptedProvider([_BUY_NARROW_902])
    records = []
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "M", db_path, retry_max=1,
            on_prompt=records.append,
        )
    assert result["status"] == "ok", result
    assert len(records) == 1
    feats = records[0]["injected_features"]
    # bounds는 JSON 직렬화 가능한 리스트로 기록된다(09:02~09:05).
    assert feats["time_window_bounds"] == [90200, 90500]
    assert feats["time_window_span_sec"] == 180
    assert feats["time_window_noop"] is False  # 좁은 창은 no-op 아님.


def test_on_prompt_records_time_window_measurement_noop():
    # 시간 게이트 없는 생성 → bounds None, noop True로 측정·기록(가시화).
    provider = _ScriptedProvider([_BUY_NO_TIME])
    records = []
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "M2", db_path, retry_max=1,
            on_prompt=records.append,
        )
    assert result["status"] == "ok", result
    feats = records[0]["injected_features"]
    assert feats["time_window_bounds"] is None
    assert feats["time_window_span_sec"] is None
    assert feats["time_window_noop"] is True


# ============================================================
# 5) LoopConfig 기본 OFF + from_dict 안전 파싱
# ============================================================

def test_config_default_off():
    cfg = LoopConfig()
    assert cfg.require_meaningful_time_window is False


def test_config_from_dict_parses_toggle():
    cfg = LoopConfig.from_dict({"require_meaningful_time_window": True})
    assert cfg.require_meaningful_time_window is True


def test_config_from_dict_ignores_unknown():
    cfg = LoopConfig.from_dict({"unknown_key_xyz": 123})
    assert cfg.require_meaningful_time_window is False
