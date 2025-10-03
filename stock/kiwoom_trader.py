import sqlite3
from kiwoom import *
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, QThread, QTimer
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num, columns_cj, columns_tj, columns_jg, columns_td, columns_tt, DB_TRADELIST, DICT_SET
from utility.static import now, timedelta_sec, str_hms, roundfigure_lower, roundfigure_upper, qtest_qwait, \
    GetKiwoomPgSgSp, GetHogaunit, error_decorator, str_ymd, str_ymdhms, str_ymdhmsf


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


class KiwoomTrader:
    def __init__(self, qlist):
        app = QApplication(sys.argv)

        self.kwzservQ  = qlist[0]
        self.sreceivQ  = qlist[1]
        self.straderQ  = qlist[2]
        self.sstgQs    = qlist[3]
        self.dict_set  = DICT_SET

        if self.dict_set['트레이더프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.df_cj = pd.DataFrame(columns=columns_cj)
        self.df_jg = pd.DataFrame(columns=columns_jg)
        self.df_tj = pd.DataFrame(columns=columns_tj)
        self.df_td = pd.DataFrame(columns=columns_td)
        self.df_tt = pd.DataFrame(columns=columns_tt)

        self.dict_order = {'매수': {}, '매도': {}}
        self.dict_info  = {}
        self.dict_curc  = {}
        self.dict_sgbn  = {}
        self.dict_intg  = {
            '장운영상태': 1,
            '예수금': 0,
            '추정예수금': 0,
            '추정예탁자산': 0,
            '종목당투자금': 0
        }
        self.dict_strg = {
            '당일날짜': str_ymd(),
            '계좌번호': ''
        }
        self.dict_bool = {
            '계좌조회': False,
            '트레이더시작': False,
            '주식잔고청산': False,
            '프로세스종료': False
        }

        self.order_time = now()
        self.int_hgtime = int(str_ymdhms())
        self.tuple_kosd = None

        self.intg_odsn = 3000                                   # 주문용 화면번호
        self.dict_sncd = {}                                     # 사용한 화면번호의 종목코드 키:화면번호, 벨류:종목코드

        self.LoadDatabase()
        self.kw = Kiwoom(self, 'Trader')
        self.KiwoomLogin()

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

        self.주문유형 = {
            '지정가': '00',
            '시장가': '03',
            '최유리지정가': '06',
            '최우선지정가': '07',
            '지정가IOC': '10',
            '시장가IOC': '13',
            '최유리IOC': '16',
            '지정가FOK': '20',
            '시장가FOK': '23',
            '최유리FOK': '26'
        }

        app.exec_()

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        self.df_cj = pd.read_sql(f"SELECT * FROM s_chegeollist WHERE 체결시간 LIKE '{self.dict_strg['당일날짜']}%'", con).set_index('index')
        self.df_td = pd.read_sql(f"SELECT * FROM s_tradelist WHERE 체결시간 LIKE '{self.dict_strg['당일날짜']}%'", con).set_index('index')

        if len(self.df_cj) > 0: self.kwzservQ.put(('window', (ui_num['S체결목록'], self.df_cj[::-1])))
        if len(self.df_td) > 0: self.kwzservQ.put(('window', (ui_num['S거래목록'], self.df_td[::-1])))
        if self.dict_set['주식모의투자']:
            self.df_jg = pd.read_sql('SELECT * FROM s_jangolist', con).set_index('index')
            if len(self.df_jg) > 0: self.sreceivQ.put(('잔고목록', tuple(self.df_jg.index)))
        con.close()

        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 정보 불러오기 완료')))

    def KiwoomLogin(self):
        self.kw.CommConnect()

        self.dict_strg['계좌번호'] = self.kw.GetAccountNumber()
        self.tuple_kosd = self.kw.GetCodeListByMarket('10')
        list_code = self.kw.GetCodeListByMarket('0') + self.tuple_kosd
        dummy_time = timedelta_sec(-3600)
        for code in list_code:
            self.dict_info[code] = {
                '종목명': self.kw.GetMasterCodeName(code),
                '시드부족시간': dummy_time,
                '최종거래시간': dummy_time,
                '손절거래시간': dummy_time
            }

        if int(str_hms()) > 90000:
            self.dict_intg['장운영상태'] = 3

        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료')))
        text = '주식 전략연산 및 트레이더를 시작하였습니다.'
        if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', text))
        self.kwzservQ.put(('tele', text))

    def UpdateTuple(self, data):
        if len(data) in (7, 8):
            self.CheckOrder(data)
        elif len(data) == 2:
            if type(data[1]) in (int, float):
                self.UpdateJango(data)
            elif data[0] == '관심진입':
                if data[1] in self.dict_order['매도'].keys():
                    self.CancelOrder(data[1], '매도')
            elif data[0] == '관심이탈':
                if data[1] in self.dict_order['매수'].keys():
                    self.CancelOrder(data[1], '매수')
            elif data[0] == '설정변경':
                self.dict_set = data[1]
            elif data[0] == '종목구분번호':
                self.dict_sgbn = data[1]
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
        매수주문중 = 종목코드 in self.dict_order['매수'].keys()
        매도주문중 = 종목코드 in self.dict_order['매도'].keys()

        주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 수동주문:
            if 잔고없음 or 매도주문중: 주문취소 = True
        elif 주문구분 == '매수':
            inthms = int(str_hms())
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
            elif self.dict_intg['추정예수금'] < 주문수량 * 주문가격:
                if 현재시간 > self.dict_info[종목코드]['시드부족시간']:
                    self.CreateOrder('시드부족', 종목코드, 종목명, 주문가격, 주문수량, '', 시그널시간, 수동주문, None)
                    self.dict_info[종목코드]['시드부족시간'] = timedelta_sec(180)
                주문취소 = True
            elif 매수주문중:
                주문취소 = True
        elif 주문구분 == '매도':
            if 잔고없음 or 매도주문중:
                주문취소 = True
            elif self.dict_set['주식매도금지간격'] and 현재시간 < self.dict_info[종목코드]['최종거래시간']:
                주문취소 = True
        elif '취소' in 주문구분:
            if 주문구분 == '매수취소' and not 매수주문중:   주문취소 = True
            elif 주문구분 == '매도취소' and not 매도주문중: 주문취소 = True

        if 주문취소:
            if '취소' not in 주문구분:
                self.PutOrderComplete(f'{주문구분}취소', 종목코드)
        else:
            if 수동주문 and 주문구분 in ('매수', '매도'):
                self.PutOrderComplete(f'{주문구분}주문', 종목코드)

            if 주문구분 == '매수':
                if self.dict_set['주식매도취소매수시그널'] and 매도주문중:
                    self.CancelOrder(종목코드, 주문구분)
            elif 주문구분 == '매도':
                if self.dict_set['주식매수취소매도시그널'] and 매수주문중:
                    self.CancelOrder(종목코드, 주문구분)

            if 주문수량 > 0:
                self.CreateOrder(주문구분, 종목코드, 종목명, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 수동주문유형)
            else:
                self.PutOrderComplete(f'{주문구분}취소', 종목코드)

    def CreateOrder(self, 주문구분, 종목코드, 종목명, 주문가격, 주문수량, 주문번호, 시그널시간, 수동주문, 수동주문유형):
        주문구분번호 = 0
        주문취소 = False
        if 주문구분 == '매수':      주문구분번호 = 1
        elif 주문구분 == '매도':    주문구분번호 = 2
        elif 주문구분 == '매수취소': 주문구분번호 = 3
        elif 주문구분 == '매도취소': 주문구분번호 = 4
        elif 주문구분 == '매수정정': 주문구분번호 = 5
        elif 주문구분 == '매도정정': 주문구분번호 = 6

        if 수동주문:
            주문유형 = '03'
        elif '매수' in 주문구분:
            주문유형 = self.주문유형[self.dict_set['주식매수주문구분']] if 수동주문유형 is None else self.주문유형[수동주문유형]
        else:
            주문유형 = self.주문유형[self.dict_set['주식매도주문구분']] if 수동주문유형 is None else self.주문유형[수동주문유형]

        if 수동주문:
            if not (self.dict_set['주식모의투자'] or 주문구분 == '시드부족'):
                주문가격 = 0
        elif 주문구분 == '매수':
            if self.dict_set['주식매수주문구분'] in ('지정가', '지정가IOC', '지정가FOK'):
                주문가격 += GetHogaunit(종목코드 in self.tuple_kosd, 주문가격, self.int_hgtime) * self.dict_set['주식매수지정가호가번호']
            if self.dict_set['주식매수금지라운드피겨'] and roundfigure_upper(주문가격, self.dict_set['주식매수금지라운드호가'], self.int_hgtime):
                주문취소 = True
            if self.dict_set['주식매수주문구분'] not in ('지정가', '지정가IOC', '지정가FOK'):
                if not (self.dict_set['주식모의투자'] or 주문구분 == '시드부족'):
                    주문가격 = 0
        elif 주문구분 == '매도':
            if self.dict_set['주식매도주문구분'] in ('지정가', '지정가IOC', '지정가FOK'):
                주문가격 += GetHogaunit(종목코드 in self.tuple_kosd, 주문가격, self.int_hgtime) * self.dict_set['주식매도지정가호가번호']
            if self.dict_set['주식매도금지라운드피겨'] and roundfigure_lower(주문가격, self.dict_set['주식매도금지라운드호가'], self.int_hgtime):
                주문취소 = True
            if self.dict_set['주식매도주문구분'] not in ('지정가', '지정가IOC', '지정가FOK'):
                if not (self.dict_set['주식모의투자'] or 주문구분 == '시드부족'):
                    주문가격 = 0
        elif 주문구분 == '매수정정':
            if self.dict_set['주식매수금지라운드피겨'] and roundfigure_upper(주문가격, self.dict_set['주식매수금지라운드호가'], self.int_hgtime):
                주문취소 = True
        elif 주문구분 == '매도정정':
            if self.dict_set['주식매도금지라운드피겨'] and roundfigure_lower(주문가격, self.dict_set['주식매도금지라운드호가'], self.int_hgtime):
                주문취소 = True

        if 주문취소:
            self.PutOrderComplete(f'{주문구분}취소', 종목코드)
        elif 주문수량 > 0:
            if self.dict_set['주식모의투자'] or 주문구분 == '시드부족':
                self.OrderTimeLog(시그널시간)
                ct = str_ymdhms()
                if 주문구분 == '시드부족':
                    self.UpdateChejanData(종목코드, 종목명, 주문가격, '접수불가', 주문구분, 주문수량, 0, 주문수량, 주문가격, 0, ct, 주문번호)
                else:
                    self.UpdateChejanData(종목코드, 종목명, 주문가격, '체결', 주문구분, 주문수량, 주문수량, 0, 주문가격, 주문가격, ct, 주문번호)
            else:
                data = [주문구분, 0, self.dict_strg['계좌번호'], 주문구분번호, 종목코드, int(주문수량), int(주문가격), 주문유형, 주문번호, 종목명, 시그널시간]
                self.SendOrder(data)

    def SendOrder(self, order):
        curr_time = now()
        if curr_time < self.order_time:
            next_time = (self.order_time - curr_time).total_seconds()
            QTimer.singleShot(int(next_time * 1000), lambda: self.SendOrder(order))
            return

        self.intg_odsn = self.intg_odsn + 1 if self.intg_odsn + 1 < 9000 else 3000
        order[1] = self.intg_odsn

        name, signal_time = order[-2:]
        self.OrderTimeLog(signal_time)
        ret = self.kw.SendOrder(order[:-2])
        if ret == 0:
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [주문전송] {name} | {order[6]} | {order[5]} | {order[0]}')))
            self.order_time = timedelta_sec(0.2)
            self.dict_sncd[self.intg_odsn] = order[4]
        else:
            self.PutOrderComplete(f'{order[0]}취소', order[4])
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [주문실패] {name} | {order[6]} | {order[5]} | {order[0]}')))

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            if 현재가 != self.df_jg['현재가'][종목코드]:
                매입금액 = self.df_jg['매입금액'][종목코드]
                보유수량 = int(self.df_jg['보유수량'][종목코드])
                평가금액, 평가손익, 수익율 = GetKiwoomPgSgSp(매입금액, 보유수량 * 현재가)
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
                    if gubun == '매수':
                        if self.dict_set['주식매수취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    else:
                        if self.dict_set['주식매도취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    if gubun == '매수':
                        if order_info[1] < self.dict_set['주식매수정정횟수'] and code in self.dict_curc.keys() and \
                                self.dict_curc[code] >= order_info[2] + order_info[3] * self.dict_set['주식매수정정호가차이']:
                            modify_list.append((code, gubun))
                    else:
                        if order_info[1] < self.dict_set['주식매도정정횟수'] and code in self.dict_curc.keys() and \
                                self.dict_curc[code] <= order_info[2] - order_info[3] * self.dict_set['주식매도정정호가차이']:
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
                self.CreateOrder(f'{주문구분}취소', 종목코드, 종목명, 0, 미체결수량, 주문번호, 현재시간, False, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        df = self.GetMichegeolDF(종목명, 주문구분)
        if len(df) > 0:
            미체결수량 = df['미체결수량'].iloc[-1]
            if 미체결수량 > 0:
                if 주문구분 == '매수':
                    주문가격 = self.dict_curc[종목코드] - self.dict_order[주문구분][종목코드][3] * self.dict_set[f'주식{주문구분}정정호가']
                else:
                    주문가격 = self.dict_curc[종목코드] + self.dict_order[주문구분][종목코드][3] * self.dict_set[f'주식{주문구분}정정호가']

                현재시간 = now()
                주문번호 = df['주문번호'].iloc[-1]
                self.CreateOrder(f'{주문구분}정정', 종목코드, 종목명, 주문가격, 미체결수량, 주문번호, 현재시간, False, None)

    def UpdateString(self, data):
        if data == 'S체결목록':
            self.kwzservQ.put(('tele', self.df_cj)) if len(self.df_cj) > 0 else self.kwzservQ.put(('tele', '현재는 주식체결목록이 없습니다.'))
        elif data == 'S거래목록':
            self.kwzservQ.put(('tele', self.df_td)) if len(self.df_td) > 0 else self.kwzservQ.put(('tele', '현재는 주식거래목록이 없습니다.'))
        elif data == 'S잔고평가':
            self.kwzservQ.put(('tele', self.df_jg)) if len(self.df_jg) > 0 else self.kwzservQ.put(('tele', '현재는 주식잔고목록이 없습니다.'))
        elif data == 'S잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로파일링결과':
            self.pr.print_stats(sort='cumulative')
        elif data == '프로세스종료':
            if not self.dict_bool['프로세스종료']:
                self.dict_bool['프로세스종료'] = True
                QTimer.singleShot(180 * 1000, self.SysExit)

    def JangoCheongsan(self, gubun):
        self.dict_bool['주식잔고청산'] = True

        for 주문구분 in self.dict_order.keys():
            for 종목코드 in self.dict_order[주문구분].keys():
                self.CancelOrder(종목코드, 주문구분)

        if (gubun == '수동' or self.dict_set['주식잔고청산']) and len(self.df_jg) > 0:
            for 종목코드 in self.df_jg.index:
                종목명 = self.df_jg['종목명'][종목코드]
                현재가 = self.df_jg['현재가'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                if self.dict_set['주식모의투자']:
                    self.UpdateChejanData(종목코드, 종목명, 현재가, '체결', '매도', 보유수량, 보유수량, 0, 현재가, 현재가, str_ymdhms(), '')
                else:
                    self.CheckOrder(('매도', 종목코드, 종목명, 현재가, 보유수량, now(), True))

            if self.dict_set['주식알림소리']:
                self.kwzservQ.put(('sound', f'주식 잔고청산 주문을 전송하였습니다.'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 실행 알림 - 주식 잔고청산 주문 완료')))

    def Scheduler(self):
        if not self.dict_bool['계좌조회']:
            self.GetAccountjanGo()

        if not self.dict_bool['트레이더시작']:
            self.OperationRealreg()

        inthms = int(str_hms())
        if self.dict_intg['장운영상태'] in (2, 3):
            if self.dict_set['주식타임프레임'] and inthms < self.dict_set['주식전략종료시간']:
                self.OrderTimeControl()

            if self.dict_set['주식전략종료시간'] < inthms and not self.dict_bool['주식잔고청산']:
                self.JangoCheongsan('자동')

        self.UpdateTotaljango()

    def GetAccountjanGo(self):
        self.dict_bool['계좌조회'] = True

        while True:
            df = self.kw.Block_Request('opw00004', 계좌번호=self.dict_strg['계좌번호'], 비밀번호='', 상장폐지조회구분=0, 비밀번호입력매체구분='00', output='계좌평가현황', next=0)
            if df['D+2추정예수금'][0]:
                if self.dict_set['주식모의투자']:
                    con = sqlite3.connect(DB_TRADELIST)
                    df = pd.read_sql('SELECT * FROM s_tradelist', con)
                    con.close()
                    self.dict_intg['예수금'] = 100_000_000 - self.df_jg['매입금액'].sum() + df['수익금'].sum()
                    if self.dict_intg['예수금'] < 100_000_000: self.dict_intg['예수금'] = 100_000_000
                else:
                    self.dict_intg['예수금'] = int(df['D+2추정예수금'][0])

                self.dict_intg['추정예수금'] = self.dict_intg['예수금'] * 2
                break
            else:
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 오류가 발생하여 계좌평가현황을 재조회합니다.')))
                qtest_qwait(3.35)

        if not self.dict_set['주식모의투자']:
            df = self.kw.Block_Request('opw00018', 계좌번호=self.dict_strg['계좌번호'], 비밀번호='', 비밀번호입력매체구분='00', 조회구분=2, output='계좌평가잔고개별합산', next=0)
            if df['종목명'][0]:
                df.rename(columns={'종목번호': 'index', '수익률(%)': '수익율'}, inplace=True)
                df['index'] = df['index'].apply(lambda x: x.strip()[1:])
                df['수익율'] = df['수익율'].apply(lambda x: round(float(x) / 100, 2))
                columns = ['매입가', '현재가', '평가손익', '매입금액', '평가금액', '보유수량']
                df[columns] = df[columns].astype(int)
                df['평가손익'] = df['평가금액'] - df['매입금액']
                df['분할매수횟수'] = 5
                df['분할매도횟수'] = 0
                df['매수시간'] = self.dict_strg['당일날짜'] + '080000'
                columns = ['index', '종목명', '매입가', '현재가', '수익율', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                df = df[columns]
                self.df_jg = df.set_index('index')

        while True:
            df = self.kw.Block_Request('opw00018', 계좌번호=self.dict_strg['계좌번호'], 비밀번호='', 비밀번호입력매체구분='00', 조회구분=2, output='계좌평가결과', next=0)
            if df['추정예탁자산'][0]:
                if self.dict_set['주식모의투자']:
                    self.dict_intg['추정예탁자산'] = self.dict_intg['예수금'] + self.df_jg['평가금액'].sum()
                    self.df_tj.loc[self.dict_strg['당일날짜']] = self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 0, 0, 0, 0, 0
                else:
                    self.dict_intg['추정예탁자산'] = int(df['추정예탁자산'][0])
                    tpp = float(int(df['총수익률(%)'][0]) / 100)
                    tsg = int(df['총평가손익금액'][0])
                    tbg = int(df['총매입금액'][0])
                    tpg = int(df['총평가금액'][0])
                    self.df_tj.loc[self.dict_strg['당일날짜']] = self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 0, tpp, tsg, tbg, tpg
                break
            else:
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 오류가 발생하여 계좌평가결과를 재조회합니다.')))
                qtest_qwait(3.35)

        if len(self.df_td) > 0: self.UpdateTotaltradelist(first=True)
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 계좌 조회 완료')))

    def OperationRealreg(self):
        self.dict_bool['트레이더시작'] = True
        self.kw.SetRealReg([sn_oper, ' ', '215;20;214', 0])
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 장운영시간 등록 완료')))
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더 시작')))

    def SysExit(self):
        if self.qtimer1.isActive():  self.qtimer1.stop()
        if self.updater.isRunning(): self.updater.quit()
        self.RemoveAllRealreg()
        self.SaveDayData()
        self.kwzservQ.put(('tele', '주식 트레이더 종료'))
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더 종료')))
        qtest_qwait(5)
        sys.exit()

    def RemoveAllRealreg(self):
        self.kw.SetRealRemove(['ALL', 'ALL'])
        if self.dict_set['주식알림소리']:
            self.kwzservQ.put(('sound', '실시간 주문체결 데이터의 수신을 중단하였습니다.'))
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 실시간 데이터 중단 완료')))

    def SaveDayData(self):
        if self.dict_intg['장운영상태'] != 1 and len(self.df_td) > 0:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql(f"SELECT * FROM s_totaltradelist WHERE `index` = '{self.dict_strg['당일날짜']}'", con)
            con.close()
            if len(df) == 0:
                df = self.df_tt[['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익율', '수익금합계']]
                self.kwzservQ.put(('query', ('거래디비', df, 's_totaltradelist', 'append')))
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
            self.PutOrderComplete('매수취소', code)

    # noinspection PyUnusedLocal
    def OnReceiveRealData(self, code, realtype, realdata):
        if realtype == '장시작시간':
            try:
                self.dict_intg['장운영상태'] = int(self.kw.GetCommRealData(code, 215))
                current = self.kw.GetCommRealData(code, 20)
            except:
                pass
            else:
                self.OperationAlert(current)

    def OperationAlert(self, current):
        if self.dict_set['주식알림소리']:
            if current == '084000':
                self.kwzservQ.put(('sound', '장시작 20분 전입니다.'))
            elif current == '085000':
                self.kwzservQ.put(('sound', '장시작 10분 전입니다.'))
            elif current == '085500':
                self.kwzservQ.put(('sound', '장시작 5분 전입니다.'))
            elif current == '085900':
                self.kwzservQ.put(('sound', '장시작 1분 전입니다.'))
            elif current == '085930':
                self.kwzservQ.put(('sound', '장시작 30초 전입니다.'))
            elif current == '085940':
                self.kwzservQ.put(('sound', '장시작 20초 전입니다.'))
            elif current == '085950':
                self.kwzservQ.put(('sound', '장시작 10초 전입니다.'))
            elif current == '090000':
                self.kwzservQ.put(('sound', f"{self.dict_strg['당일날짜'][:4]}년 {self.dict_strg['당일날짜'][4:6]}월 "
                                            f"{self.dict_strg['당일날짜'][6:]}일 장이 시작되었습니다."))
            elif current == '152000':
                self.kwzservQ.put(('sound', '장마감 10분 전입니다.'))
            elif current == '152500':
                self.kwzservQ.put(('sound', '장마감 5분 전입니다.'))
            elif current == '152900':
                self.kwzservQ.put(('sound', '장마감 1분 전입니다.'))
            elif current == '152930':
                self.kwzservQ.put(('sound', '장마감 30초 전입니다.'))
            elif current == '152940':
                self.kwzservQ.put(('sound', '장마감 20초 전입니다.'))
            elif current == '152950':
                self.kwzservQ.put(('sound', '장마감 10초 전입니다.'))
            elif current == '153000':
                self.kwzservQ.put(('sound', f"{self.dict_strg['당일날짜'][:4]}년 {self.dict_strg['당일날짜'][4:6]}월 "
                                            f"{self.dict_strg['당일날짜'][6:]}일 장이 종료되었습니다."))

    # noinspection PyUnusedLocal
    def OnReceiveChejanData(self, gubun, itemcnt, fidlist):
        if self.dict_set['주식모의투자']:
            return

        if gubun == '0':
            try:
                종목코드 = self.kw.GetChejanData(9001).strip('A')
                종목명 = self.dict_info[종목코드]['종목명']
                주문상태 = self.kw.GetChejanData(913)
                주문구분 = self.kw.GetChejanData(905)[1:]
                주문가격 = int(self.kw.GetChejanData(901))
                주문수량 = int(self.kw.GetChejanData(900))
                미체결수량 = int(self.kw.GetChejanData(902))
                주문번호 = self.kw.GetChejanData(9203)
                최우선매도호가 = abs(int(self.kw.GetChejanData(27)))
                주문시간 = self.dict_strg['당일날짜'] + self.kw.GetChejanData(908)
            except Exception as e:
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - OnReceiveChejanData 0 {e}')))
            else:
                try:
                    체결가격 = int(self.kw.GetChejanData(914))
                    체결수량 = int(self.kw.GetChejanData(915))
                except:
                    체결가격 = 0
                    체결수량 = 0
                self.UpdateChejanData(종목코드, 종목명, 최우선매도호가, 주문상태, 주문구분, 주문수량, 체결수량, 미체결수량, 주문가격, 체결가격, 주문시간, 주문번호)

    @error_decorator
    def UpdateChejanData(self, 종목코드, 종목명, 최우선매도호가, 주문상태, 주문구분, 주문수량, 체결수량, 미체결수량, 주문가격, 체결가격, 주문시간, 주문번호):
        index = self.GetIndex()

        if 주문상태 == '접수' and 주문구분 in ('매수', '매도'):
            cancel_time = timedelta_sec(self.dict_set['주식매수취소시간초' if 주문구분 == '매수' else '주식매도취소시간초'])
            if 주문구분 == '매수':
                self.dict_intg['추정예수금'] -= 주문수량 * (주문가격 if '지정가' in self.dict_set['주식매수주문구분'] else 최우선매도호가)
                self.dict_order[주문구분][종목코드] = [cancel_time, 0, 주문가격, GetHogaunit(종목코드 in self.tuple_kosd, 주문가격, self.int_hgtime)]
            else:
                self.dict_order[주문구분][종목코드] = [cancel_time, 0, 주문가격, GetHogaunit(종목코드 in self.tuple_kosd, 주문가격, self.int_hgtime)]
            self.UpdateChegeollist(index, 종목코드, 종목명, f'{주문구분} {주문상태}', 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}{주문상태}] {종목명} | {주문가격} | {주문수량}')))

        elif 주문상태 == '접수불가':
            self.UpdateChegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

        elif 주문상태 == '체결' and 주문구분 in ('매수', '매도'):
            if 주문구분 == '매수':
                if 종목코드 in self.df_jg.index:
                    보유수량 = self.df_jg['보유수량'][종목코드] + 체결수량
                    매입금액 = self.df_jg['매입금액'][종목코드] + 체결수량 * 체결가격
                    매입가 = int(round(매입금액 / 보유수량))
                    평가금액, 수익금, 수익율 = GetKiwoomPgSgSp(매입금액, 보유수량 * 체결가격)
                    columns = ['매입가', '현재가', '수익율', '평가손익', '매입금액', '평가금액', '보유수량', '매수시간']
                    self.df_jg.loc[종목코드, columns] = 매입가, 체결가격, 수익율, 수익금, 매입금액, 평가금액, 보유수량, 주문시간
                else:
                    보유수량 = 체결수량
                    매입금액 = 체결수량 * 체결가격
                    매입가 = 체결가격
                    평가금액, 수익금, 수익율 = GetKiwoomPgSgSp(매입금액, 보유수량 * 체결가격)
                    self.df_jg.loc[종목코드] = 종목명, 매입가, 체결가격, 수익율, 수익금, 매입금액, 평가금액, 보유수량, 0, 0, 주문시간

                if 미체결수량 == 0:
                    self.df_jg.loc[종목코드, '분할매수횟수'] = self.df_jg['분할매수횟수'][종목코드] + 1
                    if 종목코드 in self.dict_order[주문구분].keys():
                        del self.dict_order[주문구분][종목코드]

            else:
                if 종목코드 not in self.df_jg.index:
                    return

                보유수량 = self.df_jg['보유수량'][종목코드] - 체결수량
                매입가 = self.df_jg['매입가'][종목코드]
                if 보유수량 != 0:
                    매입금액 = 매입가 * 보유수량
                    평가금액, 수익금, 수익율 = GetKiwoomPgSgSp(매입금액, 보유수량 * 체결가격)
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
                평가금액, 수익금, 수익율 = GetKiwoomPgSgSp(매입금액, 체결수량 * 체결가격)
                if -100 < 수익율 < 100: self.UpdateTradelist(index, 종목명, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간)
                if 수익율 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['주식매수금지손절간격초'])

            columns = ['매입가', '현재가', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수']
            self.df_jg[columns] = self.df_jg[columns].astype(int)
            self.df_jg.sort_values(by=['매입금액'], ascending=False, inplace=True)
            self.PutJangoDF()

            if 미체결수량 == 0: self.PutOrderComplete(주문구분 + '완료', 종목코드)
            self.UpdateChegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            if 주문구분 == '매수':
                self.dict_intg['예수금'] -= 체결수량 * 체결가격
                if self.dict_set['주식모의투자']:
                    self.dict_intg['추정예수금'] -= 체결수량 * 체결가격
            else:
                self.dict_intg['예수금'] += 매입금액 + 수익금
                self.dict_intg['추정예수금'] += 매입금액 + 수익금

            self.kwzservQ.put(('query', ('거래디비', self.df_jg, 's_jangolist', 'replace')))
            if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', f'{종목명} {체결수량}주를 {주문구분}하였습니다'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}{주문상태}] {종목명} | {체결가격} | {체결수량}')))

        elif 주문상태 == '확인' and 주문구분 in ('매수정정', '매도정정', '매수취소', '매도취소'):
            주문구분_ = 주문구분.replace('정정', '').replace('취소', '')
            if 주문구분 == '매수정정':
                fix_count = self.dict_order[주문구분_][종목코드][1] + 1
                self.dict_order[주문구분_][종목코드] = [timedelta_sec(self.dict_set['주식매수취소시간초']), fix_count, 주문가격, GetHogaunit(종목코드 in self.tuple_kosd, 주문가격, self.int_hgtime)]
            elif 주문구분 == '매도정정':
                fix_count = self.dict_order[종목코드][1] + 1
                self.dict_order[주문구분_][종목코드] = [timedelta_sec(self.dict_set['주식매도취소시간초']), fix_count, 주문가격, GetHogaunit(종목코드 in self.tuple_kosd, 주문가격, self.int_hgtime)]
            else:
                if 주문구분 == '매수취소':
                    self.dict_intg['추정예수금'] += 미체결수량 * 주문가격
                    if 종목코드 in self.dict_order[주문구분_].keys():
                        del self.dict_order[주문구분_][종목코드]
                elif 종목코드 in self.dict_order[주문구분_].keys():
                    del self.dict_order[주문구분_][종목코드]
                self.PutOrderComplete(주문구분, 종목코드)

            self.UpdateChegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', f'{종목명} {주문수량}주를 {주문구분}하였습니다'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {주문가격} | {주문수량}')))

        self.sreceivQ.put(('잔고목록', tuple(self.df_jg.index)))
        self.sreceivQ.put(('주문목록', self.GetOrderCodeList()))

    def UpdateTradelist(self, index, 종목명, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간):
        self.df_td.loc[index] = 종목명, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간
        self.kwzservQ.put(('window', (ui_num['S거래목록'], self.df_td[::-1])))
        df = pd.DataFrame([[종목명, 매입금액, 평가금액, 체결수량, 수익율, 수익금, 주문시간]], columns=columns_td, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 's_tradelist', 'append')))
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
            self.kwzservQ.put(('live', ('주식', data_list)))

    def UpdateChegeollist(self, index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호):
        self.dict_info[종목코드]['최종거래시간'] = timedelta_sec(self.dict_set['주식매수금지간격초'])
        self.df_cj.loc[index] = 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호
        self.kwzservQ.put(('window', (ui_num['S체결목록'], self.df_cj[::-1])))
        df = pd.DataFrame([[종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]], columns=columns_cj, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 's_chegeollist', 'append')))

    def UpdateTotaljango(self):
        if len(self.df_jg) > 0:
            총평가손익 = self.df_jg['평가손익'].sum()
            총매입금액 = self.df_jg['매입금액'].sum()
            총평가금액 = self.df_jg['평가금액'].sum()
            잔고수량 = len(self.df_jg)
            총수익율 = round(총평가손익 / 총매입금액 * 100, 2)
            추정예탁자산 = self.dict_intg['예수금'] + 총평가금액
            self.df_tj.loc[self.dict_strg['당일날짜']] = 추정예탁자산, self.dict_intg['예수금'], 잔고수량, 총수익율, 총평가손익, 총매입금액, 총평가금액
        else:
            self.df_tj.loc[self.dict_strg['당일날짜']] = self.dict_intg['예수금'], self.dict_intg['예수금'], 0, 0.0, 0, 0, 0

        총평가손익 = self.df_jg['평가손익'].sum() + self.df_td['수익금'].sum()
        if self.dict_set['주식손실중지']:
            기준손실금 = self.dict_intg['추정예탁자산'] * self.dict_set['주식손실중지수익율'] / 100
            if 기준손실금 < -총평가손익: self.StrategyStop()
        if self.dict_set['주식수익중지']:
            기준수익금 = self.dict_intg['추정예탁자산'] * self.dict_set['주식수익중지수익율'] / 100
            if 기준수익금 < 총평가손익: self.StrategyStop()

        if self.dict_set['주식투자금고정']:
            종목당투자금 = int(self.dict_set['주식투자금'] * 1_000_000)
        else:
            if '시장가' in self.dict_set['주식매수주문구분']:
                종목당투자금 = int((self.dict_intg['추정예탁자산'] - self.dict_intg['추정예탁자산'] / self.dict_set['주식최대매수종목수'] * 0.3) / self.dict_set['주식최대매수종목수'])
            else:
                종목당투자금 = int(self.dict_intg['추정예탁자산'] * 0.98 / self.dict_set['주식최대매수종목수'])

        if self.dict_intg['종목당투자금'] != 종목당투자금:
            self.dict_intg['종목당투자금'] = 종목당투자금
            for q in self.sstgQs:
                q.put(('종목당투자금', self.dict_intg['종목당투자금']))

        self.kwzservQ.put(('window', (ui_num['S잔고목록'], self.df_jg)))
        self.kwzservQ.put(('window', (ui_num['S잔고평가'], self.df_tj)))

    def PutJangoDF(self):
        if not self.dict_bool['프로세스종료']:
            data = ('잔고목록', self.df_jg)
            for q in self.sstgQs:
                q.put(data)

    def StrategyStop(self):
        for q in self.sstgQs:
            q.put('매수전략중지')
        self.JangoCheongsan('수동')

    def PutOrderComplete(self, cmsg, code):
        self.sstgQs[self.dict_sgbn[code]].put((cmsg, code))

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.')))

    def GetOrderCodeList(self):
        return tuple(self.dict_order['매수'].keys()) + tuple(self.dict_order['매도'].keys())

    def GetMichegeolDF(self, name, gubun):
        return self.df_cj[(self.df_cj['종목명'] == name) & ((self.df_cj['주문구분'] == gubun) | (self.df_cj['주문구분'] == f'{gubun} 접수'))]

    def GetIndex(self):
        index = str_ymdhmsf()
        if index in self.df_cj.index:
            while index in self.df_cj.index:
                index = str(int(index) + 1)
        return index
