"""타깃 처방 — freeze_buy(매수 동결·매도만 재생성) 단위 테스트 (네트워크 없음).

문제: best(시드)가 MDD만 부족할 때 LLM이 매수를 자유 재작성해 과발화 드리프트로
졸업 못 함. 처방: 매수를 동결(시드/best 코드 그대로 복제)하고 매도(청산)만 재생성해
거래수·빈도·수익을 보존한 채 MDD만 깎는다.

검증:
  (a) freeze_buy=True면 buy는 base_buy_code 복사본으로 저장되고 generate_strategy는
      sell에 대해서만 호출된다(buy LLM 호출 0).
  (b) freeze_buy=False(기본)면 기존대로 buy+sell 둘 다 generate_strategy로 생성된다.
  (c) MDD-only 감지 로직: 빈도ok + 수익>0 + mdd>cap → True;
      빈도부족 / 수익<=0 / mdd<=cap 중 하나라도면 False.
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402


# ============================================================
# helpers
# ============================================================

def _make_strategy_db(tmp_path):
    """루프 strategy DB(stockbuy, stocksell)를 만들어 경로를 반환한다."""
    db = str(tmp_path / "strategy.db")
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.commit()
    con.close()
    return db


def _read_code(db, table, name):
    con = sqlite3.connect(db)
    try:
        cur = con.execute(f'SELECT "전략코드" FROM {table} WHERE "index"=?', (name,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        con.close()


class _StubResult:
    """provider.chat 스텁 결과 — code 블록 + usage."""

    def __init__(self, code):
        self.text = f"```python\n{code}\n```"
        self.usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}


class _RecordingProvider:
    """chat 호출을 기록하는 스텁 provider. 항상 유효한 sell 코드를 돌려준다."""

    def __init__(self):
        self.calls = 0

    # 호출마다 구조적으로 다른 코드(DedupTracker는 숫자 리터럴을 정규화하므로
    #   숫자만 바꾸면 중복으로 걸린다 → 변수 인덱스/식 구조 자체를 바꾼다).
    _BODIES = (
        "if self.단순이평(5) > self.단순이평(20):\n    self.매수(self.가능수량())",
        "if self.보유중() and self.수익률() > 1.0:\n    self.매도(self.보유수량())",
        "if self.단순이평(3) < self.단순이평(10):\n    self.매도(self.보유수량())",
        "if self.현재가() > self.시가():\n    self.매수(self.가능수량())",
    )

    def chat(self, messages, model=None, **kw):  # noqa: ARG002
        body = self._BODIES[self.calls % len(self._BODIES)]
        self.calls += 1
        # 분봉 매수/매도에 안전한 단순 코드(컴파일/토큰/스코프 게이트 통과용).
        return _StubResult(body)


# ============================================================
# (a) freeze_buy=True → buy 복사, sell만 생성
# ============================================================

def test_freeze_buy_copies_base_and_only_generates_sell(monkeypatch, tmp_path):
    """freeze_buy=True면 buy=base 복사(LLM 0), generate_strategy는 sell만 호출."""
    db = _make_strategy_db(tmp_path)
    monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", db)

    base_buy = "if self.단순이평(5) > self.단순이평(20):\n    self.매수(self.가능수량())"
    provider = _RecordingProvider()

    config = LoopConfig(provider="openrouter", bt_timeframe="min")
    res = L._generate_pair(
        provider, config, run_id="frz", gen_no=3,
        autopsy_feedback=None,
        sell_feedback="기존 청산 피드백",
        base_buy_code=base_buy,
        base_sell_code=None,
        freeze_buy=True,
    )

    assert res["status"] == "ok", res
    # buy는 base_buy_code 복사본으로 저장됨.
    saved_buy = _read_code(db, "stockbuy", "AILOOP_frz_g3_buy")
    assert saved_buy == base_buy
    # generate_strategy(=provider.chat)는 sell에 대해 한 번만 호출됨(buy LLM 0).
    assert provider.calls == 1
    # sell도 저장됨.
    assert _read_code(db, "stocksell", "AILOOP_frz_g3_sell") is not None


def test_freeze_buy_falls_back_when_no_base(monkeypatch, tmp_path):
    """freeze_buy=True라도 base_buy_code가 None이면 안전 폴백(buy도 생성)."""
    db = _make_strategy_db(tmp_path)
    monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", db)

    provider = _RecordingProvider()
    config = LoopConfig(provider="openrouter", bt_timeframe="min")
    res = L._generate_pair(
        provider, config, run_id="frz", gen_no=4,
        autopsy_feedback=None,
        base_buy_code=None,
        freeze_buy=True,
    )
    assert res["status"] == "ok", res
    # base 없음 → 동결 미발동 → buy+sell 둘 다 generate_strategy 호출.
    assert provider.calls == 2


# ============================================================
# (b) freeze_buy=False(기본) → buy+sell 둘 다 생성
# ============================================================

def test_no_freeze_generates_both(monkeypatch, tmp_path):
    """freeze_buy=False(기본)면 기존대로 buy+sell 둘 다 generate_strategy로 생성."""
    db = _make_strategy_db(tmp_path)
    monkeypatch.setattr(L.bootstrap, "LOOP_DB_STRATEGY", db)

    base_buy = "if self.단순이평(5) > self.단순이평(20):\n    self.매수(self.가능수량())"
    provider = _RecordingProvider()
    config = LoopConfig(provider="openrouter", bt_timeframe="min")
    res = L._generate_pair(
        provider, config, run_id="nofrz", gen_no=2,
        autopsy_feedback=None,
        base_buy_code=base_buy,
        # freeze_buy 생략 → 기본 False.
    )
    assert res["status"] == "ok", res
    # 둘 다 LLM 생성 → provider.chat 2회.
    assert provider.calls == 2


# ============================================================
# (c) MDD-only 감지 로직
# ============================================================
# loop.py의 best 갱신 블록과 동일한 식을 검증한다(빈도ok + 수익>0 + mdd>cap → True).

def _is_mdd_only(fit, config):
    """loop.py best 갱신 블록의 MDD-only 식과 동일한 판정(테스트 미러)."""
    return (
        (not fit.gate_passed)
        and (float(getattr(fit, "daily_avg_trades", 0.0))
             >= float(getattr(config, "min_daily_trades", 0.0) or 0.0))
        and (float(fit.total_profit) > 0.0)
        and (abs(float(fit.mdd)) > float(getattr(config, "mdd_cap", float("inf"))))
    )


class _Fit:
    """FitnessResult 대용 더미(필요한 필드만)."""

    def __init__(self, gate_passed, daily_avg_trades, total_profit, mdd):
        self.gate_passed = gate_passed
        self.daily_avg_trades = daily_avg_trades
        self.total_profit = total_profit
        self.mdd = mdd


def test_mdd_only_true_when_freq_ok_profit_pos_mdd_over_cap():
    """빈도ok + 수익>0 + mdd>cap → MDD-only True (처방 발동 조건)."""
    config = LoopConfig(min_daily_trades=0.5, mdd_cap=35.0)
    fit = _Fit(gate_passed=False, daily_avg_trades=0.6, total_profit=1000.0, mdd=36.4)
    assert _is_mdd_only(fit, config) is True


def test_mdd_only_false_when_freq_short():
    """빈도 부족 → False (거래수가 적은 실패는 매수 동결 대상 아님)."""
    config = LoopConfig(min_daily_trades=0.5, mdd_cap=35.0)
    fit = _Fit(gate_passed=False, daily_avg_trades=0.1, total_profit=1000.0, mdd=36.4)
    assert _is_mdd_only(fit, config) is False


def test_mdd_only_false_when_profit_not_positive():
    """수익<=0 → False (적자 실패는 MDD만의 문제가 아님)."""
    config = LoopConfig(min_daily_trades=0.5, mdd_cap=35.0)
    fit = _Fit(gate_passed=False, daily_avg_trades=0.6, total_profit=0.0, mdd=36.4)
    assert _is_mdd_only(fit, config) is False


def test_mdd_only_false_when_mdd_within_cap():
    """mdd<=cap → False (MDD가 cap 이내면 처방 불필요)."""
    config = LoopConfig(min_daily_trades=0.5, mdd_cap=35.0)
    fit = _Fit(gate_passed=False, daily_avg_trades=0.6, total_profit=1000.0, mdd=30.0)
    assert _is_mdd_only(fit, config) is False
