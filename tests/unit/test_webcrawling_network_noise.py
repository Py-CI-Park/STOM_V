from threading import Lock

import requests
import utility.webcrawling as webcrawling_module


class _SignalStub:
    def __init__(self):
        self.messages = []

    def emit(self, payload):
        self.messages.append(payload)


def _build_crawler():
    crawler = webcrawling_module.WebCrawling.__new__(webcrawling_module.WebCrawling)
    crawler.signal = _SignalStub()
    crawler.thread_lock = Lock()
    crawler.warning_lock = Lock()
    crawler.warning_state = {}
    crawler.warning_cooldown = 60
    crawler.thread_join = 0
    crawler.dict_data = {'BTC/USDT': 'old-data'}
    return crawler


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


def test_run_network_job_keeps_existing_data_and_marks_completion(monkeypatch):
    crawler = _build_crawler()
    monkeypatch.setattr(webcrawling_module.time, 'time', lambda: 100.0)

    def boom():
        raise requests.exceptions.ReadTimeout()

    result = webcrawling_module.WebCrawling._run_network_job(crawler, '바이낸스 데이터', 'BTC/USDT', boom)

    assert result is None
    assert crawler.dict_data['BTC/USDT'] == 'old-data'
    assert crawler.thread_join == 1
    assert crawler.signal.messages == [
        (webcrawling_module.ui_num['시스템로그'], '바이낸스 데이터 갱신 실패(BTC/USDT): ReadTimeout')
    ]
