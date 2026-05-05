
import re
import sys
import json
import uuid
import asyncio
import requests
import websockets
import pandas as pd
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QApplication
from trade.restapi_upbit import get_symbols_info
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from binance import AsyncClient, BinanceSocketManager
from utility.settings.setting_base import ui_num, columns_kp
from utility.static_method.static import comma2float, thread_decorator


class Kimp:
    """김프(업비트-바이낸스 가격 차이) 계산 클래스입니다.
    업비트와 바이낸스의 가격 차이를 계산하여 표시합니다.
    """
    def __init__(self, qlist):
        """김프 계산을 초기화합니다.
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ
           0        1       2      3       4      5      6      7       8        9       10     11
        Args:
            qlist: 큐 리스트
        """
        app = QApplication(sys.argv)

        self.windowQ   = qlist[0]
        self.usdtokrw  = None
        self.thread_ws = None
        _, self.codes  = get_symbols_info()
        self.df        = pd.DataFrame(columns=columns_kp)

        self._converted_currency()

        self.qtimer = QTimer()
        self.qtimer.setInterval(60 * 1000)
        self.qtimer.timeout.connect(self._converted_currency)
        self.qtimer.start()

        self.thread_ws = KimpWebSocketManager(self.codes)
        self.thread_ws.signal1.connect(self._update_upbit_data)
        self.thread_ws.signal2.connect(self._update_binance_data)
        self.thread_ws.start()

        app.exec_()

    def _update_upbit_data(self, data):
        """업비트 데이터를 업데이트합니다.
        Args:
            data: 업비트 데이터
        """
        code = data['code'].replace('KRW-', '')
        c = data['trade_price']
        self.df.loc[code, ['종목명', '업비트(원)']] = [code, c]

    def _update_binance_data(self, data):
        """바이낸스 데이터를 업데이트합니다.
        Args:
            data: 바이낸스 데이터
        """
        for x in data:
            if re.search('USDT$', x['s']) is not None:
                code = x['s'].replace('USDT', '')
                c = float(x['c'])
                self.df.loc[code, '바이낸스(달러)'] = c

        if self.usdtokrw is not None:
            self.df['대비(원)'] = self.df['업비트(원)'] - self.df['바이낸스(달러)'] * self.usdtokrw
            self.df['대비율(%)'] = self.df['대비(원)'] / self.df['업비트(원)'] * 100
            self.df.dropna(inplace=True)
            self.df.sort_values(by=['대비율(%)'], ascending=False, inplace=True)
            self.windowQ.put((ui_num['김프'], self.df, self.usdtokrw))

    @thread_decorator
    def _converted_currency(self):
        """환율을 변환합니다.
        """
        try:
            html = requests.get('https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW').text
            soup = BeautifulSoup(html, 'html.parser')
            # noinspection PyUnresolvedReferences
            converted_currency = soup.find('p', class_='no_today').get_text().replace('\n', '').replace('원', '')
            self.usdtokrw = comma2float(converted_currency)
        except Exception:
            pass


class KimpWebSocketManager(QThread):
    """김프 웹소켓 관리자 클래스입니다.
    업비트와 바이낸스의 웹소켓을 관리하여 실시간 데이터를 수신합니다.
    """
    signal1 = pyqtSignal(object)
    signal2 = pyqtSignal(object)

    def __init__(self, codes):
        """웹소켓 관리자를 초기화합니다.
        Args:
            codes: 종목 코드 리스트
        """
        super().__init__()
        self.codes       = codes
        self.loop        = None
        self.wsk_upbit   = None
        self.wsk_binance = None
        self.con_upbit   = False
        self.con_binance = False

    def run(self):
        """웹소켓 관리자를 실행합니다.
        """
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._run())

    async def _run(self):
        """비동기 작업을 실행합니다.
        """
        upbit_task = asyncio.create_task(self.run_upbit())
        binance_task = asyncio.create_task(self.run_binance())
        await asyncio.gather(upbit_task, binance_task)

    async def run_upbit(self):
        """업비트 웹소켓을 실행합니다.
        """
        while True:
            await self.connect_upbit()
            await self.receive_upbit()
            await asyncio.sleep(1)

    async def run_binance(self):
        """바이낸스 웹소켓을 실행합니다.
        """
        while True:
            await self.connect_binance()
            await self.receive_binance()
            await asyncio.sleep(1)

    async def connect_upbit(self):
        """업비트 웹소켓에 연결합니다.
        """
        try:
            self.wsk_upbit = await websockets.connect('wss://api.upbit.com/websocket/v1', ping_interval=60)
            data = [{'ticket': str(uuid.uuid4())[:6]}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
            await self.wsk_upbit.send(json.dumps(data))
            self.con_upbit = True
        except Exception:
            self.con_upbit = False

    async def connect_binance(self):
        """바이낸스 웹소켓에 연결합니다.
        """
        try:
            client = await AsyncClient.create()
            bsm = BinanceSocketManager(client)
            self.wsk_binance = bsm.miniticker_socket()
            self.con_binance = True
        except Exception:
            self.con_binance = False

    async def receive_upbit(self):
        """업비트 데이터를 수신합니다.
        """
        while self.con_upbit:
            try:
                data = await self.wsk_upbit.recv()
                data = json.loads(data)
                self.signal1.emit(data)
            except Exception:
                await self.wsk_upbit.close()
                self.con_upbit = False

    async def receive_binance(self):
        """바이낸스 데이터를 수신합니다.
        """
        while self.con_binance:
            async with self.wsk_binance:
                try:
                    data = await self.wsk_binance.recv()
                    self.signal2.emit(data)
                except Exception:
                    self.con_binance = False
