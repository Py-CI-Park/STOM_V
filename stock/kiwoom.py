import os
import sys
import zipfile
import datetime
import pandas as pd
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import OPENAPI_PATH, DICT_SET, ui_num
from utility.static import now, qtest_qwait, str_ymd, str_hms, timedelta_sec


sn_brrq = 1000
sn_brrd = 1001
sn_cond = 1002
sn_oper = 1003
sn_gsjm = 2000


def parseDat(trcode):
    enc    = zipfile.ZipFile(f'{OPENAPI_PATH}/data/{trcode}.enc')
    lines  = enc.read(trcode.upper() + '.dat').decode('cp949')
    lines  = lines.split('\n')
    start  = [i for i, x in enumerate(lines) if x.startswith('@START')]
    end    = [i for i, x in enumerate(lines) if x.startswith('@END')]
    blocks = zip(start, end)
    dict_enc = {}
    for start, end in blocks:
        block  = lines[start - 1:end + 1]
        blname = block[1].split('_')[1].strip().split('=')[0]
        fields = [line.split('=')[0].strip() for line in block[2:-1]]
        if 'INPUT' not in block[0]: dict_enc[blname] = fields
    return dict_enc


class Updater(QThread):
    signal1 = pyqtSignal(list)
    signal2 = pyqtSignal(dict)

    def __init__(self, kiwoomQ):
        super().__init__()
        self.kiwoomQ = kiwoomQ

    def run(self):
        while True:
            data = self.kiwoomQ.get()
            if type(data) == list:
                self.signal1.emit(data)
            elif type(data) == dict:
                self.signal2.emit(data)


