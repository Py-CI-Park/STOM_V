from __future__ import annotations

import pytest

from ai_strategy_loop.brain.principle_gate import check_principle_consistency
from ai_strategy_loop.revision.window_contract import (
    ResearchWindowContract,
    window_contract_from_census,
)


def _census():
    return {
        "schema": "stom.mcap_census.v2",
        "status": "CENSUS_COMPLETED",
        "source": {"lane": "stock_tick", "fingerprint": {"sha256": "a" * 64}},
        "window_contract": {
            "status": "AVAILABLE", "start": "090000", "end_exclusive": "103500",
            "bucket_minutes": list(range(540, 635, 5)),
        },
    }


def test_window_contract_is_derived_from_contiguous_census_buckets():
    contract = window_contract_from_census(_census())
    assert contract.start == 90000
    assert contract.end_exclusive == 103500
    assert contract.bucket_minutes[0] == 540
    assert contract.bucket_minutes[-1] == 630
    assert len(contract.contract_sha256) == 64
    assert contract.to_dict()["authority"] == "existing_db_development_no_oos_no_adoption"


def test_window_contract_rejects_gap_or_unavailable_source():
    payload = _census()
    payload["window_contract"]["bucket_minutes"].remove(600)
    with pytest.raises(ValueError, match="contiguous"):
        window_contract_from_census(payload)
    payload = _census()
    payload["window_contract"]["status"] = "SOURCE_COVERAGE_UNAVAILABLE"
    with pytest.raises(ValueError, match="unavailable"):
        window_contract_from_census(payload)


def test_d3_principle_gate_requires_explicit_census_window():
    buy = "if 90000 <= 시분초 < 103000:\n    매수 = True"
    sell = "if 수익률 <= -2:\n    매도 = True\nelif 시분초 >= 103000:\n    매도 = True"
    violations = check_principle_consistency(
        buy, sell, {"timeframe": "tick", "research_program": "D3", "principle_ids": ["P"]}
    )
    assert {row["rule_id"] for row in violations} == {"WINDOW-CONTRACT"}


def test_d3_principle_gate_accepts_window_bounded_buy_and_forced_exit():
    contract = window_contract_from_census(_census())
    buy = "if 90000 <= 시분초 < 103000:\n    매수 = True"
    sell = "if 수익률 <= -2:\n    매도 = True\nelif 시분초 >= 103000:\n    매도 = True"
    violations = check_principle_consistency(
        buy, sell,
        {"timeframe": "tick", "research_program": "D3", "principle_ids": ["P"],
         "window_contract": contract.to_dict()},
    )
    assert violations == []


def test_d3_principle_gate_rejects_buy_or_exit_beyond_contract():
    contract = ResearchWindowContract(
        lane="stock_tick", start=90000, end_exclusive=93000,
        bucket_minutes=tuple(range(540, 570, 5)), source_fingerprint="a" * 64,
    )
    violations = check_principle_consistency(
        "if 90000 <= 시분초 < 103000:\n    매수 = True",
        "if 수익률 <= -2:\n    매도 = True\nelif 시분초 >= 103000:\n    매도 = True",
        {"timeframe": "tick", "research_program": "D3", "principle_ids": ["P"],
         "window_contract": contract.to_dict()},
    )
    assert [row["rule_id"] for row in violations].count("CSC-10") == 2
