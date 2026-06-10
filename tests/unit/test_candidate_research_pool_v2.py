from __future__ import annotations

import csv
import json
from pathlib import Path

from ai_strategy_loop.controller.candidate_selection import (
    CandidateGeneration,
    select_candidate_research_pool_v2,
    write_candidate_research_pool_artifact,
)
from ai_strategy_loop.fitness.research_criteria import (
    ResearchOosMode,
    evaluate_research_criteria,
)
from ai_strategy_loop.fitness.holdout import _PROFIT_COLUMN, _SELL_TIME_COLUMN
from ai_strategy_loop.fitness.promotion_diagnostics import CandidateDiagnostics


def _write_csv(path: Path, trades: list[tuple[int, float]]) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([_SELL_TIME_COLUMN, _PROFIT_COLUMN])
        for day, profit in trades:
            writer.writerow([f"{day:08d}0930", profit])
    return path


def _year_trades(year: int, count: int, profit: float) -> list[tuple[int, float]]:
    return [(year * 10000 + 615, profit) for _ in range(count)]


def _valid_trades() -> list[tuple[int, float]]:
    trades: list[tuple[int, float]] = []
    for year in (2023, 2024, 2025):
        trades.extend(_year_trades(year, 60, 1_000.0))
    return trades


def _mixed_year_trades() -> list[tuple[int, float]]:
    trades: list[tuple[int, float]] = []
    trades.extend(_year_trades(2023, 40, -500.0))
    trades.extend(_year_trades(2024, 60, 1_000.0))
    trades.extend(_year_trades(2025, 60, 1_500.0))
    return trades


def _candidate(gen_no: int, csv_path: Path, *, trades: int = 180, mdd: float = 5.0) -> CandidateGeneration:
    return CandidateGeneration(
        gen_no=gen_no,
        status="ok",
        graded_score=float(gen_no),
        gate_passed=False,
        gate_reason="daily_avg_trades 0.1 < min_daily_trades 0.3",
        profit=180_000.0,
        total_profit_pct=18.0,
        mdd=mdd,
        trade_count=trades,
        daily_avg_trades=0.2,
        payoff_ratio=1.2,
        max_hold_count=1.0,
        buy_name=f"buy_{gen_no}",
        sell_name=f"sell_{gen_no}",
        csv_path=str(csv_path),
    )


