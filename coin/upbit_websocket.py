import json
import uuid
import asyncio
import pyupbit
import websockets
from multiprocessing import Queue


class WebSocketReceiver:
    def __init__(self, codes, q, debug=False):
        self.codes      = codes
        self.q          = q
        self.debug      = debug
        self.url        = 'wss://api.upbit.com/websocket/v1'
        self.wsk_ticker = None
        self.wsk_orderb = None
        self.con_ticker = False
        self.con_orderb = False

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run_ticker())
        asyncio.ensure_future(self.run_orderb())
        loop.run_forever()

    async def run_ticker(self):
        await self.connect_ticker()
        await self.receive_ticker()
        await asyncio.sleep(1)
        await self.run_ticker()

    async def run_orderb(self):
        await self.connect_orderb()
        await self.receive_orderb()
        await asyncio.sleep(1)
        await self.run_orderb()

    async def connect_ticker(self):
        try:
            self.wsk_ticker = await websockets.connect(self.url, ping_interval=60)
            self.con_ticker = True
            data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
            await self.wsk_ticker.send(json.dumps(data))
        except:
            self.con_ticker = False

    async def connect_orderb(self):
        try:
            self.wsk_orderb = await websockets.connect(self.url, ping_interval=60)
            self.con_orderb = True
            data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'orderbook', 'codes': self.codes, 'isOnlyRealtime': True}]
            await self.wsk_orderb.send(json.dumps(data))
        except:
            self.con_orderb = False

    async def receive_ticker(self):
        while self.con_ticker:
            try:
                data = await self.wsk_ticker.recv()
                data = json.loads(data)
                if not self.debug:
                    self.q.put(data)
                else:
                    print(data)
            except:
                await self.disconnect_ticker()

    async def receive_orderb(self):
        while self.con_orderb:
            try:
                data = await self.wsk_orderb.recv()
                data = json.loads(data)
                if not self.debug:
                    self.q.put(data)
                else:
                    print(data)
            except:
                await self.disconnect_orderb()

    async def disconnect_ticker(self):
        await self.wsk_ticker.close()
        self.con_ticker = False

    async def disconnect_orderb(self):
        await self.wsk_orderb.close()
        self.con_orderb = False


if __name__ == '__main__':
    codes_ = pyupbit.get_tickers(fiat="KRW")
    q_     = Queue()
    WebSocketReceiver(codes_, q_, debug=True)
