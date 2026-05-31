"""생성 품질 (A) — 필터 범주 게이트 단위 테스트 (네트워크/실LLM 없음).

검증 대상:
  1) count_filter_categories / categories_present 순수 함수:
     - 과발화 코드(매수=True) → 0, 단일 느슨 조건 → 1.
     - 다범주 결합 → 정확한 범주 집합.
     - 주석 토큰·대입(비교 없음)은 카운트 제외(비교 문맥 필수).
     - 실제 시드 매수 코드 → >= 8 범주(시드 게이팅 구조 실측).
  2) build_messages(require_filter_gates 토글):
     - ON: kind=='buy' 매수 프롬프트에 "필터 게이팅" 가이드 존재.
     - OFF/ON 모두 kind=='sell' 매수 가이드 부재(매도 무영향).
     - OFF시 buy/sell 모두 명시 OFF와 byte-동일(하위호환).
  3) generate_strategy(require_filter_gates 토글):
     - OFF(기본): 범주 부족 매수코드도 저장(기존 동작 회귀 보존).
     - ON: 범주 부족 매수코드는 reject→재시도, 충분하면 통과 저장.
     - ON: kind=='sell'은 필터 게이트 미적용(무영향).
  4) LoopConfig: 기본 OFF + from_dict 안전 파싱.

OFF=기존동작 보존이 핵심 — 모든 신규 동작은 토글 뒤에만 있다.
fake provider 패턴은 test_liquidity_gate.py 와 동일 스타일.
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
from ai_strategy_loop.brain.filter_gate import categories_present, count_filter_categories  # noqa: E402
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402

# 실제 시드 매수 코드를 담은 루프 DB(읽기 전용).
_SEED_DB = os.path.join(PROJECT_ROOT, "ai_strategy_loop", "state", "loop_strategies.db")
_SEED_BUY_INDEX = "Tick_B_902_905_Update_2"

# "필터 게이팅" 가이드 마커(ON 매수에서만 존재해야 한다).
_FILTER_GUIDE_MARKER = "필터 게이팅"


# ============================================================
# 1) count_filter_categories / categories_present 순수 함수
# ============================================================

def test_always_true_no_categories():
    # 과발화의 전형: 항상참 → 어떤 필터 범주도 없음.
    assert count_filter_categories("매수 = True") == 0


def test_single_loose_condition_price_band():
    # 단일 느슨한 조건(현재가>0) → price_band 1개.
    code = "매수 = 현재가 > 0"
    assert count_filter_categories(code) == 1
    assert categories_present(code) == {"price_band"}


def test_multi_category_snippet():
    # 시총·등락율·당일거래대금·체결강도·시초 시간창을 AND로 결합 → >= 4.
    code = (
        "매수 = True\n"
        "if not (시가총액 < 3000):\n"
        "    매수 = False\n"
        "elif not (2.0 <= 등락율 < 4.0):\n"
        "    매수 = False\n"
        "elif not (당일거래대금 > 500):\n"
        "    매수 = False\n"
        "elif not (체결강도 >= 50 and 체결강도 <= 300):\n"
        "    매수 = False\n"
        "elif not (시분초 < 90500):\n"
        "    매수 = False\n"
    )
    cats = categories_present(code)
    assert cats == {"market_cap", "change_band", "liquidity", "exec_strength", "time_window"}
    assert count_filter_categories(code) >= 4


def test_comment_only_token_ignored():
    # 토큰이 주석에만 등장 → 카운트 제외.
    code = "# 당일거래대금 > 100 조건을 넣고 싶지만 일단\n매수 = True"
    assert count_filter_categories(code) == 0


def test_assignment_without_comparison_not_counted():
    # 비교 없는 단순 대입 라인 단독은 범주를 추가하지 않는다(비교 문맥 필수).
    assign_only = "초당순매수금액 = (초당매수수량 - 초당매도수량) * 현재가"
    assert count_filter_categories(assign_only) == 0
    # 그러나 같은 변수를 비교하는 라인이 있으면 그 라인에서 카운트된다.
    with_compare = assign_only + "\n매수 = 초당매수수량 > 매도총잔량 * 0.2"
    assert "orderbook" in categories_present(with_compare)


def test_eq_operator_not_counted():
    # `==`/`!=`(부등호 아님)는 게이트 비교로 보지 않는다(_COMPARISON_RE=[<>]).
    assert count_filter_categories("매수 = (관심종목 == 1)") == 0


def test_empty_code():
    assert count_filter_categories("") == 0
    assert categories_present("") == set()


def test_real_seed_buy_has_many_categories():
    # 실측: 실제 인간 시드 매수 코드는 시드 게이팅 구조상 >= 8 범주를 충족한다.
    assert os.path.exists(_SEED_DB), f"seed DB 없음: {_SEED_DB}"
    con = sqlite3.connect(_SEED_DB)
    try:
        cur = con.cursor()
        cur.execute('SELECT "전략코드" FROM stockbuy WHERE "index" = ?', (_SEED_BUY_INDEX,))
        row = cur.fetchone()
    finally:
        con.close()
    assert row is not None, f"시드 매수 전략 없음: {_SEED_BUY_INDEX}"
    seed_code = row[0]
    ncat = count_filter_categories(seed_code)
    assert ncat >= 8, f"시드 범주 수 {ncat} (기대 >= 8); cats={sorted(categories_present(seed_code))}"


# ============================================================
# 2) build_messages 프롬프트 토글
# ============================================================

def _user_text(messages):
    """messages에서 user 메시지 본문을 꺼낸다."""
    return next(m["content"] for m in messages if m["role"] == "user")


def test_prompt_on_buy_has_filter_guide():
    user = _user_text(build_messages("buy", timeframe="min", require_filter_gates=True))
    assert _FILTER_GUIDE_MARKER in user


def test_prompt_off_buy_no_filter_guide():
    user = _user_text(build_messages("buy", timeframe="min", require_filter_gates=False))
    assert _FILTER_GUIDE_MARKER not in user


def test_prompt_on_sell_unaffected():
    # 매도 경로엔 매수 게이팅 가이드가 추가되지 않는다(ON이어도).
    user = _user_text(build_messages("sell", timeframe="min", require_filter_gates=True))
    assert _FILTER_GUIDE_MARKER not in user


def test_prompt_off_buy_byte_identical():
    # OFF시 매수 프롬프트는 명시 OFF와 byte-동일(기존 동작 보존).
    default_buy = _user_text(build_messages("buy", timeframe="min"))
    off_buy = _user_text(build_messages("buy", timeframe="min", require_filter_gates=False))
    assert default_buy == off_buy


def test_prompt_off_sell_byte_identical():
    default_sell = _user_text(build_messages("sell", timeframe="min"))
    off_sell = _user_text(build_messages("sell", timeframe="min", require_filter_gates=False))
    assert default_sell == off_sell


def test_prompt_on_sell_byte_identical_to_off():
    # ON이어도 매도 경로는 OFF와 byte-동일(토글이 매수에만 작용).
    off_sell = _user_text(build_messages("sell", timeframe="min"))
    on_sell = _user_text(build_messages("sell", timeframe="min", require_filter_gates=True))
    assert off_sell == on_sell


# ============================================================
# 3) generate_strategy 토글 동작 (fake provider)
# ============================================================

# 범주가 충분한 매수(시총·등락율·당일거래대금·체결강도 → 4범주).
_BUY_WELL_GATED = (
    "```python\n"
    "매수 = True\n"
    "if not (시가총액 < 3000):\n"
    "    매수 = False\n"
    "elif not (2.0 <= 등락율 < 8.0):\n"
    "    매수 = False\n"
    "elif not (당일거래대금 > 500):\n"
    "    매수 = False\n"
    "elif not (체결강도 >= 50 and 체결강도 <= 300):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 범주가 부족한 매수(등락율 1개뿐 → 1범주).
_BUY_UNDER_GATED = (
    "```python\n"
    "매수 = 등락율 > 3\n"
    "if 매수:\n"
    "    self.Buy()\n"
    "```"
)
# 매도(필터 범주 무관).
_SELL_ANY = (
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


def test_gen_off_saves_under_gated_buy():
    # OFF(기본): 범주 부족 매수코드도 그대로 저장(기존 동작 회귀 보존).
    provider = _ScriptedProvider([_BUY_UNDER_GATED])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "OFF_buy", db_path, retry_max=2,
            require_filter_gates=False,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        assert len(provider.calls) == 1
        saved = _saved_code(db_path, "OFF_buy", "stockbuy")
        assert saved is not None and "self.Buy()" in saved


def test_gen_on_rejects_under_gated_then_succeeds():
    # ON: 범주 부족 매수코드는 reject→재시도, 충분한 코드는 통과 저장.
    provider = _ScriptedProvider([_BUY_UNDER_GATED, _BUY_WELL_GATED])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "ON_buy", db_path, retry_max=3,
            require_filter_gates=True, min_filter_categories=4,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 2
        # 재시도 프롬프트에 과발화/범주 지시가 prior_error로 들어가야 한다.
        second_user = provider.calls[1][-1]["content"]
        assert "과발화" in second_user or "필터 범주" in second_user
        saved = _saved_code(db_path, "ON_buy", "stockbuy")
        assert saved is not None and "시가총액" in saved


def test_gen_on_exhausts_when_always_under_gated():
    # ON: 매번 범주 부족 코드만 나오면 retry 소진 후 error(아무것도 저장 안 됨).
    provider = _ScriptedProvider([_BUY_UNDER_GATED, _BUY_UNDER_GATED])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "X", db_path, retry_max=2,
            require_filter_gates=True, min_filter_categories=4,
        )
        assert result["status"] == "error", result
        assert result["attempts"] == 2
        assert "재시도 소진" in result["reason"]
        assert _saved_code(db_path, "X", "stockbuy") is None


def test_gen_on_accepts_well_gated_first_try():
    provider = _ScriptedProvider([_BUY_WELL_GATED])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "OK_buy", db_path, retry_max=2,
            require_filter_gates=True, min_filter_categories=4,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1


def test_gen_on_does_not_apply_to_sell():
    # ON이어도 kind=='sell'은 필터 범주 게이트 미적용 → 매도 통과 저장.
    provider = _ScriptedProvider([_SELL_ANY])
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "sell", "SELL_x", db_path, retry_max=2,
            require_filter_gates=True, min_filter_categories=4,
        )
        assert result["status"] == "ok", result
        assert result["attempts"] == 1
        saved = _saved_code(db_path, "SELL_x", "stocksell")
        assert saved is not None and "self.Sell()" in saved


# ============================================================
# 4) LoopConfig 기본 OFF + from_dict 안전 파싱
# ============================================================

def test_config_default_off():
    cfg = LoopConfig()
    assert cfg.require_filter_gates is False
    assert cfg.min_filter_categories == 5


def test_config_from_dict_parses_toggle():
    cfg = LoopConfig.from_dict({"require_filter_gates": True, "min_filter_categories": 6})
    assert cfg.require_filter_gates is True
    assert cfg.min_filter_categories == 6


def test_config_from_dict_ignores_unknown():
    cfg = LoopConfig.from_dict({"unknown_key_xyz": 123})
    assert cfg.require_filter_gates is False
