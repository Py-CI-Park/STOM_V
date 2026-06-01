"""P2b-1 — 가정 환류 프롬프트 슬롯 단위 테스트 (백테/루프 실행 없음).

P2a는 가정을 방출·판정·영속까지 하지만, 판정 결과가 다음 세대 생성 프롬프트로
환류되지 않는다. P2b-1은 직전 세대의 판정된 가정(특히 **기각**)을 side별 환류
문자열로 만들어 프롬프트에 주입해 "이 방향은 틀렸으니 다른 레버를 시도하라"고 알린다.

검증:
  - format_hypothesis_feedback: rejected 강조, side 필터(buy/sell/both),
    inconclusive/untested 생략, 빈 입력→"".
  - build_messages(hypothesis_feedback=...) → 메시지에 문구 포함;
    =None → 미포함(같은 인자로 None일 때 기존 메시지와 byte-identical 회귀).
  - generate_strategy가 hypothesis_feedback을 build_messages로 전달(provider mock).
  - _generate_pair 토글 OFF(prev_judged 미전달) 시 hypothesis_feedback=None 전달.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.hypothesis import (  # noqa: E402
    VERDICT_ACCEPTED,
    VERDICT_INCONCLUSIVE,
    VERDICT_REJECTED,
    VERDICT_UNTESTED,
    Hypothesis,
    format_hypothesis_feedback,
)
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402


def _hyp(side, text, target, direction, verdict, observed=None):
    return Hypothesis(
        side=side, text=text, target_metric=target,
        expected_direction=direction, source="gate_mdd",
        verdict=verdict, observed_delta=observed,
    )


# =====================================================================
# format_hypothesis_feedback — rejected 강조 + side 필터 + 생략 규칙.
# =====================================================================
class TestFormatHypothesisFeedback:
    def test_empty_input_returns_empty_string(self):
        assert format_hypothesis_feedback([], "buy") == ""
        assert format_hypothesis_feedback(None, "buy") == ""

    def test_rejected_emphasized_with_header_and_metric_delta(self):
        h = _hyp("sell", "매도 손절 강화로 MDD 감소 기대", "mdd", -1,
                 VERDICT_REJECTED, observed=2.5)
        out = format_hypothesis_feedback([h], "sell")
        assert out != ""
        # 헤더 + 기각 강조 문구.
        assert "[직전 가정 판정 — 같은 빗나간 방향 반복 금지]" in out
        assert "매도 손절 강화로 MDD 감소 기대" in out
        assert "기각" in out
        assert "다른 레버" in out
        # 실측 델타가 부호 포함으로 표면화된다.
        assert "+2.5" in out
        assert "mdd" in out

    def test_accepted_is_short_line(self):
        h = _hyp("buy", "진입 품질 향상으로 총손익 흑자전환 기대", "profit", +1,
                 VERDICT_ACCEPTED, observed=120000.0)
        out = format_hypothesis_feedback([h], "buy")
        assert "유효했음" in out
        assert "진입 품질 향상으로 총손익 흑자전환 기대" in out
        # 채택은 "기각/다른 레버" 강조 문구를 쓰지 않는다.
        assert "기각" not in out

    def test_inconclusive_and_untested_omitted(self):
        h_inc = _hyp("buy", "inconclusive 가정", "profit", +1, VERDICT_INCONCLUSIVE)
        h_unt = _hyp("buy", "untested 가정", "profit", +1, VERDICT_UNTESTED)
        # 표면화할 rejected/accepted가 하나도 없으면 "".
        assert format_hypothesis_feedback([h_inc, h_unt], "buy") == ""

    def test_side_filter_buy_excludes_sell_only(self):
        buy_h = _hyp("buy", "buy 전용 가정", "profit", +1, VERDICT_REJECTED, observed=-1.0)
        sell_h = _hyp("sell", "sell 전용 가정", "mdd", -1, VERDICT_REJECTED, observed=3.0)
        out = format_hypothesis_feedback([buy_h, sell_h], "buy")
        assert "buy 전용 가정" in out
        assert "sell 전용 가정" not in out

    def test_side_filter_sell_excludes_buy_only(self):
        buy_h = _hyp("buy", "buy 전용 가정", "profit", +1, VERDICT_REJECTED, observed=-1.0)
        sell_h = _hyp("sell", "sell 전용 가정", "mdd", -1, VERDICT_REJECTED, observed=3.0)
        out = format_hypothesis_feedback([buy_h, sell_h], "sell")
        assert "sell 전용 가정" in out
        assert "buy 전용 가정" not in out

    def test_both_side_included_in_both_buy_and_sell(self):
        both_h = _hyp("both", "refine baseline 가정", "graded", +1,
                      VERDICT_REJECTED, observed=-0.5)
        assert "refine baseline 가정" in format_hypothesis_feedback([both_h], "buy")
        assert "refine baseline 가정" in format_hypothesis_feedback([both_h], "sell")

    def test_rejected_listed_before_accepted(self):
        rej = _hyp("buy", "기각된 가정", "profit", +1, VERDICT_REJECTED, observed=-1.0)
        acc = _hyp("buy", "채택된 가정", "daily_avg_trades", +1, VERDICT_ACCEPTED, observed=1.0)
        out = format_hypothesis_feedback([acc, rej], "buy")
        # 입력 순서와 무관하게 rejected가 accepted보다 먼저 나온다.
        assert out.index("기각된 가정") < out.index("채택된 가정")

    def test_none_observed_delta_renders_zero(self):
        # observed_delta=None인 rejected(이론상 드묾)도 크래시 없이 0으로 표면화.
        h = _hyp("sell", "관측 없는 기각", "mdd", -1, VERDICT_REJECTED, observed=None)
        out = format_hypothesis_feedback([h], "sell")
        assert "관측 없는 기각" in out
        assert "+0" in out


# =====================================================================
# build_messages — 주입 포함 + None일 때 byte-identical 회귀.
# =====================================================================
class TestBuildMessagesInjection:
    _FB = "[직전 가정 판정 — 같은 빗나간 방향 반복 금지]\n- 직전 세대 가정 'x' → 기각."

    def test_feedback_injected_into_user_message(self):
        msgs = build_messages("buy", hypothesis_feedback=self._FB)
        user = next(m["content"] for m in msgs if m["role"] == "user")
        assert "[직전 가정 판정 — 같은 빗나간 방향 반복 금지]" in user

    def test_none_is_byte_identical_to_no_arg(self):
        # 같은 인자로 hypothesis_feedback=None일 때 미주입 인자와 메시지가 동일해야 한다.
        base = build_messages("buy")
        with_none = build_messages("buy", hypothesis_feedback=None)
        assert base == with_none

    def test_empty_string_is_byte_identical(self):
        base = build_messages("sell")
        with_empty = build_messages("sell", hypothesis_feedback="")
        assert base == with_empty

    def test_feedback_appears_before_autopsy_feedback(self):
        # "이전에 틀린 방향" 경고가 부검 피드백보다 먼저 보여야 한다(상위 슬롯).
        msgs = build_messages(
            "buy",
            hypothesis_feedback=self._FB,
            autopsy_feedback="부검: 진입 변별 변수 X",
        )
        user = next(m["content"] for m in msgs if m["role"] == "user")
        assert self._FB.splitlines()[0] in user
        assert "부검: 진입 변별 변수 X" in user
        assert user.index("[직전 가정 판정") < user.index("부검: 진입 변별 변수 X")


# =====================================================================
# generate_strategy — hypothesis_feedback을 build_messages로 전달.
# =====================================================================
class _CaptureProvider:
    """chat에 들어온 messages를 기록하는 mock provider(유효 buy 코드 반환)."""

    def __init__(self):
        self.last_messages = None

    def chat(self, messages, model=None, **kw):
        self.last_messages = messages

        class _R:
            text = (
                "```python\n매수 = True\n"
                "if not (3 <= 등락율 <= 25):\n    매수 = False\n"
                "if 매수:\n    self.Buy()\n```"
            )
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
            model = "mock"

        return _R()


class TestGenerateStrategyForwards:
    def test_generate_strategy_forwards_feedback(self, tmp_path):
        import sqlite3

        from ai_strategy_loop.brain.generator import generate_strategy

        db = str(tmp_path / "s.db")
        con = sqlite3.connect(db)
        con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.commit()
        con.close()

        provider = _CaptureProvider()
        fb = "[직전 가정 판정 — 같은 빗나간 방향 반복 금지]\n- 기각된 방향"
        res = generate_strategy(
            provider, "buy", "T_buy", db, retry_max=1,
            hypothesis_feedback=fb,
        )
        assert res["status"] == "ok", res
        user = next(m["content"] for m in provider.last_messages if m["role"] == "user")
        assert "[직전 가정 판정 — 같은 빗나간 방향 반복 금지]" in user

    def test_generate_strategy_none_omits_feedback(self, tmp_path):
        import sqlite3

        from ai_strategy_loop.brain.generator import generate_strategy

        db = str(tmp_path / "s.db")
        con = sqlite3.connect(db)
        con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.commit()
        con.close()

        provider = _CaptureProvider()
        res = generate_strategy(provider, "buy", "T_buy", db, retry_max=1)
        assert res["status"] == "ok", res
        user = next(m["content"] for m in provider.last_messages if m["role"] == "user")
        assert "직전 가정 판정" not in user


# =====================================================================
# _generate_pair — 토글 OFF(prev_judged 미전달) 시 hypothesis_feedback=None.
# =====================================================================
class TestGeneratePairOffPath:
    def test_off_path_passes_none_feedback(self, tmp_path, monkeypatch):
        """prev_judged_hypotheses를 안 넘기면(기본 None) generate_strategy에
        hypothesis_feedback=None이 전달돼야 한다(byte-identical 보호)."""
        import ai_strategy_loop.bootstrap as bootstrap

        captured = []

        def _fake_generate_strategy(provider, kind, name, db, **kw):
            captured.append((kind, kw.get("hypothesis_feedback")))
            return {"status": "ok", "name": name, "code": "x",
                    "attempts": 1, "usage": {"total_tokens": 1}}

        # _generate_pair는 함수 내부에서 brain.generate_strategy를 지연 import 한다.
        import ai_strategy_loop.brain as brain
        monkeypatch.setattr(brain, "generate_strategy", _fake_generate_strategy)

        cfg = LoopConfig()  # 기본 OFF.
        res = L._generate_pair(
            object(), cfg, "rid", 1, "buy 부검 피드백",
            # prev_judged_hypotheses 미전달(기본 None) → 환류 없음.
        )
        assert res["status"] == "ok", res
        # buy/sell 두 호출 모두 hypothesis_feedback=None.
        assert len(captured) == 2
        assert all(fb is None for _, fb in captured)

    def test_on_path_passes_side_feedback(self, tmp_path, monkeypatch):
        """prev_judged_hypotheses를 넘기면 side별 환류 문자열이 전달돼야 한다."""
        captured = {}

        def _fake_generate_strategy(provider, kind, name, db, **kw):
            captured[kind] = kw.get("hypothesis_feedback")
            return {"status": "ok", "name": name, "code": "x",
                    "attempts": 1, "usage": {"total_tokens": 1}}

        import ai_strategy_loop.brain as brain
        monkeypatch.setattr(brain, "generate_strategy", _fake_generate_strategy)

        judged = [
            _hyp("buy", "buy 기각 가정", "profit", +1, VERDICT_REJECTED, observed=-1.0),
            _hyp("sell", "sell 기각 가정", "mdd", -1, VERDICT_REJECTED, observed=3.0),
        ]
        cfg = LoopConfig()
        res = L._generate_pair(
            object(), cfg, "rid", 1, None,
            prev_judged_hypotheses=judged,
        )
        assert res["status"] == "ok", res
        assert "buy 기각 가정" in (captured.get("buy") or "")
        assert "sell 기각 가정" in (captured.get("sell") or "")
        # side 격리 — buy 환류에 sell 가정이 새지 않는다.
        assert "sell 기각 가정" not in (captured.get("buy") or "")
        assert "buy 기각 가정" not in (captured.get("sell") or "")
