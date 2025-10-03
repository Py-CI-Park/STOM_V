import os
import sys
import sqlite3
from future_kiwoom import *
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, QThread, QTimer
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num, columns_cj, columns_tj, columns_tt, DB_TRADELIST, DICT_SET, columns_tdf, columns_jgf
from utility.static import now, timedelta_sec, qtest_qwait, GetFutureLongPgSgSp, GetFutureShortPgSgSp, str_ymd, \
    now_cme, error_decorator, str_hms_cme_from_str, opstarter_kill, str_ymdhms, str_hms, str_ymdhmsf, str_hmsf, dt_hms


class Updater(QThread):
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal(str)

    def __init__(self, straderQ):
        super().__init__()
        self.straderQ = straderQ

    def run(self):
        while True:
            data = self.straderQ.get()
            if type(data) == tuple:
                self.signal1.emit(data)
            elif type(data) == str:
                self.signal2.emit(data)


class FutureTrader:
    def __init__(self, qlist):
        app = QApplication(sys.argv)

        self.kwzservQ  = qlist[0]
        self.sreceivQ  = qlist[1]
        self.straderQ  = qlist[2]
        self.sstgQ     = qlist[3]
        self.dict_set  = DICT_SET

        if self.dict_set['트레이더프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.df_cj = pd.DataFrame(columns=columns_cj)
        self.df_jg = pd.DataFrame(columns=columns_jgf)
        self.df_tj = pd.DataFrame(columns=columns_tj)
        self.df_td = pd.DataFrame(columns=columns_tdf)
        self.df_tt = pd.DataFrame(columns=columns_tt)

        self.dict_order  = {'BUY_LONG': {}, 'SELL_LONG': {}, 'SELL_SHORT': {}, 'BUY_SHORT': {}}
        self.dict_signal = {}
        self.dict_curc   = {}
        self.dict_info   = {}
        self.dict_intg   = {
            '예수금': 0,
            '추정예수금': 0,
            '예탁자산': 0,
            '추정예탁자산': 0
        }
        self.dict_strg = {
            '당일날짜': str_ymd(now_cme()),
            '계좌번호': '',
            '비밀번호': self.dict_set[f"계좌비밀번호{int(self.dict_set['증권사'][4:]) * 2 - 1}"]
        }
        self.dict_bool = {
            '계좌조회': False,
            '해선잔고청산': False,
            '프로세스종료': False
        }

        self.order_time = now()
        self.intg_odsn  = 3000                                   # 주문용 화면번호
        self.dict_sncd  = {}                                     # 사용한 화면번호의 종목코드 키:화면번호, 벨류:종목코드
        self.jgcs_time  = self.get_jgcs_time()                   # 잔고청산용 전략종료시간 2분전 시간

        self.LoadDatabase()
        self.ft = Future(self, 'Trader')
        self.FutureLogin()

        self.updater = Updater(self.straderQ)
        self.updater.signal1.connect(self.UpdateTuple)
        self.updater.signal2.connect(self.UpdateString)
        self.updater.start()

        self.qtimer1 = QTimer()
        self.qtimer1.setInterval(1 * 1000)
        self.qtimer1.timeout.connect(self.Scheduler)
        self.qtimer1.start()

        self.qtimer2 = QTimer()
        self.qtimer2.setInterval(500)
        self.qtimer2.timeout.connect(self.PutJangoDF)
        self.qtimer2.start()

        self.매도수구분 = {
            '1': '매도',
            '2': '매수'
        }
        self.주문상태 = {
            '0': '미접수',
            '1': '접수',
            '2': '확인',
            '3': '체결',
            'C': '취소',
            'X': '거부'
        }
        self.주문구분 = {
            '0': {
                '1': '신규',
                '2': '정정',
                '3': '취소'
            },
            '1': {
                '10': '원주문',
                '11': '정정주문',
                '12': '취소주문',
                '21': '체결',
                '22': '정정',
                '23': '취소',
                '24': '주문거부',
                '25': '주문접수'
            }
        }
        self.주문유형 = {
            '시장가': '1',
            '지정가': '2'
        }

        app.exec_()

    def get_jgcs_time(self):
        return int(str_hms(timedelta_sec(-120, dt_hms(str(self.dict_set['주식전략종료시간'])))))

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        self.df_cj = pd.read_sql(f"SELECT * FROM f_chegeollist WHERE 체결시간 LIKE '{self.dict_strg['당일날짜']}%'", con).set_index('index')
        self.df_td = pd.read_sql(f"SELECT * FROM f_tradelist WHERE 체결시간 LIKE '{self.dict_strg['당일날짜']}%'", con).set_index('index')

        if len(self.df_cj) > 0: self.kwzservQ.put(('window', (ui_num['S체결목록'], self.df_cj[::-1])))
        if len(self.df_td) > 0: self.kwzservQ.put(('window', (ui_num['S거래목록'], self.df_td[::-1])))
        if self.dict_set['주식모의투자']:
            self.df_jg = pd.read_sql('SELECT * FROM f_jangolist', con).set_index('index')
            if len(self.df_jg) > 0: self.sreceivQ.put(('잔고목록', tuple(self.df_jg.index)))
        con.close()

        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 정보 불러오기 완료')))

    def FutureLogin(self):
        self.ft.CommConnect()
        self.ft.ShowAccountWindow()
        opstarter_kill()

        self.dict_strg['계좌번호'] = self.ft.GetAccountNumber()
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료')))
        text = '해선 전략연산 및 트레이더를 시작하였습니다.'
        if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', text))
        self.kwzservQ.put(('tele', text))

    def UpdateTuple(self, data):
        if len(data) in (7, 8):
            self.CheckOrder(data)
        elif len(data) == 2:
            if type(data[1]) in (int, float):
                self.UpdateJango(data)
            elif data[0] == '설정변경':
                self.dict_set  = data[1]
                self.jgcs_time = self.get_jgcs_time()
            elif data[0] == '종목정보':
                self.dict_info = data[1]
                dummy_time = timedelta_sec(-3600)
                for code in self.dict_info.keys():
                    self.dict_info[code]['시드부족시간'] = dummy_time
                    self.dict_info[code]['최종거래시간'] = dummy_time
                    self.dict_info[code]['손절거래시간'] = dummy_time
        elif len(data) == 3:
            _, code, c = data
            self.dict_curc[code] = c
            self.OrderTimeControl(code)

    def CheckOrder(self, data):
        if len(data) == 7:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 수동주문 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 수동주문, 수동주문유형 = data

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
            inthms = int(str_hms(now_cme()))
            if self.dict_set['주식매수금지거래횟수'] and self.dict_set['주식매수금지거래횟수값'] <= len(self.df_td[self.df_td['종목명'] == 종목명].drop_duplicates('체결시간')):
                주문취소 = True
            elif self.dict_set['주식매수금지손절횟수'] and self.dict_set['주식매수금지손절횟수값'] <= len(self.df_td[(self.df_td['종목명'] == 종목명) & (self.df_td['수익율'] < 0)].drop_duplicates('체결시간')):
                주문취소 = True
            elif 잔고없음 and inthms < self.dict_set['주식전략종료시간'] and len(self.df_jg) >= self.dict_set['주식최대매수종목수']:
                주문취소 = True
            elif self.dict_set['주식매수금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
            elif self.dict_set['주식매수금지손절간격'] and 현재시간 < self.dict_info[종목코드]['손절거래시간']:
                주문취소 = True
            elif not 잔고없음 and self.df_jg['분할매수횟수'][종목코드] >= self.dict_set['주식매수분할횟수']:
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

        if 주문취소:
            if 'CANCEL' not in 주문구분:
                self.sstgQ.put((f'{주문구분}_CANCEL', 종목코드))
        else:
            if 수동주문 and 'CANCEL' not in 주문구분:
                self.sstgQ.put((f'{주문구분}_MANUAL', 종목코드))

            if 주문수량 > 0:
                self.CreateOrder(주문구분, 종목코드, 종목명, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 0, 수동주문유형)
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

    def CreateOrder(self, 주문구분, 종목코드, 종목명, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 정정횟수, 수동주문유형):
        주문구분번호 = 0
        if 주문구분 in ('SELL_LONG', 'BUY_SHORT'):                 주문구분번호 = 1
        elif 주문구분 in ('BUY_LONG', 'SELL_SHORT'):               주문구분번호 = 2
        elif 주문구분 in ('SELL_LONG_CANCEL', 'BUY_SHORT_CANCEL'): 주문구분번호 = 3
        elif 주문구분 in ('BUY_LONG_CANCEL', 'SELL_SHORT_CANCEL'): 주문구분번호 = 4
        elif 주문구분 in ('SELL_LONG_MODIFY', 'BUY_SHORT_MODIFY'): 주문구분번호 = 5
        elif 주문구분 in ('BUY_LONG_MODIFY', 'SELL_SHORT_MODIFY'): 주문구분번호 = 6

        if 수동주문:
            주문유형 = '1'
        elif 'BUY_LONG' in 주문구분 or 'BUY_SHORT' in 주문구분:
            주문유형 = self.주문유형[self.dict_set['주식매수주문구분']] if 수동주문유형 is None else self.주문유형[수동주문유형]
        else:
            주문유형 = self.주문유형[self.dict_set['주식매도주문구분']] if 수동주문유형 is None else self.주문유형[수동주문유형]

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
                    self.UpdateChejanData(종목코드, 종목명, '접수불가', 주문구분, '매수', 주문수량, 0, 주문가격, ct, 주문번호, 0, 0)
                else:
                    주문구분 = '매수' if 주문구분 in ('BUY_LONG', 'SELL_SHORT') else '매도'
                    self.UpdateChejanData(종목코드, 종목명, '체결', '신규', 주문구분, 주문수량, 0, 주문가격, ct, 주문번호, 주문수량, 주문가격)
            else:
                data = [주문구분, '', self.dict_strg['계좌번호'], 주문구분번호, 종목코드, 주문수량, 주문가격, '', 주문유형, 주문번호, 종목명, 시그널시간]
                self.SendOrder(data)

    def SendOrder(self, order):
        curr_time = now()
        if curr_time < self.order_time:
            next_time = (self.order_time - curr_time).total_seconds()
            QTimer.singleShot(int(next_time * 1000), lambda: self.SendOrder(order))
            return

        self.intg_odsn = self.intg_odsn + 1 if self.intg_odsn + 1 < 9000 else 3000
        order[1] = str(self.intg_odsn)

        name, signal_time = order[-2:]
        self.OrderTimeLog(signal_time)
        code = order[4]
        ret = self.ft.SendOrder(order[:-2])
        if ret == 0:
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [주문전송] [{order[0]}] {name} | {order[6]} | {order[5]}')))
            self.order_time = timedelta_sec(0.2)
            self.dict_sncd[self.intg_odsn] = order[4]
            self.dict_signal[code] = order[0]
        else:
            self.PutOrderComplete(f'{order[0]}_CANCEL', order[4])
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [주문실패] [{order[0]}] {name} | {order[6]} | {order[5]}')))

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            if 현재가 != self.df_jg['현재가'][종목코드]:
                포지션 = self.df_jg['포지션'][종목코드]
                매입가 = self.df_jg['매입가'][종목코드]
                매입금액 = self.df_jg['매입금액'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                평가금액 = 매입금액 + (현재가 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                if 포지션 == 'LONG':
                    평가금액, 평가손익, 수익율 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                else:
                    평가금액, 평가손익, 수익율 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                columns = ['현재가', '수익율', '평가손익', '평가금액']
                self.df_jg.loc[종목코드, columns] = 현재가, 수익율, 평가손익, 평가금액
        except:
            pass

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

    def CancelOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        df = self.GetMichegeolDF(종목명, 주문구분)
        if len(df) > 0:
            미체결수량 = df['미체결수량'].iloc[-1]
            if 미체결수량 > 0:
                현재시간 = now()
                주문번호 = df['주문번호'].iloc[-1]
                self.CreateOrder(f'{주문구분}_CANCEL', 종목코드, 종목명, 0, 미체결수량, 주문번호, 현재시간, False, 0, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        df = self.GetMichegeolDF(종목명, 주문구분)
        if len(df) > 0:
            미체결수량 = df['미체결수량'].iloc[-1]
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
                주문번호 = df['주문번호'].iloc[-1]
                self.CreateOrder(f'{주문구분}_MODIFY', 종목코드, 종목명, 정정가격, 미체결수량, 주문번호, 현재시간, False, 정정횟수, None)

    def UpdateString(self, data):
        if data == 'S체결목록':
            self.kwzservQ.put(('tele', self.df_cj)) if len(self.df_cj) > 0 else self.kwzservQ.put(('tele', '현재는 체결목록이 없습니다.'))
        elif data == 'S거래목록':
            self.kwzservQ.put(('tele', self.df_td)) if len(self.df_td) > 0 else self.kwzservQ.put(('tele', '현재는 거래목록이 없습니다.'))
        elif data == 'S잔고평가':
            self.kwzservQ.put(('tele', self.df_jg)) if len(self.df_jg) > 0 else self.kwzservQ.put(('tele', '현재는 잔고목록이 없습니다.'))
        elif data == 'S잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로파일링결과':
            self.pr.print_stats(sort='cumulative')
        elif data == '프로세스종료':
            if not self.dict_bool['프로세스종료']:
                self.dict_bool['프로세스종료'] = True
                QTimer.singleShot(180 * 1000, self.SysExit)

    def JangoCheongsan(self, gubun):
        self.dict_bool['해선잔고청산'] = True

        for 주문구분 in self.dict_order.keys():
            for 종목코드 in self.dict_order[주문구분].keys():
                self.CancelOrder(종목코드, 주문구분)

        if (gubun == '수동' or self.dict_set['주식잔고청산']) and len(self.df_jg) > 0:
            for 종목코드 in self.df_jg.index:
                포지션 = self.df_jg['포지션'][종목코드]
                종목명 = self.df_jg['종목명'][종목코드]
                현재가 = self.df_jg['현재가'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                주문구분 = 'SELL_LONG' if 포지션 == 'LONG' else 'BUY_SHORT'
                if self.dict_set['주식모의투자']:
                    self.dict_signal[종목코드] = 주문구분
                    ct = str_ymdhms(now_cme())
                    self.UpdateChejanData(종목코드, 종목명, '체결', '신규', '매도', 보유수량, 0, 현재가, ct, '', 보유수량, 현재가)
                else:
                    self.CheckOrder((주문구분, 종목코드, 종목명, 현재가, 보유수량, now(), True))

            if self.dict_set['주식알림소리']:
                self.kwzservQ.put(('sound', '해선 잔고청산 주문을 전송하였습니다.'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 실행 알림 - 해선 잔고청산 주문 완료')))

    def Scheduler(self):
        inthms = int(str_hms(now_cme()))
        if not self.dict_bool['계좌조회']:
            self.GetAccountjanGo()
        if self.dict_set['주식타임프레임'] and inthms < self.dict_set['주식전략종료시간']:
            self.OrderTimeControl()
        if self.jgcs_time < inthms and not self.dict_bool['해선잔고청산']:
            self.JangoCheongsan('자동')
        self.UpdateTotaljango()

    def GetAccountjanGo(self):
        self.dict_bool['계좌조회'] = True

        if self.dict_set['주식모의투자']:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql('SELECT * FROM f_tradelist', con)
            con.close()
            self.dict_intg['예수금'] = 1_000_000_000 + df['수익금'].sum()
            if self.dict_intg['예수금'] < 1_000_000_000: self.dict_intg['예수금'] = 1_000_000_000
        else:
            df = self.ft.GetBalances(self.dict_strg['계좌번호'], self.dict_strg['비밀번호'])
            df.set_index('통화코드', inplace=True)
            self.dict_intg['예수금'] = round(df['원화대용평가금액']['USD'] / 100, 2)

            df = self.ft.GetJango(self.dict_strg['계좌번호'], self.dict_strg['비밀번호'])
            if len(df) > 0:
                df['종목명'] = ''
                columns = ['종목코드', '종목명', '포지션', '매입가', '현재가', '수익율', '평가손익', '매입금액', '평가금액', '보유수량']
                df = df[[columns]]
                df['분할매수횟수'] = 5
                df['분할매도횟수'] = 0
                df['매수시간'] = self.dict_strg['당일날짜'] + '093000'
                df['종목명'] = df['종목코드'].apply(lambda x: self.dict_info[x]['종목명'])
                self.df_jg = df.set_index('종목코드')
                self.sreceivQ.put(('잔고목록', tuple(self.df_jg.index)))

        self.dict_intg['추정예수금'] = self.dict_intg['예수금']
        self.dict_intg['예탁자산'] = self.dict_intg['예수금']
        self.dict_intg['추정예탁자산'] = self.dict_intg['예수금']

        if len(self.df_jg) > 0:
            for index in self.df_jg.index:
                yesugm = self.df_jg['보유수량'][index] * self.dict_info[index]['위탁증거금']
                self.dict_intg['예수금'] -= yesugm
            self.dict_intg['추정예수금'] = self.dict_intg['예수금']

            bjc = len(self.df_jg)
            tpp = self.df_jg['수익율'].sum()
            tsg = self.df_jg['평가손익'].sum()
            tbg = self.df_jg['매입금액'].sum()
            tpg = self.df_jg['평가금액'].sum()
            self.df_tj.loc[self.dict_strg['당일날짜']] = self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], bjc, tpp, tsg, tbg, tpg

        if len(self.df_td) > 0: self.UpdateTotaltradelist(first=True)
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 계좌 조회 완료')))

    def SysExit(self):
        if self.qtimer1.isActive():  self.qtimer1.stop()
        if self.updater.isRunning(): self.updater.quit()
        self.SaveDayData()
        self.kwzservQ.put(('tele', '해선 트레이더 종료'))
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더 종료')))
        qtest_qwait(5)
        sys.exit()

    def SaveDayData(self):
        if len(self.df_td) > 0:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql(f"SELECT * FROM f_totaltradelist WHERE `index` = '{self.dict_strg['당일날짜']}'", con)
            con.close()
            if len(df) == 0:
                df = self.df_tt[['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익율', '수익금합계']]
                self.kwzservQ.put(('query', ('거래디비', df, 'f_totaltradelist', 'append')))
                if self.dict_set['주식알림소리']:
                    self.kwzservQ.put(('sound', '일별실현손익를 저장하였습니다.'))
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 일별실현손익 저장 완료')))

    # noinspection PyUnusedLocal
    def OnReceiveMsg(self, sScrNo, sRQName, sTrCode, sMsg):
        print(f'[{now()}]{sMsg}')
        self.kwzservQ.put(('window', (ui_num['S오더텍스트'], f'{sMsg}')))
        if '매수증거금' in sMsg:
            sn = int(sScrNo)
            code = self.dict_sncd[sn] if sn in self.dict_sncd.keys() else ''
            gubun = self.dict_signal[code]
            self.PutOrderComplete(f'{gubun}_CANCEL', code)

    # noinspection PyUnusedLocal
    def OnReceiveChejanData(self, gubun, itemcnt, fidlist):
        if self.dict_set['주식모의투자']:
            return

        if gubun in ('0', '1'):
            try:
                종목코드 = self.ft.GetChejanData(9001)
                종목명 = self.dict_info[종목코드]['종목명']
                주문상태 = self.ft.GetChejanData(913)
                주문구분 = self.ft.GetChejanData(905)
                매도수구분 = self.ft.GetChejanData(907)
                주문수량 = int(self.ft.GetChejanData(900))
                미체결수량 = int(self.ft.GetChejanData(902))
                주문가격 = float(self.ft.GetChejanData(901))
                주문번호 = self.ft.GetChejanData(9203)
                주문시간 = f"{self.dict_strg['당일날짜']}{str_hms_cme_from_str(self.ft.GetChejanData(908))}"
            except Exception as e:
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - OnReceiveChejanData 0 {e}')))
            else:
                try:
                    체결수량 = int(self.ft.GetChejanData(911))
                    체결가격 = float(self.ft.GetChejanData(910))
                except:
                    체결수량 = 0
                    체결가격 = 0
                주문상태 = self.주문상태[주문상태]
                주문구분 = self.주문구분[gubun][주문구분]
                매도수구분 = self.매도수구분[매도수구분]
                self.UpdateChejanData(종목코드, 종목명, 주문상태, 주문구분, 매도수구분, 주문수량, 미체결수량, 주문가격, 주문시간, 주문번호, 체결수량, 체결가격)

    @error_decorator
    def UpdateChejanData(self, 종목코드, 종목명, 주문상태, 주문구분, 매도수구분, 주문수량, 미체결수량, 주문가격, 주문시간, 주문번호, 체결수량, 체결가격):
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
                if 종목코드 in self.df_jg.index:
                    직전매입가 = self.df_jg['매입가'][종목코드]
                    직전보유수량 = self.df_jg['보유수량'][종목코드]
                    직전매입금액 = self.df_jg['매입금액'][종목코드]
                    보유수량 = 직전보유수량 + 체결수량
                    매입금액 = 직전매입금액 + self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    매입가 = round((직전매입가 * 직전보유수량 + 체결가격 * 체결수량) / 보유수량, self.dict_info[종목코드]['소숫점자리수'] + 1)
                    평가금액 = 매입금액 + (체결가격 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    if 'LONG' in gubun:
                        평가금액, 수익금, 수익율 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                    else:
                        평가금액, 수익금, 수익율 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                    columns = ['매입가', '현재가', '수익율', '평가손익', '매입금액', '평가금액', '보유수량', '매수시간']
                    self.df_jg.loc[종목코드, columns] = 매입가, 체결가격, 수익율, 수익금, 매입금액, 평가금액, 보유수량, 주문시간
                else:
                    매입금액 = 평가금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                    if 'LONG' in gubun:
                        포지션 = 'LONG'
                        평가금액, 수익금, 수익율 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                    else:
                        포지션 = 'SHORT'
                        평가금액, 수익금, 수익율 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                    self.df_jg.loc[종목코드] = 종목명, 포지션, 체결가격, 체결가격, 수익율, 수익금, 매입금액, 평가금액, 체결수량, 0, 0, 주문시간

                if 미체결수량 == 0:
                    self.df_jg.loc[종목코드, '분할매수횟수'] = self.df_jg['분할매수횟수'][종목코드] + 1
                    if 종목코드 in self.dict_order[gubun].keys():
                        del self.dict_order[gubun][종목코드]

            else:
                if 종목코드 not in self.df_jg.index:
                    return

                포지션 = self.df_jg['포지션'][종목코드]
                매입가 = self.df_jg['매입가'][종목코드]
                직전보유수량 = self.df_jg['보유수량'][종목코드]
                보유수량 = 직전보유수량 - 체결수량
                if 보유수량 != 0:
                    매입금액 = self.dict_info[종목코드]['위탁증거금'] * 보유수량
                    평가금액 = 매입금액 + (체결가격 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    if 'LONG' in gubun:
                        평가금액, 수익금, 수익율 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                    else:
                        평가금액, 수익금, 수익율 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                    columns = ['현재가', '수익율', '평가손익', '매입금액', '평가금액', '보유수량']
                    self.df_jg.loc[종목코드, columns] = 체결가격, 수익율, 수익금, 매입금액, 평가금액, 보유수량
                else:
                    self.df_jg.drop(index=종목코드, inplace=True)

                if 미체결수량 == 0:
                    if 보유수량 > 0:
                        self.df_jg.loc[종목코드, '분할매도횟수'] = self.df_jg['분할매도횟수'][종목코드] + 1
                    if 종목코드 in self.dict_order[gubun].keys():
                        del self.dict_order[gubun][종목코드]

                매입금액 = self.dict_info[종목코드]['위탁증거금'] * 체결수량
                평가금액 = 매입금액 + (체결가격 - 매입가) * self.dict_info[종목코드]['틱가치'] * 체결수량
                if 'LONG' in gubun:
                    평가금액, 수익금, 수익율 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                else:
                    평가금액, 수익금, 수익율 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                if -100 < 수익율 < 100: self.UpdateTradelist(index, 종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간)
                if 수익율 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['주식매수금지손절간격초'])

            self.df_jg.sort_values(by=['매입금액'], ascending=False, inplace=True)
            self.PutJangoDF()

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

            self.kwzservQ.put(('query', ('거래디비', self.df_jg, 'f_jangolist', 'replace')))
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

        self.sreceivQ.put(('잔고목록', tuple(self.df_jg.index)))
        self.sreceivQ.put(('주문목록', self.GetOrderCodeList()))

    def UpdateTradelist(self, index, 종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간):
        self.df_td.loc[index] = 종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간
        self.kwzservQ.put(('window', (ui_num['S거래목록'], self.df_td[::-1])))
        df = pd.DataFrame([[종목명, 포지션, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간]], columns=columns_tdf, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 'f_tradelist', 'append')))
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        거래횟수 = len(self.df_td.drop_duplicates(['종목명', '체결시간']))
        총매수금액 = self.df_td['매수금액'].sum()
        총매도금액 = self.df_td['매도금액'].sum()
        총수익금액 = self.df_td[self.df_td['수익금'] > 0]['수익금'].sum()
        총손실금액 = self.df_td[self.df_td['수익금'] < 0]['수익금'].sum()
        수익금합계 = self.df_td['수익금'].sum()
        수익율 = round(수익금합계 / self.dict_intg['추정예탁자산'] * 100, 2)
        self.df_tt.loc[self.dict_strg['당일날짜']] = 거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익율, 수익금합계
        self.kwzservQ.put(('window', (ui_num['S실현손익'], self.df_tt)))

        if not first:
            self.kwzservQ.put(('tele', f'거래횟수 {거래횟수}회 / 총매수금액 {int(총매수금액):,}원 / 총매도금액 {int(총매도금액):,}원 / 총수익금액 {int(총수익금액):,}원 / '
                                       f'총손실금액 {int(총손실금액):,}원 / 수익율 {수익율:.2f}% / 수익금합계 {int(수익금합계):,}원'))

        if self.dict_set['스톰라이브']:
            수익율 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익율, 수익금합계]
            self.kwzservQ.put(('live', ('해선', data_list)))

    def UpdateChegeollist(self, index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호):
        self.dict_info[종목코드]['최종거래시간'] = timedelta_sec(self.dict_set['주식매수금지간격초'])
        self.df_cj.loc[index] = 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호
        self.kwzservQ.put(('window', (ui_num['S체결목록'], self.df_cj[::-1])))
        df = pd.DataFrame([[종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]], columns=columns_cj, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 'f_chegeollist', 'append')))

    def UpdateTotaljango(self):
        if len(self.df_jg) > 0:
            총평가손익 = self.df_jg['평가손익'].sum()
            총매입금액 = self.df_jg['매입금액'].sum()
            총평가금액 = self.df_jg['평가금액'].sum()
            잔고수량 = len(self.df_jg)
            총수익율 = round(총평가손익 / 총매입금액 * 100, 2)
            추정예탁자산 = self.dict_intg['추정예탁자산'] + 총평가손익
            self.df_tj.loc[self.dict_strg['당일날짜']] = 추정예탁자산, self.dict_intg['예수금'], 잔고수량, 총수익율, 총평가손익, 총매입금액, 총평가금액
        else:
            추정예탁자산 = self.dict_intg['예수금']
            self.df_tj.loc[self.dict_strg['당일날짜']] = 추정예탁자산, self.dict_intg['예수금'], 0, 0.0, 0, 0, 0

        총평가손익 = self.df_jg['평가손익'].sum() + self.df_td['수익금'].sum()
        if self.dict_set['주식손실중지']:
            기준손실금 = self.dict_intg['예탁자산'] * self.dict_set['주식손실중지수익율'] / 100
            if 기준손실금 < -총평가손익: self.StrategyStop()
        if self.dict_set['주식수익중지']:
            기준수익금 = self.dict_intg['예탁자산'] * self.dict_set['주식수익중지수익율'] / 100
            if 기준수익금 < 총평가손익: self.StrategyStop()

        self.kwzservQ.put(('window', (ui_num['S잔고목록'], self.df_jg)))
        self.kwzservQ.put(('window', (ui_num['S잔고평가'], self.df_tj)))

    def PutJangoDF(self):
        if not self.dict_bool['프로세스종료']:
            data = ('잔고목록', self.df_jg)
            self.sstgQ.put(data)

    def StrategyStop(self):
        self.sstgQ.put('매수전략중지')
        self.JangoCheongsan('수동')

    def PutOrderComplete(self, cmsg, code):
        self.sstgQ.put((cmsg, code))

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.')))

    def GetOrderCodeList(self):
        return tuple(self.dict_order['BUY_LONG'].keys()) + tuple(self.dict_order['SELL_SHORT'].keys()) + \
            tuple(self.dict_order['SELL_LONG'].keys()) + tuple(self.dict_order['BUY_SHORT'].keys())

    def GetMichegeolDF(self, name, gubun):
        return self.df_cj[(self.df_cj['종목명'] == name) & ((self.df_cj['주문구분'] == gubun) | (self.df_cj['주문구분'] == f'{gubun}_REG'))]

    def GetIndex(self):
        index = str_ymdhmsf(now_cme())
        if index in self.df_cj.index:
            while index in self.df_cj.index:
                index = str(int(index) + 1)
        return index
