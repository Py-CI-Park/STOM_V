
import os
import sqlite3
from traceback import format_exc
from utility.lazy_imports import get_pd
from utility.setting_base import ui_num, columns_hj, DB_PATH, DB_COIN_TICK_BACK, \
    DB_STOCK_TICK_BACK, DB_COIN_MIN_BACK, DB_STOCK_MIN_BACK, DB_FUTURE_MIN_BACK, DB_FUTURE_TICK_BACK, \
    list_stock_tick, list_stock_min, list_coin_tick, list_coin_min


class Hoga:
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ   = qlist[0]
        self.hogaQ     = qlist[5]
        self.dict_set  = dict_set
        self.gubun     = None
        self.hoga_name = None
        self.dict_hj   = None
        self.dict_hc   = None
        self.dict_hg   = None
        self.InitHoga('S')

        self.fi = {
            '현재가': list_stock_tick.index('현재가'),
            '시가': list_stock_tick.index('시가'),
            '고가': list_stock_tick.index('고가'),
            '저가': list_stock_tick.index('저가'),
            '등락율': list_stock_tick.index('등락율'),
            '시가총액': list_stock_tick.index('시가총액'),
            'VI가격': list_stock_tick.index('VI가격'),

            '주식틱봉호가시작': list_stock_tick.index('매도호가5'),
            '주식틱봉호가종료': list_stock_tick.index('매수호가5') + 1,
            '주식틱봉잔량시작': list_stock_tick.index('매도잔량5'),
            '주식틱봉잔량종료': list_stock_tick.index('매수잔량5') + 1,
            '주식틱봉매도총잔': list_stock_tick.index('매도총잔량'),
            '주식틱봉매수총잔': list_stock_tick.index('매수총잔량'),

            '주식분봉호가시작': list_stock_min.index('매도호가5'),
            '주식분봉호가종료': list_stock_min.index('매수호가5') + 1,
            '주식분봉잔량시작': list_stock_min.index('매도잔량5'),
            '주식분봉잔량종료': list_stock_min.index('매수잔량5') + 1,
            '주식분봉매도총잔': list_stock_min.index('매도총잔량'),
            '주식분봉매수총잔': list_stock_min.index('매수총잔량'),

            '그외틱봉호가시작': list_coin_tick.index('매도호가5'),
            '그외틱봉호가종료': list_coin_tick.index('매수호가5') + 1,
            '그외틱봉잔량시작': list_coin_tick.index('매도잔량5'),
            '그외틱봉잔량종료': list_coin_tick.index('매수잔량5') + 1,
            '그외틱봉매도총잔': list_coin_tick.index('매도총잔량'),
            '그외틱봉매수총잔': list_coin_tick.index('매수총잔량'),

            '그외분봉호가시작': list_coin_min.index('매도호가5'),
            '그외분봉호가종료': list_coin_min.index('매수호가5') + 1,
            '그외분봉잔량시작': list_coin_min.index('매도잔량5'),
            '그외분봉잔량종료': list_coin_min.index('매수잔량5') + 1,
            '그외분봉매도총잔': list_coin_min.index('매도총잔량'),
            '그외분봉매수총잔': list_coin_min.index('매수총잔량')
        }

        self.MainLoop()

    def MainLoop(self):
        while True:
            data = self.hogaQ.get()
            try:
                if data[0] == '설정변경':
                    self.dict_set = data[1]
                elif len(data) == 8:
                    self.UpdateHogaJongmok(data)
                elif len(data) == 2:
                    self.UpdateChegeolcount(data)
                elif len(data) == 4:
                    self.UpdateHogaForChart(data)
                else:
                    if self.hoga_name == data[0]:
                        self.UpdateHogajalryang(data)
                        if self.gubun is not None:
                            if self.dict_hj is not None:
                                self.windowQ.put((ui_num[f'{self.gubun}호가종목'], get_pd().DataFrame([self.dict_hj])))
                            if self.dict_hc is not None:
                                self.windowQ.put((ui_num[f'{self.gubun}호가체결'], get_pd().DataFrame(self.dict_hc)))
                            if self.dict_hg is not None:
                                self.windowQ.put((ui_num[f'{self.gubun}호가잔량'], get_pd().DataFrame(self.dict_hg)))
            except:
                self.windowQ.put((ui_num['시스템로그'], format_exc()))

    def InitHoga(self, gubun):
        self.dict_hj = {
            '종목명': '', '현재가': 0., '등락율': 0., '시가총액': 0, 'UVI': 0., '시가': 0., '고가': 0., '저가': 0.
        }
        self.dict_hc = {
            '체결수량': [0.] * 12, '체결강도': [0.] * 12
        }
        self.dict_hg = {
            '잔량': [0.] * 12, '호가': [0.] * 12
        }
        self.windowQ.put((ui_num[f'{gubun}호가종목'], get_pd().DataFrame([self.dict_hj])))
        self.windowQ.put((ui_num[f'{gubun}호가체결'], get_pd().DataFrame(self.dict_hc)))
        self.windowQ.put((ui_num[f'{gubun}호가잔량'], get_pd().DataFrame(self.dict_hg)))
        self.hoga_name = ''

    def UpdateHogaJongmok(self, data):
        종목명, 현재가, 등락율, 시가총액, UVI, 시가, 고가, 저가 = data
        self.gubun = 'C' if 'KRW' in 종목명 or 'USDT' in 종목명 else 'S'
        if self.hoga_name != 종목명:
            self.InitHoga(self.gubun)
            self.hoga_name = 종목명

        self.dict_hj = {
            '종목명': 종목명, '현재가': 현재가, '등락율': 등락율, '시가총액': 시가총액,
            'UVI': UVI, '시가': 시가, '고가': 고가, '저가': 저가
        }

    def UpdateChegeolcount(self, data):
        v, ch = data
        if 'KRW' in self.hoga_name or 'USDT' in self.hoga_name:
            if v > 0:
                tbc = round(self.dict_hc['체결수량'][0] + v, 8)
                tsc = round(self.dict_hc['체결수량'][11], 8)
            else:
                tbc = round(self.dict_hc['체결수량'][0], 8)
                tsc = round(self.dict_hc['체결수량'][11] + abs(v), 8)
        else:
            if v > 0:
                tbc = self.dict_hc['체결수량'][0] + v
                tsc = self.dict_hc['체결수량'][11]
            else:
                tbc = self.dict_hc['체결수량'][0]
                tsc = self.dict_hc['체결수량'][11] + abs(v)

        hch = self.dict_hc['체결강도'][0]
        lch = self.dict_hc['체결강도'][11]

        if hch < ch:
            hch = ch
        if lch == 0 or lch > ch:
            lch = ch

        self.dict_hc['체결수량'] = [tbc, v] + self.dict_hc['체결수량'][1:10] + [tsc]
        self.dict_hc['체결강도'] = [hch, ch] + self.dict_hc['체결강도'][1:10] + [lch]

    def UpdateHogajalryang(self, data):
        jr = [data[1]] + list(data[13:23]) + [data[2]]
        if 'KRW' in self.hoga_name or 'USDT' in self.hoga_name or '해외선물' in self.dict_set['증권사']:
            hg = [self.dict_hj['고가']] + list(data[3:13]) + [self.dict_hj['저가']]
        else:
            hg = [data[23]] + [round(x) for x in data[3:13]] + [data[24]]

        self.dict_hg['잔량'] = jr
        self.dict_hg['호가'] = hg

    def UpdateHogaForChart(self, data):
        cmd, code, name, index = data
        searchdate = index[:8]
        gubun = 'C' if 'KRW' in code or 'USDT' in code else 'S'
        index = int(index)
        self.InitHoga(gubun)

        if gubun == 'C':
            db_name1 = f'{DB_PATH}/coin_tick_{searchdate}.db' if self.dict_set['코인타임프레임'] else f'{DB_PATH}/coin_min_{searchdate}.db'
            db_name2 = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
        else:
            if '키움증권' in self.dict_set['증권사']:
                db_name1 = f'{DB_PATH}/stock_tick_{searchdate}.db' if self.dict_set['주식타임프레임'] else f'{DB_PATH}/stock_min_{searchdate}.db'
                db_name2 = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
            else:
                db_name1 = f'{DB_PATH}/future_tick_{searchdate}.db' if self.dict_set['주식타임프레임'] else f'{DB_PATH}/future_min_{searchdate}.db'
                db_name2 = DB_FUTURE_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN_BACK

        if cmd == '이전호가정보요청':
            query = f"SELECT * FROM '{code}' WHERE `index` < {index} ORDER BY `index` DESC LIMIT 1"
        elif cmd == '다음호가정보요청':
            query = f"SELECT * FROM '{code}' WHERE `index` > {index} ORDER BY `index` LIMIT 1"
        else:
            query = f"SELECT * FROM '{code}' WHERE `index` = {index}"

        df = None
        try:
            if os.path.isfile(db_name1):
                con = sqlite3.connect(db_name1)
                df = get_pd().read_sql(query, con)
                con.close()
            elif os.path.isfile(db_name2):
                con = sqlite3.connect(db_name2)
                df = get_pd().read_sql(query, con)
                con.close()
        except:
            pass

        if df is not None and len(df) > 0:
            data = list(df.iloc[0])
            if gubun == 'C' or '해외선물' in self.dict_set['증권사']:
                hj = [
                    name, data[self.fi['현재가']], data[self.fi['등락율']], 0, 0,
                    data[self.fi['시가']], data[self.fi['고가']], data[self.fi['저가']]
                ]

                if (gubun == 'C' and self.dict_set['코인타임프레임']) or \
                        ('해외선물' in self.dict_set['증권사'] and self.dict_set['주식타임프레임']):
                    jr = [data[self.fi['그외틱봉매도총잔']]] + data[self.fi['그외틱봉잔량시작']:self.fi['그외틱봉잔량종료']] + [data[self.fi['그외틱봉매수총잔']]]
                    hg = [data[self.fi['고가']]]  + data[self.fi['그외틱봉호가시작']:self.fi['그외틱봉호가종료']] + [self.fi['저가']]
                else:
                    jr = [data[self.fi['그외분봉매도총잔']]] + data[self.fi['그외분봉잔량시작']:self.fi['그외분봉잔량종료']] + [data[self.fi['그외분봉매수총잔']]]
                    hg = [data[self.fi['고가']]]  + data[self.fi['그외분봉호가시작']:self.fi['그외분봉호가종료']] + [data[self.fi['저가']]]
            else:
                hj = [
                    name, data[self.fi['현재가']], data[self.fi['등락율']], data[self.fi['시가총액']], data[self.fi['VI가격']],
                    data[self.fi['시가']], data[self.fi['고가']], data[self.fi['저가']]
                ]

                if self.dict_set['주식타임프레임']:
                    jr = [data[self.fi['주식틱봉매도총잔']]] + data[self.fi['주식틱봉잔량시작']:self.fi['주식틱봉잔량종료']] + [data[self.fi['주식틱봉매수총잔']]]
                    hg = [data[self.fi['고가']]] + data[self.fi['주식틱봉호가시작']:self.fi['주식틱봉호가종료']] + [data[self.fi['저가']]]
                else:
                    jr = [data[self.fi['주식분봉매도총잔']]] + data[self.fi['주식분봉잔량시작']:self.fi['주식분봉잔량종료']] + [data[self.fi['주식분봉매수총잔']]]
                    hg = [data[self.fi['고가']]] + data[self.fi['주식분봉호가시작']:self.fi['주식분봉호가종료']] + [data[self.fi['저가']]]

            df_hj = get_pd().DataFrame([hj], columns=columns_hj)
            df_hg = get_pd().DataFrame({'잔량': jr, '호가': hg})
            self.windowQ.put((ui_num[f'{gubun}호가종목'], df_hj, str(int(data[0]))))
            self.windowQ.put((ui_num[f'{gubun}호가잔량'], df_hg))
