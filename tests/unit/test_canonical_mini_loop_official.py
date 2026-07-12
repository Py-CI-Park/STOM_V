from __future__ import annotations

import re
from pathlib import Path

from ai_strategy_loop.controller.candidate_pool import select_official_candidate
from ai_strategy_loop.scripts.run_canonical_mini_loop import METHODOLOGY, MiniLoopConfig, TIMEFRAME, run_mini_loop
from ai_strategy_loop.scripts.run_canonical_mini_loop_official import OfficialEvaluator, OfficialProvider


_EXPRESSIONS = {
    (1, 1): "체결강도 > 101",
    (1, 2): "등락율 < 4.9",
    (1, 3): "체결강도 >= 1.0",
    (1, 4): "등락율 < -3.1",
    (2, 1): "체결강도 > 102",
    (2, 2): "등락율 < 4.8",
    (2, 3): "체결강도 >= 2.0",
    (2, 4): "등락율 < -3.2",
    (3, 1): "체결강도 > 103",
    (3, 2): "등락율 < 4.7",
    (3, 3): "체결강도 >= 3.0",
    (3, 4): "등락율 < -3.3",
}


def _canonical_buy_code(expression: str) -> str:
    return (
        "매수 = False\n"
        "if 관심종목 != 1:\n"
        "    매수 = False\n"
        f"elif {expression}:\n"
        "    매수 = True\n"
        "if 매수:\n"
        "    self.Buy()\n"
    )


def _canonical_sell_code() -> str:
    return (
        "매도 = False\n"
        "if 보유시간 >= 1:\n"
        "    매도 = True\n"
        "if 매도:\n"
        "    self.Sell()\n"
    )


def _stub_generate(gubun: str, name: str, autopsy_feedback: str) -> dict:
    assert "CL-R07 round" in autopsy_feedback
    if gubun == "sell":
        return {"status": "ok", "code": _canonical_sell_code()}
    match = re.search(r"R(\d{2})_(\d{2})", name)
    assert match is not None
    key = (int(match.group(1)), int(match.group(2)))
    return {"status": "ok", "code": _canonical_buy_code(_EXPRESSIONS[key])}


def _stub_select_window(*_args) -> tuple[str, int, int, int]:
    return "005930", 20250102, 20250108, 5


class RecordingBacktest:
    def __init__(self) -> None:
        self.buy_codes: list[str] = []

    def __call__(self, buy_code: str, sell_code: str, one_code: str, start: int, end: int) -> dict:
        assert buy_code
        assert sell_code
        assert one_code == "005930"
        assert start == 20250102
        assert end == 20250108
        self.buy_codes.append(buy_code)
        arm_offset = {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}
        offset = next((value for arm, value in arm_offset.items() if f"_{arm}" in buy_code + sell_code), 0.0)
        ordinal = sum(ord(ch) for ch in buy_code + sell_code) % 17
        return {
            "status": "ok",
            "profit": 10.0 + ordinal / 10.0 + offset,
            "mdd": 1.0 + ordinal / 100.0 + offset / 10.0,
            "trade_count": 40 + ordinal,
            "daily_freq": 0.8 + ordinal / 100.0,
        }


class RecordingEvaluator(OfficialEvaluator):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.primary_clauses: list[str] = []

    def evaluate(self, candidate: dict, *, kind: str, arm: str | None, context: dict) -> dict:
        if kind == "primary":
            self.primary_clauses.append(str(candidate.get("expression") or ""))
        return super().evaluate(candidate, kind=kind, arm=arm, context=context)


def test_go_process_proof(tmp_path: Path):
    strategy_db = tmp_path / "strat.sqlite"
    backtest = RecordingBacktest()
    provider = OfficialProvider(generate=_stub_generate, strategy_db=strategy_db)
    evaluator = RecordingEvaluator(
        backtest=backtest,
        select_window=_stub_select_window,
        strategy_db=strategy_db,
    )
    summary = run_mini_loop(
        MiniLoopConfig(strategy_db=strategy_db, evidence_dir=tmp_path / "ev"),
        provider=provider,
        evaluator=evaluator,
    )

    assert summary["status"] == "GO_PROCESS_PROOF"
    assert summary["provider_calls"] <= 3
    assert summary["total_official_evaluation_spend"] <= 9
    assert summary["learning_chain_ok"] is True
    assert summary["ablation_valid"] is True
    assert summary["feedback_consumptions"] == 2
    assert evaluator.primary_clauses == ["체결강도 >= 1.0", "체결강도 >= 2.0", "체결강도 >= 3.0"]
    assert len(set(evaluator.primary_clauses)) == 3
    assert "if 관심종목 != 1:" in backtest.buy_codes[0]
    assert "elif 체결강도 >= 1.0:" in backtest.buy_codes[0]


