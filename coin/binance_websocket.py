import re
import asyncio
import binance
from multiprocessing import Queue
from binance import AsyncClient, BinanceSocketManager
from utility.static import get_logger


class WebSocketReceiver:
    def __init__(self, codes, q, debug=False):
        self.codes     = codes
        self.q         = q
        self.debug     = debug
        self.wsk_trade = None
        self.wsk_order = None
        self.con_trade = False
        self.con_order = False

        self.logger    = get_logger(self.__class__.__name__)

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run_trade())
        asyncio.ensure_future(self.run_order())
        loop.run_forever()

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
                if not self.debug:
                    self.q.put(['trade', data])
                else:
                    self.logger.info(data)

    async def receive_order(self):
        async with self.wsk_order as ws:
            while self.con_order:
                data = await ws.recv()
                if not self.debug:
                    self.q.put(['depth', data])
                else:
                    self.logger.info(data)


class WebSocketTrader:
    def __init__(self, api_key, scret_key, q, debug=False):
        self.api_key   = api_key
        self.scret_key = scret_key
        self.q         = q
        self.debug     = debug
        self.websocket = None
        self.connected = False

        self.logger    = get_logger(self.__class__.__name__)

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run())
        loop.run_forever()

    async def run(self):
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
                if not self.debug:
                    self.q.put(['user', data])
                else:
                    self.logger.info(data)


if __name__ == '__main__':
    binance = binance.Client()
    data_   = binance.futures_ticker()
    data_   = [x for x in data_ if re.search('USDT$', x['symbol']) is not None]
    codes_  = []
    for x in data_:
        codes_.append(x['symbol'])

    q_ = Queue()
    WebSocketReceiver(codes_, q_, debug=True)
