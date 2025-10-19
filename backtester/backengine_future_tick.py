import math
import numpy as np
from traceback import print_exc
from backtester.backengine_kiwoom_tick import BackEngineKiwoomTick
from utility.setting import dgree
from utility.static import GetFutureLongPgSgSp, GetFutureShortPgSgSp, dt_ymdhm, dt_ymdhms
from backtester.back_static import GetBuyStgFuture, GetSellStgFuture, GetBuyCondsFuture, GetSellCondsFuture, GetTradeInfo


# noinspection PyUnusedLocal
class BackEngineFutureTick(BackEngineKiwoomTick):
    def Settings(self):
        self.avg_gubun     = 2
        self.ui_num_txt    = 'S백테스트'
        self.is_oms        = self.dict_set['백테주문관리적용']
        self.is_tick       = self.dict_set['주식타임프레임']
        self.buy_hj_limit  = self.dict_set['주식매수시장가잔량범위']
        self.sell_hj_limit = self.dict_set['주식매도시장가잔량범위']
        self.set_dict_cond = self.dict_set['주식경과틱수설정']
        self.set_weight    = self.dict_set['주식비중조절']

    def MainLoop(self):
        while True:
            data = self.beq.get()
            if '정보' in data[0]:
                if self.back_type == '최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars      = [var[1] for var in self.vars_list]
                        self.InitDivid()
                        self.InitTradeInfo()
                        self.BackTest()
                elif self.back_type == '전진분석':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars      = [var[1] for var in self.vars_list]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.InitDivid()
                        self.InitTradeInfo()
                        self.BackTest()
                elif self.back_type == 'GA최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_lists = data[1]
                        self.InitDivid()
                        self.InitTradeInfo()
                        self.BackTest()
                elif self.back_type == '조건최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        self.avgtime   = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.CheckDayAndTime()
                    elif data[0] == '조건정보':
                        self.dict_buystg  = {}
                        self.dict_sellstg = {}
                        self.dict_sconds  = {}
                        error = False
                        for i in range(20):
                            buystg = GetBuyCondsFuture(self.is_long, data[2][i], self.gubun)
                            sellstg, dict_cond = GetSellCondsFuture(self.is_long, data[3][i], self.gubun)
                            self.dict_buystg[i]  = buystg
                            self.dict_sellstg[i] = sellstg
                            self.dict_sconds[i]  = dict_cond
                            if buystg is None or sellstg is None: error = True
                        if error:
                            self.BackStop()
                        else:
                            self.InitDivid()
                            self.InitTradeInfo()
                            self.BackTest()
                elif self.back_type == '백테스트':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        self.avgtime   = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckDayAndTime()
                            self.InitDivid()
                            self.InitTradeInfo()
                            self.BackTest()
                elif self.back_type == '백파인더':
                    if data[0] == '백테정보':
                        self.avgtime   = data[1]
                        self.startday  = data[2]
                        self.endday    = data[3]
                        self.starttime = data[4]
                        self.endtime   = data[5]
                        try:
                            self.buystg = compile(data[6], '<string>', 'exec')
                        except:
                            print_exc()
                            self.BackStop()
                        else:
                            self.CheckDayAndTime()
                            self.InitDivid()
                            self.InitTradeInfo()
                            self.BackTest()
            elif data[0] == '백테유형':
                self.back_type = data[1]
            elif data[0] == '설정변경':
                self.dict_set = data[1]
            elif data[0] == '종목명':
                self.dict_info = data[1]
            elif data[0] == '데이터로딩':
                self.DataLoad(data)
            elif data[0] == '공유데이터':
                self.shared_count = data[1]
                self.shared_info  = data[2]
            elif data == '전체틱수계산':
                self.GetTickCount()
            elif data == '백테중지':
                self.BackStop(2)

    def BackTest(self):
        if self.profile:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        j = 0
        while True:
            code = self.GetArrayData()
            if code is None:
                break

            if not self.beq.empty() and self.beq.get() == '백테중지':
                self.BackStop(1)
                return

            self.code = code
            self.name = self.dict_info[code]['종목명']
            last = len(self.arry_data) - 1
            if last > 0:
                indexs = self.arry_data[:, 0].astype(np.int64)
                day_last_indexs = [i for i in range(last) if str(indexs[i])[:8] != str(indexs[i + 1])[:8]]
                day_last_indexs.append(last)

                start_idx = 0
                for end_idx in day_last_indexs:
                    for i in range(start_idx, end_idx):
                        self.index  = indexs[i]
                        self.indexn = i
                        self.tick_count += 1

                        try:
                            self.Strategy()
                        except:
                            print_exc()
                            self.BackStop(3)
                            return

                        j += 1
                        if j == 1000:
                            j = 0
                            if self.opti_turn in (1, 3): self.tq.put('탐색완료')
                            if not self.beq.empty() and self.beq.get() == '백테중지':
                                self.BackStop(1)
                                return

                    j += 1
                    if j == 1000:
                        j = 0
                        if self.opti_turn in (1, 3): self.tq.put('탐색완료')

                    self.index  = indexs[end_idx]
                    self.indexn = end_idx
                    self.tick_count += 1
                    self.LastSell()
                    self.InitTradeInfo()
                    start_idx = end_idx + 1

            self.tq.put('백테완료')

        if self.opti_turn in (1, 3): self.tq.put(('탐색완료', j))
        if self.profile: self.pr.print_stats(sort='cumulative')

    def Strategy(self):
        def now():
            return dt_ymdhms(str(self.index))

        def Parameter_Previous(aindex, pre):
            if pre < 데이터길이:
                pindex = (self.indexn - pre) if pre != -1 else self.indexb
                return self.arry_data[pindex, aindex]
            return 0

        def 현재가N(pre):
            return Parameter_Previous(1, pre)

        def 시가N(pre):
            return Parameter_Previous(2, pre)

        def 고가N(pre):
            return Parameter_Previous(3, pre)

        def 저가N(pre):
            return Parameter_Previous(4, pre)

        def 등락율N(pre):
            return Parameter_Previous(5, pre)

        def 당일거래대금N(pre):
            return Parameter_Previous(6, pre)

        def 체결강도N(pre):
            return Parameter_Previous(7, pre)

        def 초당매수수량N(pre):
            return Parameter_Previous(8, pre)

        def 초당매도수량N(pre):
            return Parameter_Previous(9, pre)

        def 초당거래대금N(pre):
            return Parameter_Previous(10, pre)

        def 고저평균대비등락율N(pre):
            return Parameter_Previous(11, pre)

        def 매도총잔량N(pre):
            return Parameter_Previous(12, pre)

        def 매수총잔량N(pre):
            return Parameter_Previous(13, pre)

        def 매도호가5N(pre):
            return Parameter_Previous(14, pre)

        def 매도호가4N(pre):
            return Parameter_Previous(15, pre)

        def 매도호가3N(pre):
            return Parameter_Previous(16, pre)

        def 매도호가2N(pre):
            return Parameter_Previous(17, pre)

        def 매도호가1N(pre):
            return Parameter_Previous(18, pre)

        def 매수호가1N(pre):
            return Parameter_Previous(19, pre)

        def 매수호가2N(pre):
            return Parameter_Previous(20, pre)

        def 매수호가3N(pre):
            return Parameter_Previous(21, pre)

        def 매수호가4N(pre):
            return Parameter_Previous(22, pre)

        def 매수호가5N(pre):
            return Parameter_Previous(23, pre)

        def 매도잔량5N(pre):
            return Parameter_Previous(24, pre)

        def 매도잔량4N(pre):
            return Parameter_Previous(25, pre)

        def 매도잔량3N(pre):
            return Parameter_Previous(26, pre)

        def 매도잔량2N(pre):
            return Parameter_Previous(27, pre)

        def 매도잔량1N(pre):
            return Parameter_Previous(28, pre)

        def 매수잔량1N(pre):
            return Parameter_Previous(29, pre)

        def 매수잔량2N(pre):
            return Parameter_Previous(30, pre)

        def 매수잔량3N(pre):
            return Parameter_Previous(31, pre)

        def 매수잔량4N(pre):
            return Parameter_Previous(32, pre)

        def 매수잔량5N(pre):
            return Parameter_Previous(33, pre)

        def 매도수5호가잔량합N(pre):
            return Parameter_Previous(34, pre)

        def 관심종목N(pre):
            return Parameter_Previous(35, pre)

        def 이동평균(tick, pre=0):
            if tick == 60:
                return Parameter_Previous(36, pre)
            elif tick == 300:
                return Parameter_Previous(37, pre)
            elif tick == 600:
                return Parameter_Previous(38, pre)
            elif tick == 1200:
                return Parameter_Previous(39, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    return round(self.arry_data[sindex:eindex, 1].mean(), 8)
                return 0

        def GetArrayIndex(aindex):
            return aindex + 12 * self.avg_list.index(self.avgtime if self.back_type in ('백테스트', '조건최적화', '백파인더') else self.vars[0])

        def Parameter_Area(aindex, vindex, tick, pre, gubun_):
            if tick in self.avg_list:
                return Parameter_Previous(GetArrayIndex(aindex), pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    if gubun_ == 'max':
                        return self.arry_data[sindex:eindex, vindex].max()
                    elif gubun_ == 'min':
                        return self.arry_data[sindex:eindex, vindex].min()
                    elif gubun_ == 'sum':
                        return self.arry_data[sindex:eindex, vindex].sum()
                    else:
                        return self.arry_data[sindex:eindex, vindex].mean()
                return 0

        def 최고현재가(tick, pre=0):
            return Parameter_Area(40, 1, tick, pre, 'max')

        def 최저현재가(tick, pre=0):
            return Parameter_Area(41, 1, tick, pre, 'min')

        def 체결강도평균(tick, pre=0):
            return round(Parameter_Area(42, 7, tick, pre, 'mean'), 3)

        def 최고체결강도(tick, pre=0):
            return Parameter_Area(43, 7, tick, pre, 'max')

        def 최저체결강도(tick, pre=0):
            return Parameter_Area(44, 7, tick, pre, 'min')

        def 최고초당매수수량(tick, pre=0):
            return Parameter_Area(45, 8, tick, pre, 'max')

        def 최고초당매도수량(tick, pre=0):
            return Parameter_Area(46, 9, tick, pre, 'max')

        def 누적초당매수수량(tick, pre=0):
            return Parameter_Area(47, 8, tick, pre, 'sum')

        def 누적초당매도수량(tick, pre=0):
            return Parameter_Area(48, 9, tick, pre, 'sum')

        def 초당거래대금평균(tick, pre=0):
            return int(Parameter_Area(49, 10, tick, pre, 'mean'))

        def Parameter_Dgree(aindex, vindex, tick, pre, cf):
            if tick in self.avg_list:
                return Parameter_Previous(GetArrayIndex(aindex), pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn - pre - tick + 1) if pre != -1  else self.indexb - tick + 1
                    eindex = (self.indexn - pre) if pre != -1  else self.indexb
                    dmp_gap = self.arry_data[eindex, vindex] - self.arry_data[sindex, vindex]
                    return round(math.atan2(dmp_gap * cf, tick) / (2 * math.pi) * 360, 2)
                return 0

        def 등락율각도(tick, pre=0):
            return Parameter_Dgree(50, 5, tick, pre, dgree['future']['tick'][0])

        def 당일거래대금각도(tick, pre=0):
            return Parameter_Dgree(51, 6, tick, pre, dgree['future']['tick'][1])

        def 경과틱수(조건명):
            if 종목코드 in self.dict_cond_indexn and \
                    조건명 in self.dict_cond_indexn[종목코드] and self.dict_cond_indexn[종목코드][조건명] != 0:
                return self.indexn - self.dict_cond_indexn[종목코드][조건명]
            return 0

        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금, 고저평균대비등락율, 매도총잔량, \
            매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, 매도수5호가잔량합, \
            관심종목 = self.arry_data[self.indexn, 1:36]
        종목코드, 데이터길이, 시분초, 호가단위 = self.code, self.tick_count, int(str(self.index)[8:]), 매도호가2 - 매도호가1
        self.bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        self.shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn:
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                exec(v)

        if self.opti_turn == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    break

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if self.tick_count < self.vars[0]:
                        continue

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount2(vturn, vkey, 고가, 저가, 등락율각도(30), 당일거래대금각도(30))
                        exec(self.buystg)
                    else:
                        수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                        포지션 = 'LONG' if self.trade_info[vturn][vkey]['보유중'] == 1 else 'SHORT'
                        exec(self.sellstg)

        elif self.opti_turn == 3:
            for vturn in self.trade_info:
                for vkey in self.trade_info[vturn]:
                    index_ = vturn * 20 + vkey
                    if self.back_type != '조건최적화':
                        self.vars = self.vars_lists[index_]
                        if self.tick_count < self.vars[0]:
                            break
                    elif self.tick_count < self.avgtime:
                        break

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount2(vturn, vkey, 고가, 저가, 등락율각도(30), 당일거래대금각도(30))
                        if self.back_type != '조건최적화':
                            exec(self.buystg)
                        else:
                            exec(self.dict_buystg[index_])
                    else:
                        수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                        포지션 = 'LONG' if self.trade_info[vturn][vkey]['보유중'] == 1 else 'SHORT'
                        if self.back_type != '조건최적화':
                            exec(self.sellstg)
                        else:
                            exec(self.dict_sellstg[index_])
        else:
            vturn, vkey = 0, 0
            if self.back_type in ('최적화', '전진분석'):
                if self.tick_count < self.vars[0]:
                    return
            else:
                if self.tick_count < self.avgtime:
                    return

            BUY_LONG, SELL_SHORT = True, True
            SELL_LONG, BUY_SHORT = False, False
            if not self.trade_info[vturn][vkey]['보유중']:
                if not 관심종목: return
                self.SetBuyCount2(vturn, vkey, 고가, 저가, 등락율각도(30), 당일거래대금각도(30))
                exec(self.buystg)
            else:
                수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                포지션 = 'LONG' if self.trade_info[vturn][vkey]['보유중'] == 1 else 'SHORT'
                exec(self.sellstg)

    def SetBuyCount2(self, vturn, vkey, 고가, 저가, 등락율각도, 당일거래대금각도):
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = round((고가 / 저가 - 1) * 100, 2)
            elif self.set_weight[0] == 2:
                비중조절기준 = 등락율각도
            else:
                비중조절기준 = 당일거래대금각도

            if 비중조절기준 < self.set_weight[1]:
                betting = self.betting * self.set_weight[5]
            elif 비중조절기준 < self.set_weight[2]:
                betting = self.betting * self.set_weight[6]
            elif 비중조절기준 < self.set_weight[3]:
                betting = self.betting * self.set_weight[7]
            elif 비중조절기준 < self.set_weight[4]:
                betting = self.betting * self.set_weight[8]
            else:
                betting = self.betting * self.set_weight[9]

        self.trade_info[vturn][vkey]['주문수량'] = int(betting)

    def Buy(self, vturn, vkey, gubun=None):
        매수금액 = 0
        주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
        if 주문수량 > 0:
            호가정보 = self.bhogainfo if gubun == 'LONG' else self.shogainfo
            호가정보 = 호가정보[:self.buy_hj_limit]
            for 호가, 잔량 in 호가정보:
                if 미체결수량 - 잔량 <= 0:
                    매수금액 += 호가 * 미체결수량
                    미체결수량 -= 잔량
                    break
                else:
                    매수금액 += 호가 * 잔량
                    미체결수량 -= 잔량
            if 미체결수량 <= 0:
                self.trade_info[vturn][vkey] = {
                    '보유중': 1 if gubun == 'LONG' else 2,
                    '매수가': round(매수금액 / 주문수량, self.dict_info[self.code]['소숫점자리수']),
                    '매도가': 0,
                    '주문수량': 0,
                    '보유수량': 주문수량,
                    '최고수익률': 0.,
                    '최저수익률': 0.,
                    '매수틱번호': self.indexn,
                    '매수시간': dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
                }

    def SetSellCount(self, vturn, vkey, 현재가, now_time):
        _, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        매입금액 = self.dict_info[self.code]['위탁증거금'] * 보유수량
        평가금액 = 매입금액 + (현재가 - 매수가) * self.dict_info[self.code]['틱가치'] * 보유수량
        if self.trade_info[vturn][vkey]['보유중'] == 1:
            _, _, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, self.code)
        else:
            _, _, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, self.code)
        if 수익률 > 최고수익률:   self.trade_info[vturn][vkey]['최고수익률'] = 최고수익률 = 수익률
        elif 수익률 < 최저수익률: self.trade_info[vturn][vkey]['최저수익률'] = 최저수익률 = 수익률
        보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
        self.indexb = 매수틱번호
        self.trade_info[vturn][vkey]['주문수량'] = 보유수량
        return 수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호

    def Sell(self, vturn, vkey, sell_cond, gubun=None):
        매도금액 = 0
        주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
        호가정보 = self.shogainfo if gubun == 'LONG' else self.bhogainfo
        호가정보 = 호가정보[:self.sell_hj_limit]
        for 호가, 잔량 in 호가정보:
            if 미체결수량 - 잔량 <= 0:
                매도금액 += 호가 * 미체결수량
                미체결수량 -= 잔량
                break
            else:
                매도금액 += 호가 * 잔량
                미체결수량 -= 잔량
        if 미체결수량 <= 0:
            self.trade_info[vturn][vkey]['매도가'] = round(매도금액 / 주문수량, self.dict_info[self.code]['소숫점자리수'] + 1)
            self.sell_cond = sell_cond
            self.CalculationEyun(vturn, vkey)

    def LastSell(self):
        if self.ui_num_txt:
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
                self.arry_data[self.indexn, 14:34]
        else:
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
                self.arry_data[self.indexn, 17:37]
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        shogainfo = shogainfo[:self.sell_hj_limit]
        bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        bhogainfo = bhogainfo[:self.sell_hj_limit]

        for vturn in self.trade_info:
            for vkey in self.trade_info[vturn]:
                if self.trade_info[vturn][vkey]['보유중'] > 0:
                    매도금액 = 0
                    보유수량 = 미체결수량 = self.trade_info[vturn][vkey]['보유수량']
                    호가정보 = shogainfo if self.trade_info[vturn][vkey]['보유중'] == 1 else bhogainfo
                    for 매수호가, 매수잔량 in 호가정보:
                        if 미체결수량 - 매수잔량 <= 0:
                            매도금액 += 매수호가 * 미체결수량
                            미체결수량 -= 매수잔량
                            break
                        else:
                            매도금액 += 매수호가 * 매수잔량
                            미체결수량 -= 매수잔량

                    if 미체결수량 <= 0:
                        self.trade_info[vturn][vkey]['매도가'] = round(매도금액 / 보유수량, self.dict_info[self.code]['소숫점자리수'])
                    elif 매도금액 == 0:
                        self.trade_info[vturn][vkey]['매도가'] = self.arry_data[self.indexn, 1]
                    else:
                        self.trade_info[vturn][vkey]['매도가'] = round(매도금액 / (보유수량 - 미체결수량), self.dict_info[self.code]['소숫점자리수'])

                    self.trade_info[vturn][vkey]['주문수량'] = 보유수량
                    self.sell_cond = 0
                    self.CalculationEyun(vturn, vkey)

    def CalculationEyun(self, vturn, vkey):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        """
        _, 매수가, 매도가, 주문수량, _, _, _, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        매수시간, 매도시간 = int(self.arry_data[매수틱번호, 0]), self.index
        매입금액 = self.dict_info[self.code]['위탁증거금'] * 주문수량
        평가금액 = 매입금액 + (매도가 - 매수가) * self.dict_info[self.code]['틱가치'] * 주문수량
        if self.trade_info[vturn][vkey]['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, self.code)
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, self.code)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '', True
        data = ('백테결과', self.name, 포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금, 매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        self.trade_info[vturn][vkey] = GetTradeInfo(1)
