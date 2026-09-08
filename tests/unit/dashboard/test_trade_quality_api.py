"""Real FastAPI route and snapshot-to-contract integration with synthetic jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import trade_contract_api
from ai_strategy_loop.dashboard.trade_contract import build_trade_artifact_contract
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path

HEADER, ROW = official_pair()


@pytest.mark.parametrize(
    "status,body,quality,ready",
    [
        ("success", ROW, "VALID", True),
        ("success", "", "NO_TRADES", False),
        ("error", ROW, "VALID", False),
        ("success", ROW + "bad\n", "ROW_PARSE_PARTIAL", False),
    ],
)
def test_data_contract_keeps_execution_and_quality_separate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
    body: str,
    quality: str,
    ready: bool,
) -> None:
    # Given: a synthetic job and the actual data-contract router.
    path = tmp_path / "result.csv"
    path.write_text(HEADER + body, encoding="utf-8")

    class Manager:
        def get(self, job_id: str, log_tail: int = 0):
            return {
                "available": True,
                "status": status,
                "csv_path": str(path),
                "spec": {},
            }

    monkeypatch.setattr(trade_contract_api, "get_job_manager", Manager)
    app = FastAPI()
    app.include_router(trade_contract_api.trade_contract_router)
    # When: call the real route through HTTP in-process.
    with TestClient(app) as client:
        response = client.get("/data-contract", params={"job_id": "fixture"})
    # Then: profile visibility never upgrades a failed execution or bad CSV.
    assert response.status_code == 200
    value = response.json()
    assert value["data_quality"]["status"] == quality
    assert value["execution_status"] == status
    assert value["analysis_ready"] is ready
    assert (
        value["contract"]["artifact"]["sha256"]
        == value["data_quality"]["source_sha256"]
    )
    assert (
        value["contract"]["artifact"]["row_count"] == value["data_quality"]["raw_count"]
    )


def test_contract_hash_and_counts_are_from_one_file_open(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: instrument only file opens, not the parser or hashing implementation.
    from pathlib import Path as PathType

    path = tmp_path / "result.csv"
    path.write_text(HEADER + ROW, encoding="utf-8")
    original_open = PathType.open
    opens: list[str] = []

    def counted_open(self: PathType, *args, **kwargs):
        if self == path:
            opens.append(str(args))
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(PathType, "open", counted_open)
    # When: use the preserved production contract builder.
    result = build_trade_artifact_contract(csv_path=path, job_id="fixture", spec={})
    # Then: parse and hash cannot observe different file versions.
    assert result.artifact.row_count == 1
    assert len(opens) == 1
