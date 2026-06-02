"""S0: _build_warm_btconfig의 timeframe+full_session 인지 end_time 선택 검증(백테 실행 0).

OFF(기본)=byte-identical(end_time=92800), min+full_session_enabled=풀세션 151900,
tick은 토글과 무관(항상 bt_universe_end_time). start_time은 항상 90000.
"""
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller import loop as L


def _bt(**kw):
    return L._build_warm_btconfig(LoopConfig(**kw))


class TestWarmSessionWindow:
    def test_default_off_byte_identical_min(self):
        bt = _bt(bt_timeframe="min")
        assert bt.end_time == 92800
        assert bt.start_time == 90000

    def test_default_off_byte_identical_tick(self):
        bt = _bt(bt_timeframe="tick")
        assert bt.end_time == 92800
        assert bt.start_time == 90000

    def test_min_full_session_opens_end_time(self):
        bt = _bt(bt_timeframe="min", full_session_enabled=True)
        assert bt.end_time == 151900
        assert bt.start_time == 90000

    def test_tick_ignores_full_session_toggle(self):
        bt = _bt(bt_timeframe="tick", full_session_enabled=True)
        assert bt.end_time == 92800

    def test_custom_min_end_time_respected(self):
        bt = _bt(bt_timeframe="min", full_session_enabled=True,
                 bt_min_universe_end_time=150000)
        assert bt.end_time == 150000
