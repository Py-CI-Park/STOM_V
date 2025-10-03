import json
import asyncio
import requests
import websockets
import pandas as pd
from multiprocessing import Process, Queue


class Kiwooom:
    def __init__(self, access, secret, debug=False):
        self.access  = access
        self.secret  = secret
        self.debug   = debug
        self.token   = None
        self.nextkey = None
        self.cont_yn = False
        self.wproc   = None
        self.hosturl = 'https://api.kiwoom.com'

    def _url(self, endurl):
        return f'{self.hosturl}{endurl}'

    def _post(self, url, headers, params):
        self.cont_yn = False
        self.nextkey = ''
        response     = requests.post(url, headers=headers, json=params)
        self.cont_yn = True if response.headers.get('cont-yn') == 'Y' else False
        self.nextkey = response.headers.get('next-key')
        body = response.json()
        ret  = True if body['return_code'] == 0 else False
        if not ret and self.debug: print('_post', body)
        return ret, body

    def _headers(self, api_id=None, contyn='N', nextkey=''):
        headers = {'Content-Type': 'application/json;charset=UTF-8'}
        if api_id is not None:
            headers['authorization'] = f'Bearer {self.token}'
            headers['cont-yn']       = contyn
            headers['next-key']      = nextkey
            headers['api-id']        = api_id
        return headers

    def _params(self, gubun='', stk_cd='', ord_qty='', ord_uv='', trde_tp='', cond_uv='', orig_ord_no='',
                mdfy_qty='', mdfy_uv='', mdfy_cond_uv=''):
        params = {}
        if gubun in ('buy', 'sell', 'modify', 'cancel'):
            params = {
                'dmst_stex_tp': 'KRX',  # 국내거래소구분 KRX,NXT,SOR
                'stk_cd': stk_cd,       # 종목코드
            }
            if gubun in ('buy', 'sell'):
                params['ord_qty'] = ord_qty     # 주문수량
                params['ord_uv']  = ord_uv      # 주문단가
                params['trde_tp'] = trde_tp     # 매매구분
                params['cond_uv'] = cond_uv     # 조건단가
            else:
                params['orig_ord_no'] = orig_ord_no         # 원주문번호
                if gubun == 'modify':
                    params['mdfy_qty']     = mdfy_qty       # 정정수량
                    params['mdfy_uv']      = mdfy_uv        # 정정단가
                    params['mdfy_cond_uv'] = mdfy_cond_uv   # 정정조건단가
                else:
                    params['cncl_qty']     = ord_qty        # 취소수량
        elif gubun == 'tr':
            params = {'qry_tp': '0', 'dmst_stex_tp': 'KRX'}
        elif gubun in ('create', 'revoke'):
            params = {'appkey': self.access, 'secretkey': self.secret}
            if gubun == 'create':
                params['grant_type'] = 'client_credentials'
            else:
                params['token'] = self.token
        else:
            params['mrkt_tp'] = gubun
        return params

    def create_token(self):
        url       = self._url('/oauth2/token')
        headers   = self._headers()
        params    = self._params(gubun='create')
        ret, body = self._post(url, headers, params)
        if ret: self.token = body['token']
        if self.debug: print('create_token', body)
        return ret, self.token

    def revoke_token(self):
        url       = self._url('/oauth2/revoke')
        headers   = self._headers()
        params    = self._params(gubun='revoke')
        ret, body = self._post(url, headers, params)
        if ret: self.token = None
        if self.debug: print('revoke_token', body)
        return ret

    def get_code_list(self, gubun):
        """
        gubun
        0:코스피, 10:코스닥, 3:ELW, 8:ETF, 30:K-OTC, 50:코넥스, 5:신주인수권, 4:뮤추얼펀드, 6:리츠, 9:하이일드
        """
        url       = self._url('/api/dostk/stkinfo')
        headers   = self._headers(api_id='ka10099')
        params    = self._params(gubun=str(gubun))
        ret, body = self._post(url, headers, params)
        dict_ = {}
        if ret:
            for data in body['list']:
                dict_[data['code']] = data['name']
        if self.debug: print('get_code_list', dict_)
        return ret, dict_

    def get_balances(self):
        url = self._url('/api/dostk/acnt')
        headers   = self._headers(api_id='kt00004', contyn='N', nextkey=self.nextkey)
        params    = self._params(gubun='tr')
        ret, body = self._post(url, headers, params)
        balances  = int(body['d2_entra']) if ret else 0
        if self.debug: print('get_balances', balances)
        return ret, balances

    def get_jango(self, 연속조회='N'):
        url = self._url('/api/dostk/acnt')
        headers   = self._headers(api_id='kt00018', contyn=연속조회, nextkey=self.nextkey)
        params    = self._params(gubun='tr')
        ret, body = self._post(url, headers, params)
        dict_, df = None, None
        if ret:
            dict_ = {
                '총매입금액': int(body['tot_pur_amt']),
                '총평가금액': int(body['tot_evlt_amt']),
                '총평가손익금액': int(body['tot_evlt_pl']),
                '총수익률': float(body['tot_prft_rt']),
                '추정예탁자산': int(body['prsm_dpst_aset_amt'])
            }
            row_data = []
            for dict_jango in body['acnt_evlt_remn_indv_tot']:
                row_data.append(list(dict_jango.values()))
            columns = [
                '종목번호', '종목명', '평가손익', '수익률', '매입가', '전일종가', '보유수량', '매매가능수량', '현재가', '전일매수수량',
                '전일매도수량', '금일매수수량', '금일매도수량', '매입금액', '매입수수료', '평가금액', '평가수수료', '세금', '수수료합',
                '보유비중', '신용구분', '신용구분명', '대출일'
            ]
            df = pd.DataFrame(row_data, columns=columns)
            df['종목번호'] = df['종목번호'].apply(lambda x: x.strip()[1:])
            columns = ['보유비중', '수익률']
            df[columns] = df[columns].astype(float)
            columns = [
                '평가손익', '매입가', '전일종가', '보유수량', '매매가능수량', '현재가', '전일매수수량', '전일매도수량', '금일매수수량',
                '금일매도수량', '매입금액', '매입수수료', '평가금액', '평가수수료', '세금', '수수료합',
            ]
            df[columns] = df[columns].astype(int)
        if self.debug: print('get_jango', dict_, df)
        return ret, dict_, df

    def send_order(self, 구분, 종목코드='', 주문수량='', 주문단가='', 매매구분='', 조건단가='', 원주문번호='',
                   정정수량='', 정정단가='', 정정조건단가=''):
        if 구분 == 'buy':      tr_no = 'kt10000'
        elif 구분 == 'sell':   tr_no = 'kt10001'
        elif 구분 == 'modify': tr_no = 'kt10002'
        else:                 tr_no = 'kt10003'
        url       = self._url('/api/dostk/ordr')
        headers   = self._headers(api_id=tr_no)
        params    = self._params(gubun=구분, stk_cd=종목코드, ord_qty=주문수량, ord_uv=주문단가, trde_tp=매매구분,
                                 cond_uv=조건단가, orig_ord_no=원주문번호, mdfy_qty=정정수량, mdfy_uv=정정단가,
                                 mdfy_cond_uv=정정조건단가)
        """
        매매구분
            0:지정가, 3:시장가, 5:조건부지정가, 81:장마감후시간외, 61:장시작전시간외, 62:시간외단일가, 6:최유리지정가,
            7:최우선지정가, 10:지정가(IOC), 13:시장가(IOC), 16:최유리(IOC), 20:지정가(FOK), 23:시장가(FOK),
            26:최유리(FOK), 28:스톱지정가, 29:중간가, 30:중간가(IOC), 31:중간가(FOK)
        buy                                                 sell
        {                                                   {
            "dmst_stex_tp": "KRX",                              "dmst_stex_tp": "KRX",
            "stk_cd": "005930",                                 "stk_cd": "005930",
            "ord_qty": "1",                                     "stk_cd": "005930",
            "ord_uv": "",                                       "ord_qty": "1",
            "trde_tp": "3",                                     "ord_uv": "",
            "cond_uv": ""                                       "trde_tp": "3",
        }                                                       "cond_uv": ""
                                                            }
        modify                                              cancel
        {                                                   {
            "dmst_stex_tp": "KRX",                              "dmst_stex_tp": "KRX",
            "orig_ord_no": "0000139",                           "orig_ord_no": "0000140",
            "stk_cd": "005930",                                 "stk_cd": "005930",
            "mdfy_qty": "1",                                    "cncl_qty": "1"
            "mdfy_uv": "199700",                            }
            "mdfy_cond_uv": ""
        }
        """
        ret, body = self._post(url, headers, params)
        ord_no    = body['ord_no']
        if self.debug: print('send_order', body)
        return ret, ord_no

    def websoket_start(self, receiverQ, traderQ, debug=False):
        self.wproc = Process(target=WebSocketManager, args=(self.token, receiverQ, traderQ, debug))
        self.wproc.start()

    def websoket_kill(self):
        if self.wproc is not None and self.wproc.is_alive(): self.wproc.kill()


