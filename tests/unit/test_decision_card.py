"""tests/unit/test_decision_card.py — gen_decision_card 단위 테스트 (합성 입력만 사용)."""
from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

import pytest

from ai_strategy_loop.scripts.gen_decision_card import (
    collect_oos_rows,
    compose_card,
    load_json,
)


# ---------------------------------------------------------------------------
# 합성 픽스처
# ---------------------------------------------------------------------------

def _selected() -> Dict[str, Any]:
    return {
        "run_id": "test_run_oos_2026",
        "seed_profile": {
            "mdd": 17.44,
            "trade_count": 307,
            "profit": 8631199.0,
        },
        "selected_candidate": {
            "gen_no": 7,
            "buy_name": "TEST_CAND_B",
            "sell_name": "TEST_CAND_S",
            "profit": 10965479.0,
            "mdd": 10.04,
            "trade_count": 272,
            "graded_score": 7.85,
            "gate_passed": True,
        },
        "selected_yearly": {
            "years": [["2023", 4590073.0], ["2024", 4518416.0], ["2025", 1856990.0]],
            "positive_years": 3,
            "observed_years": 3,
            "meets_advisory": True,
        },
        "eligible_candidates": [
            {
                "gen_no": 7,
                "yearly": {
                    "years": [["2023", 4590073.0], ["2024", 4518416.0], ["2025", 1856990.0]],
                    "positive_years": 3,
                    "observed_years": 3,
                },
            },
            {
                "gen_no": 6,
                "yearly": {
                    "years": [["2023", 5118041.0], ["2024", 4117757.0], ["2025", 1558687.0]],
                    "positive_years": 3,
                    "observed_years": 3,
                },
            },
            {
                "gen_no": 4,
                "yearly": {
                    "years": [["2023", 4226996.0], ["2024", 4269124.0], ["2025", 1532023.0]],
                    "positive_years": 3,
                    "observed_years": 3,
                },
            },
        ],
    }


def _overfit() -> Dict[str, Any]:
    return {
        "note": "advisory only",
        "n_trials": 80,
        "dsr": {"dsr": 0.9447, "n_trials": 80.0},
        "pbo": {"pbo": 0.343, "n_combinations": 70},
        "mc_block_bootstrap": {
            "p_positive": 1.0,
            "profit_p50": 10628872.0,
            "n_days": 212,
        },
        "pool_independence": {
            "mean_pairwise_correlation": 0.9339,
            "effective_independent_candidates": 1.06,
            "pbo_reliability_warning": "후보 풀 평균 상관 0.93 > 0.7",
        },
    }


def _overlap() -> Dict[str, Any]:
    return {
        "n_trades_a": 304,
        "n_trades_b": 270,
        "n_common": 270,
        "jaccard": 0.8882,
        "interpretation": "사실상 동일 거래",
        "note": "advisory",
    }


def _yearly() -> Dict[str, Any]:
    return {"selected": False, "blocked": True, "blocker": "no candidate qualified"}


def _oos_rows() -> Dict[str, Any]:
    return {
        "theta_oos_2022_test": [
            {"gen_no": 0, "buy_name": "THETA_B", "profit": 2097751.0, "mdd": 13.75, "trade_count": 55}
        ],
        "theta_oos_2026_test": [
            {"gen_no": 0, "buy_name": "THETA_B", "profit": 164602.0, "mdd": 14.7, "trade_count": 9}
        ],
    }


def _regime() -> Dict[str, Any]:
    return {
        "metric": "breadth",
        "n_days": 952,
        "breakdowns": {
            "THETA": {
                "active": {"profit": 6503770.0, "days": 137, "months": []},
                "contracted": {"profit": 6724062.0, "days": 138, "months": []},
                "unlabeled": {"profit": 0.0, "days": 0, "months": []},
                "concentration": 0.5083,
                "warning": None,
            }
        },
        "note": "advisory",
    }


def _rejected() -> Dict[str, Any]:
    return {
        "rejected": [
            {
                "label": "REVIVAL EXIT2C take9",
                "rejected_at": "2026-06-11",
                "reject_basis": "OOS 2026 -70,903 + maxMDD 20.14",
                "train": {"profit": 12319055, "mdd": 6.23, "window": "2023-2025"},
            },
            {
                "label": "REVIVAL EXIT2NA take6",
                "rejected_at": "2026-06-12",
                "reject_basis": "OOS 2026 -288,237 + maxMDD 20.87",
                "train": {"profit": 11230126, "mdd": 6.55, "window": "2023-2025"},
            },
        ]
    }


