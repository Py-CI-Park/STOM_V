
import asyncio
from traceback import format_exc
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import UI_NUM
from binance import AsyncClient, BinanceSocketManager


class BinanceWebSocketReceiver(QThread):
    """바이낸스 웹소켓 수신 스레드 클래스입니다.
    바이낸스 시장 데이터를 웹소켓으로 수신합니다.
    """
    signal = pyqtSignal(dict)

    def __init__(self, codes, windowQ):
        super().__init__()
        self.codes        = codes
        self.windowQ      = windowQ
        self.loop         = None
        self.wsk_trade    = None
        self.wsk_depth    = None
        self.async_client = None
        self.sock_manager = None
        self.con_trade    = False
        self.con_depth    = False

        self.trade_stream_list = []
        self.depth_stream_list = []
        for code in self.codes:
            self.trade_stream_list.append(f'{code.lower()}@aggTrade')
            self.depth_stream_list.append(f'{code.lower()}@depth10')

    def run(self):
        """웹소켓 루프를 실행합니다."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.run_trade())
        self.loop.create_task(self.run_order())
        self.loop.run_forever()

    async def run_trade(self):
        """거래 데이터를 수신합니다."""
        while True:
            try:
                if not self.con_trade:
                    await self.connect_trader()
                await self.receive_trader()
            except Exception:
                self.windowQ.put(
                    (UI_NUM['시스템로그'], f'{format_exc()}오류 알림 - 바이낸스 웹소켓 체결 수신 중 오류가 발생하여 재연결합니다.')
                )

            self.con_trade = False
            await asyncio.sleep(1)

    async def run_order(self):
        """주문 데이터를 수신합니다."""
        while True:
            try:
                if not self.con_depth:
                    await self.connect_order()
                await self.receive_order()
            except Exception:
                self.windowQ.put(
                    (UI_NUM['시스템로그'], f'{format_exc()}오류 알림 - 바이낸스 웹소켓 호가 수신 중 오류가 발생하여 재연결합니다.')
                )

            self.con_depth = False
            await asyncio.sleep(1)

    async def connect_trader(self):
        """거래 웹소켓에 연결합니다."""
        if self.wsk_trade:
            try:
                await self.wsk_trade.__aexit__(None, None, None)
            except:
                pass

        if self.async_client is None:
            self.async_client = await AsyncClient.create()
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=10000)

        self.wsk_trade = self.sock_manager.futures_multiplex_socket(self.trade_stream_list, category='market')
        self.con_trade = True

    async def connect_order(self):
        """주문 웹소켓에 연결합니다."""
        if self.wsk_depth:
            try:
                await self.wsk_depth.__aexit__(None, None, None)
            except:
                pass

        if self.async_client is None:
            self.async_client = await AsyncClient.create()
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=10000)

        self.wsk_depth = self.sock_manager.futures_multiplex_socket(self.depth_stream_list, category='public')
        self.con_depth = True

    async def receive_trader(self):
        """거래 데이터를 수신합니다."""
        async with self.wsk_trade as ws:
            while self.con_trade:
                data = await ws.recv()
                self.signal.emit(data)

    async def receive_order(self):
        """주문 데이터를 수신합니다."""
        async with self.wsk_depth as ws:
            while self.con_depth:
                data = await ws.recv()
                self.signal.emit(data)

    def stop(self):
        """웹소켓을 종료합니다."""
        if self.loop and self.loop.is_running():
            self.loop.stop()


class BinanceWebSocketTrader(QThread):
    """바이낸스 웹소켓 트레이더 스레드 클래스입니다.
    바이낸스 주문 데이터를 웹소켓으로 수신합니다.
    """
    signal = pyqtSignal(dict)

    def __init__(self, api_key, scret_key, windowQ):
        super().__init__()
        self.api_key     = api_key
        self.scret_key   = scret_key
        self.windowQ     = windowQ
        self.loop        = None
        self.websocket   = None
        self.connected   = False
        self.async_client = None
        self.sock_manager = None

    def run(self):
        """웹소켓 루프를 실행합니다."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.run_user())
        self.loop.run_forever()

    async def run_user(self):
        """유저 데이터를 수신합니다."""
        while True:
            try:
                if not self.connected:
                    await self.connect()
                await self.receive_msgs()
            except Exception:
                self.windowQ.put(
                    (UI_NUM['시스템로그'], f'{format_exc()}오류 알림 - 바이낸스 웹소켓 체잔 수신 중 오류가 발생하여 재연결합니다.')
                )

            self.connected = False
            await asyncio.sleep(1)

    async def connect(self):
        """유저 웹소켓에 연결합니다."""
        if self.websocket:
            try:
                await self.websocket.__aexit__(None, None, None)
            except:
                pass

        if self.async_client is None:
            self.async_client = await AsyncClient.create(self.api_key, self.scret_key)
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=100000)

        self.websocket = self.sock_manager.futures_user_socket()
        self.connected = True

    async def receive_msgs(self):
        """메시지를 수신합니다."""
        async with self.websocket as ws:
            while self.connected:
                data = await ws.recv()
                self.signal.emit(data)

    def stop(self):
        """웹소켓을 종료합니다."""
        if self.loop and self.loop.is_running():
            self.loop.stop()
