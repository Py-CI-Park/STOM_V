
import numpy as np
from talib import stream
from utility.static_method.static import dt_ymdhms, dt_ymdhm


class StgGlobalsFunc:
    """전략 전역 함수를 제공하는 기본 클래스입니다.
    백테스트 및 실시간 트레이딩에서 사용되는 전역 함수들을 제공합니다.
    """

    def __init__(self):
        self.code             = None
        self.name             = None
        self.arry_code        = None
        self.avgtime          = None
        self.back_type        = None
        self.pre_func_keys    = None
        self.turn_key         = None
        self.mc               = None
        self.mh               = None
        self.ml               = None
        self.mv               = None
        self.k                = None

        self.fm_list          = None
        self.fm_tcnt          = None
        self.check            = None
        self.line             = None
        self.up               = None
        self.down             = None
        self.is_tick          = False
        self.backtest         = False

        self.vars             = {}
        self.dict_condition   = {}
        self.dict_cond_indexn = {}
        self.high_low         = {}
        self.dict_findex      = {}
        self.avg_list         = []
        self.sma_list         = []

        self.index            = 0
        self.indexn           = 0
        self.indexb           = 0
        self.tick_count       = 0
        self.ma_round_unit    = 0
        self.angle_pct_cf     = 0
        self.angle_dtm_cf     = 0
        self.hoga_unit        = 0
        self.profit           = 0
        self.hold_time        = 0
        self.add_cnt          = 0

        self.shogainfo        = np.zeros(5, dtype=np.float64)
        self.shreminfo        = np.zeros(5, dtype=np.float64)
        self.bhogainfo        = np.zeros(5, dtype=np.float64)
        self.bhreminfo        = np.zeros(5, dtype=np.float64)

    def _calc_fill_amount(self, 주문수량, 호가배열, 잔량배열):
        """체결 금액을 계산합니다.
        Args:
            주문수량 (int): 주문 수량
            호가배열 (np.ndarray): 호가 배열
            잔량배열 (np.ndarray): 잔량 배열
        Returns:
            tuple: (거래금액, 체결성공여부)
        """
        누적잔량 = np.cumsum(잔량배열)
        fill_idx = np.searchsorted(누적잔량, 주문수량, side='left')
        if fill_idx >= len(호가배열):
            return 0, False
        이전누적 = 누적잔량[fill_idx - 1] if fill_idx > 0 else 0
        남은수량 = 주문수량 - 이전누적
        # noinspection PyUnresolvedReferences
        거래금액 = np.sum(호가배열[:fill_idx] * 잔량배열[:fill_idx]) + 호가배열[fill_idx] * 남은수량
        return 거래금액, True

    def _now(self):
        """현재 시간을 반환합니다.
        Returns:
            datetime: 현재 시간
        """
        return dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))

    def _parameter_previous(self, cidx, pre):
        """이전 파라미터를 반환합니다.
        Args:
            cidx (int): 컬럼 인덱스
            pre (int): 이전 틱 수
        Returns:
            float: 파라미터 값
        """
        if pre < self.tick_count:
            ridx = self.indexn - pre if pre != -1 else self.indexb
            return self.arry_code[ridx, cidx]
        return 0

    def _현재가N(self, pre):
        return self._parameter_previous(self.dict_findex['현재가'], pre)

    def _시가N(self, pre):
        return self._parameter_previous(self.dict_findex['시가'], pre)

    def _고가N(self, pre):
        return self._parameter_previous(self.dict_findex['고가'], pre)

    def _저가N(self, pre):
        return self._parameter_previous(self.dict_findex['저가'], pre)

    def _등락율N(self, pre):
        return self._parameter_previous(self.dict_findex['등락율'], pre)

    def _당일거래대금N(self, pre):
        return self._parameter_previous(self.dict_findex['당일거래대금'], pre)

    def _체결강도N(self, pre):
        return self._parameter_previous(self.dict_findex['체결강도'], pre)

    def _초당매수수량N(self, pre):
        return self._parameter_previous(self.dict_findex['초당매수수량'], pre)

    def _초당매도수량N(self, pre):
        return self._parameter_previous(self.dict_findex['초당매도수량'], pre)

    def _시가총액N(self, pre):
        return self._parameter_previous(self.dict_findex['시가총액'], pre)

    def _VI해제시간N(self, pre):
        return dt_ymdhms(str(int(self._parameter_previous(self.dict_findex['VI해제시간'], pre))))

    def _VI가격N(self, pre):
        return self._parameter_previous(self.dict_findex['VI가격'], pre)

    def _VI호가단위N(self, pre):
        return self._parameter_previous(self.dict_findex['VI호가단위'], pre)

    def _초당거래대금N(self, pre):
        return self._parameter_previous(self.dict_findex['초당거래대금'], pre)

    def _고저평균대비등락율N(self, pre):
        return self._parameter_previous(self.dict_findex['고저평균대비등락율'], pre)

    def _저가대비고가등락율N(self, pre):
        return self._parameter_previous(self.dict_findex['저가대비고가등락율'], pre)

    def _초당매수금액N(self, pre):
        return self._parameter_previous(self.dict_findex['초당매수금액'], pre)

    def _초당매도금액N(self, pre):
        return self._parameter_previous(self.dict_findex['초당매도금액'], pre)

    def _당일매수금액N(self, pre):
        return self._parameter_previous(self.dict_findex['당일매수금액'], pre)

    def _최고매수금액N(self, pre):
        return self._parameter_previous(self.dict_findex['최고매수금액'], pre)

    def _최고매수가격N(self, pre):
        return self._parameter_previous(self.dict_findex['최고매수가격'], pre)

    def _당일매도금액N(self, pre):
        return self._parameter_previous(self.dict_findex['당일매도금액'], pre)

    def _최고매도금액N(self, pre):
        return self._parameter_previous(self.dict_findex['최고매도금액'], pre)

    def _최고매도가격N(self, pre):
        return self._parameter_previous(self.dict_findex['최고매도가격'], pre)

    def _매도호가5N(self, pre):
        return self._parameter_previous(self.dict_findex['매도호가5'], pre)

    def _매도호가4N(self, pre):
        return self._parameter_previous(self.dict_findex['매도호가4'], pre)

    def _매도호가3N(self, pre):
        return self._parameter_previous(self.dict_findex['매도호가3'], pre)

    def _매도호가2N(self, pre):
        return self._parameter_previous(self.dict_findex['매도호가2'], pre)

    def _매도호가1N(self, pre):
        return self._parameter_previous(self.dict_findex['매도호가1'], pre)

    def _매수호가1N(self, pre):
        return self._parameter_previous(self.dict_findex['매수호가1'], pre)

    def _매수호가2N(self, pre):
        return self._parameter_previous(self.dict_findex['매수호가2'], pre)

    def _매수호가3N(self, pre):
        return self._parameter_previous(self.dict_findex['매수호가3'], pre)

    def _매수호가4N(self, pre):
        return self._parameter_previous(self.dict_findex['매수호가4'], pre)

    def _매수호가5N(self, pre):
        return self._parameter_previous(self.dict_findex['매수호가5'], pre)

    def _매도잔량5N(self, pre):
        return self._parameter_previous(self.dict_findex['매도잔량5'], pre)

    def _매도잔량4N(self, pre):
        return self._parameter_previous(self.dict_findex['매도잔량4'], pre)

    def _매도잔량3N(self, pre):
        return self._parameter_previous(self.dict_findex['매도잔량3'], pre)

    def _매도잔량2N(self, pre):
        return self._parameter_previous(self.dict_findex['매도잔량2'], pre)

    def _매도잔량1N(self, pre):
        return self._parameter_previous(self.dict_findex['매도잔량1'], pre)

    def _매수잔량1N(self, pre):
        return self._parameter_previous(self.dict_findex['매수잔량1'], pre)

    def _매수잔량2N(self, pre):
        return self._parameter_previous(self.dict_findex['매수잔량2'], pre)

    def _매수잔량3N(self, pre):
        return self._parameter_previous(self.dict_findex['매수잔량3'], pre)

    def _매수잔량4N(self, pre):
        return self._parameter_previous(self.dict_findex['매수잔량4'], pre)

    def _매수잔량5N(self, pre):
        return self._parameter_previous(self.dict_findex['매수잔량5'], pre)

    def _매도총잔량N(self, pre):
        return self._parameter_previous(self.dict_findex['매도총잔량'], pre)

    def _매수총잔량N(self, pre):
        return self._parameter_previous(self.dict_findex['매수총잔량'], pre)

    def _매도수5호가잔량합N(self, pre):
        return self._parameter_previous(self.dict_findex['매도수5호가잔량합'], pre)

    def _관심종목N(self, pre):
        return self._parameter_previous(self.dict_findex['관심종목'], pre)

    def _분봉시가N(self, pre):
        return self._parameter_previous(self.dict_findex['분봉시가'], pre)

    def _분봉고가N(self, pre):
        return self._parameter_previous(self.dict_findex['분봉고가'], pre)

    def _분봉저가N(self, pre):
        return self._parameter_previous(self.dict_findex['분봉저가'], pre)

    def _최고분봉고가(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최고분봉고가'], self.dict_findex['분봉고가'], tick, pre, np.max, calc=calc)

    def _최저분봉저가(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최저분봉저가'], self.dict_findex['분봉저가'], tick, pre, np.min, calc=calc)

    def _분당매수수량N(self, pre):
        return self._parameter_previous(self.dict_findex['분당매수수량'], pre)

    def _분당매도수량N(self, pre):
        return self._parameter_previous(self.dict_findex['분당매도수량'], pre)

    def _분당거래대금N(self, pre):
        return self._parameter_previous(self.dict_findex['분당거래대금'], pre)

    def _분당매수금액N(self, pre):
        return self._parameter_previous(self.dict_findex['분당매수금액'], pre)

    def _분당매도금액N(self, pre):
        return self._parameter_previous(self.dict_findex['분당매도금액'], pre)

    def _최고분당매수수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최고분당매수수량'], self.dict_findex['분당매수수량'], tick, pre, np.max, calc=calc)

    def _최고분당매도수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최고분당매도수량'], self.dict_findex['분당매도수량'], tick, pre, np.max, calc=calc)

    def _누적분당매수수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['누적분당매수수량'], self.dict_findex['분당매수수량'], tick, pre, np.sum, calc=calc)

    def _누적분당매도수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['누적분당매도수량'], self.dict_findex['분당매도수량'], tick, pre, np.sum, calc=calc)

    def _분당거래대금평균(self, tick, pre=0, calc=False):
        return int(self._parameter_area(self.dict_findex['분당거래대금평균'], self.dict_findex['분당거래대금'], tick, pre, np.mean, calc=calc))

    def _get_column_index(self, cidx):
        if self.backtest:
            aidx = self.avg_list.index(self.avgtime if self.back_type in ('백테스트', '조건최적화', '백파인더') else self.vars[0])
            return cidx + self.add_cnt * aidx
        else:
            return cidx

    def _get_double_index(self, tick):
        return self.indexn + 1 - tick, self.indexn + 1

    def _get_double_pre_index(self, tick, pre):
        sidx = self.indexn + 1 - tick - pre if pre != -1 else self.indexb + 1 - tick
        eidx = self.indexn + 1 - pre if pre != -1 else self.indexb + 1
        return sidx, eidx

    def _get_angle_double_pre_index(self, tick, pre):
        sidx = self.indexn - tick - pre if pre != -1 else self.indexb - tick
        eidx = self.indexn - pre if pre != -1 else self.indexb
        return sidx, eidx

    def _이동평균(self, tick, pre=0, calc=False):
        if tick + pre <= self.tick_count:
            if not calc and tick in self.sma_list:
                return self._parameter_previous(self.dict_findex[f'이동평균{tick}'], pre)
            else:
                sidx, eidx = self._get_double_pre_index(tick, pre)
                return round(self.arry_code[sidx:eidx, self.dict_findex['현재가']].mean(), self.ma_round_unit)
        return 0

    def _parameter_area(self, cidx, fidx, tick, pre, func, calc=False):
        if tick + pre <= self.tick_count:
            if not calc and tick in self.avg_list:
                return self._parameter_previous(self._get_column_index(cidx), pre)
            else:
                sidx, eidx = self._get_double_pre_index(tick, pre)
                return func(self.arry_code[sidx:eidx, fidx])
        return 0

    def _parameter_angle(self, cidx, fidx, tick, pre, cf, calc=False):
        if tick + pre <= self.tick_count:
            if not calc and tick in self.avg_list:
                return self._parameter_previous(self._get_column_index(cidx), pre)
            else:
                sidx, eidx = self._get_angle_double_pre_index(tick, pre)
                diff = self.arry_code[eidx, fidx] - self.arry_code[sidx, fidx]
                return round(np.arctan2(diff * cf, tick) / (2 * np.pi) * 360, 2)
        return 0

    def _최고현재가(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최고현재가'], self.dict_findex['현재가'], tick, pre, np.max, calc=calc)

    def _최저현재가(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최저현재가'], self.dict_findex['현재가'], tick, pre, np.min, calc=calc)

    def _체결강도평균(self, tick, pre=0, calc=False):
        return round(self._parameter_area(self.dict_findex['체결강도평균'], self.dict_findex['체결강도'], tick, pre, np.mean, calc=calc), 3)

    def _최고체결강도(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최고체결강도'], self.dict_findex['체결강도'], tick, pre, np.max, calc=calc)

    def _최저체결강도(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최저체결강도'], self.dict_findex['체결강도'], tick, pre, np.min, calc=calc)

    def _최고초당매수수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최고초당매수수량'], self.dict_findex['초당매수수량'], tick, pre, np.max, calc=calc)

    def _최고초당매도수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['최고초당매도수량'], self.dict_findex['초당매도수량'], tick, pre, np.max, calc=calc)

    def _누적초당매수수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['누적초당매수수량'], self.dict_findex['초당매수수량'], tick, pre, np.sum, calc=calc)

    def _누적초당매도수량(self, tick, pre=0, calc=False):
        return self._parameter_area(self.dict_findex['누적초당매도수량'], self.dict_findex['초당매도수량'], tick, pre, np.sum, calc=calc)

    def _초당거래대금평균(self, tick, pre=0, calc=False):
        return int(self._parameter_area(self.dict_findex['초당거래대금평균'], self.dict_findex['초당거래대금'], tick, pre, np.mean, calc=calc))

    def _등락율각도(self, tick, pre=0, calc=False):
        return self._parameter_angle(self.dict_findex['등락율각도'], self.dict_findex['등락율'], tick, pre, self.angle_pct_cf, calc=calc)

    def _당일거래대금각도(self, tick, pre=0, calc=False):
        return self._parameter_angle(self.dict_findex['당일거래대금각도'], self.dict_findex['당일거래대금'], tick, pre, self.angle_dtm_cf, calc=calc)

    def _경과틱수(self, 조건명):
        조건명 = f'{조건명}{self.turn_key}'
        if self.code in self.dict_cond_indexn and \
                조건명 in self.dict_cond_indexn[self.code] and self.dict_cond_indexn[self.code][조건명] != 0:
            return self.indexn - self.dict_cond_indexn[self.code][조건명]
        return 0

    def _이평지지(self, tick1, tick2=30, per=0.5, cnt=10):
        if tick1 + tick2 <= self.tick_count and tick1 in self.sma_list:
            sidx, eidx = self._get_double_index(tick2)
            arry_close = self.arry_code[sidx:eidx, self.dict_findex['현재가']]
            arry_sma = self.arry_code[sidx:eidx, self.dict_findex[f'이동평균{tick1}']]
            deviation = np.abs(arry_close - arry_sma) / arry_sma * 100
            return np.sum(deviation <= per) >= cnt
        return 0

    def _시가지지(self, tick, per=0.5, cnt=10):
        if tick <= self.tick_count:
            sidx, eidx = self._get_double_index(tick)
            arry_close = self.arry_code[sidx:eidx, self.dict_findex['현재가']]
            deviation = np.abs(arry_close - self._시가N(0)) / self._시가N(0) * 100
            return np.sum(deviation <= per) >= cnt
        return 0

    # noinspection PyUnresolvedReferences
    def _변동성(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            if self.is_tick:
                arry_close = self.arry_code[sidx:eidx, self.dict_findex['현재가']]
                volatility = np.std(arry_close) / np.mean(arry_close) * 100
            else:
                arry_high  = self.arry_code[sidx:eidx, self.dict_findex['분봉고가']]
                arry_low   = self.arry_code[sidx:eidx, self.dict_findex['분봉저가']]
                volatility = np.std(arry_high - arry_low) / np.mean(arry_high - arry_low) * 100
            return volatility
        return 0

    def _구간저가대비현재가등락율(self, tick):
        if tick <= self.tick_count:
            if self.is_tick:
                return (self._현재가N(0) / self._최저현재가(tick) - 1) * 100
            else:
                return (self._현재가N(0) / self._최저분봉저가(tick) - 1) * 100
        return 0

    def _구간고가대비현재가등락율(self, tick):
        if tick <= self.tick_count:
            if self.is_tick:
                return (self._현재가N(0) / self._최고현재가(tick) - 1) * 100
            else:
                return (self._현재가N(0) / self._최고분봉고가(tick) - 1) * 100
        return 0

    def _거래대금평균대비비율(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            if self.is_tick:
                money_unit = self._초당거래대금N(pre)
                money_avg  = self._초당거래대금평균(tick, pre)
            else:
                money_unit = self._분당거래대금N(pre)
                money_avg  = self._분당거래대금평균(tick, pre)
            return money_unit / money_avg if money_avg > 0 else 0
        return 0

    def _체결강도평균대비비율(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            avg_ch = self._체결강도평균(tick, pre)
            return self._체결강도N(pre) / avg_ch if avg_ch > 0 else 0
        return 0

    def _구간호가총잔량비율(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            sum_bids = self.arry_code[sidx:eidx, self.dict_findex['매수총잔량']].sum()
            sum_asks = self.arry_code[sidx:eidx, self.dict_findex['매도총잔량']].sum()
            total_cnt = sum_bids + sum_asks
            return sum_bids / total_cnt if total_cnt != 0 else 0
        return 0

    def _매수수량변동성(self, tick, pre=0):
        if tick * 2 + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            cur_avg_buys = self.arry_code[sidx:eidx, self.dict_findex['초당매수수량' if self.is_tick else '분당매수수량']].sum()
            pre_avg_buys = self.arry_code[sidx - tick:eidx - tick, self.dict_findex['초당매수수량' if self.is_tick else '분당매수수량']].sum()
            return cur_avg_buys / pre_avg_buys if pre_avg_buys != 0 else 0
        return 0

    def _매도수량변동성(self, tick, pre=0):
        if tick * 2 + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            cur_arry_sells = self.arry_code[sidx:eidx, self.dict_findex['초당매도수량' if self.is_tick else '분당매도수량']].sum()
            pre_arry_sells = self.arry_code[sidx - tick:eidx - tick, self.dict_findex['초당매도수량' if self.is_tick else '분당매도수량']].sum()
            return cur_arry_sells / pre_arry_sells if pre_arry_sells != 0 else 0
        return 0

    def _횡보감지(self, tick, per=0.5, pre=0):
        if tick + pre <= self.tick_count:
            return self._변동성(tick, pre) <= per
        return 0

    def _고가미갱신지속틱수(self):
        return self.indexn - self.high_low[self.code][1]

    def _저가미갱신지속틱수(self):
        return self.indexn - self.high_low[self.code][3]

    def _고점기준등락율각도(self, cf):
        diff_tick = self.indexn - self.high_low[self.code][1]
        diff_pct  = (self._현재가N(0) / self.high_low[self.code][0] - 1) * 100
        return round(np.arctan2(diff_pct * cf, diff_tick) / (2 * np.pi) * 360, 2)

    def _저점기준등락율각도(self, cf):
        diff_tick = self.indexn - self.high_low[self.code][3]
        diff_pct  = (self._현재가N(0) / self.high_low[self.code][2] - 1) * 100
        return round(np.arctan2(diff_pct * cf, diff_tick) / (2 * np.pi) * 360, 2)

    def _연속상승(self, tick):
        if 1 < tick < self.tick_count:
            for cc in range(0, tick):
                if self._현재가N(cc) < self._현재가N(cc + 1):
                    return False
            return True
        return False

    def _연속하락(self, tick):
        if 1 < tick < self.tick_count:
            for cc in range(1, tick):
                if self._현재가N(cc) > self._현재가N(cc + 1):
                    return False
            return True
        return False

    def _호가갭발생(self, hogagap, pre=0):
        if pre < self.tick_count:
            if pre == 0:
                hoga_spread = (self._매도호가1N(0) - self._매수호가1N(0)) / self.hoga_unit
            else:
                hoga_spread = (self._매도호가1N(pre) - self._매수호가1N(pre)) / self.hoga_unit
            return hoga_spread >= hogagap
        return False

    def _변동성급증(self, tick, ratio=2):
        prev_volatility = self._변동성(tick, tick)
        if prev_volatility > 0:
            return self._변동성(tick) / prev_volatility >= ratio
        return False

    def _변동성급감(self, tick, ratio=0.5):
        prev_volatility = self._변동성(tick, tick)
        if prev_volatility > 0:
            if ratio == 0: return False
            return self._변동성(tick) / prev_volatility <= ratio
        return False

    def _가격급등(self, tick, per=1.0):
        return self._구간저가대비현재가등락율(tick) >= per

    def _가격급락(self, tick, per=1.0):
        return self._구간고가대비현재가등락율(tick) <= -per

    def _거래대금급증(self, tick, ratio=3):
        return self._거래대금평균대비비율(tick) >= ratio

    def _거래대금급감(self, tick, ratio=0.5):
        return self._거래대금평균대비비율(tick) <= ratio

    def _체결강도급등(self, tick, ratio=1.1):
        return self._체결강도평균대비비율(tick) >= ratio

    def _체결강도급락(self, tick, ratio=0.9):
        return self._체결강도평균대비비율(tick) <= ratio

    def _호가상승압력(self, tick, ratio=0.7):
        return self._구간호가총잔량비율(tick) >= ratio

    def _호가하락압력(self, tick, ratio=0.3):
        return self._구간호가총잔량비율(tick) <= ratio

    def _매수수량급증(self, tick, ratio=3):
        return self._매수수량변동성(tick) >= ratio

    def _매수수량급감(self, tick, ratio=0.5):
        return self._매수수량변동성(tick) <= ratio

    def _매도수량급증(self, tick, ratio=3):
        return self._매도수량변동성(tick) >= ratio

    def _매도수량급감(self, tick, ratio=0.5):
        return self._매도수량변동성(tick) <= ratio

    def _이평돌파(self, tick, per=1.0):
        sma = self._이동평균(tick)
        if sma == 0: return False
        return self._최저현재가(tick) < sma and (self._현재가N(0) / sma - 1) * 100 >= per

    def _이평이탈(self, tick, per=1.0):
        sma = self._이동평균(tick)
        if sma == 0: return False
        return self._최고현재가(tick) > sma and (self._현재가N(0) / sma - 1) * 100 <= -per

    def _시가돌파(self, tick, per=1.0):
        return self._최저현재가(tick) < self._시가N(0) and (self._현재가N(0) / self._시가N(0) - 1) * 100 >= per

    def _시가이탈(self, tick, per=1.0):
        return self._최고현재가(tick) > self._시가N(0) and (self._현재가N(0) / self._시가N(0) - 1) * 100 <= -per

    def _이평지지후이평돌파(self, tick1, tick2=30, per1=0.5, cnt=10, per2=1.0):
        return self._이평지지(tick1, tick2, per1, cnt) and self._이평돌파(tick1, per2)

    def _이평지지후이평이탈(self, tick1, tick2=30, per1=0.5, cnt=10, per2=1.0):
        return self._이평지지(tick1, tick2, per1, cnt) and self._이평이탈(tick1, per2)

    def _횡보후가격급등(self, tick1, per1=0.5, tick2=10, per2=1.0):
        return self._횡보감지(tick1, per1, tick2) and self._가격급등(tick2, per2)

    def _횡보후가격급락(self, tick1, per1=0.5, tick2=10, per2=1.0):
        return self._횡보감지(tick1, per1, tick2) and self._가격급락(tick2, per2)

    def _횡보후연속상승(self, tick1, per1=0.5, tick2=5):
        return self._횡보감지(tick1, per1, tick2) and self._연속상승(tick2)

    def _횡보후연속하락(self, tick1, per1=0.5, tick2=5):
        return self._횡보감지(tick1, per1, tick2) and self._연속하락(tick2)

    def _연속상승및가격급등(self, tick1, tick2=10, per=1.0):
        return self._연속상승(tick1) and self._가격급등(tick2, per)

    def _연속하락및가격급락(self, tick1, tick2=10, per=1.0):
        return self._연속하락(tick1) and self._가격급락(tick2, per)

    def _거래대금급증및연속상승(self, tick1, ratio=2, tick2=5):
        return self._거래대금급증(tick1, ratio) and self._연속상승(tick2)

    def _거래대금급감및연속하락(self, tick1, ratio=2, tick2=5):
        return self._거래대금급감(tick1, ratio) and self._연속하락(tick2)

    def _호가상승압력및매수수량급증(self, tick, ratio1=0.7, ratio2=3):
        return self._호가상승압력(tick, ratio1) and self._매수수량급증(tick, ratio2)

    def _호가하락압력및매도수량급증(self, tick, ratio=0.3, ratio2=3):
        return self._호가하락압력(tick, ratio) and self._매도수량급증(tick, ratio2)

    def _매수수량급증및가격급등(self, tick, ratio=3, tick2=10, per=1.0):
        return self._매수수량급증(tick, ratio) and self._가격급등(tick2, per)

    def _매도수량급증후가격급락(self, tick, ratio=3, tick2=10, per=1.0):
        return self._매도수량급증(tick, ratio) and self._가격급락(tick2, per)

    def _변동성급증및구간최고가갱신(self, tick, ratio=2):
        return self._변동성급증(tick, ratio) and self._현재가N(0) > self._최고현재가(tick, 1)

    def _변동성급감및구간최저가갱신(self, tick, ratio=0.5):
        return self._변동성급감(tick, ratio) and self._현재가N(0) < self._최저현재가(tick, 1)

    def _거래대금급증및구간최고가갱신(self, tick, ratio=2):
        return self._거래대금급증(tick, ratio) and self._현재가N(0) > self._최고현재가(tick, 1)

    def _거래대금급감후구간최저가갱신(self, tick, ratio=0.5):
        return self._거래대금급감(tick, ratio) and self._현재가N(0) < self._최저현재가(tick, 1)

    def _거래대금급증및가격급등(self, tick1, ratio=2, tick2=10, per=1.0):
        return self._거래대금급증(tick1, ratio) and self._가격급등(tick2, per)

    def _거래대금급감및가격급락(self, tick1, ratio=0.5, tick2=10, per=1.0):
        return self._거래대금급감(tick1, ratio) and self._가격급락(tick2, per)

    def _체결강도급등및호가상승압력(self, tick1, ratio1=1.1, tick2=10, ratio2=0.7):
        return self._체결강도급등(tick1, ratio1) and self._호가상승압력(tick2, ratio2)

    def _체결강도급락및호가하락압력(self, tick1, ratio1=0.9, tick2=10, ratio2=0.3):
        return self._체결강도급락(tick1, ratio1) and self._호가하락압력(tick2, ratio2)

    def _시가근접황보후시가돌파(self, tick, per1=0.5, cnt=10, per2=1.0):
        return self._시가지지(tick, per1, cnt) and self._시가돌파(tick, per2)

    def _시가근접황보후시가이탈(self, tick, per1=0.5, cnt=10, per2=1.0):
        return self._시가지지(tick, per1, cnt) and self._시가이탈(tick, per2)

    def _저가갱신후가격급등(self, tick, per=2):
        return self.indexn - self.high_low[self.code][3] <= tick and self._가격급등(tick, per)

    def _고가갱신후가격급락(self, tick, per=2):
        return self.indexn - self.high_low[self.code][1] <= tick and self._가격급락(tick, per)

    def _횡보상태장기보유(self, tick, per=0.5, time_=600):
        return self._횡보감지(tick, per) and self.hold_time >= time_

    def _변동성급증_역추세매도(self, tick, ratio=3, reversal_per=2.0):
        cur_vol = self._변동성(tick)
        pre_vol = self._변동성(tick, tick)
        if cur_vol >= pre_vol * ratio:
            return self._구간고가대비현재가등락율(tick) <= -reversal_per
        return False

    def _장기보유종목_동적익절청산(self, tick, time_=600, minper=0.3, multi=1):
        if tick <= self.tick_count:
            cur_vol = self._변동성(tick)
            min_profit = max(minper, cur_vol * multi)
            hold_time = max(time_, cur_vol * time_ * multi)
            if self.profit > min_profit and self.hold_time > hold_time:
                return True
        return False

    def _거래대금비율기반_동적청산(self, tick, ratio1=0.3, ratio2=3):
        if tick <= self.tick_count:
            if self.profit > 0:
                return self._거래대금급감(tick, ratio1)
            else:
                return self._거래대금급증(tick, ratio2)
        return False

    def _호가압력기반_동적청산(self, tick, buy_pressure=0.8, sell_pressure=0.2):
        if tick <= self.tick_count:
            if self.profit > 0:
                return self._호가하락압력(tick, sell_pressure)
            else:
                return self._호가상승압력(tick, buy_pressure)
        return False

    def _이평기반_동적청산(self, short, long=60, deviation1=0.5, deviation2=1.0):
        if short <= self.tick_count and long <= self.tick_count:
            short_ma = self._이동평균(short)
            long_ma = self._이동평균(long)
            if short_ma == 0: return False
            if self.profit > 0:
                deviation_pct = abs(self._현재가N(0) - short_ma) / short_ma * 100
                return self._현재가N(0) < short_ma and deviation_pct >= deviation1
            else:
                deviation_pct = abs(self._현재가N(0) - long_ma) / long_ma * 100
                return self._현재가N(0) < long_ma and deviation_pct >= deviation2
        return False

    def _변동성기반_동적청산(self, tick, ratio1=3, ratio2=1.5):
        if tick <= self.tick_count:
            if self.profit > 0:
                return self.profit >= self._변동성(tick) * ratio1
            else:
                return self.profit <= -self._변동성(tick) * ratio2
        return False

    def _변동성급증기반_동적청산(self, tick, multi=2, ratio1=3, ratio2=1.5):
        cur_vol = self._변동성(tick)
        avg_vol = self._변동성(tick, tick)
        if cur_vol > avg_vol * multi:
            if self.profit > 0:
                return self.profit >= cur_vol * ratio1
            else:
                return self.profit <= -cur_vol * ratio2
        return False

    def _AD_N(self, pre):
        if self.backtest:
            try:    AD_ = stream.AD(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], self.mv[:-pre])
            except Exception: AD_ = 0
            return  AD_
        else:
            return self._parameter_previous(self.dict_findex['AD'], pre)

    def _ADOSC_N(self, pre):
        if self.backtest:
            try:    ADOSC_ = stream.ADOSC(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], self.mv[:-pre], fastperiod=self.k[0], slowperiod=self.k[1])
            except Exception: ADOSC_ = 0
            return  ADOSC_
        else:
            return self._parameter_previous(self.dict_findex['ADOSC'], pre)

    def _ADXR_N(self, pre):
        if self.backtest:
            try:    ADXR_ = stream.ADXR(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[2])
            except Exception: ADXR_ = 0
            return  ADXR_
        else:
            return self._parameter_previous(self.dict_findex['ADXR'], pre)

    def _APO_N(self, pre):
        if self.backtest:
            try:    APO_ = stream.APO(self.mc[:-pre], fastperiod=self.k[3], slowperiod=self.k[4], matype=self.k[5])
            except Exception: APO_ = 0
            return  APO_
        else:
            return self._parameter_previous(self.dict_findex['APO'], pre)

    def _AROOND_N(self, pre):
        if self.backtest:
            try:    AROOND_, AROONU_ = stream.AROON(self.mh[:-pre], self.ml[:-pre], timeperiod=self.k[6])
            except Exception: AROOND_, AROONU_ = 0, 0
            return  AROOND_
        else:
            return self._parameter_previous(self.dict_findex['AROOND'], pre)

    def _AROONU_N(self, pre):
        if self.backtest:
            try:    AROOND_, AROONU_ = stream.AROON(self.mh[:-pre], self.ml[:-pre], timeperiod=self.k[3])
            except Exception: AROOND_, AROONU_ = 0, 0
            return  AROONU_
        else:
            return self._parameter_previous(self.dict_findex['AROONU'], pre)

    def _ATR_N(self, pre):
        if self.backtest:
            try:    ATR_ = stream.ATR(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[7])
            except Exception: ATR_ = 0
            return  ATR_
        else:
            return self._parameter_previous(self.dict_findex['ATR'], pre)

    def _BBU_N(self, pre):
        if self.backtest:
            try:    BBU_, BBM_, BBL_ = stream.BBANDS(self.mc[:-pre], timeperiod=self.k[8], nbdevup=self.k[9], nbdevdn=self.k[10], matype=self.k[11])
            except Exception: BBU_, BBM_, BBL_ = 0, 0, 0
            return  BBU_
        else:
            return self._parameter_previous(self.dict_findex['BBU'], pre)

    def _BBM_N(self, pre):
        if self.backtest:
            try:    BBU_, BBM_, BBL_ = stream.BBANDS(self.mc[:-pre], timeperiod=self.k[8], nbdevup=self.k[9], nbdevdn=self.k[10], matype=self.k[11])
            except Exception: BBU_, BBM_, BBL_ = 0, 0, 0
            return  BBM_
        else:
            return self._parameter_previous(self.dict_findex['BBM'], pre)

    def _BBL_N(self, pre):
        if self.backtest:
            try:    BBU_, BBM_, BBL_ = stream.BBANDS(self.mc[:-pre], timeperiod=self.k[8], nbdevup=self.k[9], nbdevdn=self.k[10], matype=self.k[11])
            except Exception: BBU_, BBM_, BBL_ = 0, 0, 0
            return  BBL_
        else:
            return self._parameter_previous(self.dict_findex['BBL'], pre)

    def _CCI_N(self, pre):
        if self.backtest:
            try:    CCI_ = stream.CCI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[12])
            except Exception: CCI_ = 0
            return  CCI_
        else:
            return self._parameter_previous(self.dict_findex['CCI'], pre)

    def _DIM_N(self, pre):
        if self.backtest:
            try:    DIM_ = stream.MINUS_DI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[13])
            except Exception: DIM_ = 0, 0
            return  DIM_
        else:
            return self._parameter_previous(self.dict_findex['DIM'], pre)

    def _DIP_N(self, pre):
        if self.backtest:
            try:    DIP_ = stream.PLUS_DI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[13])
            except Exception: DIP_ = 0
            return  DIP_
        else:
            return self._parameter_previous(self.dict_findex['DIP'], pre)

    def _MACD_N(self, pre):
        if self.backtest:
            try:    MACD_, MACDS_, MACDH_ = stream.MACD(self.mc[:-pre], fastperiod=self.k[14], slowperiod=self.k[15], signalperiod=self.k[16])
            except Exception: MACD_, MACDS_, MACDH_ = 0, 0, 0
            return  MACD_
        else:
            return self._parameter_previous(self.dict_findex['MACD'], pre)

    def _MACDS_N(self, pre):
        if self.backtest:
            try:    MACD_, MACDS_, MACDH_ = stream.MACD(self.mc[:-pre], fastperiod=self.k[14], slowperiod=self.k[15], signalperiod=self.k[16])
            except Exception: MACD_, MACDS_, MACDH_ = 0, 0, 0
            return  MACDS_
        else:
            return self._parameter_previous(self.dict_findex['MACDS'], pre)

    def _MACDH_N(self, pre):
        if self.backtest:
            try:    MACD_, MACDS_, MACDH_ = stream.MACD(self.mc[:-pre], fastperiod=self.k[14], slowperiod=self.k[15], signalperiod=self.k[16])
            except Exception: MACD_, MACDS_, MACDH_ = 0, 0, 0
            return  MACDH_
        else:
            return self._parameter_previous(self.dict_findex['MACDH'], pre)

    def _MFI_N(self, pre):
        if self.backtest:
            try:    MFI_ = stream.MFI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], self.mv[:-pre], timeperiod=self.k[17])
            except Exception: MFI_ = 0
            return  MFI_
        else:
            return self._parameter_previous(self.dict_findex['MFI'], pre)

    def _MOM_N(self, pre):
        if self.backtest:
            try:    MOM_ = stream.MOM(self.mc[:-pre], timeperiod=self.k[18])
            except Exception: MOM_ = 0
            return  MOM_
        else:
            return self._parameter_previous(self.dict_findex['MOM'], pre)

    def _OBV_N(self, pre):
        if self.backtest:
            try:    OBV_ = stream.OBV(self.mc[:-pre], self.mv)
            except Exception: OBV_ = 0
            return  OBV_
        else:
            return self._parameter_previous(self.dict_findex['OBV'], pre)

    def _PPO_N(self, pre):
        if self.backtest:
            try:    PPO_ = stream.PPO(self.mc[:-pre], fastperiod=self.k[19], slowperiod=self.k[20], matype=self.k[21])
            except Exception: PPO_ = 0
            return  PPO_
        else:
            return self._parameter_previous(self.dict_findex['PPO'], pre)

    def _ROC_N(self, pre):
        if self.backtest:
            try:    ROC_ = stream.ROC(self.mc[:-pre], timeperiod=self.k[22])
            except Exception: ROC_ = 0
            return  ROC_
        else:
            return self._parameter_previous(self.dict_findex['ROC'], pre)

    def _RSI_N(self, pre):
        if self.backtest:
            try:    RSI_ = stream.RSI(self.mc[:-pre], timeperiod=self.k[23])
            except Exception: RSI_ = 0
            return  RSI_
        else:
            return self._parameter_previous(self.dict_findex['RSI'], pre)

    def _SAR_N(self, pre):
        if self.backtest:
            try:    SAR_ = stream.SAR(self.mh[:-pre], self.ml[:-pre], acceleration=self.k[24], maximum=self.k[25])
            except Exception: SAR_ = 0
            return  SAR_
        else:
            return self._parameter_previous(self.dict_findex['SAR'], pre)

    def _STOCHSK_N(self, pre):
        if self.backtest:
            try:    STOCHSK_, STOCHSD_ = stream.STOCH(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[26], slowk_period=self.k[27], slowk_matype=self.k[28], slowd_period=self.k[29], slowd_matype=self.k[30])
            except Exception: STOCHSK_, STOCHSD_ = 0, 0
            return  STOCHSK_
        else:
            return self._parameter_previous(self.dict_findex['STOCHSK'], pre)

    def _STOCHSD_N(self, pre):
        if self.backtest:
            try:    STOCHSK_, STOCHSD_ = stream.STOCH(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[26], slowk_period=self.k[27], slowk_matype=self.k[28], slowd_period=self.k[29], slowd_matype=self.k[30])
            except Exception: STOCHSK_, STOCHSD_ = 0, 0
            return  STOCHSD_
        else:
            return self._parameter_previous(self.dict_findex['STOCHSD'], pre)

    def _STOCHFK_N(self, pre):
        if self.backtest:
            try:    STOCHFK_, STOCHFD_ = stream.STOCHF(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[31], fastd_period=self.k[32], fastd_matype=self.k[33])
            except Exception: STOCHFK_, STOCHFD_ = 0, 0
            return  STOCHFK_
        else:
            return self._parameter_previous(self.dict_findex['STOCHFK'], pre)

    def _STOCHFD_N(self, pre):
        if self.backtest:
            try:    STOCHFK_, STOCHFD_ = stream.STOCHF(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[31], fastd_period=self.k[32], fastd_matype=self.k[33])
            except Exception: STOCHFK_, STOCHFD_ = 0, 0
            return  STOCHFD_
        else:
            return self._parameter_previous(self.dict_findex['STOCHFD'], pre)

    def _WILLR_N(self, pre):
        if self.backtest:
            try:    WILLR_ = stream.WILLR(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[34])
            except Exception: WILLR_ = 0
            return  WILLR_
        else:
            return self._parameter_previous(self.dict_findex['WILLR'], pre)

    def set_globals_func(self):
        dict_add_func = {
            '현재가N': self._현재가N,
            '시가N': self._시가N,
            '고가N': self._고가N,
            '저가N': self._저가N,
            '등락율N': self._등락율N,
            '당일거래대금N': self._당일거래대금N,
            '체결강도N': self._체결강도N,

            '고저평균대비등락율N': self._고저평균대비등락율N,
            '저가대비고가등락율N': self._저가대비고가등락율N,
            '초당매수금액N': self._초당매수금액N,
            '초당매도금액N': self._초당매도금액N,
            '당일매수금액N': self._당일매수금액N,
            '최고매수금액N': self._최고매수금액N,
            '최고매수가격N': self._최고매수가격N,
            '당일매도금액N': self._당일매도금액N,
            '최고매도금액N': self._최고매도금액N,
            '최고매도가격N': self._최고매도가격N,

            '초당매수수량N': self._초당매수수량N,
            '초당매도수량N': self._초당매도수량N,
            '초당거래대금N': self._초당거래대금N,
            '최고초당매수수량': self._최고초당매수수량,
            '최고초당매도수량': self._최고초당매도수량,
            '누적초당매수수량': self._누적초당매수수량,
            '누적초당매도수량': self._누적초당매도수량,
            '초당거래대금평균': self._초당거래대금평균,

            '분봉시가N': self._분봉시가N,
            '분봉고가N': self._분봉고가N,
            '분봉저가N': self._분봉저가N,
            '분당매수수량N': self._분당매수수량N,
            '분당매도수량N': self._분당매도수량N,
            '분당거래대금N': self._분당거래대금N,
            '분당매수금액N': self._분당매수금액N,
            '분당매도금액N': self._분당매도금액N,
            '최고분봉고가': self._최고분봉고가,
            '최저분봉저가': self._최저분봉저가,
            '최고분당매수수량': self._최고분당매수수량,
            '최고분당매도수량': self._최고분당매도수량,
            '누적분당매수수량': self._누적분당매수수량,
            '누적분당매도수량': self._누적분당매도수량,
            '분당거래대금평균': self._분당거래대금평균,

            '시가총액N': self._시가총액N,
            'VI해제시간N': self._VI해제시간N,
            'VI가격N': self._VI가격N,
            'VI호가단위N': self._VI호가단위N,

            '매도호가5N': self._매도호가5N,
            '매도호가4N': self._매도호가4N,
            '매도호가3N': self._매도호가3N,
            '매도호가2N': self._매도호가2N,
            '매도호가1N': self._매도호가1N,
            '매수호가1N': self._매수호가1N,
            '매수호가2N': self._매수호가2N,
            '매수호가3N': self._매수호가3N,
            '매수호가4N': self._매수호가4N,
            '매수호가5N': self._매수호가5N,
            '매도잔량5N': self._매도잔량5N,
            '매도잔량4N': self._매도잔량4N,
            '매도잔량3N': self._매도잔량3N,
            '매도잔량2N': self._매도잔량2N,
            '매도잔량1N': self._매도잔량1N,
            '매수잔량1N': self._매수잔량1N,
            '매수잔량2N': self._매수잔량2N,
            '매수잔량3N': self._매수잔량3N,
            '매수잔량4N': self._매수잔량4N,
            '매수잔량5N': self._매수잔량5N,
            '매도총잔량N': self._매도총잔량N,
            '매수총잔량N': self._매수총잔량N,
            '매도수5호가잔량합N': self._매도수5호가잔량합N,
            '관심종목N': self._관심종목N,

            '이동평균': self._이동평균,
            '최고현재가': self._최고현재가,
            '최저현재가': self._최저현재가,
            '체결강도평균': self._체결강도평균,
            '최고체결강도': self._최고체결강도,
            '최저체결강도': self._최저체결강도,
            '등락율각도': self._등락율각도,
            '당일거래대금각도': self._당일거래대금각도,
            '경과틱수': self._경과틱수,

            '이평지지': self._이평지지,
            '시가지지': self._시가지지,
            '변동성': self._변동성,
            '구간저가대비현재가등락율': self._구간저가대비현재가등락율,
            '구간고가대비현재가등락율': self._구간고가대비현재가등락율,
            '거래대금평균대비비율': self._거래대금평균대비비율,
            '체결강도평균대비비율': self._체결강도평균대비비율,
            '구간호가총잔량비율': self._구간호가총잔량비율,
            '매수수량변동성': self._매수수량변동성,
            '매도수량변동성': self._매도수량변동성,
            '횡보감지': self._횡보감지,
            '고가미갱신지속틱수': self._고가미갱신지속틱수,
            '저가미갱신지속틱수': self._저가미갱신지속틱수,
            '고점기준등락율각도': self._고점기준등락율각도,
            '저점기준등락율각도': self._저점기준등락율각도,
            '연속상승': self._연속상승,
            '연속하락': self._연속하락,
            '호가갭발생': self._호가갭발생,
            '변동성급증': self._변동성급증,
            '변동성급감': self._변동성급감,
            '가격급등': self._가격급등,
            '가격급락': self._가격급락,
            '거래대금급증': self._거래대금급증,
            '거래대금급감': self._거래대금급감,
            '체결강도급등': self._체결강도급등,
            '체결강도급락': self._체결강도급락,
            '호가상승압력': self._호가상승압력,
            '호가하락압력': self._호가하락압력,
            '매수수량급증': self._매수수량급증,
            '매수수량급감': self._매수수량급감,
            '매도수량급증': self._매도수량급증,
            '매도수량급감': self._매도수량급감,
            '이평돌파': self._이평돌파,
            '이평이탈': self._이평이탈,
            '시가돌파': self._시가돌파,
            '시가이탈': self._시가이탈,

            '이평지지후이평돌파': self._이평지지후이평돌파,
            '이평지지후이평이탈': self._이평지지후이평이탈,
            '횡보후가격급등': self._횡보후가격급등,
            '횡보후가격급락': self._횡보후가격급락,
            '횡보후연속상승': self._횡보후연속상승,
            '횡보후연속하락': self._횡보후연속하락,
            '연속상승및가격급등': self._연속상승및가격급등,
            '연속하락및가격급락': self._연속하락및가격급락,
            '거래대금급증및연속상승': self._거래대금급증및연속상승,
            '거래대금급감및연속하락': self._거래대금급감및연속하락,
            '호가상승압력및매수수량급증': self._호가상승압력및매수수량급증,
            '호가하락압력및매도수량급증': self._호가하락압력및매도수량급증,
            '매수수량급증및가격급등': self._매수수량급증및가격급등,
            '매도수량급증후가격급락': self._매도수량급증후가격급락,
            '변동성급증및구간최고가갱신': self._변동성급증및구간최고가갱신,
            '변동성급감및구간최저가갱신': self._변동성급감및구간최저가갱신,
            '거래대금급증및구간최고가갱신': self._거래대금급증및구간최고가갱신,
            '거래대금급감후구간최저가갱신': self._거래대금급감후구간최저가갱신,
            '거래대금급증및가격급등': self._거래대금급증및가격급등,
            '거래대금급감및가격급락': self._거래대금급감및가격급락,
            '체결강도급등및호가상승압력': self._체결강도급등및호가상승압력,
            '체결강도급락및호가하락압력': self._체결강도급락및호가하락압력,
            '시가근접황보후시가돌파': self._시가근접황보후시가돌파,
            '시가근접황보후시가이탈': self._시가근접황보후시가이탈,
            '저가갱신후가격급등': self._저가갱신후가격급등,
            '고가갱신후가격급락': self._고가갱신후가격급락,
            '횡보상태장기보유': self._횡보상태장기보유,
            '변동성급증_역추세매도': self._변동성급증_역추세매도,
            '장기보유종목_동적익절청산': self._장기보유종목_동적익절청산,
            '거래대금비율기반_동적청산': self._거래대금비율기반_동적청산,
            '호가압력기반_동적청산': self._호가압력기반_동적청산,
            '이평기반_동적청산': self._이평기반_동적청산,
            '변동성기반_동적청산': self._변동성기반_동적청산,
            '변동성급증기반_동적청산': self._변동성급증기반_동적청산,

            'AD_N': self._AD_N,
            'ADOSC_N': self._ADOSC_N,
            'ADXR_N': self._ADXR_N,
            'APO_N': self._APO_N,
            'AROOND_N': self._AROOND_N,
            'AROONU_N': self._AROONU_N,
            'ATR_N': self._ATR_N,
            'BBU_N': self._BBU_N,
            'BBM_N': self._BBM_N,
            'BBL_N': self._BBL_N,
            'CCI_N': self._CCI_N,
            'DIM_N': self._DIM_N,
            'DIP_N': self._DIP_N,
            'MACD_N': self._MACD_N,
            'MACDS_N': self._MACDS_N,
            'MACDH_N': self._MACDH_N,
            'MFI_N': self._MFI_N,
            'MOM_N': self._MOM_N,
            'OBV_N': self._OBV_N,
            'PPO_N': self._PPO_N,
            'ROC_N': self._ROC_N,
            'RSI_N': self._RSI_N,
            'SAR_N': self._SAR_N,
            'STOCHSK_N': self._STOCHSK_N,
            'STOCHSD_N': self._STOCHSD_N,
            'STOCHFK_N': self._STOCHFK_N,
            'STOCHFD_N': self._STOCHFD_N,
            'WILLR_N': self._WILLR_N
        }
        if self.backtest:
            dict_add_func['now'] = self._now

        if self.fm_list:
            def create_func(col_idx):
                def formula_func(pre=0):
                    if pre <= self.indexn:
                        return self.arry_code[self.indexn - pre, col_idx]
                    return 0
                return formula_func

            for fm in self.fm_list:
                dict_add_func[fm[0]] = create_func(fm[-1])

        func_keys = dict_add_func.keys()
        if self.pre_func_keys != func_keys:
            self.pre_func_keys = func_keys
            self._update_globals_func(dict_add_func)

    def _update_globals_func(self, dict_add_func):
        pass
