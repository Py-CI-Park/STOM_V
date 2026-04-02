from threading import Lock

import pandas as pd
import requests

import utility.static as static_module
import utility.webcrawling as webcrawling_module


class _SignalStub:
    def __init__(self):
        self.messages = []

    def emit(self, payload):
        self.messages.append(payload)


class _ResponseStub:
    def __init__(self, json_data=None, text=''):
        self._json_data = json_data or []
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._json_data


def _build_crawler():
    crawler = webcrawling_module.WebCrawling.__new__(webcrawling_module.WebCrawling)
    crawler.signal = _SignalStub()
    crawler.thread_lock = Lock()
    crawler.warning_lock = Lock()
    crawler.warning_state = {}
    crawler.warning_cooldown = 60
    crawler.thread_join = 0
    crawler.network_timeout = 10
    crawler.base_url = 'https://finance.naver.com'
    crawler.headers = {}
    crawler.dict_data = {'BTC/USDT': 'old-data'}
    return crawler


def _run_threaded_entrypoint_synchronously(monkeypatch, crawler, method_name):
    wrapper = getattr(webcrawling_module.WebCrawling, method_name)
    closure_values = [cell.cell_contents for cell in (wrapper.__closure__ or ())]
    callable_values = [value for value in closure_values if callable(value)]

    if callable_values:
        callable_values[-1](crawler)
        return

    class _ImmediateThread:
        def __init__(self, target=None, args=(), daemon=None):
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    if hasattr(static_module, 'Thread'):
        monkeypatch.setattr(static_module, 'Thread', _ImmediateThread, raising=False)
        getattr(crawler, method_name)()
        return

    raise AssertionError(f'Unable to run threaded entrypoint synchronously: {method_name}')


def test_emit_network_warning_throttles_duplicate_messages(monkeypatch):
    crawler = _build_crawler()
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: 100.0)

    webcrawling_module.WebCrawling._emit_network_warning(
        crawler, '바이낸스 데이터', 'BTC/USDT', requests.exceptions.ReadTimeout()
    )
    webcrawling_module.WebCrawling._emit_network_warning(
        crawler, '바이낸스 데이터', 'BTC/USDT', requests.exceptions.ReadTimeout()
    )

    assert crawler.signal.messages == [
        (webcrawling_module.ui_num['시스템로그'], '바이낸스 데이터 갱신 실패(BTC/USDT): ReadTimeout')
    ]


def test_run_network_job_does_not_advance_completion(monkeypatch):
    crawler = _build_crawler()
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: 100.0)

    def boom():
        raise requests.exceptions.ReadTimeout()

    result = webcrawling_module.WebCrawling._run_network_job(crawler, '바이낸스 데이터', 'BTC/USDT', boom)

    assert result is None
    assert crawler.dict_data['BTC/USDT'] == 'old-data'
    assert crawler.thread_join == 0
    assert crawler.signal.messages == [
        (webcrawling_module.ui_num['시스템로그'], '바이낸스 데이터 갱신 실패(BTC/USDT): ReadTimeout')
    ]


def test_get_market_indicator_failure_keeps_existing_data_and_counts_completion(monkeypatch):
    crawler = _build_crawler()
    crawler.dict_data = {'환율': pd.DataFrame({'time': [1], 'price': [1000.0], 'change': [0.0]})}

    class _SessionStub:
        def get(self, *args, **kwargs):
            raise requests.exceptions.ConnectTimeout()

    crawler.session = _SessionStub()
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: 100.0)

    crawler._get_market_indicator()

    assert crawler.dict_data['환율'].equals(pd.DataFrame({'time': [1], 'price': [1000.0], 'change': [0.0]}))
    assert crawler.thread_join == 3
    assert crawler.signal.messages == [
        (webcrawling_module.ui_num['시스템로그'], '시장지표 갱신 실패(환율): ConnectTimeout'),
        (webcrawling_module.ui_num['시스템로그'], '시장지표 갱신 실패(휘발유): ConnectTimeout'),
        (webcrawling_module.ui_num['시스템로그'], '시장지표 갱신 실패(국제금): ConnectTimeout'),
    ]


def test_public_get_market_indicator_failure_preserves_data_and_completion(monkeypatch):
    crawler = _build_crawler()
    existing = pd.DataFrame({'time': [1], 'price': [1000.0], 'change': [0.0]})
    crawler.dict_data = {'환율': existing}

    class _SessionStub:
        def get(self, *args, **kwargs):
            raise requests.exceptions.ConnectTimeout()

    crawler.session = _SessionStub()
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: 100.0)
    _run_threaded_entrypoint_synchronously(monkeypatch, crawler, 'get_market_indicator')

    assert crawler.dict_data['환율'] is existing
    assert crawler.thread_join == 3
    assert crawler.signal.messages == [
        (webcrawling_module.ui_num['시스템로그'], '시장지표 갱신 실패(환율): ConnectTimeout'),
        (webcrawling_module.ui_num['시스템로그'], '시장지표 갱신 실패(휘발유): ConnectTimeout'),
        (webcrawling_module.ui_num['시스템로그'], '시장지표 갱신 실패(국제금): ConnectTimeout'),
    ]


def test_get_crypto_data_success_clears_warning_and_failure_warns_again(monkeypatch):
    crawler = _build_crawler()
    times = iter([100.0] * 8 + [200.0] * 8)
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: next(times))

    def fail_request(*args, **kwargs):
        raise requests.exceptions.ReadTimeout()

    monkeypatch.setattr(webcrawling_module.requests, 'get', fail_request)
    crawler._get_crypto_data()

    sample_klines = [[1710000000000, '0', '0', '0', '100.0', '0']]
    monkeypatch.setattr(webcrawling_module.requests, 'get', lambda *args, **kwargs: _ResponseStub(sample_klines))
    crawler._get_crypto_data()

    monkeypatch.setattr(webcrawling_module.requests, 'get', fail_request)
    crawler._get_crypto_data()

    btc_messages = [payload for payload in crawler.signal.messages if '(BTC/USDT)' in payload[1]]
    assert len(btc_messages) == 2
    assert crawler.dict_data['BTC/USDT'].iloc[0]['price'] == 100.0
    assert crawler.thread_join == 24


def test_get_korean_stocks_failure_keeps_existing_data_and_counts_completion(monkeypatch):
    crawler = _build_crawler()
    existing = pd.DataFrame({'time': [1], 'price': [100.0], 'gap': [0.0], 'change': [0.0]})
    crawler.dict_data = {'코스피': existing}

    class _SessionStub:
        def get(self, *args, **kwargs):
            raise requests.exceptions.ReadTimeout()

    crawler.session = _SessionStub()
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: 100.0)

    crawler._get_korean_stocks('20240101', '20240101120000', '코스피', 'KOSPI')

    assert crawler.dict_data['코스피'] is existing
    assert crawler.thread_join == 1
    assert crawler.signal.messages == [
        (webcrawling_module.ui_num['시스템로그'], '국내지수 갱신 실패(코스피): ReadTimeout')
    ]
