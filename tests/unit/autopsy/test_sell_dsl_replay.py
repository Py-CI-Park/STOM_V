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


def test_replay_skips_points_without_window_history_instead_of_substituting_zero() -> None:
    # Given: 진입 직후에는 최저현재가(4) 창을 채울 과거가 없고, 뒤에서는 채워진다.
    points = tuple(
        _point(20250102090000 + index, price)
        for index, price in enumerate((100, 101, 102, 103, 104, 99))
    )
    # 0.0 대체가 일어나면 "현재가 < 최저현재가(4)" 는 항상 거짓(현재가>0)이어야 하는데,
    #   반대로 최저현재가가 0 이 되는 순간 조건 자체가 무의미해진다 — 어느 쪽도 추정이다.
    code = """매도 = False
if 현재가 < 최저현재가(4, 1):
    매도 = True
if 매도:
    self.Sell()
"""
    result = replay_sell_strategy(
        code=code,
        points=points,
        entry_timestamp=20250102090000,
        boundary_timestamp=20250102090005,
        timeframe=Timeframe.TICK,
        buy_price=100,
        buy_amount=1_000_000,
        actual_exit=ActualExit(20250102090005, 99, -1.0, -10_000, "기존 손절"),
    )

    # Then: 부족 시점은 0.0 평가 대신 건너뛰고 그 수를 공개하며, 창이 채워진 뒤 발동한다.
    assert result.status == "supported"
    assert result.insufficient_points > 0
    assert result.triggered is True
    assert result.exit_timestamp == 20250102090005


def test_replay_reports_insufficient_history_when_no_point_can_be_evaluated() -> None:
    # Given: 어떤 시점에서도 300틱 창을 채울 수 없는 짧은 경로.
    points = tuple(_point(20250102090000 + index, 100 + index) for index in range(5))
    code = """매도 = False
if 현재가 < 이동평균(300):
    매도 = True
if 매도:
    self.Sell()
"""
    result = replay_sell_strategy(
        code=code,
        points=points,
        entry_timestamp=20250102090000,
        boundary_timestamp=20250102090004,
        timeframe=Timeframe.TICK,
        buy_price=100,
        buy_amount=1_000_000,
        actual_exit=ActualExit(20250102090004, 104, 4.0, 40_000, "기존 익절"),
    )

    # Then: 0.0 으로 추정하지 않고 평가 불가 상태를 명시한다.
    assert result.status == "insufficient_history"
    assert result.triggered is False
    assert result.insufficient_points == 5


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
