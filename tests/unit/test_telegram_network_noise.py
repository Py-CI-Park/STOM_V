import asyncio
from threading import Lock
from types import SimpleNamespace

import httpx

from utility.setting_base import ui_num
from utility.telegram_bot import TelegramBot


class _QueueStub(list):
    def put(self, item):
        self.append(item)


def _build_bot():
    bot = TelegramBot.__new__(TelegramBot)
    bot.windowQ = _QueueStub()
    bot.warning_lock = Lock()
    bot.warning_state = {}
    bot.warning_cooldown = 60
    return bot


def test_is_transient_network_error_matches_dns_and_timeout():
    bot = _build_bot()

    assert TelegramBot._is_transient_network_error(
        bot, RuntimeError('httpx.ConnectError: [Errno 11001] getaddrinfo failed')
    )
    assert TelegramBot._is_transient_network_error(bot, httpx.ConnectTimeout(''))
    assert TelegramBot._is_transient_network_error(bot, TimeoutError('timed out'))
    assert TelegramBot._is_transient_network_error(bot, RuntimeError('timedout while connecting'))
    assert TelegramBot._is_transient_network_error(
        bot, OSError('[WinError 10065] 연결된 호스트로의 통신 작업에 실패했습니다')
    )
    assert TelegramBot._is_transient_network_error(bot, RuntimeError('ReadTimeoutError: HTTPSConnectionPool(...)'))
    assert TelegramBot._is_transient_network_error(bot, RuntimeError('NetworkError: httpx.ConnectError'))
    assert not TelegramBot._is_transient_network_error(bot, RuntimeError('ValueError: local bug'))


def test_emit_network_warning_throttles_duplicate_messages(monkeypatch):
    import utility.telegram_bot as telegram_bot_module

    bot = _build_bot()
    monkeypatch.setattr(telegram_bot_module, 'time', SimpleNamespace(time=lambda: 100.0), raising=False)

    TelegramBot._emit_network_warning(bot, '텔레그램 봇 시작', TimeoutError('timed out'))
    TelegramBot._emit_network_warning(bot, '텔레그램 봇 시작', TimeoutError('timed out'))

    assert bot.windowQ == [
        (ui_num['시스템로그'], '텔레그램 봇 시작 실패: TimeoutError')
    ]


def test_handle_bot_exception_routes_transient_and_non_transient_paths(monkeypatch):
    import utility.telegram_bot as telegram_bot_module

    bot = _build_bot()
    monkeypatch.setattr(telegram_bot_module, 'time', SimpleNamespace(time=lambda: 100.0), raising=False)

    TelegramBot._handle_bot_exception(bot, '텔레그램 봇 시작', TimeoutError('timed out'))
    TelegramBot._handle_bot_exception(bot, '텔레그램 봇 시작', RuntimeError('ValueError: local bug'))

    assert bot.windowQ[0] == (
        ui_num['시스템로그'], '텔레그램 봇 시작 실패: TimeoutError'
    )
    assert bot.windowQ[1][0] == ui_num['시스템로그']
    assert '오류 알림 - 텔레그램 봇 시작' in bot.windowQ[1][1]
    assert 'ValueError: local bug' in bot.windowQ[1][1]


def test_start_bot_emits_transient_warning_without_traceback(monkeypatch):
    import utility.telegram_bot as telegram_bot_module

    class _AppStub:
        async def initialize(self):
            raise httpx.ConnectTimeout('')

    bot = _build_bot()
    bot.application = _AppStub()
    bot.running = True
    monkeypatch.setattr(telegram_bot_module, 'time', SimpleNamespace(time=lambda: 100.0), raising=False)

    asyncio.run(TelegramBot.start_bot(bot))

    assert len(bot.windowQ) == 1
    assert bot.windowQ[0] == (ui_num['시스템로그'], 'start_bot 실패: ConnectTimeout')
    assert 'Traceback' not in bot.windowQ[0][1]
    assert bot.running is False
