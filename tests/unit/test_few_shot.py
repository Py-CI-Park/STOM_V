"""생성 few-shot 샘플 주입 (#67) 단위 테스트 (네트워크/실LLM 없음).

검증 대상:
  1) select_exemplars (합성 tmp DB):
     - passing: loop_runs.db gate_passed=1 → loop_strategies.db 코드 조회, K개 cap.
     - timeframe 매칭(tick 전략은 min 생성에서 제외 — NameError 가드).
     - 다양성(정규화 해시 중복 제거 — 동일 코드 반복 금지).
     - 길이 상한(_MAX_EXEMPLAR_CHARS 초과 제외).
     - 무예외(DB 없음/매칭 0개/잘못된 인자 → 빈 리스트).
  2) build_messages(few_shot_examples 슬롯):
     - None/[] → 명시 없음과 byte-동일(하위호환), buy/sell 모두.
     - 주어지면 헤더("검증된 우수 전략 예시"·"복제하지 말") + 각 샘플 코드펜스.
     - kind=='sell'에도 동일 슬롯 동작(매수 전용 아님).
  3) generate_strategy: few_shot_examples → build_messages 전달(프롬프트에 등장).
  4) LoopConfig: 기본 few_shot_enabled=False, k=3, source='passing'.

OFF=기존동작 보존이 핵심. fake provider 패턴은 test_filter_gate.py 와 동일 스타일.
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
from ai_strategy_loop.brain.exemplar_pool import _MAX_EXEMPLAR_CHARS, select_exemplars  # noqa: E402
from ai_strategy_loop.brain.generator import generate_strategy  # noqa: E402
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402

_FEWSHOT_HEADER = "검증된 우수 전략 예시"
_NO_COPY_MARKER = "복제하지 말"


# ============================================================
# 합성 DB 빌더 (loop_runs.db generations + loop_strategies.db stockbuy/stocksell)
# ============================================================

def _make_runs_db(path, rows):
    """rows: [(run_id, gen_no, buy_name, sell_name, gate_passed, created_at)]."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE generations (run_id TEXT, gen_no INTEGER, buy_name TEXT, "
        "sell_name TEXT, gate_passed INTEGER, created_at REAL)"
    )
    con.executemany(
        "INSERT INTO generations (run_id, gen_no, buy_name, sell_name, gate_passed, created_at) "
        "VALUES (?,?,?,?,?,?)", rows,
    )
    con.commit()
    con.close()


