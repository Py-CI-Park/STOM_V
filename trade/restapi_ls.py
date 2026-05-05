
import re
import json
import asyncio
import sqlite3
import requests
import websockets
from traceback import format_exc
from trade.restapi_lsdata import LsRestData
from PyQt5.QtCore import QThread, pyqtSignal
from utility.settings.setting_base import UI_NUM
from utility.static_method.static import now, qtest_qwait


class LsRestAPI:
    """ LS증권 RESTAPI 메인 클래스 - 국내주식, 지수선물, 미국주식, 해외선물 모두 지원"""
    def __init__(self, windowQ, access, secret):
        self.windowQ = windowQ
        self.access  = access
        self.secret  = secret
        self.token   = None
        self.tr_cont = False
        self.tr_cont_key = ''

    def _post(self, gubun: str, cont='N', cont_key='', **kwargs):
        """요청용 데이터(url, headers, params) 생성 및 전송
        인자:
            gubun: TR한글이름
            cont: 연속조회여부
            cont_key: 연속조회키
            **kwargs: TR별 키워드 - LsRestData.tr_data에 미리 선언해두고 조합한다."""
        url = f'{LsRestData.호스트주소}{LsRestData.마지막주소[gubun]}'
        if gubun == '토큰발급':
            headers = {
                'content-type': 'application/x-www-form-urlencoded'
            }
            params = {
                'grant_type': 'client_credentials',
                'appkey': self.access,
                'appsecretkey': self.secret,
                'scope': 'oob'
            }
        else:
            tr_data = LsRestData.tr_data[gubun]
            headers = {
                'content-type': 'application/json; charset=utf-8',
                'authorization': f'Bearer {self.token}',
                'tr_cd': tr_data['tr_cd'],
                'tr_cont': cont,
                'tr_cont_key': cont_key
            }
            body_key = str(tr_data['body_key'])
            element_keys = tr_data['element_keys']
            element_values = [kwargs[k] for k in tr_data['element_values']]
            params = {body_key: dict(zip(element_keys, element_values))}

        self.tr_cont = False
        self.tr_cont_key = ''

        if gubun == '토큰발급':
            response = requests.post(url, headers=headers, params=params)
        else:
            response = requests.post(url, headers=headers, data=json.dumps(params))

        self.tr_cont = True if response.headers.get('tr_cont') == 'Y' else False
        self.tr_cont_key = response.headers.get('tr_cont_key')

        return response.json()

    def create_token(self):
        """토큰 발급"""
        try:
            data = self._post('토큰발급')
            self.token = data['access_token']
            return self.token
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return None

    def get_code_info_stock(self, etfgubun=0):
        """국내주식종목정보 ['구분'], '국내주식상장주수' ['종목코드', '거래소구분코드']
        etfgubun: 0 (코스피 + 코스닥), 1 (ETF), 2 (ETN)
        data['spac_gubun'] == 'N' - 구분 무관 공통사항 스펙 제외
        data['shcode'][-1] == '0' - 우선주 및 ETN 제외(ETN일 경우 확인X)"""
        try:
            from utility.settings.setting_base import DB_SETTING
            con = sqlite3.connect(DB_SETTING)
            cur = con.cursor()
            ret = cur.execute('SELECT 시가총액상위제외목록 FROM etc').fetchall()[0][0]
            exclusion_list = ret.split(';')

            tr_name = '국내주식종목정보'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 구분='0')
            dict_data = {}
            for data in data[out_block]:
                code = data['shcode']
                gubun = int(data['etfgubun'])
                if code not in exclusion_list and gubun == etfgubun and data['spac_gubun'] == 'N' and \
                        (etfgubun == 2 or code[-1] == '0'):
                    dict_data[code] = {'종목명': data['hname']}

            tr_name = '국내주식상장주수'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            insert = False
            last = len(dict_data)
            for i, code in enumerate(dict_data.copy()):
                data = self._post(tr_name, 종목코드=code, 거래소구분코드='')
                data = data[out_block]
                현재가 = int(data['price'])
                상장주식수 = int(data['listing']) * 1000

                if 현재가 * 상장주식수 < 10_000_000_000_000:
                    dict_data[code].update({
                        '상장주식수': 상장주식수
                    })
                else:
                    insert = True
                    exclusion_list.append(code)
                    dict_data.pop(code, None)

                if i % 100 == 0 or i == last - 1:
                    self.windowQ.put((UI_NUM['기본로그'], f'국내주식 상장주식수 조회 중 ... [{i+1:04d}/{last:04d}]'))

                qtest_qwait(0.05)

            if insert:
                exclusion_text = ';'.join(exclusion_list)
                cur.execute(f"UPDATE etc SET 시가총액상위제외목록 = '{exclusion_text}'")
                con.commit()

            con.close()

            return dict_data, list(dict_data.keys())

        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return {}, []

    def get_code_info_stock_usa(self):
        """해외주식종목정보 ['지연구분', '국가구분', '거래소구분', '조회갯수', '연속구분']
        거래소구분: '1' (뉴욕거래소), '2' (나스닥)
        제외: 우선주, 채권, 워런트, ADR, 유닛, 종목명이 영문인 종목, 종목코드에 '-', '.' 이 포함된 종목"""
        try:
            tr_name = '해외주식종목정보'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data_list = []
            data = self._post(tr_name, 지연구분='R', 국가구분='US', 거래소구분='1', 조회갯수=9999, 연속구분='')
            data_list.extend(data[out_block])
            data = self._post(tr_name, 지연구분='R', 국가구분='US', 거래소구분='2', 조회갯수=9999, 연속구분='')
            data_list.extend(data[out_block])
            keysymbols = []
            dict_data = {}
            korean_pattern = re.compile(r'[\uAC00-\uD7A3]')
            for data in data_list:
                code = data['symbol']
                name = data['korname']
                if not bool(korean_pattern.search(name)) or '-' in code or '.' in code or '유닛' in name or \
                        '채권' in name or '우선주' in name or '워런트' in name or '(ADR)' in name:
                    continue
                keysymbols.append(data['keysymbol'])
                dict_data[code] = {
                    '종목명': name,
                    '거래소코드': data['exchcd'],
                    '상장주식수': int(data['share'])
                }
            return dict_data, keysymbols
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return {}, []

    def get_code_info_future(self):
        """지수선물종목정보1 ['구분'], 지수선물종목정보2 ['구분'], '파생상품증거금조회' ['종목대분류코드', '종목중분류코드']
        t8432(코스피200), t8435(미니코스피200, 코스닥150) 조회 TR이 다름
        구분: '' (코스피200), 'MF' (미니코스피200), 'SF' (코스닥150)"""
        try:
            dict_data = {}
            dict_expcode = {}

            tr_name = '지수선물종목정보1'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 구분='')
            data = data[out_block][0]
            코스피200_종목코드 = data['shcode']
            dict_data[코스피200_종목코드] = {'종목명': '코스피200'}
            dict_expcode[코스피200_종목코드] = data['expcode']

            tr_name = '지수선물종목정보2'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 구분='MF')
            data = data[out_block][0]
            미니코스피200_종목코드 = data['shcode']
            dict_data[미니코스피200_종목코드] = {'종목명': '미니코스피200'}
            dict_expcode[미니코스피200_종목코드] = data['expcode']

            data = self._post(tr_name, 구분='SF')
            data = data[out_block][0]
            코스닥150_종목코드 = data['shcode']
            dict_data[코스닥150_종목코드] = {'종목명': '코스닥150'}
            dict_expcode[코스닥150_종목코드] = data['expcode']

            tr_name = '파생상품증거금조회'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 종목대분류코드='', 종목중분류코드='')
            for data in data[out_block]:
                name = data['ShtnHanglIsuNm']
                if name == 'KOSPI200':
                    dict_data[코스피200_종목코드].update({
                        '위탁증거금': int(data['OnePrcntrOrdMgn']),
                        '호가단위': 0.05,
                        '틱가치': 250_000,
                        '소숫점자리수': 2
                    })
                elif name == '미니KOSPI200':
                    dict_data[미니코스피200_종목코드].update({
                        '위탁증거금': int(data['OnePrcntrOrdMgn']),
                        '호가단위': 0.02,
                        '틱가치': 50_000,
                        '소숫점자리수': 2
                    })
                elif name == '코스닥150':
                    dict_data[코스닥150_종목코드].update({
                        '위탁증거금': int(data['OnePrcntrOrdMgn']),
                        '호가단위': 0.1,
                        '틱가치': 100_000,
                        '소숫점자리수': 1
                    })

            return dict_data, list(dict_data.keys()), dict_expcode
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return {}, [], []

    def get_code_info_future_night(self):
        """야간선물종목정보 ['구분'], 파생상품증거금조회 ['종목대분류코드', '종목중분류코드']
        구분: 'NF' (코스피200), 'NMF' (미니코스피200), 'NQF' (코스닥150)"""
        try:
            dict_data = {}
            dict_expcode = {}

            tr_name = '야간선물종목정보'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 구분='NFU')
            data = data[out_block][0]
            코스피200_종목코드 = data['shcode']
            dict_data[코스피200_종목코드] = {'종목명': '코스피200'}
            dict_expcode[코스피200_종목코드] = data['expcode']

            data = self._post(tr_name, 구분='NMF')
            data = data[out_block][0]
            미니코스피200_종목코드 = data['shcode']
            dict_data[미니코스피200_종목코드] = {'종목명': '미니코스피200'}
            dict_expcode[미니코스피200_종목코드] = data['expcode']

            qtest_qwait(1)

            data = self._post(tr_name, 구분='NQF')
            data = data[out_block][0]
            코스닥150_종목코드 = data['shcode']
            dict_data[코스닥150_종목코드] = {'종목명': '코스닥150'}
            dict_expcode[코스닥150_종목코드] = data['expcode']

            tr_name = '파생상품증거금조회'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 종목대분류코드='', 종목중분류코드='')
            for data in data[out_block]:
                name = data['ShtnHanglIsuNm']
                if name == 'KOSPI200':
                    dict_data[코스피200_종목코드].update({
                        '위탁증거금': int(data['OnePrcntrOrdMgn']),
                        '호가단위': 0.05,
                        '틱가치': 250_000,
                        '소숫점자리수': 2
                    })
                elif name == '미니KOSPI200':
                    dict_data[미니코스피200_종목코드].update({
                        '위탁증거금': int(data['OnePrcntrOrdMgn']),
                        '호가단위': 0.02,
                        '틱가치': 50_000,
                        '소숫점자리수': 2
                    })
                elif name == '코스닥150':
                    dict_data[코스닥150_종목코드].update({
                        '위탁증거금': int(data['OnePrcntrOrdMgn']),
                        '호가단위': 0.1,
                        '틱가치': 100_000,
                        '소숫점자리수': 1
                    })

            return dict_data, list(dict_data.keys()), dict_expcode
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return {}, [], []

    def get_code_info_future_oversea(self):
        """해외선물종목정보 ['구분']"""
        try:
            tr_name = '해외선물종목정보'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 구분='')
            dict_data = {}
            for data in data[out_block]:
                name = data['BscGdsNm'].replace(' ', '_')
                dict_data[data['Symbol']] = {
                    '종목명': name,
                    '위탁증거금': int(float(data['OpngMgn'])),
                    '호가단위': float(data['UntPrc']),
                    '틱가치': float(data['MnChgAmt']),
                    '소숫점자리수': int(data['DotGb'])
                }
            return dict_data, list(dict_data.keys())
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return {}, []

    def get_balance_stock(self):
        """국내주식예수금 ['레코드갯수', '잔고생성구분']"""
        try:
            tr_name = '국내주식예수금'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 레코드갯수=1, 잔고생성구분='1')
            return int(data[out_block]['D2Dps'])
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return 0

    def get_balance_stock_usa(self):
        """해외주식예수금 ['레코드갯수', '통화코드']"""
        try:
            tr_name = '해외주식예수금'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 레코드갯수=1, 통화코드='USD')
            return int(data[out_block]['FcurrDps'])
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return 0

    def get_balance_future(self):
        """지수선물예수금 ['레코드갯수']"""
        try:
            tr_name = '지수선물예수금'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 레코드갯수=1)
            return int(data[out_block]['Dps'])
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return 0

    def get_balance_future_oversea(self):
        """ 해외선물예수금 ['계좌구분코드', '거래일자']"""
        try:
            tr_name = '해외선물예수금'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 계좌구분코드='1', 거래일자=LsRestData.당일일자)
            return int(data[out_block]['FcurrOrdAbleAmt'])
        except Exception:
            self.windowQ.put((UI_NUM['시스템로그'], format_exc()))
            return 0

    def order_stock(self, 종목코드, 주문구분, 주문수량, 주문가격, 호가유형):
        """국내주식일반주문
        ['종목코드', '주문수량', '주문가격', '주문구분코드', '호가유형코드', '신용거래코드', '대출일', '주문조건코드', '회원사번호']"""
        try:
            tr_name = '국내주식일반주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            주문구분코드 = LsRestData.국내주식주문구분코드[주문구분]
            호가유형코드 = LsRestData.국내주식호가유형코드[호가유형]
            주문조건코드 = LsRestData.국내주식주문조건코드[호가유형]
            data = self._post(tr_name, 종목코드=종목코드, 주문수량=주문수량, 주문가격=주문가격, 주문구분코드=주문구분코드, 호가유형코드=호가유형코드,
                              신용거래코드='000', 대출일='', 주문조건코드=주문조건코드, 회원사번호='')
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_modify_stock(self, 종목코드, 원주문번호, 주문수량, 주문가격, 호가유형):
        """국내주식정정주문 ['원주문번호', '종목코드', '주문수량', '호가유형코드', '주문조건코드', '주문가격']"""
        try:
            tr_name = '국내주식정정주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            호가유형코드 = LsRestData.국내주식호가유형코드[호가유형]
            주문조건코드 = LsRestData.국내주식주문조건코드[호가유형]
            data = self._post(tr_name, 원주문번호=원주문번호, 종목코드=종목코드, 주문수량=주문수량, 호가유형코드=호가유형코드,
                              주문조건코드=주문조건코드, 주문가격=주문가격)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_cancel_stock(self, 종목코드, 원주문번호, 주문수량):
        """국내주식취소주문 ['원주문번호', '종목코드', '주문수량']"""
        try:
            tr_name = '국내주식취소주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 원주문번호=원주문번호, 종목코드=종목코드, 주문수량=주문수량)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_stock_usa(self, 종목코드, 주문구분, 주문시장코드, 주문수량, 주문가격, 호가유형, 원주문번호=''):
        """해외주식일반주문
        ['레코드갯수', '주문구분코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격', '호가유형코드', '중개인구분코드']"""
        try:
            tr_name = '해외주식일반주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            주문구분코드 = LsRestData.해외주식주문구분코드[주문구분]
            호가유형코드 = LsRestData.해외주식호가유형코드[호가유형]
            if 주문구분 in ('매수', '매도'):
                data = self._post(tr_name, 레코드갯수=1, 주문구분코드=주문구분코드, 주문시장코드=주문시장코드, 종목코드=종목코드,
                                  주문수량=주문수량, 주문가격=주문가격, 호가유형코드=호가유형코드, 중개인구분코드='')
            else:
                data = self._post(tr_name, 레코드갯수=1, 주문구분코드=주문구분코드, 원주문번호=원주문번호, 주문시장코드=주문시장코드,
                                  종목코드=종목코드, 주문수량=주문수량, 주문가격=주문가격, 호가유형코드=호가유형코드, 중개인구분코드='')
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_modify_stock_usa(self, 종목코드, 원주문번호, 주문구분, 주문시장코드, 주문수량, 주문가격, 호가유형):
        """해외주식정정주문
        ['레코드갯수', '주문구분코드', '원주문번호', '주문시장코드', '종목코드', '주문수량', '주문가격', '호가유형코드', '중개인구분코드']"""
        try:
            tr_name = '해외주식정정주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            주문구분코드 = LsRestData.해외주식주문구분코드[주문구분]
            호가유형코드 = LsRestData.해외주식호가유형코드[호가유형]
            data = self._post(tr_name, 레코드갯수=1, 주문구분코드=주문구분코드, 원주문번호=원주문번호, 주문시장코드=주문시장코드,
                              종목코드=종목코드, 주문수량=주문수량, 주문가격=주문가격, 호가유형코드=호가유형코드, 중개인구분코드='')
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_future(self, 종목코드, 주문구분, 주문가격, 주문수량, 호가유형):
        """지수선물일반주문 ['종목코드', '주문구분코드', '호가유형코드', '주문가격', '주문수량']"""
        try:
            tr_name = '지수선물일반주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            주문구분코드 = LsRestData.선물주문구분코드[주문구분]
            호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
            data = self._post(tr_name, 종목코드=종목코드, 주문구분코드=주문구분코드, 호가유형코드=호가유형코드, 주문가격=주문가격, 주문수량=주문수량)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_modify_future(self, 종목코드, 원주문번호, 주문가격, 주문수량, 호가유형):
        """지수선물정정주문 ['종목코드', '원주문번호', '호가유형코드', '주문가격', '주문수량']"""
        try:
            tr_name = '지수선물정정주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
            data = self._post(tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 호가유형코드=호가유형코드, 주문가격=주문가격, 주문수량=주문수량)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_cancel_future(self, 종목코드, 원주문번호, 주문수량):
        """지수선물취소주문 ['종목코드', '원주문번호', '주문수량']"""
        try:
            tr_name = '지수선물취소주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post( tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 주문수량=주문수량)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_future_night(self, 종목코드, 주문구분, 주문가격, 주문수량, 호가유형):
        """야간선물일반주문 ['종목코드', '주문구분코드', '호가유형코드', '주문가격', '주문수량']"""
        try:
            tr_name = '야간선물일반주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            주문구분코드 = LsRestData.선물주문구분코드[주문구분]
            호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
            data = self._post(tr_name, 종목코드=종목코드, 주문구분코드=주문구분코드, 호가유형코드=호가유형코드, 주문가격=주문가격,
                              주문수량=주문수량)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_modify_future_night(self, 종목코드, 원주문번호, 주문가격, 주문수량, 호가유형):
        """야간선물정정주문 ['종목코드', '원주문번호', '호가유형코드', '주문가격', '주문수량']"""
        try:
            tr_name = '야간선물정정주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            호가유형코드 = LsRestData.지수선물호가유형코드[호가유형]
            data = self._post( tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 호가유형코드=호가유형코드, 주문가격=주문가격,
                               주문수량=주문수량)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_cancel_future_night(self, 종목코드, 원주문번호, 주문수량):
        """야간선물취소주문 ['종목코드', '원주문번호', '주문수량']"""
        try:
            tr_name = '야간선물취소주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post( tr_name, 종목코드=종목코드, 원주문번호=원주문번호, 주문수량=주문수량)
            return data[out_block]['OrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_future_oversea(self, 종목코드, 주문구분, 주문가격, 주문수량, 주문유형, 조건주문가격=0):
        """해외선물일반주문
        ['주문일자', '종목코드', '주문구분', '주문구분코드', '호가유형코드', '통화코드', '주문가격', '조건주문가격', '주문수량',
        '상품코드', '만기년월', '거래소코드']"""
        try:
            tr_name = '해외선물일반주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            주문구분코드 = LsRestData.선물주문구분코드[주문구분]
            호가유형코드 = LsRestData.해외선물호가유형코드[주문유형]
            data = self._post(tr_name, 주문일자=LsRestData.당일일자, 종목코드=종목코드, 주문구분='1', 주문구분코드=주문구분코드,
                              호가유형코드=호가유형코드, 통화코드=' ',  주문가격=주문가격, 조건주문가격=조건주문가격,
                              주문수량=주문수량, 상품코드='000000', 만기년월='000001', 거래소코드=' ')
            return data[out_block]['OvrsFutsOrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_modify_future_oversea(self, 종목코드, 원주문번호, 주문구분, 주문가격, 주문수량, 주문유형, 조건주문가격=0):
        """해외선물정정주문
        ['주문일자', '원주문번호', '종목코드', '주문구분', '주문구분코드', '호가유형코드', '통화코드', '주문가격', '조건주문가격',
        '주문수량', '상품코드', '만기년월', '거래소코드']"""
        try:
            tr_name = '해외선물정정주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            주문구분코드 = LsRestData.선물주문구분코드[주문구분]
            호가유형코드 = LsRestData.해외선물호가유형코드[주문유형]
            data = self._post(tr_name, 주문일자=LsRestData.당일일자, 원주문번호=원주문번호, 종목코드=종목코드, 주문구분='2',
                              주문구분코드=주문구분코드, 호가유형코드=호가유형코드, 통화코드=' ', 주문가격=주문가격,
                              조건주문가격=조건주문가격, 주문수량=주문수량, 상품코드='', 만기년월='', 거래소코드=' ')
            return data[out_block]['OvrsFutsOrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()

    def order_cancel_future_oversea(self, 종목코드, 원주문번호):
        """해외선물취소주문 ['주문일자', '종목코드', '원주문번호', '주문구분', '상품구분코드', '거래소코드']"""
        try:
            tr_name = '해외선물취소주문'
            out_block = LsRestData.tr_data[tr_name]['out_block']
            data = self._post(tr_name, 주문일자=LsRestData.당일일자, 종목코드=종목코드, 원주문번호=원주문번호, 주문구분='3',
                              상품구분코드=' ', 거래소코드=' ')
            return data[out_block]['OvrsFutsOrdNo'], data['rsp_msg']
        except Exception:
            return 0, format_exc()


class LsWebSocketReceiver(QThread):
    signal = pyqtSignal(dict)

    def __init__(self, gubun, token, symbols, windowQ):
        super().__init__()
        self.gubun     = gubun
        self.token     = token
        self.symbols   = symbols
        self.windowQ   = windowQ
        self.loop      = None
        self.websocket = None
        self.connected = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run())
        self.loop.run_forever()

    async def _run(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                    asyncio.create_task(self._real_reg())
                await self._receive_message()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], f'{format_exc()}오류 알림 - LsWebSocketReceiver'))

            await self._disconnect()

    async def _connect(self):
        self.websocket = await websockets.connect(LsRestData.웹소켓주소, ping_interval=60)
        self.connected = True

    async def _receive_message(self):
        while self.connected:
            data = await self.websocket.recv()
            data = json.loads(data)
            if data['body']:
                self.signal.emit(data)

    async def _real_reg(self):
        while not self.connected:
            await asyncio.sleep(0.1)

        data = self._get_send_data('장운영정보', '0')
        await self.websocket.send(json.dumps(data))
        await asyncio.sleep(0.02)
        self.windowQ.put((UI_NUM['기본로그'], '장운영정보 실시간시세 등록'))

        if self.gubun == '국내주식':
            gubun = f'{self.gubun}VI'
            data = self._get_send_data(gubun, '0000000000')
            await self.websocket.send(json.dumps(data))
            await asyncio.sleep(0.02)
            self.windowQ.put((UI_NUM['기본로그'], f'{gubun}발동해제 실시간시세 등록'))

        last = len(self.symbols)
        gubun = f'{self.gubun}체결'
        for i, code in enumerate(self.symbols):
            data = self._get_send_data(gubun, code)
            await self.websocket.send(json.dumps(data))
            await asyncio.sleep(0.02)

            if i % 100 == 0 or i == last - 1:
                self.windowQ.put((UI_NUM['기본로그'], f'{gubun} 실시간시세 등록 [{i+1:04d}/{last:04d}]'))

        gubun = f'{self.gubun}호가'
        for i, code in enumerate(self.symbols):
            data = self._get_send_data(gubun, code)
            await self.websocket.send(json.dumps(data))
            await asyncio.sleep(0.02)

            if i % 100 == 0 or i == last - 1:
                self.windowQ.put((UI_NUM['기본로그'], f'{gubun} 실시간시세 등록 [{i+1:04d}/{last:04d}]'))

    def _get_send_data(self, gubun: str, code: str):
        if gubun in ('국내주식체결', '국내주식호가'):
            tr_key = f'U{code:<9}'
        elif '해외주식' in gubun:
            tr_key = f'{code:<18}'
        else:
            tr_key = code

        data = {
            'header': {
                'token': self.token,
                'tr_type': '3'
            },
            'body': {
                'tr_cd': LsRestData.실시간거래코드[gubun],
                'tr_key': tr_key
            }
        }
        return data

    async def _disconnect(self):
        self.connected = False
        if self.websocket is not None:
            await self.websocket.close()
        await asyncio.sleep(1)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()