def _make_card(
    selected=None,
    overfit=None,
    overlap=None,
    yearly=None,
    oos_rows=None,
    regime=None,
    rejected=None,
    now_label="2026-06-12 00:00",
) -> str:
    return compose_card(
        selected=selected if selected is not None else _selected(),
        overfit=overfit if overfit is not None else _overfit(),
        overlap=overlap,
        yearly=yearly,
        oos_rows=oos_rows if oos_rows is not None else _oos_rows(),
        regime=regime,
        rejected=rejected,
        now_label=now_label,
    )


# ---------------------------------------------------------------------------
# compose_card: 전 섹션 헤더 존재
# ---------------------------------------------------------------------------

class TestComposeSections:
    def test_all_section_headers_present(self):
        card = _make_card(overlap=_overlap(), regime=_regime(), rejected=_rejected())
        for expected in [
            "## 0. 자동 조립 공시",
            "## 1. 후보",
            "## 2. 과적합 통계 (V1)",
            "## 3. OOS 연도별 (후보 vs 시드)",
            "## 4. 거래 중복도 (N10 의무)",
            "## 5. 레짐 분해",
            "## 6. 기각된 경로 (N10 의무)",
            "## 7. 비교군 (N10 의무",
            "## 8. 남은 검증",
            "## 9. 최종 결정",
        ]:
            assert expected in card, f"섹션 헤더 누락: {expected!r}"

    def test_draft_mark_in_title(self):
        card = _make_card()
        assert "[DRAFT]" in card

    def test_advisory_disclaimer(self):
        card = _make_card()
        assert "이 초안은 자동 조립" in card
        assert "판정·권고는 사람이 작성" in card


# ---------------------------------------------------------------------------
# compose_card: DRAFT 표기
# ---------------------------------------------------------------------------

class TestDraftLabel:
    def test_draft_in_heading(self):
        card = compose_card(
            selected=_selected(),
            overfit=_overfit(),
            overlap=None,
            yearly=None,
            oos_rows={},
            regime=None,
            rejected=None,
            now_label="2026-06-12 09:00",
        )
        assert "[DRAFT]" in card

    def test_draft_in_footer(self):
        card = _make_card()
        assert "[DRAFT]" in card.split("##")[-1] or "[DRAFT]" in card


# ---------------------------------------------------------------------------
# compose_card: 결측 입력 → "자료 없음"
# ---------------------------------------------------------------------------

