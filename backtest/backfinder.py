
import re
import sys
import time
import sqlite3
import pandas as pd
from traceback import format_exc
from utility.static import now, str_ymdhms
from utility.setting_base import DB_STRATEGY, DB_BACKTEST, ui_num


class BackFinder:
    def __init__(self, sc, wq, sq, tq, lq, beq_list, ui_gubun, dict_set, avgtime, startday, endday, starttime,
                 endtime, buystg_name, back_count):
        self.shared_cnt  = sc
        self.wq          = wq
        self.sq          = sq
        self.tq          = tq
        self.lq          = lq
        self.beq_list    = beq_list
        self.ui_gubun    = ui_gubun
        self.dict_set    = dict_set
        self.avgtime     = int(avgtime)
        self.startday    = int(startday)
        self.endday      = int(endday)
        self.starttime   = int(starttime)
        self.endtime     = int(endtime)
        self.buystg_name = buystg_name
        self.back_count  = back_count

        if self.ui_gubun == 'S':
            self.gubun   = 'stock'
        elif self.ui_gubun == 'SF':
            self.gubun   = 'future'
        else:
            self.gubun   = 'coin'

        self.start_time = now()
        try:
            self.Start()
        except SystemExit:
            sys.exit()
        except:
            self.wq.put((ui_num['시스템로그'], format_exc()))
            self.SysExit(True)

    def Start(self):
        con = sqlite3.connect(DB_STRATEGY)
        dfb = pd.read_sql(f'SELECT * FROM {self.gubun}buy', con).set_index('index')
        con.close()

        buystg = dfb['전략코드'][self.buystg_name]
        cols_match = re.search(r"self\.tickcols\s*=\s*\[(.*?)]", buystg, re.DOTALL)
        data_match = re.search(r"self\.tickdata\s*=\s*\[(.*?)]", buystg, re.DOTALL)
        if cols_match and data_match:
            cols_text  = cols_match.group(1)
            data_text  = data_match.group(1)
            data_text  = re.findall(r'([^(,\s]+(?:\([^)]*\))?)', data_text)
            cols_count = len(re.findall(r"'[^']*'", cols_text)) + len(re.findall(r'"[^"]*"', cols_text))
            data_count = len([x for x in data_text if x.strip()])
            if cols_count != data_count:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], 'self.tickcols의 개수와 self.tickdata의 개수가 일치하지 않습니다.'))
                self.SysExit(True)
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '선택된 전략이 백파인더용 전략이 아닙니다.'))
            self.SysExit(True)

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 START'))
        self.shared_cnt.value = 0
        data = ('백테정보', self.avgtime, self.startday, self.endday, self.starttime, self.endtime, buystg, 2)
        for q in self.beq_list:
            q.put(data)

        bc = 0
        index = 0
        complete = False
        dict_back = {}
        while True:
            data = self.tq.get()
            if data[0] == '백파결과':
                _, data1, data2 = data
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], data2))
                dict_back[index] = dict(zip(data1, data2))
                index += 1

            elif data == '백테완료':
                bc += 1
                if bc == self.back_count:
                    complete = True

            elif data == '백테중지':
                self.SysExit(True)

            if complete and self.tq.empty():
                break

        if dict_back:
            save_time = str_ymdhms()
            con = sqlite3.connect(DB_BACKTEST)
            df = pd.DataFrame.from_dict(dict_back, orient='index')
            df.to_sql(f"{self.gubun}_bf_{self.buystg_name}_{save_time}", con, if_exists='append', chunksize=1000)
            con.close()
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인터 결과값 저장 완료'))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '조건을 만족하는 종목이 없어 결과를 표시할 수 없습니다.'))

        self.sq.put('백파인더를 완료하였습니다.')
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'백파인더 소요시간 {now() - self.start_time}'))
        if self.dict_set['스톰라이브']: self.lq.put('백파인더')
        self.SysExit(False)

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 STOP'))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백파인더 COMPLETE'))
        time.sleep(1)
        sys.exit()