class WebSocketManager:
    def __init__(self, token_, receiverQ, traderQ, debug=False):
        self.token     = token_
        self.receiverQ = receiverQ
        self.traderQ   = traderQ
        self.debug     = debug
        self.codes     = []
        self.websocket = None
        self.connected = False

        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.run())
        loop.run_forever()

    async def run(self):
        await self.connect()
        await self.receive_msgs()
        await asyncio.sleep(1)
        await self.run()

    async def connect(self):
        try:
            uri = 'wss://api.kiwoom.com:10000/api/dostk/websocket'
            self.websocket = await websockets.connect(uri)
            self.connected = True
            await asyncio.sleep(1)
            msg = {'trnm': 'LOGIN', 'token': self.token}
            await self.send_msg(msg)
        except:
            self.connected = False

    async def disconnect(self):
        await self.websocket.close()
        self.connected = False

    async def send_msg(self, msg):
        if self.connected:
            if not isinstance(msg, str):
                msg = json.dumps(msg)
            await self.websocket.send(msg)

    async def receive_msgs(self):
        while self.connected:
            try:
                recv_data = await self.websocket.recv()
                recv_data = json.loads(recv_data)
                trnm = recv_data['trnm']
                if trnm == 'REAL':
                    data = recv_data['data']
                    name = data['name']
                    if not self.debug:
                        if name == '주문체결':
                            self.traderQ.put(data)
                        elif name == '장시작시간':
                            self.receiverQ.put(data)
                            self.traderQ.put(data)
                        else:
                            self.receiverQ.put(data)
                    else:
                        print(f'REAL {name}', data)
                elif trnm == 'PING':
                    await self.send_msg(recv_data)
                elif trnm == 'LOGIN':
                    if recv_data['return_code'] == 0:
                        if self.debug: print('LOGIN', recv_data)
                        msg = {'trnm': 'CNSRLST'}
                        await self.send_msg(msg)
                    else:
                        await self.disconnect()
                elif trnm == 'CNSRLST':
                    data = recv_data['data']
                    if self.debug: print('CNSRLST', data)
                    msg = {'trnm': 'CNSRREQ', 'seq': '1', 'search_type': '1', 'stex_tp': 'K'}
                    await self.send_msg(msg)
                elif trnm == 'CNSRREQ':
                    data = recv_data['data']
                    if not self.codes:
                        self.codes = [d['jmcode'][1:] for d in data]
                        if self.debug: print('CNSRREQ', self.codes)
                        msg = {'trnm': 'CNSRCLR', 'seq': '1'}
                        await self.send_msg(msg)
                        msg = {'trnm': 'CNSRREQ', 'seq': '0', 'search_type': '1', 'stex_tp': 'K'}
                        await self.send_msg(msg)
                    else:
                        if self.debug: print('CNSRREQ', [d['jmcode'][1:] for d in data])
                        msg = {'trnm': 'REG', 'grp_no': '1', 'refresh': '0', 'data': [{'item': [''], 'type': ['00']}]}
                        await self.send_msg(msg)
                        msg['refresh'] = '1'
                        msg['data'] = [{'item': [''], 'type': ['0s']}]
                        await self.send_msg(msg)
                        msg['data'] = [{'item': [''], 'type': ['1h']}]
                        await self.send_msg(msg)
                        msg['data'] = [{'item': ['001', '101'], 'type': ['0J']}]
                        await self.send_msg(msg)
                        msg['data'] = [{'item': self.codes[:98], 'type': ['0B', '0D']}]
                        await self.send_msg(msg)
                        # k = 0
                        # for i in range(0, len(self.codes), 100):
                        #     msg['grp_no'] = str(grp_no + k)
                        # grp_no = 2000
                        #     msg['data']   = [{'item': self.codes[i:i+100], 'type': ['0B', '0D']}]
                        #     await self.send_msg(msg)
                        #     k += 1
                elif trnm == 'REG':
                    if self.debug: print('REG', recv_data)
            except Exception as e:
                if self.debug: print('Error', e)
                await self.disconnect()


if __name__ == '__main__':
    access_key  = ''
    secret_key  = ''

    kw = Kiwooom(access_key, secret_key, debug=True)
    kw.create_token()
    kw.get_balances()
    kw.get_jango()
    kw.get_code_list(10)
    kw.get_code_list(0)

    receiverQ_, traderQ_ = Queue(), Queue()
    kw.websoket_start(receiverQ_, traderQ_, debug=True)
