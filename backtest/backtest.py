
import re
import sys
import time
import sqlite3
import numpy as np
import pandas as pd
from traceback import format_exc
from backtest.back_static_numba import GetResult, bootstrap_test
from backtest.back_static import PlotShow, GetMoneytopQuery, GetResultDataframe, AddMdd
from utility.static import now, str_ymdhms
from utility.setting_user import stockreadlines, coinreadlines, futurereadlines
from utility.setting_base import DB_STRATEGY, DB_BACKTEST, ui_num, columns_vj, DB_STOCK_TICK_BACK, \
    DB_COIN_TICK_BACK, DB_STOCK_MIN_BACK, DB_COIN_MIN_BACK, DB_FUTURE_MIN_BACK, DB_FUTURE_TICK_BACK


class BackTest:
    def __init__(self, sc, wq, sq, tq, lq, teleQ, beq_list, bstq_list, backname, ui_gubun, dict_set, betting,
                 avgtime, startday, endday, starttime, endtime, buystg_name, sellstg_name, dict_cn, back_count,
                 blacklist, schedul, back_club):
        self.shared_cnt   = sc
        self.wq           = wq
        self.sq           = sq
        self.tq           = tq
        self.lq           = lq
        self.teleQ        = teleQ
        self.beq_list     = beq_list
        self.bstq_list    = bstq_list
        self.backname     = backname
        self.ui_gubun     = ui_gubun
        self.dict_set     = dict_set
        if self.ui_gubun not in ('CF', 'SF'):
            self.betting  = float(betting) * 1000000
        else:
            self.betting  = float(betting)
        self.avgtime      = int(avgtime)
        self.startday     = int(startday)
        self.endday       = int(endday)
        self.starttime    = int(starttime)
        self.endtime      = int(endtime)
        self.buystg_name  = buystg_name
        self.sellstg_name = sellstg_name
        self.dict_cn      = dict_cn
        self.back_count   = back_count
        self.blacklist    = blacklist
        self.schedul      = schedul
        self.back_club    = back_club

        self.buystg       = None
        self.sellstg      = None
        self.day_count    = None
        self.is_tick      = None

        if self.ui_gubun == 'S':
            self.gubun = 'stock'
            self.market_text = '주식'
        elif self.ui_gubun == 'SF':
            self.gubun = 'future'
            self.market_text = '주식'
        else:
            self.gubun = 'coin'
            self.market_text = '코인'

        gubun_text = f'{self.gubun}_future' if self.ui_gubun == 'CF' else self.gubun
        self.savename = f'{gubun_text}_bt'
        self.insertblacklist = []

        self.start_time = now()
        try:
            self.Start()
        except SystemExit:
            sys.exit()
        except:
            self.wq.put((ui_num['시스템로그'], format_exc()))
            self.SysExit(True)

    def Start(self):
        market_text = '주식' if self.ui_gubun in ('S', 'SF') else '코인'
        if self.ui_gubun == 'S':
            if self.dict_set[f'{market_text}타임프레임']:
                db = DB_STOCK_TICK_BACK
                self.is_tick = True
            else:
                db = DB_STOCK_MIN_BACK
                self.is_tick = False
        elif self.ui_gubun == 'SF':
            if self.dict_set[f'{market_text}타임프레임']:
                db = DB_FUTURE_TICK_BACK
                self.is_tick = True
            else:
                db = DB_FUTURE_MIN_BACK
                self.is_tick = False
        else:
            if self.dict_set[f'{market_text}타임프레임']:
                db = DB_COIN_TICK_BACK
                self.is_tick = True
            else:
                db = DB_COIN_MIN_BACK
                self.is_tick = False

        con   = sqlite3.connect(db)
        query = GetMoneytopQuery(self.is_tick, self.ui_gubun, self.startday, self.endday, self.starttime, self.endtime)
        df_mt = pd.read_sql(query, con)
        con.close()

        if len(df_mt) == 0 or self.back_count == 0:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '날짜 지정이 잘못되었거나 데이터가 존재하지 않습니다.'))
            self.SysExit(True)

        con = sqlite3.connect(DB_STRATEGY)
        dfb = pd.read_sql(f'SELECT * FROM {self.gubun}buy', con).set_index('index')
        dfs = pd.read_sql(f'SELECT * FROM {self.gubun}sell', con).set_index('index')
        con.close()

        buystg = dfb['전략코드'][self.buystg_name]
        if 'self.ms_analyzer' in buystg and not self.dict_set['시장미시구조분석']:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '시장미시구조분석 미적용 상태입니다. 설정을 변경하십시오.'))
            self.SysExit(True)

        if self.is_tick:
            df_mt['일자'] = (df_mt['index'].values // 1000000).astype(np.int64)
        else:
            df_mt['일자'] = (df_mt['index'].values // 10000).astype(np.int64)
        self.day_count = len(df_mt['일자'].unique())
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 기간 추출 완료'))

        self.buystg  = buystg
        self.sellstg = dfs['전략코드'][self.sellstg_name]
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 매도수전략 설정 완료'))

        arry_bct = np.zeros((len(df_mt), 3), dtype='float64')
        arry_bct[:, 0] = df_mt['index'].values
        data = ('백테정보', self.ui_gubun, None, None, arry_bct, self.betting, self.day_count)
        for q in self.bstq_list:
            q.put(data)

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} START'))
        self.shared_cnt.value = 0
        data = ('백테정보', self.betting, self.avgtime, self.startday, self.endday, self.starttime, self.endtime,
                self.buystg, self.sellstg, 2)
        for q in self.bstq_list:
            q.put(('백테시작', 2))
        for q in self.beq_list:
            q.put(data)

        bc = 0
        sc = 0
        while True:
            data = self.tq.get()
            if data == '백테완료':
                bc += 1
                if bc == self.back_count:
                    bc = 0
                    for q in self.bstq_list[:5]:
                        q.put(('백테완료', '일괄집계'))

            elif data == '수집완료':
                sc += 1
                if sc == 5:
                    sc = 0
                    for q in self.bstq_list[:5]:
                        q.put('결과집계')

            elif data[0] == '백테결과':
                _, list_tsg, arry_bct = data
                self.Report(list_tsg, arry_bct)
                break

            elif data == '백테중지':
                self.SysExit(True)

        if self.dict_set['스톰라이브']: self.lq.put(self.backname)
        self.SysExit(False)

    def Report(self, list_tsg, arry_bct):
        if not list_tsg:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '매수전략을 만족하는 경우가 없어 결과를 표시할 수 없습니다.'))
            self.SysExit(True)

        df_tsg, df_bct = GetResultDataframe(self.ui_gubun, list_tsg, arry_bct)
        if self.blacklist: self.InsertBlacklist(df_tsg)

        arry_tsg = np.array(df_tsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy(), dtype='float64')
        arry_bct = np.sort(arry_bct, axis=0)[::-1]
        result   = GetResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, self.day_count)
        result   = AddMdd(arry_tsg, result)
        tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result

        bootstrap_dist = bootstrap_test(df_tsg['수익률'].values / 100)
        bootstrap_avg  = round(np.mean(bootstrap_dist), 2)
        bootstrap_min  = round(np.percentile(bootstrap_dist, 2.5), 2)
        bootstrap_max  = round(np.percentile(bootstrap_dist, 97.5), 2)
        bootstrap_pv   = round(np.mean(bootstrap_dist > 0) * 100, 2)
        bootstrap_text = f"\n부트스트랩 평균수익률: {bootstrap_avg}%, 예상최소수익률: {bootstrap_min}%, 예상최대수익률: {bootstrap_max}%, 전략유의확률(pv): {bootstrap_pv}%"
        bootstrap_cmt  = f"\n이 전략은 95%의 확률로 [{bootstrap_min}~{bootstrap_max}%]의 수익률이 예상되며, 수익일 확률은 [{bootstrap_pv}%]입니다."

        startday, endday = str(self.startday), str(self.endday)
        startday = f'{startday[:4]}-{startday[4:6]}-{startday[6:]}'
        endday   = f'{endday[:4]}-{endday[4:6]}-{endday[6:]}'
        starttime, endtime = str(self.starttime).zfill(6), str(self.endtime).zfill(6)
        starttime = f'{starttime[:2]}:{starttime[2:4]}:{starttime[4:]}'
        endtime   = f'{endtime[:2]}:{endtime[2:4]}:{endtime[4:]}'

        bet_unit = '원' if self.ui_gubun in ('S', 'C') else '계약' if self.ui_gubun == 'SF' else 'USDT'
        tsg_unit = '원' if self.ui_gubun in ('S', 'C') else 'USD' if self.ui_gubun == 'SF' else 'USDT'
        bc_unit  = '초' if self.is_tick else '분'

        back_text  = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 거래일수 : {self.day_count}, 평균값계산틱수 : {self.avgtime}'
        label_text = f'종목당 배팅금액 {int(self.betting):,}{bet_unit}, 필요자금 {seed:,.0f}{tsg_unit}, 거래횟수 {tc}회, '\
                     f'일평균거래횟수 {atc:.1f}회, 적정최대보유종목수 {mhct}개, 평균보유기간 {ah:.2f}{bc_unit}, 익절 {pc}회, 손절 {mc}회\n'\
                     f'승률 {wr:.2f}%, 평균수익률 {app:.2f}%, 수익률합계 {tpp:.2f}%, 수익금합계 {tsg:,}{tsg_unit}, '\
                     f'최대낙폭금액 {mdd_:,.0f}{tsg_unit}, 최대낙폭률 {mdd:.2f}%, 매매성능지수 {tpi:.2f}, 연간예상수익률 {cagr:.2f}%'

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백테스팅 결과\n' + label_text))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '부트스트랩 결과' + bootstrap_text + bootstrap_cmt))

        if self.dict_set['스톰라이브']:
            data_list = [
                f'{startday}~{endday}', f'{starttime}~{endtime}', self.day_count, self.avgtime, int(self.betting),
                seed, tc, atc, mhct, ah, pc, mc, wr, app, tpp, mdd, tsg, cagr
            ]
            self.lq.put(('back', data_list))

        save_time = str_ymdhms()
        save_file_name = f'{self.savename}_{self.buystg_name}_{save_time}'

        if self.blacklist:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'블랙리스트 추가 {self.insertblacklist}'))
        self.sq.put(f'{self.backname}를 완료하였습니다.')
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 소요시간 {now() - self.start_time}'))

        if self.back_club:
            buystg_text  = ('\n'.join([x for x in self.buystg.split('if 매수:')[0].split('\n') if x and x[0] != '#'])).split(' ')
            buystg_text  = [x for x in buystg_text if x != '매수' and re.compile('[가-힣]+').findall(x)]
            buystg_text  = [x.replace('(', '').replace(')', '').replace(':', '').replace('\n', '') for x in set(buystg_text)]
            buy_vars = f"{'-' * 80} 매수변수목록 {'-' * 80}\n"
            for i, text in enumerate(buystg_text):
                if (i + 1) % 11 == 0:
                    buy_vars = f'{buy_vars}, {text},\n'
                elif i == 0 or i % 11 == 0:
                    buy_vars = f'{buy_vars}{text}'
                else:
                    buy_vars = f'{buy_vars}, {text}'
            sellstg_text = ('\n'.join([x for x in self.sellstg.split('if 매도:')[0].split('\n') if x and x[0] != '#'])).split(' ')
            sellstg_text = [x for x in sellstg_text if x != '매도' and re.compile('[가-힣]+').findall(x)]
            sellstg_text = [x.replace('(', '').replace(')', '').replace(':', '').replace('\n', '') for x in set(sellstg_text)]
            sell_vars = f"{'-' * 80} 매도변수목록 {'-' * 80}\n"
            for i, text in enumerate(sellstg_text):
                if (i + 1) % 11 == 0:
                    sell_vars = f'{sell_vars}, {text},\n'
                elif i == 0 or i % 11 == 0:
                    sell_vars = f'{sell_vars}{text}'
                else:
                    sell_vars = f'{sell_vars}, {text}'

            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '결과 그래프 생성 중 ...'))
            PlotShow('백테스트', self.is_tick, self.teleQ, df_tsg.copy(), df_bct, self.dict_cn, seed, mdd, self.startday,
                     self.endday, self.starttime, self.endtime, None, self.backname, back_text, label_text + bootstrap_text,
                     save_file_name, self.schedul, False, buy_vars=buy_vars, sell_vars=sell_vars)
        else:
            if not self.dict_set['그래프저장하지않기']:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '결과 그래프 생성 중 ...'))
                PlotShow('백테스트', self.is_tick, self.teleQ, df_tsg.copy(), df_bct, self.dict_cn, seed, mdd, self.startday,
                         self.endday, self.starttime, self.endtime, None, self.backname, back_text, label_text + bootstrap_text,
                         save_file_name, self.schedul, self.dict_set['그래프띄우지않기'])

        data = [int(self.betting), seed, tc, atc, mhct, ah, pc, mc, wr, app, tpp, mdd, tsg, tpi, cagr, self.buystg, self.sellstg]
        df = pd.DataFrame([data], columns=columns_vj, index=[save_time])
        con = sqlite3.connect(DB_BACKTEST)
        df.to_sql(self.savename, con, if_exists='append', chunksize=1000)
        df_tsg.to_sql(save_file_name, con, if_exists='append', chunksize=1000)
        con.close()
        self.wq.put((ui_num[f'{self.ui_gubun.replace("F", "")}상세기록'], df_tsg))

    def InsertBlacklist(self, df_tsg):
        name_list = df_tsg['종목명'].unique()
        dict_code = {name: code for code, name in self.dict_cn.items()}

        for name in name_list:
            if name not in dict_code:
                continue
            code = dict_code[name]
            df_tsg_code = df_tsg[df_tsg['종목명'] == name]
            trade_count = len(df_tsg_code)
            total_eyun = df_tsg_code['수익금'].sum()
            if trade_count >= 10 and total_eyun < 0:
                if self.ui_gubun == 'S':
                    if code + '\n' not in stockreadlines:
                        stockreadlines.append(code + '\n')
                        self.insertblacklist.append(code)
                elif self.ui_gubun == 'SF':
                    if code + '\n' not in futurereadlines:
                        futurereadlines.append(code + '\n')
                        self.insertblacklist.append(code)
                else:
                    if code + '\n' not in coinreadlines:
                        coinreadlines.append(code + '\n')
                        self.insertblacklist.append(code)

        if self.insertblacklist:
            if self.ui_gubun == 'S':
                with open('./utility/blacklist_stock.txt', 'w') as f:
                    f.write(''.join(stockreadlines))
            elif self.ui_gubun == 'SF':
                with open('./utility/blacklist_future.txt', 'w') as f:
                    f.write(''.join(futurereadlines))
            else:
                with open('./utility/blacklist_coin.txt', 'w') as f:
                    f.write(''.join(coinreadlines))

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} STOP'))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} COMPLETE'))
        time.sleep(1)
        sys.exit()
