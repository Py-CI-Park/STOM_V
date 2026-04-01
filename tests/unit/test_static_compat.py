import utility.static as static


def test_static_exports_summer_time_compat_symbol():
    assert hasattr(static, 'summer_time'), 'ui_process_starter 호환을 위해 summer_time 심볼이 필요합니다.'
    assert isinstance(static.summer_time, int), 'summer_time은 DST 오프셋 정수값이어야 합니다.'


def test_static_exports_get_profile_text_compat_symbol():
    assert hasattr(static, 'get_profile_text'), 'kiwoom 계열 import 호환을 위해 get_profile_text 심볼이 필요합니다.'


def test_kiwoom_trader_import_succeeds_with_static_compat():
    import importlib

    module = importlib.import_module('trade.stock_korea.kiwoom_trader')
    assert hasattr(module, 'KiwoomTrader')
