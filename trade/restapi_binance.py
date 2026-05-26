
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
        self.async_client = None
        self.sock_manager = None
        self.webs_cg      = None
        self.webs_hg      = None
        self.conn_cg      = False
        self.conn_hg      = False
        self.cg_streams   = []
        self.hg_streams   = []

        for code in self.codes:
            self.cg_streams.append(f'{code.lower()}@aggTrade')
            self.hg_streams.append(f'{code.lower()}@depth10')

    def run(self):
        """웹소켓 루프를 실행합니다."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run_cg())
        self.loop.create_task(self._run_hg())
        self.loop.run_forever()

    async def _run_cg(self):
        """체결 데이터를 수신합니다."""
        while True:
            try:
                if not self.conn_cg:
                    await self._connect_cg()
                await self._receive_msg_cg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))

            self.conn_cg = False
            await asyncio.sleep(1)

    async def _run_hg(self):
        """호가 데이터를 수신합니다."""
        while True:
            try:
                if not self.conn_hg:
                    await self._connect_hg()
                await self._receive_msg_hg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))

            self.conn_hg = False
            await asyncio.sleep(1)

    async def _connect_cg(self):
        """거래 웹소켓에 연결합니다."""
        if self.webs_cg:
            try:
                await self.webs_cg.__aexit__(None, None, None)
            except Exception:
                pass

        if self.async_client is None or self.sock_manager is None:
            self.async_client = await AsyncClient.create()
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=10000)

        self.webs_cg = self.sock_manager.futures_multiplex_socket(self.cg_streams, category='market')
        self.conn_cg = True

    async def _connect_hg(self):
        """주문 웹소켓에 연결합니다."""
        if self.webs_hg:
            try:
                await self.webs_hg.__aexit__(None, None, None)
            except Exception:
                pass

        if self.async_client is None or self.sock_manager is None:
            self.async_client = await AsyncClient.create()
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=10000)

        self.webs_hg = self.sock_manager.futures_multiplex_socket(self.hg_streams, category='public')
        self.conn_hg = True

    async def _receive_msg_cg(self):
        """거래 데이터를 수신합니다."""
        async with self.webs_cg as ws:
            while self.conn_cg:
                data = await ws.recv()
                self.signal.emit(data)

    async def _receive_msg_hg(self):
        """주문 데이터를 수신합니다."""
        async with self.webs_hg as ws:
            while self.conn_hg:
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
        self.api_key      = api_key
        self.scret_key    = scret_key
        self.windowQ      = windowQ
        self.loop         = None
        self.async_client = None
        self.sock_manager = None
        self.websocket    = None
        self.connected    = False

    def run(self):
        """웹소켓 루프를 실행합니다."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run_user())
        self.loop.run_forever()

    async def _run_user(self):
        """유저 데이터를 수신합니다."""
        while True:
            try:
                if not self.connected:
                    await self._connect()
                await self._receive_msg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))

            self.connected = False
            await asyncio.sleep(1)

    async def _connect(self):
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

    async def _receive_msg(self):
        """메시지를 수신합니다."""
        async with self.websocket as ws:
            while self.connected:
                data = await ws.recv()
                self.signal.emit(data)

    def stop(self):
        """웹소켓을 종료합니다."""
        if self.loop and self.loop.is_running():
            self.loop.stop()
