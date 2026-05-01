
import re
import jwt
import json
import uuid
import hashlib
import asyncio
import requests
import websockets
from traceback import format_exc
from urllib.parse import urlencode
from utility.setting_base import ui_num
from PyQt5.QtCore import QThread, pyqtSignal


def get_symbols_info():
    url = 'https://api.upbit.com/v1/ticker/all?quote_currencies=KRW'
    headers = {'accept': 'application/json'}
    response = requests.get(url, headers=headers)
    data = response.json()
    dict_data = {}
    for d in data:
        dict_data[d['market']] = int(d['acc_trade_price'])
    return dict_data, list(dict_data.keys())


class Upbit:
    def __init__(self, access, secret):
        self.access = access
        self.secret = secret

    def _request_headers(self, query=None):
        payload = {
            'access_key': self.access,
            'nonce': str(uuid.uuid4())
        }

        if query is not None:
            m = hashlib.sha512()
            m.update(urlencode(query, doseq=True).replace('%5B%5D=', '[]=').encode())
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        jwt_token = jwt.encode(payload, self.secret, algorithm='HS256')
        authorization_token = 'Bearer {}'.format(jwt_token)
        headers = {'Authorization': authorization_token}
        return headers

    def _get(self, url, data=None):
        headers = self._request_headers(data)
        response = requests.get(url, headers=headers, data=data)
        return response.json()

    def _post(self, url, data):
        headers = self._request_headers(data)
        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response.json()

    def _delete(self, url, data):
        headers = self._request_headers(data)
        response = requests.delete(url, headers=headers, data=json.dumps(data))
        return response.json()

    def get_balances(self):
        url = 'https://api.upbit.com/v1/accounts'
        return self._get(url)

    def buy_market_order(self, ticker, price):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'bid', 'price': str(price), 'ord_type': 'price'}
        return self._post(url, data)

    def buy_limit_order(self, ticker, price, volume):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'bid', 'volume': str(volume), 'price': str(price), 'ord_type': 'limit'}
        return self._post(url, data)

    def sell_market_order(self, ticker, volume):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'ask', 'volume': str(volume), 'ord_type': 'market'}
        return self._post(url, data)

    def sell_limit_order(self, ticker, price, volume):
        url = 'https://api.upbit.com/v1/orders'
        data = {'market': ticker, 'side': 'ask', 'volume': str(volume), 'price': str(price), 'ord_type': 'limit'}
        return self._post(url, data)

    def cancel_order(self, od_no):
        url = 'https://api.upbit.com/v1/order'
        data = {'uuid': od_no}
        return self._delete(url, data)

    def get_order(self, od_no, state='wait', page=1, limit=100):
        p = re.compile(r'^\w+-\w+-\w+-\w+-\w+$')
        is_uuid = len(p.findall(od_no)) > 0
        if is_uuid:
            url = 'https://api.upbit.com/v1/order'
            data = {'uuid': od_no}
        else:
            url = 'https://api.upbit.com/v1/orders'
            data = {'market': od_no, 'state': state, 'page': page, 'limit': limit, 'order_by': 'desc'}
        return self._get(url, data)


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
