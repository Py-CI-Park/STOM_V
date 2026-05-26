
import ssl
import jwt
import json
import uuid
import certifi
import hashlib
import asyncio
import requests
import websockets
from traceback import format_exc
from urllib.parse import unquote, urlencode
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import UI_NUM

ssl_context = ssl.create_default_context(cafile=certifi.where())


def get_symbols_info():
    """업비트 종목정보를 조회합니다."""
    dict_data = {}
    headers = {'accept': 'application/json'}
    url = 'https://api.upbit.com/v1/market/all'
    response = requests.get(url, headers=headers)
    datas = response.json()
    for data in datas:
        symbol = data['market']
        if 'KRW' in symbol:
            dict_data[symbol] = {
                '종목명': data['korean_name']
            }
    return dict_data, list(dict_data.keys())


class UpbitRestAPI:
    """업비트 RESTAPI 메인 클래스입니다."""
    def __init__(self, access, secret, windowQ):
        self.access  = access
        self.secret  = secret
        self.windowQ = windowQ

        self.주문구분 = {
            '매수': 'bid',
            '매도': 'ask'
        }

        self.주문유형 = {
            '시장가': {'매수': 'price', '매도': 'market'},
            '지정가': {'매수': 'limit', '매도': 'limit'},
            '지정가IOC': {'매수': 'limit', '매도': 'limit'},
            '지정가FOK': {'매수': 'limit', '매도': 'limit'},
            '최유리IOC': {'매수': 'best', '매도': 'best'},
            '최유리FOK': {'매수': 'best', '매도': 'best'},
        }

        self.주문조건 = {
            '지정가IOC': 'ioc',
            '지정가FOK': 'fok',
            '최유리IOC': 'ioc',
            '최유리FOK': 'fok',
        }

    def _headers(self, query=None):
        """헤더를 생성합니다."""
        payload = {
            'access_key': self.access,
            'nonce': str(uuid.uuid4())
        }
        if query is not None:
            query_string = unquote(urlencode(query, doseq=True))
            query_hash = hashlib.sha512(query_string.encode('utf-8')).hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'

        token = jwt.encode(payload, self.secret, algorithm='HS256')
        return {'Authorization': f'Bearer {token}'}

    def _get(self, url):
        """GET 요청을 보냅니다."""
        headers = self._headers()
        response = requests.get(url, headers=headers)
        return response.json()

    def _post(self, url, data):
        """POST 요청을 보냅니다."""
        headers = self._headers(data)
        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response.json()

    def _delete(self, url, data):
        """DELETE 요청을 보냅니다."""
        headers = self._headers(data)
        response = requests.delete(url, headers=headers, data=json.dumps(data))
        return response.json()

    def get_balances(self):
        """예수금을 조회합니다."""
        url = 'https://api.upbit.com/v1/accounts'
        ret = self._get(url)
        return int(float(ret[0]['balance']))

    def order_coin(self, 종목코드='', 주문구분='', 주문유형='', 주문금액=0, 주문수량=0):
        """주문을 전송합니다."""
        url = 'https://api.upbit.com/v1/orders'
        data = {
            'market': 종목코드,
            'side': self.주문구분[주문구분],
            'ord_type': self.주문유형[주문유형][주문구분]
        }

        if 주문구분 == '매수' or '지정가' in 주문유형:
            data['price'] = str(주문금액)

        if 주문수량 > 0 and (주문구분 == '매도' or '지정가' in 주문유형):
            data['volume'] = str(주문수량)

        주문조건 = self.주문조건.get(주문유형)
        if 주문조건:
            data['time_in_force'] = 주문조건

        return self._post(url, data)

    def order_cancel(self, od_no):
        """주문을 취소합니다."""
        url = 'https://api.upbit.com/v1/order'
        data = {'uuid': od_no}
        return self._delete(url, data)


