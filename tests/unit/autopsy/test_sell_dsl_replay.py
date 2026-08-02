from ai_strategy_loop.autopsy.sell_dsl_replay import replay_sell_strategy
from ai_strategy_loop.autopsy.trade_path_models import ActualExit, MarketPoint, Timeframe


def _point(timestamp: int, price: float, minute_open: float = 100.0) -> MarketPoint:
    return MarketPoint(timestamp=timestamp, price=price, minute_open=minute_open)


def test_replay_respects_minute_hold_unit_and_first_elif_trigger() -> None:
    points = (
        _point(202501020900, 100),
        _point(202501020901, 101),
        _point(202501020902, 102),
        _point(202501020903, 103),
        _point(202501020904, 98),
        _point(202501020905, 97),
    )
    code = """시가대비등락율 = ((현재가 - 분봉시가) / 분봉시가) * 100
매도 = False
if 보유시간 > 10 and 현재가 < 최저현재가(3, 보유시간):
    매도 = True
elif 보유시간 >= 2 and 수익률 <= -2:
    매도 = True
elif 수익률 >= 2:
    매도 = True
if 매도:
    self.Sell()
"""

    result = replay_sell_strategy(
        code=code,
        points=points,
        entry_timestamp=202501020902,
        boundary_timestamp=202501020905,
        timeframe=Timeframe.MIN,
        buy_price=102,
        buy_amount=1_000_000,
        actual_exit=ActualExit(202501020905, 97, -5.0, -50_000, "기존 손절"),
    )

    assert result.status == "supported"
    assert result.triggered is True
    assert result.exit_timestamp == 202501020904
    assert result.rule_order == 2
    assert "보유시간 >= 2" in result.condition
    assert result.delta_profit_krw > 0


def test_replay_uses_pre_entry_history_for_stom_window_functions() -> None:
    points = tuple(
        _point(20250102090000 + index, price)
        for index, price in enumerate((100, 101, 102, 103, 99, 98))
    )
    code = """매도 = False
if 보유시간 >= 1 and 현재가 < 최저현재가(3, 보유시간):
    매도 = True
if 매도:
    self.Sell()
"""

    result = replay_sell_strategy(
        code=code,
        points=points,
        entry_timestamp=20250102090003,
        boundary_timestamp=20250102090005,
        timeframe=Timeframe.TICK,
        buy_price=103,
        buy_amount=1_000_000,
        actual_exit=ActualExit(20250102090005, 98, -5.0, -50_000, "기존 손절"),
    )

    assert result.status == "supported"
    assert result.exit_timestamp == 20250102090004
    assert result.rule_order == 1


def test_replay_never_guesses_an_unsupported_stom_function() -> None:
    code = """매도 = False
if 사용자정의미지원함수(30) and 수익률 < 0:
    매도 = True
if 매도:
    self.Sell()
"""
    result = replay_sell_strategy(
        code=code,
        points=(_point(20250102090000, 100), _point(20250102090001, 99)),
        entry_timestamp=20250102090000,
        boundary_timestamp=20250102090001,
        timeframe=Timeframe.TICK,
        buy_price=100,
        buy_amount=1_000_000,
        actual_exit=ActualExit(20250102090001, 99, -1.0, -10_000, "기존 손절"),
    )

    assert result.status == "unsupported"
    assert result.triggered is False
    assert result.unsupported == ("사용자정의미지원함수",)
