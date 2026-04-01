import utility.static as static
import pytest
from pathlib import Path


def test_static_exports_summer_time_compat_symbol():
    assert hasattr(static, 'summer_time'), 'ui_process_starter 호환을 위해 summer_time 심볼이 필요합니다.'
    assert isinstance(static.summer_time, int), 'summer_time은 DST 오프셋 정수값이어야 합니다.'


def test_static_exports_get_profile_text_compat_symbol():
    assert hasattr(static, 'get_profile_text'), 'kiwoom 계열 import 호환을 위해 get_profile_text 심볼이 필요합니다.'


def test_kiwoom_trader_import_succeeds_with_static_compat():
    import importlib

    module = importlib.import_module('trade.stock_korea.kiwoom_trader')
    assert hasattr(module, 'KiwoomTrader')


def test_read_key_does_not_rotate_key_when_encrypted_payload_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(static, 'reg', None)
    monkeypatch.setattr(static, 'KEY_FALLBACK_FILE', str(tmp_path / 'en_key.txt'))
    monkeypatch.setattr(static, '_setting_db_has_encrypted_payload', lambda: True)

    def fail_write_key():
        raise AssertionError('write_key should not be called when encrypted payload exists')

    monkeypatch.setattr(static, 'write_key', fail_write_key)

    with pytest.raises(RuntimeError):
        static.read_key()


def test_database_check_does_not_unconditionally_rotate_key_after_read_failure():
    text = Path('utility/database_check.py').read_text(encoding='utf-8')

    assert 'write_key()' in text
    assert 'except RuntimeError:' in text, 'encrypted payload이 있는 경우는 새 키 생성 대신 그대로 실패시켜야 합니다.'


def test_get_kiwoom_pg_sg_sp_preserves_negative_loss_amount():
    pg, sg, _ = static.GetKiwoomPgSgSp(100000, 99900)

    assert sg == pg - 100000
