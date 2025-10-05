import os
import sys
import time
import sqlite3
import pandas as pd
from threading import Thread
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num, columns_cj, columns_td, DB_TRADELIST, DICT_SET, columns_jg
from utility.static import now, timedelta_sec, str_hms, roundfigure_lower, roundfigure_upper, GetKiwoomPgSgSp, \
    GetHogaunit, error_decorator, str_ymd, str_ymdhms, str_ymdhmsf, dt_hms, float_hmsf, get_logger


class PutDictjango(Thread):
    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        floathmsf = float_hmsf()
        while True:
            if float_hmsf() > floathmsf + 0.5:
                floathmsf = float_hmsf()
                data = ('잔고목록', self.main.dict_jg.copy())
                for q in self.main.sstgQs:
                    q.put(data)
            time.sleep(0.01)


class Scheduler(Thread):
    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        inthms = int(str_hms())
        while True:
            if int(str_hms()) > inthms:
                inthms = int(str_hms())
                if self.main.dict_set['주식타임프레임'] and inthms < self.main.dict_set['주식전략종료시간']:
                    self.main.straderQ.put('OrderTimeControl')
                if self.main.jgcs_time < inthms and not self.main.dict_bool['주식잔고청산']:
                    self.main.straderQ.put('JangoCheongsan')
                self.main.straderQ.put('UpdateTotaljango')
            time.sleep(0.01)


