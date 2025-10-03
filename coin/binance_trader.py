import re
import sys
import time
import sqlite3
import binance
import pandas as pd
from PyQt5.QtCore import QTimer
from multiprocessing import Process
from coin.binance_websocket import WebSocketTrader
from utility.setting import columns_cj, columns_tj, columns_tdf, columns_jgf, columns_tt, ui_num, DB_TRADELIST, DICT_SET
from utility.static import now, timedelta_sec, GetBinanceShortPgSgSp, GetBinanceLongPgSgSp, str_ymd, str_hms, \
    threading_timer, error_decorator, now_utc, str_ymdhmsf, str_hmsf


class BinanceTrader:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ          = qlist[0]
        self.soundQ           = qlist[1]
        self.queryQ           = qlist[2]
        self.teleQ            = qlist[3]
        self.creceivQ         = qlist[8]
        self.ctraderQ         = qlist[9]
        self.cstgQ            = qlist[10]
        self.liveQ            = qlist[11]
        self.dict_set         = DICT_SET

        self.dict_info        = {}
        self.dict_curc        = {}
        self.dict_lvrg        = {}
        self.dict_order       = {'BUY_LONG': {}, 'SELL_LONG': {}, 'SELL_SHORT': {}, 'BUY_SHORT': {}}
        self.dict_pos         = {}

        self.proc_webs = None

        self.df_cj = pd.DataFrame(columns=columns_cj)
        self.df_jg = pd.DataFrame(columns=columns_jgf)
        self.df_tj = pd.DataFrame(columns=columns_tj)
        self.df_td = pd.DataFrame(columns=columns_tdf)
        self.df_tt = pd.DataFrame(columns=columns_tt)

        self.str_today = str_ymd(now_utc())

        self.dict_intg = {
            '예수금': 0.,
            '추정예수금': 0.,
            '추정예탁자산': 0.,
            '종목당투자금': 0
        }
        self.dict_bool = {
            '실현손익저장': False,
            '코인잔고청산': False,
            '프로세스종료': False
        }
        curr_time = now()
        self.dict_time = {
            '주문시간': curr_time,
            '잔고전송': curr_time,
            '잔고갱신및주문취소확인': curr_time
        }

        self.binance = binance.Client(self.dict_set['Access_key2'], self.dict_set['Secret_key2'])
        self.LoadDatabase()
        self.GetBalances()
        self.SetPosition()
        self.MainLoop()

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        self.df_cj = pd.read_sql(f"SELECT * FROM c_chegeollist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        self.df_td = pd.read_sql(f"SELECT * FROM c_tradelist_future WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        self.df_jg = pd.read_sql(f'SELECT * FROM c_jangolist_future', con).set_index('index')
        con.close()

        if len(self.df_cj) > 0: self.windowQ.put((ui_num['C체결목록'], self.df_cj[::-1]))
        if len(self.df_td) > 0: self.windowQ.put((ui_num['C거래목록'], self.df_td[::-1]))
        if len(self.df_jg) > 0: self.creceivQ.put(('잔고목록', tuple(self.df_jg.index)))

        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 불러오기 완료'))

    def GetBalances(self):
        cbg = 0
        for index in self.df_jg.index:
            cbg += self.df_jg['매입가'][index] * round(self.df_jg['보유수량'][index] / self.df_jg['레버리지'][index], 4)

        if self.dict_set['코인모의투자']:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql('SELECT * FROM c_tradelist_future', con)
            con.close()
            tcg = df['수익금'].sum()
            chujeonjasan = 100000 + tcg
        else:
            datas = self.binance.futures_account_balance()
            chujeonjasan = [float(data['balance']) for data in datas if data['asset'] == 'USDT'][0]

        self.dict_intg['예수금'] = round(chujeonjasan - cbg, 4)
        self.dict_intg['추정예수금'] = round(chujeonjasan - cbg, 4)
        self.dict_intg['추정예탁자산'] = chujeonjasan

        if len(self.df_td) > 0:
            self.UpdateTotaltradelist(first=True)

        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 예수금 조회 완료'))

    def SetPosition(self):
        def get_decimal_place(float_):
            float_ = str(float(float_))
            float_ = float_.split('.')[1]
            return 0 if float_ == '0' else len(float_)

        dummy_time = timedelta_sec(-3600)
        datas = self.binance.futures_exchange_info()
        datas = [x for x in datas['symbols'] if re.search('USDT$', x['symbol']) is not None]
        self.dict_info = {
            x['symbol']: {
                '호가단위': float(x['filters'][0]['tickSize']),
                '소숫점자리수': get_decimal_place(x['filters'][2]['minQty']),
                '시드부족시간': dummy_time,
                '최종거래시간': dummy_time,
                '손절거래시간': dummy_time
            } for x in datas
        }

        codes = list(self.dict_info.keys())
        if self.dict_set['바이낸스선물고정레버리지']:
            self.dict_lvrg = {x: self.dict_set['바이낸스선물고정레버리지값'] for x in codes}
        else:
            self.dict_lvrg = {x: 1 for x in codes}

        self.cstgQ.put(('바낸선물단위정보', self.dict_info))
        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 호가단위 및 소숫점자리수 조회 완료'))

        if not self.dict_set['코인모의투자']:
            for code in codes:
                try:
                    if self.dict_set['바이낸스선물고정레버리지']:
                        self.binance.futures_change_leverage(symbol=code, leverage=self.dict_set['바이낸스선물고정레버리지값'])
                    else:
                        self.binance.futures_change_leverage(symbol=code, leverage=1)
                    self.binance.futures_change_margin_type(symbol=code, marginType=self.dict_set['바이낸스선물마진타입'])
                except:
                    pass
            try:
                self.binance.futures_change_position_mode(dualSidePosition=self.dict_set['바이낸스선물포지션'])
            except:
                pass

        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 마진타입 및 레버리지 설정 완료'))

    def MainLoop(self):
        text = '코인 전략연산 및 트레이더를 시작하였습니다.'
        if self.dict_set['코인알림소리']: self.soundQ.put(text)
        self.teleQ.put(text)
        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 트레이더 시작'))
        self.WebSocketsStart(self.ctraderQ)
        while True:
            curr_time = now()
            inthmsutc = int(str_hms(now_utc()))
            if not self.ctraderQ.empty():
                data = self.ctraderQ.get()
                if type(data) == tuple:
                    self.UpdateTuple(data)
                elif type(data) == str:
                    self.UpdateString(data)
                elif type(data) == list:
                    if data[0] == 'user':
                        data = data[1]
                        if data['e'] == 'ACCOUNT_UPDATE':
                            try:
                                data = data['a']
                                self.dict_intg['추정예탁자산'] = float(data['B'][0]['wb'])
                                self.dict_intg['예수금'] = float(data['B'][0]['cw'])
                            except Exception as e:
                                self.windowQ.put((ui_num['C단순텍스트'], f'시스템 명령 오류 알림 - 웹소켓 user {e}'))
                        elif data['e'] == 'ORDER_TRADE_UPDATE':
                            try:
                                data = data['o']
                                code = data['s']
                                p    = f"{data['S']}_{self.dict_pos[code]}"
                                if data['X'] == 'CANCELED':
                                    p = f'{p}_CANCEL'
                                oc   = float(data['q'])
                                cc   = float(data['l'])
                                mc   = round(oc - float(data['z']), self.dict_info[code]['소숫점자리수'])
                                cp   = float(data['L'])
                                op   = float(data['p'])
                                on   = int(data['i'])
                            except:
                                print('바이낸스 홈페이지 주문은 기록되지 않습니다.')
                            else:
                                if cc > 0 or 'CANCEL' in p:
                                    self.UpdateChejanData(p, code, oc, cc, mc, cp, op, on)

            if curr_time > self.dict_time['잔고갱신및주문취소확인'] and not self.dict_bool['프로세스종료']:
                if self.dict_set['코인타임프레임'] and inthmsutc < self.dict_set['코인전략종료시간']:
                    self.OrderTimeControl()
                self.UpdateTotaljango()
                self.dict_time['잔고갱신및주문취소확인'] = timedelta_sec(1)

            if curr_time > self.dict_time['잔고전송'] and not self.dict_bool['프로세스종료']:
                self.cstgQ.put(('잔고목록', self.df_jg))
                self.dict_time['잔고전송'] = timedelta_sec(0.5)

            if self.dict_set['코인전략종료시간'] < inthmsutc < self.dict_set['코인전략종료시간'] + 10 and not self.dict_bool['코인잔고청산']:
                self.JangoCheongsan('자동')

            time.sleep(0.01)

    def WebSocketsStart(self, q):
        self.proc_webs = Process(target=WebSocketTrader, args=(self.dict_set['Access_key2'], self.dict_set['Secret_key2'], q), daemon=True)
        self.proc_webs.start()

    def WebProcessKill(self):
        if self.proc_webs is not None and self.proc_webs.is_alive(): self.proc_webs.kill()

    def UpdateTuple(self, data):
        if len(data) in (6, 7):
            self.CheckOrder(data)
        elif len(data) == 9:
            self.SendOrder(data)
        elif len(data) == 2:
            if type(data[1]) in (int, float):
                self.UpdateJango(data)
            elif data[0] == '저가대비고가등락율':
                self.SetLeverage(data[1])
            elif data[0] == '관심진입':
                if data[1] in self.dict_order['SELL_LONG'].keys():
                    self.CancelOrder(data[1], 'SELL_LONG')
                if data[1] in self.dict_order['BUY_SHORT'].keys():
                    self.CancelOrder(data[1], 'BUY_SHORT')
            elif data[0] == '관심이탈':
                if data[1] in self.dict_order['BUY_LONG'].keys():
                    self.CancelOrder(data[1], 'BUY_LONG')
                if data[1] in self.dict_order['SELL_SHORT'].keys():
                    self.CancelOrder(data[1], 'SELL_SHORT')
            elif data[0] == '설정변경':
                self.dict_set = data[1]
        elif len(data) == 3:
            _, code, c = data
            self.dict_curc[code] = c
            self.OrderTimeControl(code)

    def CheckOrder(self, data):
        if len(data) == 6:
            주문구분, 종목코드, 주문가격, 주문수량, 시그널시간, 수동주문 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 주문가격, 주문수량, 시그널시간, 수동주문, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.df_jg.index
        롱매수주문중 = 종목코드 in self.dict_order['BUY_LONG'].keys()
        숏매수주문중 = 종목코드 in self.dict_order['SELL_SHORT'].keys()
        롱매도주문중 = 종목코드 in self.dict_order['SELL_LONG'].keys()
        숏매도주문중 = 종목코드 in self.dict_order['BUY_SHORT'].keys()
        포지션 = self.df_jg['포지션'][종목코드] if 종목코드 in self.df_jg.index else None

        주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 수동주문:
            if (주문구분 == 'SELL_LONG' and (잔고없음 or 롱매도주문중)) or (주문구분 == 'BUY_SHORT' and (잔고없음 or 숏매도주문중)):
                주문취소 = True
        elif 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
            inthmsutc = int(str_hms(now_utc()))
            if self.dict_set['코인매수금지거래횟수'] and self.dict_set['코인매수금지거래횟수값'] <= len(self.df_td[self.df_td['종목명'] == 종목코드].drop_duplicates('체결시간')):
                주문취소 = True
            elif self.dict_set['코인매수금지손절횟수'] and self.dict_set['코인매수금지손절횟수값'] <= len(self.df_td[(self.df_td['종목명'] == 종목코드) & (self.df_td['수익률'] < 0)].drop_duplicates('체결시간')):
                주문취소 = True
            elif 잔고없음 and inthmsutc < self.dict_set['코인전략종료시간'] and len(self.df_jg) >= self.dict_set['코인최대매수종목수']:
                주문취소 = True
            elif self.dict_set['코인매수금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
            elif self.dict_set['코인매수금지손절간격'] and 현재시간 < self.dict_info[종목코드]['손절거래시간']:
                주문취소 = True
            elif not 잔고없음 and self.df_jg['분할매수횟수'][종목코드] >= self.dict_set['코인매수분할횟수']:
                주문취소 = True
            elif self.dict_intg['추정예수금'] < 주문수량 * 주문가격:
                if 현재시간 > self.dict_info[종목코드]['시드부족시간']:
                    self.CreateOrder('시드부족', 종목코드, 주문가격, 주문수량, str_hmsf(), 시그널시간, 수동주문, 0, None)
                    self.dict_info[종목코드]['시드부족시간'] = timedelta_sec(180)
                주문취소 = True
            elif 포지션 == 'LONG' and 'SHORT' in 주문구분: 주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분: 주문취소 = True
            elif 주문구분 == 'BUY_LONG' and 롱매수주문중:        주문취소 = True
            elif 주문구분 == 'SELL_SHORT' and 숏매수주문중:      주문취소 = True
        elif 주문구분 in ('SELL_LONG', 'BUY_SHORT'):
            if 포지션 == 'LONG' and 'SHORT' in 주문구분:   주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분: 주문취소 = True
            elif 주문구분 == 'SELL_LONG' and 롱매도주문중:       주문취소 = True
            elif 주문구분 == 'BUY_SHORT' and 숏매도주문중:       주문취소 = True
            elif self.dict_set['코인매도금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
        elif 'CANCEL' in 주문구분:
            if 주문구분 == 'BUY_LONG_CANCEL' and not 롱매수주문중:     주문취소 = True
            elif 주문구분 == 'SELL_SHORT_CANCEL' and not 숏매수주문중: 주문취소 = True
            elif 주문구분 == 'SELL_LONG_CANCEL' and not 롱매도주문중:  주문취소 = True
            elif 주문구분 == 'BUY_SHORT_CANCEL' and not 숏매도주문중:  주문취소 = True

        if 주문취소:
            if 'CANCEL' not in 주문구분:
                self.cstgQ.put((f'{주문구분}_CANCEL', 종목코드))
        else:
            if 수동주문 and 'CANCEL' not in 주문구분:
                self.cstgQ.put((f'{주문구분}_MANUAL', 종목코드))

            if 주문수량 > 0:
                self.CreateOrder(주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 0, 수동주문유형)
            else:
                if 주문구분 == 'BUY_LONG':
                    if self.dict_set['코인매도취소매수시그널'] and 롱매도주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'SELL_SHORT':
                    if self.dict_set['코인매도취소매수시그널'] and 숏매도주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'SELL_LONG':
                    if self.dict_set['코인매수취소매도시그널'] and 롱매수주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'BUY_SHORT':
                    if self.dict_set['코인매수취소매도시그널'] and 숏매수주문중: self.CancelOrder(종목코드, 주문구분)
                self.cstgQ.put((f'{주문구분}_CANCEL', 종목코드))

    def CreateOrder(self, 주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 정정횟수, 수동주문유형):
        if 주문구분 in ('BUY_LONG', 'SELL_SHORT') and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['코인매수주문구분']:
                gap = self.dict_info[종목코드]['호가단위'] * self.dict_set['코인매수지정가호가번호']
                if 주문구분 == 'BUY_LONG':
                    주문가격 = round(주문가격 + gap, self.dict_info[종목코드]['소숫점자리수'])
                else:
                    주문가격 = round(주문가격 - gap, self.dict_info[종목코드]['소숫점자리수'])
        elif 주문구분 in ('SELL_LONG', 'BUY_SHORT') and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['코인매도주문구분']:
                gap = self.dict_info[종목코드]['호가단위'] * self.dict_set['코인매도지정가호가번호']
                if 주문구분 == 'SELL_LONG':
                    주문가격 = round(주문가격 + gap, self.dict_info[종목코드]['소숫점자리수'])
                else:
                    주문가격 = round(주문가격 - gap, self.dict_info[종목코드]['소숫점자리수'])

        if 주문수량 * 주문가격 < 5:
            self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 오류 알림 - 최소주문금액 5 USDT 미만입니다.'))
            self.cstgQ.put((f'{주문구분}_CANCEL', 종목코드))
            return

        if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
            주문수량 = round(주문수량 * self.dict_lvrg[종목코드], self.dict_info[종목코드]['소숫점자리수'])

        if 주문수량 > 0:
            if self.dict_set['코인모의투자'] or 주문구분 == '시드부족':
                self.OrderTimeLog(시그널시간)
                if 주문구분 == '시드부족':
                    self.UpdateChejanData(주문구분, 종목코드, 주문수량, 0, 주문수량, 주문가격, 0, '')
                else:
                    self.dict_order[주문구분][종목코드] = [timedelta_sec(self.dict_set['코인매수취소시간초']), 정정횟수, 주문가격, self.dict_lvrg[종목코드]]
                    self.UpdateChejanData(주문구분, 종목코드, 주문수량, 주문수량, 0, 주문가격, 주문가격, '')
            else:
                data = (주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 정정횟수, 수동주문유형)
                self.SendOrder(data)

    def SendOrder(self, data):
        curr_time = now()
        if curr_time < self.dict_time['주문시간']:
            next_time = (self.dict_time['주문시간'] - curr_time).total_seconds()
            threading_timer(next_time, self.ctraderQ.put, data)
            return

        주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 정정횟수, 수동주문유형 = data
        매도수구분, 포지션 = 주문구분.split('_')[:2]
        self.OrderTimeLog(시그널시간)
        if 'CANCEL' not in 주문구분:
            try:
                ret = None
                if 수동주문유형 == '시장가' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '시장가') or 수동주문:
                    ret = self.binance.futures_create_order(symbol=종목코드, side=매도수구분, type='MARKET', quantity=주문수량)
                elif 수동주문유형 == '지정가' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '지정가'):
                    ret = self.binance.futures_create_order(symbol=종목코드, side=매도수구분, type='LIMIT', price=주문가격, timeInForce='GTC', quantity=주문수량)
                elif 수동주문유형 == '지정가IOC' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '지정가IOC'):
                    ret = self.binance.futures_create_order(symbol=종목코드, side=매도수구분, type='LIMIT', price=주문가격, timeInForce='IOC', quantity=주문수량)
                elif 수동주문유형 == '지정가FOK' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '지정가FOK'):
                    ret = self.binance.futures_create_order(symbol=종목코드, side=매도수구분, type='LIMIT', price=주문가격, timeInForce='FOK', quantity=주문수량)
            except Exception as e:
                self.cstgQ.put((f'{주문구분}_CANCEL', 종목코드))
                self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - [주문 실패] {e}'))
            else:
                orderId = int(ret['orderId'])
                dt = self.GetIndex()
                if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                    self.dict_order[주문구분][종목코드] = [timedelta_sec(self.dict_set['코인매수취소시간초']), 정정횟수, 주문가격, self.dict_lvrg[종목코드]]
                    self.dict_intg['추정예수금'] -= 주문수량 * 주문가격
                else:
                    self.dict_order[주문구분][종목코드] = [timedelta_sec(self.dict_set['코인매도취소시간초']), 정정횟수, 주문가격]
                self.dict_pos[종목코드] = 포지션
                self.UpdateChegeollist(dt, 종목코드, f'{주문구분}_REG', 주문수량, 0, 주문수량, 0, dt[:14], 주문가격, orderId)
                self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}_REG] {종목코드} | {주문가격} | {주문수량} | '))
        else:
            try:
                self.binance.futures_cancel_order(symbol=종목코드, orderId=주문번호)
            except Exception as e:
                self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - [주문 실패] {e}'))
            else:
                self.dict_pos[종목코드] = 포지션

        self.dict_time['주문시간'] = timedelta_sec(0.3)
        self.creceivQ.put(('주문목록', self.GetOrderCodeList()))

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            if 현재가 != self.df_jg['현재가'][종목코드]:
                포지션 = self.df_jg['포지션'][종목코드]
                매입금액 = self.df_jg['매입금액'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                if 포지션 == 'LONG':
                    평가금액, 평가손익, 수익률 = GetBinanceLongPgSgSp(매입금액, 보유수량 * 현재가, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                else:
                    평가금액, 평가손익, 수익률 = GetBinanceShortPgSgSp(매입금액, 보유수량 * 현재가, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                columns = ['현재가', '수익률', '평가손익', '평가금액']
                self.df_jg.loc[종목코드, columns] = 현재가, 수익률, 평가손익, 평가금액
        except:
            pass

    def SetLeverage(self, dict_dlhp):
        for code in list(self.dict_info.keys()):
            try:
                leverage = self.GetLeverage(dict_dlhp[code][1])
                self.dict_lvrg[code] = leverage
                if not self.dict_set['코인모의투자']:
                    self.binance.futures_change_leverage(symbol=code, leverage=leverage)
            except:
                pass

    def GetLeverage(self, dlhp):
        leverage = 1
        for min_area, max_area, lvrg in self.dict_set['바이낸스선물변동레버리지값']:
            if min_area <= dlhp < max_area:
                leverage = lvrg
                break
        return leverage

    def OrderTimeControl(self, code_=None):
        cancel_list = []
        modify_list = []

        for gubun in self.dict_order.keys():
            for code in self.dict_order[gubun].keys():
                if code_ is None or code == code_:
                    order_info = self.dict_order[gubun][code]
                    if gubun in ('BUY_LONG', 'SELL_SHORT'):
                        if self.dict_set['코인매수취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    else:
                        if self.dict_set['코인매수취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    if gubun in ('BUY_LONG', 'BUY_SHORT'):
                        if order_info[1] < self.dict_set['코인매수정정횟수'] and code in self.dict_curc.keys() and \
                                self.dict_curc[code] >= order_info[2] + self.dict_info[code]['호가단위'] * self.dict_set['코인매수정정호가차이']:
                            modify_list.append((code, gubun))
                    else:
                        if order_info[1] < self.dict_set['코인매도정정횟수'] and code in self.dict_curc.keys() and \
                                self.dict_curc[code] <= order_info[2] - self.dict_info[code]['호가단위'] * self.dict_set['코인매도정정호가차이']:
                            modify_list.append((code, gubun))

        if cancel_list:
            for code, gubun in cancel_list:
                self.CancelOrder(code, gubun)
        if modify_list:
            for code, gubun in modify_list:
                self.ModifyOrder(code, gubun)

    def CancelOrder(self, 종목코드, 주문구분):
        df = self.GetMichegeolDF(종목코드, 주문구분)
        if len(df) > 0:
            미체결수량 = df['미체결수량'].iloc[-1]
            if 미체결수량 > 0:
                주문번호, 주문가격 = df['주문번호'].iloc[-1], df['주문가격'].iloc[-1]
                self.CreateOrder(f'{주문구분}_CANCEL', 종목코드, 주문가격, 미체결수량, 주문번호, now(), False, 0, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        df = self.GetMichegeolDF(종목코드, 주문구분)
        if len(df) > 0:
            미체결수량 = df['미체결수량'].iloc[-1]
            if 미체결수량 > 0:
                if 주문구분 == 'BUY_LONG':
                    정정가격 = self.dict_curc[종목코드] - self.dict_info[종목코드]['호가단위'] * self.dict_set['코인매수정정호가']
                elif 주문구분 == 'SELL_SHORT':
                    정정가격 = self.dict_curc[종목코드] + self.dict_info[종목코드]['호가단위'] * self.dict_set['코인매수정정호가']
                elif 주문구분 == 'SELL_LONG':
                    정정가격 = self.dict_curc[종목코드] + self.dict_info[종목코드]['호가단위'] * self.dict_set['코인매도정정호가']
                else:
                    정정가격 = self.dict_curc[종목코드] - self.dict_info[종목코드]['호가단위'] * self.dict_set['코인매도정정호가']

                정정횟수 = self.dict_order[주문구분][종목코드][1] + 1
                주문번호, 주문가격 = df['주문번호'].iloc[-1], df['주문가격'].iloc[-1]
                현재시간 = now()
                self.CreateOrder(f'{주문구분}_CANCEL', 종목코드, 주문가격, 미체결수량, 주문번호, 현재시간, False, 0, None)
                self.CreateOrder(주문구분, 종목코드, 정정가격, 미체결수량, '', 현재시간, False, 정정횟수, None)

    def UpdateString(self, data):
        if data == '체결목록':
            self.teleQ.put(self.df_cj) if len(self.df_cj) > 0 else self.teleQ.put('현재는 체결목록이 없습니다.')
        elif data == '거래목록':
            self.teleQ.put(self.df_td) if len(self.df_td) > 0 else self.teleQ.put('현재는 거래목록이 없습니다.')
        elif data == '잔고평가':
            self.teleQ.put(('잔고목록', self.df_jg)) if len(self.df_jg) > 0 else self.teleQ.put('현재는 잔고목록이 없습니다.')
        elif data == '잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로세스종료':
            if not self.dict_bool['프로세스종료']:
                self.dict_bool['프로세스종료'] = True
                QTimer.singleShot(180 * 1000, self.SysExit)

    def JangoCheongsan(self, gubun):
        self.dict_bool['코인잔고청산'] = True

        for 주문구분 in self.dict_order.keys():
            for 종목코드 in self.dict_order[주문구분].keys():
                self.CancelOrder(종목코드, 주문구분)

        if len(self.df_jg) > 0 and (gubun == '수동' or self.dict_set['코인잔고청산']):
            if gubun == '수동':
                self.teleQ.put('tele', '코인 잔고청산 주문을 전송합니다.')
            for 종목코드 in self.df_jg.index:
                포지션 = self.df_jg['포지션'][종목코드]
                현재가 = self.df_jg['현재가'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                if self.dict_set['코인모의투자']:
                    self.UpdateChejanData('SELL_LONG' if 포지션 == 'LONG' else 'BUY_SHORT', 종목코드, 보유수량, 보유수량, 0, 현재가, 현재가, '')
                else:
                    try:
                        if 포지션 == 'LONG':
                            ret = self.binance.futures_create_order(symbol=종목코드, side='SELL', type='MARKET', quantity=보유수량)
                        else:
                            ret = self.binance.futures_create_order(symbol=종목코드, side='BUY', type='MARKET', quantity=보유수량)
                    except Exception as e:
                        self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - [주문 실패] {e}'))
                    else:
                        orderId = int(ret['orderId'])
                        dt = self.GetIndex()
                        self.dict_pos[종목코드] = 포지션
                        if 포지션 == 'LONG':
                            self.UpdateChegeollist(dt, 종목코드, 'SELL_LONG_REG', 보유수량, 0, 보유수량, 0, dt[:14], 현재가, orderId)
                            self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [SELL_LONG_REG] {종목코드} | {현재가} | {보유수량}'))
                        else:
                            self.UpdateChegeollist(dt, 종목코드, 'BUY_SHORT_REG', 보유수량, 0, 보유수량, 0, dt[:14], 현재가, orderId)
                            self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [BUY_SHORT_REG] {종목코드} | {현재가} | {보유수량}'))
                    time.sleep(0.3)
            if self.dict_set['코인알림소리']:
                self.soundQ.put(f'코인 {gubun} 전략 잔고청산 주문을 전송하였습니다.')
            self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 실행 알림 - {gubun} 전략 잔고청산 주문 완료'))
        elif self.df_jg.empty and gubun == '수동':
            self.teleQ.put('tele', '현재는 코인 보유종목이 없습니다.')

    def SysExit(self):
        self.WebProcessKill()
        self.SaveDayData()
        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 트레이더 종료'))
        time.sleep(1)
        sys.exit()

    def SaveDayData(self):
        if len(self.df_td) > 0:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql(f"SELECT * FROM c_totaltradelist WHERE `index` = '{self.str_today}'", con)
            con.close()
            if len(df) == 0:
                df = self.df_tt[['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']]
                self.queryQ.put(('거래디비', df, 'c_totaltradelist', 'append'))
                if self.dict_set['코인알림소리']:
                    self.soundQ.put('일별실현손익를 저장하였습니다.')
                self.soundQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 일별실현손익 저장 완료'))

    @error_decorator
    def UpdateChejanData(self, 주문구분, 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 주문번호):
        dt = self.GetIndex()

        if 주문구분 in ('BUY_LONG', 'SELL_SHORT', 'SELL_LONG', 'BUY_SHORT'):
            if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                if 종목코드 in self.df_jg.index:
                    보유수량 = round(self.df_jg['보유수량'][종목코드] + 체결수량, self.dict_info[종목코드]['소숫점자리수'])
                    매입금액 = round(self.df_jg['매입금액'][종목코드] + 체결수량 * 체결가격, 4)
                    매입가 = round(매입금액 / 보유수량, 8)
                    평가금액 = round(체결가격 * 보유수량, 4)
                    if 주문구분 == 'BUY_LONG':
                        평가금액, 수익금, 수익률 = GetBinanceLongPgSgSp(매입금액, 평가금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                    else:
                        평가금액, 수익금, 수익률 = GetBinanceShortPgSgSp(매입금액, 평가금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                    columns = ['매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '매수시간']
                    self.df_jg.loc[종목코드, columns] = 매입가, 체결가격, 수익률, 수익금, 매입금액, 평가금액, 보유수량, dt[:14]
                else:
                    매입금액 = round(체결가격 * 체결수량, 4)
                    레버리지 = self.dict_set['바이낸스선물고정레버리지값'] if self.dict_set['바이낸스선물고정레버리지'] else self.dict_order[주문구분][종목코드][3]
                    if 주문구분 == 'BUY_LONG':
                        포지션 = 'LONG'
                        평가금액, 수익금, 수익률 = GetBinanceLongPgSgSp(매입금액, 매입금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                    else:
                        포지션 = 'SHORT'
                        평가금액, 수익금, 수익률 = GetBinanceShortPgSgSp(매입금액, 매입금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                    self.df_jg.loc[종목코드] = 종목코드, 포지션, 체결가격, 체결가격, 수익률, 수익금, 매입금액, 평가금액, 체결수량, 레버리지, 0, 0, dt[:14]

                if 미체결수량 == 0:
                    self.df_jg.loc[종목코드, '분할매수횟수'] = self.df_jg['분할매수횟수'][종목코드] + 1
                    if 종목코드 in self.dict_order[주문구분].keys():
                        del self.dict_order[주문구분][종목코드]

            else:
                포지션 = self.df_jg['포지션'][종목코드]
                매입가 = self.df_jg['매입가'][종목코드]
                보유수량 = round(self.df_jg['보유수량'][종목코드] - 체결수량, self.dict_info[종목코드]['소숫점자리수'])
                if 보유수량 != 0:
                    매입금액 = round(매입가 * 보유수량, 4)
                    평가금액 = round(체결가격 * 보유수량, 4)
                    if 주문구분 == 'SELL_LONG':
                        평가금액, 수익금, 수익률 = GetBinanceLongPgSgSp(매입금액, 평가금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                    else:
                        평가금액, 수익금, 수익률 = GetBinanceShortPgSgSp(매입금액, 평가금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                    columns = ['현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량']
                    self.df_jg.loc[종목코드, columns] = 체결가격, 수익률, 수익금, 매입금액, 평가금액, 보유수량
                else:
                    self.df_jg.drop(index=종목코드, inplace=True)

                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.df_jg.loc[종목코드, '분할매도횟수'] = self.df_jg['분할매도횟수'][종목코드] + 1
                    if 종목코드 in self.dict_order[주문구분].keys():
                        del self.dict_order[주문구분][종목코드]

                매입금액 = round(매입가 * 체결수량, 4)
                평가금액 = round(체결가격 * 체결수량, 4)
                if 주문구분 == 'SELL_LONG':
                    평가금액, 수익금, 수익률 = GetBinanceLongPgSgSp(매입금액, 평가금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                else:
                    평가금액, 수익금, 수익률 = GetBinanceShortPgSgSp(매입금액, 평가금액, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                if -100 < 수익률 < 100: self.UpdateTradelist(dt, 종목코드, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, dt[:14])
                if 수익률 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['코인매수금지손절간격초'])

            self.df_jg.sort_values(by=['매입금액'], ascending=False, inplace=True)
            self.cstgQ.put(('잔고목록', self.df_jg))

            if 미체결수량 == 0: self.cstgQ.put((f'{주문구분}_COMPLETE', 종목코드))
            self.UpdateChegeollist(dt, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, dt[:14], 주문가격, 주문번호)

            if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
                self.dict_intg['예수금'] -= 체결수량 * 체결가격
                if self.dict_set['코인모의투자']:
                    self.dict_intg['추정예수금'] -= 체결수량 * 체결가격
            else:
                self.dict_intg['예수금'] += 매입금액 + 수익금
                self.dict_intg['추정예수금'] += 매입금액 + 수익금

            self.queryQ.put(('거래디비', self.df_jg, 'c_jangolist_future', 'replace'))
            if self.dict_set['코인알림소리']:
                text = ''
                if 주문구분 == 'BUY_LONG':     text = '롱포지션을 진입'
                elif 주문구분 == 'SELL_SHORT': text = '숏포지션을 진입'
                elif 주문구분 == 'SELL_LONG':  text = '롱포지션을 청산'
                elif 주문구분 == 'BUY_SHORT':  text = '숏포지션을 청산'
                self.soundQ.put(f"{종목코드} {text}하였습니다.")
            self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}] {종목코드} | {체결가격} | {체결수량}'))

        elif 주문구분 == '시드부족':
            self.UpdateChegeollist(dt, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, dt[:14], 주문가격, 주문번호)

        elif 주문구분 in ('BUY_LONG_CANCEL', 'SELL_SHORT_CANCEL', 'SELL_LONG_CANCEL', 'BUY_SHORT_CANCEL'):
            if 주문구분 in ('BUY_LONG_CANCEL', 'SELL_SHORT_CANCEL'):
                self.dict_intg['추정예수금'] += 주문수량 * 주문가격
            gubun_ = 주문구분.replace('_CANCEL', '')
            if 종목코드 in self.dict_order[gubun_].keys():
                del self.dict_order[gubun_][종목코드]

            self.cstgQ.put((주문구분, 종목코드))
            self.UpdateChegeollist(dt, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, dt[:14], 주문가격, 주문번호)

            if self.dict_set['코인알림소리']:
                text = ''
                if 주문구분 == 'BUY_LONG_CANCEL':     text = '롱포지션 진입을 취소'
                elif 주문구분 == 'SELL_SHORT_CANCEL': text = '숏포지션 진입을 취소'
                elif 주문구분 == 'SELL_LONG_CANCEL':  text = '롱포지션 청산을 취소'
                elif 주문구분 == 'BUY_SHORT_CANCEL':  text = '숏포지션 청산을 취소'
                self.soundQ.put(f"{종목코드} {text}하였습니다.")
            self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}] {종목코드} | {주문가격} | {주문수량}'))

        self.creceivQ.put(('잔고목록', tuple(self.df_jg.index)))
        self.creceivQ.put(('주문목록', self.GetOrderCodeList()))

    def UpdateTradelist(self, index, 종목코드, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간):
        self.df_td.loc[index] = 종목코드, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간
        self.windowQ.put((ui_num['C거래목록'], self.df_td[::-1]))
        df = pd.DataFrame([[종목코드, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간]], columns=columns_tdf, index=[index])
        self.queryQ.put(('거래디비', df, 'c_tradelist_future', 'append'))
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        거래횟수 = len(self.df_td.drop_duplicates(['종목명', '체결시간']))
        총매수금액 = self.df_td['매수금액'].sum()
        총매도금액 = self.df_td['매도금액'].sum()
        총수익금액 = self.df_td[self.df_td['수익금'] > 0]['수익금'].sum()
        총손실금액 = self.df_td[self.df_td['수익금'] < 0]['수익금'].sum()
        수익금합계 = self.df_td['수익금'].sum()
        수익률 = round(수익금합계 / self.dict_intg['추정예탁자산'] * 100, 2)

        self.df_tt.loc[self.str_today] = 거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익률, 수익금합계
        self.windowQ.put((ui_num['C실현손익'], self.df_tt))

        if not first:
            self.teleQ.put(f'손익 알림 - 총매수금액 {총매수금액:,.0f}, 총매도금액 {총매도금액:,.0f}, 수익 {총수익금액:,.0f}, 손실 {총손실금액:,.0f}, 수익금합계 {수익금합계:,.0f}')

        if self.dict_set['스톰라이브']:
            수익률 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익률, 수익금합계]
            self.liveQ.put(('코인', data_list))

    def UpdateChegeollist(self, index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호):
        self.dict_info[종목코드]['최종거래시간'] = timedelta_sec(self.dict_set['코인매수금지간격초'])
        self.df_cj.loc[index] = 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호
        self.windowQ.put((ui_num['C체결목록'], self.df_cj[::-1]))
        df = pd.DataFrame([[종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]], columns=columns_cj, index=[index])
        self.queryQ.put(('거래디비', df, 'c_chegeollist', 'append'))

    def UpdateTotaljango(self):
        if len(self.df_jg) > 0:
            총평가손익 = self.df_jg['평가손익'].sum()
            총매입금액 = self.df_jg['매입금액'].sum()
            총평가금액 = self.df_jg['평가금액'].sum()
            잔고수량 = len(self.df_jg)
            총수익률 = round(총평가손익 / 총매입금액 * 100, 2)
            self.dict_intg['추정예탁자산'] = self.dict_intg['예수금'] + 총평가금액
            self.df_tj = pd.DataFrame([[self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 잔고수량, 총수익률, 총평가손익, 총매입금액, 총평가금액]], columns=columns_tj, index=[self.str_today])
        else:
            self.df_tj = pd.DataFrame([[self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 0, 0.0, 0, 0, 0]], columns=columns_tj, index=[self.str_today])

        총평가손익 = self.df_jg['평가손익'].sum() + self.df_td['수익금'].sum()
        if self.dict_set['코인손실중지']:
            기준손실금 = self.dict_intg['추정예탁자산'] * self.dict_set['코인손실중지수익률'] / 100
            if 기준손실금 < -총평가손익: self.StrategyStop()
        if self.dict_set['코인수익중지']:
            기준수익금 = self.dict_intg['추정예탁자산'] * self.dict_set['코인수익중지수익률'] / 100
            if 기준수익금 < 총평가손익: self.StrategyStop()

        if self.dict_set['코인투자금고정']:
            종목당투자금 = int(self.dict_set['코인투자금'])
        else:
            종목당투자금 = int(self.dict_intg['추정예탁자산'] * 0.98 / self.dict_set['코인최대매수종목수'])

        if self.dict_intg['종목당투자금'] != 종목당투자금:
            self.dict_intg['종목당투자금'] = 종목당투자금
            self.cstgQ.put(('종목당투자금', self.dict_intg['종목당투자금']))

        self.windowQ.put((ui_num['C잔고목록'], self.df_jg))
        self.windowQ.put((ui_num['C잔고평가'], self.df_tj))

    def StrategyStop(self):
        self.cstgQ.put('매수전략중지')
        self.JangoCheongsan('수동')

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.windowQ.put((ui_num['C단순텍스트'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.'))

    def GetOrderCodeList(self):
        return tuple(self.dict_order['BUY_LONG'].keys()) + tuple(self.dict_order['SELL_SHORT'].keys()) + \
            tuple(self.dict_order['SELL_LONG'].keys()) + tuple(self.dict_order['BUY_SHORT'].keys())

    def GetMichegeolDF(self, code, gubun):
        return self.df_cj[(self.df_cj['종목명'] == code) & ((self.df_cj['주문구분'] == gubun) | (self.df_cj['주문구분'] == f'{gubun}_REG'))]

    def GetIndex(self):
        dt = str_ymdhmsf(now_utc())
        if dt in self.df_cj.index:
            while dt in self.df_cj.index:
                dt = str(int(dt) + 1)
        return dt
