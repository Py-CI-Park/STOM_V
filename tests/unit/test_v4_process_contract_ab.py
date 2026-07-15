from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts import run_v4_process_contract_ab as contract_ab


def test_process_contract_ab_is_deterministic_and_has_no_default_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    first = contract_ab.run_process_contract_ab()
    second = contract_ab.run_process_contract_ab()

    assert first == second
    assert list(tmp_path.iterdir()) == []
    assert first["performance_proved"] is False
    assert first["baseline"]["leakage_count"] > 0
    assert first["strict"]["leakage_count"] == 0
    assert first["baseline"]["same_scope_conflicts_unreduced"] == 1
    assert first["strict"]["same_scope_conflicts_reduced"] == 1
    assert first["strict"]["routed_buy_count"] == 1
    assert first["strict"]["routed_sell_count"] == 1


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
