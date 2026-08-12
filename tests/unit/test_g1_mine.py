"""G1 채굴 러너의 순수 로직 검증 — DB·채굴 없이 우주 제약과 게이트만 본다.

사전 등록: docs/research/quant_scoring_pipeline/2026-08-12_G1_사전등록.md
"""

import sqlite3

import pytest

from ai_strategy_loop.labeling.run_g1_mine import (
    GATE_MIN_COUNT, GATE_MIN_LIFT, GATE_MIN_WINNERS, LOOKAHEAD_TICKS,
    SEED_BUDGET, THRESHOLD_PCT, WINDOW_HI, WINDOW_LO, apply_gate,
    watchlist_codes)


class TestPreregConstants:
    """사전 등록 §4 의 값이 코드에 그대로 박혀 있어야 한다(사후 조정 방지)."""

    def test_창은_사용자_확정_09시_09시20분(self):
        assert (WINDOW_LO, WINDOW_HI) == (90000, 92000)

    def test_승자_정의(self):
        assert LOOKAHEAD_TICKS == 300
        assert THRESHOLD_PCT == 5.0     # 모듈 기본 10.0 에서 의도적 이탈

    def test_게이트와_예산(self):
        assert (GATE_MIN_COUNT, GATE_MIN_LIFT, GATE_MIN_WINNERS) == (200, 1.30, 30)
        assert SEED_BUDGET == 8


@pytest.fixture
def con():
    con = sqlite3.connect(":memory:")
    con.execute('CREATE TABLE moneytop ("index" INTEGER, 거래대금순위 TEXT)')
    day = 20220323
    con.executemany('INSERT INTO moneytop VALUES (?, ?)', [
        (day * 1_000_000 + 85959, "999999"),          # 창 이전 — 제외
        (day * 1_000_000 + 90100, "000001;000002"),
        (day * 1_000_000 + 91500, "000002;000003"),
        (day * 1_000_000 + 92001, "888888"),          # 창 이후 — 제외
    ])
    return con


class TestWatchlist:
    def test_창_안_종목만_모은다(self, con):
        codes = watchlist_codes(con, 20220323, {"000001", "000002", "000003",
                                                "999999", "888888"})
        assert codes == ["000001", "000002", "000003"]

    def test_DB에_테이블이_없는_종목은_뺀다(self, con):
        codes = watchlist_codes(con, 20220323, {"000001"})
        assert codes == ["000001"]

    def test_다른_날은_비어_있다(self, con):
        assert watchlist_codes(con, 20220324, {"000001"}) == []

    def test_중복은_한_번만(self, con):
        codes = watchlist_codes(con, 20220323, {"000002"})
        assert codes == ["000002"]


def _cell(**over):
    cell = {"time_segment": "09:00~09:05", "market_cap_segment": "소형",
            "count": 1000, "winner_count": 50, "lift": 1.5}
    cell.update(over)
    return cell


class TestGate:
    def test_전부_충족하면_통과(self):
        assert len(apply_gate([_cell()])) == 1

    def test_표본_미달은_탈락(self):
        assert apply_gate([_cell(count=GATE_MIN_COUNT - 1)]) == []

    def test_lift_미달은_탈락(self):
        assert apply_gate([_cell(lift=1.29)]) == []

    def test_승자_수_미달은_탈락(self):
        assert apply_gate([_cell(winner_count=GATE_MIN_WINNERS - 1)]) == []

    def test_lift_None_은_탈락(self):
        assert apply_gate([_cell(lift=None)]) == []

    def test_시간대당_하나만_고른다(self):
        cells = [_cell(market_cap_segment="소형", lift=2.0),
                 _cell(market_cap_segment="중형", lift=1.8),
                 _cell(market_cap_segment="대형", lift=1.5)]
        seeds = apply_gate(cells)
        assert len(seeds) == 1
        assert seeds[0]["market_cap_segment"] == "소형"   # lift 최고

    def test_시간대가_다르면_각각_고른다(self):
        cells = [_cell(time_segment="09:00~09:05", lift=2.0),
                 _cell(time_segment="09:05~09:10", lift=1.8)]
        assert len(apply_gate(cells)) == 2

    def test_예산을_넘지_않는다(self):
        cells = [_cell(time_segment=f"seg{i}", lift=2.0 - i * 0.01)
                 for i in range(20)]
        assert len(apply_gate(cells)) == SEED_BUDGET

    def test_lift_내림차순으로_고른다(self):
        cells = [_cell(time_segment="a", lift=1.4),
                 _cell(time_segment="b", lift=1.9)]
        assert [s["time_segment"] for s in apply_gate(cells)] == ["b", "a"]

    def test_빈_입력(self):
        assert apply_gate([]) == []
