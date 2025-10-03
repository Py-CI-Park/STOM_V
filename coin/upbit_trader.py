import sys
import time
import pyupbit
import sqlite3
import pandas as pd
from PyQt5.QtCore import QTimer
from utility.setting import columns_cj, columns_tj, columns_jg, columns_td, columns_tt, ui_num, DB_TRADELIST, DICT_SET
from utility.static import now, timedelta_sec, GetUpbitHogaunit, GetUpbitPgSgSp, now_utc, str_ymdhmsf, str_hmsf, \
    threading_timer, error_decorator, str_hms, str_ymd


class UpbitTrader:
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

        self.upbit            = None
        self.dict_info        = {}
        self.dict_curc        = {}
        self.dict_order_cc    = {}
        self.dict_order       = {'매수': {}, '매도': {}, '매수취소': {}, '매도취소': {}}

        self.df_cj = pd.DataFrame(columns=columns_cj)
        self.df_jg = pd.DataFrame(columns=columns_jg)
        self.df_tj = pd.DataFrame(columns=columns_tj)
        self.df_td = pd.DataFrame(columns=columns_td)
        self.df_tt = pd.DataFrame(columns=columns_tt)

        self.str_today = str_ymd(now_utc())

        self.dict_intg = {
            '예수금': 0,
            '추정예수금': 0,
            '추정예탁자산': 0,
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
            '주문확인': curr_time,
            '잔고전송': curr_time,
            '잔고갱신및주문취소확인': curr_time
        }

        self.UpdateDictName()
        self.LoadDatabase()
        self.GetKey()
        self.GetBalances()
        self.MainLoop()

    def UpdateDictName(self):
        dummy_time = timedelta_sec(-3600)
        for dict_ticker in pyupbit.get_tickers(fiat="KRW", verbose=True):
            code = dict_ticker['market']
            self.dict_info[code] = {
                '시드부족시간': dummy_time,
                '최종거래시간': dummy_time,
                '손절거래시간': dummy_time
            }

        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 코인명 수집 완료'))

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        self.df_cj = pd.read_sql(f"SELECT * FROM c_chegeollist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        self.df_td = pd.read_sql(f"SELECT * FROM c_tradelist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        self.df_jg = pd.read_sql(f'SELECT * FROM c_jangolist', con).set_index('index')
        con.close()

        if len(self.df_cj) > 0: self.windowQ.put((ui_num['C체결목록'], self.df_cj[::-1]))
        if len(self.df_td) > 0: self.windowQ.put((ui_num['C거래목록'], self.df_td[::-1]))
        if len(self.df_jg) > 0: self.creceivQ.put(('잔고목록', tuple(self.df_jg.index)))

        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 불러오기 완료'))

    def GetKey(self):
        self.upbit = pyupbit.Upbit(self.dict_set['Access_key1'], self.dict_set['Secret_key1'])
        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 주문 및 체결확인용 업비트 객체 생성 완료'))

    def GetBalances(self):
        cbg = self.df_jg['매입금액'].sum()
        if self.dict_set['코인모의투자']:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql('SELECT * FROM c_tradelist', con)
            con.close()
            tcg = df['수익금'].sum()
            chujeonjasan = 100000000 + tcg
        else:
            ret = self.upbit.get_balances()
            if self.CheckError(ret):
                chujeonjasan = int(float(ret[0]['balance']))
            else:
                chujeonjasan = 0

        self.dict_intg['예수금'] = int(chujeonjasan - cbg)
        self.dict_intg['추정예수금'] = self.dict_intg['예수금']
        self.dict_intg['추정예탁자산'] = chujeonjasan

        if len(self.df_td) > 0:
            self.UpdateTotaltradelist(first=True)

        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 예수금 조회 완료'))

    def MainLoop(self):
        text = '코인 전략연산 및 트레이더를 시작하였습니다.'
        if self.dict_set['코인알림소리']: self.soundQ.put(text)
        self.teleQ.put(text)
        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 트레이더 시작'))
        while True:
            curr_time = now()
            inthmsutc = int(str_hms(now_utc()))
            if not self.ctraderQ.empty():
                data = self.ctraderQ.get()
                if type(data) == tuple:
                    self.UpdateTuple(data)
                elif type(data) == str:
                    self.UpdateString(data)

            if curr_time > self.dict_time['주문확인'] and not self.dict_bool['프로세스종료']:
                self.CheckChegeol()
                self.dict_time['주문확인'] = timedelta_sec(0.3)

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

    def UpdateTuple(self, data):
        if len(data) in (6, 7):
            self.CheckOrder(data)
        elif len(data) == 9:
            self.SendOrder(data)
        elif len(data) == 2:
            if type(data[1]) in (int, float):
                self.UpdateJango(data)
            if data[0] == '관심진입':
                if data[1] in self.dict_order['매도'].keys():
                    self.CancelOrder(data[1], '매도')
            elif data[0] == '관심이탈':
                if data[1] in self.dict_order['매수'].keys():
                    self.CancelOrder(data[1], '매수')
            elif data[0] == '설정변경':
                self.dict_set = data[1]
        elif len(data) == 3:
            _, code, c = data
            self.dict_curc[code] = c
            self.OrderTimeControl(code)

    def UpdateString(self, data):
        if data == 'C체결목록':
            self.teleQ.put(self.df_cj) if len(self.df_cj) > 0 else self.teleQ.put('현재는 코인체결목록이 없습니다.')
        elif data == 'C거래목록':
            self.teleQ.put(self.df_td) if len(self.df_td) > 0 else self.teleQ.put('현재는 코인거래목록이 없습니다.')
        elif data == 'C잔고평가':
            self.teleQ.put(('잔고목록', self.df_jg)) if len(self.df_jg) > 0 else self.teleQ.put('현재는 코인잔고목록이 없습니다.')
        elif data == 'C잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로세스종료':
            if not self.dict_bool['프로세스종료']:
                self.dict_bool['프로세스종료'] = True
                QTimer.singleShot(180 * 1000, self.SysExit)

    def CheckOrder(self, data):
        if len(data) == 6:
            주문구분, 종목코드, 주문가격, 주문수량, 시그널시간, 수동주문 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 주문가격, 주문수량, 시그널시간, 수동주문, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.df_jg.index
        매수주문중 = 종목코드 in self.dict_order['매수'].keys()
        매도주문중 = 종목코드 in self.dict_order['매도'].keys()

        주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 수동주문:
            if 잔고없음:   주문취소 = True
            elif 매도주문중: 주문취소 = True
        elif 주문구분 == '매수':
            inthmsutc = int(str_hms(now_utc()))
            if self.dict_set['코인매수금지거래횟수'] and self.dict_set['코인매수금지거래횟수값'] <= len(self.df_td[self.df_td['종목명'] == 종목코드].drop_duplicates('체결시간')):
                주문취소 = True
            elif self.dict_set['코인매수금지손절횟수'] and self.dict_set['코인매수금지손절횟수값'] <= len(self.df_td[(self.df_td['종목명'] == 종목코드) & (self.df_td['수익율'] < 0)].drop_duplicates('체결시간')):
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
                    self.CreateOrder('시드부족', 종목코드, 주문가격, 주문수량, str_hmsf(now_utc()), 시그널시간, 수동주문, 0, None)
                    self.dict_info[종목코드]['시드부족시간'] = timedelta_sec(180)
                주문취소 = True
            elif 매수주문중:
                주문취소 = True
        elif 주문구분 == '매도':
            if 잔고없음 or 매도주문중:
                주문취소 = True
            elif self.dict_set['코인매도금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
        elif '취소' in 주문구분:
            if 주문구분 == '매수취소' and not 매수주문중:   주문취소 = True
            elif 주문구분 == '매도취소' and not 매도주문중: 주문취소 = True

        if 주문취소:
            if '취소' not in 주문구분:
                self.cstgQ.put((f'{주문구분}취소', 종목코드))
        else:
            if 수동주문 and 주문구분 in ('매수', '매도'):
                self.cstgQ.put((f'{주문구분}주문', 종목코드))

            if 주문구분 == '매수':
                if self.dict_set['코인매도취소매수시그널'] and 매도주문중:
                    self.CancelOrder(종목코드, 주문구분)
            elif 주문구분 == '매도':
                if self.dict_set['코인매수취소매도시그널'] and 매수주문중:
                    self.CancelOrder(종목코드, 주문구분)

            if 주문수량 > 0:
                self.CreateOrder(주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 0, 수동주문유형)
            else:
                self.cstgQ.put((f'{주문구분}취소', 종목코드))

    def CreateOrder(self, 주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 정정횟수, 수동주문유형):
        if 주문구분 == '매수' and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['코인매수주문구분']:
                주문가격 = round(주문가격 + GetUpbitHogaunit(주문가격) * self.dict_set['코인매수지정가호가번호'], 8)
        elif 주문구분 == '매도' and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['코인매도주문구분']:
                주문가격 = round(주문가격 + GetUpbitHogaunit(주문가격) * self.dict_set['코인매도지정가호가번호'], 8)

        if 주문수량 * 주문가격 < 5000:
            self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - 주문금액이 5천원미만입니다.'))
            self.cstgQ.put((f'{주문구분}취소', 종목코드))
            return

        if 주문수량 > 0:
            if self.dict_set['코인모의투자'] or 주문구분 == '시드부족':
                self.OrderTimeLog(시그널시간)
                if 주문구분 == '시드부족':
                    self.UpdateChejanData(주문구분, 종목코드, 주문수량, 0, 주문수량, 주문가격, 0, '')
                else:
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
        self.OrderTimeLog(시그널시간)
        if self.upbit is not None:
            if 주문구분 == '매수':
                ret = None
                if 수동주문유형 == '시장가' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '시장가') or 수동주문:
                    ret = self.upbit.buy_market_order(종목코드, int(주문가격 * 주문수량))
                elif 수동주문유형 == '지정가' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '지정가'):
                    ret = self.upbit.buy_limit_order(종목코드, 주문가격, 주문수량)

                if ret is not None:
                    if self.CheckError(ret):
                        dt = self.GetIndex()
                        self.dict_intg['추정예수금'] -= 주문수량 * 주문가격
                        self.dict_order[주문구분][종목코드] = [ret['uuid'], timedelta_sec(self.dict_set['코인매수취소시간초']), 정정횟수, 주문가격, GetUpbitHogaunit(주문가격)]
                        self.UpdateChegeollist(dt, 종목코드, f'{주문구분} 접수', 주문수량, 0, 주문수량, 0, dt[:14], 주문가격, ret['uuid'])
                        self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}접수] {종목코드} | {주문가격} | {주문수량}'))
                else:
                    self.cstgQ.put(('매수취소', 종목코드))
                    self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - [주문실패] {종목코드} | {주문가격} | {주문수량}'))

            elif 주문구분 == '매도':
                ret = None
                if 수동주문유형 == '시장가' or self.dict_set['코인매도주문구분'] == '시장가' or 수동주문:
                    ret = self.upbit.sell_market_order(종목코드, 주문수량)
                elif 수동주문유형 == '지정가' or self.dict_set['코인매도주문구분'] == '지정가':
                    ret = self.upbit.sell_limit_order(종목코드, 주문가격, 주문수량)

                if ret is not None:
                    if self.CheckError(ret):
                        dt = self.GetIndex()
                        self.dict_order[주문구분][종목코드] = [ret['uuid'], timedelta_sec(self.dict_set['코인매도취소시간초']), 정정횟수, 주문가격, GetUpbitHogaunit(주문가격)]
                        self.UpdateChegeollist(dt, 종목코드, f'{주문구분} 접수', 주문수량, 0, 주문수량, 0, dt[:14], 주문가격, ret['uuid'])
                        self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}접수] {종목코드} | {주문가격} | {주문수량}'))
                else:
                    self.cstgQ.put(('매도취소', 종목코드))
                    self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - [주문실패] {종목코드} | {주문가격} | {주문수량} | {주문구분}'))

            elif 주문구분 in ('매수취소', '매도취소'):
                ret = self.upbit.cancel_order(주문번호)
                if ret is not None:
                    if self.CheckError(ret):
                        if 주문구분 == '매수취소':
                            self.dict_order[주문구분][종목코드] = ret['uuid']
                        elif 주문구분 == '매도취소':
                            self.dict_order[주문구분][종목코드] = ret['uuid']
                else:
                    self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - [주문 실패] {종목코드} | {주문가격} | {주문수량} | {주문구분}'))

        self.dict_time['주문시간'] = timedelta_sec(0.3)
        self.creceivQ.put(('주문목록', self.GetOrderCodeList()))

    def CheckChegeol(self):
        order_info_list = []
        for gubun in self.dict_order.keys():
            for code, orders in self.dict_order[gubun].items():
                order_info = self.GetOrderInfo(code, orders[0])
                if order_info is not None:
                    order_info_list.append([gubun] + order_info)
    
        if order_info_list:
            for 종목코드, 주문수량, 총체결수량, 미체결수량, 체결가격, 주문가격, 주문번호 in order_info_list:
                self.UpdateChejanData(종목코드, 주문수량, 총체결수량, 미체결수량, 체결가격, 주문가격, 주문번호)

    def GetOrderInfo(self, 종목코드, 주문번호):
        order_info = None
        ret = self.upbit.get_order(주문번호)
        if ret is not None and self.CheckError(ret):
            try:
                주문가격 = float(ret['price'])
            except:
                주문가격 = 0.
            try:
                주문수량 = float(ret['volume'])
            except:
                주문수량 = 0.
            try:
                미체결수량 = float(ret['remaining_volume'])
            except:
                미체결수량 = 0.

            총체결수량, 체결가격, 매입금액 = 0., 0., 0.
            if ret['trades_count'] > 0:
                trades = ret['trades']
                for i in range(len(trades)):
                    매입금액 += float(trades[i]['funds'])
                    총체결수량 += float(trades[i]['volume'])
                if 총체결수량 > 0:
                    체결가격 = round(매입금액 / 총체결수량, 4)
                    총체결수량 = round(총체결수량, 8)

            if 총체결수량 > 0:
                if 주문번호 not in self.dict_order_cc.keys():
                    order_info = [종목코드, 주문수량, 총체결수량, 미체결수량, 체결가격, 주문가격, 주문번호]
                    self.dict_order_cc[주문번호] = 총체결수량
                else:
                    체결수량 = round(총체결수량 - self.dict_order_cc[주문번호], 8)
                    if 체결수량 > 0:
                        order_info = [종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 주문번호]
                        self.dict_order_cc[주문번호] = 총체결수량

                if 미체결수량 == 0 and 주문번호 in self.dict_order_cc.keys():
                    del self.dict_order_cc[주문번호]

        time.sleep(0.1)
        return order_info

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            if 현재가 != self.df_jg['현재가'][종목코드]:
                매입금액 = self.df_jg['매입금액'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                평가금액, 평가손익, 수익율 = GetUpbitPgSgSp(매입금액, 보유수량 * 현재가)
                columns = ['현재가', '수익율', '평가손익', '평가금액']
                self.df_jg.loc[종목코드, columns] = 현재가, 수익율, 평가손익, 평가금액
        except:
            pass

    def OrderTimeControl(self, code_=None):
        cancel_list = []
        modify_list = []

        for gubun in self.dict_order.keys():
            if gubun in ('매수', '매도'):
                for code in self.dict_order[gubun].keys():
                    if code_ is None or code == code_:
                        order_info = self.dict_order[gubun][code]
                        if gubun == '매수':
                            if self.dict_set['코인매수취소시간'] and now() > order_info[1]:
                                cancel_list.append((code, gubun))
                        else:
                            if self.dict_set['코인매도취소시간'] and now() > order_info[1]:
                                cancel_list.append((code, gubun))
                        if gubun == '매수':
                            if order_info[2] < self.dict_set['코인매수정정횟수'] and code in self.dict_curc.keys() and \
                                    self.dict_curc[code] >= order_info[3] + order_info[4] * self.dict_set['코인매수정정호가차이']:
                                modify_list.append((code, gubun))
                        else:
                            if order_info[2] < self.dict_set['코인매도정정횟수'] and code in self.dict_curc.keys() and \
                                    self.dict_curc[code] <= order_info[3] - order_info[4] * self.dict_set['코인매도정정호가차이']:
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
                self.CreateOrder(f'{주문구분}취소', 종목코드, 주문가격, 미체결수량, 주문번호, now(), False, 0, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        df = self.GetMichegeolDF(종목코드, 주문구분)
        if len(df) > 0:
            미체결수량 = df['미체결수량'].iloc[-1]
            if 미체결수량 > 0:
                주문번호, 주문가격 = df['주문번호'].iloc[-1], df['주문가격'].iloc[-1]
                if 주문구분 == '매수':
                    정정가격 = self.dict_curc[종목코드] - self.dict_order[주문구분][종목코드][4] * self.dict_set['코인매수정정호가']
                else:
                    정정가격 = self.dict_curc[종목코드] + self.dict_order[주문구분][종목코드][4] * self.dict_set['코인매도정정호가']

                현재시간 = now()
                정정횟수 = self.dict_order[주문구분][종목코드][2] + 1
                self.CreateOrder(f'{주문구분}취소', 종목코드, 주문가격, 미체결수량, 주문번호, 현재시간, False, 0, None)
                self.CreateOrder(주문구분, 종목코드, 정정가격, 미체결수량, '', 현재시간, False, 정정횟수, None)

    def JangoCheongsan(self, gubun):
        self.dict_bool['코인잔고청산'] = True

        if len(self.dict_order) > 0:
            for code in list(self.dict_order.keys()):
                self.CancelOrder(code, '매수')

        if len(self.dict_order) > 0:
            for code in list(self.dict_order.keys()):
                self.CancelOrder(code, '매도')

        if (gubun == '수동' or self.dict_set['코인잔고청산']) and len(self.df_jg) > 0:
            for code in self.df_jg.index:
                c, oc = self.df_jg['현재가'][code], self.df_jg['보유수량'][code]
                if self.dict_set['코인모의투자']:
                    self.UpdateChejanData('매도', code, oc, oc, 0, c, c, '')
                else:
                    ret = self.upbit.sell_market_order(code, oc)
                    if ret is not None:
                        if self.CheckError(ret):
                            self.dict_order[gubun][code] = [ret['uuid'], now()]
                    else:
                        self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - [주문 실패] {code} | {c} | {oc} | 매도'))
                    time.sleep(0.3)

            if self.dict_set['코인알림소리']:
                self.soundQ.put(f'코인 {gubun} 전략 잔고청산 주문을 전송하였습니다.')
            self.windowQ.put((ui_num['C로그텍스트'], f'시스템 명령 실행 알림 - {gubun} 전략 잔고청산 주문 완료'))

    def SysExit(self):
        self.SaveDayData()
        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 트레이더 종료'))
        time.sleep(1)
        sys.exit()

    def SaveDayData(self):
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM c_totaltradelist WHERE `index` = '{self.str_today}'", con)
        con.close()
        if len(df) == 0:
            df = self.df_tt[['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익율', '수익금합계']]
            self.queryQ.put(('거래디비', df, 'c_totaltradelist', 'append'))
            if self.dict_set['코인알림소리']:
                self.soundQ.put('일별실현손익를 저장하였습니다.')
            self.soundQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 일별실현손익 저장 완료'))

    @error_decorator
    def UpdateChejanData(self, 주문구분, 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 주문번호):
        index = self.GetIndex()

        if 주문구분 in ('매수', '매도'):
            if 주문구분 == '매수':
                if 종목코드 in self.df_jg.index:
                    보유수량 = round(self.df_jg['보유수량'][종목코드] + 체결수량, 8)
                    매입금액 = int(self.df_jg['매입금액'][종목코드] + 체결수량 * 체결가격)
                    매입가 = round(매입금액 / 보유수량, 4)
                    평가금액, 수익금, 수익율 = GetUpbitPgSgSp(매입금액, 보유수량 * 체결가격)
                    columns = ['매입가', '현재가', '수익율', '평가손익', '매입금액', '평가금액', '보유수량', '매수시간']
                    self.df_jg.loc[종목코드, columns] = 매입가, 체결가격, 수익율, 수익금, 매입금액, 평가금액, 보유수량, index[:14]
                else:
                    보유수량 = 체결수량
                    매입금액 = int(체결수량 * 체결가격)
                    매입가 = 체결가격
                    평가금액, 수익금, 수익율 = GetUpbitPgSgSp(매입금액, 보유수량 * 체결가격)
                    self.df_jg.loc[종목코드] = 종목코드, 매입가, 체결가격, 수익율, 수익금, 매입금액, 평가금액, 보유수량, 0, 0, index[:14]

                if 미체결수량 == 0:
                    self.df_jg.loc[종목코드, '분할매수횟수'] = self.df_jg['분할매수횟수'][종목코드] + 1
                    if 종목코드 in self.dict_order[주문구분].keys():
                        del self.dict_order[주문구분][종목코드]

            else:
                보유수량 = round(self.df_jg['보유수량'][종목코드] - 체결수량, 8)
                매입가 = self.df_jg['매입가'][종목코드]
                if 보유수량 != 0:
                    매입금액 = int(매입가 * 보유수량)
                    평가금액, 수익금, 수익율 = GetUpbitPgSgSp(매입금액, 보유수량 * 체결가격)
                    columns = ['현재가', '수익율', '평가손익', '매입금액', '평가금액', '보유수량']
                    self.df_jg.loc[종목코드, columns] = 체결가격, 수익율, 수익금, 매입금액, 평가금액, 보유수량
                else:
                    self.df_jg.drop(index=종목코드, inplace=True)

                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.df_jg.loc[종목코드, '분할매도횟수'] = self.df_jg['분할매도횟수'][종목코드] + 1
                    if 종목코드 in self.dict_order[주문구분].keys():
                        del self.dict_order[주문구분][종목코드]

                매입금액 = 매입가 * 체결수량
                평가금액, 수익금, 수익율 = GetUpbitPgSgSp(매입금액, 체결수량 * 체결가격)
                if -100 < 수익율 < 100: self.UpdateTradelist(index, 종목코드, 매입금액, 평가금액, 체결수량, 수익율, 수익금, index[:14])
                if 수익율 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['코인매수금지손절간격초'])

            columns = ['평가손익', '매입금액', '평가금액', '분할매수횟수', '분할매도횟수']
            self.df_jg[columns] = self.df_jg[columns].astype(int)
            self.df_jg.sort_values(by=['매입금액'], ascending=False, inplace=True)
            self.cstgQ.put(('잔고목록', self.df_jg))

            if 미체결수량 == 0: self.cstgQ.put((주문구분 + '완료', 종목코드))
            self.UpdateChegeollist(index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, index[:14], 주문가격, 주문번호)

            if 주문구분 == '매수':
                self.dict_intg['예수금'] -= 체결수량 * 체결가격
                if self.dict_set['코인모의투자']:
                    self.dict_intg['추정예수금'] -= 체결수량 * 체결가격
            else:
                self.dict_intg['예수금'] += 매입금액 + 수익금
                self.dict_intg['추정예수금'] += 매입금액 + 수익금

            self.queryQ.put(('거래디비', self.df_jg, 'c_jangolist', 'replace'))
            if self.dict_set['코인알림소리']: self.soundQ.put(f"{종목코드} {주문구분}하였습니다.")
            self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}체결] {종목코드} | {체결가격} | {체결수량}'))

        elif 주문구분 == '시드부족':
            self.UpdateChegeollist(index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, index[:14], 주문가격, 주문번호)

        elif 주문구분 in ('매수취소', '매도취소'):
            if 주문구분 == '매수취소':
                self.dict_intg['추정예수금'] += 주문수량 * 주문가격
                if 종목코드 in self.dict_order[주문구분].keys():
                    del self.dict_order[주문구분][종목코드]
            elif 종목코드 in self.dict_order[주문구분].keys():
                del self.dict_order[주문구분][종목코드]

            self.cstgQ.put((주문구분, 종목코드))
            self.UpdateChegeollist(index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, index[:14], 주문가격, 주문번호)

            if self.dict_set['코인알림소리']: self.soundQ.put(f"{종목코드} {주문구분}하였습니다.")
            self.windowQ.put((ui_num['C로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}] {종목코드} | {주문가격} | {주문수량}'))

        self.creceivQ.put(('잔고목록', tuple(self.df_jg.index)))
        self.creceivQ.put(('주문목록', self.GetOrderCodeList()))

    def UpdateTradelist(self, index, 종목명, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간):
        self.df_td.loc[index] = 종목명, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간
        self.windowQ.put((ui_num['C거래목록'], self.df_td[::-1]))
        df = pd.DataFrame([[종목명, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간]], columns=columns_td, index=[index])
        self.queryQ.put(('거래디비', df, 'c_tradelist', 'append'))
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        거래횟수 = len(self.df_td.drop_duplicates(['종목명', '체결시간']))
        총매수금액 = self.df_td['매수금액'].sum()
        총매도금액 = self.df_td['매도금액'].sum()
        총수익금액 = self.df_td[self.df_td['수익금'] > 0]['수익금'].sum()
        총손실금액 = self.df_td[self.df_td['수익금'] < 0]['수익금'].sum()
        수익금합계 = self.df_td['수익금'].sum()
        수익율 = round(수익금합계 / self.dict_intg['추정예탁자산'] * 100, 2)

        self.df_tt.loc[self.str_today] = 거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익율, 수익금합계
        self.windowQ.put((ui_num['C실현손익'], self.df_tt))

        if not first:
            self.teleQ.put(f'손익 알림 - 총매수금액 {총매수금액:,.0f}, 총매도금액 {총매도금액:,.0f}, 수익 {총수익금액:,.0f}, 손실 {총손실금액:,.0f}, 수익금합계 {수익금합계:,.0f}')

        if self.dict_set['스톰라이브']:
            수익율 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익율, 수익금합계]
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
            총수익율 = round(총평가손익 / 총매입금액 * 100, 2)
            self.dict_intg['추정예탁자산'] = self.dict_intg['예수금'] + 총평가금액
            self.df_tj = pd.DataFrame([[self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 잔고수량, 총수익율, 총평가손익, 총매입금액, 총평가금액]], columns=columns_tj, index=[self.str_today])
        else:
            self.df_tj = pd.DataFrame([[self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 0, 0.0, 0, 0, 0]], columns=columns_tj, index=[self.str_today])

        총평가손익 = self.df_jg['평가손익'].sum() + self.df_td['수익금'].sum()
        if self.dict_set['코인손실중지']:
            기준손실금 = self.dict_intg['추정예탁자산'] * self.dict_set['코인손실중지수익율'] / 100
            if 기준손실금 < -총평가손익: self.StrategyStop()
        if self.dict_set['코인수익중지']:
            기준수익금 = self.dict_intg['추정예탁자산'] * self.dict_set['코인수익중지수익율'] / 100
            if 기준수익금 < 총평가손익: self.StrategyStop()

        if self.dict_set['코인투자금고정']:
            종목당투자금 = int(self.dict_set['코인투자금'] * 1_000_000)
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

    def CheckError(self, ret):
        if type(ret) == dict and list(ret.keys())[0] == 'error':
            self.windowQ.put((ui_num['C로그텍스트'], f"시스템 명령 오류 알림 - {ret['error']['name']} : {ret['error']['message']}"))
            return False
        return True

    def GetOrderCodeList(self):
        return tuple(self.dict_order['매수'].keys()) + tuple(self.dict_order['매도'].keys())

    def GetMichegeolDF(self, code, gubun):
        return self.df_cj[(self.df_cj['종목명'] == code) & ((self.df_cj['주문구분'] == gubun) | (self.df_cj['주문구분'] == f'{gubun} 접수'))]

    def GetIndex(self):
        index = str_ymdhmsf(now_utc())
        if index in self.df_cj.index:
            while index in self.df_cj.index:
                index = str(int(index) + 1)
        return index
