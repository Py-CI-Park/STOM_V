"""Production-loader regression; all inputs are temporary synthetic CSVs."""

from __future__ import annotations

import hashlib
import importlib
import os
from typing import TYPE_CHECKING

import pytest

from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path

HEADER, ROW = official_pair()


def test_missing_is_not_zero_trades(tmp_path: Path) -> None:
    # Given / When: actual production adapter reads an absent artifact.
    module = importlib.import_module("ai_strategy_loop.dashboard.trade_csv_quality")
    result = module.load_trade_quality(tmp_path / "missing.csv")
    # Then: no invented row count or hash.
    assert result.quality.status == "MISSING_ARTIFACT"
    assert result.quality.raw_count is None
    assert result.quality.source_sha256 is None


@pytest.mark.parametrize("body,count,status", [("", 0, "NO_TRADES"), (ROW, 1, "VALID")])
def test_valid_header_preserves_real_zero(
    tmp_path: Path,
    body: str,
    count: int,
    status: str,
) -> None:
    # Given: a normal schema with either zero rows or a zero-profit trade.
    path = tmp_path / "result.csv"
    path.write_text(HEADER + body, encoding="utf-8-sig")
    # When: parse real bytes.
    module = importlib.import_module("ai_strategy_loop.dashboard.trade_csv_quality")
    result = module.load_trade_quality(path)
    # Then: hash, counts and values retain their distinct meanings.
    assert result.quality.status == status
    assert result.quality.raw_count == result.quality.accepted_count == count
    assert result.quality.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    if count:
        assert result.trades[0].profit_krw == 0
        assert result.trades[0].hold_sec == 60


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_nonfinite_row_never_silently_passes(tmp_path: Path, bad: str) -> None:
    # Given: one valid row and one nonfinite row.
    path = tmp_path / "result.csv"
    path.write_text(
        HEADER + ROW + ROW.replace(",0,0\n", f",0,{bad}\n"), encoding="utf-8"
    )
    # When: inspect, keeping partial rows only for diagnostics.
    module = importlib.import_module("ai_strategy_loop.dashboard.trade_csv_quality")
    result = module.load_trade_quality(path)
    # Then: report both partial parsing and the nonfinite issue.
    assert result.quality.status == "NONFINITE_VALUE"
    assert result.quality.raw_count == 2
    assert result.quality.accepted_count == result.quality.rejected_count == 1
    assert {i.code for i in result.quality.issues} >= {
        "NONFINITE_VALUE",
        "ROW_PARSE_PARTIAL",
    }
    assert result.quality.analysis_ready is False


@pytest.mark.parametrize(
    "text", ["", "wrong,header\n1,2\n", HEADER.replace("수익금", "수익률")]
)
def test_invalid_headers_are_not_no_trades(tmp_path: Path, text: str) -> None:
    # Given / When: empty, missing-required, or duplicate header input.
    path = tmp_path / "result.csv"
    path.write_text(text, encoding="utf-8")
    module = importlib.import_module("ai_strategy_loop.dashboard.trade_csv_quality")
    result = module.load_trade_quality(path)
    # Then: schema failure is not normal zero trades.
    assert result.quality.status == "INVALID_SCHEMA"
    assert result.quality.analysis_ready is False


def test_same_mtime_and_size_cannot_reuse_stale_content(tmp_path: Path) -> None:
    # Given: two equal-length snapshots under the same path and timestamps.
    path = tmp_path / "result.csv"
    path.write_text(HEADER + ROW, encoding="utf-8")
    stamp = path.stat()
    module = importlib.import_module("ai_strategy_loop.dashboard.trade_csv_quality")
    first = module.load_trade_quality(path)
    path.write_text(HEADER + ROW.replace(",0,0\n", ",0,1\n"), encoding="utf-8")
    os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    # When: use the production adapter again.
    second = module.load_trade_quality(path)
    # Then: identity and data change together, prior immutable result stays intact.
    assert first.quality.source_sha256 != second.quality.source_sha256
    assert first.trades[0].profit_krw == 0
    assert second.trades[0].profit_krw == 1


def test_expected_count_and_hash_mismatch_are_both_retained(tmp_path: Path) -> None:
    # Given / When: explicit expectations do not match the actual artifact.
    path = tmp_path / "result.csv"
    path.write_text(HEADER + ROW, encoding="utf-8")
    module = importlib.import_module("ai_strategy_loop.dashboard.trade_csv_quality")
    result = module.load_trade_quality(
        path, expected_row_count=2, expected_sha256="0" * 64
    )
    # Then: multiple failures survive, without replacing actual identity/counts.
    assert result.quality.status == "IDENTITY_MISMATCH"
    assert {i.code for i in result.quality.issues} >= {
        "IDENTITY_MISMATCH",
        "ROW_COUNT_MISMATCH",
    }
    assert result.quality.raw_count == 1