def test_protected_db_refused(tmp_path: Path):
    provider = OfficialProvider(generate=_stub_generate, strategy_db=tmp_path / "unused.db")
    evaluator = OfficialEvaluator(
        backtest=RecordingBacktest(),
        select_window=_stub_select_window,
        strategy_db=tmp_path / "unused.db",
    )
    summary = run_mini_loop(
        MiniLoopConfig(strategy_db=Path("_database") / "x.db", evidence_dir=tmp_path / "ev"),
        provider=provider,
        evaluator=evaluator,
    )

    assert summary["status"].startswith("NO_GO_OPERATING_DB_PATH_REFUSED")


def test_propose_pack_shape(tmp_path: Path):
    provider = OfficialProvider(generate=_stub_generate, strategy_db=tmp_path / "strat.db")
    proposals = provider.propose_pack(round_no=1, feedback=[])

    assert len(proposals) == 4
    assert [proposal["lane"] for proposal in proposals].count("repair") == 2
    assert [proposal["lane"] for proposal in proposals].count("discovery") == 2
    assert len({proposal["expression"] for proposal in proposals}) == 4
    assert all("if 관심종목 != 1:" in proposal["buy_code"] for proposal in proposals)
    selection = select_official_candidate(
        proposals,
        timeframe=TIMEFRAME,
        methodology_version=METHODOLOGY,
    )
    assert selection["selected"] is not None
    assert not any("semantic_duplicate" in reason for reason in selection.get("pool_blockers", []))
def test_retry_yields_distinct(tmp_path: Path):
    calls: dict[str, int] = {}

    def generate(gubun: str, name: str, autopsy_feedback: str) -> dict:
        if gubun == "sell":
            return {"status": "ok", "code": _canonical_sell_code()}
        calls[name] = calls.get(name, 0) + 1
        match = re.search(r"R(\d{2})_(\d{2})", name)
        assert match is not None
        round_no = int(match.group(1))
        index = int(match.group(2))
        if index == 2 and calls[name] == 1:
            expression = _EXPRESSIONS[(round_no, 1)]
        elif index == 2:
            assert _EXPRESSIONS[(round_no, 1)] in autopsy_feedback
            expression = _EXPRESSIONS[(round_no, 2)]
        else:
            expression = _EXPRESSIONS[(round_no, index)]
        return {"status": "ok", "code": _canonical_buy_code(expression)}

    provider = OfficialProvider(generate=generate, strategy_db=tmp_path / "strat.sqlite")
    proposals = provider.propose_pack(round_no=1, feedback=[])

    assert len(proposals) == 4
    assert len({proposal["expression"] for proposal in proposals}) == 4
    assert calls["CLR07_R01_02_repair_mean_reversion_buy"] == 2
    selection = select_official_candidate(
        proposals,
        timeframe=TIMEFRAME,
        methodology_version=METHODOLOGY,
    )
    assert selection["selected"] is not None


def test_persistent_duplicate_degrades_gracefully(tmp_path: Path):
    def generate(gubun: str, name: str, autopsy_feedback: str) -> dict:
        if gubun == "sell":
            return {"status": "ok", "code": _canonical_sell_code()}
        return {"status": "ok", "code": _canonical_buy_code("체결강도 > 101")}

    strategy_db = tmp_path / "strat.sqlite"
    provider = OfficialProvider(generate=generate, strategy_db=strategy_db)
    evaluator = OfficialEvaluator(
        backtest=RecordingBacktest(),
        select_window=_stub_select_window,
        strategy_db=strategy_db,
    )

    summary = run_mini_loop(
        MiniLoopConfig(strategy_db=strategy_db, evidence_dir=tmp_path / "ev"),
        provider=provider,
        evaluator=evaluator,
    )

    assert summary["status"] == "NO_GO_POOL_BLOCKED"
