import sys
import time
import sqlite3
import pandas as pd
from multiprocessing import Process
from utility.static import strf_time, now
from utility.setting import DB_STRATEGY, DB_BACKTEST, ui_num, DICT_SET


class Total:
    def __init__(self, wq, sq, tq, bq, ui_gubun, gubun):
        self.wq           = wq
        self.sq           = sq
        self.tq           = tq
        self.bq           = bq
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
        self.df_back      = None

        self.MainLoop()

    def MainLoop(self):
        bc = 0
        index = 0
        start = now()
        while True:
            data = self.tq.get()
            if data[0] == '백파결과':
                data = data[1:]
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], data))
                self.df_back.loc[index] = data
                index += 1

            elif data[0] == '백테완료':
                bc += 1
                self.wq.put((ui_num[f'{self.ui_gubun}백테바'], bc, self.back_count, start))
                if bc == self.back_count:
                    break

            elif data[0] == '백테정보':
                self.avgtime     = data[1]
                self.startday    = data[2]
                self.endday      = data[3]
                self.starttime   = data[4]
                self.endtime     = data[5]
                self.buystg_name = data[6]
                self.back_count  = data[7]
                self.df_back     = pd.DataFrame(columns=['종목코드', '체결시간'] + data[8])

            elif data == '백테중지':
                try:
                    self.bq.put('백테중지')
                except:
                    pass
                time.sleep(1)
                sys.exit()

        if len(self.df_back) > 0:
            save_time = strf_time('%Y%m%d%H%M%S')
            con = sqlite3.connect(DB_BACKTEST)
            self.df_back.to_sql(f"{self.gubun}_bf_{self.buystg_name}_{save_time}", con, if_exists='append', chunksize=1000)
            con.close()
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인터 결과값 저장 완료'))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '조건을 만족하는 종목이 없어 결과를 표시할 수 없습니다.'))
        self.sq.put('백파인더를 완료하였습니다.')
        self.bq.put('백파인더 완료')
        time.sleep(1)
        sys.exit()


class BackFinder:
    def __init__(self, wq, bq, sq, tq, lq, beq_list, ui_gubun):
        self.wq       = wq
        self.bq       = bq
        self.sq       = sq
        self.tq       = tq
        self.lq       = lq
        self.beq_list = beq_list
        self.ui_gubun = ui_gubun
        self.dict_set = DICT_SET
        self.gubun    = 'stock' if self.ui_gubun == 'S' else 'coin'
        self.tickcols = None
        self.Start()

    def Start(self):
        self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
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
        if 'self.tickcols' not in buystg:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '선택된 전략이 백파인더용 전략이 아닙니다.'))
            self.SysExit(True)

        buystg_ = buystg.split('self.tickcols = [')[1].split(']')[0]
        self.tickcols = [x.strip() for x in buystg_.split(',')]
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 매수전략 설정 완료'))

        Process(target=Total, args=(self.wq, self.sq, self.tq, self.bq, self.ui_gubun, self.gubun)).start()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 집계용 프로세스 생성 완료'))

        self.tq.put(('백테정보', avgtime, startday, endday, starttime, endtime, buystg_name, back_count, self.tickcols))
        data = ('백테정보', avgtime, startday, endday, starttime, endtime, buystg, None)
        for q in self.beq_list:
            q.put(data)

        data = self.bq.get()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'백파인더 소요시간 {now() - start_time}'))
        if self.dict_set['스톰라이브']: self.lq.put('백파인더')
        self.SysExit(False) if data == '백파인더 완료' else self.SysExit(True)

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 완료'))
        time.sleep(1)
        sys.exit()
