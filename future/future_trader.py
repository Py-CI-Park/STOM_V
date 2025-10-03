import os
import sys
import time
import sqlite3
import pandas as pd
from threading import Thread
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num, columns_cj, DB_TRADELIST, DICT_SET, columns_tdf, columns_jgf
from utility.static import now, timedelta_sec, GetFutureLongPgSgSp, GetFutureShortPgSgSp, str_ymd, now_cme, \
    error_decorator, str_ymdhms, str_hms, str_ymdhmsf, str_hmsf, dt_hms, float_hmsf


class PutDictjango(Thread):
    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        floathmsf = float_hmsf()
        while True:
            if float_hmsf() > floathmsf + 0.5:
                floathmsf = float_hmsf()
                self.main.sstgQ.put(('잔고목록', self.main.dict_jg.copy()))
            time.sleep(0.01)


class Scheduler(Thread):
    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        inthms = int(str_hms(now_cme()))
        while True:
            if int(str_hms(now_cme())) > inthms:
                inthms = int(str_hms(now_cme()))
                if self.main.dict_set['주식타임프레임'] and inthms < self.main.dict_set['주식전략종료시간']:
                    self.main.straderQ.put('OrderTimeControl')
                if self.main.jgcs_time < inthms and not self.main.dict_bool['해선잔고청산']:
                    self.main.straderQ.put('JangoCheongsan')
                self.main.straderQ.put('UpdateTotaljango')
            time.sleep(0.01)