class UpbitWebSocketReceiver(QThread):
    """업비트 웹소켓 수신 스레드 클래스입니다.
    체결 및 호가 데이터를 웹소켓으로 수신합니다."""
    signal = pyqtSignal(dict)

    def __init__(self, codes, windowQ):
        super().__init__()
        self.codes   = codes
        self.windowQ = windowQ
        self.loop    = None
        self.webs_cg = None
        self.webs_hg = None
        self.conn_cg = False
        self.conn_hg = False
        self.url     = 'wss://api.upbit.com/websocket/v1'

    def run(self):
        """웹소켓 루프를 실행합니다."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run_cg())
        self.loop.create_task(self._run_hg())
        self.loop.run_forever()

    async def _run_cg(self):
        """체결 웹소켓 연결 및 수신을 실행합니다."""
        while True:
            try:
                if not self.conn_cg:
                    await self._connect_cg()
                await self._receive_cg_msg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))

            await self._disconnect_cg()

    async def _run_hg(self):
        """호가 웹소켓 연결 및 수신을 실행합니다."""
        while True:
            try:
                if not self.conn_hg:
                    await self._connect_hg()
                await self._receive_hg_msg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))

            await self._disconnect_hg()

    async def _connect_cg(self):
        """체결 웹소켓에 연결합니다."""
        self.conn_cg = True
        self.webs_cg = await websockets.connect(self.url, ssl=ssl_context)
        data = [{'ticket': str(uuid.uuid4())}, {'type': 'ticker', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.webs_cg.send(json.dumps(data))

    async def _connect_hg(self):
        """호가 웹소켓에 연결합니다."""
        self.conn_hg = True
        self.webs_hg = await websockets.connect(self.url, ssl=ssl_context)
        data = [{'ticket': str(uuid.uuid4())}, {'type': 'orderbook', 'codes': self.codes, 'isOnlyRealtime': True}]
        await self.webs_hg.send(json.dumps(data))

    async def _receive_cg_msg(self):
        """체결 데이터를 수신합니다."""
        while self.conn_cg:
            data = await self.webs_cg.recv()
            data = json.loads(data)
            self.signal.emit(data)

    async def _receive_hg_msg(self):
        """호가 데이터를 수신합니다."""
        while self.conn_hg:
            data = await self.webs_hg.recv()
            data = json.loads(data)
            self.signal.emit(data)

    async def _disconnect_cg(self):
        """체결 웹소켓을 종료합니다."""
        self.conn_cg = False
        if self.webs_cg is not None:
            try:
                await self.webs_cg.close()
            except Exception:
                pass
        await asyncio.sleep(1)

    async def _disconnect_hg(self):
        """호가 웹소켓을 종료합니다."""
        self.conn_hg = False
        if self.webs_hg is not None:
            try:
                await self.webs_hg.close()
            except Exception:
                pass
        await asyncio.sleep(1)

    def stop(self):
        """웹소켓 루프를 종료합니다."""
        if self.loop and self.loop.is_running():
            self.loop.stop()


class UpbitWebSocketTrader(QThread):
    """업비트 웹소켓 트레이더 스레드 클래스입니다.
    주문체결 데이터를 웹소켓으로 수신합니다."""
    signal = pyqtSignal(dict)

    def __init__(self, access, secret, windowQ):
        super().__init__()
        self.access    = access
        self.secret    = secret
        self.windowQ   = windowQ
        self.loop      = None
        self.websocket = None
        self.connected = False
        self.url       = 'wss://api.upbit.com/websocket/v1/private'

    def run(self):
        """웹소켓 루프를 실행합니다."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run_user())
        self.loop.run_forever()

    async def _run_user(self):
        """주문체결 웹소켓 연결 및 수신을 실행합니다."""
        while True:
            try:
                if not self.connected:
                    await self._connect()
                await self._receive_msg()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))

            await self._disconnect()

    def _headers(self):
        """JWT 토큰으로 해더를 생성합니다."""
        payload = {
            'access_key': self.access,
            'nonce': str(uuid.uuid4())
        }
        token = jwt.encode(payload, self.secret, algorithm='HS256')
        return {'Authorization': f'Bearer {token}'}

    async def _connect(self):
        """주문체결 웹소켓에 연결하고 실시간시세를 등록합니다."""
        headers = self._headers()
        self.websocket = await websockets.connect(self.url, additional_headers=headers, ssl=ssl_context)
        self.connected = True
        data = [{'ticket': str(uuid.uuid4())}, {'type': 'myOrder'}]
        await self.websocket.send(json.dumps(data))

    async def _receive_msg(self):
        """주문체결 데이터를 수신합니다."""
        while self.connected:
            data = await self.websocket.recv()
            data = json.loads(data)
            self.signal.emit(data)

    async def _disconnect(self):
        """웹소켓 연결을 종료합니다."""
        self.connected = False
        if self.websocket is not None:
            await self.websocket.close()
        await asyncio.sleep(1)

    def stop(self):
        """웹소켓 루프를 종료합니다."""
        if self.loop and self.loop.is_running():
            self.loop.stop()
