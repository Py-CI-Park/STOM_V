
import sys
import time
import sqlite3
import pandas as pd
from multiprocessing import Process, Queue
from utility.static import now, str_ymdhms
from utility.setting_base import DB_STRATEGY, DB_BACKTEST, ui_num


class Total:
    def __init__(self, wq, sq, tq, mq, ui_gubun, gubun):
        self.wq           = wq
        self.sq           = sq
        self.tq           = tq
        self.mq           = mq
        self.ui_gubun     = ui_gubun
        self.gubun        = gubun
        if self.ui_gubun == 'CF': self.gubun = 'coin_future'

        self.back_count   = None
        self.buystg_name  = None
        self.startday     = None
        self.endday       = None
        self.starttime    = None
        self.endtime      = None
        self.avgtime      = None
        self.tickcols     = None
        self.dict_back    = {}

        self.MainLoop()

    def MainLoop(self):
        bc = 0
        index = 0
        complete = False
        while True:
            data = self.tq.get()
            if data[0] == '백파결과':
                data = data[1:]
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], data))
                self.dict_back[index] = dict(zip(self.tickcols, data))
                index += 1

            elif data == '백테완료':
                bc += 1
                if bc == self.back_count:
                    complete = True

            elif data[0] == '백테정보':
                self.avgtime     = data[1]
                self.startday    = data[2]
                self.endday      = data[3]
                self.starttime   = data[4]
                self.endtime     = data[5]
                self.buystg_name = data[6]
                self.back_count  = data[7]
                self.tickcols    = data[8]

            elif data == '백테중지':
                self.mq.put('백테중지')
                break

            if complete and self.tq.empty():
                break

        if complete:
            if self.dict_back:
                save_time = str_ymdhms()
                con = sqlite3.connect(DB_BACKTEST)
                df = pd.DataFrame.from_dict(self.dict_back, orient='index')
                df.to_sql(f"{self.gubun}_bf_{self.buystg_name}_{save_time}", con, if_exists='append', chunksize=1000)
                con.close()
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인터 결과값 저장 완료'))
            else:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '조건을 만족하는 종목이 없어 결과를 표시할 수 없습니다.'))

            self.sq.put('백파인더를 완료하였습니다.')
            self.mq.put('백파인더 완료')

        time.sleep(1)
        sys.exit()


class BackFinder:
    def __init__(self, sc, wq, bq, sq, tq, lq, beq_list, ui_gubun, dict_set):
        self.shared_cnt = sc
        self.wq         = wq
        self.bq         = bq
        self.sq         = sq
        self.tq         = tq
        self.lq         = lq
        self.beq_list   = beq_list
        self.ui_gubun   = ui_gubun
        self.dict_set   = dict_set
        if self.ui_gubun == 'S':
            self.gubun = 'stock'
        elif self.ui_gubun == 'SF':
            self.gubun = 'future'
        else:
            self.gubun = 'coin'

        self.Start()

    def Start(self):
        start_time = now()
        data = self.bq.get()
        avgtime   = int(data[0])
        startday  = int(data[1])
        endday    = int(data[2])
        starttime = int(data[3])
        endtime   = int(data[4])
        buystg_name   = data[5]
        back_count    = data[6]

        con = sqlite3.connect(DB_STRATEGY)
        dfb = pd.read_sql(f'SELECT * FROM {self.gubun}buy', con).set_index('index')
        con.close()

        buystg = dfb['전략코드'][buystg_name]
        if 'self.tickcols' not in buystg or 'self.tickdata' not in buystg:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '선택된 전략이 백파인더용 전략이 아닙니다.'))
            self.SysExit(True)
        colm_list = buystg.split('self.tickcols = [', 1)[1].split(']', 1)[0].split(',')
        data_list = buystg.split('self.tickdata = [', 1)[1].split(']', 1)[0].split(',')
        if len(colm_list) != len(data_list):
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '칼럼명 리스트와 데이터 리스트의 길이가 다릅니다.'))
            self.SysExit(True)

        tickcols = ['종목코드', '체결시간'] + [x.strip() for x in colm_list]
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 매수전략 설정 완료'))

        mq = Queue()
        Process(target=Total, args=(self.wq, self.sq, self.tq, mq, self.ui_gubun, self.gubun)).start()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 집계용 프로세스 생성 완료'))

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 START'))

        self.shared_cnt.value = 0
        self.tq.put(('백테정보', avgtime, startday, endday, starttime, endtime, buystg_name, back_count, tickcols))
        data = ('백테정보', avgtime, startday, endday, starttime, endtime, buystg, 2)
        for q in self.beq_list:
            q.put(data)

        data = mq.get()
        if data != '백파인더 완료': self.SysExit(True)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'백파인더 소요시간 {now() - start_time}'))
        if self.dict_set['스톰라이브']: self.lq.put('백파인더')
        self.SysExit(False)

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 STOP'))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 COMPLETE'))
        time.sleep(1)
        sys.exit()