class LsWebSocketTrader(QThread):
    signal = pyqtSignal(dict)

    def __init__(self, market, token, windowQ):
        super().__init__()
        self.market    = market
        self.token     = token
        self.windowQ   = windowQ
        self.loop      = None
        self.websocket = None
        self.connected = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self._run())
        self.loop.run_forever()

    async def _run(self):
        while True:
            try:
                if not self.connected:
                    await self._connect()
                await self._receive_message()
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], f'{format_exc()}오류 알림 - LsWebSocketTrader'))

            await self._disconnect()

    async def _connect(self):
        self.websocket = await websockets.connect(LsRestData.웹소켓주소, ping_interval=60)
        self.connected = True
        for k, v in LsRestData.주문거래코드.items():
            if self.market in k:
                data = self._get_send_data(v)
                await self.websocket.send(json.dumps(data))
                self.windowQ.put((UI_NUM['기본로그'], f'{k} 실시간시세 계좌등록'))

    async def _receive_message(self):
        while self.connected:
            data = await self.websocket.recv()
            data = json.loads(data)
            if data['body']:
                self.signal.emit(data)

    def _get_send_data(self, tr_cd: str):
        data = {
            'header': {
                'token': self.token,
                'tr_type': '1'
            },
            'body': {
                'tr_cd': tr_cd,
                'tr_key': ''
            }
        }
        return data

    async def _disconnect(self):
        self.connected = False
        if self.websocket is not None:
            await self.websocket.close()
        await asyncio.sleep(1)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.stop()


