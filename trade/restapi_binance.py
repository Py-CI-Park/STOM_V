
import asyncio
from traceback import format_exc
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import ui_num
from binance import AsyncClient, BinanceSocketManager


class BinanceWebSocketReceiver(QThread):
    """바이낸스 웹소켓 수신 스레드 클래스입니다.
    바이낸스 시장 데이터를 웹소켓으로 수신합니다.
    """
    signal = pyqtSignal(dict)

    def __init__(self, codes, windowQ):
        """수신기를 초기화합니다.
        Args:
            codes: 종목 코드 리스트
            windowQ: 윈도우 큐
        """
        super().__init__()
        self.codes     = codes
        self.windowQ   = windowQ
        self.loop      = None
        self.wsk_trade = None
        self.wsk_order = None
        self.con_trade = False
        self.con_order = False

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
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 바이낸스 웹소켓 체결 수신 중 오류가 발생하여 재연결합니다.')
                )

            self.con_trade = False
            await asyncio.sleep(5)

    async def run_order(self):
        """주문 데이터를 수신합니다."""
        while True:
            try:
                if not self.con_order:
                    await self.connect_order()
                await self.receive_order()
            except Exception:
                self.windowQ.put(
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 바이낸스 웹소켓 호가 수신 중 오류가 발생하여 재연결합니다.')
                )

            self.con_order = False
            await asyncio.sleep(5)

    async def connect_trader(self):
        """거래 웹소켓에 연결합니다."""
        stream_list = []
        for code in self.codes:
            stream_list.append(f'{code.lower()}@aggTrade')
        client = await AsyncClient.create()
        bsm    = BinanceSocketManager(client)
        self.wsk_trade = bsm.futures_multiplex_socket(stream_list)
        self.con_trade = True

    async def connect_order(self):
        """주문 웹소켓에 연결합니다."""
        stream_list = []
        for code in self.codes:
            stream_list.append(f'{code.lower()}@depth10')
        client = await AsyncClient.create()
        bsm    = BinanceSocketManager(client)
        self.wsk_order = bsm.futures_multiplex_socket(stream_list)
        self.con_order = True

    async def receive_trader(self):
        """거래 데이터를 수신합니다."""
        async with self.wsk_trade as ws:
            while self.con_trade:
                data = await ws.recv()
                self.signal.emit(data)

    async def receive_order(self):
        """주문 데이터를 수신합니다."""
        async with self.wsk_order as ws:
            while self.con_order:
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
        """트레이더를 초기화합니다.
        Args:
            api_key: API 키
            scret_key: 시크릿 키
            windowQ: 윈도우 큐
        """
        super().__init__()
        self.api_key     = api_key
        self.scret_key   = scret_key
        self.windowQ     = windowQ
        self.loop        = None
        self.websocket   = None
        self.connected   = False

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
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 바이낸스 웹소켓 체잔 수신 중 오류가 발생하여 재연결합니다.')
                )

            self.connected = False
            await asyncio.sleep(5)

    async def connect(self):
        """유저 웹소켓에 연결합니다."""
        client = await AsyncClient.create(self.api_key, self.scret_key)
        bsm    = BinanceSocketManager(client)
        self.websocket = bsm.futures_user_socket()
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
