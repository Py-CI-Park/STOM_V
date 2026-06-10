from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ai_strategy_loop.controller.candidate_selection import (
    CandidateGeneration,
    ForbiddenOosFieldError,
    parse_candidate_generation,
    select_sparse_positive_v1,
    select_yearly_sparse_robust_v1,
    write_yearly_sparse_robust_artifact,
)
from ai_strategy_loop.fitness.holdout import _PROFIT_COLUMN, _SELL_TIME_COLUMN


def _write_csv(path: Path, trades: list[tuple[int, float]]) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([_SELL_TIME_COLUMN, _PROFIT_COLUMN])
        for day, profit in trades:
            writer.writerow([f"{day:08d}0930", profit])
    return path


def _year_trades(year: int, count: int, profit: float) -> list[tuple[int, float]]:
    return [(year * 10000 + 615, profit) for _ in range(count)]


def _candidate(gen_no: int, csv_path: Path, *, profit: float = 180_000.0, trades: int = 180) -> CandidateGeneration:
    return CandidateGeneration(
        gen_no=gen_no,
        status="ok",
        graded_score=float(gen_no),
        gate_passed=False,
        gate_reason="daily_avg_trades 0.1 < min_daily_trades 0.3",
        profit=profit,
        total_profit_pct=profit / 100_000.0,
        mdd=5.0,
        trade_count=trades,
        daily_avg_trades=0.2,
        payoff_ratio=1.2,
        max_hold_count=1.0,
        buy_name=f"buy_{gen_no}",
        sell_name=f"sell_{gen_no}",
        csv_path=str(csv_path),
    )


def _valid_trades() -> list[tuple[int, float]]:
    trades: list[tuple[int, float]] = []
    for year in (2023, 2024, 2025):
        trades.extend(_year_trades(year, 60, 1_000.0))
    return trades


def test_writes_artifact_when_candidate_is_yearly_robust(tmp_path: Path) -> None:
    # Given: one sparse-positive candidate with positive 2023/2024/2025 CSV evidence.
    csv_path = _write_csv(tmp_path / "robust.csv", _valid_trades())
    candidate = _candidate(4, csv_path)

    # When: yearly_sparse_robust_v1 selects and writes the frozen artifact.
    result = select_yearly_sparse_robust_v1(
        (candidate,),
        run_id="train",
        config_path="config.json",
        config_hash="cfg",
        policy_hash="policy",
        selection_timestamp="2026-06-04T12:00:00+00:00",
    )
    output_path = tmp_path / "selected.json"
    write_yearly_sparse_robust_artifact(result, output_path)

    # Then: the artifact is OOS-blind and carries the yearly robustness fields.
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["selector_version"] == "yearly_sparse_robust_v1"
    assert payload["selected"] is True
    assert payload["oos_excluded"] is True
    assert payload["diagnostic_only"] is False
    assert payload["forbidden_oos_fields_present"] is False
    assert payload["selected_generation"]["gen_no"] == 4
    assert {item["year"] for item in payload["yearly_breakdown"]} == {2023, 2024, 2025}
    assert payload["uptrend_r2"] >= 0.5


