import pyqtgraph as pg
from ui.ui_crosshair import CrossHair
from ui.ui_get_label_text import get_label_text
from ui.set_style import qfont12, color_fg_bt, color_bg_bt, color_bg_ld
from utility.chart_items import CandlestickItem, VolumeBarsItem
from utility.setting import list_stock_tick_real, list_coin_tick_real, list_stock_min_real, list_coin_min_real
from utility.static import error_decorator, from_timestamp, strp_time


class DrawRealChart:
    def __init__(self, ui):
        self.ui = ui
        self.crosshair = CrossHair(self.ui)
        self.chart_item_index = 0

    @error_decorator
    def draw_realchart(self, data):
        def fi(fname):
            if is_min:
                return list_stock_min_real.index(fname) if not coin else list_coin_min_real.index(fname)
            else:
                return list_stock_tick_real.index(fname) if not coin else list_coin_tick_real.index(fname)

        def ci():
            self.chart_item_index += 1
            return self.chart_item_index

        self.chart_item_index = 0
        name, self.ui.ctpg_arry = data[1:]
        coin = True if 'KRW' in name or 'USDT' in name else False
        chart_count = len(self.ui.ctpg)
        is_min = chart_count in (6, 10) or (chart_count == 8 and self.ui.ct_pushButtonnn_04.text() == 'CHART 12')

        if not self.ui.dialog_chart.isVisible():
            self.ui.ChartClear()
            if coin:
                if self.ui.CoinStrategyProcessAlive(): self.ui.cstgQ.put(('차트종목코드', None))
                if not self.ui.dict_set['코인타임프레임'] and self.ui.CoinReceiverProcessAlive(): self.ui.creceivQ.put(('차트종목코드', None))
            else:
                self.ui.wdzservQ.put(('strategy', ('차트종목코드', None)))
                if not self.ui.dict_set['주식타임프레임']: self.ui.wdzservQ.put(('receiver', ('차트종목코드', None)))
            return

        if self.ui.ctpg_name != name:
            self.ui.ctpg_item    = {}
            self.ui.ctpg_data    = {}
            self.ui.ctpg_legend  = {}
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
            if not coin:
                if self.ui.ft_checkBoxxxxx_14.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_14.text())
                if self.ui.ft_checkBoxxxxx_15.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_15.text())
                if self.ui.ft_checkBoxxxxx_16.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_16.text())
                if self.ui.ft_checkBoxxxxx_17.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_17.text())
                if self.ui.ft_checkBoxxxxx_18.isChecked(): self.ui.ctpg_factors.append(self.ui.ft_checkBoxxxxx_18.text())
            if is_min:
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

        if not coin:
            if is_min:
                tuple_factor = (
                    fi('등락율'), fi('분당매수수량'), fi('분당매도수량'), fi('고저평균대비등락율'), fi('분당거래대금'),
                    fi('분당거래대금평균'), fi('등락율각도'), fi('당일거래대금각도'), fi('전일비각도'), fi('관심종목'),
                    fi('AD'), fi('ADOSC'), fi('APO'), fi('AROOND'), fi('AROONU'), fi('CCI'), fi('MACD'),
                    fi('MACDS'), fi('MACDH'), fi('MFI'), fi('MOM'), fi('PPO'), fi('ROC'), fi('RSI'),
                    fi('STOCHSK'), fi('STOCHSD'), fi('STOCHFK'), fi('STOCHFD'), fi('WILLR')
                )
            else:
                tuple_factor = (
                    fi('등락율'), fi('초당매수수량'), fi('초당매도수량'), fi('고저평균대비등락율'), fi('초당거래대금'),
                    fi('초당거래대금평균'), fi('등락율각도'), fi('당일거래대금각도'), fi('전일비각도'), fi('관심종목')
                )
        else:
            if is_min:
                tuple_factor = (
                    fi('등락율'), fi('분당매수수량'), fi('분당매도수량'), fi('고저평균대비등락율'), fi('분당거래대금'),
                    fi('분당거래대금평균'), fi('등락율각도'), fi('당일거래대금각도'), fi('관심종목'),
                    fi('AD'), fi('ADOSC'), fi('APO'), fi('AROOND'), fi('AROONU'), fi('CCI'), fi('MACD'),
                    fi('MACDS'), fi('MACDH'), fi('MFI'), fi('MOM'), fi('PPO'), fi('ROC'), fi('RSI'),
                    fi('STOCHSK'), fi('STOCHSD'), fi('STOCHFK'), fi('STOCHFD'), fi('WILLR')
                )
            else:
                tuple_factor = (
                    fi('등락율'), fi('초당매수수량'), fi('초당매도수량'), fi('고저평균대비등락율'), fi('초당거래대금'),
                    fi('초당거래대금평균'), fi('등락율각도'), fi('당일거래대금각도'), fi('관심종목')
                )

        for i in range(len(self.ui.ctpg_arry[0, :])):
            tick_arry = self.ui.ctpg_arry[:, i]
            if i in tuple_factor:
                self.ui.ctpg_data[i] = tick_arry
            else:
                self.ui.ctpg_data[i] = tick_arry[tick_arry != 0]

        self.ui.ctpg_xticks = [strp_time('%Y%m%d%H%M%S', f'{str(int(x))}00' if is_min else str(int(x))).timestamp() for x in self.ui.ctpg_data[0]]
        xmin, xmax = self.ui.ctpg_xticks[0], self.ui.ctpg_xticks[-1]
        hms = from_timestamp(xmax).strftime('%H:%M' if is_min else '%H:%M:%S')

        len_list = []
        tlen = len(self.ui.ctpg_xticks)
        for data in list(self.ui.ctpg_data.values()):
            len_list.append(tlen - len(data))

        if self.ui.ctpg_name != name or self.ui.ctpg_last_xtick != xmax:
            for i, factor in enumerate(self.ui.ctpg_factors):
                self.ui.ctpg[i].clear()
                ymax, ymin = 0, 0
                if factor == '현재가':
                    if is_min:
                        ymax = self.ui.ctpg_data[fi('분봉고가')].max()
                        ymin = self.ui.ctpg_data[fi('분봉저가')].min()
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균005')]:], y=self.ui.ctpg_data[fi('이동평균005')], pen=(180, 180, 180))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균010')]:], y=self.ui.ctpg_data[fi('이동평균010')], pen=(140, 140, 140))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균020')]:], y=self.ui.ctpg_data[fi('이동평균020')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균060')]:], y=self.ui.ctpg_data[fi('이동평균060')], pen=(80, 80, 80))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균120')]:], y=self.ui.ctpg_data[fi('이동평균120')], pen=(80, 80, 80))
                        self.ui.ctpg[i].addItem(CandlestickItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi('분봉고가'), fi('분봉저가')], self.ui.ctpg_xticks, gubun=1))
                        self.ui.ctpg_last_candlestick = CandlestickItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi('분봉고가'), fi('분봉저가')], self.ui.ctpg_xticks, gubun=2)
                        self.ui.ctpg[i].addItem(self.ui.ctpg_last_candlestick)
                    else:
                        ymax = self.ui.ctpg_data[fi('현재가')].max()
                        ymin = self.ui.ctpg_data[fi('현재가')].min()
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균0060')]:], y=self.ui.ctpg_data[fi('이동평균0060')], pen=(180, 180, 180))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균0300')]:], y=self.ui.ctpg_data[fi('이동평균0300')], pen=(140, 140, 140))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균0600')]:], y=self.ui.ctpg_data[fi('이동평균0600')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균1200')]:], y=self.ui.ctpg_data[fi('이동평균1200')], pen=(60, 60, 60))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('현재가')]:], y=self.ui.ctpg_data[fi('현재가')], pen=(200, 100, 100))
                    self.ui.ctpg_cline = pg.InfiniteLine(angle=0)
                    self.ui.ctpg_cline.setPen(pg.mkPen(color_fg_bt))
                    self.ui.ctpg_cline.setPos(self.ui.ctpg_data[fi('현재가')][-1])
                    self.ui.ctpg[i].addItem(self.ui.ctpg_cline)
                elif factor in ('초당거래대금', '분당거래대금'):
                    ymax = self.ui.ctpg_data[fi(factor)].max()
                    ymin = self.ui.ctpg_data[fi(f'{factor}평균')].min()
                    if is_min:
                        self.ui.ctpg[i].addItem(VolumeBarsItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi(factor)], self.ui.ctpg_xticks, gubun=1))
                        self.ui.ctpg_last_volumebar = VolumeBarsItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi(factor)], self.ui.ctpg_xticks, gubun=2)
                        self.ui.ctpg[i].addItem(self.ui.ctpg_last_volumebar)
                    else:
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi(factor)]:], y=self.ui.ctpg_data[fi(factor)], pen=(200, 100, 100))
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi(f'{factor}평균')]:], y=self.ui.ctpg_data[fi(f'{factor}평균')], pen=(100, 200, 100))
                elif factor == '체결강도':
                    ymax = max(self.ui.ctpg_data[fi('체결강도')].max(), self.ui.ctpg_data[fi('최고체결강도')].max())
                    ymin = min(self.ui.ctpg_data[fi('체결강도')].min(), self.ui.ctpg_data[fi('최저체결강도')].min())
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('체결강도평균')]:], y=self.ui.ctpg_data[fi('체결강도평균')], pen=(200, 200, 200))
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('최저체결강도')]:], y=self.ui.ctpg_data[fi('최저체결강도')], pen=(100, 100, 200))
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('최고체결강도')]:], y=self.ui.ctpg_data[fi('최고체결강도')], pen=(200, 100, 50))
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('체결강도')]:], y=self.ui.ctpg_data[fi('체결강도')], pen=(100, 200, 100))
                elif factor in ('초당체결수량', '분당체결수량'):
                    if is_min:
                        ymax = max(self.ui.ctpg_data[fi('분당매수수량')].max(), self.ui.ctpg_data[fi('분당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('분당매수수량')].min(), self.ui.ctpg_data[fi('분당매도수량')].min())
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('분당매도수량')]:], y=self.ui.ctpg_data[fi('분당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('분당매수수량')]:], y=self.ui.ctpg_data[fi('분당매수수량')], pen=(200, 100, 100))
                    else:
                        ymax = max(self.ui.ctpg_data[fi('초당매수수량')].max(), self.ui.ctpg_data[fi('초당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('초당매수수량')].min(), self.ui.ctpg_data[fi('초당매도수량')].min())
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('초당매도수량')]:], y=self.ui.ctpg_data[fi('초당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('초당매수수량')]:], y=self.ui.ctpg_data[fi('초당매수수량')], pen=(200, 100, 100))
                elif factor == '호가총잔량':
                    ymax = max(self.ui.ctpg_data[fi('매수총잔량')].max(), self.ui.ctpg_data[fi('매도총잔량')].max())
                    ymin = min(self.ui.ctpg_data[fi('매수총잔량')].min(), self.ui.ctpg_data[fi('매도총잔량')].min())
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매수총잔량')]:], y=self.ui.ctpg_data[fi('매수총잔량')], pen=(200, 100, 100))
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매도총잔량')]:], y=self.ui.ctpg_data[fi('매도총잔량')], pen=(100, 100, 200))
                elif factor == '매도수호가잔량1':
                    ymax = max(self.ui.ctpg_data[fi('매수잔량1')].max(), self.ui.ctpg_data[fi('매도잔량1')].max())
                    ymin = min(self.ui.ctpg_data[fi('매수잔량1')].min(), self.ui.ctpg_data[fi('매도잔량1')].min())
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매수잔량1')]:], y=self.ui.ctpg_data[fi('매수잔량1')], pen=(200, 100, 100))
                    self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매도잔량1')]:], y=self.ui.ctpg_data[fi('매도잔량1')], pen=(100, 100, 200))
                elif factor in ('누적초당매도수수량', '누적분당매도수수량'):
                    if is_min:
                        ymax = max(self.ui.ctpg_data[fi('누적분당매수수량')].max(), self.ui.ctpg_data[fi('누적분당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('누적분당매수수량')].min(), self.ui.ctpg_data[fi('누적분당매도수량')].min())
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적분당매도수량')]:], y=self.ui.ctpg_data[fi('누적분당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적분당매수수량')]:], y=self.ui.ctpg_data[fi('누적분당매수수량')], pen=(200, 100, 100))
                    else:
                        ymax = max(self.ui.ctpg_data[fi('누적초당매수수량')].max(), self.ui.ctpg_data[fi('누적초당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('누적초당매수수량')].min(), self.ui.ctpg_data[fi('누적초당매도수량')].min())
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적초당매도수량')]:], y=self.ui.ctpg_data[fi('누적초당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적초당매수수량')]:], y=self.ui.ctpg_data[fi('누적초당매수수량')], pen=(200, 100, 100))
                elif factor == 'AROON':
                    if len(self.ui.ctpg_data[fi('AROONU')]) > 0:
                        ymax = self.ui.ctpg_data[fi('AROONU')].max()
                        ymin = self.ui.ctpg_data[fi('AROOND')].min()
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('AROOND')]:], y=self.ui.ctpg_data[fi('AROOND')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('AROONU')]:], y=self.ui.ctpg_data[fi('AROONU')], pen=(100, 200, 100))
                elif factor == 'BBAND':
                    if len(self.ui.ctpg_data[fi('BBU')]) > 0:
                        ymax = max(self.ui.ctpg_data[fi('BBU')].max(), self.ui.ctpg_data[fi('현재가')].max())
                        ymin = min(self.ui.ctpg_data[fi('BBL')].min(), self.ui.ctpg_data[fi('현재가')].min())
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('BBM')]:], y=self.ui.ctpg_data[fi('BBM')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('BBL')]:], y=self.ui.ctpg_data[fi('BBL')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('BBU')]:], y=self.ui.ctpg_data[fi('BBU')], pen=(100, 200, 100))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('현재가')]:], y=self.ui.ctpg_data[fi('현재가')], pen=(200, 100, 100))
                elif factor == 'DMI':
                    if len(self.ui.ctpg_data[fi('DIP')]) > 0:
                        ymax = self.ui.ctpg_data[fi('DIP')].max()
                        ymin = self.ui.ctpg_data[fi('DIM')].min()
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('DIM')]:], y=self.ui.ctpg_data[fi('DIM')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('DIP')]:], y=self.ui.ctpg_data[fi('DIP')], pen=(100, 200, 100))
                elif factor == 'MACD':
                    if len(self.ui.ctpg_data[fi('MACD')]) > 0:
                        ymax = max(self.ui.ctpg_data[fi('MACD')].max(), self.ui.ctpg_data[fi('MACDS')].max(), self.ui.ctpg_data[fi('MACDH')].max())
                        ymin = min(self.ui.ctpg_data[fi('MACD')].min(), self.ui.ctpg_data[fi('MACDS')].min(), self.ui.ctpg_data[fi('MACDH')].min())
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('MACD')]:], y=self.ui.ctpg_data[fi('MACD')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('MACDH')]:], y=self.ui.ctpg_data[fi('MACDH')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('MACDS')]:], y=self.ui.ctpg_data[fi('MACDS')], pen=(100, 200, 100))
                elif factor == 'STOCHS':
                    if len(self.ui.ctpg_data[fi('STOCHSD')]) > 0:
                        ymax = self.ui.ctpg_data[fi('STOCHSD')].max()
                        ymin = self.ui.ctpg_data[fi('STOCHSK')].min()
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHSD')]:], y=self.ui.ctpg_data[fi('STOCHSD')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHSK')]:], y=self.ui.ctpg_data[fi('STOCHSK')], pen=(100, 200, 100))
                elif factor == 'STOCHF':
                    if len(self.ui.ctpg_data[fi('STOCHFD')]) > 0:
                        ymax = self.ui.ctpg_data[fi('STOCHFD')].max()
                        ymin = self.ui.ctpg_data[fi('STOCHFK')].min()
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHFD')]:], y=self.ui.ctpg_data[fi('STOCHFD')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHFK')]:], y=self.ui.ctpg_data[fi('STOCHFK')], pen=(100, 200, 100))
                else:
                    if len(self.ui.ctpg_data[fi(factor)]) > 0:
                        pen = (100, 200, 100)
                        if is_min:
                            if coin and fi(factor) > 57:
                                pen = (100, 200, 200)
                            elif not coin and fi(factor) > 67:
                                pen = (100, 200, 200)
                        ymax = self.ui.ctpg_data[fi(factor)].max()
                        ymin = self.ui.ctpg_data[fi(factor)].min()
                        self.ui.ctpg_item[ci()] = self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi(factor)]:], y=self.ui.ctpg_data[fi(factor)], pen=pen)

                if self.ui.ct_checkBoxxxxx_02.isChecked():
                    legend = pg.TextItem(anchor=(0, 0), color=color_fg_bt, border=color_bg_bt, fill=color_bg_ld)
                    legend.setText(get_label_text(True, coin, name, is_min, self.ui.ctpg_arry, -1, self.ui.ctpg_factors[i], hms))
                    legend.setFont(qfont12)
                    legend.setPos(xmax, ymax)
                    self.ui.ctpg[i].addItem(legend)
                    self.ui.ctpg_legend[i] = legend

                if is_min:
                    if i == 1:
                        self.ui.ctpg[i].setXLink(self.ui.ctpg[0])
                    elif i > 1:
                        self.ui.ctpg[i].setXLink(self.ui.ctpg[2])
                elif i != 0:
                    self.ui.ctpg[i].setXLink(self.ui.ctpg[0])

                self.ui.ctpg_cvb[i].set_range(xmin, xmax, ymin, ymax)
                self.ui.ctpg[i].setRange(xRange=(xmin, xmax), yRange=(ymin, ymax))
                if self.ui.ct_checkBoxxxxx_02.isChecked():
                    self.ui.ctpg_legend[i].setPos(self.ui.ctpg_cvb[i].state['viewRange'][0][0], self.ui.ctpg_cvb[i].state['viewRange'][1][1])

                if i == chart_count - 1: break

            if self.ui.ct_checkBoxxxxx_01.isChecked():
                if chart_count == 6:
                    self.crosshair.crosshair(
                        True, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                        self.ui.ctpg[4], self.ui.ctpg[5]
                    )
                elif chart_count == 8:
                    self.crosshair.crosshair(
                        True, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                        self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7]
                    )
                elif chart_count == 10:
                    self.crosshair.crosshair(
                        True, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                        self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8],
                        self.ui.ctpg[9]
                    )
                elif chart_count == 12:
                    self.crosshair.crosshair(
                        True, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                        self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8],
                        self.ui.ctpg[9], self.ui.ctpg[10], self.ui.ctpg[11]
                    )
                elif chart_count == 16:
                    self.crosshair.crosshair(
                        True, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                        self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8],
                        self.ui.ctpg[9], self.ui.ctpg[10], self.ui.ctpg[11], self.ui.ctpg[12], self.ui.ctpg[13],
                        self.ui.ctpg[14], self.ui.ctpg[15]
                    )

            self.ui.ctpg_name, self.ui.ctpg_last_xtick = name, xmax
        else:
            for i, factor in enumerate(self.ui.ctpg_factors):
                ymax, ymin = 0, 0
                if factor == '현재가':
                    if is_min:
                        ymax = self.ui.ctpg_data[fi('분봉고가')].max()
                        ymin = self.ui.ctpg_data[fi('분봉저가')].min()
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균005')]:], y=self.ui.ctpg_data[fi('이동평균005')], pen=(180, 180, 180))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균010')]:], y=self.ui.ctpg_data[fi('이동평균010')], pen=(140, 140, 140))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균020')]:], y=self.ui.ctpg_data[fi('이동평균020')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균060')]:], y=self.ui.ctpg_data[fi('이동평균060')], pen=(80, 80, 80))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균120')]:], y=self.ui.ctpg_data[fi('이동평균120')], pen=(80, 80, 80))
                        self.ui.ctpg[i].removeItem(self.ui.ctpg_last_candlestick)
                        self.ui.ctpg_last_candlestick = CandlestickItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi('분봉고가'), fi('분봉저가')], self.ui.ctpg_xticks, gubun=2)
                        self.ui.ctpg[i].addItem(self.ui.ctpg_last_candlestick)
                    else:
                        ymax = self.ui.ctpg_data[fi('현재가')].max()
                        ymin = self.ui.ctpg_data[fi('현재가')].min()
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균0060')]:], y=self.ui.ctpg_data[fi('이동평균0060')], pen=(180, 180, 180))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균0300')]:], y=self.ui.ctpg_data[fi('이동평균0300')], pen=(140, 140, 140))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균0600')]:], y=self.ui.ctpg_data[fi('이동평균0600')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('이동평균1200')]:], y=self.ui.ctpg_data[fi('이동평균1200')], pen=(60, 60, 60))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('현재가')]:], y=self.ui.ctpg_data[fi('현재가')], pen=(200, 100, 100))
                    self.ui.ctpg_cline.setPos(self.ui.ctpg_data[fi('현재가')][-1])
                elif factor in ('초당거래대금', '분당거래대금'):
                    ymax = self.ui.ctpg_data[fi(factor)].max()
                    ymin = self.ui.ctpg_data[fi(f'{factor}평균')].min()
                    if is_min:
                        self.ui.ctpg[i].removeItem(self.ui.ctpg_last_volumebar)
                        self.ui.ctpg_last_volumebar = VolumeBarsItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi(factor)], self.ui.ctpg_xticks, gubun=2)
                        self.ui.ctpg[i].addItem(self.ui.ctpg_last_volumebar)
                    else:
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi(factor)]:], y=self.ui.ctpg_data[fi(factor)], pen=(200, 100, 100))
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi(f'{factor}평균')]:], y=self.ui.ctpg_data[fi(f'{factor}평균')], pen=(100, 200, 100))
                elif factor == '체결강도':
                    ymax = max(self.ui.ctpg_data[fi('체결강도')].max(), self.ui.ctpg_data[fi('최고체결강도')].max())
                    ymin = min(self.ui.ctpg_data[fi('체결강도')].min(), self.ui.ctpg_data[fi('최저체결강도')].min())
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('체결강도평균')]:], y=self.ui.ctpg_data[fi('체결강도평균')], pen=(200, 200, 200))
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('최저체결강도')]:], y=self.ui.ctpg_data[fi('최저체결강도')], pen=(100, 100, 200))
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('최고체결강도')]:], y=self.ui.ctpg_data[fi('최고체결강도')], pen=(200, 100, 100))
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('체결강도')]:], y=self.ui.ctpg_data[fi('체결강도')], pen=(100, 200, 100))
                elif factor in ('초당체결수량', '분당체결수량'):
                    if is_min:
                        ymax = max(self.ui.ctpg_data[fi('분당매수수량')].max(), self.ui.ctpg_data[fi('분당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('분당매수수량')].min(), self.ui.ctpg_data[fi('분당매도수량')].min())
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('분당매도수량')]:], y=self.ui.ctpg_data[fi('분당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('분당매수수량')]:], y=self.ui.ctpg_data[fi('분당매수수량')], pen=(200, 100, 100))
                    else:
                        ymax = max(self.ui.ctpg_data[fi('초당매수수량')].max(), self.ui.ctpg_data[fi('초당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('초당매수수량')].min(), self.ui.ctpg_data[fi('초당매도수량')].min())
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('초당매도수량')]:], y=self.ui.ctpg_data[fi('초당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('초당매수수량')]:], y=self.ui.ctpg_data[fi('초당매수수량')], pen=(200, 100, 100))
                elif factor == '호가총잔량':
                    ymax = max(self.ui.ctpg_data[fi('매수총잔량')].max(), self.ui.ctpg_data[fi('매도총잔량')].max())
                    ymin = min(self.ui.ctpg_data[fi('매수총잔량')].min(), self.ui.ctpg_data[fi('매도총잔량')].min())
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('매수총잔량')]:], y=self.ui.ctpg_data[fi('매수총잔량')], pen=(200, 100, 100))
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('매도총잔량')]:], y=self.ui.ctpg_data[fi('매도총잔량')], pen=(100, 100, 200))
                elif factor == '매도수호가잔량1':
                    ymax = max(self.ui.ctpg_data[fi('매수잔량1')].max(), self.ui.ctpg_data[fi('매도잔량1')].max())
                    ymin = min(self.ui.ctpg_data[fi('매수잔량1')].min(), self.ui.ctpg_data[fi('매도잔량1')].min())
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('매수잔량1')]:], y=self.ui.ctpg_data[fi('매수잔량1')], pen=(200, 100, 100))
                    self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('매도잔량1')]:], y=self.ui.ctpg_data[fi('매도잔량1')], pen=(100, 100, 200))
                elif factor in ('누적초당매도수수량', '누적분당매도수수량'):
                    if is_min:
                        ymax = max(self.ui.ctpg_data[fi('누적분당매수수량')].max(), self.ui.ctpg_data[fi('누적분당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('누적분당매수수량')].min(), self.ui.ctpg_data[fi('누적분당매도수량')].min())
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('누적분당매도수량')]:], y=self.ui.ctpg_data[fi('누적분당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('누적분당매수수량')]:], y=self.ui.ctpg_data[fi('누적분당매수수량')], pen=(200, 100, 100))
                    else:
                        ymax = max(self.ui.ctpg_data[fi('누적초당매수수량')].max(), self.ui.ctpg_data[fi('누적초당매도수량')].max())
                        ymin = min(self.ui.ctpg_data[fi('누적초당매수수량')].min(), self.ui.ctpg_data[fi('누적초당매도수량')].min())
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('누적초당매도수량')]:], y=self.ui.ctpg_data[fi('누적초당매도수량')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('누적초당매수수량')]:], y=self.ui.ctpg_data[fi('누적초당매수수량')], pen=(200, 100, 100))
                elif factor == 'AROON':
                    if len(self.ui.ctpg_data[fi('AROONU')]) > 0:
                        ymax = self.ui.ctpg_data[fi('AROONU')].max()
                        ymin = self.ui.ctpg_data[fi('AROOND')].min()
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('AROOND')]:], y=self.ui.ctpg_data[fi('AROOND')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('AROONU')]:], y=self.ui.ctpg_data[fi('AROONU')], pen=(100, 200, 100))
                elif factor == 'BBAND':
                    if len(self.ui.ctpg_data[fi('BBU')]) > 0:
                        ymax = max(self.ui.ctpg_data[fi('BBU')].max(), self.ui.ctpg_data[fi('현재가')].max())
                        ymin = min(self.ui.ctpg_data[fi('BBL')].min(), self.ui.ctpg_data[fi('현재가')].min())
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('BBM')]:], y=self.ui.ctpg_data[fi('BBM')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('BBL')]:], y=self.ui.ctpg_data[fi('BBL')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('BBU')]:], y=self.ui.ctpg_data[fi('BBU')], pen=(100, 200, 100))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('현재가')]:], y=self.ui.ctpg_data[fi('현재가')], pen=(200, 100, 100))
                elif factor == 'DMI':
                    if len(self.ui.ctpg_data[fi('DIP')]) > 0:
                        ymax = self.ui.ctpg_data[fi('DIP')].max()
                        ymin = self.ui.ctpg_data[fi('DIM')].min()
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('DIM')]:], y=self.ui.ctpg_data[fi('DIM')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('DIP')]:], y=self.ui.ctpg_data[fi('DIP')], pen=(100, 200, 100))
                elif factor == 'MACD':
                    if len(self.ui.ctpg_data[fi('MACD')]) > 0:
                        ymax = max(self.ui.ctpg_data[fi('MACD')].max(), self.ui.ctpg_data[fi('MACDS')].max(), self.ui.ctpg_data[fi('MACDH')].max())
                        ymin = min(self.ui.ctpg_data[fi('MACD')].min(), self.ui.ctpg_data[fi('MACDS')].min(), self.ui.ctpg_data[fi('MACDH')].min())
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('MACD')]:], y=self.ui.ctpg_data[fi('MACD')], pen=(100, 100, 100))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('MACDH')]:], y=self.ui.ctpg_data[fi('MACDH')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('MACDS')]:], y=self.ui.ctpg_data[fi('MACDS')], pen=(100, 200, 100))
                elif factor == 'STOCHS':
                    if len(self.ui.ctpg_data[fi('STOCHSD')]) > 0:
                        ymax = self.ui.ctpg_data[fi('STOCHSD')].max()
                        ymin = self.ui.ctpg_data[fi('STOCHSK')].min()
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('STOCHSD')]:], y=self.ui.ctpg_data[fi('STOCHSD')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('STOCHSK')]:], y=self.ui.ctpg_data[fi('STOCHSK')], pen=(100, 200, 100))
                elif factor == 'STOCHF':
                    if len(self.ui.ctpg_data[fi('STOCHFD')]) > 0:
                        ymax = self.ui.ctpg_data[fi('STOCHFD')].max()
                        ymin = self.ui.ctpg_data[fi('STOCHFK')].min()
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('STOCHFD')]:], y=self.ui.ctpg_data[fi('STOCHFD')], pen=(100, 100, 200))
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi('STOCHFK')]:], y=self.ui.ctpg_data[fi('STOCHFK')], pen=(100, 200, 100))
                else:
                    if len(self.ui.ctpg_data[fi(factor)]) > 0:
                        ymax = self.ui.ctpg_data[fi(factor)].max()
                        ymin = self.ui.ctpg_data[fi(factor)].min()
                        self.ui.ctpg_item[ci()].setData(x=self.ui.ctpg_xticks[len_list[fi(factor)]:], y=self.ui.ctpg_data[fi(factor)])

                self.ui.ctpg_cvb[i].set_range(xmin, xmax, ymin, ymax)
                self.ui.ctpg[i].setRange(xRange=(xmin, xmax), yRange=(ymin, ymax))

                if self.ui.ct_checkBoxxxxx_01.isChecked():
                    self.ui.ctpg_labels[i].setPos(self.ui.ctpg_cvb[i].state['viewRange'][0][0], self.ui.ctpg_cvb[i].state['viewRange'][1][0])
                if self.ui.ct_checkBoxxxxx_02.isChecked():
                    self.ui.ctpg_legend[i].setPos(self.ui.ctpg_cvb[i].state['viewRange'][0][0], self.ui.ctpg_cvb[i].state['viewRange'][1][1])
                    self.ui.ctpg_legend[i].setText(get_label_text(True, coin, name, is_min, self.ui.ctpg_arry, -1, self.ui.ctpg_factors[i], hms))

                if i == chart_count - 1: break

        if self.ui.database_chart: self.ui.database_chart = False
