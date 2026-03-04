
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from binance import AsyncClient, BinanceSocketManager
from utility.static import get_logger


class WebSocketReceiver(QThread):
    signal1 = pyqtSignal(dict)
    signal2 = pyqtSignal(dict)

    def __init__(self, codes):
        super().__init__()
        self.codes       = codes
        self.loop        = None
        self.wsk_trade   = None
        self.wsk_order   = None
        self.con_trade   = False
        self.con_order   = False
        self.logger      = get_logger(self.__class__.__name__)

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._run())

    async def _run(self):
        trader_task = asyncio.create_task(self.run_trade())
        order_task = asyncio.create_task(self.run_order())
        await asyncio.gather(trader_task, order_task)

    async def run_trade(self):
        while True:
            try:
                if not self.con_trade:
                    await self.connect_trader()
                await self.receive_trader()
            except Exception as e:
                self.logger.error(f"run_trade {e}, reconnecting...")

            self.con_trade = False
            await asyncio.sleep(5)

    async def run_order(self):
        while True:
            try:
                if not self.con_order:
                    await self.connect_order()
                await self.receive_order()
            except Exception as e:
                self.logger.error(f"run_order {e}, reconnecting...")

            self.con_order = False
            await asyncio.sleep(5)

    async def connect_trader(self):
        stream_list = []
        for code in self.codes:
            stream_list.append(f'{code.lower()}@aggTrade')
        client = await AsyncClient.create()
        bsm    = BinanceSocketManager(client)
        self.wsk_trade = bsm.futures_multiplex_socket(stream_list)
        self.con_trade = True

    async def connect_order(self):
        stream_list = []
        for code in self.codes:
            stream_list.append(f'{code.lower()}@depth10')
        client = await AsyncClient.create()
        bsm    = BinanceSocketManager(client)
        self.wsk_order = bsm.futures_multiplex_socket(stream_list)
        self.con_order = True

    async def receive_trader(self):
        async with self.wsk_trade as ws:
            while self.con_trade:
                data = await ws.recv()
                self.signal1.emit(data)

    async def receive_order(self):
        async with self.wsk_order as ws:
            while self.con_order:
                data = await ws.recv()
                self.signal2.emit(data)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()


class WebSocketTrader(QThread):
    signal1 = pyqtSignal(dict)

    def __init__(self, api_key, scret_key):
        super().__init__()
        self.api_key     = api_key
        self.scret_key   = scret_key
        self.loop        = None
        self.websocket   = None
        self.connected   = False
        self.logger      = get_logger(self.__class__.__name__)

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._run())

    async def _run(self):
        trader_task = asyncio.create_task(self.run_user())
        await asyncio.gather(trader_task)

    async def run_user(self):
        while True:
            try:
                if not self.connected:
                    await self.connect()
                await self.receive_msgs()
            except Exception as e:
                self.logger.error(f"run: {e}, reconnecting...")

            self.connected = False
            await asyncio.sleep(5)

    async def connect(self):
        client = await AsyncClient.create(self.api_key, self.scret_key)
        bsm    = BinanceSocketManager(client)
        self.websocket = bsm.futures_user_socket()
        self.connected = True

    async def receive_msgs(self):
        async with self.websocket as ws:
            while self.connected:
                data = await ws.recv()
                self.signal1.emit(data)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()