def _make_strategy_db(path, buys, sells):
    """buys/sells: {name: code}. 운영 스키마(index + 전략코드)와 동일."""
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE stockbuy ("index" TEXT, "전략코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("index" TEXT, "전략코드" TEXT)')
    con.executemany('INSERT INTO stockbuy VALUES (?,?)', list(buys.items()))
    con.executemany('INSERT INTO stocksell VALUES (?,?)', list(sells.items()))
    con.commit()
    con.close()


# tick 스코프에서 유효한 매수 코드(초당* 계열, 공통 변수). min에선 NameError 가드로 제외돼야.
#   주의: normalized_ast_hash는 상수 리터럴 차이를 무시한다(설계). 따라서 다양성 테스트는
#   임계값(숫자)이 아니라 **구조**(쓰는 변수/조건 수)가 다른 코드를 만들어야 한다.
_TICK_BUY_VARIANTS = [
    # variant 0: 시총·당일거래대금·초당거래대금 3조건.
    "매수 = True\n"
    "if not (시가총액 < 3000):\n"
    "    매수 = False\n"
    "elif not (당일거래대금 > 500):\n"
    "    매수 = False\n"
    "elif not (초당거래대금 > 100):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n",
    # variant 1: 등락율·체결강도 2조건(다른 변수).
    "매수 = True\n"
    "if not (2.0 <= 등락율 < 8.0):\n"
    "    매수 = False\n"
    "elif not (체결강도 >= 80):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n",
    # variant 2: 시분초·현재가·당일거래대금 3조건(또 다른 구조).
    "매수 = True\n"
    "if not (시분초 < 90500):\n"
    "    매수 = False\n"
    "elif not (현재가 > 1000):\n"
    "    매수 = False\n"
    "elif not (당일거래대금 > 800):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n",
    # variant 3: 초당매수수량·매도총잔량 호가압력(또 다른 구조).
    "매수 = True\n"
    "if not (초당매수수량 > 매도총잔량 * 0.2):\n"
    "    매수 = False\n"
    "if 매수:\n"
    "    self.Buy()\n",
    # variant 4: 시가총액만(단일 조건).
    "매수 = 시가총액 < 5000\n"
    "if 매수:\n"
    "    self.Buy()\n",
]

_TICK_SELL_VARIANTS = [
    "매도 = False\n"
    "if 수익률 <= -2.0:\n"
    "    매도 = True\n"
    "if 매도:\n"
    "    self.Sell()\n",
    "매도 = False\n"
    "if 최고수익률 - 수익률 >= 1.0:\n"
    "    매도 = True\n"
    "if 매도:\n"
    "    self.Sell()\n",
    "매도 = False\n"
    "if 보유시간 > 600:\n"
    "    매도 = True\n"
    "if 매도:\n"
    "    self.Sell()\n",
]


def _tick_buy(i):
    """구조적으로 서로 다른 매수 변형을 순환 반환(다양성 테스트용)."""
    return _TICK_BUY_VARIANTS[i % len(_TICK_BUY_VARIANTS)]


def _tick_sell(i):
    return _TICK_SELL_VARIANTS[i % len(_TICK_SELL_VARIANTS)]


# ============================================================
# 1) select_exemplars (합성 tmp DB)
# ============================================================

def test_select_passing_buy_basic_and_cap():
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        buys = {f"b{i}": _tick_buy(i) for i in range(5)}
        _make_strategy_db(strat, buys, {})
        _make_runs_db(runs, [
            (f"run{i}", i, f"b{i}", f"s{i}", 1, 100.0 + i) for i in range(5)
        ])
        ex = select_exemplars(kind="buy", timeframe="tick", k=3,
                              source="passing", db_path=strat, runs_db_path=runs)
        assert len(ex) == 3, ex  # K cap
        assert all("self.Buy()" in e for e in ex)


def test_select_only_gate_passed():
    # gate_passed=0 행은 제외된다.
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        _make_strategy_db(strat, {"good": _tick_buy(1), "bad": _tick_buy(2)}, {})
        _make_runs_db(runs, [
            ("r1", 0, "good", "sg", 1, 100.0),
            ("r2", 1, "bad", "sb", 0, 101.0),  # gate_passed=0 → 제외
        ])
        ex = select_exemplars(kind="buy", timeframe="tick", k=5,
                              source="passing", db_path=strat, runs_db_path=runs)
        assert len(ex) == 1, ex
        assert ex[0].strip() == _tick_buy(1).strip()  # gate_passed=1인 'good'만


def test_select_timeframe_guard_excludes_tick_in_min():
    # tick 전용 변수(초당거래대금)를 쓴 전략은 min 생성에서 제외(NameError 가드).
    #   variant 0이 초당거래대금/초당* 계열을 쓰는 tick-only 코드다.
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        _make_strategy_db(strat, {"b0": _tick_buy(0)}, {})
        _make_runs_db(runs, [("r", 0, "b0", "s", 1, 100.0)])
        ex_tick = select_exemplars(kind="buy", timeframe="tick", k=3,
                                  source="passing", db_path=strat, runs_db_path=runs)
        ex_min = select_exemplars(kind="buy", timeframe="min", k=3,
                                 source="passing", db_path=strat, runs_db_path=runs)
        assert len(ex_tick) == 1
        assert ex_min == []  # tick-only 변수라 min에선 스코프 위반 → 제외


def test_select_diversity_dedup():
    # 동일 코드가 여러 이름으로 등장해도 다양성 중복 제거로 1개만 남는다.
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        same = _tick_buy(7)
        _make_strategy_db(strat, {"a": same, "b": same, "c": _tick_buy(9)}, {})
        _make_runs_db(runs, [
            ("r", 0, "a", "sa", 1, 102.0),
            ("r", 1, "b", "sb", 1, 101.0),
            ("r", 2, "c", "sc", 1, 100.0),
        ])
        ex = select_exemplars(kind="buy", timeframe="tick", k=5,
                              source="passing", db_path=strat, runs_db_path=runs)
        assert len(ex) == 2, ex  # a==b 중복 제거, c 별개


def test_select_length_cap_excludes_long():
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        long_code = _tick_buy(1) + ("\n# pad" + "x" * (_MAX_EXEMPLAR_CHARS))
        _make_strategy_db(strat, {"short": _tick_buy(2), "long": long_code}, {})
        _make_runs_db(runs, [
            ("r", 0, "short", "ss", 1, 101.0),
            ("r", 1, "long", "sl", 1, 100.0),
        ])
        ex = select_exemplars(kind="buy", timeframe="tick", k=5,
                              source="passing", db_path=strat, runs_db_path=runs)
        assert len(ex) == 1, ex  # long_code는 길이 상한 초과로 제외
        assert len(ex[0]) <= _MAX_EXEMPLAR_CHARS


def test_select_sell_kind():
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        _make_strategy_db(strat, {}, {f"s{i}": _tick_sell(i + 1) for i in range(3)})
        _make_runs_db(runs, [(f"r{i}", i, f"b{i}", f"s{i}", 1, 100.0 + i) for i in range(3)])
        ex = select_exemplars(kind="sell", timeframe="tick", k=2,
                             source="passing", db_path=strat, runs_db_path=runs)
        assert len(ex) == 2
        assert all("self.Sell()" in e for e in ex)


def test_select_no_exceptions_on_missing_db():
    # DB 없음 → 빈 리스트(무예외).
    assert select_exemplars(kind="buy", timeframe="tick", k=3, source="passing",
                            db_path="/no/such.db", runs_db_path="/no/runs.db") == []


def test_select_invalid_args_return_empty():
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        _make_strategy_db(strat, {"b": _tick_buy(1)}, {})
        _make_runs_db(runs, [("r", 0, "b", "s", 1, 100.0)])
        kw = dict(db_path=strat, runs_db_path=runs)
        assert select_exemplars(kind="x", timeframe="tick", k=3, source="passing", **kw) == []
        assert select_exemplars(kind="buy", timeframe="x", k=3, source="passing", **kw) == []
        assert select_exemplars(kind="buy", timeframe="tick", k=3, source="x", **kw) == []
        assert select_exemplars(kind="buy", timeframe="tick", k=0, source="passing", **kw) == []
        assert select_exemplars(kind="buy", timeframe="tick", k=-1, source="passing", **kw) == []


def test_select_empty_when_no_passing():
    with tempfile.TemporaryDirectory() as tmp:
        runs = os.path.join(tmp, "runs.db")
        strat = os.path.join(tmp, "strat.db")
        _make_strategy_db(strat, {"b": _tick_buy(1)}, {})
        _make_runs_db(runs, [("r", 0, "b", "s", 0, 100.0)])  # gate_passed=0뿐
        assert select_exemplars(kind="buy", timeframe="tick", k=3, source="passing",
                               db_path=strat, runs_db_path=runs) == []


# ============================================================
# 2) build_messages(few_shot_examples 슬롯)
# ============================================================

def _user_text(messages):
    return next(m["content"] for m in messages if m["role"] == "user")


def test_prompt_none_byte_identical_buy():
    default = _user_text(build_messages("buy", timeframe="tick"))
    none_ = _user_text(build_messages("buy", timeframe="tick", few_shot_examples=None))
    empty = _user_text(build_messages("buy", timeframe="tick", few_shot_examples=[]))
    assert default == none_ == empty


def test_prompt_none_byte_identical_sell():
    default = _user_text(build_messages("sell", timeframe="tick"))
    none_ = _user_text(build_messages("sell", timeframe="tick", few_shot_examples=None))
    empty = _user_text(build_messages("sell", timeframe="tick", few_shot_examples=[]))
    assert default == none_ == empty


def test_prompt_injects_header_and_fences():
    ex = [_tick_buy(1), _tick_buy(2)]
    user = _user_text(build_messages("buy", timeframe="tick", few_shot_examples=ex))
    assert _FEWSHOT_HEADER in user
    assert _NO_COPY_MARKER in user  # §3.14 복제 금지 지시
    for e in ex:
        assert e in user
    # base_code 없는 매수 프롬프트엔 코드펜스가 few-shot 만큼만 추가된다(2개).
    assert user.count("```python") >= 2


def test_prompt_sell_slot_also_works():
    ex = [_tick_sell(2)]
    user = _user_text(build_messages("sell", timeframe="tick", few_shot_examples=ex))
    assert _FEWSHOT_HEADER in user
    assert _tick_sell(2) in user


# ============================================================
# 3) generate_strategy → build_messages 전달 (fake provider)
# ============================================================

class _FakeUsage:
    prompt_tokens = 10
    completion_tokens = 20
    total_tokens = 30


class _FakeResult:
    def __init__(self, text):
        self.text = text
        self.usage = _FakeUsage()


class _CapturingProvider:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def chat(self, messages, model=None, **kw):
        self.calls.append(messages)
        return _FakeResult(self._response)


_GOOD_BUY = (
    "```python\n"
    + _tick_buy(3)
    + "```"
)


def test_generate_passes_few_shot_to_prompt():
    provider = _CapturingProvider(_GOOD_BUY)
    ex = [_tick_buy(1)]
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "fs_buy", db_path, timeframe="tick", retry_max=1,
            few_shot_examples=ex,
        )
        assert result["status"] == "ok", result
        user = next(m["content"] for m in provider.calls[0] if m["role"] == "user")
        assert _FEWSHOT_HEADER in user
        assert _tick_buy(1) in user


def test_generate_without_few_shot_no_header():
    provider = _CapturingProvider(_GOOD_BUY)
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "s.db")
        result = generate_strategy(
            provider, "buy", "nofs_buy", db_path, timeframe="tick", retry_max=1,
        )
        assert result["status"] == "ok", result
        user = next(m["content"] for m in provider.calls[0] if m["role"] == "user")
        assert _FEWSHOT_HEADER not in user


# ============================================================
# 4) LoopConfig 기본 OFF + from_dict 안전 파싱
# ============================================================

def test_config_defaults():
    cfg = LoopConfig()
    assert cfg.few_shot_enabled is False
    assert cfg.few_shot_k == 3
    assert cfg.few_shot_source == "passing"


def test_config_from_dict_parses():
    cfg = LoopConfig.from_dict({
        "few_shot_enabled": True, "few_shot_k": 5, "few_shot_source": "seed_db",
    })
    assert cfg.few_shot_enabled is True
    assert cfg.few_shot_k == 5
    assert cfg.few_shot_source == "seed_db"


def test_config_from_dict_ignores_unknown():
    cfg = LoopConfig.from_dict({"few_shot_unknown_xyz": 1})
    assert cfg.few_shot_enabled is False
