
from backtest.back_static import get_trade_info
from utility.setting_base import dict_order_ratio
from backtest.backengine_base import BackEngineBase
from utility.static import timedelta_sec, roundfigure_upper, roundfigure_lower, dt_ymdhms, dt_ymdhm


class BackEngineBaseOms(BackEngineBase):
    def GetHoldInfo(self, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간):
        포지션, 수익금, 수익률, 보유시간 = None, 0, 0, 0
        if self.curr_trade_info['보유중']:
            포지션, _, 수익금, 수익률 = self.GetProfitInfo(현재가, 매수가, 보유수량)
            if 수익률 > 최고수익률:   self.curr_trade_info['최고수익률'] = 최고수익률 = 수익률
            elif 수익률 < 최저수익률: self.curr_trade_info['최저수익률'] = 최저수익률 = 수익률
            now_time = self._now()
            보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
            self.indexb = 매수틱번호
        return 포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간

    def CheckBuyOrSell(self, 보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량, 매수호가단위,
                       매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션, 분봉고가=None, 분봉저가=None):
        gubun = None
        if self.dict_set[f'{self.market_text}매수주문구분'] == '시장가':
            if not 보유중:
                gubun = '매수'
            elif 매수분할횟수 < self.dict_set[f'{self.market_text}매수분할횟수']:
                gubun = '매수매도'
            else:
                gubun = '매도'
        elif self.dict_set[f'{self.market_text}매수주문구분'] == '지정가':
            관심종목1 = self._관심종목N(1)
            if not 보유중:
                if 매수호가 == 0:
                    gubun = '매수'
                else:
                    관심이탈 = not 관심종목 and 관심종목1
                    self.CheckBuy(주문포지션, 현재가, 관심이탈, 분봉고가, 분봉저가, 매수가, 주문수량, 보유수량, 매수호가, 매수호가단위, 매수주문취소시간)
                    return gubun
            elif 매수분할횟수 < self.dict_set[f'{self.market_text}매수분할횟수']:
                if 매수호가 == 0 and 매도호가 == 0:
                    if self.dict_set[f'{self.market_text}매도금지매수횟수'] and 매수분할횟수 < self.dict_set[f'{self.market_text}매도금지매수횟수값']:
                        gubun = '매수'
                    else:
                        gubun = '매수매도'
                elif 매수호가 != 0:
                    관심이탈 = not 관심종목 and 관심종목1
                    self.CheckBuy(주문포지션, 현재가, 관심이탈, 분봉고가, 분봉저가, 매수가, 주문수량, 보유수량, 매수호가, 매수호가단위, 매수주문취소시간)
                    return gubun
                else:
                    관심진입 = 관심종목 and not 관심종목1
                    self.CheckSell(보유중, 현재가, 관심진입, 분봉고가, 분봉저가, 매도호가, 매도호가단위, 매도정정횟수, 매도주문취소시간)
                    return gubun
            else:
                if 매도호가 == 0:
                    gubun = '매도'
                else:
                    관심진입 = 관심종목 and not 관심종목1
                    self.CheckSell(보유중, 현재가, 관심진입, 분봉고가, 분봉저가, 매도호가, 매도호가단위, 매도정정횟수, 매도주문취소시간)
                    return gubun
        return gubun

    def CancelBuyOrder(self, 현재가):
        cancel = False
        now_time = self._now()
        거래횟수, 손절횟수, 직전거래시간, 손절매도시간 = self.curr_day_info.values()
        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set[f'{self.market_text}매수금지거래횟수'] and \
                self.dict_set[f'{self.market_text}매수금지거래횟수값'] <= 거래횟수:
            cancel = True
        elif self.dict_set[f'{self.market_text}매수금지손절횟수'] and \
                self.dict_set[f'{self.market_text}매수금지손절횟수값'] <= 손절횟수:
            cancel = True
        elif self.dict_set[f'{self.market_text}매수금지시간'] and \
                self.dict_set[f'{self.market_text}매수금지시작시간'] < hms < self.dict_set[f'{self.market_text}매수금지종료시간']:
            cancel = True
        elif self.dict_set[f'{self.market_text}매수금지간격'] and now_time <= 직전거래시간:
            cancel = True
        elif self.dict_set[f'{self.market_text}매수금지손절간격'] and now_time <= 손절매도시간:
            cancel = True
        elif self.market_gubun == 1 and self.dict_set[f'{self.market_text}매수금지라운드피겨'] and \
                roundfigure_upper(현재가, self.dict_set[f'{self.market_text}매수금지라운드호가'], self.index):
            cancel = True
        elif self.market_gubun in (3, 4) and self.dict_set[f'{self.market_text}매수금지200원이하'] and 현재가 <= 200:
            cancel = True
        return cancel

    def Buy(self, buy_long=False):
        self.SetBuyCount()
        주문수량 = self.curr_trade_info['주문수량']
        if 주문수량 > 0:
            if self.dict_set[f'{self.market_text}매수주문구분'] == '시장가':
                if self.market_gubun in (1, 3) or buy_long:
                    호가배열 = self.shogainfo[:self.buy_hj_limit]
                    잔량배열 = self.shreminfo[:self.buy_hj_limit]
                else:
                    호가배열 = self.bhogainfo[:self.buy_hj_limit]
                    잔량배열 = self.bhreminfo[:self.buy_hj_limit]

                거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
                if 체결완료:
                    매수가 = self.curr_trade_info['매수가']
                    보유수량 = self.curr_trade_info['보유수량']
                    총수량 = 보유수량 + 주문수량
                    추가매수가 = self.GetBuyPrice(거래금액, 주문수량)
                    평단가 = self.GetBuyPrice(매수가 * 보유수량 + 거래금액, 총수량)
                    주문포지션 = None if self.market_gubun in (1, 3) else 'LONG' if buy_long else 'SHORT'
                    self.curr_trade_info.update({
                        '매수가': 평단가,
                        '보유수량': 총수량,
                        '추가매수가': 추가매수가
                    })
                    self.UpdateBuyInfo(주문포지션, True if 매수가 == 0 else False)

            elif self.dict_set[f'{self.market_text}매수주문구분'] == '지정가':
                매수주문취소시간 = timedelta_sec(
                    self.dict_set[f'{self.market_text}매수취소시간초'],
                    dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
                )
                self.curr_trade_info.update({
                    '매수호가': self.curr_trade_info['매수호가_'],
                    '매수호가단위': self.hoga_unit,
                    '매수주문취소시간': 매수주문취소시간
                })

    def SetBuyCount(self):
        보유중, 매수가, 현재가, 저가대비고가등락율, 매수분할횟수, 매도호가1, 매수호가1 = self.info_for_order[:-4]
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.set_weight[0] == 2:
                비중조절기준 = self._거래대금평균대비비율(30)
            elif self.set_weight[0] == 3:
                비중조절기준 = self._등락율각도(30)
            elif self.set_weight[0] == 4:
                비중조절기준 = self._당일거래대금각도(30)
            else:
                비중조절기준 = self.비중조절기준

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

        order_ratio = dict_order_ratio[self.dict_set[f'{self.market_text}매수분할방법']][self.dict_set[f'{self.market_text}매수분할횟수']]
        oc_ratio = order_ratio[매수분할횟수]
        self.curr_trade_info['주문수량'] = self.GetOrderCount(betting, 현재가, 보유중, 매수가, oc_ratio)

        if self.dict_set[f'{self.market_text}매수주문구분'] == '지정가':
            기준가격 = 현재가
            if self.dict_set[f'{self.market_text}매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set[f'{self.market_text}매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.curr_trade_info['매수호가_'] = 기준가격 + self.hoga_unit * self.dict_set[f'{self.market_text}매수지정가호가번호']

    def CheckDividBuy(self, 포지션, 현재가, 추가매수가, 수익률):
        분할매수기준수익률 = round((현재가 / 추가매수가 - 1) * 100, 2) if self.dict_set[f'{self.market_text}매수분할고정수익률'] else 수익률
        if 포지션.__class__ == int:
            if self.dict_set[f'{self.market_text}매수분할하방'] and \
                    분할매수기준수익률 < -self.dict_set[f'{self.market_text}매수분할하방수익률']:
                self.Buy()
                return True
            elif self.dict_set[f'{self.market_text}매수분할상방'] and \
                    분할매수기준수익률 > self.dict_set[f'{self.market_text}매수분할상방수익률']:
                self.Buy()
                return True
        else:
            if 포지션 == 'LONG' and \
                    self.dict_set[f'{self.market_text}매수분할하방'] and \
                    분할매수기준수익률 < -self.dict_set[f'{self.market_text}매수분할하방수익률']:
                self.Buy(True)
                return True
            elif 포지션 == 'LONG' and \
                    self.dict_set[f'{self.market_text}매수분할상방'] and \
                    분할매수기준수익률 > self.dict_set[f'{self.market_text}매수분할상방수익률']:
                self.Buy(True)
                return True
            elif 포지션 == 'SHORT' and \
                    self.dict_set[f'{self.market_text}매수분할하방'] and \
                    분할매수기준수익률 < -self.dict_set[f'{self.market_text}매수분할하방수익률']:
                self.Buy(False)
                return True
            elif 포지션 == 'SHORT' and \
                    self.dict_set[f'{self.market_text}매수분할상방'] and \
                    분할매수기준수익률 > self.dict_set[f'{self.market_text}매수분할상방수익률']:
                self.Buy(False)
                return True
        return False

    # noinspection PyUnusedLocal
    def CheckBuy(self, 주문포지션, 현재가, 관심이탈, 분봉고가, 분봉저가, 매수가, 주문수량, 보유수량, 매수호가, 매수호가단위, 매수주문취소시간):
        if self.dict_set[f'{self.market_text}매수취소관심이탈'] and 관심이탈:
            self.curr_trade_info['매수호가'] = 0

        elif self.dict_set[f'{self.market_text}매수취소시간'] and \
                (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매수주문취소시간:
            self.curr_trade_info['매수호가'] = 0

        elif (주문포지션 is None or 주문포지션 == 'LONG') and \
                self.curr_trade_info['매수정정횟수'] < self.dict_set[f'{self.market_text}매수정정횟수'] and \
                현재가 >= 매수호가 + 매수호가단위 * self.dict_set[f'{self.market_text}매수정정호가차이']:
            매수호가 = 현재가 - 매수호가단위 * self.dict_set[f'{self.market_text}매수정정호가']
            매수정정횟수 = self.curr_trade_info['매수정정횟수'] + 1
            self.curr_trade_info.update({
                '매수호가': 매수호가,
                '매수정정횟수': 매수정정횟수,
                '매수호가단위': self.hoga_unit
            })

        elif 주문포지션 == 'SHORT' and \
                self.curr_trade_info['매수정정횟수'] < self.dict_set[f'{self.market_text}매수정정횟수'] and \
                현재가 <= 매수호가 - 매수호가단위 * self.dict_set[f'{self.market_text}매수정정호가차이']:
            매수호가 = 현재가 + 매수호가단위 * self.dict_set[f'{self.market_text}매수정정호가']
            매수정정횟수 = self.curr_trade_info['매수정정횟수'] + 1
            self.curr_trade_info.update({
                '매수호가': 매수호가,
                '매수정정횟수': 매수정정횟수,
                '매수호가단위': self.hoga_unit
            })

        else:
            A = 주문포지션 is None and ((분봉저가 is None and 현재가 < 매수호가) or (분봉저가 is not None and 분봉저가 < 매수호가))
            B = 주문포지션 == 'LONG' and ((분봉저가 is None and 현재가 < 매수호가) or (분봉저가 is not None and 분봉저가 < 매수호가))
            C = 주문포지션 == 'SHORT' and ((분봉고가 is None and 현재가 > 매수호가) or (분봉고가 is not None and 분봉고가 > 매수호가))
            if A or B or C:
                총수량 = 보유수량 + 주문수량
                평단가 = self.GetBuyPrice(매수가 * 보유수량 + 매수호가 * 주문수량, 총수량)
                self.curr_trade_info.update({
                    '매수가': 평단가,
                    '보유수량': 총수량,
                    '추가매수가': 매수호가
                })
                self.UpdateBuyInfo(주문포지션, True if 매수가 == 0 else False)

    def UpdateBuyInfo(self, 주문포지션, firstbuy):
        datetimefromindex = dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
        self.curr_trade_info.update({
            '보유중': 1 if 주문포지션 is None or 주문포지션 == 'LONG' else 2,
            '매수호가': 0,
            '매수정정횟수': 0
        })
        self.curr_day_info['직전거래시간'] = timedelta_sec(self.dict_set[f'{self.market_text}매수금지간격초'], datetimefromindex)
        if firstbuy:
            self.curr_trade_info.update({
                '매수틱번호': self.indexn,
                '매수시간': datetimefromindex,
                '추가매수시간': [],
                '매수분할횟수': 0
            })
        text = f"{self.index};{self.curr_trade_info['추가매수가']}"
        self.curr_trade_info['추가매수시간'].append(text)
        self.curr_trade_info['매수분할횟수'] += 1

    def CheckSonjeol(self, 수익률, 수익금):
        A = self.dict_set[f'{self.market_text}매도익절수익률청산'] and 수익률 > self.dict_set[f'{self.market_text}매도익절수익률']
        B = self.dict_set[f'{self.market_text}매도익절수익금청산'] and 수익금 > self.dict_set[f'{self.market_text}매도익절수익금']
        C = self.dict_set[f'{self.market_text}매도손절수익률청산'] and 수익률 < -self.dict_set[f'{self.market_text}매도손절수익률']
        D = self.dict_set[f'{self.market_text}매도손절수익금청산'] and 수익금 < -self.dict_set[f'{self.market_text}매도손절수익금']
        if A or B or C or D:
            origin_sell_gubun = self.dict_set[f'{self.market_text}매도주문구분']
            self.dict_set[f'{self.market_text}매도주문구분'] = '시장가'
            self.curr_trade_info['주문수량'] = self.curr_trade_info['보유수량']
            self.Sell()
            self.sell_cond = 1001 if A or B else 1002
            self.dict_set[f'{self.market_text}매도주문구분'] = origin_sell_gubun
            return True
        return False

    def CancelSellOrder(self, 현재가, 매수분할횟수):
        cancel = False
        if self.dict_set[f'{self.market_text}매도주문구분'] == '시장가':
            if 매수분할횟수 != self.curr_trade_info['매수분할횟수']:
                cancel = True
                return cancel
        elif self.curr_trade_info['매수호가'] != 0:
            cancel = True
            return cancel

        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set[f'{self.market_text}매도금지시간'] and \
                self.dict_set[f'{self.market_text}매도금지시작시간'] < hms < self.dict_set[f'{self.market_text}매도금지종료시간']:
            cancel = True
        elif self.dict_set[f'{self.market_text}매도금지간격'] and self._now() <= self.curr_day_info['직전거래시간']:
            cancel = True
        elif self.dict_set[f'{self.market_text}매수분할횟수'] > 1 and \
                self.dict_set[f'{self.market_text}매도금지매수횟수'] and \
                매수분할횟수 <= self.dict_set[f'{self.market_text}매도금지매수횟수값']:
            cancel = True
        elif self.market_gubun == 1 and self.dict_set[f'{self.market_text}매도금지라운드피겨'] and \
                roundfigure_lower(현재가, self.dict_set[f'{self.market_text}매도금지라운드호가'], self.index):
            cancel = True
        return cancel

    def Sell(self, sell_long=False):
        self.SetSellCount()
        if self.dict_set[f'{self.market_text}매도주문구분'] == '시장가':
            주문수량 = self.curr_trade_info['주문수량']
            if 주문수량 > 0:
                if self.market_gubun in (1, 3) or sell_long:
                    호가배열 = self.bhogainfo[:self.sell_hj_limit]
                    잔량배열 = self.bhreminfo[:self.sell_hj_limit]
                else:
                    호가배열 = self.shogainfo[:self.sell_hj_limit]
                    잔량배열 = self.shreminfo[:self.sell_hj_limit]

                거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
                if 체결완료:
                    self.curr_trade_info['매도가'] = self.GetSellPrice(거래금액, 주문수량)
                    self.CalculationEyun()

        elif self.dict_set[f'{self.market_text}매도주문구분'] == '지정가':
            매도주문취소시간 = timedelta_sec(
                self.dict_set[f'{self.market_text}매도취소시간초'],
                dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
            )
            self.curr_trade_info.update({
                '매도호가': self.curr_trade_info['매도호가_'],
                '매도호가단위': self.hoga_unit,
                '매도주문취소시간': 매도주문취소시간
            })

    def SetSellCount(self):
        _, _, 현재가, _, _, 매도호가1, 매수호가1, 보유수량, 매도분할횟수 = self.info_for_order[:-2]
        if self.dict_set[f'{self.market_text}매도분할횟수'] == 1:
            self.curr_trade_info['주문수량'] = 보유수량
        else:
            dict_ratio = dict_order_ratio[self.dict_set[f'{self.market_text}매도분할방법']][self.dict_set[f'{self.market_text}매도분할횟수']]
            oc_ratio = dict_ratio[매도분할횟수]
            if 매도분할횟수 == 0:
                매도수량 = int(보유수량 * oc_ratio / 100) if self.market_gubun < 3 else round(보유수량 * oc_ratio / 100, 8)
            else:
                보유비율 = sum(비율 for 횟수, 비율 in dict_ratio.items() if 횟수 >= 매도분할횟수)
                매도수량 = int(보유수량 / 보유비율 * oc_ratio) if self.market_gubun < 3 else round(보유수량 / 보유비율 * oc_ratio, 8)

            self.curr_trade_info['주문수량'] = 매도수량
            if self.curr_trade_info['주문수량'] > 보유수량 or 매도분할횟수 + 1 == self.dict_set[f'{self.market_text}매도분할횟수']:
                self.curr_trade_info['주문수량'] = 보유수량

        if self.dict_set[f'{self.market_text}매도주문구분'] == '지정가':
            기준가격 = 현재가
            if self.dict_set[f'{self.market_text}매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set[f'{self.market_text}매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.curr_trade_info['매도호가_'] = 기준가격 + self.hoga_unit * self.dict_set[f'{self.market_text}매도지정가호가번호']

    def CheckDividSell(self, 포지션, 수익률, 매도분할횟수):
        if 포지션.__class__ == int:
            if self.dict_set[f'{self.market_text}매도분할하방'] and \
                    수익률 < -self.dict_set[f'{self.market_text}매도분할하방수익률'] * (매도분할횟수 + 1):
                self.Sell()
                self.sell_cond = 1000
                return True
            elif self.dict_set[f'{self.market_text}매도분할상방'] and \
                    수익률 > self.dict_set[f'{self.market_text}매도분할상방수익률'] * (매도분할횟수 + 1):
                self.Sell()
                self.sell_cond = 1000
                return True
        else:
            if 포지션 == 'LONG' and self.dict_set[f'{self.market_text}매도분할하방'] and \
                    수익률 < -self.dict_set[f'{self.market_text}매도분할하방수익률'] * (매도분할횟수 + 1):
                self.Sell(True)
                self.sell_cond = 1000
                return True
            elif 포지션 == 'LONG' and self.dict_set[f'{self.market_text}매도분할상방'] and \
                    수익률 > self.dict_set[f'{self.market_text}매도분할상방수익률'] * (매도분할횟수 + 1):
                self.Sell(True)
                self.sell_cond = 1000
                return True
            elif 포지션 == 'SHORT' and self.dict_set[f'{self.market_text}매도분할하방'] and \
                    수익률 < -self.dict_set[f'{self.market_text}매도분할하방수익률'] * (매도분할횟수 + 1):
                self.Sell(False)
                self.sell_cond = 1000
                return True
            elif 포지션 == 'SHORT' and self.dict_set[f'{self.market_text}매도분할상방'] and \
                    수익률 > self.dict_set[f'{self.market_text}매도분할상방수익률'] * (매도분할횟수 + 1):
                self.Sell(False)
                self.sell_cond = 1000
                return True
        return False

    # noinspection PyUnusedLocal
    def CheckSell(self, 보유중, 현재가, 관심진입, 분봉고가, 분봉저가, 매도호가, 매도호가단위, 매도정정횟수, 매도주문취소시간):
        if self.dict_set[f'{self.market_text}매도취소관심진입'] and 관심진입:
            self.curr_trade_info['매도호가'] = 0

        elif self.dict_set[f'{self.market_text}매도취소시간'] and \
                (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매도주문취소시간:
            self.curr_trade_info['매도호가'] = 0

        elif self.market_gubun in (1, 3):
            if 매도정정횟수 < self.dict_set[f'{self.market_text}매도정정횟수'] and \
                    현재가 <= 매도호가 - 매도호가단위 * self.dict_set[f'{self.market_text}매도정정호가차이']:
                self.curr_trade_info['매도호가'] = 현재가 + 매도호가단위 * self.dict_set[f'{self.market_text}매도정정호가']
                self.curr_trade_info['매도정정횟수'] += 1
                self.curr_trade_info['매도호가단위'] = self.hoga_unit
            elif (분봉고가 is None and 현재가 > 매도호가) or (분봉고가 is not None and 분봉고가 > 매도호가):
                self.curr_trade_info['매도가'] = 매도호가
                self.CalculationEyun()

        else:
            gubun = 'LONG' if 보유중 == 1 else 'SHORT'
            if gubun == 'LONG' and 매도정정횟수 < self.dict_set[f'{self.market_text}매도정정횟수'] and \
                    현재가 <= 매도호가 - 매도호가단위 * self.dict_set[f'{self.market_text}매도정정호가차이']:
                self.curr_trade_info['매도호가'] = 현재가 + 매도호가단위 * self.dict_set[f'{self.market_text}매도정정호가']
                self.curr_trade_info['매도정정횟수'] += 1
            elif gubun == 'SHORT' and 매도정정횟수 < self.dict_set[f'{self.market_text}매도정정횟수'] and \
                    현재가 >= 매도호가 + 매도호가단위 * self.dict_set[f'{self.market_text}매도정정호가차이']:
                self.curr_trade_info['매도호가'] = 현재가 - 매도호가단위 * self.dict_set[f'{self.market_text}매도정정호가']
                self.curr_trade_info['매도정정횟수'] += 1
            else:
                A = gubun == 'LONG' and ((분봉고가 is None and 현재가 > 매도호가) or (분봉고가 is not None and 분봉고가 > 매도호가))
                B = gubun == 'SHORT' and ((분봉저가 is None and 현재가 < 매도호가) or (분봉저가 is not None and 분봉저가 < 매도호가))
                if A or B:
                    self.curr_trade_info['매도가'] = 매도호가
                    self.CalculationEyun()

    def CalculationEyun(self):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()
        """
        vturn, vkey = self.info_for_order[-2:]
        _, 매수가, 매도가, 주문수량, 보유수량, _, _, 매수틱번호, 매수시간, 추가매수시간 = list(self.curr_trade_info.values())[:10]
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        매수시간, 매도시간, 매입금액 = int(self.arry_code[매수틱번호, 0]), self.index, 주문수량 * 매수가
        시가총액또는포지션, 평가금액, 수익금, 수익률 = self.GetProfitInfo(매도가, 매수가, 주문수량)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '^'.join(추가매수시간), 보유수량 - 주문수량 == 0
        data = ('백테결과', self.name, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금,
                매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_kind in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1

        self.curr_day_info['거래횟수'] += 1
        if 수익률 < 0:
            손절매도시간 = timedelta_sec(
                self.dict_set[f'{self.market_text}매수금지손절간격초'],
                dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
            )
            self.curr_day_info['손절횟수'] += 1
            self.curr_day_info['손절매도시간'] = 손절매도시간

        if 보유수량 - 주문수량 > 0:
            self.curr_trade_info['매도호가'] = 0
            self.curr_trade_info['보유수량'] -= 주문수량
            self.curr_trade_info['매도정정횟수'] = 0
            self.curr_trade_info['매도분할횟수'] += 1
        else:
            self.trade_info[vturn][vkey] = get_trade_info(2)
