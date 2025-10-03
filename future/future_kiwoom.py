import datetime
import pythoncom
import pandas as pd
from PyQt5.QAxContainer import QAxWidget


class Future:
    def __init__(self, user_class, gubun):
        self.dict_bool = {
            '로그인': False,
            'TR수신': False,
            'TR다음': False,
            '실시간등록': False
        }
        self.tr_df = None

        self.ocx = QAxWidget('KFOPENAPI.KFOpenAPICtrl.1')
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.ocx.OnReceiveTrData.connect(self.OnReceiveTrData)

        if gubun == 'Receiver':
            self.ocx.OnReceiveRealData.connect(user_class.OnReceiveRealData)
        elif gubun == 'Trader':
            self.ocx.OnReceiveMsg.connect(user_class.OnReceiveMsg)
            self.ocx.OnReceiveChejanData.connect(user_class.OnReceiveChejanData)

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect(0)')
        while not self.dict_bool['로그인']:
            pythoncom.PumpWaitingMessages()

    def OnEventConnect(self, err_code):
        if err_code == 0: self.dict_bool['로그인'] = True

    # noinspection PyUnusedLocal
    def OnReceiveTrData(self, screen, rqname, trcode, record, nnext):
        if 'ORD' in trcode:
            return

        if trcode == 'opt10001':
            self.dict_bool['실시간등록'] = True
            return

        self.dict_bool['TR다음'] = True if nnext == '2' else False
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
            columns  = ['종목코드', '포지션', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량']

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
                columns = ['매입가', '현재가', '수익률']
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
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '예수금조회', 'opw30009', '', 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            pythoncom.PumpWaitingMessages()
        return self.tr_df

    def GetJango(self, acc_num: str, pass_num: str) -> pd.DataFrame:
        self.dict_bool['TR수신'] = False
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '계좌번호', acc_num)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '비밀번호', pass_num)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '비밀번호입력매체', '00')
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '통화코드', 'USD')
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '잔고조회', 'opw30003', '', 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            pythoncom.PumpWaitingMessages()
        return self.tr_df

    def SearchDeposit(self, gubun: str) -> pd.DataFrame:
        self.dict_bool['TR수신'] = False
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '품목구분', gubun)
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '해외파생구분', 'FU')
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '파생품목코드', '')
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '삼품별명세및요약조회', 'opw50004', '', 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            pythoncom.PumpWaitingMessages()
        return self.tr_df

    def SearchInterest(self, codes: str) -> pd.DataFrame:
        self.dict_bool['TR수신'] = False
        self.ocx.dynamicCall('SetInputValue(QString, QString)', '종목코드', codes)
        self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '관심종목조회', 'opt10005', '', 1000)
        sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
        while not self.dict_bool['TR수신'] or datetime.datetime.now() < sleeptime:
            pythoncom.PumpWaitingMessages()
        self.DisconnectRealData()
        return self.tr_df

    def SetRealReg(self, code_list: list):
        sn = '1001'
        for code in code_list:
            self.dict_bool['실시간등록'] = False
            self.ocx.dynamicCall('SetInputValue(QString, QString)', '종목코드', code)
            self.ocx.dynamicCall('CommRqData(QString, QString, QString, QString)', '실시간시세등록', 'opt10001', '', sn)
            sleeptime = datetime.datetime.now() + datetime.timedelta(seconds=0.25)
            while not self.dict_bool['실시간등록'] or datetime.datetime.now() < sleeptime:
                pythoncom.PumpWaitingMessages()
            sn = str(int(sn) + 1)

    def ShowAccountWindow(self):
        self.ocx.dynamicCall('GetCommonFunc(QString, QString)', 'ShowAccountWindow', '')

    def GetAccountNumber(self):
        return self.ocx.dynamicCall('GetLoginInfo(QString)', 'ACCNO').split(';')[0]

    def DisconnectRealData(self):
        return self.ocx.dynamicCall('DisconnectRealData(QString)', 1000)

    def GetGlobalFutureCodelist(self, code: str) -> str:
        return self.ocx.dynamicCall('GetGlobalFutureCodelist(QString)', code)

    def GetCommRealData(self, code: str, fid: int):
        return self.ocx.dynamicCall('GetCommRealData(QString, int)', code, fid)

    def GetChejanData(self, fid: int):
        return self.ocx.dynamicCall('GetChejanData(int)', fid)

    def SendOrder(self, order: list):
        """
        sRQName     STR     사용사지정명
        sScreenNo   STR     화면번호
        sAccNo      STR     계좌번호
        nOrderType  LONG    주문유형 (1:신규매도, 2:신규매수 3:매도취소, 4:매수취소, 5:매도정정, 6:매수정정)
        sCode       STR     종목코드
        nQty        LONG    주문수량
        sPrice      STR     주문단가
        sStop       STR     Stop단가
        sHogaGb     STR     거래구분 (1:시장가, 2:지정가, 3:STOP, 4:STOP LIMIT)
        sOrgOrderNo STR     원주문번호
        """
        return self.ocx.dynamicCall('SendOrder(QString, QString, QString, int, QString, int, QString, QString, QString, QString)', order)
