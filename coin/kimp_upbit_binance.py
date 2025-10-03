import re
import json
import time
import uuid
import asyncio
import pyupbit
import requests
import websockets
import pandas as pd
from bs4 import BeautifulSoup
from multiprocessing import Process
from binance import AsyncClient, BinanceSocketManager
from utility.setting import ui_num, columns_kp
from utility.static import comma2float, threading_timer


class Kimp:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ   = qlist[0]
        self.kimpQ     = qlist[12]
        self.usdtokrw  = None
        self.proc_webs = None
        self.codes     = None
        self.threadrun = True
        self.df        = pd.DataFrame(columns=columns_kp)
        self.Start()

    def Start(self):
        self.codes = pyupbit.get_tickers(fiat="KRW")
        self.ConvertedCurrency()
        self.WebsSocketsStart(self.kimpQ)
        while True:
            data = self.kimpQ.get()
            if data[0] == 'upbit':
                data = data[1]
                code = data['code'].replace('KRW-', '')
                c    = data['trade_price']
                self.df.loc[code, ['종목명', '업비트(원)']] = code, c
            elif data[0] == 'binance' and self.usdtokrw is not None:
                data = data[1]
                for x in data:
                    if re.search('USDT$', x['s']) is not None:
                        code = x['s'].replace('USDT', '')
                        c    = float(x['c'])
                        self.df.loc[code, '바이낸스(달러)'] = c

                self.df['대비(원)'] = self.df['업비트(원)'] - self.df['바이낸스(달러)'] * self.usdtokrw
                self.df['대비율(%)'] = self.df['대비(원)'] / self.df['업비트(원)'] * 100
                self.df.dropna(inplace=True)
                self.df.sort_values(by=['대비율(%)'], ascending=False, inplace=True)
                self.windowQ.put((ui_num['김프'], self.df, self.usdtokrw))
            elif data == '프로세스종료':
                self.threadrun = False
                self.WebProcessKill()
                break

        time.sleep(3)

    def ConvertedCurrency(self):
        try:
            html = requests.get('https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW').text
            soup = BeautifulSoup(html, 'html.parser')
            converted_currency = soup.find('p', class_='no_today').get_text().replace('\n', '').replace('원', '')
            self.usdtokrw = comma2float(converted_currency)
        except:
            pass

        if self.threadrun:
            threading_timer(60, self.ConvertedCurrency)

    def WebsSocketsStart(self, q):
        self.proc_webs = Process(target=WebSocketManager, args=(self.codes, q), daemon=True)
        self.proc_webs.start()

    def WebProcessKill(self):
        if self.proc_webs is not None and self.proc_webs.is_alive(): self.proc_webs.kill()


class WebSocketManager:
    def __init__(self, codes, q):
        self.codes       = codes
        self.q           = q
        self.wsk_upbit   = None
        self.wsk_binance = None
        self.con_upbit   = False
        self.con_binance = False

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run_upbit())
        asyncio.ensure_future(self.run_binance())
        loop.run_forever()

    async def run_upbit(self):
        await self.connect_upbit()
        await self.receive_upbit()
        await asyncio.sleep(1)
        await self.run_upbit()

    async def run_binance(self):
        await self.connect_binance()
        await self.receive_binance()
        await asyncio.sleep(1)
        await self.run_binance()

    async def connect_upbit(self):
        try:
            self.wsk_upbit = await websockets.connect('wss://api.upbit.com/websocket/v1', ping_interval=60)
            self.con_upbit = True
            data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
            await self.wsk_upbit.send(json.dumps(data))
        except:
            self.con_upbit = False

    async def connect_binance(self):
        try:
            client = await AsyncClient.create()
            bsm = BinanceSocketManager(client)
            self.wsk_binance = bsm.miniticker_socket()
        except:
            self.con_binance = False

    async def receive_upbit(self):
        while self.con_upbit:
            try:
                data = await self.wsk_upbit.recv()
                data = json.loads(data)
                self.q.put(('upbit', data))
            except:
                await self.disconnect_ticker()

    async def receive_binance(self):
        async with self.wsk_binance:
            self.con_binance = True
            while self.con_binance:
                try:
                    data = await self.wsk_binance.recv()
                    self.q.put(('binance', data))
                except:
                    self.con_binance = False

    async def disconnect_ticker(self):
        await self.wsk_upbit.close()
        self.con_upbit = False
