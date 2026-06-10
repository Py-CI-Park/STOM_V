from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.candidate_selection import (  # noqa: E402
    CandidateGeneration,
    SeedProfile,
    SeedRelativeThresholds,
    select_seed_relative_v1,
    select_sparse_positive_v1,
    write_seed_relative_artifact,
)


def _candidate(
    gen_no: int,
    *,
    profit: float,
    mdd: float,
    trade_count: int,
    daily: float = 0.2,
    payoff: float = 1.4,
    csv_path: str = "",
    status: str = "ok",
) -> CandidateGeneration:
    return CandidateGeneration(
        gen_no=gen_no,
        status=status,
        graded_score=1.0,
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


# 2026-06-10 train 실측 프로파일.
SEED_LIKE = dict(profit=8_631_199, mdd=17.44, trade_count=307, daily=0.4, payoff=1.486)
C7_LIKE = dict(profit=2_347_400, mdd=16.52, trade_count=142, daily=0.2, payoff=1.452)
GEN4_LIKE = dict(profit=1_155_715, mdd=9.12, trade_count=124, daily=0.2, payoff=1.552)
SEED_PROFILE = SeedProfile(mdd=17.44, trade_count=307, profit=8_631_199, source="test")


def test_root_cause_1_seed_like_passes_here_but_fails_sparse_positive() -> None:
    """원인1 문서화: 시드급 행동(MDD 17.44/거래 307)은 sparse_positive_v1에서 탈락하지만
    seed_relative_v1에서는 적격이어야 한다."""
    seedlike = _candidate(0, **SEED_LIKE)

    sparse = select_sparse_positive_v1(
        (seedlike,), run_id="r", config_path="c", config_hash="h",
    )
    assert sparse.selected is False
    reasons = sparse.rejected_candidates[0].reasons
    assert any("mdd" in r for r in reasons)
    assert any("trade_count > 250" in r for r in reasons)

    rel = select_seed_relative_v1(
        (seedlike,), run_id="r", config_path="c", config_hash="h",
        seed_profile=SEED_PROFILE,
    )
    assert rel.selected is True
    assert rel.selected_candidate is not None
    assert rel.selected_candidate.gen_no == 0
    # mdd 한도 = max(20, 17.44*1.1=19.184) = 20.
    assert rel.mdd_limit == pytest.approx(20.0)


def test_mdd_limit_uses_seed_mult_when_above_floor() -> None:
    rel = select_seed_relative_v1(
        (_candidate(0, **C7_LIKE),), run_id="r", config_path="c", config_hash="h",
        seed_profile=SeedProfile(mdd=25.0, trade_count=300),
    )
    assert rel.mdd_limit == pytest.approx(27.5)  # 25*1.1 > floor 20


def test_no_seed_profile_falls_back_to_abs_floor() -> None:
    rel = select_seed_relative_v1(
        (_candidate(0, **C7_LIKE),), run_id="r", config_path="c", config_hash="h",
        seed_profile=None,
    )
    assert rel.mdd_limit == pytest.approx(20.0)
    assert rel.selected is True


def test_rejections_negative_profit_low_trades_overtrade() -> None:
    candidates = (
        _candidate(0, profit=-100.0, mdd=5.0, trade_count=100),
        _candidate(1, profit=1000.0, mdd=5.0, trade_count=49),
        _candidate(2, profit=1000.0, mdd=5.0, trade_count=401),
        _candidate(3, profit=1000.0, mdd=30.0, trade_count=100),
    )
    rel = select_seed_relative_v1(
        candidates, run_id="r", config_path="c", config_hash="h",
        seed_profile=SEED_PROFILE,
    )
    assert rel.selected is False
    assert rel.blocked is True
    by_gen = {r.gen_no: r.reasons for r in rel.rejected_candidates}
    assert any("profit <= 0" in x for x in by_gen[0])
    assert any("trade_count < 50" in x for x in by_gen[1])
    assert any("trade_count > 400" in x for x in by_gen[2])
    assert any("seed-relative limit" in x for x in by_gen[3])


def test_yearly_advisory_ranks_consistent_candidate_first() -> None:
    """연도별 흑자 advisory가 1차 순위 신호다 — 자격이 아니라 순위만 바꾼다."""
    def fake_loader(csv_path: str):
        if csv_path == "csv_a":  # 3/3년 흑자, 수익은 더 작음
            return (("2023", 500_000.0), ("2024", 400_000.0), ("2025", 300_000.0))
        if csv_path == "csv_b":  # 2023 한 해 행운형, 수익은 더 큼
            return (("2023", 5_000_000.0), ("2024", -500_000.0), ("2025", -300_000.0))
        return None

    a = _candidate(0, profit=1_200_000, mdd=10.0, trade_count=150, csv_path="csv_a")
    b = _candidate(1, profit=4_200_000, mdd=10.0, trade_count=150, csv_path="csv_b")

    rel = select_seed_relative_v1(
        (a, b), run_id="r", config_path="c", config_hash="h",
        seed_profile=SEED_PROFILE, csv_loader=fake_loader,
    )
    assert rel.selected is True
    assert rel.selected_candidate is not None
    assert rel.selected_candidate.gen_no == 0  # 3년 흑자 > 단년 행운(수익 커도)
    assert rel.selected_yearly is not None
    assert rel.selected_yearly.positive_years == 3
    assert rel.selected_yearly.meets_advisory is True
    # b는 자격은 유지(advisory는 순위 신호일 뿐).
    assert {e.gen_no for e in rel.eligible_candidates} == {0, 1}


def test_yearly_advisory_is_graceful_when_csv_missing() -> None:
    rel = select_seed_relative_v1(
        (_candidate(0, **C7_LIKE, csv_path="no_such.csv"),),
        run_id="r", config_path="c", config_hash="h", seed_profile=SEED_PROFILE,
    )
    assert rel.selected is True  # advisory 실패는 자격에 영향 없음
    assert rel.selected_yearly is None


def test_artifact_is_oos_blind_and_json_serializable(tmp_path) -> None:
    rel = select_seed_relative_v1(
        (_candidate(0, **C7_LIKE),), run_id="r", config_path="c", config_hash="h",
        seed_profile=SEED_PROFILE,
    )
    out = tmp_path / "p5-seed-relative.json"
    write_seed_relative_artifact(rel, out)

    import json

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["selector_version"] == "seed_relative_v1"
    assert payload["oos_excluded"] is True
    assert payload["forbidden_oos_fields_present"] is False
    assert "oos_2022" not in json.dumps(payload)


def test_custom_thresholds_respected() -> None:
    rel = select_seed_relative_v1(
        (_candidate(0, profit=1000.0, mdd=5.0, trade_count=30),),
        run_id="r", config_path="c", config_hash="h",
        thresholds=SeedRelativeThresholds(min_trade_count=20),
    )
    assert rel.selected is True
