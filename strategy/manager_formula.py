
import sqlite3
from strategy.stg_globals_func import StgGlobalsFunc
from utility.static_method.static import dt_ymdhms

dict_fm_count = {
    '선:일반': 1,
    '선:조건': 1,
    '화살표:일반': 1,
    '화살표:매매': 2,
    '범위': 3
}


def get_formula_data(forchart, col_idx):
    import pandas as pd
    from utility.settings.setting_base import DB_STRATEGY
    con = sqlite3.connect(DB_STRATEGY)
    fm_df = pd.read_sql("SELECT * FROM formula", con)
    con.close()

    fm_list = []
    dict_fm = {}
    fm_tcnt = 0

    if forchart:
        fm_list_origine = [list(fm) for fm in fm_df.values if fm[1] == 1]
    else:
        fm_list_origine = [list(fm) for fm in fm_df.values if fm[2] == 1]

    if fm_list_origine:
        [fm_list.append(fm) for fm in fm_list_origine if fm[4] == '선:일반']
        [fm_list.append(fm) for fm in fm_list_origine if fm[4] == '선:조건']
        [fm_list.append(fm) for fm in fm_list_origine if fm[4] == '범위']
        [fm_list.append(fm) for fm in fm_list_origine if fm[4] == '화살표:일반']
        if forchart: [fm_list.append(fm) for fm in fm_list_origine if fm[4] == '화살표:매매']

    """
    수식명, 차트표시, 전략연산, 팩터명, 표시형태, 색상, 굵기, 종류, 수식코드, 인덱스
      0      1       2      3       4     5    6    7      8      9
    """
    if fm_list:
        cnt_list = [dict_fm_count[fm[4]] for fm in fm_list]
        fm_tcnt  = sum(cnt_list)
        if fm_tcnt > 0:
            for i, fm in enumerate(fm_list):
                fm.append(col_idx)
                col_idx += cnt_list[i]

            fname_set = set(fm[3] for fm in fm_list)
            dict_fm   = {fname: [[fm[0], fm[4], fm[9]] for fm in fm_list if fm[3] == fname] for fname in fname_set}

    return fm_list, dict_fm, fm_tcnt