class MonitorWindowQ(QThread):
    signal = pyqtSignal(str)

    def __init__(self, windowQ):
        super().__init__()
        self.windowQ = windowQ

    def run(self):
        while True:
            data = self.windowQ.get()
            self.signal.emit(data[1])


if __name__ == "__main__":
    """
    테스트 코드
    gubun_ 입력: 국내주식, 국내주식ETF, 국내주식ETN, 지수선물, 야간선물, 해외주식, 해외선물
    """
    import sys
    from multiprocessing import Queue
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    gubun_ = '지수선물'
    access_key = ''
    secret_key = ''

    windowQ_ = Queue()

    ls = LsRestAPI(windowQ_, access_key, secret_key)
    token_ = ls.create_token()

    dict_expcode_ = None
    if gubun_ == '국내주식':
        dict_info, symbols_ = ls.get_code_info_stock(etfgubun=0)
    elif gubun_ == '국내주식ETF':
        dict_info, symbols_ = ls.get_code_info_stock(etfgubun=1)
    elif gubun_ == '국내주식ETN':
        dict_info, symbols_ = ls.get_code_info_stock(etfgubun=2)
    elif gubun_ == '지수선물':
        dict_info, symbols_, dict_expcode_ = ls.get_code_info_future()
    elif gubun_ == '야간선물':
        dict_info, symbols_, dict_expcode_ = ls.get_code_info_future_night()
    elif gubun_ == '해외주식':
        dict_info, symbols_ = ls.get_code_info_stock_usa()
    else:
        dict_info, symbols_ = ls.get_code_info_future_oversea()

    print(dict_info)
    print()
    print(symbols_)
    print()
    if dict_expcode_ is not None:
        print(dict_expcode_)
        print()

    def real_data_print(data):
        print(f'[{now()}] {data}')

    writer = MonitorWindowQ(windowQ_)
    writer.signal.connect(real_data_print)
    writer.start()

    ws_thread = LsWebSocketReceiver(gubun_, token_, symbols_, windowQ_)
    ws_thread.signal.connect(real_data_print)
    ws_thread.start()

    app.exec_()
