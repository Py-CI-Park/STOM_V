import sys
import types

import pytest


if 'utility.lazy_imports' not in sys.modules:
    fake_lazy_imports = types.ModuleType('utility.lazy_imports')
    fake_lazy_imports.get_np = lambda: None
    fake_lazy_imports.get_pd = lambda: None
    fake_lazy_imports.get_talib_stream = lambda: None
    sys.modules['utility.lazy_imports'] = fake_lazy_imports

import utility.static as static_module


def test_error_decorator_reraises_system_exit(monkeypatch):
    @static_module.error_decorator
    def wrapped():
        raise SystemExit()

    with pytest.raises(SystemExit):
        wrapped()


def test_error_decorator_returns_none_for_regular_exception():
    @static_module.error_decorator
    def wrapped():
        raise ValueError('boom')

    assert wrapped() is None
