"""Unit tests for absolute_niche_v1 selector.

케이스 목록 (스펙 §3 테스트 명세):
  1. 전 기준 통과 + corr 0.3 → 선택됨
  2. corr 0.6 + time_overlap True → 니치 자격 미달 기각 (사유 문자열 확인)
  3. corr None + time_overlap False → 시간버킷 분기로 적격
  4. corr/overlap 둘 다 None → 판정 불가 기각
  5. MDD 21 → 기각
  6. 흑자 연도 1 → 기각  (csv 주입)
  7. payoff 1.0 → 기각
  8. 적격 2개 중 graded_score 큰 쪽 선택
  9. 아티팩트 writer: oos_excluded=true 포함 JSON 생성
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.candidate_selection import (  # noqa: E402
    CandidateGeneration,
    NicheMetricEntry,
    select_absolute_niche_v1,
    write_absolute_niche_artifact,
)
from ai_strategy_loop.fitness.holdout import _PROFIT_COLUMN, _SELL_TIME_COLUMN  # noqa: E402


# ---------------------------------------------------------------------------
# 헬퍼: 합성 후보 생성
# ---------------------------------------------------------------------------


def _candidate(
    gen_no: int,
    *,
    profit: float = 2_000_000.0,
    mdd: float = 10.0,
    trade_count: int = 100,
    payoff: float = 1.2,
    graded_score: float = 1.0,
    csv_path: str = "",
    status: str = "ok",
    daily: float = 0.2,
) -> CandidateGeneration:
    return CandidateGeneration(
        gen_no=gen_no,
        status=status,
        graded_score=graded_score,
        gate_passed=False,
        gate_reason="daily_avg_trades 0.2 < min_daily_trades 0.3",
        profit=profit,
        total_profit_pct=None,
        mdd=mdd,
        trade_count=trade_count,
        daily_avg_trades=daily,
        payoff_ratio=payoff,
        max_hold_count=0.0,
        buy_name=f"BUY_{gen_no}",
        sell_name=f"SELL_{gen_no}",
        csv_path=csv_path,
    )


def _write_trade_csv(
    path: Path,
    year_profits: list[tuple[int, float]],
    trades_per_year: int = 30,
) -> Path:
    """year_profits: [(year, profit_per_trade), ...] — trades_per_year 행씩 기록."""
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([_SELL_TIME_COLUMN, _PROFIT_COLUMN])
        for year, profit_per_trade in year_profits:
            for _ in range(trades_per_year):
                writer.writerow([f"{year:04d}06150930", profit_per_trade])
    return path


# ---------------------------------------------------------------------------
# 케이스 1: 전 기준 통과 + corr 0.3 → 선택됨
# ---------------------------------------------------------------------------


def test_all_criteria_pass_corr_low_selected(tmp_path: Path) -> None:
    csv_path = _write_trade_csv(
        tmp_path / "c1.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    c = _candidate(1, csv_path=str(csv_path))
    metrics = {1: NicheMetricEntry(corr_vs_frozen=0.3, time_bucket_overlap=None)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is True
    assert result.selected_candidate is not None
    assert result.selected_candidate.gen_no == 1
    assert result.oos_excluded is True
    assert result.selector_version == "absolute_niche_v1"


# ---------------------------------------------------------------------------
# 케이스 2: corr 0.6 + time_overlap True → 니치 자격 미달 기각 (사유 확인)
# ---------------------------------------------------------------------------


def test_high_corr_and_overlap_true_rejected(tmp_path: Path) -> None:
    csv_path = _write_trade_csv(
        tmp_path / "c2.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    c = _candidate(2, csv_path=str(csv_path))
    metrics = {2: NicheMetricEntry(corr_vs_frozen=0.6, time_bucket_overlap=True)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is False
    assert len(result.rejected_candidates) == 1
    rej = result.rejected_candidates[0]
    assert rej.gen_no == 2
    # 사유 문자열에 corr 수치와 niche_disqualified 포함
    reason_text = " ".join(rej.reasons)
    assert "niche_disqualified" in reason_text
    assert "0.600" in reason_text or "corr_vs_frozen=0.6" in reason_text


# ---------------------------------------------------------------------------
# 케이스 3: corr None + time_overlap False → 시간버킷 분기로 적격
# ---------------------------------------------------------------------------


def test_corr_none_overlap_false_qualifies_via_bucket(tmp_path: Path) -> None:
    csv_path = _write_trade_csv(
        tmp_path / "c3.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    c = _candidate(3, csv_path=str(csv_path))
    metrics = {3: NicheMetricEntry(corr_vs_frozen=None, time_bucket_overlap=False)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is True
    assert result.selected_candidate is not None
    assert result.selected_candidate.gen_no == 3


# ---------------------------------------------------------------------------
# 케이스 4: corr/overlap 둘 다 None → 판정 불가 기각
# ---------------------------------------------------------------------------


def test_both_niche_metrics_none_rejected(tmp_path: Path) -> None:
    csv_path = _write_trade_csv(
        tmp_path / "c4.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    c = _candidate(4, csv_path=str(csv_path))
    metrics = {4: NicheMetricEntry(corr_vs_frozen=None, time_bucket_overlap=None)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is False
    rej = result.rejected_candidates[0]
    assert rej.gen_no == 4
    reason_text = " ".join(rej.reasons)
    assert "undetermined" in reason_text or "cannot determine" in reason_text


# ---------------------------------------------------------------------------
# 케이스 5: MDD 21 → 기각
# ---------------------------------------------------------------------------


def test_mdd_above_ceiling_rejected(tmp_path: Path) -> None:
    csv_path = _write_trade_csv(
        tmp_path / "c5.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    c = _candidate(5, mdd=21.0, csv_path=str(csv_path))
    metrics = {5: NicheMetricEntry(corr_vs_frozen=0.3, time_bucket_overlap=None)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is False
    rej = result.rejected_candidates[0]
    reason_text = " ".join(rej.reasons)
    assert "mdd > 20.0" in reason_text or "absolute ceiling" in reason_text


# ---------------------------------------------------------------------------
# 케이스 6: 흑자 연도 1 → 기각 (P2 연도 일관성)
# ---------------------------------------------------------------------------


def test_only_one_positive_year_rejected(tmp_path: Path) -> None:
    # 2023 흑자, 2024/2025 적자 → 흑자 연도 1
    csv_path = _write_trade_csv(
        tmp_path / "c6.csv",
        [(2023, 10_000.0), (2024, -500.0), (2025, -500.0)],
    )
    c = _candidate(6, csv_path=str(csv_path))
    metrics = {6: NicheMetricEntry(corr_vs_frozen=0.3, time_bucket_overlap=None)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is False
    rej = result.rejected_candidates[0]
    reason_text = " ".join(rej.reasons)
    assert "positive_years" in reason_text or "P2" in reason_text


# ---------------------------------------------------------------------------
# 케이스 7: payoff_ratio 1.0 → 기각
# ---------------------------------------------------------------------------


def test_payoff_below_threshold_rejected(tmp_path: Path) -> None:
    csv_path = _write_trade_csv(
        tmp_path / "c7.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    c = _candidate(7, payoff=1.0, csv_path=str(csv_path))
    metrics = {7: NicheMetricEntry(corr_vs_frozen=0.3, time_bucket_overlap=None)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is False
    rej = result.rejected_candidates[0]
    reason_text = " ".join(rej.reasons)
    assert "payoff_ratio" in reason_text


# ---------------------------------------------------------------------------
# 케이스 8: 적격 2개 중 graded_score 큰 쪽 선택
# ---------------------------------------------------------------------------


def test_higher_graded_score_wins(tmp_path: Path) -> None:
    csv_a = _write_trade_csv(
        tmp_path / "ca.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    csv_b = _write_trade_csv(
        tmp_path / "cb.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    # gen_no=10: graded 1.5 (낮음), gen_no=11: graded 2.8 (높음) → 11이 선택돼야
    a = _candidate(10, graded_score=1.5, csv_path=str(csv_a))
    b = _candidate(11, graded_score=2.8, csv_path=str(csv_b))
    metrics = {
        10: NicheMetricEntry(corr_vs_frozen=0.3, time_bucket_overlap=None),
        11: NicheMetricEntry(corr_vs_frozen=0.2, time_bucket_overlap=None),
    }

    result = select_absolute_niche_v1(
        [a, b], niche_metrics=metrics, run_id="r", config_path="p", config_hash="h"
    )

    assert result.selected is True
    assert result.selected_candidate is not None
    assert result.selected_candidate.gen_no == 11
    assert len(result.eligible_candidates) == 2


# ---------------------------------------------------------------------------
# 케이스 9: 아티팩트 writer — oos_excluded=true 포함 JSON 생성
# ---------------------------------------------------------------------------


def test_artifact_writer_oos_excluded_true(tmp_path: Path) -> None:
    csv_path = _write_trade_csv(
        tmp_path / "c9.csv",
        [(2023, 10_000.0), (2024, 10_000.0), (2025, 10_000.0)],
    )
    c = _candidate(9, csv_path=str(csv_path))
    metrics = {9: NicheMetricEntry(corr_vs_frozen=0.3, time_bucket_overlap=None)}

    result = select_absolute_niche_v1(
        [c], niche_metrics=metrics, run_id="run_test", config_path="cfg.json", config_hash="abc"
    )
    out = tmp_path / "niche_artifact.json"
    write_absolute_niche_artifact(result, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["selector_version"] == "absolute_niche_v1"
    assert payload["oos_excluded"] is True
    assert payload["selected"] is True
    assert payload["selected_generation"]["gen_no"] == 9
    assert payload["selected_niche_metric"]["corr_vs_frozen"] == pytest.approx(0.3)
    # OOS 필드가 직렬화되지 않았는지 확인
    raw = out.read_text(encoding="utf-8")
    assert "oos_2022" not in raw
    assert "forbidden_oos_fields_present" in raw
