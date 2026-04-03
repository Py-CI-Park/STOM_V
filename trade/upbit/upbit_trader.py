
import sys
import pyupbit
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from utility.setting_base import columns_cj, columns_td, ui_num, DB_TRADELIST, columns_jg
from utility.static import now, timedelta_sec, GetUpbitHogaunit, GetUpbitPgSgSp, now_utc, str_ymdhmsf, str_hmsf, \
    str_hms, str_ymd, dt_hms, qtest_qwait, set_builtin_print, error_decorator


class Updater(QThread):
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal(tuple)
    signal3 = pyqtSignal(str)

    def __init__(self, ctraderQ):
        super().__init__()
        self.ctraderQ = ctraderQ

    def run(self):
        while True:
            data = self.ctraderQ.get()
            if data.__class__ == tuple:
                if len(data) in (6, 7):
                    self.signal1.emit(data)
                else:
                    self.signal2.emit(data)
            elif data.__class__ == str:
                self.signal3.emit(data)


class UpbitTrader:
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, wdzservQ
           0        1       2      3       4      5      6      7       8         9         10     11      12
        """
        app = QApplication(sys.argv)

        self.windowQ       = qlist[0]
        self.soundQ        = qlist[1]
        self.queryQ        = qlist[2]
        self.teleQ         = qlist[3]
        self.creceivQ      = qlist[8]
        self.ctraderQ      = qlist[9]
        self.cstgQ         = qlist[10]
        self.liveQ         = qlist[11]
        self.dict_set      = dict_set

        self.order_time    = now()
        self.dict_cj       = {}  # 체결목록
        self.dict_jg       = {}  # 잔고목록
        self.dict_tj       = {}  # 잔고평가
        self.dict_td       = {}  # 거래목록
        self.dict_tt       = {}  # 평가손익
        self.dict_info     = {}
        self.dict_curc     = {}
        self.dict_order_cc = {}
        self.dict_order    = {
            '매수': {},
            '매도': {},
            '매수취소': {},
            '매도취소': {}
        }
        self.dict_intg = {
            '예수금': 0,
            '추정예수금': 0,
            '추정예탁자산': 0,
            '종목당투자금': 0
        }
        self.dict_bool = {
            '코인잔고청산': False
        }

        self.upbit     = pyupbit.Upbit(self.dict_set['Access_key1'], self.dict_set['Secret_key1'])
        self.jgcs_time = self.get_jgcs_time()
        self.str_today = str_ymd(now_utc())

        self.UpdateDictInfo()
        self.LoadDatabase()
        self.GetBalances()

        self.qtimer1 = QTimer()
        self.qtimer1.setInterval(500)
        self.qtimer1.timeout.connect(self.Scheduler1)
        self.qtimer1.start()

        self.qtimer2 = QTimer()
        self.qtimer2.setInterval(1 * 1000)
        self.qtimer2.timeout.connect(self.Scheduler2)
        self.qtimer2.start()

        self.updater = Updater(self.ctraderQ)
        self.updater.signal1.connect(self.CheckOrder)
        self.updater.signal2.connect(self.UpdateTuple)
        self.updater.signal3.connect(self.UpdateString)
        self.updater.start()

        set_builtin_print(True, self.windowQ)
        app.exec_()

    def get_jgcs_time(self):
        return int(str_hms(timedelta_sec(-120, dt_hms(str(self.dict_set['코인전략종료시간'])))))

    def UpdateDictInfo(self):
        dummy_time = timedelta_sec(-3600)
        for dict_ticker in pyupbit.get_tickers(fiat="KRW", verbose=True):
            code = dict_ticker['market']
            self.dict_info[code] = {
                '시드부족시간': dummy_time,
                '최종거래시간': dummy_time,
                '손절거래시간': dummy_time
            }

        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 코인명 수집 완료'))

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        df_cj = pd.read_sql(f"SELECT * FROM c_chegeollist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        df_td = pd.read_sql(f"SELECT * FROM c_tradelist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        if len(df_cj) > 0:
            self.dict_cj = df_cj.to_dict('index')
            self.windowQ.put((ui_num['C체결목록'], df_cj[::-1]))
        if len(df_td) > 0:
            self.dict_td = df_td.to_dict('index')
            self.windowQ.put((ui_num['C거래목록'], df_td[::-1]))
        if self.dict_set['코인모의투자']:
            df_jg = pd.read_sql(f'SELECT * FROM c_jangolist', con).set_index('index')
            if len(df_jg) > 0:
                self.dict_jg = df_jg.to_dict('index')
                self.creceivQ.put(('잔고목록', tuple(self.dict_jg)))
        con.close()
        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 데이터베이스 불러오기 완료'))

    def GetBalances(self):
        if self.dict_set['코인모의투자']:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql('SELECT * FROM c_tradelist', con)
            con.close()
            tcg = df['수익금'].sum()
            chujeonjasan = 100_000_000 + tcg
            if chujeonjasan < 100_000_000: chujeonjasan = 100_000_000
        else:
            ret = self.upbit.get_balances()
            if self.CheckError(ret):
                chujeonjasan = int(float(ret[0]['balance']))
            else:
                chujeonjasan = 0

        총매입금액 = sum([v['매입금액'] for v in self.dict_jg.values()]) if self.dict_jg else 0
        self.dict_intg['예수금'] = int(chujeonjasan - 총매입금액)
        self.dict_intg['추정예수금'] = int(chujeonjasan - 총매입금액)
        self.dict_intg['추정예탁자산'] = chujeonjasan

        if self.dict_td: self.UpdateTotaltradelist(first=True)

        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 예수금 조회 완료'))

        text = '코인 전략연산 및 트레이더를 시작하였습니다.'
        if self.dict_set['코인알림소리']: self.soundQ.put(text)
        self.teleQ.put(text)
        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 트레이더 시작'))

    def CheckError(self, ret):
        if ret.__class__ == dict and list(ret)[0] == 'error':
            self.windowQ.put((ui_num['시스템로그'], f"오류 알림 - {ret['error']['name']} : {ret['error']['message']}"))
            return False
        return True

    def Scheduler1(self):
        self.cstgQ.put(('잔고목록', self.dict_jg.copy()))
        if not self.dict_set['코인모의투자']: self.CheckChegeol()

    def Scheduler2(self):
        inthms = int(str_hms(now_utc()))
        if self.dict_set['코인타임프레임'] and inthms < self.dict_set['코인전략종료시간']:
            self.OrderTimeControl()
        if self.dict_set['코인잔고청산'] and not self.dict_bool['코인잔고청산'] and self.jgcs_time < inthms < self.jgcs_time + 10:
            self.JangoCheongsan('자동')
        self.UpdateTotaljango()

    @error_decorator
    def CheckOrder(self, data):
        if len(data) == 6:
            주문구분, 종목코드, 주문가격, 주문수량, 시그널시간, 잔고청산 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 주문가격, 주문수량, 시그널시간, 잔고청산, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.dict_jg
        매수주문중 = 종목코드 in self.dict_order['매수']
        매도주문중 = 종목코드 in self.dict_order['매도']

        주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 잔고청산:
            if 잔고없음 or 매도주문중:
                주문취소 = True
        elif self.dict_bool['코인잔고청산']:
            주문취소 = True
        elif 주문구분 == '매수':
            inthmsutc = int(str_hms(now_utc()))
            거래횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목코드]))
            손절횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목코드 and v['수익률'] < 0]))
            if self.dict_set['코인매수금지거래횟수'] and self.dict_set['코인매수금지거래횟수값'] <= 거래횟수:
                주문취소 = True
            elif self.dict_set['코인매수금지손절횟수'] and self.dict_set['코인매수금지손절횟수값'] <= 손절횟수:
                주문취소 = True
            elif 잔고없음 and inthmsutc < self.dict_set['코인전략종료시간'] and len(self.dict_jg) >= self.dict_set['코인최대매수종목수']:
                주문취소 = True
            elif self.dict_set['코인매수금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
            elif self.dict_set['코인매수금지손절간격'] and 현재시간 < self.dict_info[종목코드]['손절거래시간']:
                주문취소 = True
            elif not 잔고없음 and self.dict_jg[종목코드]['분할매수횟수'] >= self.dict_set['코인매수분할횟수']:
                주문취소 = True
            elif self.dict_intg['추정예수금'] < 주문수량 * 주문가격:
                if 현재시간 > self.dict_info[종목코드]['시드부족시간']:
                    self.CreateOrder('시드부족', 종목코드, 주문가격, 주문수량, str_hmsf(now_utc()), 시그널시간, 잔고청산, 0, None)
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
            if 주문구분 == '매수취소' and not 매수주문중:
                주문취소 = True
            elif 주문구분 == '매도취소' and not 매도주문중:
                주문취소 = True

        if 주문취소:
            if '취소' not in 주문구분:
                self.cstgQ.put((f'{주문구분}취소', 종목코드))
        else:
            if 주문수량 > 0:
                if 잔고청산: self.cstgQ.put((f'{주문구분}주문', 종목코드))
                self.CreateOrder(주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 잔고청산, 0, 수동주문유형)
            else:
                if 주문구분 == '매수':
                    if self.dict_set['코인매도취소매수시그널'] and 매도주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == '매도':
                    if self.dict_set['코인매수취소매도시그널'] and 매수주문중: self.CancelOrder(종목코드, 주문구분)
                self.cstgQ.put((f'{주문구분}취소', 종목코드))

    def CreateOrder(self, 주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 잔고청산, 정정횟수, 수동주문유형):
        if 주문구분 == '매수' and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['코인매수주문구분']:
                주문가격 = round(주문가격 + GetUpbitHogaunit(주문가격) * self.dict_set['코인매수지정가호가번호'], 8)
        elif 주문구분 == '매도' and 정정횟수 == 0:
            if 수동주문유형 is None and '지정가' in self.dict_set['코인매도주문구분']:
                주문가격 = round(주문가격 + GetUpbitHogaunit(주문가격) * self.dict_set['코인매도지정가호가번호'], 8)

        if 주문수량 * 주문가격 < 5000:
            self.windowQ.put((ui_num['시스템로그'], f'오류 알림 - 주문금액이 5천원미만입니다.'))
            self.cstgQ.put((f'{주문구분}취소', 종목코드))
            return

        if self.dict_set['코인모의투자'] or 주문구분 == '시드부족':
            self.OrderTimeLog(시그널시간)
            if 주문구분 == '시드부족':
                self.UpdateChejanData(주문구분, 종목코드, 주문수량, 0, 주문수량, 주문가격, 0, '')
            else:
                self.UpdateChejanData(주문구분, 종목코드, 주문수량, 주문수량, 0, 주문가격, 주문가격, '')
        else:
            data = (주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 잔고청산, 정정횟수, 수동주문유형)
            self.SendOrder(data)

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.windowQ.put((ui_num['타임로그'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.'))

    def SendOrder(self, data):
        curr_time = now()
        if curr_time < self.order_time:
            next_time = (self.order_time - curr_time).total_seconds()
            QTimer.singleShot(int(next_time * 1000), lambda: self.SendOrder(data))
            return

        주문구분, 종목코드, 주문가격, 주문수량, 주문번호, 시그널시간, 잔고청산, 정정횟수, 수동주문유형 = data
        self.OrderTimeLog(시그널시간)
        if self.upbit is not None:
            if 주문구분 == '매수':
                ret = None
                if 수동주문유형 == '시장가' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '시장가'):
                    ret = self.upbit.buy_market_order(종목코드, int(주문가격 * 주문수량))
                elif 수동주문유형 == '지정가' or (수동주문유형 is None and self.dict_set['코인매수주문구분'] == '지정가'):
                    ret = self.upbit.buy_limit_order(종목코드, 주문가격, 주문수량)

                if ret is not None:
                    if self.CheckError(ret):
                        dt = self.GetIndex()
                        self.dict_intg['추정예수금'] -= 주문수량 * 주문가격
                        self.dict_order[주문구분][종목코드] = [ret['uuid'], timedelta_sec(self.dict_set['코인매수취소시간초']), 정정횟수, 주문가격, GetUpbitHogaunit(주문가격)]
                        self.UpdateChegeollist(dt, 종목코드, f'{주문구분} 접수', 주문수량, 0, 주문수량, 0, dt[:14], 주문가격, ret['uuid'])
                        self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}접수] {종목코드} | {주문가격} | {주문수량}'))
                else:
                    self.cstgQ.put(('매수취소', 종목코드))
                    self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [주문실패] {종목코드} | {주문가격} | {주문수량}'))

            elif 주문구분 == '매도':
                ret = None
                if 수동주문유형 == '시장가' or self.dict_set['코인매도주문구분'] == '시장가' or 잔고청산:
                    ret = self.upbit.sell_market_order(종목코드, 주문수량)
                elif 수동주문유형 == '지정가' or self.dict_set['코인매도주문구분'] == '지정가':
                    ret = self.upbit.sell_limit_order(종목코드, 주문가격, 주문수량)

                if ret is not None:
                    if self.CheckError(ret):
                        dt = self.GetIndex()
                        self.dict_order[주문구분][종목코드] = [ret['uuid'], timedelta_sec(self.dict_set['코인매도취소시간초']), 정정횟수, 주문가격, GetUpbitHogaunit(주문가격)]
                        self.UpdateChegeollist(dt, 종목코드, f'{주문구분} 접수', 주문수량, 0, 주문수량, 0, dt[:14], 주문가격, ret['uuid'])
                        self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}접수] {종목코드} | {주문가격} | {주문수량}'))
                else:
                    self.cstgQ.put(('매도취소', 종목코드))
                    self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [주문실패] {종목코드} | {주문가격} | {주문수량} | {주문구분}'))

            elif 주문구분 in ('매수취소', '매도취소'):
                ret = self.upbit.cancel_order(주문번호)
                if ret is not None:
                    if self.CheckError(ret):
                        self.dict_order[주문구분][종목코드] = ret['uuid']
                else:
                    self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [주문 실패] {종목코드} | {주문가격} | {주문수량} | {주문구분}'))

        self.order_time = timedelta_sec(0.3)
        self.creceivQ.put(('주문목록', self.GetOrderCodeList()))

    def GetOrderCodeList(self):
        return tuple(self.dict_order['매수']) + tuple(self.dict_order['매도'])

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '잔고갱신':
            self.UpdateJango(data)
        elif gubun == '주문확인':
            code, c = data
            self.dict_curc[code] = c
            self.OrderTimeControl(code)
        if gubun == '관심진입':
            if data in self.dict_order['매도']:
                self.CancelOrder(data, '매도')
        elif gubun == '관심이탈':
            if data in self.dict_order['매수']:
                self.CancelOrder(data, '매수')
        elif gubun == '설정변경':
            self.dict_set = data

    def UpdateString(self, data):
        if data == '체결목록':
            df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
            self.teleQ.put(df_cj) if len(df_cj) > 0 else self.teleQ.put('현재는 업비트 체결목록이 없습니다.')
        elif data == '거래목록':
            df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
            self.teleQ.put(df_td) if len(df_td) > 0 else self.teleQ.put('현재는 업비트 거래목록이 없습니다.')
        elif data == '잔고평가':
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.teleQ.put(df_jg) if len(df_jg) > 0 else self.teleQ.put('현재는 업비트 잔고목록이 없습니다.')
        elif data == '잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로세스종료':
            self.SysExit()

    def CheckChegeol(self):
        order_info_list = []
        for gubun in self.dict_order:
            for code, orders in self.dict_order[gubun].items():
                order_info = self.GetOrderInfo(code, orders[0])
                if order_info is not None:
                    order_info_list.append([gubun] + order_info)
                qtest_qwait(0.1)

        if order_info_list:
            for 주문구분, 종목코드, 주문수량, 총체결수량, 미체결수량, 체결가격, 주문가격, 주문번호 in order_info_list:
                self.UpdateChejanData(주문구분, 종목코드, 주문수량, 총체결수량, 미체결수량, 체결가격, 주문가격, 주문번호)

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
                if 주문번호 not in self.dict_order_cc:
                    order_info = [종목코드, 주문수량, 총체결수량, 미체결수량, 체결가격, 주문가격, 주문번호]
                else:
                    체결수량 = round(총체결수량 - self.dict_order_cc[주문번호], 8)
                    if 체결수량 > 0:
                        order_info = [종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 주문번호]

                self.dict_order_cc[주문번호] = 총체결수량
                if 미체결수량 == 0 and 주문번호 in self.dict_order_cc:
                    del self.dict_order_cc[주문번호]

        return order_info

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            # ['종목명', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
            if 현재가 != self.dict_jg[종목코드]['현재가']:
                매입금액 = self.dict_jg[종목코드]['매입금액']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                평가금액, 평가손익, 수익률 = GetUpbitPgSgSp(매입금액, 보유수량 * 현재가)
                self.dict_jg[종목코드].update({
                    '현재가': 현재가,
                    '수익률': 수익률,
                    '평가손익': 평가손익,
                    '평가금액': 평가금액
                })
        except:
            pass

    def OrderTimeControl(self, code_=None):
        cancel_list = []
        modify_list = []

        for gubun in self.dict_order:
            if gubun in ('매수', '매도'):
                for code in self.dict_order[gubun]:
                    if code_ is None or code == code_:
                        order_info = self.dict_order[gubun][code]
                        if gubun == '매수':
                            if self.dict_set['코인매수취소시간'] and now() > order_info[1]:
                                cancel_list.append((code, gubun))
                        else:
                            if self.dict_set['코인매도취소시간'] and now() > order_info[1]:
                                cancel_list.append((code, gubun))
                        if gubun == '매수':
                            if order_info[2] < self.dict_set['코인매수정정횟수'] and code in self.dict_curc and \
                                    self.dict_curc[code] >= order_info[3] + order_info[4] * self.dict_set['코인매수정정호가차이']:
                                modify_list.append((code, gubun))
                        else:
                            if order_info[2] < self.dict_set['코인매도정정횟수'] and code in self.dict_curc and \
                                    self.dict_curc[code] <= order_info[3] - order_info[4] * self.dict_set['코인매도정정호가차이']:
                                modify_list.append((code, gubun))

        if cancel_list:
            for code, gubun in cancel_list:
                self.CancelOrder(code, gubun)
        if modify_list:
            for code, gubun in modify_list:
                self.ModifyOrder(code, gubun)

    def GetChejanLastValue(self, code, gubun):
        return [v for v in self.dict_cj.values() if v['종목명'] == code and (v['주문구분'] == gubun or v['주문구분'] == f'{gubun} 접수')][-1]

    def CancelOrder(self, 종목코드, 주문구분):
        last_value = self.GetChejanLastValue(종목코드, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
            if 미체결수량 > 0:
                주문번호, 주문가격 = last_value['주문번호'], last_value['주문가격']
                self.CreateOrder(f'{주문구분}취소', 종목코드, 주문가격, 미체결수량, 주문번호, now(), False, 0, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        last_value = self.GetChejanLastValue(종목코드, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
            if 미체결수량 > 0:
                if 주문구분 == '매수':
                    정정가격 = self.dict_curc[종목코드] - self.dict_order[주문구분][종목코드][4] * self.dict_set['코인매수정정호가']
                else:
                    정정가격 = self.dict_curc[종목코드] + self.dict_order[주문구분][종목코드][4] * self.dict_set['코인매도정정호가']

                현재시간 = now()
                정정횟수 = self.dict_order[주문구분][종목코드][2] + 1
                주문번호, 주문가격 = last_value['주문번호'], last_value['주문가격']
                self.CreateOrder(f'{주문구분}취소', 종목코드, 주문가격, 미체결수량, 주문번호, 현재시간, False, 0, None)
                self.CreateOrder(주문구분, 종목코드, 정정가격, 미체결수량, '', 현재시간, False, 정정횟수, None)

    def JangoCheongsan(self, gubun):
        for 주문구분 in self.dict_order:
            if 주문구분 in ('매수', '매도'):
                for 종목코드 in self.dict_order[주문구분]:
                    self.CancelOrder(종목코드, 주문구분)

        if self.dict_jg:
            if gubun == '수동':
                self.teleQ.put('코인 잔고청산 주문을 전송합니다.')
            for 종목코드 in self.dict_jg.copy():
                현재가 = self.dict_jg[종목코드]['현재가']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                if self.dict_set['코인모의투자']:
                    self.UpdateChejanData('매도', 종목코드, 보유수량, 보유수량, 0, 현재가, 현재가, '')
                else:
                    self.CheckOrder(('매도', 종목코드, 현재가, 보유수량, now(), True))
            if self.dict_set['코인알림소리']:
                self.soundQ.put('코인 잔고청산 주문을 전송하였습니다.')
            self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 코인 잔고청산 주문 완료'))
        elif gubun == '수동':
            self.teleQ.put('현재는 코인 보유종목이 없습니다.')
        self.dict_bool['코인잔고청산'] = True

    def SysExit(self):
        qtest_qwait(5)
        self.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 트레이더 종료'))

    def GetIndex(self):
        index = str_ymdhmsf(now_utc())
        if index in self.dict_cj:
            while index in self.dict_cj:
                index = str(int(index) + 1)
        return index

    @error_decorator
    def UpdateChejanData(self, 주문구분, 종목코드, 주문수량, 체결수량, 미체결수량, 체결가격, 주문가격, 주문번호):
        index = self.GetIndex()

        if 주문구분 in ('매수', '매도'):
            if 주문구분 == '매수':
                # ['종목명', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                if 종목코드 in self.dict_jg:
                    보유수량 = round(self.dict_jg[종목코드]['보유수량'] + 체결수량, 8)
                    매입금액 = int(self.dict_jg[종목코드]['매입금액'] + 체결수량 * 체결가격)
                    매수가 = round(매입금액 / 보유수량, 4)
                    평가금액, 수익금, 수익률 = GetUpbitPgSgSp(매입금액, 보유수량 * 체결가격)
                    self.dict_jg[종목코드].update({
                        '매수가': 매수가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '매수시간': index[:14]
                    })
                else:
                    매입금액 = int(체결수량 * 체결가격)
                    평가금액, 수익금, 수익률 = GetUpbitPgSgSp(매입금액, 체결수량 * 체결가격)
                    self.dict_jg[종목코드] = {
                        '종목명': 종목코드,
                        '매수가': 체결가격,
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
                    self.dict_jg[종목코드]['분할매수횟수'] += 1
                    if 종목코드 in self.dict_order[주문구분]:
                        del self.dict_order[주문구분][종목코드]

            else:
                if 종목코드 not in self.dict_jg: return
                매수가 = self.dict_jg[종목코드]['매수가']
                보유수량 = round(self.dict_jg[종목코드]['보유수량'] - 체결수량, 8)
                if 보유수량 != 0:
                    매입금액 = int(매수가 * 보유수량)
                    평가금액, 수익금, 수익률 = GetUpbitPgSgSp(매입금액, 보유수량 * 체결가격)
                    # ['종목명', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
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
                    if 종목코드 in self.dict_order[주문구분]:
                        del self.dict_order[주문구분][종목코드]

                매입금액 = 매수가 * 체결수량
                평가금액, 수익금, 수익률 = GetUpbitPgSgSp(매입금액, 체결수량 * 체결가격)
                if -100 < 수익률 < 100: self.UpdateTradelist(index, 종목코드, 매입금액, 평가금액, 체결수량, 수익률, 수익금, index[:14])
                if 수익률 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['코인매수금지손절간격초'])

            self.dict_jg = dict(sorted(self.dict_jg.items(), key=lambda x: x[1]['매입금액'], reverse=True))

            if 미체결수량 == 0: self.cstgQ.put((주문구분 + '완료', 종목코드))
            self.UpdateChegeollist(index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, index[:14], 주문가격, 주문번호)

            if 주문구분 == '매수':
                self.dict_intg['예수금'] -= 체결수량 * 체결가격
                if self.dict_set['코인모의투자']:
                    self.dict_intg['추정예수금'] -= 체결수량 * 체결가격
            else:
                self.dict_intg['예수금'] += 매입금액 + 수익금
                self.dict_intg['추정예수금'] += 매입금액 + 수익금

            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.queryQ.put(('거래디비', df_jg, 'c_jangolist', 'replace'))
            if self.dict_set['코인알림소리']: self.soundQ.put(f"{종목코드} {주문구분}하였습니다.")
            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}체결] {종목코드} | {체결가격} | {체결수량}'))

        elif 주문구분 == '시드부족':
            self.UpdateChegeollist(index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, index[:14], 주문가격, 주문번호)

        elif 주문구분 in ('매수취소', '매도취소'):
            if 주문구분 == '매수취소':
                self.dict_intg['추정예수금'] += 주문수량 * 주문가격
                if 종목코드 in self.dict_order[주문구분]:
                    del self.dict_order[주문구분][종목코드]
            elif 종목코드 in self.dict_order[주문구분]:
                del self.dict_order[주문구분][종목코드]

            self.cstgQ.put((주문구분, 종목코드))
            self.UpdateChegeollist(index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, index[:14], 주문가격, 주문번호)

            if self.dict_set['코인알림소리']: self.soundQ.put(f"{종목코드} {주문구분}하였습니다.")
            self.windowQ.put((ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문구분}] {종목코드} | {주문가격} | {주문수량}'))

        self.creceivQ.put(('잔고목록', tuple(self.dict_jg)))
        self.creceivQ.put(('주문목록', self.GetOrderCodeList()))

    def UpdateTradelist(self, index, 종목코드, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간):
        # ['종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
        self.dict_td[index] = {
            '종목명': 종목코드,
            '매수금액': 매입금액,
            '매도금액': 평가금액,
            '주문수량': 체결수량,
            '수익률': 수익률,
            '수익금': 수익금,
            '체결시간': 주문시간
        }
        df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
        self.windowQ.put((ui_num['C거래목록'], df_td[::-1]))
        df = pd.DataFrame([[종목코드, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간]], columns=columns_td, index=[index])
        self.queryQ.put(('거래디비', df, 'c_tradelist', 'append'))
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        td_values = self.dict_td.values()
        거래횟수 = len(set([(v['종목명'], v['체결시간']) for v in td_values]))
        총매수금액 = sum([v['매수금액'] for v in td_values])
        총매도금액 = sum([v['매도금액'] for v in td_values])
        총수익금액 = sum([v['수익금'] for v in td_values if v['수익금'] >= 0])
        총손실금액 = sum([v['수익금'] for v in td_values if v['수익금'] < 0])
        수익금합계 = sum([v['수익금'] for v in td_values])
        수익률 = round(수익금합계 / self.dict_intg['추정예탁자산'] * 100, 2)

        # ['거래횟수', '총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']
        self.dict_tt[self.str_today] = {
            '거래횟수': 거래횟수,
            '총매수금액': 총매수금액,
            '총매도금액': 총매도금액,
            '총수익금액': 총수익금액,
            '총손실금액': 총손실금액,
            '수익률': 수익률,
            '수익금합계': 수익금합계
        }
        df_tt = pd.DataFrame.from_dict(self.dict_tt, orient='index')
        delete_query = f"DELETE FROM c_totaltradelist WHERE `index` = '{self.str_today}'"
        self.queryQ.put(('거래디비', delete_query))
        self.queryQ.put(('거래디비', df_tt, 'c_totaltradelist', 'append'))
        self.windowQ.put((ui_num['C실현손익'], df_tt))

        if not first:
            self.teleQ.put(f'총매수금액 {총매수금액:,.0f}, 총매도금액 {총매도금액:,.0f}, 수익 {총수익금액:,.0f}, 손실 {총손실금액:,.0f}, 수익금합계 {수익금합계:,.0f}')

        if self.dict_set['스톰라이브']:
            수익률 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익률, 수익금합계]
            self.liveQ.put(('코인', data_list))

    def UpdateChegeollist(self, index, 종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호):
        # ['종목명', '주문구분', '주문수량', '체결수량', '미체결수량', '체결가', '체결시간', '주문가격', '주문번호']
        self.dict_info[종목코드]['최종거래시간'] = timedelta_sec(self.dict_set['코인매수금지간격초'])
        self.dict_cj[index] = {
            '종목명': 종목코드,
            '주문구분': 주문구분,
            '주문수량': 주문수량,
            '체결수량': 체결수량,
            '미체결수량': 미체결수량,
            '체결가': 체결가격,
            '체결시간': 체결시간,
            '주문가격': 주문가격,
            '주문번호': 주문번호
        }
        self.dict_cj = dict(sorted(self.dict_cj.items(), key=lambda x: x[0]))
        df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
        self.windowQ.put((ui_num['C체결목록'], df_cj[::-1]))
        df = pd.DataFrame([[종목코드, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]], columns=columns_cj, index=[index])
        self.queryQ.put(('거래디비', df, 'c_chegeollist', 'append'))

    def UpdateTotaljango(self):
        # ['추정예탁자산', '추정예수금', '보유종목수', '수익률', '총평가손익', '총매입금액', '총평가금액']
        if self.dict_jg:
            jg_values = self.dict_jg.values()
            총평가손익 = sum([v['평가손익'] for v in jg_values])
            총매입금액 = sum([v['매입금액'] for v in jg_values])
            총평가금액 = sum([v['평가금액'] for v in jg_values])
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

        거래수익금합계 = sum([v['수익금'] for v in self.dict_td.values()])
        당일평가손익 = 총평가손익 + 거래수익금합계
        if self.dict_set['코인손실중지']:
            기준손실금 = self.dict_intg['추정예탁자산'] * self.dict_set['코인손실중지수익률'] / 100
            if 기준손실금 < -당일평가손익: self.StrategyStop()
        if self.dict_set['코인수익중지']:
            기준수익금 = self.dict_intg['추정예탁자산'] * self.dict_set['코인수익중지수익률'] / 100
            if 기준수익금 < 당일평가손익: self.StrategyStop()

        if self.dict_set['코인투자금고정']:
            종목당투자금 = int(self.dict_set['코인투자금'] * 1_000_000)
        else:
            종목당투자금 = int(self.dict_intg['추정예탁자산'] * 0.98 / self.dict_set['코인최대매수종목수'])

        if self.dict_intg['종목당투자금'] != 종목당투자금:
            self.dict_intg['종목당투자금'] = 종목당투자금
            self.cstgQ.put(('종목당투자금', self.dict_intg['종목당투자금']))

        if self.dict_jg:
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
        else:
            df_jg = pd.DataFrame(columns=columns_jg)
        df_tj = pd.DataFrame.from_dict(self.dict_tj, orient='index')
        self.windowQ.put((ui_num['C잔고목록'], df_jg))
        self.windowQ.put((ui_num['C잔고평가'], df_tj))

    def StrategyStop(self):
        self.cstgQ.put('매수전략중지')
        self.JangoCheongsan('수동')
