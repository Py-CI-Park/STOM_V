
import os
import sys
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utility.setting_base import ui_num, columns_cj, DB_TRADELIST, columns_tdf, columns_jgf
from utility.static import now, timedelta_sec, GetFutureLongPgSgSp, GetFutureShortPgSgSp, str_ymd, now_cme, \
    str_ymdhms, str_hms, str_ymdhmsf, str_hmsf, dt_hms, qtest_qwait, set_builtin_print, error_decorator


class Updater(QThread):
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal(tuple)
    signal3 = pyqtSignal(str)

    def __init__(self, straderQ):
        super().__init__()
        self.straderQ = straderQ

    def run(self):
        while True:
            data = self.straderQ.get()
            if data.__class__ == tuple:
                if len(data) in (7, 8):
                    self.signal1.emit(data)
                else:
                    self.signal2.emit(data)
            elif data.__class__ == str:
                self.signal3.emit(data)


class FutureTrader:
    def __init__(self, qlist, dict_set):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ
                0            1             2            3
        """
        app = QApplication(sys.argv)

        self.mgzservQ    = qlist[0]
        self.sagentQ     = qlist[1]
        self.straderQ    = qlist[2]
        self.sstgQ       = qlist[3]
        self.dict_set    = dict_set

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
        self.dict_intg = {
            '예수금': 0,
            '추정예수금': 0,
            '예탁자산': 0,
            '추정예탁자산': 0
        }
        self.dict_bool = {
            '주식잔고청산': False
        }
        self.거래구분 = {
            '시장가': '1',
            '지정가': '2'
        }
        self.주문유형 = {
            '시드부족': 0,
            'SELL_LONG': 1,
            'BUY_SHORT': 1,
            'BUY_LONG': 2,
            'SELL_SHORT': 2,
            'SELL_LONG_CANCEL': 3,
            'BUY_SHORT_CANCEL': 3,
            'BUY_LONG_CANCEL': 4,
            'SELL_SHORT_CANCEL': 4,
            'SELL_LONG_MODIFY': 5,
            'BUY_SHORT_MODIFY': 5,
            'BUY_LONG_MODIFY': 6,
            'SELL_SHORT_MODIFY': 6
        }

        self.jgcs_time = self.get_jgcs_time()
        self.str_today = str_ymd(now_cme())

        self.LoadDatabase()

        self.qtimer1 = QTimer()
        self.qtimer1.setInterval(500)
        self.qtimer1.timeout.connect(self.Scheduler1)
        self.qtimer1.start()

        self.qtimer2 = QTimer()
        self.qtimer2.setInterval(1 * 1000)
        self.qtimer2.timeout.connect(self.Scheduler2)
        self.qtimer2.start()

        self.updater = Updater(self.straderQ)
        self.updater.signal1.connect(self.CheckOrder)
        self.updater.signal2.connect(self.UpdateTuple)
        self.updater.signal3.connect(self.UpdateString)
        self.updater.start()

        set_builtin_print(True, self.mgzservQ)
        app.exec_()

    def get_jgcs_time(self):
        return int(str_hms(timedelta_sec(-120, dt_hms(str(self.dict_set['주식전략종료시간'])))))

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        df_cj = pd.read_sql(f"SELECT * FROM f_chegeollist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        df_td = pd.read_sql(f"SELECT * FROM f_tradelist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        if len(df_cj) > 0:
            self.dict_cj = df_cj.to_dict('index')
            self.mgzservQ.put(('window', (ui_num['S체결목록'], df_cj[::-1])))
        if len(df_td) > 0:
            self.dict_td = df_td.to_dict('index')
            self.mgzservQ.put(('window', (ui_num['S거래목록'], df_td[::-1])))
            self.UpdateTotaltradelist(first=True)
        if self.dict_set['주식모의투자']:
            df_jg = pd.read_sql(f'SELECT * FROM f_jangolist', con).set_index('index')
            if len(df_jg) > 0:
                self.dict_jg = df_jg.to_dict('index')
                self.sagentQ.put(('잔고목록', tuple(self.dict_jg)))
        con.close()
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 데이터베이스 정보 불러오기 완료')))
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 트레이더 시작')))

    def Scheduler1(self):
        self.sstgQ.put(('잔고목록', self.dict_jg.copy()))

    def Scheduler2(self):
        inthms = int(str_hms(now_cme()))
        if self.dict_set['주식타임프레임'] and inthms < self.dict_set['주식전략종료시간']:
            self.OrderTimeControl()
        if self.dict_set['주식잔고청산'] and not self.dict_bool['주식잔고청산'] and self.jgcs_time < inthms:
            self.JangoCheongsan('자동')
        self.UpdateTotaljango()

    @error_decorator
    def CheckOrder(self, data):
        if len(data) == 7:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.dict_jg
        롱매수주문중 = 종목코드 in self.dict_order['BUY_LONG']
        숏매수주문중 = 종목코드 in self.dict_order['SELL_SHORT']
        롱매도주문중 = 종목코드 in self.dict_order['SELL_LONG']
        숏매도주문중 = 종목코드 in self.dict_order['BUY_SHORT']
        jg_data = self.dict_jg.get(종목코드)
        포지션 = jg_data['포지션'] if jg_data else None

        원주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 잔고청산:
            if 잔고없음 or (주문구분 == 'SELL_LONG' and 롱매도주문중) or (주문구분 == 'BUY_SHORT' and 숏매도주문중):
                주문취소 = True
        elif self.dict_bool['주식잔고청산']:
            주문취소 = True
        elif 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
            inthms = int(str_hms(now_cme()))
            거래횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목명]))
            손절횟수 = len(set([v['체결시간'] for v in self.dict_td.values() if v['종목명'] == 종목명 and v['수익률'] < 0]))
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
                    self.CreateOrder('시드부족', 종목코드, 종목명, 주문가격, 주문수량, str_hmsf(now_cme()), 시그널시간, 잔고청산, None)
                    self.dict_info[종목코드]['시드부족시간'] = timedelta_sec(180)
                주문취소 = True
            elif 포지션 == 'LONG' and 'SHORT' in 주문구분:
                주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분:
                주문취소 = True
            elif 주문구분 == 'BUY_LONG' and 롱매수주문중:
                주문취소 = True
            elif 주문구분 == 'SELL_SHORT' and 숏매수주문중:
                주문취소 = True
        elif 주문구분 in ('SELL_LONG', 'BUY_SHORT'):
            if self.dict_set['주식매도금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
            elif 포지션 == 'LONG' and 'SHORT' in 주문구분:
                주문취소 = True
            elif 포지션 == 'SHORT' and 'LONG' in 주문구분:
                주문취소 = True
            elif 주문구분 == 'SELL_LONG' and 롱매도주문중:
                주문취소 = True
            elif 주문구분 == 'BUY_SHORT' and 숏매도주문중:
                주문취소 = True
        elif 'CANCEL' in 주문구분:
            if 주문구분 == 'BUY_LONG_CANCEL' and not 롱매수주문중:
                주문취소 = True
            elif 주문구분 == 'SELL_SHORT_CANCEL' and not 숏매수주문중:
                주문취소 = True
            elif 주문구분 == 'SELL_LONG_CANCEL' and not 롱매도주문중:
                주문취소 = True
            elif 주문구분 == 'BUY_SHORT_CANCEL' and not 숏매도주문중:
                주문취소 = True

        if 주문취소:
            if 'CANCEL' not in 주문구분:
                self.PutOrderComplete(f'{주문구분}_CANCEL', 종목코드)
        else:
            if 주문수량 > 0:
                if 잔고청산: self.PutOrderComplete(f'{주문구분}_MANUAL', 종목코드)
                self.CreateOrder(주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 수동주문유형)
            else:
                if 주문구분 == 'BUY_LONG':
                    if self.dict_set['주식매도취소매수시그널'] and 롱매도주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'SELL_SHORT':
                    if self.dict_set['주식매도취소매수시그널'] and 숏매도주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'SELL_LONG':
                    if self.dict_set['주식매수취소매도시그널'] and 롱매수주문중: self.CancelOrder(종목코드, 주문구분)
                elif 주문구분 == 'BUY_SHORT':
                    if self.dict_set['주식매수취소매도시그널'] and 숏매수주문중: self.CancelOrder(종목코드, 주문구분)
                self.PutOrderComplete(f'{주문구분}_CANCEL', 종목코드)

    def PutOrderComplete(self, cmsg, code):
        self.sstgQ.put((cmsg, code))

    def CreateOrder(self, 주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 수동주문유형):
        주문유형 = self.주문유형[주문구분]

        if 잔고청산:
            거래구분 = self.거래구분['시장가']
        elif 'BUY_LONG' in 주문구분 or 'BUY_SHORT' in 주문구분:
            거래구분 = self.거래구분[self.dict_set['주식매수주문구분']] if 수동주문유형 is None else self.거래구분[수동주문유형]
        else:
            거래구분 = self.거래구분[self.dict_set['주식매도주문구분']] if 수동주문유형 is None else self.거래구분[수동주문유형]

        if 주문구분 in ('BUY_LONG', 'SELL_SHORT'):
            if 수동주문유형 is None and '지정가' in self.dict_set['주식매수주문구분']:
                gap = self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매수지정가호가번호']
                주문가격 = round((주문가격 + gap) if 주문구분 == 'BUY_LONG' else (주문가격 - gap), self.dict_info[종목코드]['소숫점자리수'])
            if self.dict_set['주식매수주문구분'] == '시장가' and not (self.dict_set['주식모의투자'] or 주문구분 == '시드부족'):
                주문가격 = 0
        elif 주문구분 in ('SELL_LONG', 'BUY_SHORT'):
            if 수동주문유형 is None and '지정가' in self.dict_set['주식매도주문구분']:
                gap = self.dict_info[종목코드]['호가단위'] * self.dict_set['주식매도지정가호가번호']
                주문가격 = round((주문가격 + gap) if 주문구분 == 'SELL_LONG' else (주문가격 - gap), self.dict_info[종목코드]['소숫점자리수'])
            if self.dict_set['주식매도주문구분'] == '시장가' and not (self.dict_set['주식모의투자'] or 주문구분 == '시드부족'):
                주문가격 = 0

        self.dict_signal[종목코드] = 주문구분
        if self.dict_set['주식모의투자'] or 주문구분 == '시드부족':
            ct = str_ymdhms(now_cme())
            self.OrderTimeLog(시그널시간)
            if 주문구분 == '시드부족':
                data = (종목코드, 종목명, '시드부족', 주문구분, '매수', 주문수량, 0, 주문가격, ct, 원주문번호, 0, 0)
            else:
                주문구분 = '매수' if 주문구분 in ('BUY_LONG', 'SELL_SHORT') else '매도'
                data = (종목코드, 종목명, '체결', '체결', 주문구분, 주문수량, 0, 주문가격, ct, 원주문번호, 주문수량, 주문가격)
            self.UpdateChejanData(data)
        else:
            data = [주문구분, '', '', 주문유형, 종목코드, 주문수량, 주문가격, '', 거래구분, 원주문번호, 종목명, 시그널시간]
            self.sagentQ.put(data)

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.mgzservQ.put(('window', (ui_num['타임로그'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.')))

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '체잔통보':
            self.UpdateChejanData(data)
        elif gubun == '잔고갱신':
            self.UpdateJango(data)
        elif gubun == '주문전송':
            code, gubun = data
            self.dict_signal[code] = gubun
        elif gubun == '주문확인':
            code, c = data
            self.dict_curc[code] = c
            self.OrderTimeControl(code)
        elif gubun == '증거금부족':
            gubun = self.dict_signal[data]
            self.PutOrderComplete(f'{gubun}_CANCEL', data)
        elif gubun == '종목정보':
            self.dict_info = data
            dummy_time = timedelta_sec(-3600, now_cme())
            for code in self.dict_info:
                self.dict_info[code]['시드부족시간'] = dummy_time
                self.dict_info[code]['최종거래시간'] = dummy_time
                self.dict_info[code]['손절거래시간'] = dummy_time
        elif gubun == '잔고조회':
            self.UpdateYesugm(data)
        elif gubun == '설정변경':
            self.dict_set  = data
            self.jgcs_time = self.get_jgcs_time()

    def UpdateString(self, data):
        if data == '체결목록':
            df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
            self.mgzservQ.put(('tele', df_cj)) if len(df_cj) > 0 else self.mgzservQ.put(('tele', '현재는 해선 체결목록이 없습니다.'))
        elif data == '거래목록':
            df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
            self.mgzservQ.put(('tele', df_td)) if len(df_td) > 0 else self.mgzservQ.put(('tele', '현재는 해선 거래목록이 없습니다.'))
        elif data == '잔고평가':
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.mgzservQ.put(('tele', df_jg)) if len(df_jg) > 0 else self.mgzservQ.put(('tele', '현재는 해선 잔고목록이 없습니다.'))
        elif data == '잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로세스종료':
            self.SysExit()

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            # ['종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
            if 현재가 != self.dict_jg[종목코드]['현재가']:
                포지션 = self.dict_jg[종목코드]['포지션']
                매수가 = self.dict_jg[종목코드]['매수가']
                매입금액 = self.dict_jg[종목코드]['매입금액']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                평가금액 = 매입금액 + (현재가 - 매수가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
                if 포지션 == 'LONG':
                    평가금액, 평가손익, 수익률 = GetFutureLongPgSgSp(mini, 매입금액, 평가금액)
                else:
                    평가금액, 평가손익, 수익률 = GetFutureShortPgSgSp(mini, 매입금액, 평가금액)
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
            for code in self.dict_order[gubun]:
                if code_ is None or code == code_:
                    order_info = self.dict_order[gubun][code]
                    if gubun in ('BUY_LONG', 'SELL_SHORT'):
                        if self.dict_set['주식매수취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    else:
                        if self.dict_set['주식매도취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))

                    text = '주식매수' if gubun in ('BUY_LONG', 'SELL_SHORT') else '주식매도'
                    if gubun in ('BUY_LONG', 'BUY_SHORT'):
                        if order_info[1] < self.dict_set[f'{text}정정횟수'] and code in self.dict_curc and \
                                self.dict_curc[code] >= order_info[2] + self.dict_info[code]['호가단위'] * self.dict_set[f'{text}정정호가차이']:
                            modify_list.append((code, gubun))
                    else:
                        if order_info[1] < self.dict_set[f'{text}정정횟수'] and code in self.dict_curc and \
                                self.dict_curc[code] <= order_info[2] - self.dict_info[code]['호가단위'] * self.dict_set[f'{text}정정호가차이']:
                            modify_list.append((code, gubun))

        if cancel_list:
            for code, gubun in cancel_list:
                self.CancelOrder(code, gubun)
        if modify_list:
            for code, gubun in modify_list:
                self.ModifyOrder(code, gubun)

    def GetChejanLastValue(self, name, gubun):
        return [v for v in self.dict_cj.values() if v['종목명'] == name and (v['주문구분'] == gubun or v['주문구분'] == f'{gubun}_REG')][-1]

    def CancelOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        last_value = self.GetChejanLastValue(종목명, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
            if 미체결수량 > 0:
                현재시간 = now()
                주문번호 = last_value['주문번호']
                self.CreateOrder(f'{주문구분}_CANCEL', 종목코드, 종목명, 0, 미체결수량, 주문번호, 현재시간, False, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        last_value = self.GetChejanLastValue(종목명, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
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
                주문번호 = last_value['주문번호']
                self.CreateOrder(f'{주문구분}_MODIFY', 종목코드, 종목명, 정정가격, 미체결수량, 주문번호, 현재시간, False, None)

    def JangoCheongsan(self, gubun):
        for 주문구분 in self.dict_order:
            for 종목코드 in self.dict_order[주문구분]:
                self.CancelOrder(종목코드, 주문구분)

        if self.dict_jg:
            if gubun == '수동':
                self.mgzservQ.put(('tele', '해선 잔고청산 주문을 전송합니다.'))
            for 종목코드 in self.dict_jg.copy():
                포지션 = self.dict_jg[종목코드]['포지션']
                종목명 = self.dict_jg[종목코드]['종목명']
                현재가 = self.dict_jg[종목코드]['현재가']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                주문구분 = 'SELL_LONG' if 포지션 == 'LONG' else 'BUY_SHORT'
                if self.dict_set['주식모의투자']:
                    self.dict_signal[종목코드] = 주문구분
                    ct = str_ymdhms(now_cme())
                    data = (종목코드, 종목명, '체결', '체결', '매도', 보유수량, 0, 현재가, ct, '', 보유수량, 현재가)
                    self.UpdateChejanData(data)
                else:
                    self.CheckOrder((주문구분, 종목코드, 종목명, 현재가, 보유수량, now(), True))
            if self.dict_set['주식알림소리']:
                self.mgzservQ.put(('sound', '해선 잔고청산 주문을 전송하였습니다.'))
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'시스템 명령 실행 알림 - 해선 잔고청산 주문 완료')))
        elif gubun == '수동':
            self.mgzservQ.put(('tele', '현재는 해선 보유종목이 없습니다.'))
        self.dict_bool['주식잔고청산'] = True

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
            for index in self.dict_jg:
                yesugm = self.dict_jg[index]['보유수량'] * self.dict_info[index]['위탁증거금']
                self.dict_intg['예수금'] -= yesugm
            self.dict_intg['추정예수금'] = self.dict_intg['예수금']

    def SysExit(self):
        qtest_qwait(5)
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 트레이더 종료')))

    def GetIndex(self):
        index = str_ymdhmsf(now_cme())
        if index in self.dict_cj:
            while index in self.dict_cj:
                index = str(int(index) + 1)
        return index

    """
    gubun:1, 종목코드:NQU25, 주문상태:확인, 주문구분:정정, 매도수구분:매수, 주문수량:2, 미체결수량:2, 주문가격:23825.50, 주문번호:000000909010126, 주문시간:20250908072509, 체결수량:0, 체결가격:0.000000
    gubun:1, 종목코드:NQU25, 주문상태:확인, 주문구분:취소, 매도수구분:매수, 주문수량:2, 미체결수량:0, 주문가격:23825.50, 주문번호:000000909010135, 주문시간:20250908072509, 체결수량:0, 체결가격:0.000000
    gubun:0, 종목코드:NQU25, 주문상태:접수, 주문구분:신규, 매도수구분:매수, 주문수량:2, 미체결수량:2, 주문가격:23826.25, 주문번호:000000909010141, 주문시간:20250908072509, 체결수량:0, 체결가격:0.000000
    gubun:1, 종목코드:NQU25, 주문상태:확인, 주문구분:취소, 매도수구분:매수, 주문수량:2, 미체결수량:0, 주문가격:23826.25, 주문번호:000000909010151, 주문시간:20250908072509, 체결수량:0, 체결가격:0.000000
    gubun:0, 종목코드:NQU25, 주문상태:접수, 주문구분:신규, 매도수구분:매수, 주문수량:2, 미체결수량:2, 주문가격:23827.50, 주문번호:000000909010177, 주문시간:20250908072509, 체결수량:0, 체결가격:0.000000
    gubun:1, 종목코드:NQU25, 주문상태:체결, 주문구분:체결, 매도수구분:매수, 주문수량:2, 미체결수량:0, 주문가격:23827.50, 주문번호:000000909010177, 주문시간:20250908072509, 체결수량:2, 체결가격:23827.500000
    gubun:0, 종목코드:NQU25, 주문상태:접수, 주문구분:신규, 매도수구분:매도, 주문수량:2, 미체결수량:2, 주문가격:23828.75, 주문번호:000000909010238, 주문시간:20250908072509, 체결수량:2, 체결가격:23827.500000
    gubun:1, 종목코드:NQU25, 주문상태:체결, 주문구분:체결, 매도수구분:매도, 주문수량:2, 미체결수량:0, 주문가격:23828.75, 주문번호:000000909010238, 주문시간:20250908072509, 체결수량:2, 체결가격:23828.750000
    gubun:0, 종목코드:NQU25, 주문상태:접수, 주문구분:신규, 매도수구분:매도, 주문수량:2, 미체결수량:2, 주문가격:23830.25, 주문번호:000000909010259, 주문시간:20250908072509, 체결수량:2, 체결가격:23828.750000
    """

    @error_decorator
    def UpdateChejanData(self, data):
        종목코드, 종목명, 주문상태, 주문구분, 매도수구분, 주문수량, 미체결수량, 주문가격, 주문시간, 주문번호, 체결수량, 체결가격 = data
        index = self.GetIndex()
        gubun = self.dict_signal.get(종목코드, None)
        if gubun is None:
            self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - HTS 수동 주문은 포지션 방향을 추적할 수 없어 기록하지 않습니다.')))
            return

        if 주문상태 == '접수' and 주문구분 == '신규' and 매도수구분 in ('매수', '매도'):
            취소시간 = timedelta_sec(self.dict_set['주식매수취소시간초' if gubun in ('BUY_LONG', 'SELL_SHORT') else '주식매도취소시간초'])
            if gubun in ('BUY_LONG', 'SELL_SHORT'): self.dict_intg['추정예수금'] -= 주문수량 * self.dict_info[종목코드]['위탁증거금']
            self.dict_order[gubun][종목코드] = [취소시간, 0, 주문가격]
            self.UpdateChegeollist(index, 종목코드, 종목명, f'{gubun}_REG', 주문수량, 0, 미체결수량, 0, 주문시간, 주문가격, 주문번호)
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'주문 관리 시스템 알림 - [{gubun}_REG] {종목명} | {주문가격} | {주문수량}')))

        elif 주문상태 == '시드부족':
            self.UpdateChegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

        elif 주문상태 == '체결' and 주문구분 == '체결' and 매도수구분 in ('매수', '매도'):
            if gubun in ('BUY_LONG', 'SELL_SHORT'):
                # ['종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                if 종목코드 in self.dict_jg:
                    직전매수가 = self.dict_jg[종목코드]['매수가']
                    직전보유수량 = self.dict_jg[종목코드]['보유수량']
                    직전매입금액 = self.dict_jg[종목코드]['매입금액']
                    보유수량 = 직전보유수량 + 체결수량
                    매입금액 = 직전매입금액 + self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    매수가 = round((직전매수가 * 직전보유수량 + 체결가격 * 체결수량) / 보유수량, self.dict_info[종목코드]['소숫점자리수'] + 1)
                    평가금액 = 매입금액 + (체결가격 - 매수가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
                    if 'LONG' in gubun:
                        평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(mini, 매입금액, 평가금액)
                    else:
                        평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(mini, 매입금액, 평가금액)
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
                    보유수량 = 체결수량
                    매입금액 = 평가금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
                    if 'LONG' in gubun:
                        포지션 = 'LONG'
                        평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(mini, 매입금액, 평가금액)
                    else:
                        포지션 = 'SHORT'
                        평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(mini, 매입금액, 평가금액)
                    self.dict_jg[종목코드] = {
                        '종목명': 종목명,
                        '포지션': 포지션,
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
                    if 보유수량 > 0:
                        self.dict_jg[종목코드]['분할매수횟수'] += 1
                    if 종목코드 in self.dict_order[gubun]:
                        del self.dict_order[gubun][종목코드]

            else:
                if 종목코드 not in self.dict_jg: return
                포지션 = self.dict_jg[종목코드]['포지션']
                매수가 = self.dict_jg[종목코드]['매수가']
                보유수량 = self.dict_jg[종목코드]['보유수량'] - 체결수량
                if 보유수량 != 0:
                    매입금액 = self.dict_info[종목코드]['위탁증거금'] * 보유수량
                    평가금액 = 매입금액 + (체결가격 - 매수가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
                    if 'LONG' in gubun:
                        평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(mini, 매입금액, 평가금액)
                    else:
                        평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(mini, 매입금액, 평가금액)
                    # ['종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '레버리지', '분할매수횟수', '분할매도횟수', '매수시간']
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
                    if 종목코드 in self.dict_order[gubun]:
                        del self.dict_order[gubun][종목코드]

                매입금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                평가금액 = 매입금액 + (체결가격 - 매수가) * self.dict_info[종목코드]['틱가치'] * 체결수량
                mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
                if 'LONG' in gubun:
                    평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(mini, 매입금액, 평가금액)
                else:
                    평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(mini, 매입금액, 평가금액)
                if -100 < 수익률 < 100: self.UpdateTradelist(index, 종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간)
                if 수익률 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['주식매수금지손절간격초'])

            self.dict_jg = dict(sorted(self.dict_jg.items(), key=lambda x: x[1]['매입금액'], reverse=True))

            if 미체결수량 == 0: self.PutOrderComplete(f'{gubun}_COMPLETE', 종목코드)
            self.UpdateChegeollist(index, 종목코드, 종목명, gubun, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            총위탁증거금 = 체결수량 * self.dict_info[종목코드]['위탁증거금']
            if gubun in ('BUY_LONG', 'SELL_SHORT'):
                self.dict_intg['예수금'] -= 총위탁증거금
                if self.dict_set['주식모의투자']:
                    self.dict_intg['추정예수금'] -= 총위탁증거금
            else:
                self.dict_intg['추정예탁자산'] += 수익금
                self.dict_intg['예수금'] += 총위탁증거금 + 수익금
                self.dict_intg['추정예수금'] += 총위탁증거금 + 수익금

            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.mgzservQ.put(('query', ('거래디비', df_jg, 'f_jangolist', 'replace')))
            if self.dict_set['주식알림소리']: self.mgzservQ.put(('sound', f'{종목명} {체결수량}주를 {주문구분}하였습니다'))
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'주문 관리 시스템 알림 - [{gubun}] {종목명} | {체결가격} | {체결수량}')))

        elif 주문상태 == '확인' and 주문구분 in ('정정', '취소'):
            if 주문구분 == '정정':
                gubun_ = gubun.replace('_MODIFY', '')
                정정횟수 = self.dict_order[gubun_][종목코드][1] + 1
                취소시간 = timedelta_sec(self.dict_set['주식매수취소시간초' if gubun in ('BUY_LONG', 'SELL_SHORT') else '주식매도취소시간초'])
                self.dict_order[gubun_][종목코드] = [취소시간, 정정횟수, 주문가격]
            else:
                gubun_ = gubun.replace('_CANCEL', '')
                if gubun in ('BUY_LONG', 'SELL_SHORT'):
                    self.dict_intg['추정예수금'] += 주문수량 * self.dict_info[종목코드]['위탁증거금']
                if 종목코드 in self.dict_order[gubun_]:
                    del self.dict_order[gubun_][종목코드]
                self.PutOrderComplete(gubun, 종목코드)

            self.UpdateChegeollist(index, 종목코드, 종목명, gubun, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            if self.dict_set['주식알림소리']: self.mgzservQ.put(('sound', f'{종목명} {주문수량}주를 {주문구분}하였습니다'))
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'주문 관리 시스템 알림 - [{gubun}] {종목명} | {주문가격} | {주문수량}')))

        elif 주문상태 in ('미접수', '취소', '거부'):
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'주문 관리 시스템 알림 - [{주문상태}][{gubun}] {종목명} | {주문가격} | {주문수량}')))

        self.sagentQ.put(('잔고목록', tuple(self.dict_jg)))
        self.sagentQ.put(('주문목록', self.GetOrderCodeList()))

    def GetOrderCodeList(self):
        return tuple(self.dict_order['BUY_LONG']) + tuple(self.dict_order['SELL_SHORT']) + \
            tuple(self.dict_order['SELL_LONG']) + tuple(self.dict_order['BUY_SHORT'])

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
        self.mgzservQ.put(('window', (ui_num['S거래목록'], df_td[::-1])))
        df = pd.DataFrame([[종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간]], columns=columns_tdf, index=[index])
        self.mgzservQ.put(('query', ('거래디비', df, 'f_tradelist', 'append')))
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
        delete_query = f"DELETE FROM f_totaltradelist WHERE `index` = '{self.str_today}'"
        self.mgzservQ.put(('query', ('거래디비', delete_query)))
        self.mgzservQ.put(('query', ('거래디비', df_tt, 'f_totaltradelist', 'append')))
        self.mgzservQ.put(('window', (ui_num['S실현손익'], df_tt)))

        if not first:
            self.mgzservQ.put(('tele', f'총매수금액 {총매수금액:,.0f}, 총매도금액 {총매도금액:,.0f}, 수익 {총수익금액:,.0f}, 손실 {총손실금액:,.0f}, 수익금합계 {수익금합계:,.0f}'))

        if self.dict_set['스톰라이브']:
            수익률 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익률, 수익금합계]
            self.mgzservQ.put(('live', ('해선', data_list)))

    def UpdateChegeollist(self, index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호):
        # ['종목명', '주문구분', '주문수량', '체결수량', '미체결수량', '체결가', '체결시간', '주문가격', '주문번호']
        self.dict_info[종목코드]['최종거래시간'] = timedelta_sec(self.dict_set['주식매수금지간격초'])
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
        self.dict_cj = dict(sorted(self.dict_cj.items(), key=lambda x: x[0]))
        df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
        self.mgzservQ.put(('window', (ui_num['S체결목록'], df_cj[::-1])))
        df = pd.DataFrame([[종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]], columns=columns_cj, index=[index])
        self.mgzservQ.put(('query', ('거래디비', df, 'f_chegeollist', 'append')))

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
        if self.dict_set['주식손실중지']:
            기준손실금 = self.dict_intg['예탁자산'] * self.dict_set['주식손실중지수익률'] / 100
            if 기준손실금 < -당일평가손익: self.StrategyStop()
        if self.dict_set['주식수익중지']:
            기준수익금 = self.dict_intg['예탁자산'] * self.dict_set['주식수익중지수익률'] / 100
            if 기준수익금 < 당일평가손익: self.StrategyStop()

        if self.dict_jg:
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
        else:
            df_jg = pd.DataFrame(columns=columns_jgf)
        df_tj = pd.DataFrame.from_dict(self.dict_tj, orient='index')
        self.mgzservQ.put(('window', (ui_num['S잔고목록'], df_jg)))
        self.mgzservQ.put(('window', (ui_num['S잔고평가'], df_tj)))

    def StrategyStop(self):
        self.sstgQ.put('매수전략중지')
        self.JangoCheongsan('수동')
