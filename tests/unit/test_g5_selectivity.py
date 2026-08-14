"""G5 선택도 사다리 검증 — 격자 고정과 렌더 파라미터화만 본다.

사전 등록: docs/research/quant_scoring_pipeline/2026-08-13_G5_사전등록.md
"""

import ast

import pytest

from ai_strategy_loop.labeling.run_g2_assemble import BANDS, render_strategy
from ai_strategy_loop.labeling.run_g5_selectivity import (
    CELL_TIMEOUT, CELLS, cell_names)

SEEDS = [
    {"time_segment": "0900-0905", "features": {
        "등락율": {"q25": 2.05, "q50": 4.91, "q75": 9.26},
        "회전율": {"q25": 0.52, "q50": 1.4, "q75": 3.38}}},
    {"time_segment": "0905-0910", "features": {
        "등락율": {"q25": 3.42, "q50": 7.39, "q75": 12.99}}},
    {"time_segment": "0910-0915", "features": {
        "등락율": {"q25": 4.15, "q50": 8.21, "q75": 13.9}}},
]


class TestPrereg:
    def test_격자는_3셀_고정(self):
        assert cell_names() == ["Q50_ALL", "Q50_BAND1", "Q75_ALL"]

    def test_셀_상한은_90분(self):
        assert CELL_TIMEOUT == 5400

    def test_밴드1_셀은_밴드가_하나다(self):
        bands = {name: b for name, _, b in CELLS}
        assert len(bands["Q50_BAND1"]) == 1
        assert len(bands["Q50_ALL"]) == len(BANDS) == 3

    def test_분위_수위(self):
        quantiles = {name: q for name, q, _ in CELLS}
        assert quantiles == {"Q50_ALL": "q50", "Q50_BAND1": "q50",
                             "Q75_ALL": "q75"}


class TestRenderParams:
    def test_기본값은_G2_와_동일하다(self):
        """G2 산출이 바뀌지 않아야 한다(기존 라운드 재현성)."""
        assert render_strategy(SEEDS, "LOWER") == render_strategy(
            SEEDS, "LOWER", quantile="q25", bands=BANDS)

    @pytest.mark.parametrize("quantile,expected", [
        ("q25", "등락율 >= 2.05"), ("q50", "등락율 >= 4.91"),
        ("q75", "등락율 >= 9.26")])
    def test_분위_수위가_문턱에_반영된다(self, quantile, expected):
        code = render_strategy(SEEDS, "LOWER", quantile=quantile)
        assert expected in code
        ast.parse(code)

    def test_밴드를_하나로_줄일_수_있다(self):
        code = render_strategy(SEEDS, "LOWER", quantile="q50", bands=BANDS[:1])
        assert "90000 <= 시분초 < 90500" in code
        assert "90500 <= 시분초 < 91000" not in code
        ast.parse(code)

    def test_밴드가_비면_거부(self):
        with pytest.raises(ValueError, match="시간밴드가 비었다"):
            render_strategy(SEEDS, "LOWER", bands=[])

    def test_수위가_없는_피처는_건너뛴다(self):
        seeds = [{"time_segment": "0900-0905",
                  "features": {"등락율": {"q25": 1.0}}}]     # q50 없음
        code = render_strategy(seeds, "LOWER", quantile="q50")
        ast.parse(code)
        assert "등락율" not in code

    @pytest.mark.parametrize("name,quantile,bands", CELLS)
    def test_전_셀이_구문상_유효하다(self, name, quantile, bands):
        code = render_strategy(SEEDS, "LOWER", quantile=quantile, bands=bands)
        ast.parse(code)
        assert "시가총액 < 1000" in code        # 세그먼트 유지
        assert "관심종목 == 1" in code          # 안전절 유지
