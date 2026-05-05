
import pyqtgraph as pg
from PyQt5.QtGui import QColor
from ui.draw_chart.draw_crosshair import CrossHair
from utility.static_method.static import from_timestamp
from ui.draw_chart.draw_label_text import get_label_text
from ui.draw_chart.draw_chart_items import CandlestickItem, VolumeBarItem, AreaItem
from ui.create_widget.set_style import qfont12, color_fg_bt, color_bg_bt, color_bg_ld


class DrawChartBase:
    """차트 그리기 기본 클래스입니다.
    PyQtGraph를 사용하여 차트를 그리는 기본 기능을 제공합니다.
    """

    def __init__(self, ui):
        """차트 그리기 기본 클래스를 초기화합니다.
        Args:
            ui: UI 객체
        """
        self.ui         = ui

        self.last       = 0
        self.xmin       = 0
        self.xmax       = 0
        self.ymin       = 0
        self.ymax       = 0
        self.chart_cnt  = 0

        self.code       = None
        self.hms        = None
        self.len_list   = None
        self.dict_idxs  = None
        self.gsjm_arry  = None
        self.last_index = None
        self.drop_zero_factors = None

        self.is_min     = not self.ui.dict_set['타임프레임']
        self.real       = False
        self.same_code  = False
        self.same_time  = False

        self.crosshair  = CrossHair(self.ui)
        self.cached_min_max = {}

        self.rgb_red    = (200, 100, 100)
        self.rgb_blue   = (100, 100, 200)
        self.rgb_green  = (100, 200, 100)
        self.rgb_cyan   = (100, 200, 200)
        self.rgb_gray   = (100, 100, 100)
        self.rgb_dgray  = (200, 200, 200)
        self.sma_colors = [
            (180, 180, 180),
            (140, 140, 140),
            (100, 100, 100),
            (80, 80, 80),
            (60, 60, 60)
        ]

    def fi(self, fname):
        """요소 인덱스를 반환합니다.
        Args:
            fname: 요소 이름
        Returns:
            요소 인덱스
        """
        return self.ui.dict_findex[fname]

    def draw_all_chart(self):
        """모든 차트를 그립니다."""
        if not self.real:
            self.dict_idxs = None
            self.drop_zero_factors = None

        self.chart_cnt = len(self.ui.ctpg)
        self.is_min = not self.ui.dict_set['타임프레임']
        self.gsjm_arry = self.ui.ctpg_arry[:, self.fi('관심종목')]
        self.xmin, self.xmax = self.ui.ctpg_xticks[0], self.ui.ctpg_xticks[-1]
        self.hms = from_timestamp(self.xmax).strftime('%H:%M' if self.is_min else '%H:%M:%S')

        self.update_factor_list()
        self.update_dict_idxs()
        self.update_ctpg_date()

        for i, factor in enumerate(self.ui.ctpg_factors):
            if not (self.same_code and self.same_time):
                self.ui.ctpg[i].clear()

            if factor == '현재가':
                if self.is_min:
                    fidx1, fidx2, fidx3, fidx4 = self.dict_idxs[factor]
                    self.get_optimized_min_max((fidx3, fidx4))
                    self.draw_area(i)
                    for idx, color in zip(self.dict_idxs['이동평균'], self.sma_colors):
                        self.draw_line(i, idx, color)
                    self.draw_formula(i, factor)
                    self.draw_candlestick(i, fidx1, fidx2, fidx3, fidx4)
                    if self.real: self.draw_infinite_line(i, fidx1)
                else:
                    fidx1 = self.fi('현재가')
                    self.get_optimized_min_max(fidx1)
                    self.draw_area(i)
                    for idx, color in zip(self.dict_idxs['이동평균'], self.sma_colors):
                        self.draw_line(i, idx, color)
                    self.draw_formula(i, factor)
                    self.draw_line(i, fidx1, self.rgb_red)
                    if self.real: self.draw_infinite_line(i, fidx1)

                if not self.real:
                    self.draw_buy_or_sell_point(i)

            elif factor in ('초당거래대금', '분당거래대금'):
                try:
                    fidx1, fidx2 = self.dict_idxs[factor]
                    self.get_optimized_min_max((fidx1, fidx2))
                    self.draw_area(i)
                    self.draw_formula(i, factor)
                    if self.is_min:
                        fidx3, fidx4 = self.dict_idxs['양음봉구분']
                        self.draw_volumebar(i, fidx1, fidx3, fidx4)
                    else:
                        self.draw_line(i, fidx1, self.rgb_red)
                    self.draw_line(i, fidx2, self.rgb_green)
                except Exception:
                    self.ymax, self.ymin = 0, 0

            elif factor in ('초당체결수량', '분당체결수량', '누적초당매도수수량', '누적분당매도수수량', '초당매도수금액', '분당매도수금액',
                            '당일매도수금액', '최고매도수금액', '최고매도수가격', '호가총잔량', '매도수호가잔량1'):
                try:
                    fidx1, fidx2 = self.dict_idxs[factor]
                    self.get_optimized_min_max((fidx1, fidx2))
                    self.draw_area(i)
                    self.draw_formula(i, factor)
                    self.draw_line(i, fidx1, self.rgb_blue)
                    self.draw_line(i, fidx2, self.rgb_red)
                except Exception:
                    self.ymax, self.ymin = 0, 0

            elif factor == '체결강도':
                try:
                    fidx1, fidx2, fidx3, fidx4 = self.dict_idxs[factor]
                    self.get_optimized_min_max((fidx1, fidx2, fidx3))
                    self.draw_area(i)
                    self.draw_formula(i, factor)
                    self.draw_line(i, fidx4, self.rgb_dgray)
                    self.draw_line(i, fidx3, self.rgb_red)
                    self.draw_line(i, fidx2, self.rgb_blue)
                    self.draw_line(i, fidx1, self.rgb_green)
                except Exception:
                    self.ymax, self.ymin = 0, 0

            elif factor in ('AROON', 'DMI', 'STOCHS', 'STOCHF'):
                try:
                    fidx1, fidx2 = self.dict_idxs[factor]
                    color1 = self.rgb_blue if factor in ('AROON', 'DMI') else self.rgb_red
                    color2 = self.rgb_red if factor in ('AROON', 'DMI') else self.rgb_green
                    self.get_optimized_min_max((fidx1, fidx2))
                    self.draw_area(i)
                    self.draw_formula(i, factor)
                    self.draw_line(i, fidx2, color1)
                    self.draw_line(i, fidx1, color2)
                except Exception:
                    self.ymax, self.ymin = 0, 0

            elif factor == 'BBAND':
                try:
                    fidx1, fidx2, fidx3, fidx4 = self.dict_idxs[factor]
                    self.get_optimized_min_max((fidx1, fidx2, fidx3))
                    self.draw_area(i)
                    self.draw_formula(i, factor)
                    self.draw_line(i, fidx4, self.rgb_gray)
                    self.draw_line(i, fidx3, self.rgb_blue)
                    self.draw_line(i, fidx2, self.rgb_green)
                    self.draw_line(i, fidx1, self.rgb_red)
                except Exception:
                    self.ymax, self.ymin = 0, 0

            elif factor == 'MACD':
                try:
                    fidx1, fidx2, fidx3 = self.dict_idxs[factor]
                    self.get_optimized_min_max((fidx1, fidx2, fidx3))
                    self.draw_area(i)
                    self.draw_formula(i, factor)
                    self.draw_line(i, fidx3, self.rgb_gray)
                    self.draw_line(i, fidx2, self.rgb_red)
                    self.draw_line(i, fidx1, self.rgb_green)
                except Exception:
                    self.ymax, self.ymin = 0, 0

            else:
                fidx1 = self.fi(factor)
                if len(self.ui.ctpg_data[fidx1]) > 0:
                    color = self.rgb_cyan if self.is_min and fidx1 > self.fi('AD') else self.rgb_green
                    self.get_optimized_min_max(fidx1)
                    self.draw_area(i)
                    self.draw_formula(i, factor)
                    self.draw_line(i, fidx1, color)
                else:
                    self.ymax, self.ymin = 0, 0

            self.draw_legend(i)
            if i == self.chart_cnt - 1: break

        if self.ui.ct_checkBoxxxxx_01.isChecked():
            self.insert_crosshair()

        self.ui.ctpg_code = self.code
        if self.real and self.ui.database_chart: self.ui.database_chart = False
        if not self.real and not self.ui.database_chart: self.ui.database_chart = True

    def update_factor_list(self):
        """요소 리스트를 업데이트합니다."""
        if not (self.same_code and self.same_time):
            self.ui.ctpg_item   = {}
            self.ui.ctpg_data   = {}
            self.ui.ctpg_legend = {}

        self.ui.ctpg_factors = []
        if self.ui.ft_checkBoxxxxx_01.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_01.text())
        if self.ui.ft_checkBoxxxxx_02.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_02.text())
        if self.ui.ft_checkBoxxxxx_03.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_03.text())
        if self.ui.ft_checkBoxxxxx_04.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_04.text())
        if self.ui.ft_checkBoxxxxx_05.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_05.text())
        if self.ui.ft_checkBoxxxxx_06.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_06.text())
        if self.ui.ft_checkBoxxxxx_07.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_07.text())
        if self.ui.ft_checkBoxxxxx_08.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_08.text())
        if self.ui.ft_checkBoxxxxx_09.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_09.text())
        if self.ui.ft_checkBoxxxxx_10.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_10.text())
        if self.ui.ft_checkBoxxxxx_11.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_11.text())
        if self.ui.ft_checkBoxxxxx_12.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_12.text())
        if self.ui.ft_checkBoxxxxx_13.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_13.text())
        if self.ui.ft_checkBoxxxxx_14.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_14.text())
        if self.ui.ft_checkBoxxxxx_15.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_15.text())
        if self.ui.ft_checkBoxxxxx_16.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_16.text())
        if self.ui.ft_checkBoxxxxx_17.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_17.text())
        if self.ui.ft_checkBoxxxxx_18.isChecked():     self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_18.text())
        if self.is_min:
            if self.ui.ft_checkBoxxxxx_19.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_19.text())
            if self.ui.ft_checkBoxxxxx_20.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_20.text())
            if self.ui.ft_checkBoxxxxx_21.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_21.text())
            if self.ui.ft_checkBoxxxxx_22.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_22.text())
            if self.ui.ft_checkBoxxxxx_23.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_23.text())
            if self.ui.ft_checkBoxxxxx_24.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_24.text())
            if self.ui.ft_checkBoxxxxx_25.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_25.text())
            if self.ui.ft_checkBoxxxxx_26.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_26.text())
            if self.ui.ft_checkBoxxxxx_27.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_27.text())
            if self.ui.ft_checkBoxxxxx_28.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_28.text())
            if self.ui.ft_checkBoxxxxx_29.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_29.text())
            if self.ui.ft_checkBoxxxxx_30.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_30.text())
            if self.ui.ft_checkBoxxxxx_31.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_31.text())
            if self.ui.ft_checkBoxxxxx_32.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_32.text())
            if self.ui.ft_checkBoxxxxx_33.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_33.text())
            if self.ui.ft_checkBoxxxxx_34.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_34.text())
            if self.ui.ft_checkBoxxxxx_35.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_35.text())
            if self.ui.ft_checkBoxxxxx_36.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_36.text())
            if self.ui.ft_checkBoxxxxx_37.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_37.text())
            if self.ui.ft_checkBoxxxxx_38.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_38.text())

    def update_dict_idxs(self):
        """요소 인덱스 딕셔너리를 업데이트합니다."""
        if self.dict_idxs is not None:
            return

        if self.is_min:
            self.dict_idxs = {
                '체결강도': [self.fi('체결강도'), self.fi('최고체결강도'), self.fi('최저체결강도'), self.fi('체결강도평균')],
                '호가총잔량': [self.fi('매도총잔량'), self.fi('매수총잔량')],
                '당일매도수금액': [self.fi('당일매도금액'), self.fi('당일매수금액')],
                '최고매도수금액': [self.fi('최고매도금액'), self.fi('최고매수금액')],
                '최고매도수가격': [self.fi('최고매도가격'), self.fi('최고매수가격')],
                '매도수호가잔량1': [self.fi('매도잔량1'), self.fi('매수잔량1')],

                '이동평균': [self.fi('이동평균5'), self.fi('이동평균10'), self.fi('이동평균20'), self.fi('이동평균60'), self.fi('이동평균120')],
                '분당거래대금': [self.fi('분당거래대금'), self.fi('분당거래대금평균')],
                '분당체결수량': [self.fi('분당매도수량'), self.fi('분당매수수량')],
                '분당매도수금액': [self.fi('분당매도금액'), self.fi('분당매수금액')],
                '누적분당매도수수량': [self.fi('누적분당매도수량'), self.fi('누적분당매수수량')],

                '현재가': [self.fi('현재가'), self.fi('분봉시가'), self.fi('분봉고가'), self.fi('분봉저가')],
                '양음봉구분': [self.fi('현재가'), self.fi('분봉시가')],

                'BBAND': [self.fi('현재가'), self.fi('BBU'), self.fi('BBL'), self.fi('BBM')],
                'MACD': [self.fi('MACDS'), self.fi('MACDH'), self.fi('MACD')],
                'STOCHS': [self.fi('STOCHSK'), self.fi('STOCHSD')],
                'STOCHF': [self.fi('STOCHFK'), self.fi('STOCHFD')],
                'AROON': [self.fi('AROONU'), self.fi('AROOND')],
                'DMI': [self.fi('DIP'), self.fi('DIM')]
            }
        else:
            self.dict_idxs = {
                '체결강도': [self.fi('체결강도'), self.fi('최고체결강도'), self.fi('최저체결강도'), self.fi('체결강도평균')],
                '호가총잔량': [self.fi('매도총잔량'), self.fi('매수총잔량')],
                '당일매도수금액': [self.fi('당일매도금액'), self.fi('당일매수금액')],
                '최고매도수금액': [self.fi('최고매도금액'), self.fi('최고매수금액')],
                '최고매도수가격': [self.fi('최고매도가격'), self.fi('최고매수가격')],
                '매도수호가잔량1': [self.fi('매도잔량1'), self.fi('매수잔량1')],

                '이동평균': [self.fi('이동평균60'), self.fi('이동평균150'), self.fi('이동평균300'), self.fi('이동평균600'), self.fi('이동평균1200')],
                '초당거래대금': [self.fi('초당거래대금'), self.fi('초당거래대금평균')],
                '초당체결수량': [self.fi('초당매도수량'), self.fi('초당매수수량')],
                '초당매도수금액': [self.fi('초당매도금액'), self.fi('초당매수금액')],
                '누적초당매도수수량': [self.fi('누적초당매도수량'), self.fi('누적초당매수수량')]
            }

    def update_ctpg_date(self):
        """차트 데이터를 업데이트합니다."""
        if self.same_code and self.same_time:
            self._incremental_update()
        else:
            self._process_all_data()

        tlen = len(self.ui.ctpg_arry)
        self.last = tlen - 1
        self.len_list = [tlen - len(x) for x in self.ui.ctpg_data.values()]

    def _incremental_update(self):
        """증분 업데이트를 수행합니다."""
        for i, row in enumerate(self.ui.ctpg_arry[-1]):
            if len(self.ui.ctpg_data[i]) > 0:
                self.ui.ctpg_data[i][-1] = row

    def _process_all_data(self):
        """모든 데이터를 처리합니다."""
        if self.drop_zero_factors is None:
            self.drop_zero_factors = self.get_drop_zero_factors()

        for i, col in enumerate(self.ui.ctpg_arry.T):
            if i in self.drop_zero_factors:
                self.ui.ctpg_data[i] = col[col != 0]
            else:
                self.ui.ctpg_data[i] = col

    def get_drop_zero_factors(self):
        """0값 제거 요소 인덱스를 반환합니다.
        Returns:
            0값 제거 요소 인덱스 튜플
        """
        if self.is_min:
            drop_zero_factors = (
                self.fi('이동평균5'), self.fi('이동평균10'), self.fi('이동평균20'), self.fi('이동평균60'), self.fi('이동평균120'),
                self.fi('최고현재가'), self.fi('최저현재가'), self.fi('최고분봉고가'), self.fi('최저분봉저가'), self.fi('체결강도평균'),
                self.fi('최고체결강도'), self.fi('최저체결강도'), self.fi('최고분당매수수량'), self.fi('최고분당매도수량'),
                self.fi('누적분당매수수량'), self.fi('누적분당매도수량'), self.fi('분당거래대금평균'),
                self.fi('ADXR'), self.fi('ATR'), self.fi('BBU'), self.fi('BBM'), self.fi('BBL'), self.fi('DIM'),
                self.fi('DIP'), self.fi('OBV'), self.fi('SAR')
            )
        else:
            drop_zero_factors = (
                self.fi('이동평균60'), self.fi('이동평균150'), self.fi('이동평균300'), self.fi('이동평균600'),
                self.fi('이동평균1200'), self.fi('최고현재가'), self.fi('최저현재가'), self.fi('체결강도평균'),
                self.fi('최고체결강도'), self.fi('최저체결강도'), self.fi('최고초당매수수량'), self.fi('최고초당매도수량'),
                self.fi('누적초당매수수량'), self.fi('누적초당매도수량'), self.fi('초당거래대금평균')
            )
        return drop_zero_factors

    def get_optimized_min_max(self, fidx_list):
        """최적화된 최소/최대값을 계산합니다.
        Args:
            fidx_list: 요소 인덱스 리스트
        """
        fidx_tuple = fidx_list if isinstance(fidx_list, tuple) else (fidx_list,)
        if self.same_code and self.same_time and fidx_tuple in self.cached_min_max:
            self._incremental_min_max_update(fidx_tuple)
        else:
            self._full_min_max_calculation(fidx_tuple)

    def _incremental_min_max_update(self, fidx_tuple):
        """증분 최소/최대값 업데이트를 수행합니다.
        Args:
            fidx_tuple: 요소 인덱스 튜플
        """
        cached_ymax, cached_ymin = self.cached_min_max[fidx_tuple]
        new_values = []
        for fidx in fidx_tuple:
            if fidx in self.ui.ctpg_data and len(self.ui.ctpg_data[fidx]) > 0:
                new_values.append(self.ui.ctpg_data[fidx][-1])

        if new_values:
            new_max = max(new_values)
            new_min = min(new_values)
            self.ymax = max(cached_ymax, new_max)
            self.ymin = min(cached_ymin, new_min)
            self.cached_min_max[fidx_tuple] = (self.ymax, self.ymin)
        else:
            self.ymax, self.ymin = cached_ymax, cached_ymin

    def _full_min_max_calculation(self, fidx_tuple):
        """전체 최소/최대값 계산을 수행합니다.
        Args:
            fidx_tuple: 요소 인덱스 튜플
        """
        all_values = []
        for fidx in fidx_tuple:
            if fidx in self.ui.ctpg_data and len(self.ui.ctpg_data[fidx]) > 0:
                all_values.extend(self.ui.ctpg_data[fidx])

        if all_values:
            self.ymax = max(all_values)
            self.ymin = min(all_values)
            self.cached_min_max[fidx_tuple] = (self.ymax, self.ymin)
        else:
            self.ymax, self.ymin = 0, 0
            self.cached_min_max[fidx_tuple] = (0, 0)

    def draw_buy_or_sell_point(self, i):
        """매수/매도 지점을 그립니다.
        Args:
            i: 차트 인덱스
        """
        buy_arrow_list = [(j, price) for j, price in enumerate(self.ui.ctpg_arry[:, self.fi('매수가')]) if price > 0]
        sell_arrow_list = [(j, price) for j, price in enumerate(self.ui.ctpg_arry[:, self.fi('매도가')]) if price > 0]
        if buy_arrow_list:
            for j, price in buy_arrow_list:
                arrow = pg.ArrowItem(angle=180, tipAngle=60, headLen=10, pen='w', brush='r')
                arrow.setPos(self.ui.ctpg_xticks[j], price)
                self.ui.ctpg[i].addItem(arrow)
        if sell_arrow_list:
            for j, price in sell_arrow_list:
                arrow = pg.ArrowItem(angle=0, tipAngle=60, headLen=10, pen='w', brush='b')
                arrow.setPos(self.ui.ctpg_xticks[j], price)
                self.ui.ctpg[i].addItem(arrow)

        if self.ui.market_gubun > 5:
            buy_arrow_list = [(j, price) for j, price in enumerate(self.ui.ctpg_arry[:, self.fi('매수가2')]) if price > 0]
            sell_arrow_list = [(j, price) for j, price in enumerate(self.ui.ctpg_arry[:, self.fi('매도가2')]) if price > 0]
            if buy_arrow_list:
                for j, price in buy_arrow_list:
                    arrow = pg.ArrowItem(angle=180, tipAngle=60, headLen=10, pen='w', brush='m')
                    arrow.setPos(self.ui.ctpg_xticks[j], price)
                    self.ui.ctpg[i].addItem(arrow)
            if sell_arrow_list:
                for j, price in sell_arrow_list:
                    arrow = pg.ArrowItem(angle=0, tipAngle=60, headLen=10, pen='w', brush='b')
                    arrow.setPos(self.ui.ctpg_xticks[j], price)
                    self.ui.ctpg[i].addItem(arrow)

    def draw_line(self, i, fidx1, color):
        """라인을 그립니다.
        Args:
            i: 차트 인덱스
            fidx1: 요소 인덱스
            color: 색상
        """
        if self.same_code and self.same_time:
            self.ui.ctpg_item[fidx1].setData(x=self.ui.ctpg_xticks[self.len_list[fidx1]:], y=self.ui.ctpg_data[fidx1])
        else:
            line = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[self.len_list[fidx1]:], y=self.ui.ctpg_data[fidx1], pen=color)
            line.setZValue(10)
            self.ui.ctpg_item[fidx1] = line

    def draw_infinite_line(self, i, fidx1):
        """무한 라인을 그립니다.
        Args:
            i: 차트 인덱스
            fidx1: 요소 인덱스
        """
        if self.same_code and self.same_time:
            self.ui.ctpg_cline.setPos(self.ui.ctpg_data[fidx1][-1])
        else:
            self.ui.ctpg_cline = pg.InfiniteLine(angle=0)
            self.ui.ctpg_cline.setPen(pg.mkPen(color_fg_bt))
            self.ui.ctpg_cline.setPos(self.ui.ctpg_data[fidx1][-1])
            self.ui.ctpg_cline.setZValue(25)
            self.ui.ctpg[i].addItem(self.ui.ctpg_cline)

    def draw_area(self, i):
        """영역을 그립니다.
        Args:
            i: 차트 인덱스
        """
        if self.same_code and self.same_time:
            last_area = self.ui.ctpg_item[0]
            self.ui.ctpg[i].removeItem(last_area)
            last_area = AreaItem(self.gsjm_arry, self.ymin, self.ymax, self.ui.ctpg_xticks, gubun=2)
        else:
            self.ui.ctpg[i].addItem(AreaItem(self.gsjm_arry, self.ymin, self.ymax, self.ui.ctpg_xticks, gubun=1))
            last_area = AreaItem(self.gsjm_arry, self.ymin, self.ymax, self.ui.ctpg_xticks, gubun=2)
        self.ui.ctpg_item[0] = last_area
        self.ui.ctpg[i].addItem(last_area)

    def draw_candlestick(self, i, fidx1, fidx2, fidx3, fidx4):
        """캔들스틱을 그립니다.
        Args:
            i: 차트 인덱스
            fidx1: 시가 인덱스
            fidx2: 고가 인덱스
            fidx3: 저가 인덱스
            fidx4: 종가 인덱스
        """
        if self.same_code and self.same_time:
            last_candlestick = self.ui.ctpg_item[fidx1]
            self.ui.ctpg[i].removeItem(last_candlestick)
            last_candlestick = CandlestickItem(self.ui.ctpg_arry, [fidx1, fidx2, fidx3, fidx4], self.ui.ctpg_xticks, gubun=2)
        else:
            self.ui.ctpg[i].addItem(CandlestickItem(self.ui.ctpg_arry, [fidx1, fidx2, fidx3, fidx4], self.ui.ctpg_xticks, gubun=1))
            last_candlestick = CandlestickItem(self.ui.ctpg_arry, [fidx1, fidx2, fidx3, fidx4], self.ui.ctpg_xticks, gubun=2)
        self.ui.ctpg_item[fidx1] = last_candlestick
        self.ui.ctpg[i].addItem(last_candlestick)

    def draw_volumebar(self, i, fidx1, fidx3, fidx4):
        """볼륨바를 그립니다.
        Args:
            i: 차트 인덱스
            fidx1: 거래량 인덱스
            fidx3: 시가 인덱스
            fidx4: 종가 인덱스
        """
        if self.same_code and self.same_time:
            last_volumebar = self.ui.ctpg_item[fidx1]
            self.ui.ctpg[i].removeItem(last_volumebar)
            last_volumebar = VolumeBarItem(self.ui.ctpg_arry, [fidx3, fidx4, fidx1], self.ui.ctpg_xticks, gubun=2)
        else:
            self.ui.ctpg[i].addItem(VolumeBarItem(self.ui.ctpg_arry, [fidx3, fidx4, fidx1], self.ui.ctpg_xticks, gubun=1))
            last_volumebar = VolumeBarItem(self.ui.ctpg_arry, [fidx3, fidx4, fidx1], self.ui.ctpg_xticks, gubun=2)
        self.ui.ctpg_item[fidx1] = last_volumebar
        self.ui.ctpg[i].addItem(last_volumebar)

    def draw_legend(self, i):
        """범례를 그립니다.
        Args:
            i: 차트 인덱스
        """
        if self.same_code and self.same_time:
            if self.ui.ct_checkBoxxxxx_01.isChecked():
                self.ui.ctpg_labels[i].setPos(self.ui.ctpg_cvb[i].state['viewRange'][0][0], self.ui.ctpg_cvb[i].state['viewRange'][1][0])
            self.ui.ctpg_legend[i].setPos(self.ui.ctpg_cvb[i].state['viewRange'][0][0], self.ui.ctpg_cvb[i].state['viewRange'][1][1])
            self.ui.ctpg_legend[i].setText(get_label_text(self.ui, self.is_min, -1, self.ui.ctpg_factors[i], self.hms))
        else:
            if self.real or self.ui.ct_checkBoxxxxx_02.isChecked():
                legend = pg.TextItem(anchor=(0, 0), color=color_fg_bt, border=color_bg_bt, fill=color_bg_ld)
                legend.setText(get_label_text(self.ui, self.is_min, -1, self.ui.ctpg_factors[i], self.hms))
                legend.setFont(qfont12)
                legend.setPos(self.xmax, self.ymax)
                legend.setZValue(30)
                self.ui.ctpg[i].addItem(legend)
                self.ui.ctpg_legend[i] = legend

            self.ui.ctpg_cvb[i].linkX(self.ui.ctpg_cvb[0])
            self.ui.ctpg_cvb[i].set_range(self.xmin, self.xmax, self.ymin, self.ymax)

            if not self.ui.ctpg_cvb[0].is_zoomin():
                self.ui.ctpg[i].setXRange(self.xmin, self.xmax, padding=0.01)
                self.ui.ctpg[i].setYRange(self.ymin, self.ymax, padding=0.03)

            if self.real or self.ui.ct_checkBoxxxxx_02.isChecked():
                self.ui.ctpg_legend[i].setPos(self.ui.ctpg_cvb[i].state['viewRange'][0][0], self.ui.ctpg_cvb[i].state['viewRange'][1][1])

    def draw_formula(self, i, factor):
        """공식을 그립니다.
        Args:
            i: 차트 인덱스
            factor: 요소 이름
        """
        if self.ui.fm_list:
            factor_fm_list = [fm for fm in self.ui.fm_list if fm[3] == factor]
            if factor_fm_list:
                for name, _, _, _, data_type, color, width, style, _, col_idx in factor_fm_list:
                    if data_type in ('선:일반', '선:조건'):
                        self.draw_fm_line(i, col_idx, color, width, style)
                    elif data_type == '화살표:일반':
                        self.draw_fm_arrow(i, col_idx, style, width, color)
                    else:
                        self.draw_fm_area(i, col_idx, color)

    def draw_fm_line(self, i, col_idx, color, width, style):
        """공식 라인을 그립니다.
        Args:
            i: 차트 인덱스
            col_idx: 칼럼 인덱스
            color: 색상
            width: 너비
            style: 스타일
        """
        if self.same_code and self.same_time:
            self.ui.ctpg_item[col_idx].setData(x=self.ui.ctpg_xticks, y=self.ui.ctpg_data[col_idx])
        else:
            line = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks, y=self.ui.ctpg_data[col_idx], pen=pg.mkPen(color, width=width, style=style))
            line.setZValue(15)
            self.ui.ctpg_item[col_idx] = line

    def draw_fm_arrow(self, i, col_idx, style, width, color):
        """공식 화살표를 그립니다.
        Args:
            i: 차트 인덱스
            col_idx: 칼럼 인덱스
            style: 스타일
            width: 너비
            color: 색상
        """
        style_angle = {
            6: 90,
            7: -90,
            8: 180,
            9: 0
        }
        arry = self.ui.ctpg_data[col_idx]
        if self.same_code and self.same_time:
            price = arry[-1]
            arrow = self.ui.ctpg_item[col_idx]
            self.ui.ctpg[i].removeItem(arrow)
            if price > 0:
                arrow = pg.ArrowItem(angle=style_angle[style], tipAngle=60, headLen=width, pen='w', brush=color)
                arrow.setPos(self.ui.ctpg_xticks[-1], price)
            else:
                arrow = pg.TextItem()
            self.ui.ctpg_item[col_idx] = arrow
            self.ui.ctpg[i].addItem(arrow)
        else:
            arrow_data = [(j, price) for j, price in enumerate(arry) if price > 0]
            for j, price in arrow_data:
                if j != self.last:
                    arrow = pg.ArrowItem(angle=style_angle[style], tipAngle=60, headLen=width, pen='w', brush=color)
                    arrow.setPos(self.ui.ctpg_xticks[j], price)
                    self.ui.ctpg[i].addItem(arrow)

            price = arry[-1]
            if price > 0:
                arrow = pg.ArrowItem(angle=style_angle[style], tipAngle=60, headLen=width, pen='w', brush=color)
                arrow.setPos(self.ui.ctpg_xticks[-1], price)
            else:
                arrow = pg.TextItem()
            self.ui.ctpg_item[col_idx] = arrow
            self.ui.ctpg[i].addItem(arrow)

    def draw_fm_area(self, i, col_idx, color):
        """공식 영역을 그립니다.
        Args:
            i: 차트 인덱스
            col_idx: 칼럼 인덱스
            color: 색상
        """
        arry = self.ui.ctpg_data[col_idx]
        if self.same_code and self.same_time:
            fill_item = self.ui.ctpg_item[col_idx]
            self.ui.ctpg[i].removeItem(fill_item)
            if arry[-1]:
                x_data = [self.ui.ctpg_xticks[-2], self.ui.ctpg_xticks[-1]]
                pre_up = self.ui.ctpg_data[col_idx + 1][-2]
                pre_down = self.ui.ctpg_data[col_idx + 2][-2]
                up = self.ui.ctpg_data[col_idx + 1][-1]
                down = self.ui.ctpg_data[col_idx + 2][-1]
                upper_curve = pg.PlotDataItem(x=x_data, y=[pre_up, up])
                lower_curve = pg.PlotDataItem(x=x_data, y=[pre_down, down])
                color_with_alpha = QColor(color)
                color_with_alpha.setAlpha(100)
                fill_item = pg.FillBetweenItem(upper_curve, lower_curve, brush=color_with_alpha)
            else:
                fill_item = pg.TextItem()
            fill_item.setZValue(5)
            self.ui.ctpg_item[col_idx] = fill_item
            self.ui.ctpg[i].addItem(fill_item)
        else:
            segments = []
            segment = []
            last_index = 0
            for j, data in enumerate(arry):
                if j <= self.last - 1:
                    if data > 0:
                        up = self.ui.ctpg_data[col_idx + 1][j]
                        down = self.ui.ctpg_data[col_idx + 2][j]
                        if segment:
                            if j - last_index == 1:
                                segment.append((self.ui.ctpg_xticks[j], up, down))
                                last_index = j
                            else:
                                if len(segment) > 1:
                                    segments.append(segment)
                                segment = [(self.ui.ctpg_xticks[j], up, down)]
                                last_index = j
                        else:
                            segment.append((self.ui.ctpg_xticks[j], up, down))
                            last_index = j

                else:
                    if len(segment) > 1:
                        segments.append(segment)

            if segments:
                for segment in segments:
                    x_data = [point[0] for point in segment]
                    up_data = [point[1] for point in segment]
                    down_data = [point[2] for point in segment]
                    upper_curve = pg.PlotDataItem(x=x_data, y=up_data)
                    lower_curve = pg.PlotDataItem(x=x_data, y=down_data)
                    color_with_alpha = QColor(color)
                    color_with_alpha.setAlpha(100)
                    fill_item = pg.FillBetweenItem(upper_curve, lower_curve, brush=color_with_alpha)
                    fill_item.setZValue(5)
                    self.ui.ctpg[i].addItem(fill_item)

            if arry[-1]:
                x_data = [self.ui.ctpg_xticks[-2], self.ui.ctpg_xticks[-1]]
                pre_up = self.ui.ctpg_data[col_idx + 1][-2]
                pre_down = self.ui.ctpg_data[col_idx + 2][-2]
                up = self.ui.ctpg_data[col_idx + 1][-1]
                down = self.ui.ctpg_data[col_idx + 2][-1]
                upper_curve = pg.PlotDataItem(x=x_data, y=[pre_up, up])
                lower_curve = pg.PlotDataItem(x=x_data, y=[pre_down, down])
                color_with_alpha = QColor(color)
                color_with_alpha.setAlpha(100)
                fill_item = pg.FillBetweenItem(upper_curve, lower_curve, brush=color_with_alpha)
            else:
                fill_item = pg.TextItem()
            fill_item.setZValue(5)
            self.ui.ctpg_item[col_idx] = fill_item
            self.ui.ctpg[i].addItem(fill_item)

    def insert_crosshair(self):
        """십자선을 삽입합니다."""
        if self.chart_cnt == 6:
            self.crosshair.crosshair(
                self.real, self.is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                self.ui.ctpg[4], self.ui.ctpg[5]
            )
        elif self.chart_cnt == 7:
            self.crosshair.crosshair(
                self.real, self.is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6]
            )
        elif self.chart_cnt == 8:
            self.crosshair.crosshair(
                self.real, self.is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7]
            )
        elif self.chart_cnt == 10:
            self.crosshair.crosshair(
                self.real, self.is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8], self.ui.ctpg[9]
            )
        elif self.chart_cnt == 13:
            self.crosshair.crosshair(
                self.real, self.is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8], self.ui.ctpg[9],
                self.ui.ctpg[10], self.ui.ctpg[11], self.ui.ctpg[12]
            )
