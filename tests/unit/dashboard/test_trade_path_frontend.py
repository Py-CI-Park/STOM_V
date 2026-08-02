"""QSP7 거래 경로 연구가 V4 정본 화면에 배선되는지 검사한다."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_backtest_mounts_trade_path_workbench() -> None:
    source = _read("v4-backtest.jsx")
    assert 'from "./bt-trade-path-tab.jsx"' in source
    assert "<BtTradePathTab" in source


def test_replay_reads_trade_path_deep_link_context() -> None:
    source = _read("v4-replay.jsx")
    assert 'from "./bt-replay-trade-context.jsx"' in source
    assert "<BtReplayTradeContext" in source


def test_history_mounts_official_pair_evidence() -> None:
    source = _read("v4-history.jsx")
    assert 'from "./bt-trade-path-history.jsx"' in source
    assert "<BtTradePathHistory" in source


def test_trade_path_surface_discloses_authority_and_boundary() -> None:
    source = _read("bt-trade-path-tab.jsx") + _read("bt-exit-counterfactual.jsx")
    assert "진단" in source
    assert "자문" in source
    assert "정본" in source
    assert "전체청산" in source
    assert "전체청산 (HHMMSS)" in source
    assert "forced_liquidation_time" in source
    assert "/bt/trade-path/preflight" in source
    assert "/bt/trade-path/counterfactual" in source


def test_trade_path_surface_mounts_data_contract_page() -> None:
    source = _read("bt-trade-path-tab.jsx")
    contract = _read("bt-data-contract.jsx")
    assert 'from "./bt-data-contract.jsx"' in source
    assert "데이터 계약" in source
    assert "/bt/trade-path/data-contract" in source
    assert "CSV SHA256" in contract
    assert "zero_only" in contract
    assert "missing" in contract


def test_official_run_form_sends_intraday_session_boundary() -> None:
    source = _read("bt-tab-run.jsx")
    assert "start_time" in source
    assert "end_time" in source
    assert "전체청산" in source


def test_trade_path_surface_mounts_entry_variable_autopsy() -> None:
    source = _read("bt-trade-path-tab.jsx")
    entry = _read("bt-entry-autopsy.jsx")
    assert 'from "./bt-entry-autopsy.jsx"' in source
    assert "매수 해부" in source
    assert "/bt/analysis/leaf_matrix" in entry
    assert "/bt/analysis/feature_map" in entry
    assert "모든 B_*" in entry
    assert "R_*·S_*는 매수 입력으로 사용하지 않습니다" in entry


def test_trade_path_time_formatter_handles_tick_and_min_timestamps() -> None:
    source = _read("bt-trade-path-chart.jsx")
    assert "text.length === 12" in source
    assert "text.length === 14" in source


def test_reports_wiki_indexes_quant_scoring_pipeline() -> None:
    research_api = (ROOT / "ai_strategy_loop" / "dashboard" / "research_api.py").read_text(encoding="utf-8")
    research_index = (ROOT / "ai_strategy_loop" / "dashboard" / "research_index.py").read_text(encoding="utf-8")
    assert "docs/research/quant_scoring_pipeline" in research_api
    assert "docs/research/quant_scoring_pipeline" in research_index
