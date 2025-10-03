import win32api
import win32gui
import pyqtgraph as pg
from PyQt5.QtWidgets import QMessageBox
from ui.ui_crosshair import CrossHair
from ui.ui_get_label_text import get_label_text
from utility.chart_items import ChuseItem, CandlestickItem, VolumeBarsItem
from ui.set_style import qfont12, color_fg_bt, color_bg_bt, color_bg_ld
from stock.login_kiwoom.manuallogin import leftClick, enter_keys, press_keys
from utility.setting import list_stock_tick, list_stock_min, list_coin_min1, list_coin_min2, list_coin_tick1, list_coin_tick2
from utility.static import error_decorator, strf_time, from_timestamp, thread_decorator


class DrawChart:
    def __init__(self, ui):
        self.ui = ui
        self.crosshair = CrossHair(self.ui)

    @error_decorator
    def draw_chart(self, data):
        def fi(fname):
            if is_min:
                if not coin:        return list_stock_min.index(fname)
                elif 'KRW' in code: return list_coin_min1.index(fname)
                else:               return list_coin_min2.index(fname)
            else:
                if not coin:        return list_stock_tick.index(fname)
                elif 'KRW' in code: return list_coin_tick1.index(fname)
                else:               return list_coin_tick2.index(fname)

        self.ui.ChartClear()
        if not self.ui.dialog_chart.isVisible():
            return

        coin, self.ui.ctpg_xticks, self.ui.ctpg_arry, self.ui.buy_index, self.ui.sell_index = data[1:]
        if coin == '차트오류':
            QMessageBox.critical(self.ui.dialog_chart, '오류 알림', '해당 날짜의 데이터가 존재하지 않습니다.\n')
            return

        xmin, xmax = self.ui.ctpg_xticks[0], self.ui.ctpg_xticks[-1]
        code = self.ui.ct_lineEdittttt_04.text()
        date = strf_time('%Y%m%d', from_timestamp(xmin))
        if not coin: self.KiwoomHTSChart(code, date)
        chart_count = len(self.ui.ctpg)
        is_min = chart_count in (6, 10) or (chart_count == 8 and self.ui.ct_pushButtonnn_04.text() == 'CHART 12')
        hms = from_timestamp(xmax).strftime('%H:%M' if is_min else '%H:%M:%S')

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

        len_list = []
        tlen = len(self.ui.ctpg_xticks)
        for data in list(self.ui.ctpg_data.values()):
            len_list.append(tlen - len(data))
        gsjm_arry   = self.ui.ctpg_arry[:, fi('관심종목')]
        chuse_exist = True if len(gsjm_arry[gsjm_arry > 0]) > 0 else False

        for i, factor in enumerate(self.ui.ctpg_factors):
            self.ui.ctpg[i].clear()
            if factor == '현재가':
                if is_min:
                    ymax = self.ui.ctpg_data[fi('분봉고가')].max()
                    ymin = self.ui.ctpg_data[fi('분봉저가')].min()
                    if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균005')]:], y=self.ui.ctpg_data[fi('이동평균005')], pen=(180, 180, 180))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균010')]:], y=self.ui.ctpg_data[fi('이동평균010')], pen=(140, 140, 140))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균020')]:], y=self.ui.ctpg_data[fi('이동평균020')], pen=(100, 100, 100))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균060')]:], y=self.ui.ctpg_data[fi('이동평균060')], pen=(80, 80, 80))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균120')]:], y=self.ui.ctpg_data[fi('이동평균120')], pen=(80, 80, 80))
                    self.ui.ctpg[i].addItem(CandlestickItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi('분봉고가'), fi('분봉저가')], self.ui.ctpg_xticks))
                    for j, price in enumerate(self.ui.ctpg_arry[:, fi('매수가')]):
                        if price > 0:
                            arrow = pg.ArrowItem(angle=-180, tipAngle=60, headLen=10, pen='w', brush='r')
                            arrow.setPos(self.ui.ctpg_xticks[j], price)
                            self.ui.ctpg[i].addItem(arrow)
                    for j, price in enumerate(self.ui.ctpg_arry[:, fi('매도가')]):
                        if price > 0:
                            arrow = pg.ArrowItem(angle=0, tipAngle=60, headLen=10, pen='w', brush='b')
                            arrow.setPos(self.ui.ctpg_xticks[j], price)
                            self.ui.ctpg[i].addItem(arrow)
                    if 'USDT' in code:
                        for j, price in enumerate(self.ui.ctpg_arry[:, fi('매수가2')]):
                            if price > 0:
                                arrow = pg.ArrowItem(angle=-180, tipAngle=60, headLen=10, pen='w', brush='m')
                                arrow.setPos(self.ui.ctpg_xticks[j], price)
                                self.ui.ctpg[i].addItem(arrow)
                        for j, price in enumerate(self.ui.ctpg_arry[:, fi('매도가2')]):
                            if price > 0:
                                arrow = pg.ArrowItem(angle=0, tipAngle=60, headLen=10, pen='w', brush='b')
                                arrow.setPos(self.ui.ctpg_xticks[j], price)
                                self.ui.ctpg[i].addItem(arrow)
                else:
                    ymax = self.ui.ctpg_data[fi('현재가')].max()
                    ymin = self.ui.ctpg_data[fi('현재가')].min()
                    if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균0060')]:], y=self.ui.ctpg_data[fi('이동평균0060')], pen=(180, 180, 180))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균0300')]:], y=self.ui.ctpg_data[fi('이동평균0300')], pen=(140, 140, 140))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균0600')]:], y=self.ui.ctpg_data[fi('이동평균0600')], pen=(100, 100, 100))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('이동평균1200')]:], y=self.ui.ctpg_data[fi('이동평균1200')], pen=(60, 60, 60))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('현재가')]:], y=self.ui.ctpg_data[fi('현재가')], pen=(200, 100, 100))
                    for j, price in enumerate(self.ui.ctpg_arry[:, fi('매수가')]):
                        if price > 0:
                            arrow = pg.ArrowItem(angle=-180, tipAngle=60, headLen=10, pen='w', brush='r')
                            arrow.setPos(self.ui.ctpg_xticks[j], price)
                            self.ui.ctpg[i].addItem(arrow)
                    for j, price in enumerate(self.ui.ctpg_arry[:, fi('매도가')]):
                        if price > 0:
                            arrow = pg.ArrowItem(angle=0, tipAngle=60, headLen=10, pen='w', brush='b')
                            arrow.setPos(self.ui.ctpg_xticks[j], price)
                            self.ui.ctpg[i].addItem(arrow)
                    if 'USDT' in code:
                        for j, price in enumerate(self.ui.ctpg_arry[:, fi('매수가2')]):
                            if price > 0:
                                arrow = pg.ArrowItem(angle=-180, tipAngle=60, headLen=10, pen='w', brush='m')
                                arrow.setPos(self.ui.ctpg_xticks[j], price)
                                self.ui.ctpg[i].addItem(arrow)
                        for j, price in enumerate(self.ui.ctpg_arry[:, fi('매도가2')]):
                            if price > 0:
                                arrow = pg.ArrowItem(angle=0, tipAngle=60, headLen=10, pen='w', brush='b')
                                arrow.setPos(self.ui.ctpg_xticks[j], price)
                                self.ui.ctpg[i].addItem(arrow)
            elif factor in ('초당거래대금', '분당거래대금'):
                ymax = self.ui.ctpg_data[fi(factor)].max()
                ymin = self.ui.ctpg_data[fi(f'{factor}평균')].min()
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                if is_min:
                    self.ui.ctpg[i].addItem(VolumeBarsItem(self.ui.ctpg_arry, [fi('현재가'), fi('분봉시가'), fi(factor)], self.ui.ctpg_xticks))
                else:
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi(factor)]:], y=self.ui.ctpg_data[fi(factor)], pen=(200, 100, 100))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi(f'{factor}평균')]:], y=self.ui.ctpg_data[fi(f'{factor}평균')], pen=(100, 200, 100))
            elif factor == '체결강도':
                ymax = max(self.ui.ctpg_data[fi('체결강도')].max(), self.ui.ctpg_data[fi('최고체결강도')].max())
                ymin = min(self.ui.ctpg_data[fi('체결강도')].min(), self.ui.ctpg_data[fi('최저체결강도')].min())
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('체결강도평균')]:], y=self.ui.ctpg_data[fi('체결강도평균')], pen=(200, 200, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('최저체결강도')]:], y=self.ui.ctpg_data[fi('최저체결강도')], pen=(100, 100, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('최고체결강도')]:], y=self.ui.ctpg_data[fi('최고체결강도')], pen=(200, 100, 100))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('체결강도')]:], y=self.ui.ctpg_data[fi('체결강도')], pen=(100, 200, 100))
            elif factor in ('초당체결수량', '분당체결수량'):
                if is_min:
                    ymax = max(self.ui.ctpg_data[fi('분당매수수량')].max(), self.ui.ctpg_data[fi('분당매도수량')].max())
                    ymin = min(self.ui.ctpg_data[fi('분당매수수량')].min(), self.ui.ctpg_data[fi('분당매도수량')].min())
                else:
                    ymax = max(self.ui.ctpg_data[fi('초당매수수량')].max(), self.ui.ctpg_data[fi('초당매도수량')].max())
                    ymin = min(self.ui.ctpg_data[fi('초당매수수량')].min(), self.ui.ctpg_data[fi('초당매도수량')].min())
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                if is_min:
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('분당매도수량')]:], y=self.ui.ctpg_data[fi('분당매도수량')], pen=(100, 100, 200))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('분당매수수량')]:], y=self.ui.ctpg_data[fi('분당매수수량')], pen=(200, 100, 100))
                else:
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('초당매도수량')]:], y=self.ui.ctpg_data[fi('초당매도수량')], pen=(100, 100, 200))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('초당매수수량')]:], y=self.ui.ctpg_data[fi('초당매수수량')], pen=(200, 100, 100))
            elif factor == '호가총잔량':
                ymax = max(self.ui.ctpg_data[fi('매수총잔량')].max(), self.ui.ctpg_data[fi('매도총잔량')].max())
                ymin = min(self.ui.ctpg_data[fi('매수총잔량')].min(), self.ui.ctpg_data[fi('매도총잔량')].min())
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매수총잔량')]:], y=self.ui.ctpg_data[fi('매수총잔량')], pen=(200, 100, 100))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매도총잔량')]:], y=self.ui.ctpg_data[fi('매도총잔량')], pen=(100, 100, 200))
            elif factor == '매도수호가잔량1':
                ymax = max(self.ui.ctpg_data[fi('매수잔량1')].max(), self.ui.ctpg_data[fi('매도잔량1')].max())
                ymin = min(self.ui.ctpg_data[fi('매수잔량1')].min(), self.ui.ctpg_data[fi('매도잔량1')].min())
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매수잔량1')]:], y=self.ui.ctpg_data[fi('매수잔량1')], pen=(200, 100, 100))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('매도잔량1')]:], y=self.ui.ctpg_data[fi('매도잔량1')], pen=(100, 100, 200))
            elif factor in ('누적초당매도수수량', '누적분당매도수수량'):
                if is_min:
                    ymax = max(self.ui.ctpg_data[fi('누적분당매수수량')].max(), self.ui.ctpg_data[fi('누적분당매도수량')].max())
                    ymin = min(self.ui.ctpg_data[fi('누적분당매수수량')].min(), self.ui.ctpg_data[fi('누적분당매도수량')].min())
                else:
                    ymax = max(self.ui.ctpg_data[fi('누적초당매수수량')].max(), self.ui.ctpg_data[fi('누적초당매도수량')].max())
                    ymin = min(self.ui.ctpg_data[fi('누적초당매수수량')].min(), self.ui.ctpg_data[fi('누적초당매도수량')].min())
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                if is_min:
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적분당매도수량')]:], y=self.ui.ctpg_data[fi('누적분당매도수량')], pen=(100, 100, 200))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적분당매수수량')]:], y=self.ui.ctpg_data[fi('누적분당매수수량')], pen=(200, 100, 100))
                else:
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적초당매도수량')]:], y=self.ui.ctpg_data[fi('누적초당매도수량')], pen=(100, 100, 200))
                    self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('누적초당매수수량')]:], y=self.ui.ctpg_data[fi('누적초당매수수량')], pen=(200, 100, 100))
            elif factor == 'AROON':
                ymax = self.ui.ctpg_data[fi('AROONU')].max()
                ymin = self.ui.ctpg_data[fi('AROOND')].min()
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('AROOND')]:], y=self.ui.ctpg_data[fi('AROOND')], pen=(100, 100, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('AROONU')]:], y=self.ui.ctpg_data[fi('AROONU')], pen=(100, 200, 100))
            elif factor == 'BBAND':
                ymax = max(self.ui.ctpg_data[fi('BBU')].max(), self.ui.ctpg_data[fi('현재가')].max())
                ymin = min(self.ui.ctpg_data[fi('BBL')].min(), self.ui.ctpg_data[fi('현재가')].min())
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('BBM')]:], y=self.ui.ctpg_data[fi('BBM')], pen=(100, 100, 100))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('BBL')]:], y=self.ui.ctpg_data[fi('BBL')], pen=(100, 100, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('BBU')]:], y=self.ui.ctpg_data[fi('BBU')], pen=(100, 200, 100))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('현재가')]:], y=self.ui.ctpg_data[fi('현재가')], pen=(200, 100, 100))
            elif factor == 'DMI':
                ymax = self.ui.ctpg_data[fi('DIP')].max()
                ymin = self.ui.ctpg_data[fi('DIM')].min()
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('DIM')]:], y=self.ui.ctpg_data[fi('DIM')], pen=(100, 100, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('DIP')]:], y=self.ui.ctpg_data[fi('DIP')], pen=(100, 200, 100))
            elif factor == 'MACD':
                ymax = max(self.ui.ctpg_data[fi('MACD')].max(), self.ui.ctpg_data[fi('MACDS')].max(), self.ui.ctpg_data[fi('MACDH')].max())
                ymin = min(self.ui.ctpg_data[fi('MACD')].min(), self.ui.ctpg_data[fi('MACDS')].min(), self.ui.ctpg_data[fi('MACDH')].min())
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('MACD')]:], y=self.ui.ctpg_data[fi('MACD')], pen=(100, 100, 100))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('MACDH')]:], y=self.ui.ctpg_data[fi('MACDH')], pen=(100, 100, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('MACDS')]:], y=self.ui.ctpg_data[fi('MACDS')], pen=(100, 200, 100))
            elif factor == 'STOCHS':
                ymax = self.ui.ctpg_data[fi('STOCHSD')].max()
                ymin = self.ui.ctpg_data[fi('STOCHSK')].min()
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHSD')]:], y=self.ui.ctpg_data[fi('STOCHSD')], pen=(100, 100, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHSK')]:], y=self.ui.ctpg_data[fi('STOCHSK')], pen=(100, 200, 100))
            elif factor == 'STOCHF':
                ymax = self.ui.ctpg_data[fi('STOCHFD')].max()
                ymin = self.ui.ctpg_data[fi('STOCHFK')].min()
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHFD')]:], y=self.ui.ctpg_data[fi('STOCHFD')], pen=(100, 100, 200))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi('STOCHFK')]:], y=self.ui.ctpg_data[fi('STOCHFK')], pen=(100, 200, 100))
            else:
                pen = (100, 200, 100)
                if is_min:
                    if coin and fi(factor) > 57:
                        pen = (100, 200, 200)
                    elif not coin and fi(factor) > 67:
                        pen = (100, 200, 200)
                ymax = self.ui.ctpg_data[fi(factor)].max()
                ymin = self.ui.ctpg_data[fi(factor)].min()
                if chuse_exist: self.ui.ctpg[i].addItem(ChuseItem(self.ui.ctpg_arry[:, fi('관심종목')], ymin, ymax, self.ui.ctpg_xticks))
                self.ui.ctpg[i].plot(x=self.ui.ctpg_xticks[len_list[fi(factor)]:], y=self.ui.ctpg_data[fi(factor)], pen=pen)

            if self.ui.ct_checkBoxxxxx_02.isChecked():
                legend = pg.TextItem(anchor=(1, 0), color=color_fg_bt, border=color_bg_bt, fill=color_bg_ld)
                legend.setText(get_label_text(False, coin, code, is_min, self.ui.ctpg_arry, -1, self.ui.ctpg_factors[i], hms))
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
                self.ui.ctpg_legend[i].setPos(self.ui.ctpg_cvb[i].state['viewRange'][0][1], self.ui.ctpg_cvb[i].state['viewRange'][1][1])

            if i == chart_count - 1: break

        if self.ui.ct_checkBoxxxxx_01.isChecked():
            if chart_count == 6:
                self.crosshair.crosshair(
                    False, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                    self.ui.ctpg[4], self.ui.ctpg[5]
                )
            elif chart_count == 8:
                self.crosshair.crosshair(
                    False, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                    self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7]
                )
            elif chart_count == 10:
                self.crosshair.crosshair(
                    False, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                    self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8],
                    self.ui.ctpg[9]
                )
            elif chart_count == 12:
                self.crosshair.crosshair(
                    False, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                    self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8],
                    self.ui.ctpg[9], self.ui.ctpg[10], self.ui.ctpg[11]
                )
            elif chart_count == 16:
                self.crosshair.crosshair(
                    False, coin, is_min, self.ui.ctpg[0], self.ui.ctpg[1], self.ui.ctpg[2], self.ui.ctpg[3],
                    self.ui.ctpg[4], self.ui.ctpg[5], self.ui.ctpg[6], self.ui.ctpg[7], self.ui.ctpg[8],
                    self.ui.ctpg[9], self.ui.ctpg[10], self.ui.ctpg[11], self.ui.ctpg[12], self.ui.ctpg[13],
                    self.ui.ctpg[14], self.ui.ctpg[15]
                )

        self.ui.ctpg_name = self.ui.ct_lineEdittttt_05.text()
        if not self.ui.database_chart: self.ui.database_chart = True

        if self.ui.dialog_hoga.isVisible() and self.ui.hg_labellllllll_01.text() != '':
            self.ui.hgButtonClicked_02('매수')

    @thread_decorator
    def KiwoomHTSChart(self, code, date):
        try:
            hwnd_mult = win32gui.FindWindowEx(None, None, None, "[0607] 멀티차트")
            if hwnd_mult != 0:
                win32gui.SetForegroundWindow(hwnd_mult)
                self.HTSControl(code, date, hwnd_mult)
            else:
                hwnd_main = win32gui.FindWindowEx(None, None, '_NKHeroMainClass', None)
                if hwnd_main != 0:
                    win32gui.SetForegroundWindow(hwnd_main)
                    hwnd_mult = win32gui.FindWindowEx(hwnd_main, None, "MDIClient", None)
                    hwnd_mult = win32gui.FindWindowEx(hwnd_mult, None, None, "[0607] 멀티차트")
                    self.HTSControl(code, date, hwnd_mult)
        except:
            pass

    def HTSControl(self, code, date, hwnd_mult):
        try:
            hwnd_part = win32gui.FindWindowEx(hwnd_mult, None, "AfxFrameOrView110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)

            hwnd_prev = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)

            hwnd_prev = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)
            hwnd_mid1 = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)
            hwnd_mid2 = win32gui.FindWindowEx(hwnd_part, hwnd_mid1, "AfxWnd110", None)
            hwnd_mid3 = win32gui.FindWindowEx(hwnd_part, hwnd_mid2, "AfxWnd110", None)

            hwnd_prev = win32gui.FindWindowEx(hwnd_mid2, None, "AfxWnd110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid2, hwnd_prev, "AfxWnd110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid2, hwnd_prev, "AfxWnd110", None)
            hwnd_code = win32gui.FindWindowEx(hwnd_mid2, hwnd_prev, "AfxWnd110", None)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_code, 0x01))
            enter_keys(win32gui.GetDlgItem(hwnd_code, 0x01), code)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_mid3, 0x834))
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid1, None, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_mid1, hwnd_prev, "AfxWnd110", None)
            hwnd_date = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_date, 0x7D1))
            press_keys(int(date[0]))
            press_keys(int(date[1]))
            press_keys(int(date[2]))
            press_keys(int(date[3]))
            press_keys(int(date[4]))
            press_keys(int(date[5]))
            press_keys(int(date[6]))
            press_keys(int(date[7]))
            win32api.Sleep(200)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_mid3, 0x838))
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid1, None, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_mid1, hwnd_prev, "AfxWnd110", None)
            hwnd_date = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_date, 0x7D1))
            press_keys(int(date[4]))
            press_keys(int(date[5]))
            press_keys(int(date[6]))
            press_keys(int(date[7]))
        except:
            print('키움HTS에 멀티차트가 없거나 일봉, 분봉 차트 두개로 설정되어 있지 않습니다.')
            print('2x1로 좌측은 일봉, 우측은 분봉, 종목일괄변경으로 설정하신 다음 실행하십시오.')

        win32gui.SetForegroundWindow(int(self.ui.winId()))
