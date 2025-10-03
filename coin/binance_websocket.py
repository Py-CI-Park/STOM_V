import re
import asyncio
import binance
from multiprocessing import Queue
from binance import AsyncClient, BinanceSocketManager


class WebSocketReceiver:
    def __init__(self, codes, q, debug=False):
        self.codes     = codes
        self.q         = q
        self.debug     = debug
        self.wsk_trade = None
        self.wsk_order = None

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run_trade())
        asyncio.ensure_future(self.run_order())
        loop.run_forever()

    async def run_trade(self):
        await self.connect_ticker()
        await self.receive_trader()
        await asyncio.sleep(1)
        await self.run_trade()

    async def run_order(self):
        await self.connect_orderb()
        await self.receive_orderb()
        await asyncio.sleep(1)
        await self.run_order()

    async def connect_ticker(self):
        stream_list = []
        for code in self.codes:
            stream_list.append(f'{code.lower()}@aggTrade')
        client = await AsyncClient.create()
        bsm    = BinanceSocketManager(client)
        self.wsk_trade = bsm.futures_multiplex_socket(stream_list)

    async def connect_orderb(self):
        stream_list = []
        for code in self.codes:
            stream_list.append(f'{code.lower()}@depth10')
        client = await AsyncClient.create()
        bsm    = BinanceSocketManager(client)
        self.wsk_order = bsm.futures_multiplex_socket(stream_list)

    async def receive_trader(self):
        async with self.wsk_trade:
            while True:
                try:
                    data = await self.wsk_trade.recv()
                    if not self.debug:
                        self.q.put(['trade', data])
                    else:
                        print(data)
                except:
                    break

    async def receive_orderb(self):
        async with self.wsk_order:
            while True:
                try:
                    data = await self.wsk_order.recv()
                    if not self.debug:
                        self.q.put(['depth', data])
                    else:
                        print(data)
                except:
                    break


class WebSocketTrader:
    def __init__(self, api_key, scret_key, q):
        self.api_key   = api_key
        self.scret_key = scret_key
        self.q         = q
        self.websocket = None

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run())
        loop.run_forever()

    async def run(self):
        await self.connect()
        await self.receive_msgs()
        await asyncio.sleep(1)
        await self.run()

    async def connect(self):
        client = await AsyncClient.create(self.api_key, self.scret_key)
        bsm    = BinanceSocketManager(client)
        self.websocket = bsm.futures_user_socket()

    async def receive_msgs(self):
        async with self.websocket:
            while True:
                try:
                    data = await self.websocket.recv()
                    self.q.put(['user', data])
                except:
                    break


if __name__ == '__main__':
    binance = binance.Client()
    data_   = binance.futures_ticker()
    data_   = [x for x in data_ if re.search('USDT$', x['symbol']) is not None]
    codes_  = []
    for x in data_:
        codes_.append(x['symbol'])

    q_ = Queue()
    WebSocketReceiver(codes_, q_, debug=True)