def test_mdd_risk_candidate_is_retained_for_exploration(tmp_path: Path) -> None:
    # Given: a high-train candidate that misses strict MDD.
    candidate = _candidate(1, _write_csv(tmp_path / "mdd.csv", _valid_trades()), mdd=12.0)

    # When: the three-tier selector runs.
    result = select_candidate_research_pool_v2(
        (candidate,), run_id="train", config_path="cfg.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: it remains analyzable but not promotable.
    assert [item.gen_no for item in result.exploration_pool] == [1]
    assert "mdd_risk" in result.exploration_pool[0].labels
    assert result.promotion_candidate is None


def test_gen6_style_trade_near_miss_stays_in_research_pool(tmp_path: Path) -> None:
    # Given: gen6-like candidate: good profit/MDD but aggregate trades below promotion floor.
    candidate = _candidate(6, _write_csv(tmp_path / "gen6.csv", _valid_trades()), trades=136, mdd=7.6)

    # When: the pool selector runs.
    result = select_candidate_research_pool_v2(
        (candidate,), run_id="train", config_path="cfg.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: it is research-worthy but fails Promotion Gate.
    assert [item.gen_no for item in result.research_pool] == [6]
    assert "near_miss" in result.research_pool[0].labels
    assert result.promotion_candidate is None
    assert "trade_count < 150" in result.research_pool[0].promotion_reasons


def test_gen7_style_mdd_near_miss_stays_in_research_pool(tmp_path: Path) -> None:
    # Given: gen7-like candidate with MDD just above strict threshold.
    candidate = _candidate(7, _write_csv(tmp_path / "gen7.csv", _valid_trades()), trades=91, mdd=10.32)

    # When: the pool selector runs.
    result = select_candidate_research_pool_v2(
        (candidate,), run_id="train", config_path="cfg.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: it is retained with risk labels, not promoted.
    assert [item.gen_no for item in result.research_pool] == [7]
    assert {"near_miss", "mdd_risk"} <= set(result.research_pool[0].labels)
    assert result.promotion_candidate is None


def test_oos_contaminated_csv_is_structurally_rejected(tmp_path: Path) -> None:
    # Given: a training CSV polluted by fixed-OOS years.
    trades = _valid_trades()
    trades.extend(_year_trades(2022, 1, 1_000.0))
    contaminated = _candidate(8, _write_csv(tmp_path / "oos.csv", trades))

    # When: the pool selector runs.
    result = select_candidate_research_pool_v2(
        (contaminated,), run_id="train", config_path="cfg.json", config_hash="cfg", policy_hash="policy"
    )

    # Then: the candidate is rejected before either pool.
    assert result.exploration_pool == ()
    assert result.structural_rejections[0].gen_no == 8
    assert "csv contains non-training year 2022" in result.structural_rejections[0].reasons


def test_diagnostics_label_research_candidate_without_removing_it(tmp_path: Path) -> None:
    # Given: a candidate with high PBO and insufficient DSR.
    candidate = _candidate(9, _write_csv(tmp_path / "diag.csv", _valid_trades()), trades=136)
    diagnostics = {9: CandidateDiagnostics(pbo_status="ok", pbo_value=0.7, dsr_status="insufficient_data")}

    # When: diagnostics are attached to the selector.
    result = select_candidate_research_pool_v2(
        (candidate,),
        run_id="train",
        config_path="cfg.json",
        config_hash="cfg",
        policy_hash="policy",
        diagnostics_by_gen=diagnostics,
    )

    # Then: risk labels are present but the candidate remains in the research pool.
    assert [item.gen_no for item in result.research_pool] == [9]
    assert {"pbo_high", "dsr_insufficient"} <= set(result.research_pool[0].labels)


def test_pool_artifact_writes_oos_blind_schema(tmp_path: Path) -> None:
    # Given: a labeled research candidate with diagnostics.
    candidate = _candidate(10, _write_csv(tmp_path / "artifact.csv", _valid_trades()), trades=136)
    diagnostics = {10: CandidateDiagnostics(pbo_status="ok", pbo_value=0.7, dsr_status="insufficient_data")}
    result = select_candidate_research_pool_v2(
        (candidate,),
        run_id="train",
        config_path="cfg.json",
        config_hash="cfg",
        policy_hash="policy",
        diagnostics_by_gen=diagnostics,
    )

    # When: the result is written as an artifact.
    output_path = tmp_path / "pools.json"
    write_candidate_research_pool_artifact(result, output_path)

    # Then: the schema remains OOS-blind and preserves labels/diagnostics.
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["selector_version"] == "candidate_research_pool_v2"
    assert payload["policy_hash"] == "policy"
    assert payload["config_hash"] == "cfg"
    assert payload["oos_excluded"] is True
    assert payload["forbidden_oos_fields_detected"] is False
    assert payload["promotion_candidate"] is None
    assert payload["exploration_pool"][0]["labels"]
    assert payload["research_pool"][0]["diagnostics"]["pbo_value"] == 0.7
    assert payload["rejected_structural"] == []


def test_research_criteria_allows_losing_year_when_aggregate_curve_is_upward(tmp_path: Path) -> None:
    # Given: a candidate with one losing year but positive aggregate and stronger recent years.
    candidate = _candidate(11, _write_csv(tmp_path / "mixed.csv", _mixed_year_trades()), trades=160)

    # When: research criteria are evaluated in OOS-disabled discovery mode.
    result = select_candidate_research_pool_v2(
        (candidate,),
        run_id="train",
        config_path="cfg.json",
        config_hash="cfg",
        policy_hash="policy",
        research_oos_mode=ResearchOosMode.DISABLED,
    )

    # Then: the candidate remains research-continuable but not a promotion claim.
    assert result.research_oos_mode is ResearchOosMode.DISABLED
    assert result.research_pool[0].research_criteria.research_continue is True
    assert result.research_pool[0].research_criteria.promotion_claim is False
    assert "losing_year_allowed" in result.research_pool[0].research_criteria.reason_codes
    assert "oos_disabled_research_only" in result.research_pool[0].research_criteria.reason_codes


def test_oos_disabled_mode_does_not_reject_candidate_from_missing_oos(tmp_path: Path) -> None:
    # Given: a normal training-only candidate with no fixed-OOS evidence attached.
    candidate = _candidate(12, _write_csv(tmp_path / "train.csv", _valid_trades()), trades=160)

    # When: the selector runs in OOS-disabled mode.
    result = select_candidate_research_pool_v2(
        (candidate,),
        run_id="train",
        config_path="cfg.json",
        config_hash="cfg",
        policy_hash="policy",
        research_oos_mode=ResearchOosMode.DISABLED,
    )

    # Then: missing OOS cannot be a research rejection reason.
    assert [item.gen_no for item in result.research_pool] == [12]
    assert result.research_pool[0].research_criteria.research_continue is True
    assert "missing_oos" not in result.research_pool[0].research_criteria.reason_codes
    assert result.promotion_candidate is None


def test_research_criteria_helper_reports_payoff_compensation() -> None:
    # Given: a low win-day proxy but strong payoff candidate and upward yearly series.
    candidate = CandidateGeneration(
        gen_no=13,
        status="ok",
        graded_score=1.0,
        gate_passed=False,
        gate_reason="daily_avg_trades 0.1 < min_daily_trades 0.3",
        profit=200_000.0,
        total_profit_pct=20.0,
        mdd=6.0,
        trade_count=80,
        daily_avg_trades=0.2,
        payoff_ratio=2.2,
        max_hold_count=1.0,
        buy_name="buy_13",
        sell_name="sell_13",
    )

    # When: criteria are computed directly.
    criteria = evaluate_research_criteria(
        candidate,
        yearly_breakdown=(),
        research_oos_mode=ResearchOosMode.DISABLED,
    )

    # Then: large payoff can compensate sparse/lower-hit-rate research signal.
    assert criteria.research_continue is True
    assert criteria.payoff_compensation is True
    assert criteria.win_day_ratio is None
