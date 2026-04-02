import sys
import types

import pytest


if 'utility.lazy_imports' not in sys.modules:
    fake_lazy_imports = types.ModuleType('utility.lazy_imports')
    fake_lazy_imports.get_np = lambda: None
    fake_lazy_imports.get_talib_stream = lambda: None
    sys.modules['utility.lazy_imports'] = fake_lazy_imports

import utility.static as static_module


def test_error_decorator_reraises_system_exit(monkeypatch):
    calls = []
    monkeypatch.setattr(static_module, 'print_exc', lambda: calls.append('printed'))

    @static_module.error_decorator
    def wrapped():
        raise SystemExit()

    with pytest.raises(SystemExit):
        wrapped()

    assert calls == []


def test_error_decorator_logs_regular_exception_and_returns_none(monkeypatch):
    calls = []
    monkeypatch.setattr(static_module, 'print_exc', lambda: calls.append('printed'))

    @static_module.error_decorator
    def wrapped():
        raise ValueError('boom')

    assert wrapped() is None
    assert calls == ['printed']
