"""Review findings: schema, count authority, bounded issues, malformed timestamp."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ai_strategy_loop.dashboard import trade_contract_api
from ai_strategy_loop.dashboard.trade_csv_quality import load_trade_quality
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path

HEADER = "종목명,매수시간,매도시간,보유시간,수익률,수익금\n"
ROW = "삼성전자,20250102090000,20250102090100,60,0,0\n"


def test_custom_header_does_not_certify_official_schema(tmp_path: Path) -> None:
    # Given / When: a readable six-column subset is not an official artifact.
    path = tmp_path / "custom.csv"
    path.write_text(HEADER + ROW, encoding="utf-8")
    result = load_trade_quality(path)
    # Then: diagnostics may retain the row, but readiness is blocked.
    assert result.quality.status == "INVALID_SCHEMA"
    assert result.quality.analysis_ready is False
    assert len(result.trades) == 1


def test_late_issue_category_survives_detail_limit(tmp_path: Path) -> None:
    # Given: many parse errors precede a nonfinite value and hash mismatch.
    path = tmp_path / "bad.csv"
    path.write_text(
        HEADER
        + ROW.replace(",0,0\n", ",0,bad\n") * 101
        + ROW.replace(",0,0\n", ",0,nan\n"),
        encoding="utf-8",
    )
    # When: details are bounded.
    result = load_trade_quality(path, expected_sha256="0" * 64)
    # Then: all distinct categories are still present separately.
    assert result.quality.issues_truncated is True
    assert set(result.quality.issue_codes) >= {
        "NONFINITE_VALUE",
        "ROW_PARSE_PARTIAL",
        "IDENTITY_MISMATCH",
    }


@pytest.mark.parametrize("bad_time", [False, True])
def test_api_uses_actual_count_and_keeps_malformed_time_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_time: bool,
) -> None:
    # Given: actual job metrics disagree with the CSV; optional corrupt timestamp.
    path = tmp_path / "result.csv"
    body = ROW.replace("20250102090100", "²" * 14) if bad_time else ROW
    path.write_text(HEADER + body, encoding="utf-8")

    class Manager:
        def get(self, job_id: str, log_tail: int = 0):
            return {
                "available": True,
                "status": "success",
                "csv_path": str(path),
                "metrics": {"trade_count": 2},
                "spec": {},
            }

    monkeypatch.setattr(trade_contract_api, "get_job_manager", Manager)
    # When: profile the bad artifact through the real endpoint.
    result = trade_contract_api.data_contract("fixture")
    # Then: do not raise HTTP500; count mismatch remains visible.
    assert result.data_quality is not None
    assert result.data_quality.expected_row_count == 2
    assert "ROW_COUNT_MISMATCH" in result.data_quality.issue_codes
    assert result.analysis_ready is False


@pytest.mark.parametrize("legacy", [False, True])
def test_named_official_schemas_are_supported(tmp_path: Path, legacy: bool) -> None:
    # Given / When: real owner names, including the legacy fourteen B columns.
    header, row = official_pair(legacy=legacy)
    path = tmp_path / "official.csv"
    path.write_text(header + row, encoding="utf-8")
    result = load_trade_quality(path)
    # Then: actual supported shape, not merely a padded column count.
    assert result.quality.status == "VALID"
    assert result.quality.official_schema == ("legacy_37" if legacy else "modern_54")
    assert result.quality.analysis_ready is True


def test_padded_54_column_custom_schema_is_not_official(tmp_path: Path) -> None:
    # Given / When: arbitrary names are padded to the official width.
    path = tmp_path / "custom.csv"
    path.write_text(
        ",".join(f"fake{i}" for i in range(48)) + "," + HEADER + "0," * 48 + ROW,
        encoding="utf-8",
    )
    result = load_trade_quality(path)
    # Then: do not certify official schema by count alone.
    assert result.quality.status == "INVALID_SCHEMA"
    assert result.quality.official_schema is None


def test_nonfinite_unprojected_official_factor_blocks_readiness(tmp_path: Path) -> None:
    # Given: a corrupt official factor not copied into the legacy trade dict.
    header, row = official_pair()
    cells = row.strip().split(",")
    cells[header.strip().split(",").index("B_현재가")] = "nan"
    path = tmp_path / "factor.csv"
    path.write_text(header + ",".join(cells) + "\n", encoding="utf-8")
    # When / Then: official factor corruption is not mislabeled as zero-only readiness.
    result = load_trade_quality(path)
    assert result.quality.status == "NONFINITE_VALUE"
    assert result.quality.analysis_ready is False
