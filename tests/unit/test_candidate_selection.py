from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_strategy_loop.controller.candidate_selection import (
    CandidateGeneration,
    ForbiddenOosFieldError,
    parse_candidate_generation,
    select_sparse_positive_v1,
    write_selection_artifact,
)


def _candidate(
    gen_no: int,
    *,
    profit: float,
    mdd: float,
    trade_count: int,
    daily_avg_trades: float,
    gate_passed: bool = False,
    gate_reason: str = "daily_avg_trades 0.1 < min_daily_trades 0.3",
    payoff_ratio: float = 1.2,
) -> CandidateGeneration:
    return CandidateGeneration(
        gen_no=gen_no,
        status="ok",
        graded_score=float(gen_no),
        gate_passed=gate_passed,
        gate_reason=gate_reason,
        profit=profit,
        total_profit_pct=profit / 100000.0,
        mdd=mdd,
        trade_count=trade_count,
        daily_avg_trades=daily_avg_trades,
        payoff_ratio=payoff_ratio,
        max_hold_count=1.0,
        buy_name=f"buy_{gen_no}",
        sell_name=f"sell_{gen_no}",
    )


def test_selects_sparse_positive_when_graded_best_is_training_negative() -> None:
    # Given: prior gen4-like negative candidate and gen5-like sparse-positive candidate.
    candidates = (
        _candidate(4, profit=-67190.0, mdd=23.52, trade_count=287, daily_avg_trades=0.4),
        _candidate(5, profit=1432608.0, mdd=5.74, trade_count=99, daily_avg_trades=0.1, payoff_ratio=1.57),
    )

    # When: sparse_positive_v1 selects from training-only generations.
    result = select_sparse_positive_v1(
        candidates,
        run_id="train_run",
        config_path="config.json",
        config_hash="abc123",
        diagnostic_only=True,
        selection_timestamp="2026-06-04T12:40:00+09:00",
    )

    # Then: the negative generation is rejected and the sparse-positive generation is selected.
    assert result.selected is True
    assert result.blocked is False
    assert result.selected_candidate is not None
    assert result.selected_candidate.gen_no == 5
    assert result.selected_bucket == "sparse_positive"
    assert result.rejected_candidates[0].gen_no == 4
    assert "profit <= 0" in result.rejected_candidates[0].reasons
    assert result.oos_excluded is True
    assert result.diagnostic_only is True


def test_gate_passed_positive_bucket_outranks_sparse_positive() -> None:
    # Given: one lower-profit hard-gate positive and one higher-profit sparse-positive candidate.
    candidates = (
        _candidate(2, profit=500000.0, mdd=5.0, trade_count=60, daily_avg_trades=0.4, gate_passed=True, gate_reason=""),
        _candidate(3, profit=1500000.0, mdd=5.0, trade_count=80, daily_avg_trades=0.1),
    )

    # When: candidates are selected by sparse_positive_v1.
    result = select_sparse_positive_v1(
        candidates,
        run_id="train_run",
        config_path="config.json",
        config_hash="abc123",
        selection_timestamp="2026-06-04T12:40:00+09:00",
    )

    # Then: the hard-gate positive bucket wins before within-bucket ranking is considered.
    assert result.selected_candidate is not None
    assert result.selected_candidate.gen_no == 2
    assert result.selected_bucket == "hard_gate_positive"


def test_rejects_mixed_gate_failure_even_when_profitable() -> None:
    # Given: a profitable candidate with an MDD gate failure in the reason text.
    candidates = (
        _candidate(
            7,
            profit=1000000.0,
            mdd=5.0,
            trade_count=80,
            daily_avg_trades=0.1,
            gate_reason="daily_avg_trades 0.1 < min_daily_trades 0.3; mdd 64.66 > mdd_cap 35",
        ),
    )

    # When: the selector evaluates it.
    result = select_sparse_positive_v1(
        candidates,
        run_id="train_run",
        config_path="config.json",
        config_hash="abc123",
        selection_timestamp="2026-06-04T12:40:00+09:00",
    )

    # Then: mixed failures are not eligible for the sparse-positive bucket.
    assert result.selected is False
    assert result.blocked is True
    assert result.rejected_candidates[0].gen_no == 7
    assert "mixed gate failure" in result.rejected_candidates[0].reasons


def test_parse_candidate_generation_rejects_oos_fields() -> None:
    # Given: a training row polluted by an OOS field.
    raw = {
        "gen_no": 1,
        "status": "ok",
        "graded_score": 0.1,
        "gate_passed": False,
        "gate_reason": "daily_avg_trades 0.1 < min_daily_trades 0.3",
        "profit": 1.0,
        "total_profit_pct": 1.0,
        "mdd": 1.0,
        "trade_count": 20,
        "daily_avg_trades": 0.1,
        "payoff_ratio": 1.1,
        "max_hold_count": 1.0,
        "buy_name": "buy",
        "sell_name": "sell",
        "oos_2022": {"profit": 999},
    }

    # When / Then: boundary parsing rejects the polluted row.
    with pytest.raises(ForbiddenOosFieldError):
        parse_candidate_generation(raw)


def test_write_selection_artifact_contains_required_schema(tmp_path: Path) -> None:
    # Given: a valid sparse-positive selection result.
    result = select_sparse_positive_v1(
        (_candidate(5, profit=1432608.0, mdd=5.74, trade_count=99, daily_avg_trades=0.1),),
        run_id="train_run",
        config_path="config.json",
        config_hash="abc123",
        diagnostic_only=True,
        selection_timestamp="2026-06-04T12:40:00+09:00",
    )
    output_path = tmp_path / "selected.json"

    # When: the artifact is written.
    write_selection_artifact(result, output_path)

    # Then: the JSON contains the freeze schema needed before OOS.
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["selector_version"] == "sparse_positive_v1"
    assert payload["run_id"] == "train_run"
    assert payload["selected"] is True
    assert payload["gen_no"] == 5
    assert payload["oos_excluded"] is True
    assert payload["diagnostic_only"] is True
    assert payload["forbidden_oos_fields_present"] is False
    assert payload["eligible_candidates"][0]["bucket"] == "sparse_positive"
