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
        self.wsk_trader = None
        self.wsk_order  = None
        self.con_trader = False
        self.con_order  = False

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run_trader())
        asyncio.ensure_future(self.run_order())
        loop.run_forever()

    async def run_trader(self):
        while True:
            try:
                if not self.con_trader:
                    await self.connect_trader()
                await self.receive_ticker()
            except Exception as e:
                print(f'Error WebSocketReceiver trader: {e}, reconnecting...')

            await self.disconnect_trader()

    async def run_order(self):
        while True:
            try:
                if not self.con_order:
                    await self.connect_order()
                await self.receive_order()
            except Exception as e:
                print(f'Error WebSocketReceiver order: {e}, reconnecting...')

            await self.disconnect_order()

    async def connect_trader(self):
        self.wsk_trader = await websockets.connect(self.url, ping_interval=60)
        self.con_trader = True
        data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.wsk_trader.send(json.dumps(data))

    async def connect_order(self):
        self.wsk_order = await websockets.connect(self.url, ping_interval=60)
        self.con_order = True
        data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'orderbook', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.wsk_order.send(json.dumps(data))

    async def receive_ticker(self):
        while self.con_trader:
            data = await self.wsk_trader.recv()
            data = json.loads(data)
            if not self.debug:
                self.q.put(data)
            else:
                print(data)

    async def receive_order(self):
        while self.con_order:
            data = await self.wsk_order.recv()
            data = json.loads(data)
            if not self.debug:
                self.q.put(data)
            else:
                print(data)

    async def disconnect_trader(self):
        self.con_trader = False
        await self.wsk_trader.close()
        await asyncio.sleep(5)

    async def disconnect_order(self):
        self.con_order = False
        await self.wsk_order.close()
        await asyncio.sleep(5)


if __name__ == '__main__':
    codes_ = pyupbit.get_tickers(fiat="KRW")
    q_     = Queue()
    WebSocketReceiver(codes_, q_, debug=True)