class ManagerFormula(StgGlobalsFunc):
    """포뮬러 매니저 클래스입니다.
    보조지표 데이터를 관리하고 업데이트합니다.
    """
    def __init__(self, fm_list, dict_set, is_tick, dict_findex):
        super().__init__()
        self.fm_list      = fm_list
        self.dict_set     = dict_set
        self.is_tick      = is_tick
        self.dict_findex  = dict_findex

        self.base_cnt     = self.dict_findex['관심종목'] + 1
        self.check        = None
        self.buy          = None
        self.sell         = None
        self.line         = None
        self.up           = None
        self.down         = None
        self.hold         = False

        if self.is_tick:
            self.dict_findex['초당매도수금액'] = self.dict_findex['초당매수금액']
            self.dict_findex['누적초당매도수수량'] = self.dict_findex['누적초당매수수량']
        else:
            self.dict_findex['분당매도수금액'] = self.dict_findex['분당매수금액']
            self.dict_findex['누적분당매도수수량'] = self.dict_findex['누적분당매수수량']

        self.dict_findex['당일매도수금액'] = self.dict_findex['당일매수금액']
        self.dict_findex['최고매도수금액'] = self.dict_findex['최고매수금액']
        self.dict_findex['최고매도수가격'] = self.dict_findex['최고매수가격']
        self.dict_findex['호가총잔량'] = self.dict_findex['매수총잔량']
        self.dict_findex['매도수호가잔량1'] = self.dict_findex['매수잔량1']

        self.set_globals_func()

    def _update_globals_func(self, dict_add_func):
        """전역 함수를 업데이트합니다.
        Args:
            dict_add_func: 추가할 전역 함수 딕셔너리
        """
        globals().update(dict_add_func)

    # noinspection PyUnboundLocalVariable,PyUnusedLocal
    def update_all_data(self, code, arry, market_gubun, w_unit):
        """모든 데이터를 업데이트합니다.
        Args:
            code: 종목 코드
            arry: 데이터 배열
            market_gubun: 마켓 구분
            w_unit: 시간 단위
        """
        self.code        = code
        self.arry_code   = arry
        self.avg_list    = [w_unit]
        self.high_low: dict[str, list] = {}
        self.tick_count  = 0

        for fm in self.fm_list:
            fm[8] = compile(fm[-2], '<string>', 'exec')

        for i, index in enumerate(self.arry_code[:, 0]):
            self.index  = int(index)
            self.indexn = i
            self.tick_count += 1

            if market_gubun < 4:
                if self.is_tick:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                        VI해제시간, VI가격, VI호가단위, \
                        초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                        당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[i, 1:self.base_cnt]
                else:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                        VI해제시간, VI가격, VI호가단위, \
                        분봉시가, 분봉고가, 분봉저가, \
                        분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                        당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[i, 1:self.base_cnt]
                VI해제시간 = dt_ymdhms(str(int(VI해제시간)))
            elif market_gubun == 4:
                if self.is_tick:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                        초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                        당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[i, 1:self.base_cnt]
                else:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                        분봉시가, 분봉고가, 분봉저가, \
                        분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                        당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[i, 1:self.base_cnt]
            else:
                if self.is_tick:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
                        초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                        당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[i, 1:self.base_cnt]
                else:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
                        분봉시가, 분봉고가, 분봉저가, \
                        분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                        당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[i, 1:self.base_cnt]

            시분초 = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
            순매수금액 = 초당매수금액 - 초당매도금액 if self.is_tick else 분당매수금액 - 분당매도금액
            종목명, 종목코드, 데이터길이, 체결시간 = self.name, self.code, self.tick_count, self.index

            high_low = self.high_low.get(self.code)
            if self.is_tick:
                if high_low:
                    if 현재가 >= high_low[0]:
                        high_low[0] = 현재가
                        high_low[1] = i
                    if 현재가 <= high_low[2]:
                        high_low[2] = 현재가
                        high_low[3] = i
                else:
                    self.high_low[self.code] = [현재가, i, 현재가, i]
            else:
                if high_low:
                    if 분봉고가 >= high_low[0]:
                        high_low[0] = 분봉고가
                        high_low[1] = i
                    if 분봉저가 <= high_low[2]:
                        high_low[2] = 분봉저가
                        high_low[3] = i
                else:
                    self.high_low[self.code] = [분봉고가, i, 분봉저가, i]

            for name, _, _, fname, data_type, _, _, style, stg, col_idx in self.fm_list:
                self.check, self.line, self.buy, self.sell, self.up, self.down = None, None, None, None, None, None

                exec(stg)

                if data_type == '선:일반':
                    if self.line is not None:
                        self.arry_code[i, col_idx] = self.line

                elif data_type == '선:조건':
                    if self.check is not None and self.line is not None:
                        if self.check:
                            self.arry_code[i, col_idx] = self.line
                        else:
                            pre_line = self.arry_code[i-1, col_idx]
                            if pre_line > 0:
                                self.arry_code[i, col_idx] = pre_line

                elif data_type == '범위':
                    if self.check is not None and self.up is not None and self.down is not None:
                        self.arry_code[i, col_idx] = 1.0 if self.check else 0.0
                        self.arry_code[i, col_idx + 1] = self.up
                        self.arry_code[i, col_idx + 2] = self.down

                elif data_type == '화살표:일반':
                    if self.check is not None and self.check:
                        if self.is_tick or fname != '현재가':
                            price = self.arry_code[i, self.dict_findex[fname]]
                        else:
                            price = 분봉저가 if style == 6 else 분봉고가
                        self.arry_code[i, col_idx] = price

                elif data_type == '화살표:매매':
                    if self.buy is not None and self.sell is not None:
                        if not self.hold and self.buy:
                            self.arry_code[i, col_idx] = 현재가
                            self.hold = True
                        elif self.hold and self.sell:
                            self.arry_code[i, col_idx + 1] = 현재가
                            self.hold = False
