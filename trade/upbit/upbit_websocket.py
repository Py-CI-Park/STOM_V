
import json
import uuid
import asyncio
import websockets
from traceback import format_exc
from utility.setting_base import ui_num
from PyQt5.QtCore import QThread, pyqtSignal


class WebSocketReceiver(QThread):
    signal1 = pyqtSignal(dict)
    signal2 = pyqtSignal(dict)

    def __init__(self, codes, windowQ):
        super().__init__()
        self.codes     = codes
        self.windowQ   = windowQ
        self.loop      = None
        self.wsk_trade = None
        self.wsk_order = None
        self.con_trade = False
        self.con_order = False
        self.url       = 'wss://api.upbit.com/websocket/v1'

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.run_trade())
        self.loop.create_task(self.run_order())
        self.loop.run_forever()

    async def run_trade(self):
        while True:
            try:
                if not self.con_trade:
                    await self.connect_trader()
                await self.receive_ticker()
            except:
                self.windowQ.put(
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 업비트 웹소켓 체결 수신 중 오류가 발생하여 재연결합니다.')
                )

            await self.disconnect_trader()

    async def run_order(self):
        while True:
            try:
                if not self.con_order:
                    await self.connect_order()
                await self.receive_order()
            except:
                self.windowQ.put(
                    (ui_num['시스템로그'], f'{format_exc()}오류 알림 - 업비트 웹소켓 호가 수신 중 오류가 발생하여 재연결합니다.')
                )

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
