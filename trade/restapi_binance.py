
import asyncio
from traceback import format_exc
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import UI_NUM
from binance import AsyncClient, BinanceSocketManager


class BinanceWebSocketReceiver(QThread):
    """바이낸스 웹소켓 수신 스레드 클래스입니다.
    바이낸스 시장 데이터를 웹소켓으로 수신합니다."""
    signal = pyqtSignal(dict)

    def __init__(self, codes, windowQ):
        super().__init__()
        self.windowQ      = windowQ
        self.loop         = None
        self.async_client = None
        self.sock_manager = None
        self.webs_cg      = None
        self.webs_hg      = None
        self.conn_cg      = False
        self.conn_hg      = False
        self.cg_streams   = [f'{code.lower()}@aggTrade' for code in codes]
        self.hg_streams   = [f'{code.lower()}@depth10' for code in codes]

    def run(self):
        """웹소켓 루프를 실행합니다."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run_cg())
        self.loop.create_task(self._run_hg())
        self.loop.run_forever()

    async def _run_cg(self):
        """체결 웹소켓 연결 및 수신을 실행합니다."""
        while True:
            try:
                if not self.conn_cg:
                    await self._connect_cg()
                await self._receive_msg_cg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            await self._disconnect_cg()

    async def _run_hg(self):
        """호가 웹소켓 연결 및 수신을 실행합니다."""
        while True:
            try:
                if not self.conn_hg:
                    await self._connect_hg()
                await self._receive_msg_hg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            await self._disconnect_hg()

    async def _connect_cg(self):
        """체결 웹소켓에 연결합니다."""
        if self.async_client is None or self.sock_manager is None:
            self.async_client = await AsyncClient.create()
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=10000)
        try:
            self.webs_cg = self.sock_manager.futures_multiplex_socket(self.cg_streams, category='market')
            self.conn_cg = True
        except Exception:
            self.conn_cg = False

    async def _connect_hg(self):
        """호가 웹소켓에 연결합니다."""
        if self.async_client is None or self.sock_manager is None:
            self.async_client = await AsyncClient.create()
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=10000)
        try:
            self.webs_hg = self.sock_manager.futures_multiplex_socket(self.hg_streams, category='public')
            self.conn_hg = True
        except Exception:
            self.conn_hg = False

    async def _receive_msg_cg(self):
        """체결의 실시간시세를 등록합니다."""
        async with self.webs_cg as ws:
            while self.conn_cg:
                data = await ws.recv()
                self.signal.emit(data)

    async def _receive_msg_hg(self):
        """호가의 실시간시세를 등록합니다."""
        async with self.webs_hg as ws:
            while self.conn_hg:
                data = await ws.recv()
                self.signal.emit(data)

    async def _disconnect_cg(self):
        """체결 웹소켓을 종료합니다."""
        try:
            if self.webs_cg is not None:
                await self.webs_cg.__aexit__(None, None, None)
        except Exception:
            pass
        self.conn_cg = False
        await asyncio.sleep(1)

    async def _disconnect_hg(self):
        """호가 웹소켓을 종료합니다."""
        try:
            if self.webs_hg is not None:
                await self.webs_hg.__aexit__(None, None, None)
        except Exception:
            pass
        self.conn_hg = False
        await asyncio.sleep(1)


class BinanceWebSocketTrader(QThread):
    """바이낸스 웹소켓 트레이더 스레드 클래스입니다.
    주문체결 데이터를 웹소켓으로 수신합니다."""
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
        """주문체결 웹소켓 연결 및 수신을 실행합니다."""
        while True:
            try:
                if not self.connected:
                    await self._connect()
                await self._receive_msg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            await self.disconnect_user()

    async def _connect(self):
        """주문체결 웹소켓을 연결합니다."""
        if self.async_client is None:
            self.async_client = await AsyncClient.create(self.api_key, self.scret_key)
            self.sock_manager = BinanceSocketManager(self.async_client, max_queue_size=100000)
        try:
            self.websocket = self.sock_manager.futures_user_socket()
            self.connected = True
        except Exception:
            self.connected = False

    async def _receive_msg(self):
        """주문체결 데이터를 수신합니다."""
        async with self.websocket as ws:
            while self.connected:
                data = await ws.recv()
                self.signal.emit(data)

    async def disconnect_user(self):
        """주문체결 웹소켓을 종료합니다."""
        try:
            if self.websocket:
                await self.websocket.__aexit__(None, None, None)
        except:
            pass
        self.connected = False
        await asyncio.sleep(1)