class Kiwoom:
    def __init__(self, qlist):
        """
        self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQs, self.kiwoomQ
                0            1              2             3           4
        """
        app = QApplication(sys.argv)

        self.kwzservQ = qlist[0]
        self.sreceivQ = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQs   = qlist[3]
        self.kiwoomQ  = qlist[4]
        self.dict_set = DICT_SET

        self.ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
        self.ocx.OnReceiveMsg.connect(self.OnReceiveMsg)
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.ocx.OnReceiveTrData.connect(self.OnReceiveTrData)
        self.ocx.OnReceiveRealData.connect(self.OnReceiveRealData)
        self.ocx.OnReceiveChejanData.connect(self.OnReceiveChejanData)
        self.ocx.OnReceiveTrCondition.connect(self.OnReceiveTrCondition)
        self.ocx.OnReceiveConditionVer.connect(self.OnReceiveConditionVer)
        self.ocx.OnReceiveRealCondition.connect(self.OnReceiveRealCondition)

        self.dict_bool = {
            '로그인': False,
            'TR수신': False,
            'TR다음': False,
            'CD로딩': False,
            'CD수신': False,
            '계좌조회': False,
            '실시간등록': False,
            '프로세스종료': False,
            '주식체결필드확인': False,
            '주식체결필드같음': False,
            '호가잔량필드확인': False,
            '호가잔량필드같음': False,
            '실시간조건검색시작': False
        }
        self.dict_name   = {}
        self.dict_sgbn   = {}
        self.dict_sncd   = {}
        self.list_code   = []
        self.list_cond   = []

        self.str_account = ''
        self.str_today   = str_ymd()
        self.order_time  = now()
        self.intg_odsn   = 3000
        self.operation   = 1 if int(str_hms()) < 85900 else 3
        self.tr_fields   = None
        self.tr_cdlist   = None
        self.tr_df       = None

        int_hms = int(str_hms())
        self.test_mode   = True if 90000 < int_hms or int_hms < 70000 else False

        self.CommConnect()

        self.updater = Updater(self.kiwoomQ)
        self.updater.signal1.connect(self.ReceivOrder)
        self.updater.signal2.connect(self.ChangeDictset)
        self.updater.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.Scheduler)
        self.qtimer.start()

        app.exec_()

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect()')
        while not self.dict_bool['로그인']:
            qtest_qwait(0.01)

        qtest_qwait(5)
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료')))
        text = '주식 시스템을 시작하였습니다.'
        if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', text))
        self.kwzservQ.put(('tele', text))

        self.str_account = self.GetAccountNumber()
        tuple_kosd = tuple(self.GetCodeListByMarket('10'))
        self.list_code = self.GetCodeListByMarket('0') + self.GetCodeListByMarket('8') + list(tuple_kosd)
        self.dict_sgbn = {code: i % 8 for i, code in enumerate(self.list_code)}
        self.dict_name = {code: self.GetMasterCodeName(code) for code in self.list_code}
        dict_code = {name: code for code, name in self.dict_name.items()}

        self.kwzservQ.put(('window', (ui_num['종목명데이터'], self.dict_name, dict_code)))
        self.sreceivQ.put(('종목정보', (tuple_kosd, self.dict_sgbn, self.dict_name, dict_code)))
        self.straderQ.put(('종목정보', (self.dict_sgbn, self.dict_name)))
        for q in self.sstgQs:
            q.put(('코스닥목록', tuple_kosd))

        df = pd.DataFrame(self.dict_name.values(), columns=['종목명'], index=list(self.dict_name))
        df['코스닥'] = [True if x in tuple_kosd else False for x in df.index]
        self.kwzservQ.put(('query', ('종목디비', df, 'stockinfo', 'replace')))

        self.GetConditionLoad()
        error = True
        while error:
            qtest_qwait(2)
            self.list_cond = self.GetConditionNamelist()
            try:
                if self.list_cond[0][0] == 0 and self.list_cond[1][0] == 1:
                    self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 조건검색식 불러오기 완료')))
            except:
                print('조건검색식 불러오기 실패, 2초후 재시도합니다.')
            else:
                error = False
                self.kwzservQ.put(('window', (ui_num['S단순텍스트'], self.list_cond)))

    def GetAccountNumber(self):
        return self.ocx.dynamicCall('GetLoginInfo(QString)', 'ACCNO').split(';')[0]

    def GetCodeListByMarket(self, market):
        data = self.ocx.dynamicCall('GetCodeListByMarket(QString)', market)
        tokens = data.split(';')[:-1]
        return tokens

    def GetMasterCodeName(self, code):
        return self.ocx.dynamicCall('GetMasterCodeName(QString)', code)

    def GetConditionLoad(self):
        self.ocx.dynamicCall('GetConditionLoad()')
        while not self.dict_bool['CD로딩']:
            qtest_qwait(0.01)

    def GetConditionNamelist(self):
        data = self.ocx.dynamicCall('GetConditionNameList()')
        conditions = data.split(';')[:-1]
        list_cond = [[int(condition.split('^')[0]), condition.split('^')[1]] for condition in conditions]
        return list_cond

    def Scheduler(self):
        inthms = int(str_hms())
        if not self.dict_bool['계좌조회']:
            self.GetAccountjanGo()
        if self.dict_set['리시버공유'] < 2 and not self.dict_bool['실시간등록']:
            self.OperationRealreg()

        if not self.test_mode:
            if self.operation == 1:
                if 90100 < inthms and self.dict_set['휴무프로세스종료'] and not self.dict_bool['프로세스종료']:
                    self.ProcessKill()
            elif self.operation in (3, 2, 4):
                if self.dict_set['리시버공유'] < 2 and not self.dict_bool['실시간조건검색시작']:
                    self.ConditionSearchStart()
                if self.dict_set['주식전략종료시간'] < inthms and self.dict_set['주식프로세스종료'] and not self.dict_bool['프로세스종료']:
                    self.ProcessKill()
            elif self.operation == 8:
                if 153500 < inthms and not self.dict_bool['프로세스종료']:
                    self.ProcessKill()

    def GetAccountjanGo(self):
        self.dict_bool['계좌조회'] = True

        while True:
            df = self.Block_Request('opw00004', 계좌번호=self.str_account, 비밀번호='', 상장폐지조회구분=0, 비밀번호입력매체구분='00', output='계좌평가현황', next=0)
            if df['D+2추정예수금'][0]:
                yesugm = int(df['D+2추정예수금'][0]) if not self.dict_set['주식모의투자'] else 100_000_000
                break
            else:
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 오류가 발생하여 계좌평가현황을 재조회합니다.')))
                qtest_qwait(3.35)

        dict_jg = None
        if not self.dict_set['주식모의투자']:
            df = self.Block_Request('opw00018', 계좌번호=self.str_account, 비밀번호='', 비밀번호입력매체구분='00', 조회구분=2, output='계좌평가잔고개별합산', next=0)
            if df['종목명'][0]:
                df.rename(columns={'종목번호': 'index', '수익률(%)': '수익률'}, inplace=True)
                df['index'] = df['index'].apply(lambda x: x.strip()[1:])
                df['수익률'] = df['수익률'].apply(lambda x: round(float(x) / 100, 2))
                columns = ['매입가', '현재가', '평가손익', '매입금액', '평가금액', '보유수량']
                df[columns] = df[columns].astype(int)
                df['평가손익'] = df['평가금액'] - df['매입금액']
                df['분할매수횟수'] = 5
                df['분할매도횟수'] = 0
                df['매수시간'] = self.str_today + '080000'
                columns = ['index', '종목명', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                df = df[columns]
                df.set_index('index', inplace=True)
                dict_jg = df.to_dict('index')

        while True:
            df = self.Block_Request('opw00018', 계좌번호=self.str_account, 비밀번호='', 비밀번호입력매체구분='00', 조회구분=2, output='계좌평가결과', next=0)
            if df['추정예탁자산'][0]:
                jasan = int(df['추정예탁자산'][0]) if not self.dict_set['주식모의투자'] else yesugm
                break
            else:
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 오류가 발생하여 계좌평가결과를 재조회합니다.')))
                qtest_qwait(3.35)

        self.straderQ.put(('잔고조회', (yesugm, jasan, dict_jg)))
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 계좌 조회 완료')))

    def OperationRealreg(self):
        self.dict_bool['실시간등록'] = True

        self.SetRealReg([sn_oper, ' ', '215;20;214', 0])
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 장운영시간 등록 완료')))

        self.SetRealReg([sn_oper, '001;101', '10;15;20', 1])
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 업종지수 등록 완료')))

        self.Block_Request('opt10054', 시장구분='000', 장전구분='1', 종목코드='', 발동구분='1', 제외종목='000000000',
                           거래량구분='0', 거래대금구분='0', 발동방향='0', output='발동종목', next=0)
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - VI발동해제 등록 완료')))

        self.list_code = self.SendCondition([sn_cond, self.list_cond[1][1], self.list_cond[1][0], 0])
        if len(self.list_code) > 2400:
            print('조건검색식 설정이 잘못되었습니다.')
            print('감시종목수가 너무 많으니 조건검색식을 재설정하십시오.')

        k = 0
        for i in range(0, len(self.list_code), 100):
            rreg = [sn_gsjm + k, ';'.join(self.list_code[i:i + 100]), '10;12;14;30;228;41;61;71;81', 1]
            self.SetRealReg(rreg)
            text = f"실시간 알림 등록 완료 - [{sn_gsjm + k}] 종목갯수 {len(rreg[1].split(';'))}"
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], text)))
            k += 1

        if k < 10:
            print('조건검색식 설정이 잘못되었습니다.')
            print('감시종목수가 너무 적으니 조건검색식을 재설정하십시오.')

        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 실시간 등록 완료')))

    def SetRealReg(self, rreg):
        self.ocx.dynamicCall('SetRealReg(QString, QString, QString, QString)', rreg)

    def ConditionSearchStart(self):
        self.dict_bool['실시간조건검색시작'] = True
        codes = self.SendCondition([sn_cond, self.list_cond[0][1], self.list_cond[0][0], 1])
        if len(codes) > 0:
            self.sreceivQ.put(('실시간조건검색시작', codes))
        if len(codes) > 100:
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - 조건검색식 0번이 잘못되었습니다. HTS에서 확인하십시오.')))
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 실시간조건검색 0번 등록 완료')))

    def ProcessKill(self):
        self.dict_bool['프로세스종료'] = True
        self.ConditionSearchStop()
        self.RemoveAllRealreg()
        if self.dict_set['주식알림소리']:
            self.kwzservQ.put(('sound', '주식 시스템을 3분 후 종료합니다.'))
        self.sreceivQ.put('프로세스종료')

    def ConditionSearchStop(self):
        self.SendConditionStop([sn_cond, self.list_cond[0][1], self.list_cond[0][0]])
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 실시간조건검색 0번 중단 완료')))

    def SendConditionStop(self, cond):
        self.ocx.dynamicCall("SendConditionStop(QString, QString, int)", cond)

    def RemoveAllRealreg(self):
        self.SetRealRemove(['ALL', 'ALL'])
        if self.dict_set['주식알림소리']:
            self.kwzservQ.put(('sound', '조건검색 및 실시간데이터의 수신을 중단하였습니다.'))

    def SetRealRemove(self, rreg):
        self.ocx.dynamicCall('SetRealRemove(QString, QString)', rreg)

    # noinspection PyUnusedLocal
    def OnReceiveMsg(self, sScrNo, sRQName, sTrCode, sMsg):
        print(f'[{now()}]{sScrNo} {sRQName} {sTrCode} {sMsg}')
        self.kwzservQ.put(('window', (ui_num['S오더텍스트'], f'{sMsg}')))
        if '매수증거금' in sMsg:
            sn = int(sScrNo)
            code = self.dict_sncd[sn] if sn in self.dict_sncd else ''
            self.straderQ.put(('증거금부족', code))

    def Block_Request(self, *args, **kwargs):
        trcode = args[0].lower()
        self.tr_fields = parseDat(trcode)
        rqname = kwargs['output']
        nnext  = kwargs['next']
        for i in kwargs:
            if i.lower() != 'output' and i.lower() != 'next':
                self.ocx.dynamicCall('SetInputValue(QString, QString)', i, kwargs[i])
        self.dict_bool['TR수신'] = False
        self.dict_bool['TR다음'] = False
        sn_num = sn_brrd if trcode == 'opt10054' else sn_brrq
        self.ocx.dynamicCall('CommRqData(QString, QString, int, QString)', rqname, trcode, nnext, sn_num)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            qtest_qwait(0.01)
        if trcode != 'opt10054':
            self.DisconnectRealData(sn_brrq)
        return self.tr_df

    def DisconnectRealData(self, screen):
        self.ocx.dynamicCall('DisconnectRealData(QString)', screen)

    def SendCondition(self, cond):
        self.dict_bool['CD수신'] = False
        self.ocx.dynamicCall('SendCondition(QString, QString, int, int)', cond)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['CD수신'] or datetime.datetime.now() < sleeptime:
            qtest_qwait(0.01)
        return self.tr_cdlist

    def OnEventConnect(self, err_code):
        if err_code == 0: self.dict_bool['로그인'] = True

    # noinspection PyUnusedLocal
    def OnReceiveConditionVer(self, ret, msg):
        if ret == 1: self.dict_bool['CD로딩'] = True

    # noinspection PyUnusedLocal
    def OnReceiveTrCondition(self, screen, code_list, cond_name, cond_index, nnext):
        codes = code_list.split(';')[:-1]
        self.tr_cdlist = codes
        self.dict_bool['CD수신'] = True

    # noinspection PyUnusedLocal
    def OnReceiveTrData(self, screen, rqname, trcode, record, nnext):
        if 'ORD' in trcode: return
        self.dict_bool['TR다음'] = True if nnext == '2' else False
        fields = self.tr_fields[rqname]
        rows   = self.ocx.dynamicCall('GetRepeatCnt(QString, QString)', trcode, rqname)
        if rows == 0: rows = 1
        data_list = []
        for row in range(rows):
            row_data = []
            for item in fields:
                data = self.ocx.dynamicCall('GetCommData(QString, QString, int, QString)', trcode, rqname, row, item)
                row_data.append(data.strip())
            data_list.append(row_data)
        self.tr_df = pd.DataFrame(data_list, columns=fields)
        self.dict_bool['TR수신'] = True

    # noinspection PyUnusedLocal
    def OnReceiveRealCondition(self, code, IorD, cname, cindex):
        if self.dict_bool['프로세스종료']:
            return
        if IorD == 'I':
            self.sreceivQ.put(('관심진입', code))
        elif IorD == 'D':
            self.sreceivQ.put(('관심이탈', code))

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
                self.kwzservQ.put(('sound', f"{self.str_today[:4]}년 {self.str_today[4:6]}월 "
                                            f"{self.str_today[6:]}일 장이 시작되었습니다."))
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
                self.kwzservQ.put(('sound', f"{self.str_today[:4]}년 {self.str_today[4:6]}월 "
                                            f"{self.str_today[6:]}일 장이 종료되었습니다."))

    def OnReceiveRealData(self, code, realtype, realdata):
        if self.dict_bool['프로세스종료']:
            return

        if realtype == '장시작시간':
            try:
                self.operation = int(self.GetCommRealData(code, 215))
                current            = self.GetCommRealData(code, 20)
                remain             = self.GetCommRealData(code, 214)
            except:
                pass
            else:
                self.OperationAlert(current)
                self.kwzservQ.put(
                    (
                        'window',
                        (
                            ui_num['S단순텍스트'],
                            f'장운영 시간 수신 알림 - {self.operation} {current[:2]}:{current[2:4]}:{current[4:]} '
                            f'남은시간 {remain[:2]}:{remain[2:4]}:{remain[4:]}'
                        )
                    )
                )

        elif realtype == '업종지수':
            try:
                dt = int(self.str_today + self.GetCommRealData(code, 20))
                c  = round(abs(float(self.GetCommRealData(code, 10))) / 100, 2)
            except:
                pass
            else:
                self.kwzservQ.put(('chart', ('코스피' if code == '001' else '코스닥', dt, c)))

        elif realtype == 'VI발동/해제':
            try:
                gubun = self.GetCommRealData(code, 9068)
                code  = self.GetCommRealData(code, 9001).strip('A').strip('Q')
                name  = self.dict_name[code]
            except:
                pass
            else:
                self.sreceivQ.put(('VI발동해제', (gubun, code, name)))

        elif realtype == '주식체결':
            dt = self.GetCommRealData(code, 20)
            if int(dt) < 90000:
                return

            try:
                if not self.dict_bool['주식체결필드확인']:
                    data = realdata.split('\t')
                    if data[0]                             == self.GetCommRealData(code, 20) and \
                            abs(int(data[1]))      == abs(int(self.GetCommRealData(code, 10))) and \
                            float(data[3])           == float(self.GetCommRealData(code, 12)) and \
                            data[6]                        == self.GetCommRealData(code, 15) and \
                            int(data[8])               == int(self.GetCommRealData(code, 14)) and \
                            abs(int(data[9]))      == abs(int(self.GetCommRealData(code, 16))) and \
                            abs(int(data[10]))     == abs(int(self.GetCommRealData(code, 17))) and \
                            abs(int(data[11]))     == abs(int(self.GetCommRealData(code, 18))) and \
                            float(data[18])          == float(self.GetCommRealData(code, 228)) and \
                            int(data[14])              == int(self.GetCommRealData(code, 29)) and \
                            abs(float(data[15])) == abs(float(self.GetCommRealData(code, 30))) and \
                            float(data[16])          == float(self.GetCommRealData(code, 31)) and \
                            float(data[25]) / 100    == float(self.GetCommRealData(code, 851)) / 100 and \
                            int(data[19])              == int(self.GetCommRealData(code, 311)) and \
                            int(data[4])               == int(self.GetCommRealData(code, 27)) and \
                            int(data[5])               == int(self.GetCommRealData(code, 28)):
                        self.dict_bool['주식체결필드같음'] = True
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 주식체결 필드값 같음')))
                    else:
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 주식체결 필드값이 다릅니다. 필드값 갱신요망!!')))
                    self.dict_bool['주식체결필드확인'] = True

                dt = int(self.str_today + dt)
                if self.dict_bool['주식체결필드같음']:
                    data  = realdata.split('\t')
                    c     = abs(int(data[1]))
                    per     = float(data[3])
                    v             = data[6]
                    dm        = int(data[8])
                    o     = abs(int(data[9]))
                    h     = abs(int(data[10]))
                    low   = abs(int(data[11]))
                    ch      = float(data[18])
                    dmp       = int(data[14])
                    jvp = abs(float(data[15]))
                    vrp     = float(data[16])
                    jsvp    = float(data[25]) / 100
                    sgta      = int(data[19])
                    csp       = int(data[4])
                    cbp       = int(data[5])
                else:
                    c     = abs(int(self.GetCommRealData(code, 10)))
                    per     = float(self.GetCommRealData(code, 12))
                    v             = self.GetCommRealData(code, 15)
                    dm        = int(self.GetCommRealData(code, 14))
                    o     = abs(int(self.GetCommRealData(code, 16)))
                    h     = abs(int(self.GetCommRealData(code, 17)))
                    low   = abs(int(self.GetCommRealData(code, 18)))
                    ch      = float(self.GetCommRealData(code, 228))
                    dmp       = int(self.GetCommRealData(code, 29))
                    jvp = abs(float(self.GetCommRealData(code, 30)))
                    vrp     = float(self.GetCommRealData(code, 31))
                    jsvp    = float(self.GetCommRealData(code, 851)) / 100
                    sgta      = int(self.GetCommRealData(code, 311))
                    csp       = int(self.GetCommRealData(code, 27))
                    cbp       = int(self.GetCommRealData(code, 28))
            except:
                pass
            else:
                self.sreceivQ.put(('체결정보', (code, dt, c, o, h, low, per, dm, v, ch, dmp, jvp, vrp, jsvp, sgta, csp, cbp)))

        elif realtype == '주식호가잔량':
            dt = self.GetCommRealData(code, 21)
            if int(dt) < 90000:
                return

            try:
                start = now()
                if not self.dict_bool['호가잔량필드확인']:
                    data = realdata.split('\t')
                    if int(data[61])               == int(self.GetCommRealData(code, 121)) and \
                            int(data[63])          == int(self.GetCommRealData(code, 125)) and \
                            abs(int(data[55])) == abs(int(self.GetCommRealData(code, 50))) and \
                            abs(int(data[49])) == abs(int(self.GetCommRealData(code, 49))) and \
                            abs(int(data[43])) == abs(int(self.GetCommRealData(code, 48))) and \
                            abs(int(data[37])) == abs(int(self.GetCommRealData(code, 47))) and \
                            abs(int(data[31])) == abs(int(self.GetCommRealData(code, 46))) and \
                            abs(int(data[25])) == abs(int(self.GetCommRealData(code, 45))) and \
                            abs(int(data[19])) == abs(int(self.GetCommRealData(code, 44))) and \
                            abs(int(data[13])) == abs(int(self.GetCommRealData(code, 43))) and \
                            abs(int(data[7]))  == abs(int(self.GetCommRealData(code, 42))) and \
                            abs(int(data[1]))  == abs(int(self.GetCommRealData(code, 41))) and \
                            abs(int(data[4]))  == abs(int(self.GetCommRealData(code, 51))) and \
                            abs(int(data[10])) == abs(int(self.GetCommRealData(code, 52))) and \
                            abs(int(data[16])) == abs(int(self.GetCommRealData(code, 53))) and \
                            abs(int(data[22])) == abs(int(self.GetCommRealData(code, 54))) and \
                            abs(int(data[28])) == abs(int(self.GetCommRealData(code, 55))) and \
                            abs(int(data[34])) == abs(int(self.GetCommRealData(code, 56))) and \
                            abs(int(data[40])) == abs(int(self.GetCommRealData(code, 57))) and \
                            abs(int(data[46])) == abs(int(self.GetCommRealData(code, 58))) and \
                            abs(int(data[52])) == abs(int(self.GetCommRealData(code, 59))) and \
                            abs(int(data[58])) == abs(int(self.GetCommRealData(code, 60))) and \
                            int(data[56])          == int(self.GetCommRealData(code, 70)) and \
                            int(data[50])          == int(self.GetCommRealData(code, 69)) and \
                            int(data[44])          == int(self.GetCommRealData(code, 68)) and \
                            int(data[38])          == int(self.GetCommRealData(code, 67)) and \
                            int(data[32])          == int(self.GetCommRealData(code, 66)) and \
                            int(data[26])          == int(self.GetCommRealData(code, 65)) and \
                            int(data[20])          == int(self.GetCommRealData(code, 64)) and \
                            int(data[14])          == int(self.GetCommRealData(code, 63)) and \
                            int(data[8])           == int(self.GetCommRealData(code, 62)) and \
                            int(data[2])           == int(self.GetCommRealData(code, 61)) and \
                            int(data[5])           == int(self.GetCommRealData(code, 71)) and \
                            int(data[11])          == int(self.GetCommRealData(code, 72)) and \
                            int(data[17])          == int(self.GetCommRealData(code, 73)) and \
                            int(data[23])          == int(self.GetCommRealData(code, 74)) and \
                            int(data[29])          == int(self.GetCommRealData(code, 75)) and \
                            int(data[35])          == int(self.GetCommRealData(code, 76)) and \
                            int(data[41])          == int(self.GetCommRealData(code, 77)) and \
                            int(data[47])          == int(self.GetCommRealData(code, 78)) and \
                            int(data[53])          == int(self.GetCommRealData(code, 79)) and \
                            int(data[59])          == int(self.GetCommRealData(code, 80)):
                        self.dict_bool['호가잔량필드같음'] = True
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 실행 알림 - 주식호가잔량 필드값 같음')))
                    else:
                        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - 주식호가잔량 필드값이 다릅니다. 필드값 갱신요망!!')))
                    self.dict_bool['호가잔량필드확인'] = True

                name = self.dict_name[code]
                dt = int(self.str_today + dt)
                if self.dict_bool['호가잔량필드같음']:
                    data = realdata.split('\t')
                    hoga_tamount = (
                        int(data[61]), int(data[63])
                    )
                    hoga_seprice = (
                        abs(int(data[55])), abs(int(data[49])), abs(int(data[43])), abs(int(data[37])), abs(int(data[31])),
                        abs(int(data[25])), abs(int(data[19])), abs(int(data[13])), abs(int(data[7])), abs(int(data[1]))
                    )
                    hoga_buprice = (
                        abs(int(data[4])), abs(int(data[10])), abs(int(data[16])), abs(int(data[22])), abs(int(data[28])),
                        abs(int(data[34])), abs(int(data[40])), abs(int(data[46])), abs(int(data[52])), abs(int(data[58]))
                    )
                    hoga_samount = (
                        int(data[56]), int(data[50]), int(data[44]), int(data[38]), int(data[32]),
                        int(data[26]), int(data[20]), int(data[14]), int(data[8]), int(data[2])
                    )
                    hoga_bamount = (
                        int(data[5]), int(data[11]), int(data[17]), int(data[23]), int(data[29]),
                        int(data[35]), int(data[41]), int(data[47]), int(data[53]), int(data[59])
                    )
                else:
                    hoga_tamount = (
                        int(self.GetCommRealData(code, 121)),
                        int(self.GetCommRealData(code, 125))
                    )
                    hoga_seprice = (
                        abs(int(self.GetCommRealData(code, 50))),
                        abs(int(self.GetCommRealData(code, 49))),
                        abs(int(self.GetCommRealData(code, 48))),
                        abs(int(self.GetCommRealData(code, 47))),
                        abs(int(self.GetCommRealData(code, 46))),
                        abs(int(self.GetCommRealData(code, 45))),
                        abs(int(self.GetCommRealData(code, 44))),
                        abs(int(self.GetCommRealData(code, 43))),
                        abs(int(self.GetCommRealData(code, 42))),
                        abs(int(self.GetCommRealData(code, 41)))
                    )
                    hoga_buprice = (
                        abs(int(self.GetCommRealData(code, 51))),
                        abs(int(self.GetCommRealData(code, 52))),
                        abs(int(self.GetCommRealData(code, 53))),
                        abs(int(self.GetCommRealData(code, 54))),
                        abs(int(self.GetCommRealData(code, 55))),
                        abs(int(self.GetCommRealData(code, 56))),
                        abs(int(self.GetCommRealData(code, 57))),
                        abs(int(self.GetCommRealData(code, 58))),
                        abs(int(self.GetCommRealData(code, 59))),
                        abs(int(self.GetCommRealData(code, 60)))
                    )
                    hoga_samount = (
                        int(self.GetCommRealData(code, 70)),
                        int(self.GetCommRealData(code, 69)),
                        int(self.GetCommRealData(code, 68)),
                        int(self.GetCommRealData(code, 67)),
                        int(self.GetCommRealData(code, 66)),
                        int(self.GetCommRealData(code, 65)),
                        int(self.GetCommRealData(code, 64)),
                        int(self.GetCommRealData(code, 63)),
                        int(self.GetCommRealData(code, 62)),
                        int(self.GetCommRealData(code, 61))
                    )
                    hoga_bamount = (
                        int(self.GetCommRealData(code, 71)),
                        int(self.GetCommRealData(code, 72)),
                        int(self.GetCommRealData(code, 73)),
                        int(self.GetCommRealData(code, 74)),
                        int(self.GetCommRealData(code, 75)),
                        int(self.GetCommRealData(code, 76)),
                        int(self.GetCommRealData(code, 77)),
                        int(self.GetCommRealData(code, 78)),
                        int(self.GetCommRealData(code, 79)),
                        int(self.GetCommRealData(code, 80))
                    )
            except:
                pass
            else:
                lastprice = self.GetMasterLastPrice(code)
                self.sreceivQ.put(('호가정보', (dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, name, start, lastprice)))

    # noinspection PyUnusedLocal
    def OnReceiveChejanData(self, gubun, itemcnt, fidlist):
        if self.dict_set['주식모의투자']:
            return

        if gubun == '0':
            try:
                종목코드 = self.GetChejanData(9001).strip('A')
                종목명 = self.dict_name[종목코드]
                주문상태 = self.GetChejanData(913)
                주문구분 = self.GetChejanData(905)[1:]
                주문가격 = int(self.GetChejanData(901))
                주문수량 = int(self.GetChejanData(900))
                미체결수량 = int(self.GetChejanData(902))
                주문번호 = self.GetChejanData(9203)
                최우선매도호가 = abs(int(self.GetChejanData(27)))
                주문시간 = self.str_today + self.GetChejanData(908)
            except Exception as e:
                self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - OnReceiveChejanData 0 {e}')))
            else:
                try:
                    체결가격 = int(self.GetChejanData(914))
                    체결수량 = int(self.GetChejanData(915))
                except:
                    체결가격 = 0
                    체결수량 = 0
                self.straderQ.put(('체잔통보', (종목코드, 종목명, 최우선매도호가, 주문상태, 주문구분, 주문수량, 체결수량, 미체결수량, 주문가격, 체결가격, 주문시간, 주문번호)))

    def GetCommRealData(self, code, fid):
        return self.ocx.dynamicCall('GetCommRealData(QString, int)', code, fid)

    def GetChejanData(self, fid):
        return self.ocx.dynamicCall('GetChejanData(int)', fid)

    def ReceivOrder(self, order):
        # [주문구분, 화면번호, 계좌번호, 주문유형, 종목코드, 주문수량, 주문가격, 거래구분, 원주문번호], 종목명, 시그널시간
        curr_time = now()
        if curr_time < self.order_time:
            next_time = (self.order_time - curr_time).total_seconds()
            QTimer.singleShot(int(next_time * 1000), lambda: self.SendOrder(order))
            return

        self.intg_odsn = self.intg_odsn + 1 if self.intg_odsn + 1 < 9000 else 3000
        order[1] = str(self.intg_odsn)
        order[2] = self.str_account

        주문구분, _, _, _, 종목코드, 주문수량, 주문가격, _, _, 종목명, 시그널시간 = order

        self.OrderTimeLog(시그널시간)
        ret = self.SendOrder(order[:-2])
        if ret == 0:
            self.dict_sncd[self.intg_odsn] = 종목코드
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [주문전송] {종목명} | {주문가격} | {주문수량} | {주문구분}')))
            self.order_time = timedelta_sec(0.2)
        else:
            self.sstgQs[self.dict_sgbn[종목코드]].put((f'{주문구분}취소', 종목코드))
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'주문 관리 시스템 알림 - [주문실패] {종목명} | {주문가격} | {주문수량} | {주문구분}')))

    def SendOrder(self, order):
        return self.ocx.dynamicCall('SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)', order)

    def ChangeDictset(self, data):
        self.dict_set = data

    def OrderTimeLog(self, signal_time):
        gap = (now() - signal_time).total_seconds()
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'시그널 주문 시간 알림 - 발생시간과 주문시간의 차이는 [{gap:.6f}]초입니다.')))

    def GetMasterLastPrice(self, code):
        return int(self.ocx.dynamicCall('GetMasterLastPrice(QString)', code))
