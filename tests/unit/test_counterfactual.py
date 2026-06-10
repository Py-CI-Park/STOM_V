"""R2·R6(2026-06-11) — 반사실 필터 엔진 + 플라시보 생성기 테스트.

반사실: 강화 필터를 백테 0회로 평가(잔존=부분집합). 총손익이 깎이지 않는 필터만 제안.
플라시보: 결정론 의사난수 진입 베이스라인(생성 가드 통과 필수).
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.fitness.counterfactual import (  # noqa: E402
    FilterSpec,
    evaluate_filters,
    feedback_lines,
    suggest_filters,
    suggestions_payload,
)
from ai_strategy_loop.scripts.gen_placebo_strategy import build_placebo_code  # noqa: E402


def _make_csv(path: Path, rows: list) -> str:
    """rows: [(연도, 수익률, 수익금, 시가총액)]"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "매수시간", "매도시간", "수익률", "수익금", "B_시가총액",
        ])
        w.writeheader()
        for i, (year, pct, krw, cap) in enumerate(rows):
            w.writerow({
                "종목명": "T",
                "매수시간": f"{year}01{(i % 28) + 1:02d}090100",
                "매도시간": f"{year}01{(i % 28) + 1:02d}090300",
                "수익률": pct, "수익금": krw, "B_시가총액": cap,
            })
    return str(path)


@pytest.fixture
def cap_loser_csv(tmp_path) -> str:
    """고시총 거래가 순손실인 구조: cap<=저시총 필터가 손익을 늘려야 한다."""
    rows = []
    for i in range(25):
        rows.append(("2023", 1.0, 100000, 1000 + i * 10))   # 저시총 승자 25
    for i in range(15):
        rows.append(("2024", -1.0, -80000, 5000 + i * 10))  # 고시총 패자 15
    for i in range(5):
        rows.append(("2024", 0.5, 30000, 5200 + i * 10))    # 고시총 소수 승자 5
    return _make_csv(tmp_path / "bt.csv", rows)


class TestEvaluateFilters:
    def test_math_and_yearly(self, cap_loser_csv) -> None:
        cf = evaluate_filters(cap_loser_csv, [FilterSpec("B_시가총액", "<=", 2000)])
        assert cf is not None
        assert cf.base_trades == 45
        assert cf.kept_trades == 25
        assert cf.kept_profit == 25 * 100000
        assert cf.cut_net_profit == (-80000 * 15 + 30000 * 5)
        assert cf.profit_ratio > 1.0
        years = {y.year: y for y in cf.yearly}
        assert years["2023"].kept_trades == 25
        assert years["2024"].kept_trades == 0

    def test_and_combination(self, cap_loser_csv) -> None:
        cf = evaluate_filters(cap_loser_csv, [
            FilterSpec("B_시가총액", "<=", 2000),
            FilterSpec("B_시가총액", ">=", 1100),
        ])
        assert cf is not None
        assert cf.kept_trades == 15  # 1100 <= cap <= 2000 → i>=10 인 승자 15개.

    def test_graceful_on_bad_input(self, cap_loser_csv) -> None:
        assert evaluate_filters("no_such.csv", [FilterSpec("B_시가총액", "<=", 1)]) is None
        assert evaluate_filters(cap_loser_csv, []) is None
        assert evaluate_filters(cap_loser_csv, [FilterSpec("없는컬럼", "<=", 1)]) is None
        assert evaluate_filters(cap_loser_csv, [FilterSpec("B_시가총액", "==", 1)]) is None


class TestSuggestFilters:
    def test_finds_profit_preserving_upper_bound(self, cap_loser_csv) -> None:
        out = suggest_filters(cap_loser_csv, top_k=3, min_kept_trades=10)
        assert out, "고시총 순손실 구조에서 상한 필터를 찾아야 한다"
        best = out[0]
        assert best["feature"] == "B_시가총액"
        assert best["op"] == "<="
        assert best["profit_ratio"] >= 1.0
        assert best["kept_trades"] >= 10
        assert best["recent_year"] is not None

    def test_profit_losing_filters_excluded(self, tmp_path) -> None:
        # 모든 거래가 흑자 → 어떤 강화 필터든 손익을 깎는다 → 제안 0(비율<1 배제).
        rows = [("2023", 1.0, 100000, 1000 + i * 100) for i in range(30)]
        csv_path = _make_csv(tmp_path / "all_win.csv", rows)
        out = suggest_filters(csv_path, top_k=5, min_kept_trades=5)
        for s in out:
            assert s["profit_ratio"] >= 1.0

    def test_graceful_on_missing_csv(self) -> None:
        assert suggest_filters("no_such.csv") == []
        assert suggestions_payload("no_such.csv") == {"suggestions": [], "count": 0}


class TestFeedbackLines:
    def test_lines_contain_numbers_and_caveat(self, cap_loser_csv) -> None:
        lines = feedback_lines(suggest_filters(cap_loser_csv, min_kept_trades=10))
        assert lines
        assert "인샘플" in lines[0]
        assert any("B_시가총액 <=" in ln for ln in lines)
        assert any("총손익" in ln for ln in lines)

    def test_empty_suggestions_yield_no_lines(self) -> None:
        assert feedback_lines([]) == []


class TestLoopWiring:
    def test_counterfactual_feedback_toggle(self, cap_loser_csv) -> None:
        from ai_strategy_loop.controller.loop import _default_autopsy_fn

        off = _default_autopsy_fn(LoopConfig.from_dict({"min_trades": 10}))(cap_loser_csv)
        on = _default_autopsy_fn(LoopConfig.from_dict({
            "min_trades": 10, "counterfactual_feedback_enabled": True,
        }))(cap_loser_csv)
        assert "반사실" not in (off or "")
        assert "반사실 검증된 필터 후보" in (on or "")

    def test_config_default_off_and_spec(self) -> None:
        from ai_strategy_loop.launch_config import config_field_specs

        assert LoopConfig().counterfactual_feedback_enabled is False
        names = {f["name"] for f in config_field_specs()}
        assert "counterfactual_feedback_enabled" in names


class TestPlaceboGenerator:
    def test_code_compiles_and_passes_guards(self) -> None:
        from ai_strategy_loop.brain.token_check import check_tokens
        from ai_strategy_loop.brain.variable_scope import check_variable_scope

        code = build_placebo_code(rate=5, start=90030, end=92000, shift=3)
        compile(code, "<string>", "exec")
        ok, msg = check_tokens(code)
        assert ok, msg
        ok, missing = check_variable_scope(code, "tick", "buy")
        assert ok, missing
        assert "% 1000 < 5" in code
        assert "90030 <= 시분초 < 92000" in code

    def test_deterministic(self) -> None:
        assert build_placebo_code(5, 90030, 92000) == build_placebo_code(5, 90030, 92000)
