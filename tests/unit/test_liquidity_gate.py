"""Track B 2차 — 거래대금 유동성 게이트 단위 테스트 (네트워크/실LLM 없음).

검증 대상:
  1) has_liquidity_gate 순수 함수: 당일거래대금 비교 조건 검출 positive/negative.
     R7 ground-truth 교정: 초당거래대금·분당거래대금(상대비율) 단독 → False 필수.
  2) generate_strategy(require_liquidity_gate 토글):
     - OFF(기본): 당일거래대금 없는 코드도 저장(기존 동작 회귀 보존).
     - ON: 당일거래대금 없는 매수코드는 reject→재시도, retry 소진 시 error.
     - ON: 당일거래대금 있는 매수코드는 통과 저장.
     - ON: kind=='sell'은 거래대금 게이트 미적용(무영향).

fake provider 패턴은 test_generator_guardrail.py 와 동일 스타일.
"""

import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# generator는 cli.* 를 지연 import 한다. bootstrap을 먼저 import해 env-before-import 계약 충족.
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.brain.liquidity_gate import has_liquidity_gate  # noqa: E402

# --- canned 전략 스니펫 (코드 블록 형태; extract_code가 추출) ---
# 거래대금 비교 게이트 포함 매수.
BUY_WITH_LIQUIDITY = (
    "```python\n"
    "매수 = True\n"
    "if 당일거래대금 > 500:\n"
    "    매수 = True\n"
    "else:\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 각도 가속 윈도우 형태(>= 비교).
BUY_WITH_LIQUIDITY_ANGLE = (
    "```python\n"
    "매수 = 당일거래대금각도(30) >= 5 and 등락율 > 3\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 거래대금이 전혀 없는 매수.
BUY_NO_LIQUIDITY = (
    "```python\n"
    "매수 = True\n"
    "if not (3 <= 등락율 <= 25):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 거래대금이 주석에만 등장.
BUY_LIQUIDITY_IN_COMMENT = (
    "```python\n"
    "# 당일거래대금 > 500 조건을 넣고 싶지만 일단 등락율만\n"
    "매수 = 등락율 > 3\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 매도 스니펫 (거래대금 없음).
SELL_NO_LIQUIDITY = (
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
        text = self._responses.pop(0)
        return _FakeResult(text)


# ============================================================
# 1) has_liquidity_gate 순수 함수
# ============================================================

def test_has_liquidity_gate_positive_simple_threshold():
    assert has_liquidity_gate("if 당일거래대금 > 500:\n    매수 = True") is True


def test_has_liquidity_gate_positive_angle_window():
    code = "매수 = 당일거래대금각도(30) >= 5 and 등락율 > 3"
    assert has_liquidity_gate(code) is True


def test_has_liquidity_gate_positive_various_tokens():
    # "당일거래대금" 부분일치로 절대 일누적 유동성 바닥/각도 계열 검출.
    assert has_liquidity_gate("elif not (당일거래대금 > 5 * 100): pass") is True
    assert has_liquidity_gate("elif not (당일거래대금각도(30) > 5 and 당일거래대금각도(30) < 30): pass") is True


def test_has_liquidity_gate_negative_no_token():
    # 거래대금 변수가 전혀 없음.
    assert has_liquidity_gate("if 등락율 > 3:\n    매수 = True") is False


def test_has_liquidity_gate_negative_relative_ratio_only():
    # R7 핵심 회귀: 손실 세대(g2/g3) 패턴 — 초당거래대금 상대비율만 있고
    # 당일거래대금(절대 유동성 바닥)은 없음 → False 필수.
    code = "매수 = 초당거래대금 / 초당거래대금평균(30) > 3.0 and 등락율 > 2"
    assert has_liquidity_gate(code) is False


def test_has_liquidity_gate_negative_intraday_only():
    # 초당거래대금 단독 비교(당일 없음) → False.
    assert has_liquidity_gate("if 초당거래대금 > 100: pass") is False
    # 분당거래대금 단독 비교(당일 없음) → False.
    assert has_liquidity_gate("if 분당거래대금 >= 1000: pass") is False


def test_has_liquidity_gate_negative_comment_only():
    # 당일거래대금이 주석에만 등장 → 비교 문맥 아님.
    code = "# 당일거래대금 > 500 넣고 싶음\n매수 = 등락율 > 3"
    assert has_liquidity_gate(code) is False


def test_has_liquidity_gate_negative_assignment_only():
    # 단순 대입(비교 없음).
    assert has_liquidity_gate("x = 당일거래대금") is False


def test_has_liquidity_gate_empty():
    assert has_liquidity_gate("") is False
    assert has_liquidity_gate(None) is False  # type: ignore[arg-type]


# ============================================================
# 2) generate_strategy 토글 동작
# ============================================================

def _saved_code(db_path, name, table):
    # 저장이 전혀 일어나지 않으면 DB/테이블이 없을 수 있다 → "저장 없음"으로 본다.
    if not os.path.exists(db_path):
        return None
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        try:
            cur.execute(f'SELECT "전략코드" FROM {table} WHERE "index" = ?', (name,))
        except sqlite3.OperationalError:
            return None  # 테이블 미생성 = 저장 없음.
        row = cur.fetchone()
    finally:
        con.close()
    return row[0] if row else None


def test_off_saves_buy_without_liquidity():
    # OFF(기본): 거래대금 없는 매수코드도 그대로 저장(기존 동작 회귀 보존).
    provider = _ScriptedProvider([BUY_NO_LIQUIDITY])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "OFF_buy", db_path, retry_max=2,
            require_liquidity_gate=False,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        assert len(provider.calls) == 1
        saved = _saved_code(db_path, "OFF_buy", "stockbuy")
        assert saved is not None and "self.Buy()" in saved


def test_on_rejects_buy_without_liquidity_then_succeeds():
    # ON: 거래대금 없는 매수코드는 reject→재시도, 다음에 거래대금 있는 코드는 통과 저장.
    provider = _ScriptedProvider([BUY_NO_LIQUIDITY, BUY_WITH_LIQUIDITY])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "ON_buy", db_path, retry_max=3,
            require_liquidity_gate=True,
        )
        assert result["status"] == "ok", result
        # 첫 시도 거부 후 두 번째에서 저장.
        assert result["attempts"] == 2
        assert "당일거래대금" in result["code"]
        # 재시도 프롬프트에 게이트 누락 지시가 prior_error로 들어가야 한다.
        second_user = provider.calls[1][-1]["content"]
        assert "거래대금" in second_user
        saved = _saved_code(db_path, "ON_buy", "stockbuy")
        assert saved is not None and "당일거래대금" in saved


def test_on_exhausts_retries_when_liquidity_always_missing():
    # ON: 매번 거래대금 없는 코드만 나오면 retry 소진 후 error.
    provider = _ScriptedProvider([BUY_NO_LIQUIDITY, BUY_LIQUIDITY_IN_COMMENT])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "X", db_path, retry_max=2,
            require_liquidity_gate=True,
        )
        assert result["status"] == "error", result
        assert result["attempts"] == 2
        assert "재시도 소진" in result["reason"]
        # 아무것도 저장되면 안 됨.
        assert _saved_code(db_path, "X", "stockbuy") is None


def test_on_accepts_buy_with_liquidity_first_try():
    # ON: 거래대금 게이트 포함 코드는 첫 시도에 통과 저장.
    provider = _ScriptedProvider([BUY_WITH_LIQUIDITY_ANGLE])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "OK_buy", db_path, retry_max=2,
            require_liquidity_gate=True,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        assert "당일거래대금각도" in result["code"]


def test_on_does_not_apply_to_sell():
    # ON이어도 kind=='sell'은 거래대금 게이트 미적용 → 거래대금 없는 매도 통과 저장.
    provider = _ScriptedProvider([SELL_NO_LIQUIDITY])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "sell", "SELL_x", db_path, retry_max=2,
            require_liquidity_gate=True,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        assert len(provider.calls) == 1
        saved = _saved_code(db_path, "SELL_x", "stocksell")
        assert saved is not None and "self.Sell()" in saved
