from backtest.backengine_base import BackEngineBase


def _engine_without_runtime() -> BackEngineBase:
    engine = BackEngineBase.__new__(BackEngineBase)
    engine.code = "006740"
    engine.indexn = 0
    engine.dict_set = {"시장미시구조분석": False}
    engine.is_oms = False
    engine.opti_kind = 0
    engine.back_type = "백테스트"
    engine.InitTradeInfo()
    return engine


def test_backtest_high_low_supports_shared_strategy_functions() -> None:
    # Given
    engine = _engine_without_runtime()

    # When
    engine.UpdateHighLow(1234.0)

    # Then
    assert engine._고가미갱신지속틱수() == 0
    assert engine._저가미갱신지속틱수() == 0
    assert engine.high_low == {"006740": [1234.0, 0, 1234.0, 0]}


def test_backtest_high_low_tracks_current_code_extrema() -> None:
    # Given
    engine = _engine_without_runtime()
    engine.UpdateHighLow(1234.0)
    engine.indexn = 3

    # When
    engine.UpdateHighLow(1200.0)

    # Then
    assert engine._고가미갱신지속틱수() == 3
    assert engine._저가미갱신지속틱수() == 0
    assert engine.high_low["006740"] == [1234.0, 0, 1200.0, 3]
