
from backtest.back_static import get_trade_info
from backtest.backengine_base import BackEngineBase
from utility.settings.setting_base import dict_order_ratio
from utility.static_method.static import timedelta_sec, dt_ymdhms, dt_ymdhm


class BackEngineBaseOms(BackEngineBase):
    """주문 관리 시스템(OMS)이 적용된 백테스트 엔진 기본 클래스입니다.
    BackEngineBase를 상속받아 주문 분할, 취소, 정정 등
    실제 거래와 같은 주문 관리 기능을 제공합니다.
    """
    def _update_globals_func(self, dict_add_func):
        """전역 함수를 업데이트합니다.
        Args:
            dict_add_func: 추가할 전역 함수 딕셔너리
        """
        globals().update(dict_add_func)

    # noinspection PyUnusedLocal
    def _strategy(self):
        """전략을 실행합니다 (OMS 버전).
        현재 데이터를 기반으로 전략 연산을 수행하고 매수/매도 시그널을 처리합니다."""

        초당매수금액, 초당매도금액, 분당매수금액, 분당매도금액 = 0, 0, 0, 0
        if self.market_gubun < 4:
            if self.is_tick:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                    VI해제시간, VI가격, VI호가단위, \
                    초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            else:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                    VI해제시간, VI가격, VI호가단위, \
                    분봉시가, 분봉고가, 분봉저가, \
                    분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            VI해제시간 = dt_ymdhms(str(int(VI해제시간)))
        elif self.market_gubun == 4:
            if self.is_tick:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                    초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            else:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                    분봉시가, 분봉고가, 분봉저가, \
                    분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
        else:
            if self.is_tick:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
                    초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            else:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
                    분봉시가, 분봉고가, 분봉저가, \
                    분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

        시분초 = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        순매수금액 = 초당매수금액 - 초당매도금액 if self.is_tick else 분당매수금액 - 분당매도금액
        종목명, 종목코드, 데이터길이, 체결시간 = self.name, self.code, self.tick_count, self.index
        self.hoga_unit = 호가단위 = self._get_hogaunit(현재가 if self.market_gubun < 6 else self.code)

        리스크점수 = 0
        if self.is_tick and self.tick_count >= 30:
            if self.dict_set['시장미시구조분석']:
                self.ms_analyzer.update_data(self.code, self.arry_code[self.indexn + 1 - self.tick_count:self.indexn + 1, :])
            if self.dict_set['시장리스크분석']:
                리스크점수 = self.rk_analyzer.get_risk_score(self.arry_code[self.indexn + 1 - self.tick_count:self.indexn + 1, :])

        패턴점수, 패턴신뢰도 = 0, 0
        if not self.is_tick and self.dict_set['패턴인식분석'] and 데이터길이 >= 5:
            패턴점수, 패턴신뢰도 = self.pt_analyzer.analyze_patterns(self.code, self.arry_code)

        self.shogainfo[:] = [매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5]
        self.shreminfo[:] = [매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5]
        self.bhogainfo[:] = [매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5]
        self.bhreminfo[:] = [매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5]

        self._update_highlow(현재가)

        if self.fm_list:
            for name, _, _, fname, data_type, _, _, style, stg, col_idx in self.fm_list:
                self.check, self.line, self.up, self.down = None, None, None, None

                exec(stg)

                if data_type == '선:일반':
                    if self.line is not None:
                        self.arry_code[self.indexn, col_idx] = self.line

                elif data_type == '선:조건':
                    if self.check is not None and self.line is not None:
                        if self.check:
                            self.arry_code[self.indexn, col_idx] = self.line
                        else:
                            pre_line = self.arry_code[self.indexn - 1, col_idx]
                            if pre_line > 0:
                                self.arry_code[self.indexn, col_idx] = pre_line

                elif data_type == '범위':
                    if self.check is not None and self.up is not None and self.down is not None:
                        self.arry_code[self.indexn, col_idx] = 1.0 if self.check else 0.0
                        self.arry_code[self.indexn, col_idx + 1] = self.up
                        self.arry_code[self.indexn, col_idx + 2] = self.down

                elif data_type == '화살표:일반':
                    if self.check is not None and self.check:
                        price = self.arry_code[self.indexn, self.dict_findex[fname]]
                        self.arry_code[self.indexn, col_idx] = price

        if self.opti_kind == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    return

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if vturn == 0 and self.tick_count < self.vars[0]:
                        continue

                    if self.dict_condition:
                        self.turn_key = f'{vturn}{vturn}'
                        if 종목코드 not in self.dict_cond_indexn:
                            self.dict_cond_indexn[종목코드] = {}
                        for k, v in self.dict_condition.items():
                            exec(v)

                    self.curr_day_info = self.day_info[vturn][vkey]
                    self.curr_trade_info = self.trade_info[vturn][vkey]

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()

                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                        self._get_hold_info(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)

                    self.info_for_order = \
                        보유중, 매수가, 현재가, 저가대비고가등락율, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수, vturn, vkey

                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self._check_buy_or_sell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량,
                                                    보유수량, 매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수,
                                                    매도주문취소시간, 주문포지션)
                    if gubun is None: continue

                    매수, 매도 = True, False
                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False

                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self._cancel_buy_order(현재가): continue
                        if not 보유중:
                            exec(self.buystg)
                        else:
                            if not self._check_divid_buy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set['매수분할시그널']:
                                exec(self.buystg)

                    if '매도' in gubun:
                        if self._check_sonjeol(수익률, 수익금): continue
                        if self._cancel_sell_order(매수분할횟수): continue
                        if self.dict_set['매도분할횟수'] == 1:
                            exec(self.sellstg)
                        else:
                            if not self._check_divid_sell(포지션, 수익률, 매도분할횟수) and self.dict_set['매도분할시그널']:
                                exec(self.sellstg)

        elif self.opti_kind == 3:
            for vturn in self.trade_info:
                for vkey in self.trade_info[vturn]:
                    index_ = vturn * 20 + vkey
                    if self.back_type != '조건최적화':
                        self.vars = self.vars_lists[index_]
                        if vturn != 0:
                            if self.tick_count < self.vars[0]:
                                return
                        else:
                            if self.tick_count < self.vars[0]:
                                continue
                    elif self.tick_count < self.avgtime:
                        return

                    if self.dict_condition:
                        self.turn_key = f'{vturn}{vturn}'
                        if 종목코드 not in self.dict_cond_indexn:
                            self.dict_cond_indexn[종목코드] = {}
                        for k, v in self.dict_condition.items():
                            exec(v)

                    self.curr_day_info = self.day_info[vturn][vkey]
                    self.curr_trade_info = self.trade_info[vturn][vkey]

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()

                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                        self._get_hold_info(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)

                    self.info_for_order = \
                        보유중, 매수가, 현재가, 저가대비고가등락율, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수, vturn, vkey

                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self._check_buy_or_sell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량,
                                                    보유수량, 매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수,
                                                    매도주문취소시간, 주문포지션)
                    if gubun is None: continue

                    매수, 매도 = True, False
                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False

                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self._cancel_buy_order(현재가): continue
                        if not 보유중:
                            if self.back_type != '조건최적화':
                                exec(self.buystg)
                            else:
                                exec(self.dict_buystg[index_])
                        else:
                            if not self._check_divid_buy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set['매수분할시그널']:
                                if self.back_type != '조건최적화':
                                    exec(self.buystg)
                                else:
                                    exec(self.dict_buystg[index_])

                    if '매도' in gubun:
                        if self._check_sonjeol(수익률, 수익금): continue
                        if self._cancel_sell_order(매수분할횟수): continue
                        if self.dict_set['매도분할횟수'] == 1:
                            if self.back_type != '조건최적화':
                                exec(self.sellstg)
                            else:
                                exec(self.dict_sellstg[index_])
                        else:
                            if not self._check_divid_sell(포지션, 수익률, 매도분할횟수) and self.dict_set['매도분할시그널']:
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

            if self.dict_condition:
                self.turn_key = f'{vturn}{vturn}'
                if 종목코드 not in self.dict_cond_indexn:
                    self.dict_cond_indexn[종목코드] = {}
                for k, v in self.dict_condition.items():
                    exec(v)

            self.curr_day_info = self.day_info[vturn][vkey]
            self.curr_trade_info = self.trade_info[vturn][vkey]

            보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()

            포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                self._get_hold_info(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)

            self.info_for_order = \
                보유중, 매수가, 현재가, 저가대비고가등락율, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수, vturn, vkey

            self.profit, self.hold_time = 수익률, 보유시간

            gubun = self._check_buy_or_sell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량,
                                            매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션)
            if gubun is None: return

            매수, 매도 = True, False
            BUY_LONG, SELL_SHORT = True, True
            SELL_LONG, BUY_SHORT = False, False

            if '매수' in gubun:
                if not 관심종목: return
                if self._cancel_buy_order(현재가): return
                if not 보유중:
                    exec(self.buystg)
                else:
                    if not self._check_divid_buy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set['매수분할시그널']:
                        exec(self.buystg)

            if '매도' in gubun:
                if self._check_sonjeol(수익률, 수익금): return
                if self._cancel_sell_order(매수분할횟수): return
                if self.dict_set['매도분할횟수'] == 1:
                    exec(self.sellstg)
                else:
                    if not self._check_divid_sell(포지션, 수익률, 매도분할횟수) and self.dict_set['매도분할시그널']:
                        exec(self.sellstg)

    def _get_hold_info(self, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간):
        """보유 정보를 계산합니다 (OMS 버전).
        Args:
            보유수량: 보유 수량
            매수가: 매수 가격
            현재가: 현재 가격
            최고수익률: 최고 수익률
            최저수익률: 최저 수익률
            매수틱번호: 매수 틱 번호
            매수시간: 매수 시간
        Returns:
            (시가총액또는포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간) 튜플
        """
        시가총액또는포지션, 수익금, 수익률, 보유시간 = None, 0, 0, 0
        if self.curr_trade_info['보유중']:
            시가총액또는포지션, _, 수익금, 수익률 = self._get_profit_info(현재가, 매수가, 보유수량)
            if 수익률 > 최고수익률:   self.curr_trade_info['최고수익률'] = 최고수익률 = 수익률
            elif 수익률 < 최저수익률: self.curr_trade_info['최저수익률'] = 최저수익률 = 수익률
            now_time = self._now()
            # noinspection PyUnresolvedReferences
            보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
            self.indexb = 매수틱번호
        return 시가총액또는포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간

    def _check_buy_or_sell(self, 보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량, 매수호가단위,
                           매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션, 분봉고가=None, 분봉저가=None):
        """매수 또는 매도 여부를 확인합니다.
        주문 유형(시장가/지정가)과 보유 상태에 따라
        매수, 매도, 매수매도 중 하나를 결정합니다.
        Returns:
            '매수', '매도', '매수매도' 또는 None
        """
        gubun = None
        if self.dict_set['매수주문유형'] == '시장가':
            if not 보유중:
                gubun = '매수'
            elif 매수분할횟수 < self.dict_set['매수분할횟수']:
                gubun = '매수매도'
            else:
                gubun = '매도'

        elif self.dict_set['매수주문유형'] == '지정가':
            관심종목1 = self._관심종목N(1)
            if not 보유중:
                if 매수호가 == 0:
                    gubun = '매수'
                else:
                    관심이탈 = not 관심종목 and 관심종목1
                    self._check_buy(
                        주문포지션, 현재가, 관심이탈, 분봉고가, 분봉저가, 매수가, 주문수량, 보유수량, 매수호가, 매수호가단위, 매수주문취소시간
                    )
                    return gubun

            elif 매수분할횟수 < self.dict_set['매수분할횟수']:
                if 매수호가 == 0 and 매도호가 == 0:
                    if self.dict_set['매도금지매수횟수'] and 매수분할횟수 < self.dict_set['매도금지매수횟수값']:
                        gubun = '매수'
                    else:
                        gubun = '매수매도'
                elif 매수호가 != 0:
                    관심이탈 = not 관심종목 and 관심종목1
                    self._check_buy(
                        주문포지션, 현재가, 관심이탈, 분봉고가, 분봉저가, 매수가, 주문수량, 보유수량, 매수호가, 매수호가단위, 매수주문취소시간
                    )
                    return gubun
                else:
                    관심진입 = 관심종목 and not 관심종목1
                    self._check_sell(보유중, 현재가, 관심진입, 분봉고가, 분봉저가, 매도호가, 매도호가단위, 매도정정횟수, 매도주문취소시간)
                    return gubun

            else:
                if 매도호가 == 0:
                    gubun = '매도'
                else:
                    관심진입 = 관심종목 and not 관심종목1
                    self._check_sell(보유중, 현재가, 관심진입, 분봉고가, 분봉저가, 매도호가, 매도호가단위, 매도정정횟수, 매도주문취소시간)
                    return gubun

        return gubun

    def _cancel_buy_order(self, 현재가):
        """매수 주문 취소 조건을 확인합니다.
        Args:
            현재가: 현재 가격
        Returns:
            취소 여부
        """
        cancel = False
        now_time = self._now()
        거래횟수, 손절횟수, 직전거래시간, 손절매도시간 = self.curr_day_info.values()
        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set['매수금지거래횟수'] and self.dict_set['매수금지거래횟수값'] <= 거래횟수:
            cancel = True
        elif self.dict_set['매수금지손절횟수'] and self.dict_set['매수금지손절횟수값'] <= 손절횟수:
            cancel = True
        elif self.dict_set['매수금지시간'] and self.dict_set['매수금지시작시간'] < hms < self.dict_set['매수금지종료시간']:
            cancel = True
        elif self.dict_set['매수금지간격'] and now_time <= 직전거래시간:
            cancel = True
        elif self.dict_set['매수금지손절간격'] and now_time <= 손절매도시간:
            cancel = True
        elif self.market_gubun in (3, 4) and self.dict_set['매수금지200원이하'] and 현재가 <= 200:
            cancel = True
        return cancel

    def Buy(self, buy_long=False):
        """매수 주문을 실행합니다 (OMS 버전).
        Args:
            buy_long: 롱 포지션 여부
        """
        self._get_buy_count(buy_long)
        주문수량 = self.curr_trade_info['주문수량']
        if 주문수량 > 0:
            if self.dict_set['매수주문유형'] == '시장가':
                if self.market_gubun < 6 or buy_long:
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
                    추가매수가 = self._get_order_price(거래금액, 주문수량)
                    평단가 = self._get_order_price(매수가 * 보유수량 + 거래금액, 총수량)
                    주문포지션 = None if self.market_gubun < 6 else 'LONG' if buy_long else 'SHORT'
                    self.curr_trade_info.update({
                        '매수가': 평단가,
                        '보유수량': 총수량,
                        '추가매수가': 추가매수가
                    })
                    self._update_buy_info(주문포지션, True if 매수가 == 0 else False)

            elif self.dict_set['매수주문유형'] == '지정가':
                매수주문취소시간 = timedelta_sec(
                    self.dict_set['매수취소시간초'],
                    dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
                )
                self.curr_trade_info.update({
                    '매수호가': self.curr_trade_info['매수호가_'],
                    '매수호가단위': self.hoga_unit,
                    '매수주문취소시간': 매수주문취소시간
                })

    def _get_buy_count(self, buy_long=False):
        """매수 수량을 계산합니다 (OMS 버전).
        비중 조절과 분할 매수 비율을 고려하여 주문 수량을 계산합니다.
        Args:
            buy_long: 롱 포지션 여부
        """
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

        order_ratio = dict_order_ratio[self.dict_set['매수분할방법']][self.dict_set['매수분할횟수']]
        oc_ratio = order_ratio[매수분할횟수]
        self.curr_trade_info['주문수량'] = self._set_buy_count(betting, 현재가, 매수가, oc_ratio)

        if self.dict_set['매수주문유형'] == '지정가':
            기준가격 = 현재가
            if self.dict_set['매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.curr_trade_info['매수호가_'] = 기준가격 + self.hoga_unit * self.dict_set['매수지정가호가번호']

    def _check_divid_buy(self, 포지션, 현재가, 추가매수가, 수익률):
        """분할 매수 조건을 확인합니다.
        수익률에 따른 분할 매수 조건을 확인하고 매수를 실행합니다.
        Args:
            포지션: 시가총액 또는 포지션
            현재가: 현재 가격
            추가매수가: 추가 매수 가격
            수익률: 수익률
        Returns:
            매수 실행 여부
        """
        분할매수기준수익률 = round((현재가 / 추가매수가 - 1) * 100, 2) if self.dict_set['매수분할고정수익률'] else 수익률
        if self.market_gubun < 6:
            if self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                self.Buy()
                return True
            elif self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                self.Buy()
                return True
        else:
            if 포지션 == 'LONG' and self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                self.Buy(True)
                return True
            elif 포지션 == 'LONG' and self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                self.Buy(True)
                return True
            elif 포지션 == 'SHORT' and self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                self.Buy(False)
                return True
            elif 포지션 == 'SHORT' and self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                self.Buy(False)
                return True
        return False

    def _check_buy(self, 주문포지션, 현재가, 관심이탈, 분봉고가, 분봉저가, 매수가, 주문수량, 보유수량, 매수호가, 매수호가단위, 매수주문취소시간):
        """매수 주문 정정/취소 조건을 확인합니다.
        관심 종목 이탈, 시간 초과 등 조건에 따라 매수 주문을 취소합니다.
        """
        if self.dict_set['매수취소관심이탈'] and 관심이탈:
            self.curr_trade_info['매수호가'] = 0

        elif self.dict_set['매수취소시간'] and \
                (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매수주문취소시간:
            self.curr_trade_info['매수호가'] = 0

        elif (주문포지션 is None or 주문포지션 == 'LONG') and \
                self.curr_trade_info['매수정정횟수'] < self.dict_set['매수정정횟수'] and \
                현재가 >= 매수호가 + 매수호가단위 * self.dict_set['매수정정호가차이']:
            매수호가 = 현재가 - 매수호가단위 * self.dict_set['매수정정호가']
            매수정정횟수 = self.curr_trade_info['매수정정횟수'] + 1
            self.curr_trade_info.update({
                '매수호가': 매수호가,
                '매수정정횟수': 매수정정횟수,
                '매수호가단위': self.hoga_unit
            })

        elif 주문포지션 == 'SHORT' and \
                self.curr_trade_info['매수정정횟수'] < self.dict_set['매수정정횟수'] and \
                현재가 <= 매수호가 - 매수호가단위 * self.dict_set['매수정정호가차이']:
            매수호가 = 현재가 + 매수호가단위 * self.dict_set['매수정정호가']
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
                평단가 = self._get_order_price(매수가 * 보유수량 + 매수호가 * 주문수량, 총수량)
                self.curr_trade_info.update({
                    '매수가': 평단가,
                    '보유수량': 총수량,
                    '추가매수가': 매수호가
                })
                self._update_buy_info(주문포지션, True if 매수가 == 0 else False)

    def _update_buy_info(self, 주문포지션, firstbuy):
        """매수 정보를 업데이트합니다.
        매수 체결 후 거래 정보를 업데이트합니다.
        Args:
            주문포지션 (str or None): 주문 포지션
            firstbuy (bool): 첫 매수 여부
        """
        datetimefromindex = dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
        self.curr_trade_info.update({
            '보유중': 1 if 주문포지션 is None or 주문포지션 == 'LONG' else 2,
            '매수호가': 0,
            '매수정정횟수': 0
        })

        self.curr_day_info['직전거래시간'] = timedelta_sec(self.dict_set['매수금지간격초'], datetimefromindex)
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

    def _check_sonjeol(self, 수익률, 수익금):
        """익절/손절 조건을 확인합니다.
        수익률과 수익금에 따른 익절/손절 조건을 확인하고 청산합니다.
        Args:
            수익률: 수익률
            수익금: 수익금
        Returns:
            청산 실행 여부
        """
        A = self.dict_set['매도익절수익률청산'] and 수익률 > self.dict_set['매도익절수익률']
        B = self.dict_set['매도익절수익금청산'] and 수익금 > self.dict_set['매도익절수익금']
        C = self.dict_set['매도손절수익률청산'] and 수익률 < -self.dict_set['매도손절수익률']
        D = self.dict_set['매도손절수익금청산'] and 수익금 < -self.dict_set['매도손절수익금']
        if A or B or C or D:
            origin_sell_gubun = self.dict_set['매도주문유형']
            self.dict_set['매도주문유형'] = '시장가'
            self.curr_trade_info['주문수량'] = self.curr_trade_info['보유수량']
            self.Sell()
            self.sell_cond = 1001 if A or B else 1002
            self.dict_set['매도주문유형'] = origin_sell_gubun
            return True
        return False

    def _cancel_sell_order(self, 매수분할횟수):
        """매도 주문 취소 조건을 확인합니다.
        Args:
            매수분할횟수: 매수 분할 횟수
        Returns:
            취소 여부
        """
        cancel = False
        if self.dict_set['매도주문유형'] == '시장가':
            if 매수분할횟수 != self.curr_trade_info['매수분할횟수']:
                cancel = True
                return cancel
        elif self.curr_trade_info['매수호가'] != 0:
            cancel = True
            return cancel

        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set['매도금지시간'] and self.dict_set['매도금지시작시간'] < hms < self.dict_set['매도금지종료시간']:
            cancel = True
        elif self.dict_set['매도금지간격'] and self._now() <= self.curr_day_info['직전거래시간']:
            cancel = True
        elif self.dict_set['매수분할횟수'] > 1 and self.dict_set['매도금지매수횟수'] and \
                매수분할횟수 <= self.dict_set['매도금지매수횟수값']:
            cancel = True
        return cancel

    def Sell(self, sell_long=False):
        """매도 주문을 실행합니다 (OMS 버전).
        Args:
            sell_long: 롱 포지션 매도 여부
        """
        self._get_sell_count()
        if self.dict_set['매도주문유형'] == '시장가':
            주문수량 = self.curr_trade_info['주문수량']
            if 주문수량 > 0:
                if self.market_gubun < 6 or sell_long:
                    호가배열 = self.bhogainfo[:self.sell_hj_limit]
                    잔량배열 = self.bhreminfo[:self.sell_hj_limit]
                else:
                    호가배열 = self.shogainfo[:self.sell_hj_limit]
                    잔량배열 = self.shreminfo[:self.sell_hj_limit]

                거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
                if 체결완료:
                    self.curr_trade_info['매도가'] = self._get_order_price(거래금액, 주문수량)
                    self._calculation_eyun()

        elif self.dict_set['매도주문유형'] == '지정가':
            매도주문취소시간 = timedelta_sec(
                self.dict_set['매도취소시간초'],
                dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
            )
            self.curr_trade_info.update({
                '매도호가': self.curr_trade_info['매도호가_'],
                '매도호가단위': self.hoga_unit,
                '매도주문취소시간': 매도주문취소시간
            })

    def _get_sell_count(self):
        """매도 수량을 계산합니다.
        분할 매도 비율을 고려하여 주문 수량을 계산합니다.
        """
        _, _, 현재가, _, _, 매도호가1, 매수호가1, 보유수량, 매도분할횟수 = self.info_for_order[:-2]
        if self.dict_set['매도분할횟수'] == 1:
            self.curr_trade_info['주문수량'] = 보유수량
        else:
            dict_ratio = dict_order_ratio[self.dict_set['매도분할방법']][self.dict_set['매도분할횟수']]
            oc_ratio = dict_ratio[매도분할횟수]
            보유비율 = sum(비율 for 횟수, 비율 in dict_ratio.items() if 횟수 >= 매도분할횟수)
            매도수량 = self._set_sell_count(보유수량, 보유비율, oc_ratio)

            self.curr_trade_info['주문수량'] = 매도수량
            if self.curr_trade_info['주문수량'] > 보유수량 or 매도분할횟수 + 1 == self.dict_set['매도분할횟수']:
                self.curr_trade_info['주문수량'] = 보유수량

        if self.dict_set['매도주문유형'] == '지정가':
            기준가격 = 현재가
            if self.dict_set['매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.curr_trade_info['매도호가_'] = 기준가격 + self.hoga_unit * self.dict_set['매도지정가호가번호']

    def _check_divid_sell(self, 포지션, 수익률, 매도분할횟수):
        """분할 매도 조건을 확인합니다.
        수익률에 따른 분할 매도 조건을 확인하고 매도를 실행합니다.
        Args:
            포지션: 포지션
            수익률: 수익률
            매도분할횟수: 매도 분할 횟수
        Returns:
            매도 실행 여부
        """
        if 포지션.__class__ == int:
            if self.dict_set['매도분할하방'] and 수익률 < -self.dict_set['매도분할하방수익률'] * (매도분할횟수 + 1):
                self.Sell()
                self.sell_cond = 1000
                return True
            elif self.dict_set['매도분할상방'] and 수익률 > self.dict_set['매도분할상방수익률'] * (매도분할횟수 + 1):
                self.Sell()
                self.sell_cond = 1000
                return True
        else:
            if 포지션 == 'LONG' and self.dict_set['매도분할하방'] and \
                    수익률 < -self.dict_set['매도분할하방수익률'] * (매도분할횟수 + 1):
                self.Sell(True)
                self.sell_cond = 1000
                return True
            elif 포지션 == 'LONG' and self.dict_set['매도분할상방'] and \
                    수익률 > self.dict_set['매도분할상방수익률'] * (매도분할횟수 + 1):
                self.Sell(True)
                self.sell_cond = 1000
                return True
            elif 포지션 == 'SHORT' and self.dict_set['매도분할하방'] and \
                    수익률 < -self.dict_set['매도분할하방수익률'] * (매도분할횟수 + 1):
                self.Sell(False)
                self.sell_cond = 1000
                return True
            elif 포지션 == 'SHORT' and self.dict_set['매도분할상방'] and \
                    수익률 > self.dict_set['매도분할상방수익률'] * (매도분할횟수 + 1):
                self.Sell(False)
                self.sell_cond = 1000
                return True
        return False

    def _check_sell(self, 보유중, 현재가, 관심진입, 분봉고가, 분봉저가, 매도호가, 매도호가단위, 매도정정횟수, 매도주문취소시간):
        """매도 주문 정정/취소 조건을 확인합니다.
        관심 종목 진입, 시간 초과 등 조건에 따라 매도 주문을 취소하거나 정정합니다.
        """
        if self.dict_set['매도취소관심진입'] and 관심진입:
            self.curr_trade_info['매도호가'] = 0

        elif self.dict_set['매도취소시간'] and \
                (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매도주문취소시간:
            self.curr_trade_info['매도호가'] = 0

        elif self.market_gubun < 6:
            if 매도정정횟수 < self.dict_set['매도정정횟수'] and \
                    현재가 <= 매도호가 - 매도호가단위 * self.dict_set['매도정정호가차이']:
                self.curr_trade_info['매도호가'] = 현재가 + 매도호가단위 * self.dict_set['매도정정호가']
                self.curr_trade_info['매도정정횟수'] += 1
                self.curr_trade_info['매도호가단위'] = self.hoga_unit
            elif (분봉고가 is None and 현재가 > 매도호가) or (분봉고가 is not None and 분봉고가 > 매도호가):
                self.curr_trade_info['매도가'] = 매도호가
                self._calculation_eyun()

        else:
            gubun = 'LONG' if 보유중 == 1 else 'SHORT'
            if gubun == 'LONG' and 매도정정횟수 < self.dict_set['매도정정횟수'] and \
                    현재가 <= 매도호가 - 매도호가단위 * self.dict_set['매도정정호가차이']:
                self.curr_trade_info['매도호가'] = 현재가 + 매도호가단위 * self.dict_set['매도정정호가']
                self.curr_trade_info['매도정정횟수'] += 1
            elif gubun == 'SHORT' and 매도정정횟수 < self.dict_set['매도정정횟수'] and \
                    현재가 >= 매도호가 + 매도호가단위 * self.dict_set['매도정정호가차이']:
                self.curr_trade_info['매도호가'] = 현재가 - 매도호가단위 * self.dict_set['매도정정호가']
                self.curr_trade_info['매도정정횟수'] += 1
            else:
                A = gubun == 'LONG' and ((분봉고가 is None and 현재가 > 매도호가) or (분봉고가 is not None and 분봉고가 > 매도호가))
                B = gubun == 'SHORT' and ((분봉저가 is None and 현재가 < 매도호가) or (분봉저가 is not None and 분봉저가 < 매도호가))
                if A or B:
                    self.curr_trade_info['매도가'] = 매도호가
                    self._calculation_eyun()

    def _calculation_eyun(self):
        """실제 거래 결과를 계산하고 기록합니다.
        매수/매도 거래의 수익률, 수익금 등을 계산하여 결과 큐에 전송합니다.
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
        시가총액또는포지션, 평가금액, 수익금, 수익률 = self._get_profit_info(매도가, 매수가, 주문수량)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '^'.join(추가매수시간), 보유수량 - 주문수량 == 0

        data = ('백테결과', self.name, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금,
                매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_kind in (1, 3) else (self.sell_count % 5)].put(data)

        self.sell_count += 1
        self.curr_day_info['거래횟수'] += 1

        if 수익률 < 0:
            손절매도시간 = timedelta_sec(
                self.dict_set['매수금지손절간격초'],
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

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다 (오버라이드용).
        하위 클래스에서 오버라이드하여 구현합니다.
        Args:
            보유수량: 보유 수량
            보유비율: 보유 비율
            oc_ratio: 분할 비율
        Returns:
            매도 수량
        """
        return 0
