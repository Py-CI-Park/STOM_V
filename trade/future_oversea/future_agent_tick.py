
import os
import sys
import sqlite3
import datetime
import numpy as np
import pandas as pd
from traceback import format_exc
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utility.setting_base import ui_num, DB_CODE_INFO, DB_TRADELIST, DB_FUTURE_TICK, DB_FUTURE_MIN
from utility.static import now, str_hms_cme_from_str, qtest_qwait, opstarter_kill, str_ymd, now_cme, str_hms, \
    timedelta_sec


class Updater(QThread):
    signal1 = pyqtSignal(list)
    signal2 = pyqtSignal(tuple)

    def __init__(self, sagentQ):
        super().__init__()
        self.sagentQ = sagentQ

    def run(self):
        while True:
            data = self.sagentQ.get()
            if data.__class__ == list:
                self.signal1.emit(data)
            elif data.__class__ == tuple:
                self.signal2.emit(data)


class FutureAgentTick:
    def __init__(self, qlist, dict_set):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ
                0            1             2            3
        """
        app = QApplication(sys.argv)

        self.mgzservQ = qlist[0]
        self.sagentQ  = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQ    = qlist[3]
        self.dict_set = dict_set

        self.ocx = QAxWidget('KFOPENAPI.KFOpenAPICtrl.1')
        self.ocx.OnReceiveMsg.connect(self.OnReceiveMsg)
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.ocx.OnReceiveTrData.connect(self.OnReceiveTrData)
        self.ocx.OnReceiveRealData.connect(self.OnReceiveRealData)
        self.ocx.OnReceiveChejanData.connect(self.OnReceiveChejanData)

        self.dict_bool = {
            '로그인': False,
            'TR수신': False,
            '계좌조회': False,
            '실시간등록': False,
            '프로세스종료': False,
            '해선체결필드확인': False,
            '해선체결필드같음': False,
            '호가잔량필드확인': False,
            '호가잔량필드같음': False
        }

        self.str_account = ''
        self.str_pass    = self.dict_set[f"계좌비밀번호{int(self.dict_set['증권사'][4:])}"]
        self.str_today   = str_ymd(now_cme())
        self.order_time  = now()
        self.intg_odsn   = 3000
        self.tr_next     = None
        self.tr_df       = None

        self.dict_dtdm   = {}
        self.dict_hgbs   = {}
        self.dict_data   = {}
        self.dict_info   = {}
        self.dict_mtop   = {}
        self.dict_jgdt   = {}
        self.dict_sncd   = {}
        self.dict_money  = {}
        self.dict_bmbyp  = {}
        self.dict_smbyp  = {}
        self.dict_index  = {}

        self.list_hgdt   = [0, 0, 0, 0]
        self.real_codes  = []
        self.list_gsjm   = []
        self.tuple_jango = ()
        self.tuple_order = ()

        self.int_logt    = 0
        self.int_mtdt    = None
        self.hoga_code   = None
        self.chart_code  = None

        self.CommConnect()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.Scheduler)
        self.qtimer.start()

        self.updater = Updater(self.sagentQ)
        self.updater.signal1.connect(self.ReceivOrder)
        self.updater.signal2.connect(self.UpdateTuple)
        self.updater.start()

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

        app.exec_()

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect(0)')
        while not self.dict_bool['로그인']:
            qtest_qwait(0.01)
        self.ShowAccountWindow()
        opstarter_kill()

        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료')))

        self.str_account = self.GetAccountNumber()

        con = sqlite3.connect(DB_CODE_INFO)
        df = pd.read_sql('SELECT * FROM futureinfo', con).set_index('index')
        con.close()
        self.dict_info = df.to_dict('index')

        df_list = []
        # IDX:지수, CUR:통화, MTL:금속, ENG:에너지, CMD:농축산물, OPT:해외옵션, INT:금리
        for gubun in ['IDX', 'CUR']:
            nnext = ''
            while True:
                df = self.SearchDeposit(gubun, nnext)      # 상품코드별 종목명, 위탁증거금, 유지증거금을 조회한다
                df_list.append(df)
                qtest_qwait(0.25)
                if self.tr_next:
                    nnext = self.tr_next
                else:
                    break
        df = pd.concat(df_list)
        df = df[df['거래소'] == 'CME']
        df.set_index('종목코드', inplace=True)

        # 품목코드를 추가하려면 HTS에서 코드를 확인 후 여기에 추가하면 됩니다.
        # 추가된 품목코드가 지수나 통화 상품이 아닐 경우 상단 for문에서 상품코드를 추가해야합니다.
        # 현재는 CME 거래소에서 거래량이 많은 지수 및 코인 품목만 포함되어 있으며
        # 크루드오일 등 에너지는 CBOT 거래소의 실시간시세 이용료를 납부해야합니다.
        code_list = ['NQ', 'RTY', 'ES', 'EMD', 'MNQ', 'M2K', 'MES', 'BTC', 'MBT', 'ETH', 'MET']
        for code in code_list:
            str_codes = self.GetGlobalFutureCodelist(code)       # 품목코드로 종목코드 목록을 조회한다
            df_gs = self.SearchInterest(str_codes)               # 조회된 종목코드의 틱단위, 틱가치를 조회한다
            if len(df_gs) > 0:
                df_gs.sort_values(by=['누적거래량'], ascending=False, inplace=True)
                max_code  = df_gs['종목코드'].iloc[0]              # 조회된 종목코드 중 당일 거래량이 가장 많은 종목을 선택한다
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

        dict_name = {code: self.dict_info[code]['종목명'] for code in self.dict_info}
        dict_code = {self.dict_info[code]['종목명']: code for code in self.dict_info}
        self.mgzservQ.put(('window', (ui_num['종목명데이터'], dict_name, dict_code)))
        self.straderQ.put(('종목정보', self.dict_info))
        self.sstgQ.put(('종목정보', self.dict_info))

        df = pd.DataFrame.from_dict(self.dict_info, orient='index')
        self.mgzservQ.put(('query', ('종목디비', df, 'futureinfo', 'replace')))
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 종목 정보 검색 완료')))

        text = '해외선물 시스템을 시작하였습니다.'
        if self.dict_set['주식알림소리']: self.mgzservQ.put(('sound', text))
        self.mgzservQ.put(('tele', text))
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 에이전트 시작')))

    def OnEventConnect(self, err_code):
        if err_code == 0: self.dict_bool['로그인'] = True

    def OnReceiveRealData(self, code, realtype, realdata):
        if self.dict_bool['프로세스종료']:
            return

        if realtype == '해외선물호가':
            try:
                start = now()
                if not self.dict_bool['호가잔량필드확인']:
                    data = realdata.split(';')
                    if data[0]                             == self.GetCommRealData(code, 21) and \
                            int(data[43])              == int(self.GetCommRealData(code, 121)) and \
                            int(data[46])              == int(self.GetCommRealData(code, 125)) and \
                            abs(float(data[35])) == abs(float(self.GetCommRealData(code, 45))) and \
                            abs(float(data[27])) == abs(float(self.GetCommRealData(code, 44))) and \
                            abs(float(data[19])) == abs(float(self.GetCommRealData(code, 43))) and \
                            abs(float(data[11])) == abs(float(self.GetCommRealData(code, 42))) and \
                            abs(float(data[3]))  == abs(float(self.GetCommRealData(code, 41))) and \
                            abs(float(data[7]))  == abs(float(self.GetCommRealData(code, 51))) and \
                            abs(float(data[15])) == abs(float(self.GetCommRealData(code, 52))) and \
                            abs(float(data[23])) == abs(float(self.GetCommRealData(code, 53))) and \
                            abs(float(data[31])) == abs(float(self.GetCommRealData(code, 54))) and \
                            abs(float(data[39])) == abs(float(self.GetCommRealData(code, 55))) and \
                            int(data[36])              == int(self.GetCommRealData(code, 65)) and \
                            int(data[28])              == int(self.GetCommRealData(code, 64)) and \
                            int(data[20])              == int(self.GetCommRealData(code, 63)) and \
                            int(data[12])              == int(self.GetCommRealData(code, 62)) and \
                            int(data[4])               == int(self.GetCommRealData(code, 61)) and \
                            int(data[8])               == int(self.GetCommRealData(code, 71)) and \
                            int(data[16])              == int(self.GetCommRealData(code, 72)) and \
                            int(data[24])              == int(self.GetCommRealData(code, 73)) and \
                            int(data[32])              == int(self.GetCommRealData(code, 74)) and \
                            int(data[40])              == int(self.GetCommRealData(code, 75)):
                        self.dict_bool['호가잔량필드같음'] = True
                        self.mgzservQ.put(('window', (ui_num['기본로그'], f'시스템 명령 실행 알림 - 해선호가잔량 필드값 같음')))
                    else:
                        self.mgzservQ.put(('window', (ui_num['시스템로그'], f'오류 알림 - 해선호가잔량 필드값이 다릅니다. 필드값 갱신요망!!')))
                    self.dict_bool['호가잔량필드확인'] = True

                if self.dict_bool['호가잔량필드같음']:
                    data = realdata.split(';')
                    dt = data[0]
                    hoga_tamount = [
                        int(data[43]), int(data[46])
                    ]
                    hoga_seprice = [
                        abs(float(data[35])), abs(float(data[27])), abs(float(data[19])), abs(float(data[11])), abs(float(data[3]))
                    ]
                    hoga_buprice = [
                        abs(float(data[7])), abs(float(data[15])), abs(float(data[23])), abs(float(data[31])), abs(float(data[39]))
                    ]
                    hoga_samount = [
                        int(data[36]), int(data[28]), int(data[20]), int(data[12]), int(data[4])
                    ]
                    hoga_bamount = [
                        int(data[8]), int(data[16]), int(data[24]), int(data[32]), int(data[40])
                    ]
                else:
                    dt = self.GetCommRealData(code, 21)
                    hoga_tamount = [
                        int(self.GetCommRealData(code, 121)),
                        int(self.GetCommRealData(code, 125))
                    ]
                    hoga_seprice = [
                        abs(float(self.GetCommRealData(code, 45))),
                        abs(float(self.GetCommRealData(code, 44))),
                        abs(float(self.GetCommRealData(code, 43))),
                        abs(float(self.GetCommRealData(code, 42))),
                        abs(float(self.GetCommRealData(code, 41)))
                    ]
                    hoga_buprice = [
                        abs(float(self.GetCommRealData(code, 51))),
                        abs(float(self.GetCommRealData(code, 52))),
                        abs(float(self.GetCommRealData(code, 53))),
                        abs(float(self.GetCommRealData(code, 54))),
                        abs(float(self.GetCommRealData(code, 55)))
                    ]
                    hoga_samount = [
                        int(self.GetCommRealData(code, 65)),
                        int(self.GetCommRealData(code, 64)),
                        int(self.GetCommRealData(code, 63)),
                        int(self.GetCommRealData(code, 62)),
                        int(self.GetCommRealData(code, 61))
                    ]
                    hoga_bamount = [
                        int(self.GetCommRealData(code, 71)),
                        int(self.GetCommRealData(code, 72)),
                        int(self.GetCommRealData(code, 73)),
                        int(self.GetCommRealData(code, 74)),
                        int(self.GetCommRealData(code, 75))
                    ]

                str_cme_hms = str_hms_cme_from_str(dt)
                if self.dict_set['주식타임프레임']:
                    if int(str_cme_hms) < 93000:
                        return
                else:
                    if int(str_cme_hms) < 90000:
                        return
                dt = int(f'{self.str_today}{str_cme_hms}')
                name = self.dict_info[code]['종목명']
            except:
                self.mgzservQ.put(('window', (ui_num['시스템로그'], f'{format_exc()}오류 알림 - OnReceiveRealData')))
            else:
                try:
                    self.UpdateHogaData(dt, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, hoga_tamount, code, name, start)
                except:
                    self.mgzservQ.put(('window', (ui_num['시스템로그'], f'{format_exc()}오류 알림 - UpdateHogaData')))

        elif realtype == '해외선물시세':
            try:
                if not self.dict_bool['해선체결필드확인']:
                    data = realdata.split(';')
                    if data[0]                             == self.GetCommRealData(code, 20) and \
                            float(data[2])           == float(self.GetCommRealData(code, 140)) and \
                            float(data[4])           == float(self.GetCommRealData(code, 12)) and \
                            data[7]                        == self.GetCommRealData(code, 15) and \
                            abs(float(data[9]))  == abs(float(self.GetCommRealData(code, 16))) and \
                            abs(float(data[10])) == abs(float(self.GetCommRealData(code, 17))) and \
                            abs(float(data[11])) == abs(float(self.GetCommRealData(code, 18))) and \
                            abs(float(data[5]))  == abs(float(self.GetCommRealData(code, 27))) and \
                            abs(float(data[6]))  == abs(float(self.GetCommRealData(code, 28))):
                        self.dict_bool['해선체결필드같음'] = True
                        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 해선체결 필드값 같음')))
                    else:
                        self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 해선체결 필드값이 다릅니다. 필드값 갱신요망!!')))
                    self.dict_bool['해선체결필드확인'] = True

                if self.dict_bool['해선체결필드같음']:
                    data = realdata.split(';')
                    dt            = data[0]
                    c       = float(data[2])
                    per     = float(data[4])
                    v             = data[7]
                    o   = abs(float(data[9]))
                    h   = abs(float(data[10]))
                    low = abs(float(data[11]))
                    csp = abs(float(data[5]))
                    cbp = abs(float(data[6]))
                else:
                    dt            = self.GetCommRealData(code, 20)
                    c       = float(self.GetCommRealData(code, 140))
                    per     = float(self.GetCommRealData(code, 12))
                    v             = self.GetCommRealData(code, 15)
                    o   = abs(float(self.GetCommRealData(code, 16)))
                    h   = abs(float(self.GetCommRealData(code, 17)))
                    low = abs(float(self.GetCommRealData(code, 18)))
                    csp = abs(float(self.GetCommRealData(code, 27)))
                    cbp = abs(float(self.GetCommRealData(code, 28)))

                str_cme_hms = str_hms_cme_from_str(dt)
                if self.dict_set['주식타임프레임']:
                    if int(str_cme_hms) < 93000:
                        return
                else:
                    if int(str_cme_hms) < 90000:
                        return
                dt = int(f'{self.str_today}{str_cme_hms}')
            except:
                self.mgzservQ.put(('window', (ui_num['시스템로그'], f'{format_exc()}오류 알림 - OnReceiveRealData')))
            else:
                try:
                    self.UpdateTickData(code, dt, c, o, h, low, per, v, csp, cbp)
                except:
                    self.mgzservQ.put(('window', (ui_num['시스템로그'], f'{format_exc()}오류 알림 - UpdateTickData')))

    def UpdateTickData(self, code, dt, c, o, h, low, per, v, csp, cbp):
        data = self.dict_data.get(code)
        if data:
            dm, _, bids, asks, tbids, tasks = data[5:11]
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

        ch = min(500, round(tbids / tasks * 100, 2)) if tasks > 0 else 500

        if code not in self.list_gsjm:
            self.list_gsjm.append(code)

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks]

        self.UpdateMoneyFactor(code, c, int(wtm * bids_), int(wtm * asks_))
        self.UpdateHogaWindowTick(code, dt, bids_, asks_, c, per, o, h, low, ch)

    def UpdateMoneyFactor(self, code, c, buy_money, sell_money):
        if code not in self.dict_money:
            # 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격
            #     0          1          2          3          4          5          6          7
            self.dict_money[code] = [buy_money, sell_money, buy_money, buy_money, c, sell_money, sell_money, c]
            self.dict_index[code] = {c: 0}
            self.dict_bmbyp[code] = np.zeros(1000, dtype=np.float64)
            self.dict_smbyp[code] = np.zeros(1000, dtype=np.float64)
            self.dict_bmbyp[code][0] = buy_money
            self.dict_smbyp[code][0] = sell_money
            self.dict_index[code]['count'] = 1
        else:
            money_arr = self.dict_money[code]
            price_idx = self.dict_index[code]
            buy_arr = self.dict_bmbyp[code]
            sell_arr = self.dict_smbyp[code]

            money_arr[0] += buy_money
            money_arr[1] += sell_money
            money_arr[2] += buy_money
            money_arr[5] += sell_money

            idx = price_idx.get(c)
            if idx is not None:
                buy_arr[idx] += buy_money
                sell_arr[idx] += sell_money
            else:
                idx = price_idx['count']
                if idx >= len(buy_arr):
                    self.dict_bmbyp[code] = np.resize(buy_arr, len(buy_arr) * 2)
                    self.dict_smbyp[code] = np.resize(sell_arr, len(sell_arr) * 2)
                    buy_arr = self.dict_bmbyp[code]
                    sell_arr = self.dict_smbyp[code]

                price_idx[c] = idx
                buy_arr[idx] = buy_money
                sell_arr[idx] = sell_money
                price_idx['count'] += 1

            if buy_arr[idx] >= money_arr[3]:
                money_arr[3] = buy_arr[idx]
                money_arr[4] = c
            if sell_arr[idx] >= money_arr[6]:
                money_arr[6] = sell_arr[idx]
                money_arr[7] = c

    def UpdateHogaWindowTick(self, code, dt, bids_, asks_, c, per, o, h, low, ch):
        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.mgzservQ.put(('hoga', (self.dict_info[code]['종목명'], c, per, 0, -1, o, h, low)))
                if asks > 0: self.mgzservQ.put(('hoga', (-asks, ch)))
                if bids > 0: self.mgzservQ.put(('hoga', (bids, ch)))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, dt, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, hoga_tamount,
                       code, name, receivetime):

        send   = False
        dt_min = int(str(dt)[:12])

        code_data = self.dict_data.get(code)
        money_arr = self.dict_money.get(code)
        if code_data and money_arr:
            code_dtdm = self.dict_dtdm.get(code)
            if code_dtdm:
                if dt > code_dtdm[0]:
                    send = True
            else:
                self.dict_dtdm[code] = [dt, 0]
                code_dtdm = self.dict_dtdm[code]
                send = True

            if send:
                csp, cbp = self.dict_hgbs[code]
                hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount = \
                    self.CorrectionHogaData(csp, cbp, hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount)

                data, c, dm, logt = self.GetSendData(True, code, name, code_data, code_dtdm, money_arr,
                                                     hoga_samount, hoga_bamount, hoga_seprice, hoga_buprice,
                                                     hoga_tamount, dt, dt_min)

                self.sstgQ.put(data)
                if code in self.tuple_jango or code in self.tuple_order:
                    self.straderQ.put(('잔고갱신', (code, c)))

                code_dtdm[0] = dt
                code_dtdm[1] = dm
                code_data[7] = 0
                code_data[8] = 0
                money_arr[0] = 0
                money_arr[1] = 0

                self.SendLog(logt, dt_min, receivetime)

        self.UpdateMoneyTop(dt)
        self.UpdateHogaWindowRem(code, name, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount)

    def CorrectionHogaData(self, csp, cbp, hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount):
        if hoga_seprice[-1] < csp:
            valid_indices = [i for i, price in enumerate(hoga_seprice) if price >= csp]
            end_index = valid_indices[-1] + 1 if valid_indices else None
            if end_index is not None:
                add_cnt = 5 - end_index
                hoga_seprice = [0.] * add_cnt + hoga_seprice[:end_index]
                hoga_samount = [0] * add_cnt + hoga_samount[:end_index]
            else:
                hoga_seprice = [0.] * 5
                hoga_samount = [0] * 5

        if hoga_buprice[0] > cbp:
            valid_indices = [i for i, price in enumerate(hoga_buprice) if price <= cbp]
            start_index = valid_indices[0] if valid_indices else None
            if start_index is not None:
                hoga_buprice = hoga_buprice[start_index:] + [0.] * start_index
                hoga_bamount = hoga_bamount[start_index:] + [0] * start_index
            else:
                hoga_buprice = [0.] * 5
                hoga_bamount = [0] * 5

        return hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount

    def GetSendData(self, is_tick, code, name, code_data, code_dtdm, money_arr, hoga_samount, hoga_bamount,
                    hoga_seprice, hoga_buprice, hoga_tamount, dt, dt_min):
        c, _, h, low, _, dm, _, bids, asks = code_data[:9]
        tm = dm - code_dtdm[1]
        if tm == dm and 93500 < int(str(dt)[8:]): tm = 0
        hlp = round((c / ((h + low) / 2) - 1) * 100, 2)
        lhp = round((h / low - 1) * 100, 2)
        hjt = sum(hoga_samount + hoga_bamount)
        logt = now() if self.int_logt < dt_min else 0
        if is_tick:
            tick_data = code_data[:9]
        else:
            tick_data = code_data[:9] + code_data[11:]
            dt = code_dtdm[0]
        data = [dt] + tick_data + [tm, hlp, lhp] + money_arr + \
            hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + hoga_tamount + [hjt, 1, code, name, logt]
        return data, c, dm, logt

    def SendLog(self, logt, dt_min, receivetime):
        if logt != 0:
            gap = (now() - receivetime).total_seconds()
            self.mgzservQ.put(('window', (ui_num['타임로그'], f'에젼트 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
            self.int_logt = dt_min

    def UpdateMoneyTop(self, dt):
        if self.int_mtdt is None:
            self.int_mtdt = dt
        elif self.int_mtdt < dt:
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt

    def UpdateHogaWindowRem(self, code, name, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount):
        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            self.mgzservQ.put(('hoga', [name] + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5]))

    # noinspection PyUnusedLocal
    def OnReceiveMsg(self, sScrNo, sRQName, sTrCode, sMsg):
        if '매수증거금' in sMsg:
            sn = int(sScrNo)
            code = self.dict_sncd.get(sn, '')
            self.straderQ.put(('증거금부족', code))
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'{sMsg}')))

    # noinspection PyUnusedLocal
    def OnReceiveChejanData(self, gubun, itemcnt, fidlist):
        if self.dict_set['주식모의투자']:
            return

        if gubun in ('0', '1'):
            try:
                종목코드 = self.GetChejanData(9001)
                종목명 = self.dict_info[종목코드]['종목명']
                주문상태 = self.GetChejanData(913)
                주문구분 = self.GetChejanData(905)
                매도수구분 = self.GetChejanData(907)
                주문수량 = int(self.GetChejanData(900))
                미체결수량 = int(self.GetChejanData(902))
                주문가격 = float(self.GetChejanData(901))
                주문번호 = self.GetChejanData(9203)
                주문시간 = f"{self.str_today}{str_hms_cme_from_str(self.GetChejanData(908))}"
            except:
                pass
            else:
                try:
                    체결수량 = int(self.GetChejanData(911))
                    체결가격 = float(self.GetChejanData(910))
                except:
                    체결수량 = 0
                    체결가격 = 0
                주문상태 = self.주문상태[주문상태]
                주문구분 = self.주문구분[gubun][주문구분]
                매도수구분 = self.매도수구분[매도수구분]
                self.straderQ.put(('체잔통보', (종목코드, 종목명, 주문상태, 주문구분, 매도수구분, 주문수량, 미체결수량, 주문가격, 주문시간, 주문번호, 체결수량, 체결가격)))

    def Scheduler(self):
        if not self.dict_bool['계좌조회']:
            self.GetAccountjanGo()
        if not self.dict_bool['실시간등록']:
            self.OperationRealreg()

        inthms = int(str_hms(now_cme()))
        if self.dict_set['주식전략종료시간'] < inthms and self.dict_set['주식프로세스종료'] and not self.dict_bool['프로세스종료']:
            self.ProcessKill()
        if 160500 < inthms and not self.dict_bool['프로세스종료']:
            self.ProcessKill()

    def GetAccountjanGo(self):
        self.dict_bool['계좌조회'] = True

        dict_jg = None
        if self.dict_set['주식모의투자']:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql('SELECT * FROM f_tradelist', con)
            con.close()
            yesugm = 1_000_000_000 + df['수익금'].sum()
            if yesugm < 1_000_000_000: yesugm = 1_000_000_000
        else:
            df = self.GetBalances(self.str_account, self.str_pass)
            df.set_index('통화코드', inplace=True)
            yesugm = round(df['원화대용평가금액']['USD'] / 100, 2) if len(df) > 0 else 0

            df = self.GetJango(self.str_account, self.str_pass)
            if len(df) > 0:
                df['종목명'] = ''
                columns = ['종목코드', '종목명', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량']
                df = df[columns]
                df['분할매수횟수'] = 5
                df['분할매도횟수'] = 0
                df['매수시간'] = self.str_today + '083000'
                df['종목명'] = df['종목코드'].apply(lambda x: self.dict_info[x]['종목명'])
                df.set_index('index', inplace=True)
                dict_jg = df.to_dict('index')

        self.straderQ.put(('잔고조회', (yesugm, dict_jg)))
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 계좌 조회 완료')))

    def OperationRealreg(self):
        self.dict_bool['실시간등록'] = True
        self.SetRealReg(self.real_codes)
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 실시간 등록 완료')))

    def ProcessKill(self):
        self.dict_bool['프로세스종료'] = True
        if self.dict_set['주식알림소리']:
            self.mgzservQ.put(('sound', '해외선물 시스템을 3분 후 종료합니다.'))
        QTimer.singleShot(180 * 1000, self.SysExit)

    def SysExit(self):
        if self.dict_set['주식데이터저장']:
            self.SaveData()
        self.sstgQ.put('프로세스종료')
        self.straderQ.put('프로세스종료')
        qtest_qwait(5)
        self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 에이전트 종료')))

    def SaveData(self):
        if self.dict_mtop:
            con = sqlite3.connect(DB_FUTURE_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN)
            last_index = 0
            try:
                df = pd.read_sql(f'SELECT * FROM moneytop ORDER BY "index" DESC LIMIT 1', con)
                last_index = df['index'][0]
            except:
                pass
            dict_mtop = {key: value for key, value in self.dict_mtop.items() if key > last_index}
            df = pd.DataFrame(dict_mtop.values(), columns=['거래대금순위'], index=list(dict_mtop))
            df.to_sql('moneytop', con, if_exists='append', chunksize=1000)
            con.close()
            self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 데이터수집목록 저장 완료')))

    def ReceivOrder(self, order):
        # [주문구분, 화면번호, 계좌번호, 주문유형, 종목코드, 주문수량, 주문가격, Stop단가, 거래구분, 원주문번호], 종목명, 시그널시간
        curr_time = now()
        if curr_time < self.order_time:
            next_time = (self.order_time - curr_time).total_seconds()
            QTimer.singleShot(int(next_time * 1000), lambda: self.ReceivOrder(order))
            return

        self.intg_odsn = self.intg_odsn + 1 if self.intg_odsn + 1 < 9000 else 3000
        order[1] = str(self.intg_odsn)
        order[2] = self.str_account

        주문구분, _, _, _, 종목코드, 주문수량, 주문가격, _, _, _, 종목명, 시그널시간 = order

        self.OrderTimeLog(시그널시간)
        ret = self.SendOrder(order[:-2])
        if ret == 0:
            self.straderQ.put(('주문전송', (종목코드, 주문구분)))
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'주문 관리 시스템 알림 - [주문전송] [{주문구분}] {종목명} | {주문가격} | {주문수량}')))
            self.order_time = timedelta_sec(0.2)
            self.dict_sncd[self.intg_odsn] = 종목코드
        else:
            self.sstgQ.put((f'{주문구분}_CANCEL', 종목코드))
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'주문 관리 시스템 알림 - [주문실패] [{주문구분}] {종목명} | {주문가격} | {주문수량}')))

    def SendOrder(self, order: list):
        return self.ocx.dynamicCall('SendOrder(QString, QString, QString, int, QString, int, QString, QString, QString, QString)', order)

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.mgzservQ.put(('window', (ui_num['타임로그'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.')))

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
        elif gubun == '수동데이터저장':
            self.ProcessKill()

    # noinspection PyUnusedLocal, PyUnresolvedReferences
    def OnReceiveTrData(self, screen, rqname, trcode, record, nnext):
        if 'ORD' in trcode:
            return

        if trcode == 'opt10001':
            self.dict_bool['실시간등록'] = True
            return

        self.tr_next = nnext.strip()
        columns_, columns = None, None
        if trcode == 'opw50004':
            columns_ = ['파생품목코드', '파생품목명', '위탁증거금', '유지증거금', '틱단위수', '틱가치', '해외거래소코드']
            columns  = ['종목코드', '종목명', '위탁증거금', '유지증거금', '호가단위', '틱가치', '거래소']
        elif trcode == 'opt10005':
            columns_ = columns = ['종목코드', '누적거래량']
        elif trcode == 'opw30009':
            columns_ = columns = ['통화코드', '원화대용평가금액', '주문가능금액']
        elif trcode == 'opw30003':
            columns_ = ['종목코드', '매도수구분', '평균단가', '현재가격', '수익률', '평가손익', '약정금액', '평가금액', '수량']
            columns  = ['종목코드', '포지션', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량']

        rows = self.ocx.dynamicCall('GetRepeatCnt(QString, QString)', trcode, rqname)
        if rows == 0: rows = 1

        data_list = []
        for row in range(rows):
            row_data = []
            for item in columns_:
                data = self.ocx.dynamicCall('GetCommData(QString, QString, int, QString)', trcode, rqname, row, item)
                row_data.append(data.strip())
            data_list.append(row_data)

        self.tr_df = pd.DataFrame(data_list, columns=columns)
        self.tr_df = self.tr_df.replace('', pd.NA)
        self.tr_df = self.tr_df.dropna()
        if len(self.tr_df) > 0:
            if trcode == 'opw50004':
                columns = ['위탁증거금', '유지증거금']
                self.tr_df[columns] = self.tr_df[columns].astype(int)
                columns = ['호가단위', '틱가치']
                self.tr_df[columns] = self.tr_df[columns].astype(float)
            elif trcode == 'opt10005':
                columns = ['누적거래량']
                self.tr_df[columns] = self.tr_df[columns].astype(int)
            elif trcode == 'opw30009':
                columns = ['원화대용평가금액', '주문가능금액']
                self.tr_df[columns] = self.tr_df[columns].astype(int)
            elif trcode == 'opw30003':
                columns = ['매수가', '현재가', '수익률']
                self.tr_df[columns] = self.tr_df[columns].astype(float)
                columns = ['평가손익', '약정금액', '평가금액', '보유수량']
                self.tr_df[columns] = self.tr_df[columns].astype(int)
                self.tr_df['포지션'] = self.tr_df['포지션'].apply(lambda x: 'LONG' if x == '매수' else 'SHORT')
        self.dict_bool['TR수신'] = True

    def GetBalances(self, acc_num: str, pass_num: str) -> pd.DataFrame:
        self.dict_bool['TR수신'] = False
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '계좌번호', acc_num)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '비밀번호', pass_num)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체', '00')
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '예수금및증거금현황조회', 'opw30009', '', 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            qtest_qwait(0.01)
        return self.tr_df

    def GetJango(self, acc_num: str, pass_num: str) -> pd.DataFrame:
        self.dict_bool['TR수신'] = False
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '계좌번호', acc_num)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '비밀번호', pass_num)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체', '00')
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '통화코드', 'USD')
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '미체결잔고내역조회', 'opw30003', '', 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            qtest_qwait(0.01)
        return self.tr_df

    def SearchDeposit(self, gubun: str, nnext: str) -> pd.DataFrame:
        self.dict_bool['TR수신'] = False
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '품목구분', gubun)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '해외파생구분', 'FU')
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '파생품목코드', '')
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '삼품별명세및요약조회', 'opw50004', nnext, 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            qtest_qwait(0.01)
        return self.tr_df

    def SearchInterest(self, codes: str) -> pd.DataFrame:
        self.dict_bool['TR수신'] = False
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '종목코드', codes)
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '관심종목조회', 'opt10005', '', 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            qtest_qwait(0.01)
        self.DisconnectRealData()
        return self.tr_df

    def SetRealReg(self, code_list: list):
        sn = '1001'
        for code in code_list:
            self.dict_bool['실시간등록'] = False
            self.ocx.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)
            self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '종목정보조회', 'opt10001', '', sn)
            sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
            while not self.dict_bool['실시간등록'] or datetime.datetime.now() < sleeptime:
                qtest_qwait(0.01)
            sn = str(int(sn) + 1)

    def ShowAccountWindow(self):
        self.ocx.dynamicCall('GetCommonFunc(QString, QString)', 'ShowAccountWindow', '')

    def DisconnectRealData(self):
        self.ocx.dynamicCall('DisconnectRealData(QString)', 1000)

    def GetAccountNumber(self):
        return self.ocx.dynamicCall('GetLoginInfo(QString)', 'ACCNO').split(';')[0]

    def GetGlobalFutureCodelist(self, code: str) -> str:
        return self.ocx.dynamicCall('GetGlobalFutureCodelist(QString)', code)

    def GetCommRealData(self, code: str, fid: int):
        return self.ocx.dynamicCall('GetCommRealData(QString, int)', code, fid)

    def GetChejanData(self, fid: int):
        return self.ocx.dynamicCall('GetChejanData(int)', fid)