class TestMissingInputHandling:
    def test_none_overlap_shows_na(self):
        card = _make_card(overlap=None)
        # 섹션 4가 있고 "자료 없음" 포함
        assert "## 4. 거래 중복도" in card
        assert "자료 없음" in card

    def test_none_regime_shows_na(self):
        card = _make_card(regime=None)
        assert "## 5. 레짐 분해" in card
        assert "자료 없음" in card

    def test_none_rejected_shows_na(self):
        card = _make_card(rejected=None)
        assert "## 6. 기각된 경로" in card
        assert "자료 없음" in card

    def test_empty_oos_rows_shows_na(self):
        card = _make_card(oos_rows={})
        assert "## 3. OOS 연도별" in card
        assert "자료 없음" in card

    def test_all_none_no_exception(self):
        """모든 선택적 입력이 None이어도 예외 없이 문자열 반환."""
        result = compose_card(
            selected={},
            overfit={},
            overlap=None,
            yearly=None,
            oos_rows={},
            regime=None,
            rejected=None,
            now_label="",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_missing_selected_fields_no_exception(self):
        """selected에 필드 없어도 예외 없음."""
        result = compose_card(
            selected={"run_id": "test"},
            overfit={},
            overlap=None,
            yearly=None,
            oos_rows={},
            regime=None,
            rejected=None,
            now_label="",
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# compose_card: N10 의무 필드 5종
# ---------------------------------------------------------------------------

class TestN10MandatoryFields:
    """N10 의무 필드 5종: 비교군 ≥3 · 약세 연도 · 기각된 경로 · 거래 중복도 · 남은 검증."""

    def test_comparison_group_section_exists(self):
        """비교군 ≥3: 섹션 7 헤더"""
        card = _make_card(overlap=_overlap(), regime=_regime(), rejected=_rejected())
        assert "## 7. 비교군 (N10 의무" in card

    def test_comparison_group_has_entries(self):
        """비교군 3개 등재 — eligible_candidates 3개"""
        card = _make_card(overlap=_overlap(), regime=_regime(), rejected=_rejected())
        # gen_no 7, 6, 4 모두 포함
        assert "| 7 |" in card
        assert "| 6 |" in card
        assert "| 4 |" in card

    def test_bear_year_solo_present(self):
        """약세 연도 단독 성과: 약세 연도 행이 카드에 포함"""
        card = _make_card()
        assert "약세 연도" in card

    def test_rejected_paths_section_exists(self):
        """기각된 경로: 섹션 6 헤더"""
        card = _make_card(rejected=_rejected())
        assert "## 6. 기각된 경로 (N10 의무)" in card

    def test_rejected_paths_entries(self):
        """기각된 경로: 등재 항목 포함"""
        card = _make_card(rejected=_rejected())
        assert "EXIT2C" in card
        assert "EXIT2NA" in card

    def test_trade_overlap_section_exists(self):
        """거래 중복도: 섹션 4 헤더"""
        card = _make_card(overlap=_overlap())
        assert "## 4. 거래 중복도 (N10 의무)" in card

    def test_trade_overlap_jaccard(self):
        """거래 중복도: Jaccard 수치 포함"""
        card = _make_card(overlap=_overlap())
        assert "Jaccard" in card
        assert "0.888" in card

    def test_remaining_verification_section_exists(self):
        """남은 검증: 섹션 8 헤더"""
        card = _make_card()
        assert "## 8. 남은 검증" in card

    def test_remaining_verification_template(self):
        """남은 검증: 빈 템플릿 칸 포함"""
        card = _make_card()
        assert "V2 플라시보" in card
        assert "V4 walk-forward" in card
        assert "V5 슬리피지" in card


# ---------------------------------------------------------------------------
# collect_oos_rows: :memory: sqlite 합성 테스트
# ---------------------------------------------------------------------------

def _make_memory_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.execute("""
        CREATE TABLE generations (
            run_id TEXT,
            gen_no INTEGER,
            buy_name TEXT,
            profit REAL,
            mdd REAL,
            trade_count INTEGER
        )
    """)
    rows = [
        ("theta_oos_2022_test", 0, "THETA_B", 2097751.0, 13.75, 55),
        ("theta_oos_2022_test", 1, "THETA_CAND_B", 2500000.0, 12.0, 50),
        ("theta_oos_2026_test", 0, "THETA_B", 164602.0, 14.7, 9),
        ("train_baseline_run", 0, "OTHER_B", 1000000.0, 5.0, 100),
    ]
    con.executemany("INSERT INTO generations VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    return con


class TestCollectOosRows:
    def test_only_oos_runs_collected(self):
        con = _make_memory_db()
        result = collect_oos_rows(con)
        con.close()
        assert "theta_oos_2022_test" in result
        assert "theta_oos_2026_test" in result
        assert "train_baseline_run" not in result

    def test_all_gens_per_run_included(self):
        con = _make_memory_db()
        result = collect_oos_rows(con)
        con.close()
        assert len(result["theta_oos_2022_test"]) == 2

    def test_gen0_row_fields(self):
        con = _make_memory_db()
        result = collect_oos_rows(con)
        con.close()
        gen0 = result["theta_oos_2022_test"][0]
        assert gen0["gen_no"] == 0
        assert gen0["buy_name"] == "THETA_B"
        assert gen0["profit"] == pytest.approx(2097751.0)
        assert gen0["mdd"] == pytest.approx(13.75)
        assert gen0["trade_count"] == 55

    def test_empty_db_returns_empty(self):
        con = sqlite3.connect(":memory:")
        con.execute("""
            CREATE TABLE generations (
                run_id TEXT, gen_no INTEGER, buy_name TEXT,
                profit REAL, mdd REAL, trade_count INTEGER
            )
        """)
        result = collect_oos_rows(con)
        con.close()
        assert result == {}

    def test_custom_pattern(self):
        con = _make_memory_db()
        result = collect_oos_rows(con, run_id_pattern="%2022%")
        con.close()
        assert "theta_oos_2022_test" in result
        assert "theta_oos_2026_test" not in result
