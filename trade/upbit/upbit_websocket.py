
import json
import uuid
import asyncio
import websockets
from PyQt5.QtCore import QThread, pyqtSignal
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
        self.url         = 'wss://api.upbit.com/websocket/v1'
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
                await self.receive_ticker()
            except Exception as e:
                self.logger.error(f'run_trader {e}, reconnecting...')

            await self.disconnect_trader()

    async def run_order(self):
        while True:
            try:
                if not self.con_order:
                    await self.connect_order()
                await self.receive_order()
            except Exception as e:
                self.logger.error(f'run_order {e}, reconnecting...')

            await self.disconnect_order()

    async def connect_trader(self):
        self.con_trade = True
        self.wsk_trade = await websockets.connect(self.url, ping_interval=60)
        data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.wsk_trade.send(json.dumps(data))

    async def connect_order(self):
        self.con_order = True
        self.wsk_order = await websockets.connect(self.url, ping_interval=60)
        data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'orderbook', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.wsk_order.send(json.dumps(data))

    async def receive_ticker(self):
        while self.con_trade:
            data = await self.wsk_trade.recv()
            data = json.loads(data)
            self.signal1.emit(data)

    async def receive_order(self):
        while self.con_order:
            data = await self.wsk_order.recv()
            data = json.loads(data)
            self.signal2.emit(data)

    async def disconnect_trader(self):
        self.con_trade = False
        if self.wsk_trade is not None:
            await self.wsk_trade.close()
        await asyncio.sleep(5)

    async def disconnect_order(self):
        self.con_order = False
        if self.wsk_order is not None:
            await self.wsk_order.close()
        await asyncio.sleep(5)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()