class KiwoomTrader:
    def __init__(self, qlist):
        """
        self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQs, self.kiwoomQ
                0            1              2             3           4
        """
        self.kwzservQ   = qlist[0]
        self.sreceivQ   = qlist[1]
        self.straderQ   = qlist[2]
        self.sstgQs     = qlist[3]
        self.kiwoomQ    = qlist[4]
        self.dict_set   = DICT_SET

        self.logger     = get_logger(self.__class__.__name__)

        self.dict_cj    = {}  # 체결목록
        self.dict_jg    = {}  # 잔고목록
        self.dict_tj    = {}  # 잔고평가
        self.dict_td    = {}  # 거래목록
        self.dict_tt    = {}  # 평가손익
        self.dict_info  = {}
        self.dict_curc  = {}
        self.dict_sgbn  = {}
        self.dict_order = {
            '매수': {},
            '매도': {}
        }
        self.dict_intg  = {
            '예수금': 0,
            '추정예수금': 0,
            '추정예탁자산': 0,
            '종목당투자금': 0
        }
        self.dict_bool  = {
            '주식잔고청산': False
        }
        self.거래구분 = {
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
        self.주문유형 = {
            '매수': 1,
            '매도': 2,
            '매수취소': 3,
            '매도취소': 4,
            '매수정정': 5,
            '매도정정': 6
        }

        self.str_account = ''
        self.str_today   = str_ymd()
        self.int_hgtime  = int(str_ymdhms())
        self.jgcs_time   = self.get_jgcs_time()
        self.tuple_kosd  = None

        self.put_dict_jango = PutDictjango(self)
        self.put_dict_jango.daemon = True
        self.put_dict_jango.start()

        self.scheduler = Scheduler(self)
        self.scheduler.daemon = True
        self.scheduler.start()

        if self.dict_set['트레이더프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.LoadDatabase()
        self.Mainloop()

    def get_jgcs_time(self):
        return int(str_hms(timedelta_sec(-120, dt_hms(str(self.dict_set['주식전략종료시간'])))))

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        df_cj = pd.read_sql(f"SELECT * FROM s_chegeollist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        df_td = pd.read_sql(f"SELECT * FROM s_tradelist WHERE 체결시간 LIKE '{self.str_today}%'", con).set_index('index')
        if len(df_cj) > 0:
            self.dict_cj = df_cj.to_dict('index')
            self.kwzservQ.put(('window', (ui_num['S체결목록'], df_cj[::-1])))
        if len(df_td) > 0:
            self.dict_td = df_td.to_dict('index')
            self.kwzservQ.put(('window', (ui_num['S거래목록'], df_td[::-1])))
        if self.dict_set['주식모의투자']:
            df_jg = pd.read_sql('SELECT * FROM s_jangolist', con).set_index('index')
            if len(df_jg) > 0:
                self.dict_jg = df_jg.to_dict('index')
                self.sreceivQ.put(('잔고목록', tuple(self.dict_jg)))
        con.close()
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 정보 불러오기 완료')))

    def Mainloop(self):
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더 시작')))
        self.logger.info('트레이더 시작 완료')
        while True:
            data = self.straderQ.get()
            if type(data) == tuple:
                if len(data) in (7, 8):
                    self.CheckOrder(data)
                else:
                    self.UpdateTuple(data)
            elif type(data) == str:
                self.UpdateString(data)

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '체잔통보':
            self.UpdateChejanData(data)
        elif gubun == '잔고갱신':
            self.UpdateJango(data)
        elif gubun == '주문확인':
            code, c = data
            self.dict_curc[code] = c
            self.OrderTimeControl(code)
        elif gubun == '관심진입':
            if data in self.dict_order['매도']:
                self.CancelOrder(data, '매도')
        elif gubun == '관심이탈':
            if data in self.dict_order['매수']:
                self.CancelOrder(data, '매수')
        elif gubun == '증거금부족':
            self.PutOrderComplete('매수취소', data)
        elif gubun == '잔고조회':
            self.UpdateYesugm(data)
        elif gubun == '설정변경':
            self.dict_set = data
            self.jgcs_time = self.get_jgcs_time()
        elif gubun == '종목정보':
            self.dict_sgbn, dict_name = data
            dummy_time = timedelta_sec(-3600)
            for code in dict_name:
                self.dict_info[code] = {
                    '종목명': dict_name[code],
                    '시드부족시간': dummy_time,
                    '최종거래시간': dummy_time,
                    '손절거래시간': dummy_time
                }

    def UpdateString(self, data):
        if data == 'UpdateTotaljango':
            self.UpdateTotaljango()
        elif data == 'OrderTimeControl':
            self.OrderTimeControl()
        elif data == 'JangoCheongsan':
            self.JangoCheongsan('자동')
        elif data == '체결목록':
            df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
            self.kwzservQ.put(('tele', df_cj)) if len(df_cj) > 0 else self.kwzservQ.put(('tele', '현재는 주식 체결목록이 없습니다.'))
        elif data == '거래목록':
            df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
            self.kwzservQ.put(('tele', df_td)) if len(df_td) > 0 else self.kwzservQ.put(('tele', '현재는 주식 거래목록이 없습니다.'))
        elif data == '잔고평가':
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.kwzservQ.put(('tele', df_jg)) if len(df_jg) > 0 else self.kwzservQ.put(('tele', '현재는 주식 잔고목록이 없습니다.'))
        elif data == '잔고청산':
            self.JangoCheongsan('수동')
        elif data == '프로파일링결과':
            self.pr.print_stats(sort='cumulative')
        elif data == '프로세스종료':
            self.SysExit()

    def CheckOrder(self, data):
        if len(data) == 7:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산 = data
            수동주문유형 = None
        else:
            주문구분, 종목코드, 종목명, 주문가격, 주문수량, 시그널시간, 잔고청산, 수동주문유형 = data

        잔고없음 = 종목코드 not in self.dict_jg
        매수주문중 = 종목코드 in self.dict_order['매수']
        매도주문중 = 종목코드 in self.dict_order['매도']

        원주문번호 = ''
        주문취소 = False
        현재시간 = now()
        if 잔고청산:
            if 잔고없음 or 매도주문중: 주문취소 = True
        elif 주문구분 == '매수':
            inthms = int(str_hms())
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
            elif self.dict_intg['추정예수금'] < 주문수량 * 주문가격:
                if 현재시간 > self.dict_info[종목코드]['시드부족시간']:
                    self.CreateOrder('시드부족', 종목코드, 종목명, 주문가격, 주문수량, '', 시그널시간, 잔고청산, None)
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
        elif self.dict_bool['주식잔고청산']:
            주문취소 = True

        if 주문취소:
            if '취소' not in 주문구분:
                self.PutOrderComplete(f'{주문구분}취소', 종목코드)
        else:
            if 잔고청산 and 주문구분 in ('매수', '매도'):
                self.PutOrderComplete(f'{주문구분}주문', 종목코드)

            if 주문구분 == '매수':
                if self.dict_set['주식매도취소매수시그널'] and 매도주문중:
                    self.CancelOrder(종목코드, 주문구분)
            elif 주문구분 == '매도':
                if self.dict_set['주식매수취소매도시그널'] and 매수주문중:
                    self.CancelOrder(종목코드, 주문구분)

            if 주문수량 > 0:
                self.CreateOrder(주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 수동주문유형)
            else:
                self.PutOrderComplete(f'{주문구분}취소', 종목코드)

    def PutOrderComplete(self, cmsg, code):
        self.sstgQs[self.dict_sgbn[code]].put((cmsg, code))

    def CreateOrder(self, 주문구분, 종목코드, 종목명, 주문가격, 주문수량, 원주문번호, 시그널시간, 잔고청산, 수동주문유형):
        주문유형 = self.주문유형[주문구분]
        주문취소 = False

        if 잔고청산:
            거래구분 = '03'
        elif '매수' in 주문구분:
            거래구분 = self.거래구분[self.dict_set['주식매수주문구분']] if 수동주문유형 is None else self.거래구분[수동주문유형]
        else:
            거래구분 = self.거래구분[self.dict_set['주식매도주문구분']] if 수동주문유형 is None else self.거래구분[수동주문유형]

        if 잔고청산:
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
                    data = (종목코드, 종목명, 주문가격, '접수불가', 주문구분, 주문수량, 0, 주문수량, 주문가격, 0, ct, 원주문번호)
                else:
                    data = (종목코드, 종목명, 주문가격, '체결', 주문구분, 주문수량, 주문수량, 0, 주문가격, 주문가격, ct, 원주문번호)
                self.UpdateChejanData(data)
            else:
                data = [주문구분, 0, self.str_account, 주문유형, 종목코드, int(주문수량), int(주문가격), 거래구분, 원주문번호, 종목명, 시그널시간]
                self.kiwoomQ.put(data)

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.')))

    def OrderTimeControl(self, code_=None):
        cancel_list = []
        modify_list = []

        for gubun in self.dict_order:
            for code in self.dict_order[gubun]:
                if code_ is None or code == code_:
                    order_info = self.dict_order[gubun][code]
                    if gubun == '매수':
                        if self.dict_set['주식매수취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    else:
                        if self.dict_set['주식매도취소시간'] and now() > order_info[0]:
                            cancel_list.append((code, gubun))
                    if gubun == '매수':
                        if order_info[1] < self.dict_set['주식매수정정횟수'] and code in self.dict_curc and \
                                self.dict_curc[code] >= order_info[2] + order_info[3] * self.dict_set['주식매수정정호가차이']:
                            modify_list.append((code, gubun))
                    else:
                        if order_info[1] < self.dict_set['주식매도정정횟수'] and code in self.dict_curc and \
                                self.dict_curc[code] <= order_info[2] - order_info[3] * self.dict_set['주식매도정정호가차이']:
                            modify_list.append((code, gubun))

        if cancel_list:
            for code, gubun in cancel_list:
                self.CancelOrder(code, gubun)
        if modify_list:
            for code, gubun in modify_list:
                self.ModifyOrder(code, gubun)

    def GetChejanLastValue(self, name, gubun):
        return [v for v in self.dict_cj.values() if v['종목명'] == name and (v['주문구분'] == gubun or v['주문구분'] == f'{gubun} 접수')][-1]

    def CancelOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        last_value = self.GetChejanLastValue(종목명, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
            if 미체결수량 > 0:
                현재시간 = now()
                주문번호 = last_value['주문번호']
                self.CreateOrder(f'{주문구분}취소', 종목코드, 종목명, 0, 미체결수량, 주문번호, 현재시간, False, None)

    def ModifyOrder(self, 종목코드, 주문구분):
        종목명 = self.dict_info[종목코드]['종목명']
        last_value = self.GetChejanLastValue(종목명, 주문구분)
        if last_value:
            미체결수량 = last_value['미체결수량']
            if 미체결수량 > 0:
                if 주문구분 == '매수':
                    주문가격 = self.dict_curc[종목코드] - self.dict_order[주문구분][종목코드][3] * self.dict_set[f'주식{주문구분}정정호가']
                else:
                    주문가격 = self.dict_curc[종목코드] + self.dict_order[주문구분][종목코드][3] * self.dict_set[f'주식{주문구분}정정호가']

                현재시간 = now()
                주문번호 = last_value['주문번호']
                self.CreateOrder(f'{주문구분}정정', 종목코드, 종목명, 주문가격, 미체결수량, 주문번호, 현재시간, False, None)

    def UpdateJango(self, data):
        종목코드, 현재가 = data
        self.dict_curc[종목코드] = 현재가
        try:
            # ['종목명', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
            if 현재가 != self.dict_jg[종목코드]['현재가']:
                매입금액 = self.dict_jg[종목코드]['매입금액']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                평가금액, 평가손익, 수익률 = GetKiwoomPgSgSp(매입금액, 보유수량 * 현재가)
                self.dict_jg[종목코드].update({
                    '현재가': 현재가,
                    '수익률': 수익률,
                    '평가손익': 평가손익,
                    '평가금액': 평가금액
                })
        except:
            pass

    def JangoCheongsan(self, gubun):
        self.dict_bool['주식잔고청산'] = True

        for 주문구분 in self.dict_order:
            for 종목코드 in self.dict_order[주문구분]:
                self.CancelOrder(종목코드, 주문구분)

        if self.dict_jg and (gubun == '수동' or self.dict_set['주식잔고청산']):
            if gubun == '수동':
                self.kwzservQ.put(('tele', '주식 잔고청산 주문을 전송합니다.'))
            for 종목코드 in self.dict_jg:
                종목명 = self.dict_jg[종목코드]['종목명']
                현재가 = self.dict_jg[종목코드]['현재가']
                보유수량 = self.dict_jg[종목코드]['보유수량']
                if self.dict_set['주식모의투자']:
                    data = (종목코드, 종목명, 현재가, '체결', '매도', 보유수량, 보유수량, 0, 현재가, 현재가, str_ymdhms(), '')
                    self.UpdateChejanData(data)
                else:
                    self.CheckOrder(('매도', 종목코드, 종목명, 현재가, 보유수량, now(), True))
            if self.dict_set['주식알림소리']:
                self.kwzservQ.put(('sound', f'주식 잔고청산 주문을 전송하였습니다.'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 실행 알림 - 주식 잔고청산 주문 완료')))
        elif not self.dict_jg and gubun == '수동':
            self.kwzservQ.put(('tele', '현재는 주식 보유종목이 없습니다.'))

    def UpdateYesugm(self, data):
        yesugm, jasan, dict_jg = data
        if not self.dict_set['주식모의투자']:
            self.dict_intg.update({
                '예수금': yesugm,
                '추정예수금': yesugm * 2,
                '추정예탁자산': jasan
            })
            if dict_jg: self.dict_jg = dict_jg
        else:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql('SELECT * FROM s_tradelist', con)
            con.close()
            총수익금 = df['수익금'].sum()
            총매입금액 = sum([v['매입금액'] for v in self.dict_jg.values()]) if self.dict_jg else 0
            예수금 = 100_000_000 - 총매입금액 + 총수익금
            if 예수금 < 100_000_000: 예수금 = 100_000_000
            총평가금액 = sum([v['평가금액'] for v in self.dict_jg.values()]) if self.dict_jg else 0
            추정예탁자산 = 예수금 + 총평가금액
            self.dict_intg.update({
                '예수금': 예수금,
                '추정예수금': 예수금 * 2,
                '추정예탁자산': 추정예탁자산
            })

    def SysExit(self):
        self.SaveDayData()
        time.sleep(5)
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 트레이더 종료')))

    def SaveDayData(self):
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM s_totaltradelist WHERE `index` = '{self.str_today}'", con)
        con.close()
        if len(df) == 0 and self.dict_tt:
            df = pd.DataFrame.from_dict(self.dict_tt, orient='index')
            self.kwzservQ.put(('query', ('거래디비', df, 's_totaltradelist', 'append')))
            if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', '일별실현손익를 저장하였습니다.'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 일별실현손익 저장 완료')))

    def GetIndex(self):
        index = str_ymdhmsf()
        if index in self.dict_cj:
            while index in self.dict_cj:
                index = str(int(index) + 1)
        return index

    @error_decorator
    def UpdateChejanData(self, data):
        종목코드, 종목명, 최우선매도호가, 주문상태, 주문구분, 주문수량, 체결수량, 미체결수량, 주문가격, 체결가격, 주문시간, 주문번호 = data
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
                # ['종목명', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                if 종목코드 in self.dict_jg:
                    보유수량 = self.dict_jg[종목코드]['보유수량'] + 체결수량
                    매입금액 = self.dict_jg[종목코드]['매입금액'] + 체결수량 * 체결가격
                    매입가 = int(round(매입금액 / 보유수량))
                    평가금액, 수익금, 수익률 = GetKiwoomPgSgSp(매입금액, 보유수량 * 체결가격)
                    self.dict_jg[종목코드].update({
                        '매입가': 매입가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '매수시간': 주문시간
                    })
                else:
                    보유수량 = 체결수량
                    매입금액 = 체결수량 * 체결가격
                    매입가 = 체결가격
                    평가금액, 수익금, 수익률 = GetKiwoomPgSgSp(매입금액, 보유수량 * 체결가격)
                    self.dict_jg[종목코드] = {
                        '종목명': 종목명,
                        '매입가': 매입가,
                        '현재가': 체결가격,
                        '수익률': 수익률,
                        '평가손익': 수익금,
                        '매입금액': 매입금액,
                        '평가금액': 평가금액,
                        '보유수량': 보유수량,
                        '분할매수횟수': 0,
                        '분할매도횟수': 0,
                        '매수시간': 주문시간
                    }

                if 미체결수량 == 0:
                    self.dict_jg[종목코드]['분할매수횟수'] += 1
                    if 종목코드 in self.dict_order[주문구분]:
                        del self.dict_order[주문구분][종목코드]

            else:
                if 종목코드 not in self.dict_jg: return
                보유수량 = self.dict_jg[종목코드]['보유수량'] - 체결수량
                매입가 = self.dict_jg[종목코드]['매입가']
                if 보유수량 != 0:
                    매입금액 = 매입가 * 보유수량
                    평가금액, 수익금, 수익률 = GetKiwoomPgSgSp(매입금액, 보유수량 * 체결가격)
                    # ['종목명', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
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

                매입금액 = 매입가 * 체결수량
                평가금액, 수익금, 수익률 = GetKiwoomPgSgSp(매입금액, 체결수량 * 체결가격)
                if -100 < 수익률 < 100: self.UpdateTradelist(index, 종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간)
                if 수익률 < 0: self.dict_info[종목코드]['손절거래시간'] = timedelta_sec(self.dict_set['주식매수금지손절간격초'])

            sorted_items = sorted(self.dict_jg.items(), key=lambda x: x[1]['매입금액'], reverse=True)
            self.dict_jg = {k: v for k, v in sorted_items}

            if 미체결수량 == 0: self.PutOrderComplete(주문구분 + '완료', 종목코드)
            self.UpdateChegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            if 주문구분 == '매수':
                self.dict_intg['예수금'] -= 체결수량 * 체결가격
                if self.dict_set['주식모의투자']:
                    self.dict_intg['추정예수금'] -= 체결수량 * 체결가격
            else:
                self.dict_intg['예수금'] += 매입금액 + 수익금
                self.dict_intg['추정예수금'] += 매입금액 + 수익금

            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
            self.kwzservQ.put(('query', ('거래디비', df_jg, 's_jangolist', 'replace')))
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
                    if 종목코드 in self.dict_order[주문구분_]:
                        del self.dict_order[주문구분_][종목코드]
                elif 종목코드 in self.dict_order[주문구분_]:
                    del self.dict_order[주문구분_][종목코드]
                self.PutOrderComplete(주문구분, 종목코드)

            self.UpdateChegeollist(index, 종목코드, 종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 주문시간, 주문가격, 주문번호)

            if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', f'{종목명} {주문수량}주를 {주문구분}하였습니다'))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [{주문구분}] {종목명} | {주문가격} | {주문수량}')))

        self.sreceivQ.put(('잔고목록', tuple(self.dict_jg)))
        self.sreceivQ.put(('주문목록', self.GetOrderCodeList()))

    def GetOrderCodeList(self):
        return tuple(self.dict_order['매수']) + tuple(self.dict_order['매도'])

    def UpdateTradelist(self, index, 종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간):
        # ['종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
        self.dict_td[index] = {
            '종목명': 종목명,
            '매수금액': 매입금액,
            '매도금액': 평가금액,
            '주문수량': 체결수량,
            '수익률': 수익률,
            '수익금': 수익금,
            '체결시간': 주문시간
        }
        df_td = pd.DataFrame.from_dict(self.dict_td, orient='index')
        self.kwzservQ.put(('window', (ui_num['S거래목록'], df_td[::-1])))
        df = pd.DataFrame([[종목명, 매입금액, 평가금액, 체결수량, 수익률, 수익금, 주문시간]], columns=columns_td, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 's_tradelist', 'append')))
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        거래횟수 = len(set([(v['종목명'], v['체결시간']) for v in self.dict_td.values()]))
        총매수금액 = sum([v['매수금액'] for v in self.dict_td.values()])
        총매도금액 = sum([v['매도금액'] for v in self.dict_td.values()])
        총수익금액 = sum([v['수익금'] for v in self.dict_td.values() if v['수익금'] >= 0])
        총손실금액 = sum([v['수익금'] for v in self.dict_td.values() if v['수익금'] < 0])
        수익금합계 = sum([v['수익금'] for v in self.dict_td.values()])
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
        self.kwzservQ.put(('window', (ui_num['S실현손익'], df_tt)))

        if not first:
            self.kwzservQ.put(('tele', f'총매수금액 {총매수금액:,.0f}, 총매도금액 {총매도금액:,.0f}, 수익 {총수익금액:,.0f}, 손실 {총손실금액:,.0f}, 수익금합계 {수익금합계:,.0f}'))

        if self.dict_set['스톰라이브']:
            수익률 = round(수익금합계 / 총매수금액 * 100, 2)
            data_list = [거래횟수, 총매수금액, 총매도금액, 총수익금액, 총손실금액, 수익률, 수익금합계]
            self.kwzservQ.put(('live', ('주식', data_list)))

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
        sorted_items = sorted(self.dict_cj.items(), key=lambda x: x[0])
        self.dict_cj = {k: v for k, v in sorted_items}
        df_cj = pd.DataFrame.from_dict(self.dict_cj, orient='index')
        self.kwzservQ.put(('window', (ui_num['S체결목록'], df_cj[::-1])))
        df = pd.DataFrame([[종목명, 주문구분, 주문수량, 체결수량, 미체결수량, 체결가격, 체결시간, 주문가격, 주문번호]], columns=columns_cj, index=[index])
        self.kwzservQ.put(('query', ('거래디비', df, 's_chegeollist', 'append')))

    def UpdateTotaljango(self):
        # ['추정예탁자산', '추정예수금', '보유종목수', '수익률', '총평가손익', '총매입금액', '총평가금액']
        if self.dict_jg:
            총평가손익 = sum([v['평가손익'] for v in self.dict_jg.values()])
            총매입금액 = sum([v['매입금액'] for v in self.dict_jg.values()])
            총평가금액 = sum([v['평가금액'] for v in self.dict_jg.values()])
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

        잔고평가손익합계 = sum([v['평가손익'] for v in self.dict_jg.values()])
        거래수익금합계 = sum([v['수익금'] for v in self.dict_td.values()])
        총평가손익 = 잔고평가손익합계 + 거래수익금합계
        if self.dict_set['주식손실중지']:
            기준손실금 = self.dict_intg['추정예탁자산'] * self.dict_set['주식손실중지수익률'] / 100
            if 기준손실금 < -총평가손익: self.StrategyStop()
        if self.dict_set['주식수익중지']:
            기준수익금 = self.dict_intg['추정예탁자산'] * self.dict_set['주식수익중지수익률'] / 100
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

        if self.dict_jg:
            df_jg = pd.DataFrame.from_dict(self.dict_jg, orient='index')
        else:
            df_jg = pd.DataFrame(columns=columns_jg)
        df_tj = pd.DataFrame.from_dict(self.dict_tj, orient='index')
        self.kwzservQ.put(('window', (ui_num['S잔고목록'], df_jg)))
        self.kwzservQ.put(('window', (ui_num['S잔고평가'], df_tj)))

    def StrategyStop(self):
        self.logger.info('매수전략중지')
        for q in self.sstgQs:
            q.put('매수전략중지')
        self.JangoCheongsan('수동')
