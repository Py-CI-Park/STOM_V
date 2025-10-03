import os
import sys
import zmq
import sqlite3
import numpy as np
from future_kiwoom import *
from multiprocessing import Queue
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET, ui_num, DB_CODE_INFO, DB_FUTURE_MIN
from utility.static import now, qtest_qwait, str_hms_cme_from_str, opstarter_kill, now_cme, str_hms, str_ymd


class ZmqServ(QThread):
    def __init__(self, recvservQ):
        super().__init__()
        self.recvservQ = recvservQ
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.PUB)
        self.sock.bind('tcp://*:5777')

    def run(self):
        while True:
            msg, data = self.recvservQ.get()
            self.sock.send_string(msg, zmq.SNDMORE)
            self.sock.send_pyobj(data)


class Updater(QThread):
    signal = pyqtSignal(tuple)

    def __init__(self, sreceivQ):
        super().__init__()
        self.sreceivQ = sreceivQ

    def run(self):
        while True:
            data = self.sreceivQ.get()
            self.signal.emit(data)


class FutureReceiverTick:
    def __init__(self, qlist):
        """
        self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQ
                0            1              2             3
        """
        app = QApplication(sys.argv)

        self.kwzservQ = qlist[0]
        self.sreceivQ = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQ    = qlist[3]
        self.dict_set = DICT_SET

        if self.dict_set['리시버프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.dict_bool = {
            '리시버시작': False,
            '프로세스종료': False,
            '해선체결필드확인': False,
            '해선체결필드같음': False,
            '호가잔량필드확인': False,
            '호가잔량필드같음': False
        }
        self.dict_tmdt   = {}
        self.dict_hgbs   = {}
        self.dict_data   = {}
        self.dict_jgdt   = {}
        self.dict_info   = {}
        self.dict_mtop   = {}

        self.list_gsjm   = []
        self.real_codes  = []
        self.list_hgdt   = [0, 0, 0, 0]
        self.tuple_jango = ()
        self.tuple_order = ()

        self.str_tday    = str_ymd(now_cme())
        self.int_logt    = 0
        self.int_mtdt    = None
        self.hoga_code   = None
        self.chart_code  = None
        cme_hms          = int(str_hms(now_cme()))
        if self.dict_set['주식타임프레임']:
            self.test_mode = True if cme_hms > 103000 or cme_hms > self.dict_set['주식전략종료시간'] else False
        else:
            self.test_mode = True if cme_hms > 160000 or cme_hms > self.dict_set['주식전략종료시간'] else False
        self.recvservQ   = Queue()

        if self.dict_set['리시버공유'] == 1:
            self.zmqserver = ZmqServ(self.recvservQ)
            self.zmqserver.start()

        self.ft = Future(self, 'Receiver')
        self.FutureLogin()

        self.updater = Updater(self.sreceivQ)
        self.updater.signal.connect(self.UpdateTuple)
        self.updater.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.Scheduler)
        self.qtimer.start()

        app.exec_()

    def FutureLogin(self):
        self.ft.CommConnect()
        opstarter_kill()

        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료')))
        text = '해외선물 리시버를 시작하였습니다.'
        if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', text))
        self.kwzservQ.put(('tele', text))

        con = sqlite3.connect(DB_CODE_INFO)
        df = pd.read_sql('SELECT * FROM futureinfo', con).set_index('index')
        con.close()
        self.dict_info = df.to_dict('index')

        df_list = []
        # IDX:지수, CUR:통화, MTL:금속, ENG:에너지, CMD:농축산물, OPT:해외옵션, INT:금리
        for gubun in ['IDX', 'CUR']:
            df = self.ft.SearchDeposit(gubun)                       # 상품코드별 종목명, 위탁증거금, 유지증거금을 조회한다
            df_list.append(df)
            qtest_qwait(0.25)
        df = pd.concat(df_list)
        df = df[df['거래소'] == 'CME']
        df.set_index('종목코드', inplace=True)

        # 품목코드를 추가하려면 HTS에서 코드를 확인 후 여기에 추가하면 됩니다.
        # 추가된 품목코드가 지수나 통화 상품이 아닐 경우 상단 for문에서 상품코드를 추가해야합니다.
        # 현재는 CME 거래소에서 거래량이 많은 지수 및 코인 품목만 포함되어 있으며
        # 크루드오일 등 에너지는 CBOT 거래소의 실시간시세 이용료를 납부해야합니다.
        code_list = ['NQ', 'RTY', 'ES', 'EMD', 'MNQ', 'M2K', 'MES', 'BTC', 'MBT', 'ETH', 'MET']
        for code in code_list:
            str_codes = self.ft.GetGlobalFutureCodelist(code)       # 품목코드로 종목코드 목록을 조회한다
            df_gs = self.ft.SearchInterest(str_codes)               # 조회된 종목코드의 틱단위, 틱가치를 조회한다
            if len(df_gs) > 0:
                df_gs.sort_values(by=['누적거래량'], ascending=False, inplace=True)
                max_code  = df_gs['종목코드'].iloc[0]                # 조회된 종목코드 중 당일 거래량이 가장 많은 종목을 선택한다
                tick_unit = df['호가단위'][code]
                point_cnt = len(str(tick_unit).split('.')[1]) if '.' in str(tick_unit) else 5 if str(tick_unit) == '5e-05' else 0
                self.real_codes.append(max_code)
                self.dict_info[max_code] = {
                    '종목명': df['종목명'][code],
                    '위탁증거금': int(df['위탁증거금'][code] / 100),
                    '호가단위': tick_unit,
                    '틱가치': round(df['틱가치'][code] / 1000 / tick_unit, 2),
                    '소숫점자리수': point_cnt
                }
            qtest_qwait(0.25)

        dict_name = {code: self.dict_info[code]['종목명'] for code in self.dict_info.keys()}
        dict_code = {self.dict_info[code]['종목명']: code for code in self.dict_info.keys()}
        self.kwzservQ.put(('window', (ui_num['종목명데이터'], dict_name, dict_code)))
        self.straderQ.put(('종목정보', self.dict_info))
        self.sstgQ.put(('종목정보', self.dict_info))
        if self.dict_set['리시버공유'] == 1:
            self.recvservQ.put(('logininfo', self.dict_info))

        df = pd.DataFrame.from_dict(self.dict_info, orient='index')
        self.kwzservQ.put(('query', ('종목디비', df, 'futureinfo', 'replace')))

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data
        elif gubun == '호가종목코드':
            self.hoga_code = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '설정변경':
            self.dict_set = data
        elif gubun == '프로파일링결과':
            self.pr.print_stats(sort='cumulative')

    def Scheduler(self):
        if not self.dict_bool['리시버시작']:
            self.OperationRealreg()
        if not self.test_mode:
            inthms = int(str_hms(now_cme()))
            if self.dict_set['주식전략종료시간'] < inthms and not self.dict_bool['프로세스종료'] and self.dict_set['주식프로세스종료']:
                self.ReceiverProcKill()
            if 160500 < inthms and not self.dict_bool['프로세스종료']:
                self.ReceiverProcKill()

    def OperationRealreg(self):
        self.dict_bool['리시버시작'] = True
        self.ft.SetRealReg(self.real_codes)
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 실시간 등록 완료')))
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 시작')))

    def ReceiverProcKill(self):
        self.dict_bool['프로세스종료'] = True
        self.straderQ.put('프로세스종료')
        QTimer.singleShot(180 * 1000, self.SysExit)
        if self.dict_set['주식알림소리']:
            self.kwzservQ.put(('sound', '해외선물 시스템을 3분 후 종료합니다.'))

    def SysExit(self):
        if self.qtimer.isActive():  self.qtimer.stop()
        if self.updater.isRunning(): self.updater.quit()
        if self.dict_set['주식데이터저장']:
            self.SaveData()
        else:
            self.sstgQ.put('프로세스종료')
        qtest_qwait(5)
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료')))
        qtest_qwait(1)

    def SaveData(self):
        if self.dict_mtop:
            con = sqlite3.connect(DB_FUTURE_MIN)
            last_index = 0
            try:
                df = pd.read_sql(f'SELECT * FROM moneytop ORDER BY "index" DESC LIMIT 1', con)
                last_index = df['index'][0]
            except:
                pass
            df = {key: value for key, value in self.dict_mtop.items() if key > last_index}
            df = pd.DataFrame(df.values(), columns=['거래대금순위'], index=list(df.keys()))
            df.to_sql('moneytop', con, if_exists='append', chunksize=1000)
            con.close()
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 데이터수집목록 저장 완료')))

        self.sstgQ.put('데이터저장')

    def OnReceiveRealData(self, code, realtype, realdata):
        if self.dict_bool['프로세스종료']:
            return

        if realtype == '해외선물시세':
            try:
                if not self.dict_bool['해선체결필드확인']:
                    data = realdata.split(';')
                    if data[0]                             == self.ft.GetCommRealData(code, 20) and \
                            float(data[2])           == float(self.ft.GetCommRealData(code, 140)) and \
                            float(data[4])           == float(self.ft.GetCommRealData(code, 12)) and \
                            data[7]                        == self.ft.GetCommRealData(code, 15) and \
                            abs(float(data[9]))  == abs(float(self.ft.GetCommRealData(code, 16))) and \
                            abs(float(data[10])) == abs(float(self.ft.GetCommRealData(code, 17))) and \
                            abs(float(data[11])) == abs(float(self.ft.GetCommRealData(code, 18))) and \
                            float(data[5])           == float(self.ft.GetCommRealData(code, 27)) and \
                            float(data[6])           == float(self.ft.GetCommRealData(code, 28)):
                        self.dict_bool['해선체결필드같음'] = True
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 해선체결 필드값 같음')))
                    else:
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 해선체결 필드값이 다릅니다. 필드값 갱신요망!!')))
                    self.dict_bool['해선체결필드확인'] = True

                if self.dict_bool['해선체결필드같음']:
                    data  = realdata.split(';')
                    dt            = data[0]
                    c       = float(data[2])
                    per     = float(data[4])
                    v             = data[7]
                    o   = abs(float(data[9]))
                    h   = abs(float(data[10]))
                    low = abs(float(data[11]))
                    csp     = float(data[5])
                    cbp     = float(data[6])
                else:
                    dt            = self.ft.GetCommRealData(code, 20)
                    c             = self.ft.GetCommRealData(code, 10)
                    per     = float(self.ft.GetCommRealData(code, 12))
                    v             = self.ft.GetCommRealData(code, 15)
                    o   = abs(float(self.ft.GetCommRealData(code, 16)))
                    h   = abs(float(self.ft.GetCommRealData(code, 17)))
                    low = abs(float(self.ft.GetCommRealData(code, 18)))
                    csp     = float(self.ft.GetCommRealData(code, 27))
                    cbp     = float(self.ft.GetCommRealData(code, 28))

                cme_hms = str_hms_cme_from_str(dt)
                if not self.test_mode and ((not self.dict_set['주식타임프레임'] and int(cme_hms) < 90000) or (self.dict_set['주식타임프레임'] and int(cme_hms) < 93000)):
                    return
                dt = int(f'{self.str_tday}{cme_hms}')
            except:
                pass
            else:
                self.UpdateTickData(code, dt, c, o, h, low, per, v, csp, cbp)

        elif realtype == '해외선물호가':
            try:
                start = now()
                if not self.dict_bool['호가잔량필드확인']:
                    data = realdata.split(';')
                    if data[0]                             == self.ft.GetCommRealData(code, 21) and \
                            int(data[43])              == int(self.ft.GetCommRealData(code, 121)) and \
                            int(data[46])              == int(self.ft.GetCommRealData(code, 125)) and \
                            abs(float(data[35])) == abs(float(self.ft.GetCommRealData(code, 45))) and \
                            abs(float(data[27])) == abs(float(self.ft.GetCommRealData(code, 44))) and \
                            abs(float(data[19])) == abs(float(self.ft.GetCommRealData(code, 43))) and \
                            abs(float(data[11]))  == abs(float(self.ft.GetCommRealData(code, 42))) and \
                            abs(float(data[3]))  == abs(float(self.ft.GetCommRealData(code, 41))) and \
                            abs(float(data[7]))  == abs(float(self.ft.GetCommRealData(code, 51))) and \
                            abs(float(data[15])) == abs(float(self.ft.GetCommRealData(code, 52))) and \
                            abs(float(data[23])) == abs(float(self.ft.GetCommRealData(code, 53))) and \
                            abs(float(data[31])) == abs(float(self.ft.GetCommRealData(code, 54))) and \
                            abs(float(data[39])) == abs(float(self.ft.GetCommRealData(code, 55))) and \
                            int(data[36])              == int(self.ft.GetCommRealData(code, 65)) and \
                            int(data[28])              == int(self.ft.GetCommRealData(code, 64)) and \
                            int(data[20])              == int(self.ft.GetCommRealData(code, 63)) and \
                            int(data[12])               == int(self.ft.GetCommRealData(code, 62)) and \
                            int(data[4])               == int(self.ft.GetCommRealData(code, 61)) and \
                            int(data[8])               == int(self.ft.GetCommRealData(code, 71)) and \
                            int(data[16])              == int(self.ft.GetCommRealData(code, 72)) and \
                            int(data[24])              == int(self.ft.GetCommRealData(code, 73)) and \
                            int(data[32])              == int(self.ft.GetCommRealData(code, 74)) and \
                            int(data[40])              == int(self.ft.GetCommRealData(code, 75)):
                        self.dict_bool['호가잔량필드같음'] = True
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 실행 알림 - 해선호가잔량 필드값 같음')))
                    else:
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - 해선호가잔량 필드값이 다릅니다. 필드값 갱신요망!!')))
                    self.dict_bool['호가잔량필드확인'] = True

                if self.dict_bool['호가잔량필드같음']:
                    data = realdata.split(';')
                    dt = data[0]
                    hoga_tamount = (
                        int(data[43]), int(data[46])
                    )
                    hoga_seprice5 = abs(float(data[35]))
                    hoga_seprice = (
                        hoga_seprice5, hoga_seprice5, hoga_seprice5, hoga_seprice5, hoga_seprice5, hoga_seprice5,
                        abs(float(data[27])), abs(float(data[19])), abs(float(data[11])), abs(float(data[3]))
                    )
                    hoga_buprice5 = abs(float(data[39]))
                    hoga_buprice = (
                        abs(float(data[7])), abs(float(data[15])), abs(float(data[23])), abs(float(data[31])),
                        hoga_buprice5, hoga_buprice5, hoga_buprice5, hoga_buprice5, hoga_buprice5, hoga_buprice5
                    )
                    hoga_samount = (
                        0, 0, 0, 0, 0,
                        int(data[36]), int(data[28]), int(data[20]), int(data[12]), int(data[4])
                    )
                    hoga_bamount = (
                        int(data[8]), int(data[16]), int(data[24]), int(data[32]), int(data[40]),
                        0, 0, 0, 0, 0
                    )
                else:
                    dt = self.ft.GetCommRealData(code, 21)
                    hoga_tamount = (
                        int(self.ft.GetCommRealData(code, 121)),
                        int(self.ft.GetCommRealData(code, 125))
                    )
                    hoga_seprice5 = abs(float(self.ft.GetCommRealData(code, 45)))
                    hoga_seprice = (
                        hoga_seprice5, hoga_seprice5, hoga_seprice5, hoga_seprice5, hoga_seprice5, hoga_seprice5,
                        abs(float(self.ft.GetCommRealData(code, 44))),
                        abs(float(self.ft.GetCommRealData(code, 43))),
                        abs(float(self.ft.GetCommRealData(code, 42))),
                        abs(float(self.ft.GetCommRealData(code, 41)))
                    )
                    hoga_buprice5 = abs(float(self.ft.GetCommRealData(code, 55)))
                    hoga_buprice = (
                        abs(float(self.ft.GetCommRealData(code, 51))),
                        abs(float(self.ft.GetCommRealData(code, 52))),
                        abs(float(self.ft.GetCommRealData(code, 53))),
                        abs(float(self.ft.GetCommRealData(code, 54))),
                        hoga_buprice5, hoga_buprice5, hoga_buprice5, hoga_buprice5, hoga_buprice5, hoga_buprice5
                    )
                    hoga_samount = (
                        0, 0, 0, 0, 0,
                        int(self.ft.GetCommRealData(code, 65)),
                        int(self.ft.GetCommRealData(code, 64)),
                        int(self.ft.GetCommRealData(code, 63)),
                        int(self.ft.GetCommRealData(code, 62)),
                        int(self.ft.GetCommRealData(code, 61))
                    )
                    hoga_bamount = (
                        int(self.ft.GetCommRealData(code, 71)),
                        int(self.ft.GetCommRealData(code, 72)),
                        int(self.ft.GetCommRealData(code, 73)),
                        int(self.ft.GetCommRealData(code, 74)),
                        int(self.ft.GetCommRealData(code, 75)),
                        0, 0, 0, 0, 0
                    )

                cme_hms = str_hms_cme_from_str(dt)
                if not self.test_mode and ((not self.dict_set['주식타임프레임'] and int(cme_hms) < 90000) or (self.dict_set['주식타임프레임'] and int(cme_hms) < 93000)):
                    return
                dt = int(f'{self.str_tday}{cme_hms}')
                name = self.dict_info[code]['종목명']
            except:
                pass
            else:
                self.UpdateHogaData(int(dt), hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, name, start)

    def UpdateTickData(self, code, dt, c, o, h, low, per, v, csp, cbp):
        if self.dict_set['리시버공유'] == 1:
            self.recvservQ.put(('tickdata', (code, c, dt)))

        if code in self.tuple_jango and (code not in self.dict_jgdt.keys() or dt > self.dict_jgdt[code]):
            self.straderQ.put((code, c))
            self.dict_jgdt[code] = dt

        if code in self.dict_data.keys():
            dm, _, bids, asks, tbids, tasks = self.dict_data[code][5:]
        else:
            dm, bids, asks, tbids, tasks = 0, 0, 0, 0, 0

        bids_, asks_ = 0, 0
        wtm = self.dict_info[code]['위탁증거금']
        if '+' in v:
            bids_ = abs(int(v))
            dm   += int(bids_ * wtm)
        if '-' in v:
            asks_ = abs(int(v))
            dm   += int(asks_ * wtm)
        bids += bids_
        asks += asks_
        tbids += bids_
        tasks += asks_

        try:
            ch = round(tbids / tasks * 100, 2)
        except:
            ch = 500.
        if ch > 500: ch = 500.

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks]

        if code not in self.list_gsjm:
            self.list_gsjm.append(code)

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.kwzservQ.put(('hoga', (self.dict_info[code]['종목명'], c, per, 0, 0, o, h, low)))
                if asks > 0: self.kwzservQ.put(('hoga', (-asks, ch)))
                if bids > 0: self.kwzservQ.put(('hoga', (bids, ch)))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, name, receivetime):
        sm     = 0
        dm     = 0
        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data.keys():
            dm = self.dict_data[code][5]
            if code in self.dict_tmdt.keys():
                if dt > self.dict_tmdt[code][0]:
                    send = True
            else:
                self.dict_tmdt[code] = [dt, 0]
            sm = dm - self.dict_tmdt[code][1]

        if send:
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                index = 0
                for i, price in enumerate(hoga_seprice[::-1]):
                    if price >= csp:
                        index = i
                        break
                if index <= 5:
                    hoga_seprice = hoga_seprice[5 - index:10 - index]
                    hoga_samount = hoga_samount[5 - index:10 - index]
                else:
                    hoga_seprice = tuple(np.zeros(index - 5)) + hoga_seprice[:10 - index]
                    hoga_samount = tuple(np.zeros(index - 5)) + hoga_samount[:10 - index]
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                index = 0
                for i, price in enumerate(hoga_buprice):
                    if price <= cbp:
                        index = i
                        break
                hoga_buprice = hoga_buprice[index:index + 5]
                hoga_bamount = hoga_bamount[index:index + 5]
                if index > 5:
                    hoga_buprice = hoga_buprice + tuple(np.zeros(index - 5))
                    hoga_bamount = hoga_bamount + tuple(np.zeros(index - 5))
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            c     = self.dict_data[code][0]
            hlp   = round((c / ((self.dict_data[code][2] + self.dict_data[code][3]) / 2) - 1) * 100, 2)
            hgjrt = sum(hoga_samount + hoga_bamount)
            logt  = now() if self.int_logt < dt_min else 0
            data  = (dt,) + tuple(self.dict_data[code][:9]) + (sm, hlp) + hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + (hgjrt, 1, code, name, logt)

            self.sstgQ.put(data)
            if code in self.tuple_jango or code in self.tuple_order:
                self.straderQ.put(('주문확인', code, c))

            if self.dict_set['리시버공유'] == 1:
                self.recvservQ.put(('tickdata', data))

            self.dict_tmdt[code] = [dt, dm]
            self.dict_data[code][7:9] = [0, 0]

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'리시버 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt
        elif self.int_mtdt < dt and str(self.int_mtdt)[-4:] < '1600':
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt
            self.list_gsjm = []

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            self.kwzservQ.put(('hoga', (name,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5]))