class FutureTrader:
    def __init__(self, qlist):
        """
        self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQ, self.futureQ
                0            1              2             3           4
        """
        self.kwzservQ    = qlist[0]
        self.sreceivQ    = qlist[1]
        self.straderQ    = qlist[2]
        self.sstgQ       = qlist[3]
        self.futureQ     = qlist[4]
        self.dict_set    = DICT_SET

        self.dict_cj     = {}  # 체결목록
        self.dict_jg     = {}  # 잔고목록
        self.dict_tj     = {}  # 잔고평가
        self.dict_td     = {}  # 거래목록
        self.dict_tt     = {}  # 평가손익
        self.dict_signal = {}
        self.dict_curc   = {}
        self.dict_info   = {}
        self.dict_order  = {
            'BUY_LONG': {},
            'SELL_LONG': {},
            'SELL_SHORT': {},
            'BUY_SHORT': {}
        }
        self.dict_intg   = {
            '예수금': 0,
            '추정예수금': 0,
            '예탁자산': 0,
            '추정예탁자산': 0
        }
        self.dict_bool = {
            '해선잔고청산': False
        }
        self.거래구분 = {
            '시장가': '1',
            '지정가': '2'
        }

        self.jgcs_time = self.get_jgcs_time()
        self.str_today = str_ymd(now_cme())

        self.put_dict_jango = PutDictjango(self)
        self.put_dict_jango.daemon = True
        self.put_dict_jango.start()

        self.scheduler = Scheduler(self)
        self.scheduler.daemon = True
        self.scheduler.start()

        self.LoadDatabase()
        self.Mainloop()

    def get_jgcs_time(self):
        return int(str_hms(timedelta_sec(-120, dt_hms(str(self.dict_set['주식전략종료시간'])))))

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        df_cj = pd.read_sql(f"SELECT * FROM f_chegeollist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        df_td = pd.read_sql(f"SELECT * FROM f_tradelist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        if len(df_cj) > 0:
            self.dict_cj = df_cj.to_dict('index')
            self.kwzservQ.put(('window', (ui_num['S체결목록'], df_cj[::-1])))
        if len(df_td) > 0:
            self.dict_td = df_td.to_dict('index')
            self.kwzservQ.put(('window', (ui_num['S거래목록'], df_td[::-1])))
            self.UpdateTotaltradelist(first=True)
        if self.dict_set['주식모의투자']:
            df_jg = pd.read_sql(f'SELECT * FROM f_jangolist', con).set_index('index')
            if len(df_jg) > 0:
                self.dict_jg = df_jg.to_dict('index')
                self.sreceivQ.put(('잔고목록', tuple(self.dict_jg.keys())))
        con.close()
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 정보 불러오기 완료')))

    def Mainloop(self):
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더 시작')))
        while True:
            data = self.straderQ.get()
            if type(data) == tuple:
                self.UpdateTuple(data)
            elif type(data) == str:
                self.UpdateString(data)

    def UpdateTuple(self, data):
        if len(data) in (7, 8):
            self.CheckOrder(data)
        elif len(data) == 2:
            if data[0] == '체잔통보':
                self.UpdateChejanData(data[1])
            elif data[0] == '주문전송':
                code, gubun = data[1]
                self.dict_signal[code] = gubun
            elif data[0] == '잔고갱신':
                self.UpdateJango(data[1])
            elif data[0] == '주문확인':
                code, c = data
                self.dict_curc[code] = c
                self.OrderTimeControl(code)
            elif data[0] == '증거금부족':
                gubun = self.dict_signal[data[1]]
                self.PutOrderComplete(f'{gubun}_CANCEL', data[1])
            elif data[0] == '종목정보':
                self.dict_info = data[1]
                dummy_time = timedelta_sec(-3600, now_cme())
                for code in self.dict_info.keys():
                    self.dict_info[code]['시드부족시간'] = dummy_time
                    self.dict_info[code]['최종거래시간'] = dummy_time
                    self.dict_info[code]['손절거래시간'] = dummy_time
            elif data[0] == '잔고조회':
                self.UpdateYesugm(data[1])
            elif data[0] == '설정변경':
                self.dict_set  = data[1]
                self.jgcs_time = self.get_jgcs_time()

    def UpdateString(self, data):
        if data == 'UpdateTotaljango':
            self.UpdateTotaljango()
        elif data == 'OrderTimeControl':
            self.OrderTimeControl()
        elif data == 'JangoCheongsan':
            self.JangoCheongsan('자동')
        elif data == '체결목록':
            df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
            self.kwzservQ.put(('tele', df_cj)) if len(df_cj) > 0 else self.kwzservQ.put(('tele', '현재는 체결목록이 없습니다.'))
        elif data == '거래목록':
            df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
            self.kwzservQ.put(('tele', df_td)) if len(df_td) > 0 else self.kwzservQ.put(('tele', '현재는 거래목록이 없습니다.'))
        elif data == '잔고평가':
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.kwzservQ.put(('tele', df_jg)) if len(df_jg) > 0 else self.kwzservQ.put(('tele', '현재는 잔고목록이 없습니다.'))
        elif data == '잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로세스종료':
            self.SysExit()

    def CheckOrder(self, data):
        if len(data) == 7:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 수동주문 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 수동주문, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.dict_jg.keys()
        롱매수주문중 = 종목코드 in self.dict_order['BUY_LONG'].keys()
        숏매수주문중 = 종목코드 in self.dict_order['SELL_SHORT'].keys()
        롱매도주문중 = 종목코드 in self.dict_order['SELL_LONG'].keys()
        숏매도주문중 = 종목코드 in self.dict_order['BUY_SHORT'].keys()
        포지션 = self.dict_jg[종목코드]['포지션'] if 종목코드 in self.dict_jg.keys() else None

        원주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 수동주문:
            if (주문구분 == 'SELL_LONG' and (잔고없음 or 롱매도주문중)) or (주문구분 == 'BUY_SHORT' and (잔고없음 or 숏매도주문중)):
                주문취소 = True
        elif 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
            inthms = int(str_hms(now_cme()))
            거래횟수 = len(set([v['체결시간'] for k, v in self.dict_td.items() if v['종목명'] == 종목명]))
            손절횟수 = len(set([v['체결시간'] for k, v in self.dict_td.items() if v['종목명'] == 종목명 and v['수익률'] < 0]))
            if self.dict_set['주식매수금지거래횟수'] and self.dict_set['주식매수금지거래횟수값'] <= 거래횟수:
                주문취소 = True
            elif self.dict_set['주식매수금지손절횟수'] and self.dict_set['주식매수금지손절횟수값'] <= 손절횟수:
                주문취소 = True
            elif 잔고없음 and inthms < self.dict_set['주식전략종료시간'] and len(self.dict_jg) >= self.dict_set['주식최대매수종목수']:
                주문취소 = True
            elif self.dict_set['주식매수금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
            elif self.dict_set['주식매수금지손절간격'] and 현재시간 < self.dict_info[종목코드]['손절거래시간']:
                주문취소 = True
            elif not 잔고없음 and self.dict_jg[종목코드]['분할매수횟수'] >= self.dict_set['주식매수분할횟수']:
                주문취소 = True
            elif self.dict_intg['추정예수금'] < 주문수량 * self.dict_info[종목코드]['위탁증거금']:
                if 현재시간 > self.dict_info[종목코드]['시드부족시간']:
                    self.CreateOrder('시드부족', 종목코드, 종목명, 주문가격, 주문수량, str_hmsf(now_cme()), 시그널시간, 수동주문, 0, None)
                    self.dict_info[종목코드]['시드부족시간'] = timedelta_sec(180)
                주문취소 = True
            elif 포지션 == 'LONG' and 'SHORT' in 주문구분: 주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분: 주문취소 = True
            elif 주문구분 == 'BUY_LONG' and 롱매수주문중:   주문취소 = True
            elif 주문구분 == 'SELL_SHORT' and 숏매수주문중: 주문취소 = True
        elif 주문구분 in ('SELL_LONG', 'BUY_SHORT'):
            if 포지션 == 'LONG' and 'SHORT' in 주문구분:   주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분: 주문취소 = True
            elif 주문구분 == 'SELL_LONG' and 롱매도주문중:  주문취소 = True
            elif 주문구분 == 'BUY_SHORT' and 숏매도주문중:  주문취소 = True
            elif self.dict_set['주식매도금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']: 주문취소 = True
        elif 'CANCEL' in 주문구분:
            if 주문구분 == 'BUY_LONG_CANCEL' and not 롱매수주문중:     주문취소 = True
            elif 주문구분 == 'SELL_SHORT_CANCEL' and not 숏매수주문중: 주문취소 = True
            elif 주문구분 == 'SELL_LONG_CANCEL' and not 롱매도주문중:  주문취소 = True
            elif 주문구분 == 'BUY_SHORT_CANCEL' and not 숏매도주문중:  주문취소 = True
        elif self.dict_bool['해선잔고청산']:
            주문취소 = True

        if 주문취소:
            if 'CANCEL' not in 주문구분:
                self.sstgQ.put((f'{주문구분}_CANCEL', 종목코드))
        else:
            if 수동주문 and 'CANCEL' not in 주문구분:
                self.sstgQ.put((f'{주문구분}_MANUAL', 종목코드))

            if 주문수량 > 0:
                self.CreateOrder(주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 수동주문, 0, 수동주문유형)
            else:
                if 주문구분 == 'BUY_LONG':
                    if self.dict_set['주식매도취소매수시그널'] and 롱매도주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'SELL_SHORT':
                    if self.dict_set['주식매도취소매수시그널'] and 숏매도주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'SELL_LONG':
                    if self.dict_set['주식매수취소매도시그널'] and 롱매수주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'BUY_SHORT':
                    if self.dict_set['주식매수취소매도시그널'] and 숏매수주문중: self.CancelOrder(종목코드, 주문구분)
                self.sstgQ.put((f'{주문구분}_CANCEL', 종목코드))

    def CreateOrder(self, 주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 수동주문, 정정횟수, 수동주문유형):
        주문유형 = 0
        if 주문구분 in ('SELL_LONG', 'BUY_SHORT'):                 주문유형 = 1
        elif 주문구분 in ('BUY_LONG', 'SELL_SHORT'):               주문유형 = 2
        elif 주문구분 in ('SELL_LONG_CANCEL', 'BUY_SHORT_CANCEL'): 주문유형 = 3
        elif 주문구분 in ('BUY_LONG_CANCEL', 'SELL_SHORT_CANCEL'): 주문유형 = 4
        elif 주문구분 in ('SELL_LONG_MODIFY', 'BUY_SHORT_MODIFY'): 주문유형 = 5
        elif 주문구분 in ('BUY_LONG_MODIFY', 'SELL_SHORT_MODIFY'): 주문유형 = 6

        if 수동주문:
            거래구분 = '1'
        elif 'BUY_LONG' in 주문구분 or 'BUY_SHORT' in 주문구분:
            거래구분 = self.거래구분[self.dict_set['주식매수주문구분']] if 수동주문유형 is None else self.거래구분[수동주문유형]
        else:
            거래구분 = self.거래구분[self.dict_set['주식매도주문구분']] if 수동주문유형 is None else self.거래구분[수동주문유형]

        if 주문구분 in ('BUY_LONG', 'SELL_SHORT') and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['주식매수주문구분']:
                gap = self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매수지정가호가번호']
                주문가격 = round((주문가격 + gap) if 주문구분 == 'BUY_LONG' else (주문가격 - gap), self.dict_info[종목코드]['소숫점자리수'])
            if self.dict_set['주식매수주문구분'] == '시장가' and not (self.dict_set['주식모의투자'] or 주문구분 == '시드부족'):
                주문가격 = 0
        elif 주문구분 in ('SELL_LONG', 'BUY_SHORT') and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['주식매도주문구분']:
                gap = self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매도지정가호가번호']
                주문가격 = round((주문가격 + gap) if 주문구분 == 'SELL_LONG' else (주문가격 - gap), self.dict_info[종목코드]['소숫점자리수'])
            if self.dict_set['주식매도주문구분'] == '시장가' and not (self.dict_set['주식모의투자'] or 주문구분 == '시드부족'):
                주문가격 = 0

        if 주문수량 > 0:
            if self.dict_set['주식모의투자'] or 주문구분 == '시드부족':
                self.dict_signal[종목코드] = 주문구분
                ct = str_ymdhms(now_cme())
                self.OrderTimeLog(시그널시간)
                if 주문구분 == '시드부족':
                    data = (종목코드, 종목명, '접수불가', 주문구분, '매수', 주문수량, 0, 주문가격, ct, 원주문번호, 0, 0)
                else:
                    주문구분 = '매수' if 주문구분 in ('BUY_LONG', 'SELL_SHORT') else '매도'
                    data = (종목코드, 종목명, '체결', '신규', 주문구분, 주문수량, 0, 주문가격, ct, 원주문번호, 주문수량, 주문가격)
                self.UpdateChejanData(data)
            else:
                data = [주문구분, '', '', 주문유형, 종목코드, 주문수량, 주문가격, '', 거래구분, 원주문번호, 종목명, 시그널시간]
                self.futureQ.put(data)

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.')))

    def OrderTimeControl(self, code_=None):
        cancel_list = []
        modify_list = []

        for gubun in self.dict_order.keys():
            for code in self.dict_order[gubun].keys():
                if code_ is None or code == code_:
                    order_info = self.dict_order[gubun][code]
                    if gubun in ('BUY_LONG', 'SELL_SHORT'):
                        if self.dict_set['주식매수취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    else:
                        if self.dict_set['주식매수취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    if gubun in ('BUY_LONG', 'BUY_SHORT'):
                        if order_info[1] < self.dict_set['주식매수정정횟수'] and code in self.dict_curc.keys() and \
                                self.dict_curc[code] >= order_info[2] + self.dict_info[code]['호가단위'] * self.dict_set['주식매수정정호가차이']:
                            modify_list.append((code, gubun))
                    else:
                        if order_info[1] < self.dict_set['주식매도정정횟수'] and code in self.dict_curc.keys() and \
                                self.dict_curc[code] <= order_info[2] - self.dict_info[code]['호가단위'] * self.dict_set['주식매도정정호가차이']:
                            modify_list.append((code, gubun))

        if cancel_list:
            for code, gubun in cancel_list:
                self.CancelOrder(code, gubun)
        if modify_list:
            for code, gubun in modify_list:
                self.ModifyOrder(code, gubun)

    def GetNameChejan(self, name, gubun):
        return {k: v for k, v in self.dict_cj.items() if v['종목명'] == name and (v['주문구분'] == gubun or v['주문구분'] == f'{gubun}_REG')}

    def CancelOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        dict_cj = self.GetNameChejan(종목명, 주문구분)
        last_key = list(dict_cj.keys())[-1]
        if len(dict_cj) > 0:
            미체결수량 = dict_cj[last_key]['미체결수량']
            if 미체결수량 > 0:
                현재시간 = now()
                주문번호 = dict_cj[last_key]['주문번호']
                self.CreateOrder(f'{주문구분}_CANCEL', 종목코드, 종목명, 0, 미체결수량, 주문번호, 현재시간, False, 0, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        dict_cj = self.GetNameChejan(종목명, 주문구분)
        last_key = list(dict_cj.keys())[-1]
        if len(dict_cj) > 0:
            미체결수량 = dict_cj[last_key]['미체결수량']
            if 미체결수량 > 0:
                if 주문구분 == 'BUY_LONG':
                    정정가격 = self.dict_curc[종목코드] - self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매수정정호가']
                elif 주문구분 == 'SELL_SHORT':
                    정정가격 = self.dict_curc[종목코드] + self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매수정정호가']
                elif 주문구분 == 'SELL_LONG':
                    정정가격 = self.dict_curc[종목코드] + self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매도정정호가']
                else:
                    정정가격 = self.dict_curc[종목코드] - self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매도정정호가']

                현재시간 = now()
                정정횟수 = self.dict_order[주문구분][종목코드][1] + 1
                주문번호 = dict_cj[last_key]['주문번호']
                self.CreateOrder(f'{주문구분}_MODIFY', 종목코드, 종목명, 정정가격, 미체결수량, 주문번호, 현재시간, False, 정정횟수, None)

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            # ['종목명', '포지션', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
            if 현재가 != self.dict_jg[종목코드]['현재가']:
                포지션 = self.dict_jg[종목코드]['포지션']
                매입가 = self.dict_jg[종목코드]['매입가']
                매입금액 = self.dict_jg[종목코드]['매입금액']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                평가금액 = 매입금액 + (현재가 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                if 포지션 == 'LONG':
                    평가금액, 평가손익, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                else:
                    평가금액, 평가손익, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                self.dict_jg[종목코드].update({
                    '현재가': 현재가,
                    '수익률': 수익률,
                    '평가손익': 평가손익,
                    '평가금액': 평가금액
                })
        except:
            pass

    def JangoCheongsan(self, gubun):
        self.dict_bool['해선잔고청산'] = True

        for 주문구분 in self.dict_order.keys():
            for 종목코드 in self.dict_order[주문구분].keys():
                self.CancelOrder(종목코드, 주문구분)

        if self.dict_jg and (gubun == '수동' or self.dict_set['주식잔고청산']):
            if gubun == '수동':
                self.kwzservQ.put(('tele', '해선 잔고청산 주문을 전송합니다.'))
            for 종목코드 in self.dict_jg.keys():
                포지션 = self.dict_jg[종목코드]['포지션']
                종목명 = self.dict_jg[종목코드]['종목명']
                현재가 = self.dict_jg[종목코드]['현재가']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                주문구분 = 'SELL_LONG' if 포지션 == 'LONG' else 'BUY_SHORT'
                if self.dict_set['주식모의투자']:
                    self.dict_signal[종목코드] = 주문구분
                    ct = str_ymdhms(now_cme())
                    data = (종목코드, 종목명, '체결', '신규', '매도', 보유수량, 0, 현재가, ct, '', 보유수량, 현재가)
                    self.UpdateChejanData(data)
                else:
                    self.CheckOrder((주문구분, 종목코드, 종목명, 현재가, 보유수량, now(), True))
            if self.dict_set['주식알림소리']:
                self.kwzservQ.put(('sound', '해선 잔고청산 주문을 전송하였습니다.'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 실행 알림 - 해선 잔고청산 주문 완료')))
        elif not self.dict_jg and gubun == '수동':
            self.kwzservQ.put(('tele', '현재는 해선 보유종목이 없습니다.'))

    def UpdateYesugm(self, data):
        yesugm, dict_jg = data
        self.dict_intg = {
            '예수금': yesugm,
            '추정예수금': yesugm,
            '예탁자산': yesugm,
            '추정예탁자산': yesugm
        }
        if dict_jg:
            self.dict_jg = dict_jg
            for index in self.dict_jg.keys():
                yesugm = self.dict_jg[index]['보유수량'] * self.dict_info[index]['위탁증거금']
                self.dict_intg['예수금'] -= yesugm
            self.dict_intg['추정예수금'] = self.dict_intg['예수금']

    def SysExit(self):
        self.SaveDayData()
        time.sleep(5)
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 트레이더 종료')))

    def SaveDayData(self):
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM f_totaltradelist WHERE `index` = '{self.str_today}'", con)
        con.close()
        if len(df) == 0:
            df = pd.DataFrame.from_dict(self.dict_tt, orient='index')
            self.kwzservQ.put(('query', ('거래디비', df, 'f_totaltradelist', 'append')))
            if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', '일별실현손익를 저장하였습니다.'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 일별실현손익 저장 완료')))

    def GetIndex(self):
        index = str_ymdhmsf(now_cme())
        if index in self.dict_cj.keys():
            while index in self.dict_cj.keys():
                index = str(int(index) + 1)
        return index

    @error_decorator
    def UpdateChejanData(self, data):
        종목코드, 종목명, 주문상태, 주문구분, 매도수구분, 주문수량, 미체결수량, 주문가격, 주문시간, 주문번호, 체결수량, 체결가격 = data
        index = self.GetIndex()
        gubun = self.dict_signal[종목코드]

        if 주문상태 == '접수' and 주문구분 == '신규' and 매도수구분 in ('매수', '매도'):
            취소시간 = timedelta_sec(self.dict_set['주식매수취소시간초' if 매도수구분 == '매수' else '주식매도취소시간초'])
            if 매도수구분 == '매수': self.dict_intg['추정예수금'] -= 주문수량 * self.dict_info[종목코드]['위탁증거금']
            self.dict_order[gubun][종목코드] = [취소시간, 0, 주문가격]
            self.UpdateChegeollist(index, 종목코드, 종목명, f'{gubun}_REG', 주문수량, 0, 미체결수량, 0, 주문시간, 주문가격, 주문번호)
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{gubun}_REG] {종목명} | {주문가격} | {주문수량}')))

        elif 주문상태 == '접수불가':
            self.UpdateChegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

        elif 주문상태 == '체결' and 주문구분 == '체결' and 매도수구분 in ('매수', '매도'):
            if 매도수구분 == '매수':
                # ['종목명', '포지션', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                if 종목코드 in self.dict_jg.keys():
                    직전매입가 = self.dict_jg[종목코드]['매입가']
                    직전보유수량 = self.dict_jg[종목코드]['보유수량']
                    직전매입금액 = self.dict_jg[종목코드]['매입금액']
                    보유수량 = 직전보유수량 + 체결수량
                    매입금액 = 직전매입금액 + self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    매입가 = round((직전매입가 * 직전보유수량 + 체결가격 * 체결수량) / 보유수량, self.dict_info[종목코드]['소숫점자리수'] + 1)
                    평가금액 = 매입금액 + (체결가격 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    if 'LONG' in gubun:
                        평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                    else:
                        평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                    self.dict_jg[종목코드].update({
                        '매입가': 매입가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '매수시간': index[:14]
                    })
                else:
                    보유수량 = 체결수량
                    매입금액 = 평가금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    if 'LONG' in gubun:
                        포지션 = 'LONG'
                        평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                    else:
                        포지션 = 'SHORT'
                        평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                    self.dict_jg[종목코드] = {
                        '종목명': 종목코드,
                        '포지션': 포지션,
                        '매입가': 체결가격,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 체결수량,
                        '분할매수횟수': 0,
                        '분할매도횟수': 0,
                        '매수시간': index[:14]
                    }

                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.dict_jg[종목코드]['분할매수횟수'] += 1
                    if 종목코드 in self.dict_order[주문구분].keys():
                        del self.dict_order[주문구분][종목코드]

            else:
                if 종목코드 not in self.dict_jg.keys(): return
                포지션 = self.dict_jg[종목코드]['포지션']
                매입가 = self.dict_jg[종목코드]['매입가']
                보유수량 = self.dict_jg[종목코드]['보유수량'] - 체결수량
                if 보유수량 != 0:
                    매입금액 = self.dict_info[종목코드]['위탁증거금'] * 보유수량
                    평가금액 = 매입금액 + (체결가격 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    if 'LONG' in gubun:
                        평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                    else:
                        평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                    # ['종목명', '포지션', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '레버리지', '분할매수횟수', '분할매도횟수', '매수시간']
                    self.dict_jg[종목코드].update({
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량
                    })
                else:
                    del self.dict_jg[종목코드]

                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.dict_jg[종목코드]['분할매도횟수'] += 1
                    if 종목코드 in self.dict_order[주문구분].keys():
                        del self.dict_order[주문구분][종목코드]

                매입금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                평가금액 = 매입금액 + (체결가격 - 매입가) * self.dict_info[종목코드]['틱가치'] * 체결수량
                if 'LONG' in gubun:
                    평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                else:
                    평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                if -100 < 수익률 < 100: self.UpdateTradelist(index, 종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간)
                if 수익률 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['주식매수금지손절간격초'])

            sorted_items = sorted(self.dict_jg.items(), key=lambda x: x[1]['매입금액'], reverse=True)
            self.dict_jg = {k: v for k, v in sorted_items}

            if 미체결수량 == 0: self.PutOrderComplete(f'{gubun}_COMPLETE', 종목코드)
            self.UpdateChegeollist(index, 종목코드, 종목명, gubun, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            총위탁증거금 = 체결수량 * self.dict_info[종목코드]['위탁증거금']
            if 매도수구분 == '매수':
                self.dict_intg['예수금'] -= 총위탁증거금
                if self.dict_set['주식모의투자']:
                    self.dict_intg['추정예수금'] -= 총위탁증거금
            else:
                self.dict_intg['추정예탁자산'] += 수익금
                self.dict_intg['예수금'] += 총위탁증거금 + 수익금
                self.dict_intg['추정예수금'] += 총위탁증거금 + 수익금

            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.kwzservQ.put(('query', ('거래디비', df_jg, 'f_jangolist', 'replace')))
            if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', f'{종목명} {체결수량}주를 {주문구분}하였습니다'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{gubun}] {종목명} | {체결가격} | {체결수량}')))

        elif 주문상태 == '확인' and 주문구분 in ('정정', '취소'):
            if 주문구분 == '정정':
                gubun_ = gubun.replace('_MODIFY', '')
                정정횟수 = self.dict_order[gubun_][종목코드][1] + 1
                취소시간 = timedelta_sec(self.dict_set['주식매수취소시간초' if 매도수구분 == '매수' else '주식매도취소시간초'])
                self.dict_order[gubun_][종목코드] = [취소시간, 정정횟수, 주문가격]
            else:
                gubun_ = gubun.replace('_CANCEL', '')
                if 매도수구분 == '매수':
                    self.dict_intg['추정예수금'] += 주문수량 * self.dict_info[종목코드]['위탁증거금']
                if 종목코드 in self.dict_order[gubun_].keys():
                    del self.dict_order[gubun_][종목코드]
                self.PutOrderComplete(gubun, 종목코드)

            self.UpdateChegeollist(index, 종목코드, 종목명, gubun, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', f'{종목명} {주문수량}주를 {주문구분}하였습니다'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{gubun}] {종목명} | {주문가격} | {주문수량}')))

        elif 주문상태 in ('미접수', '취소', '거부'):
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{주문상태}][{gubun}] {종목명} | {주문가격} | {주문수량}')))

        self.sreceivQ.put(('잔고목록', tuple(self.dict_jg.keys())))
        self.sreceivQ.put(('주문목록', self.GetOrderCodeList()))

    def PutOrderComplete(self, cmsg, code):
        self.sstgQ.put((cmsg, code))

    def GetOrderCodeList(self):
        return tuple(self.dict_order['BUY_LONG'].keys()) + tuple(self.dict_order['SELL_SHORT'].keys()) + \
            tuple(self.dict_order['SELL_LONG'].keys()) + tuple(self.dict_order['BUY_SHORT'].keys())

    def UpdateTradelist(self, index, 종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간):
        # ['종목명', '포지션', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
        self.dict_td[index] = {
            '종목명': 종목명,
            '포지션': 포지션,
            '매수금액': 매입금액,
            '매도금액': 평가금액,
            '주문수량': 체결수량,
            '수익률': 수익률,
            '수익금': 수익금,
            '체결시간': 주문시간
        }
        df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
        self.kwzservQ.put(('window', (ui_num['S거래목록'], df_td[::-1])))
        df = pd.DataFrame([[종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간]], columns=columns_tdf, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 'f_tradelist', 'append')))
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        거래횟수 = len(set([(v['종목명'], v['체결시간']) for k, v in self.dict_td.items()]))
        총매수금액 = sum([v['매수금액'] for k, v in self.dict_td.items()])
        총매도금액 = sum([v['매도금액'] for k, v in self.dict_td.items()])
        총수익금액 = sum([v['수익금'] for k, v in self.dict_td.items() if v['수익금'] >= 0])
        총손실금액 = sum([v['수익금'] for k, v in self.dict_td.items() if v['수익금'] < 0])
        수익금합계 = sum([v['수익금'] for k, v in self.dict_td.items()])
        수익률 = round(수익금합계 / self.dict_intg['추정예탁자산'] * 100, 2)

        # ['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']
        self.dict_tt[self.str_today] = {
            '총매수금액': 총매수금액,
            '총매도금액': 총매도금액,
            '총수익금액': 총수익금액,
            '총손실금액': 총손실금액,
            '수익률': 수익률,
            '수익금합계': 수익금합계
        }
        df_tt = pd.DataFrame.from_dict(self.dict_tt, orient='index')
        self.kwzservQ.put(('window', (ui_num['S실현손익'], df_tt)))

        if not first:
            self.kwzservQ.put(('tele', f'총매수금액 {총매수금액:,.0f}, 총매도금액 {총매도금액:,.0f}, 수익 {총수익금액:,.0f}, 손실 {총손실금액:,.0f}, 수익금합계 {수익금합계:,.0f}'))

        if self.dict_set['스톰라이브']:
            수익률 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익률, 수익금합계]
            self.kwzservQ.put(('live', ('해선', data_list)))

    def UpdateChegeollist(self, index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호):
        # ['종목명', '주문구분', '주문수량', '체결수량', '미체결수량', '체결가', '체결시간', '주문가격', '주문번호']
        self.dict_info[종목코드]['최종거래시간'] = timedelta_sec(self.dict_set['코인매수금지간격초'])
        self.dict_cj[index] = {
            '종목명': 종목명,
            '주문구분': 주문구분,
            '주문수량': 주문수량,
            '체결수량': 체결수량,
            '미체결수량': 미체결수량,
            '체결가': 체결가격,
            '체결시간': 체결시간,
            '주문가격': 주문가격,
            '주문번호': 주문번호
        }
        sorted_items = sorted(self.dict_cj.items(), key=lambda x: x[0])
        self.dict_cj = {k: v for k, v in sorted_items}
        df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
        self.kwzservQ.put(('window', (ui_num['S체결목록'], df_cj[::-1])))
        df = pd.DataFrame([[종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]], columns=columns_cj, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 'f_chegeollist', 'append')))

    def UpdateTotaljango(self):
        # ['추정예탁자산', '추정예수금', '보유종목수', '수익률', '총평가손익', '총매입금액', '총평가금액']
        if self.dict_jg:
            총평가손익 = sum([v['평가손익'] for k, v in self.dict_jg.items()])
            총매입금액 = sum([v['매입금액'] for k, v in self.dict_jg.items()])
            총평가금액 = sum([v['평가금액'] for k, v in self.dict_jg.items()])
            총수익률 = round(총평가손익 / 총매입금액 * 100, 2)
            잔고수량 = len(self.dict_jg)
            추정예탁자산 = self.dict_intg['예수금'] + 총평가금액
        else:
            총평가손익, 총매입금액, 총평가금액, 총수익률, 잔고수량 = 0, 0, 0, 0., 0
            추정예탁자산 = self.dict_intg['예수금']

        self.dict_tj[self.str_today] = {
            '추정예탁자산': 추정예탁자산,
            '추정예수금': self.dict_intg['예수금'],
            '보유종목수': 잔고수량,
            '수익률': 총수익률,
            '총평가손익': 총평가손익,
            '총매입금액': 총매입금액,
            '총평가금액': 총평가금액
        }

        잔고평가손익합계 = sum([v['평가손익'] for k, v in self.dict_jg.items()])
        거래수익금합계 = sum([v['수익금'] for k, v in self.dict_td.items()])
        총평가손익 = 잔고평가손익합계 + 거래수익금합계
        if self.dict_set['주식손실중지']:
            기준손실금 = self.dict_intg['예탁자산'] * self.dict_set['주식손실중지수익률'] / 100
            if 기준손실금 < -총평가손익: self.StrategyStop()
        if self.dict_set['주식수익중지']:
            기준수익금 = self.dict_intg['예탁자산'] * self.dict_set['주식수익중지수익률'] / 100
            if 기준수익금 < 총평가손익: self.StrategyStop()

        if self.dict_jg:
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
        else:
            df_jg = pd.DataFrame(columns=columns_jgf)
        df_tj = pd.DataFrame.from_dict(self.dict_tj, orient='index')
        self.kwzservQ.put(('window', (ui_num['S잔고목록'], df_jg)))
        self.kwzservQ.put(('window', (ui_num['S잔고평가'], df_tj)))

    def StrategyStop(self):
        self.sstgQ.put('매수전략중지')
        self.JangoCheongsan('수동')
