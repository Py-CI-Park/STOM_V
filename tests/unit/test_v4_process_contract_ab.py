from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import run_v4_process_contract_ab as contract_ab


def test_process_contract_ab_is_deterministic_and_has_no_default_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    first = contract_ab.run_process_contract_ab()
    second = contract_ab.run_process_contract_ab()

    assert first == second
    assert list(tmp_path.iterdir()) == []
    assert first["performance_proved"] is False
    assert first["baseline"]["leakage_count"] == 5
    assert first["strict"]["leakage_count"] == 0
    assert first["baseline"]["same_scope_conflicts_unreduced"] == 1
    assert first["strict"]["same_scope_conflicts_reduced"] == 1
    assert first["strict"]["routed_buy_count"] == 1
    assert first["strict"]["routed_sell_count"] == 1
    assert first["baseline"]["buy_prompt_contains_all_free_text"] is True
    assert first["baseline"]["sell_prompt_contains_free_text"] is False
    assert first["strict"]["buy_prompt_contains_only_authorized"] is True
    assert first["strict"]["sell_prompt_contains_only_authorized"] is True

    directive_ids = {
        directive["statement"]: directive["directive_id"]
        for directive in first["fixed_input"]["directives"]
    }
    assert first["baseline"]["unauthorized_buy_directive_ids"] == [
        directive_ids["BUY loser: allow every price move."],
        directive_ids["SELL winner: exit after trailing reversal."],
        directive_ids["HOLDOUT BUY: optimize on evaluation data."],
        directive_ids["STALE BUY: reuse retired threshold."],
        directive_ids["BLOCKED BUY: override risk controls."],
    ]
    assert {
        item["directive_id"] for item in first["baseline"]["routed_buy"]
    } >= set(first["baseline"]["unauthorized_buy_directive_ids"])


def test_cli_json_schema_and_explicit_output_only(tmp_path, capsys):
    assert contract_ab.main([]) == 0
    stdout_result = json.loads(capsys.readouterr().out)
    assert set(stdout_result) == {"schema", "performance_proved", "claim", "fixed_input", "baseline", "strict"}
    assert stdout_result["schema"] == contract_ab.SCHEMA
    assert stdout_result["performance_proved"] is False
    assert "return improvement" in stdout_result["claim"]

    output_path = tmp_path / "evidence.json"
    assert contract_ab.main(["--output", str(output_path)]) == 0
    assert json.loads(output_path.read_text(encoding="utf-8")) == stdout_result
    assert output_path.read_text(encoding="utf-8").endswith("\n")


@pytest.mark.parametrize(
    "protected_path",
    [
        "_database/evidence.json",
        "_database_v3k_shadow/evidence.json",
        "_log/evidence.json",
        "backup/evidence.json",
        "result.DB",
        "backtest/GRAPH/evidence.json",
        ".omx/REPORTS/evidence.json",
        "V3K_SETTINGS_local.JSON",
        "ai_strategy_loop/STATE/evidence.json",
    ],
)
def test_cli_rejects_all_protected_output_classes(tmp_path, protected_path):
    output_path = tmp_path / protected_path

    with pytest.raises(SystemExit) as exc_info:
        contract_ab.main(["--output", str(output_path)])

    assert exc_info.value.code == 2
    assert not output_path.exists()


def test_cli_rejects_input_output_windows_case_alias(tmp_path):
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text("종목코드\n000001\n", encoding="utf-8")
    output_alias = tmp_path / "TRADES.CSV"

    with pytest.raises(SystemExit) as exc_info:
        contract_ab.main(["--csv", str(csv_path), "--output", str(output_alias)])

    assert exc_info.value.code == 2
    assert csv_path.read_text(encoding="utf-8") == "종목코드\n000001\n"


@pytest.mark.parametrize(
    "args",
    [
        ["--output", "_database./evidence.json"],
        ["--output", "result.db."],
        ["--output", "backup /evidence.json"],
        ["--csv", "trades.csv", "--output", "TRADES.CSV."],
        ["--output", "loop_runs.db:evidence"],
        ["--csv", "trades.csv", "--output", "trades.csv:evidence"],
    ],
)
def test_cli_rejects_ambiguous_win32_path_aliases(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text("종목코드\n000001\n", encoding="utf-8")
    before = csv_path.read_bytes()

    with pytest.raises(SystemExit) as exc_info:
        contract_ab.main(args)

    assert exc_info.value.code == 2
    assert csv_path.read_bytes() == before


@pytest.mark.parametrize(
    "args",
    [
        ["--csv", "../trades.csv"],
        ["--output", "../evidence.json"],
    ],
)
def test_cli_rejects_relative_parent_traversal(tmp_path, monkeypatch, args):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        contract_ab.main(args)

    assert exc_info.value.code == 2
    assert list(tmp_path.iterdir()) == []


def test_csv_analysis_is_read_only_and_deterministic(tmp_path):
    csv_path = tmp_path / "trades.csv"
    frame = pd.DataFrame(
        {
            "매수시간": ["2026-01-02 09:01:00", "2026-01-03 09:02:00"],
            "종목코드": ["000001", "000002"],
            "수익률": [1.5, -0.5],
            "수익금": [1500, -500],
            "custom_signal": [10, 20],
        }
    )
    frame.to_csv(csv_path, index=False)
    before = csv_path.read_bytes()

    first = contract_ab.analyze_csv(csv_path)
    second = contract_ab.analyze_csv(csv_path)

    assert first == second
    assert csv_path.read_bytes() == before
    assert first["read_only"] is True
    assert first["performance_proved"] is False
    assert first["analysis_card_v3_count"] == 1
    assert first["feature_findings_count"] == 1
    assert len(first["analysis_card_content_hash"]) == 64
