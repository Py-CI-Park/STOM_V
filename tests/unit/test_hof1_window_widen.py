"""HOF1 시간창 확장 러너의 순수 함수 검증.

엔진을 돌리지 않고 변환·게이트·원장 적재 규칙만 검증한다.
사전 등록: docs/research/quant_scoring_pipeline/2026-08-10_HOF1_사전등록.md
"""

import pytest

from ai_strategy_loop.labeling.run_window_widen import (
    MAX_END, WINDOW_LINE, hof1_gate, sync_ledger, widen_window)

FIXTURE = (
    "if 시분초 < 90200:\n"
    "    매수 = 조건A\n"
    "elif 90200 <= 시분초 < 90500:\n"
    "    매수 = 조건B\n"
)


class TestWidenWindow:
    def test_한_줄만_바뀐다(self):
        out = widen_window(FIXTURE, 92000)
        assert "elif 90200 <= 시분초 < 92000:" in out
        assert WINDOW_LINE not in out
        # 나머지 줄은 그대로다.
        assert out.splitlines()[0] == "if 시분초 < 90200:"
        assert out.splitlines()[1] == "    매수 = 조건A"
        assert out.splitlines()[3] == "    매수 = 조건B"

    def test_표식이_남는다(self):
        out = widen_window(FIXTURE, 92000)
        assert "HOF1 시간창 확장" in out
        assert "원본 90500" in out

    def test_원본은_불변이다(self):
        code = str(FIXTURE)
        widen_window(code, 91000)
        assert code == FIXTURE

    def test_대상_줄이_없으면_거부(self):
        with pytest.raises(ValueError, match="0회"):
            widen_window("elif 90200 <= 시분초 < 90600:\n", 92000)

    def test_대상_줄이_두_번이면_거부(self):
        with pytest.raises(ValueError, match="2회"):
            widen_window(FIXTURE + FIXTURE, 92000)

    def test_이미_확장된_코드는_거부(self):
        once = widen_window(FIXTURE, 92000)
        with pytest.raises(ValueError, match="이미"):
            widen_window(once, 92000)

    @pytest.mark.parametrize("bad", [90500, 90400, 92001, 93000])
    def test_사용자_확정_상한_밖은_거부(self, bad):
        # 사용자 확정(2026-08-10): 09:20 이 최대. 09:30 시도 금지.
        with pytest.raises(ValueError, match="허용 범위"):
            widen_window(FIXTURE, bad)

    @pytest.mark.parametrize("ok", [90600, 91000, MAX_END])
    def test_허용_범위는_통과(self, ok):
        assert f"< {ok}:" in widen_window(FIXTURE, ok)


BASE = {"trade_count": 361, "avg_profit_pct": 0.67,
        "total_profit_krw": 2_421_433, "seed_capital": 1_004_095}


def _cand(**over):
    cand = {"trade_count": 1300, "avg_profit_pct": 0.40,
            "total_profit_krw": 3_500_000, "seed_capital": 4_000_000}
    cand.update(over)
    return cand


class TestGate:
    def test_전부_통과(self):
        gate = hof1_gate(BASE, _cand(), capital_limit_krw=20_000_000)
        assert gate["pass"] is True
        assert gate["trade_gain"] == 939

    def test_건당은_참고일_뿐_필수가_아니다(self):
        # 건당이 기준선보다 낮아도(0.40 < 0.67) 통과한다 — 사전 등록 E항.
        gate = hof1_gate(BASE, _cand(avg_profit_pct=0.40),
                         capital_limit_krw=20_000_000)
        assert gate["per_trade_ref"] is False
        assert gate["pass"] is True

    def test_거래가_늘지_않으면_실패(self):
        gate = hof1_gate(BASE, _cand(trade_count=361),
                         capital_limit_krw=20_000_000)
        assert gate["pass"] is False

    def test_총수익금_미달이면_실패(self):
        gate = hof1_gate(BASE, _cand(total_profit_krw=2_000_000),
                         capital_limit_krw=20_000_000)
        assert gate["money_pass"] is False
        assert gate["pass"] is False

    def test_헌법_12항_기준선이_적자여도_후보는_흑자여야_한다(self):
        base = dict(BASE, total_profit_krw=-100_000)
        gate = hof1_gate(base, _cand(total_profit_krw=-50_000),
                         capital_limit_krw=20_000_000)
        assert gate["money_pass"] is True      # 기준선 이상이지만
        assert gate["positive_pass"] is False  # 흑자가 아니다
        assert gate["pass"] is False

    def test_자금_한도_초과면_실패(self):
        gate = hof1_gate(BASE, _cand(seed_capital=25_000_000),
                         capital_limit_krw=20_000_000)
        assert gate["capital_pass"] is False
        assert gate["pass"] is False

    def test_지표_결측이면_실패(self):
        gate = hof1_gate(BASE, {"trade_count": 1300},
                         capital_limit_krw=20_000_000)
        assert gate["pass"] is False


def _report(gate_pass: bool) -> dict:
    return {
        "lane": "tick", "design": [20220323, 20250822], "end_hhmmss": 92000,
        "baseline_metrics": dict(BASE),
        "outcomes": [
            {"arm": "baseline", "buy": "Tick_B_902_905",
             "sell": "Tick_S_902_905", "engine": dict(BASE), "gate": None},
            {"arm": "candidate", "buy": "HOF1_B_WINDOW_920",
             "sell": "Tick_S_902_905", "engine": _cand(),
             "gate": {"pass": gate_pass, "trade_gain": 939,
                      "money_pass": True, "positive_pass": True,
                      "capital_pass": True, "capital_limit_krw": 20_000_000.0}},
        ],
    }


class TestLedger:
    @pytest.fixture
    def records(self, monkeypatch):
        captured = []
        monkeypatch.setattr(
            "ai_strategy_loop.controller.strategy_ledger.append",
            lambda record: captured.append(record))
        return captured

    def test_기준선_팔은_적재하지_않는다(self, records):
        assert sync_ledger(_report(True)) == 1
        assert len(records) == 1
        assert records[0].buy_name == "HOF1_B_WINDOW_920"

    def test_통과해도_상한은_PROMISING(self, records):
        sync_ledger(_report(True))
        assert records[0].verdict == "PROMISING"  # PASS 는 불가능하다

    def test_실패는_REJECT(self, records):
        sync_ledger(_report(False))
        assert records[0].verdict == "REJECT"

    def test_매도식_이름이_바르게_적힌다(self, records):
        sync_ledger(_report(True))
        assert records[0].sell_name == "Tick_S_902_905"
        assert records[0].baseline_id == "Tick_B_902_905::Tick_S_902_905"
