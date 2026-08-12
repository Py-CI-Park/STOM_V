"""HOF5 게이트·원장 규칙 검증 — 엔진 없이 규율만 본다.

사전 등록: docs/research/quant_scoring_pipeline/2026-08-12_HOF5_사전등록.md
"""

import pytest

from ai_strategy_loop.labeling.run_hof5_relax import (
    CANDIDATES, hof5_gate, sync_ledger)

BASE = {"trade_count": 175, "avg_profit_pct": 0.755,
        "total_profit_krw": 1_316_746, "seed_capital": 1_004_095}


def _cand(**over):
    cand = {"trade_count": 370, "avg_profit_pct": 0.40,
            "total_profit_krw": 1_500_000, "seed_capital": 2_000_000}
    cand.update(over)
    return cand


class TestGate:
    def test_전부_통과(self):
        gate = hof5_gate(BASE, _cand(), capital_limit_krw=20_000_000)
        assert gate["pass"] is True

    def test_건당은_참고일_뿐(self):
        gate = hof5_gate(BASE, _cand(avg_profit_pct=0.3),
                         capital_limit_krw=20_000_000)
        assert gate["per_trade_ref"] is False
        assert gate["pass"] is True

    def test_총수익금_동률은_실패(self):
        gate = hof5_gate(BASE, _cand(total_profit_krw=1_316_746),
                         capital_limit_krw=20_000_000)
        assert gate["money_pass"] is False and gate["pass"] is False

    def test_기준_적자여도_후보는_흑자여야(self):
        base = dict(BASE, total_profit_krw=-10_000)
        gate = hof5_gate(base, _cand(total_profit_krw=-5_000),
                         capital_limit_krw=20_000_000)
        assert gate["money_pass"] is True
        assert gate["positive_pass"] is False and gate["pass"] is False

    def test_자금_초과는_실패(self):
        gate = hof5_gate(BASE, _cand(seed_capital=21_000_000),
                         capital_limit_krw=20_000_000)
        assert gate["pass"] is False

    def test_완화인데_거래가_줄면_실패(self):
        # 절을 뺐는데 거래가 주는 것은 측정 이상 신호다(게이트 D).
        gate = hof5_gate(BASE, _cand(trade_count=170),
                         capital_limit_krw=20_000_000)
        assert gate["more_trades"] is False and gate["pass"] is False


def _report(stage_pass: bool) -> dict:
    return {
        "span": [20220323, 20231121],
        "baseline_metrics": dict(BASE),
        "outcomes": [
            {"arm": "baseline", "buy": "Tick_B_902_905",
             "engine": dict(BASE), "gate": None},
            {"arm": "relax_902_회전율", "clause": "902_회전율",
             "buy": "HOF5_B_RELAX_902_회전율", "engine": _cand(),
             "gate": {"pass": stage_pass, "trade_gain": 195}},
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

    def test_후보는_2종으로_고정(self):
        assert CANDIDATES == ("902_회전율", "905_전일비")

    def test_1차_통과는_MIXED_검증_대기(self):
        sync_ledger(_report(True), stage="train")
        # records fixture 없이 직접 검증하지 않도록 아래 테스트에서 다룬다.

    def test_1차_통과_판정(self, records):
        sync_ledger(_report(True), stage="train")
        assert records[0].verdict == "MIXED"
        assert "검증 대기" in records[0].verdict_reason

    def test_2차_통과가_PROMISING_상한(self, records):
        sync_ledger(_report(True), stage="valid")
        assert records[0].verdict == "PROMISING"  # PASS 불가

    def test_실패는_REJECT(self, records):
        sync_ledger(_report(False), stage="valid")
        assert records[0].verdict == "REJECT"

    def test_재판정임이_notes_에_명시된다(self, records):
        sync_ledger(_report(True), stage="train")
        assert "정책 변경 재판정" in records[0].notes

    def test_기준선_팔은_적재하지_않는다(self, records):
        sync_ledger(_report(True), stage="train")
        assert len(records) == 1