def test_rejects_when_total_trade_count_is_below_150(tmp_path: Path) -> None:
    # Given: a candidate that passes sparse_positive_v1 but misses the robust total trade floor.
    csv_path = _write_csv(tmp_path / "low_total.csv", _valid_trades())
    candidate = _candidate(5, csv_path, trades=149)

    # When: the robust selector evaluates it.
    result = select_yearly_sparse_robust_v1(
        (candidate,), run_id="train", config_path="config.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: no candidate is selected and the exact robust floor is recorded.
    assert result.selected is False
    assert result.blocked is True
    assert "trade_count < 150" in result.rejected_candidates[0].reasons


def test_rejects_negative_training_year(tmp_path: Path) -> None:
    # Given: a candidate with one negative training year in the result CSV.
    trades = _year_trades(2023, 60, 1_000.0)
    trades.extend(_year_trades(2024, 60, -1_000.0))
    trades.extend(_year_trades(2025, 60, 1_000.0))
    csv_path = _write_csv(tmp_path / "negative_year.csv", trades)

    # When: the robust selector evaluates it.
    result = select_yearly_sparse_robust_v1(
        (_candidate(6, csv_path),), run_id="train", config_path="config.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: the negative year blocks OOS eligibility.
    assert result.selected is False
    assert "year 2024 profit <= 0" in result.rejected_candidates[0].reasons


def test_rejects_year_below_30_trades(tmp_path: Path) -> None:
    # Given: a candidate with 2024 below the per-year trade floor.
    trades = _year_trades(2023, 60, 1_000.0)
    trades.extend(_year_trades(2024, 29, 1_000.0))
    trades.extend(_year_trades(2025, 60, 1_000.0))
    csv_path = _write_csv(tmp_path / "sparse_year.csv", trades)

    # When: the robust selector evaluates it.
    result = select_yearly_sparse_robust_v1(
        (_candidate(7, csv_path),), run_id="train", config_path="config.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: the sparse year is rejected before OOS.
    assert result.selected is False
    assert "year 2024 trade_count < 30" in result.rejected_candidates[0].reasons


def test_rejects_missing_csv(tmp_path: Path) -> None:
    # Given: a candidate whose generation CSV is missing.
    missing = tmp_path / "missing.csv"

    # When: the robust selector evaluates it.
    result = select_yearly_sparse_robust_v1(
        (_candidate(8, missing),), run_id="train", config_path="config.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: missing CSV blocks the candidate rather than silently selecting it.
    assert result.selected is False
    assert any(reason.startswith("csv read failed") for reason in result.rejected_candidates[0].reasons)


def test_rejects_csv_containing_oos_year_rows(tmp_path: Path) -> None:
    # Given: a candidate CSV contaminated with fixed-OOS year rows.
    trades = _valid_trades()
    trades.extend(_year_trades(2022, 1, 999_999.0))
    trades.extend(_year_trades(2026, 1, 999_999.0))
    csv_path = _write_csv(tmp_path / "oos_contaminated.csv", trades)

    # When: the robust selector evaluates it before any fixed OOS run.
    result = select_yearly_sparse_robust_v1(
        (_candidate(10, csv_path),), run_id="train", config_path="config.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: non-training CSV years block selection instead of influencing ranking.
    assert result.selected is False
    reasons = result.rejected_candidates[0].reasons
    assert "csv contains non-training year 2022" in reasons
    assert "csv contains non-training year 2026" in reasons


def test_parse_rejects_additional_oos_fields() -> None:
    # Given: a generation row polluted by a fixed-OOS AI result field.
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
        "ai_2022": {"profit": 999.0},
    }

    # When / Then: boundary parsing rejects the polluted input.
    with pytest.raises(ForbiddenOosFieldError):
        parse_candidate_generation(raw)


def test_ranking_prefers_higher_minimum_yearly_profit(tmp_path: Path) -> None:
    # Given: candidate 2 has lower total profit but better worst-year profit.
    high_total = _year_trades(2023, 60, 100.0)
    high_total.extend(_year_trades(2024, 60, 1_000.0))
    high_total.extend(_year_trades(2025, 60, 1_000.0))
    balanced = _valid_trades()
    candidate_a = _candidate(2, _write_csv(tmp_path / "a.csv", high_total), profit=126_000.0)
    candidate_b = _candidate(3, _write_csv(tmp_path / "b.csv", balanced), profit=180_000.0)

    # When: both candidates are eligible.
    result = select_yearly_sparse_robust_v1(
        (candidate_a, candidate_b), run_id="train", config_path="config.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: the candidate with the stronger weakest year wins deterministically.
    assert result.selected_candidate is not None
    assert result.selected_candidate.gen_no == 3


def test_sparse_positive_v1_stays_less_strict_than_yearly_selector(tmp_path: Path) -> None:
    # Given: a candidate that passes sparse_positive_v1 but not yearly_sparse_robust_v1.
    csv_path = _write_csv(tmp_path / "valid.csv", _valid_trades())
    candidate = _candidate(9, csv_path, trades=99)

    # When: both selectors evaluate the same candidate.
    v1 = select_sparse_positive_v1((candidate,), run_id="train", config_path="config.json", config_hash="cfg")
    robust = select_yearly_sparse_robust_v1(
        (candidate,), run_id="train", config_path="config.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: v1 behavior is unchanged and the new selector is strictly separate.
    assert v1.selected is True
    assert v1.selector_version == "sparse_positive_v1"
    assert robust.selected is False
    assert robust.selector_version == "yearly_sparse_robust_v1"
