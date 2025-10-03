import pandas as pd
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem
from ui.set_style import color_fg_bt, color_fg_dk, color_fg_bc, color_bf_bt, color_bf_dk, color_ct_hg
from ui.ui_get_label_text import get_label_text
from utility.setting import ui_num, columns_hg, columns_hj, list_stock_tick, list_stock_min, list_coin_min1, \
    list_coin_min2, list_coin_tick1, list_coin_tick2
from utility.static import error_decorator, change_format, comma2int, comma2float, strp_time


class NumericItem(QTableWidgetItem):
    # noinspection PyUnresolvedReferences
    def __lt__(self, other):
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)


class UpdateTablewidget:
    def __init__(self, ui):
        """
        windowQ, soundQ, ui.queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.ui = ui

    @error_decorator
    def update_tablewidget(self, data):
        if len(data) == 2:
            gubun, df = data
        else:
            if type(data[2]) == str:
                gubun, df, ymshms = data
                if self.ui.ctpg_xticks is not None:
                    self.UpdateHogainfoForChart(gubun, ymshms)
            else:
                gubun, df, usdtokrw = data
                self.ui.dialog_kimp.setWindowTitle(f'STOM KIMP - 환율 {usdtokrw:,}원/달러')

        tableWidget = None
        if gubun == ui_num['S실현손익']:
            tableWidget = self.ui.stt_tableWidgettt
        elif gubun == ui_num['S거래목록']:
            tableWidget = self.ui.std_tableWidgettt
        elif gubun == ui_num['S잔고평가']:
            tableWidget = self.ui.stj_tableWidgettt
        elif gubun == ui_num['S잔고목록']:
            tableWidget = self.ui.sjg_tableWidgettt
        elif gubun == ui_num['S체결목록']:
            tableWidget = self.ui.scj_tableWidgettt
        elif gubun == ui_num['S당일합계']:
            tableWidget = self.ui.sdt_tableWidgettt
        elif gubun == ui_num['S당일상세']:
            tableWidget = self.ui.sds_tableWidgettt
        elif gubun == ui_num['S누적합계']:
            tableWidget = self.ui.snt_tableWidgettt
        elif gubun == ui_num['S누적상세']:
            tableWidget = self.ui.sns_tableWidgettt
        elif gubun == ui_num['S관심종목']:
            tableWidget = self.ui.sgj_tableWidgettt
        elif gubun == ui_num['C실현손익']:
            tableWidget = self.ui.ctt_tableWidgettt
        elif gubun == ui_num['C거래목록']:
            tableWidget = self.ui.ctd_tableWidgettt
        elif gubun == ui_num['C잔고평가']:
            tableWidget = self.ui.ctj_tableWidgettt
        elif gubun == ui_num['C잔고목록']:
            tableWidget = self.ui.cjg_tableWidgettt
        elif gubun == ui_num['C체결목록']:
            tableWidget = self.ui.ccj_tableWidgettt
        elif gubun == ui_num['C당일합계']:
            tableWidget = self.ui.cdt_tableWidgettt
        elif gubun == ui_num['C당일상세']:
            tableWidget = self.ui.cds_tableWidgettt
            if tableWidget.columnCount() != len(df.columns):
                tableWidget.setColumnCount(len(df.columns))
                tableWidget.setHorizontalHeaderLabels(df.columns)
                if len(df.columns) == 7:
                    tableWidget.setColumnWidth(0, 90)
                    tableWidget.setColumnWidth(1, 101)
                    tableWidget.setColumnWidth(2, 95)
                    tableWidget.setColumnWidth(3, 95)
                    tableWidget.setColumnWidth(4, 95)
                    tableWidget.setColumnWidth(5, 95)
                    tableWidget.setColumnWidth(6, 95)
                else:
                    tableWidget.setColumnWidth(0, 90)
                    tableWidget.setColumnWidth(1, 96)
                    tableWidget.setColumnWidth(2, 80)
                    tableWidget.setColumnWidth(3, 80)
                    tableWidget.setColumnWidth(4, 80)
                    tableWidget.setColumnWidth(5, 80)
                    tableWidget.setColumnWidth(6, 80)
                    tableWidget.setColumnWidth(7, 80)
        elif gubun == ui_num['C누적합계']:
            tableWidget = self.ui.cnt_tableWidgettt
        elif gubun == ui_num['C누적상세']:
            tableWidget = self.ui.cns_tableWidgettt
        elif gubun == ui_num['C관심종목']:
            tableWidget = self.ui.cgj_tableWidgettt
        elif gubun == ui_num['S상세기록']:
            tableWidget = self.ui.ss_tableWidget_01
            tableWidget.setHorizontalHeaderLabels(df.columns)
        elif gubun == ui_num['C상세기록']:
            tableWidget = self.ui.cs_tableWidget_01
            tableWidget.setHorizontalHeaderLabels(df.columns)
        elif gubun in (ui_num['C호가종목'], ui_num['S호가종목']):
            tableWidget = self.ui.hj_tableWidgett_01
        elif gubun in (ui_num['C호가체결'], ui_num['S호가체결']):
            if not self.ui.dialog_hoga.isVisible():
                self.ui.wdzservQ.put(('receiver', ('호가종목코드', '000000')))
                if self.ui.CoinReceiverProcessAlive():  self.ui.creceivQ.put('000000')
                return
            tableWidget = self.ui.hc_tableWidgett_01
        elif gubun in (ui_num['C호가체결2'], ui_num['S호가체결2']):
            tableWidget = self.ui.hc_tableWidgett_02
        elif gubun in (ui_num['C호가잔량'], ui_num['S호가잔량']):
            tableWidget = self.ui.hg_tableWidgett_01
        elif gubun == ui_num['기업공시']:
            tableWidget = self.ui.gs_tableWidgett_01
        elif gubun == ui_num['기업뉴스']:
            tableWidget = self.ui.ns_tableWidgett_01
        elif gubun == ui_num['재무년도']:
            tableWidget = self.ui.jm_tableWidgett_01
            tableWidget.setHorizontalHeaderLabels(df.columns)
        elif gubun == ui_num['재무분기']:
            tableWidget = self.ui.jm_tableWidgett_02
            tableWidget.setHorizontalHeaderLabels(df.columns)
        elif gubun == ui_num['스톰라이브1']:
            tableWidget = self.ui.slsd_tableWidgett
        elif gubun == ui_num['스톰라이브2']:
            tableWidget = self.ui.slsn_tableWidgett
        elif gubun == ui_num['스톰라이브3']:
            tableWidget = self.ui.slst_tableWidgett
        elif gubun == ui_num['스톰라이브4']:
            tableWidget = self.ui.slcd_tableWidgett
        elif gubun == ui_num['스톰라이브5']:
            tableWidget = self.ui.slcn_tableWidgett
        elif gubun == ui_num['스톰라이브6']:
            tableWidget = self.ui.slct_tableWidgett
        elif gubun == ui_num['스톰라이브7']:
            tableWidget = self.ui.slbt_tableWidgett
        elif gubun == ui_num['스톰라이브8']:
            tableWidget = self.ui.slbd_tableWidgett
        elif gubun == ui_num['김프']:
            if not self.ui.dialog_kimp.isVisible():
                return
            tableWidget = self.ui.kp_tableWidget_01
        if tableWidget is None:
            return

        len_df = len(df)
        if len_df == 0:
            tableWidget.clearContents()
            return

        if gubun in (ui_num['S상세기록'], ui_num['C상세기록'],
                     ui_num['S관심종목'], ui_num['C관심종목'], ui_num['S당일상세'], ui_num['김프'], ui_num['S누적상세'],
                     ui_num['C당일상세'], ui_num['C누적상세'], ui_num['스톰라이브1'], ui_num['스톰라이브3'],
                     ui_num['스톰라이브4'], ui_num['스톰라이브6'], ui_num['스톰라이브7']):
            tableWidget.setSortingEnabled(False)

        tableWidget.setRowCount(len_df)
        arry = df.values
        for i, index in enumerate(df.index):
            for j, column in enumerate(df.columns):
                if column in ('체결시간', '매수시간', '매도시간'):
                    cgtime = str(arry[i, j])
                    if column == '체결시간': cgtime = f'{cgtime[8:10]}:{cgtime[10:12]}:{cgtime[12:14]}'
                    item = QTableWidgetItem(cgtime)
                elif column in ('거래일자', '일자', '일자 및 시간'):
                    day = arry[i, j]
                    if '.' not in day:
                        day = day[:4] + '.' + day[4:6] + '.' + day[6:]
                    item = QTableWidgetItem(day)
                elif gubun in (ui_num['C체결목록'], ui_num['C잔고목록'], ui_num['C잔고평가'], ui_num['C거래목록'], ui_num['C실현손익']) and \
                        column in ('매입금액', '평가금액', '평가손익', '매수금액', '매도금액', '수익금', '총매수금액', '총매도금액',
                                   '총수익금액', '총손실금액', '수익금합계', '총평가손익', '총매입금액', '총평가금액'):
                    item = QTableWidgetItem(change_format(arry[i, j], dotdown4=True))
                elif column in ('종목명', '포지션', '주문번호', '주문구분', '공시', '정보제공', '언론사', '제목', '링크', '구분', 'period', 'time', '추가매수시간') or \
                        gubun in (ui_num['재무년도'], ui_num['재무분기']) or (self.ui.database_chart and column == '체결수량'):
                    try:
                        item = QTableWidgetItem(str(arry[i, j]))
                    except:
                        continue
                elif '량' in column and gubun in (ui_num['C잔고목록'], ui_num['C체결목록'], ui_num['C거래목록'], ui_num['C호가체결'], ui_num['C호가잔량']):
                    item = QTableWidgetItem(change_format(arry[i, j], dotdown8=True))
                elif (gubun == ui_num['C잔고목록'] and column in ('매입가', '현재가')) or \
                        (gubun == ui_num['C체결목록'] and column in ('체결가', '주문가격')) or \
                        (gubun == ui_num['C호가종목'] and column in ('현재가', '시가', '고가', '저가')) or \
                        (gubun == ui_num['C호가잔량'] and column == '호가'):
                    item = QTableWidgetItem(change_format(arry[i, j], dotdown8=True))
                elif gubun in (ui_num['S관심종목'], ui_num['C관심종목'], ui_num['S상세기록'],
                               ui_num['C상세기록'], ui_num['S당일상세'], ui_num['S누적상세'],
                               ui_num['C당일상세'], ui_num['C누적상세'], ui_num['스톰라이브1'], ui_num['스톰라이브3'],
                               ui_num['스톰라이브4'], ui_num['스톰라이브6'], ui_num['스톰라이브7'], ui_num['김프']):
                    value = str(arry[i, j])
                    if column in ('수익률', '누적수익률', 'per', 'hlml_per', 'ch', 'ch_avg', 'ch_high', '대비(원)',
                                  '대비율(%)', 'aht', 'wr', 'app', 'tpp', 'mdd', 'cagr'):
                        item = NumericItem(change_format(value))
                    elif (gubun == ui_num['C상세기록'] and column in ('매수가', '매도가')) or column == '바이낸스(달러)':
                        item = NumericItem(change_format(value, dotdown8=True))
                    elif column == '업비트(원)':
                        item = NumericItem(change_format(value, dotdown4=True))
                    elif column == '매도조건':
                        item = QTableWidgetItem(value)
                    else:
                        item = NumericItem(change_format(value, dotdowndel=True))
                    if column != '매도조건':
                        value = float(value)
                        item.setData(Qt.UserRole, value)
                elif column not in ('수익률', '누적수익률', '등락율', '체결강도'):
                    item = QTableWidgetItem(change_format(arry[i, j], dotdowndel=True))
                else:
                    item = QTableWidgetItem(change_format(arry[i, j]))

                if column in ('종목명', '공시', '제목', '링크', '매도조건'):
                    item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignLeft))
                elif column in ('포지션', '거래횟수', '추정예탁자산', '추정예수금', '보유종목수', '정보제공', '언론사', '주문구분',
                                '매수시간', '매도시간', '체결시간', '거래일자', '기간', '일자', '일자 및 시간', '구분', 'period', 'time'):
                    item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
                else:
                    item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignRight))

                if gubun in (ui_num['C호가체결'], ui_num['S호가체결']) and not self.ui.database_chart:
                    if column == '체결수량':
                        if i == 0:    item.setIcon(self.ui.icon_totalb)
                        elif i == 11: item.setIcon(self.ui.icon_totals)
                    elif column == '체결강도':
                        if i == 0:    item.setIcon(self.ui.icon_up)
                        elif i == 11: item.setIcon(self.ui.icon_down)
                elif gubun in (ui_num['C호가잔량'], ui_num['S호가잔량']):
                    if column == '잔량':
                        if i == 0:    item.setIcon(self.ui.icon_totalb)
                        elif i == 11: item.setIcon(self.ui.icon_totals)
                    elif column == '호가':
                        if i == 0:    item.setIcon(self.ui.icon_up)
                        elif i == 11: item.setIcon(self.ui.icon_down)
                        else:
                            if self.ui.hj_tableWidgett_01.item(0, 0) is not None:
                                func = comma2int if gubun == ui_num['S호가잔량'] else comma2float
                                o    = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('시가')).text())
                                h    = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('고가')).text())
                                low  = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('저가')).text())
                                uvi  = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('UVI')).text())
                                if o != 0:
                                    hg = arry[i, j]
                                    if hg == o:     item.setIcon(self.ui.icon_open)
                                    elif hg == h:   item.setIcon(self.ui.icon_high)
                                    elif hg == low: item.setIcon(self.ui.icon_low)
                                    elif hg == uvi: item.setIcon(self.ui.icon_vi)

                if '수익금' in df.columns and gubun not in (ui_num['S상세기록'], ui_num['C상세기록']):
                    color = color_fg_bt if arry[i, list(df.columns).index('수익금')] >= 0 else color_fg_dk
                    item.setForeground(color)
                elif '누적수익금' in df.columns and gubun not in (ui_num['S상세기록'], ui_num['C상세기록']):
                    color = color_fg_bt if arry[i, list(df.columns).index('누적수익금')] >= 0 else color_fg_dk
                    item.setForeground(color)
                elif '수익금합계' in df.columns and gubun not in (ui_num['S상세기록'], ui_num['C상세기록']):
                    color = color_fg_bt if arry[i, list(df.columns).index('수익금합계')] >= 0 else color_fg_dk
                    item.setForeground(color)
                elif '평가손익' in df.columns and gubun not in (ui_num['S상세기록'], ui_num['C상세기록']):
                    color = color_fg_bt if arry[i, list(df.columns).index('평가손익')] >= 0 else color_fg_dk
                    item.setForeground(color)
                elif '총평가손익' in df.columns and gubun not in (ui_num['S상세기록'], ui_num['C상세기록']):
                    color = color_fg_bt if arry[i, list(df.columns).index('총평가손익')] >= 0 else color_fg_dk
                    item.setForeground(color)
                elif gubun in (ui_num['S체결목록'], ui_num['C체결목록']):
                    order_gubun = arry[i, 1]
                    if order_gubun == '매수':   item.setForeground(color_fg_bt)
                    elif order_gubun == '매도': item.setForeground(color_fg_dk)
                    elif '취소' in order_gubun: item.setForeground(color_fg_bc)
                elif gubun in (ui_num['C호가체결'], ui_num['S호가체결']) and not self.ui.database_chart:
                    if column == '체결수량':
                        if i in (0, 11):
                            color = color_fg_bt if arry[i, j] > arry[11 if i == 0 else 0, 0] else color_fg_dk
                            item.setForeground(color)
                        else:
                            func = comma2int if gubun == ui_num['S호가체결'] else comma2float
                            c    = func(self.ui.hg_tableWidgett_01.item(5, columns_hg.index('호가')).text())
                            if arry[i, j] > 0:
                                item.setForeground(color_fg_bt)
                                if arry[i, j] * c > 90000000:  item.setBackground(color_bf_bt)
                            else:
                                item.setForeground(color_fg_dk)
                                if arry[i, j] * c < -90000000: item.setBackground(color_bf_dk)
                    elif column == '체결강도':
                        color = color_fg_bt if arry[i, j] >= 100 else color_fg_dk
                        item.setForeground(color)
                elif gubun in (ui_num['C호가잔량'], ui_num['S호가잔량']):
                    if column == '잔량':
                        if i in (0, 11):
                            color = color_fg_bt if arry[i, j] > arry[11 if i == 0 else 0, 0] else color_fg_dk
                            item.setForeground(color)
                        elif i < 11:
                            item.setForeground(color_fg_bt)
                        else:
                            item.setForeground(color_fg_dk)
                    elif column == '호가':
                        if column == '호가' and arry[i, j] != 0:
                            if self.ui.hj_tableWidgett_01.item(0, 0) is not None:
                                func = comma2int if gubun == ui_num['S호가잔량'] else comma2float
                                c    = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('현재가')).text())
                                if i not in (0, 11) and arry[i, j] == c:
                                    item.setBackground(color_bf_bt)
                elif gubun in (ui_num['기업공시'], ui_num['기업뉴스']):
                    text = arry[i, 2]
                    if '단기과열' in text or '투자주의' in text or '투자경고' in text or '투자위험' in text or \
                            '거래정지' in text or '환기종목' in text or '불성실공시' in text or '관리종목' in text or \
                            '정리매매' in text or '유상증자' in text or '무상증자' in text:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                elif gubun in (ui_num['재무년도'],  ui_num['재무분기']):
                    color = color_fg_bt if '-' not in arry[i, j] else color_fg_dk
                    item.setForeground(color)
                tableWidget.setItem(i, j, item)

        if len_df < 13 and gubun in (ui_num['S거래목록'], ui_num['S잔고목록'], ui_num['C거래목록'], ui_num['C잔고목록']):
            tableWidget.setRowCount(13)
        elif len_df < 15 and gubun in (ui_num['S체결목록'], ui_num['C체결목록'], ui_num['S관심종목'], ui_num['C관심종목']):
            tableWidget.setRowCount(15)
        elif len_df < 19 and gubun in (ui_num['S당일상세'], ui_num['C당일상세']):
            tableWidget.setRowCount(19)
        elif len_df < 28 and gubun in (ui_num['S누적상세'], ui_num['C누적상세']):
            tableWidget.setRowCount(28)
        elif len_df < 20 and gubun == ui_num['기업공시']:
            tableWidget.setRowCount(20)
        elif len_df < 10 and gubun == ui_num['기업뉴스']:
            tableWidget.setRowCount(10)
        elif len_df < 32 and gubun in (ui_num['S상세기록'], ui_num['C상세기록']):
            tableWidget.setRowCount(32)
        elif len_df < 30 and gubun in (ui_num['스톰라이브1'], ui_num['스톰라이브4']):
            tableWidget.setRowCount(30)
        elif len_df < 28 and gubun in (ui_num['스톰라이브3'], ui_num['스톰라이브6']):
            tableWidget.setRowCount(28)
        elif len_df < 26 and gubun == ui_num['스톰라이브7']:
            tableWidget.setRowCount(26)
        elif len_df < 50 and gubun == ui_num['김프']:
            tableWidget.setRowCount(50)
        elif len_df < 12 and gubun in (ui_num['C호가체결2'], ui_num['S호가체결2']):
            tableWidget.setRowCount(12)

        if gubun in (ui_num['S상세기록'], ui_num['C상세기록'],
                     ui_num['S관심종목'], ui_num['C관심종목'], ui_num['S당일상세'], ui_num['김프'], ui_num['S누적상세'],
                     ui_num['C당일상세'], ui_num['C누적상세'], ui_num['스톰라이브1'], ui_num['스톰라이브3'],
                     ui_num['스톰라이브4'], ui_num['스톰라이브6'], ui_num['스톰라이브7']):
            tableWidget.setSortingEnabled(True)

    def UpdateHogainfoForChart(self, gubun, ymdhms):
        def fi(fname):
            if is_min:
                if gubun == ui_num['S호가종목']:   return list_stock_min.index(fname)
                elif 'KRW' in self.ui.ctpg_name: return list_coin_min1.index(fname)
                else:                            return list_coin_min2.index(fname)
            else:
                if gubun == ui_num['S호가종목']:  return list_stock_tick.index(fname)
                elif 'KRW' in self.ui.ctpg_name: return list_coin_tick1.index(fname)
                else:                            return list_coin_tick2.index(fname)

        def setInfiniteLine():
            vhline = pg.InfiniteLine()
            vhline.setPen(pg.mkPen(color_ct_hg, width=1))
            return vhline

        is_min = len(ymdhms) == 12
        if is_min:
            x = strp_time('%Y%m%d%H%M%S', f'{ymdhms}00').timestamp()
        else:
            x = strp_time('%Y%m%d%H%M%S', ymdhms).timestamp()
        try:
            xpoint = self.ui.ctpg_xticks.index(x)
        except:
            return

        if self.ui.ctpg_hline is None:
            vLine1  = setInfiniteLine()
            vLine2  = setInfiniteLine()
            vLine3  = setInfiniteLine()
            vLine4  = setInfiniteLine()
            vLine5  = setInfiniteLine()
            vLine6  = setInfiniteLine()
            vLine7  = setInfiniteLine()
            vLine8  = setInfiniteLine()
            vLine9  = setInfiniteLine()
            vLine10 = setInfiniteLine()
            vLine11 = setInfiniteLine()
            vLine12 = setInfiniteLine()
            vLine13 = setInfiniteLine()
            vLine14 = setInfiniteLine()
            vLine15 = setInfiniteLine()
            vLine16 = setInfiniteLine()

            self.ui.ctpg[0].addItem(vLine1)
            self.ui.ctpg[1].addItem(vLine2)
            self.ui.ctpg[2].addItem(vLine3)
            self.ui.ctpg[3].addItem(vLine4)
            self.ui.ctpg[4].addItem(vLine5)
            self.ui.ctpg[5].addItem(vLine6)
            self.ui.ctpg_hline = [vLine1, vLine2, vLine3, vLine4, vLine5, vLine6]
            if len(self.ui.ctpg) > 6:
                self.ui.ctpg[6].addItem(vLine7)
                self.ui.ctpg[7].addItem(vLine8)
                self.ui.ctpg_hline += [vLine7, vLine8]
            if len(self.ui.ctpg) > 8:
                self.ui.ctpg[8].addItem(vLine9)
                self.ui.ctpg[9].addItem(vLine10)
                self.ui.ctpg_hline += [vLine9, vLine10]
            if len(self.ui.ctpg) > 10:
                self.ui.ctpg[10].addItem(vLine11)
                self.ui.ctpg[11].addItem(vLine12)
                self.ui.ctpg_hline += [vLine11, vLine12]
            if len(self.ui.ctpg) > 12:
                self.ui.ctpg[12].addItem(vLine13)
                self.ui.ctpg[13].addItem(vLine14)
                self.ui.ctpg[14].addItem(vLine15)
                self.ui.ctpg[15].addItem(vLine16)
                self.ui.ctpg_hline += [vLine13, vLine14, vLine15, vLine16]

        for vline in self.ui.ctpg_hline:
            vline.setPos(x)

        ymd = ymdhms[:8]
        hms = ymdhms[8:]
        ymd_text = f'{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}'
        hms_text = f'{hms[:2]}:{hms[2:]}' if is_min else f'{hms[:2]}:{hms[2:4]}:{hms[4:]}'
        self.ui.hg_labellllllll_01.setText(f'{ymd_text} {hms_text}')

        if is_min:
            info = [
                '이동평균005', '이동평균010', '이동평균020', '이동평균060', '체결강도', '체결강도평균', '최고체결강도',
                '최저체결강도', '분당거래대금', '분당거래대금평균', '분당매수수량', '분당매도수량'
            ]
        else:
            info = [
                '이동평균0060', '이동평균0300', '이동평균0600', '이동평균1200', '체결강도', '체결강도평균', '최고체결강도',
                '최저체결강도', '초당거래대금', '초당거래대금평균', '초당매수수량', '초당매도수량'
            ]

        data = []
        for col_name in info:
            data.append(self.ui.ctpg_arry[xpoint, fi(col_name)])
        df1 = pd.DataFrame({'체결수량': info, '체결강도': data})

        if is_min:
            if gubun == ui_num['S호가종목']:
                info = [
                    '고저평균대비등락율', '매도수5호가잔량합', '당일거래대금', '누적분당매수수량', '누적분당매도수량',
                    '등락율각도', '당일거래대금각도', '전일비각도', '거래대금증감', '전일비', '회전율', '전일동시간비'
                ]
            else:
                info = [
                    '고저평균대비등락율', '매도수5호가잔량합', '당일거래대금', '누적분당매수수량', '누적분당매도수량',
                    '등락율각도', '당일거래대금각도'
                ]
        else:
            if gubun == ui_num['S호가종목']:
                info = [
                    '고저평균대비등락율', '매도수5호가잔량합', '당일거래대금', '누적초당매수수량', '누적초당매도수량',
                    '등락율각도', '당일거래대금각도', '전일비각도', '거래대금증감', '전일비', '회전율', '전일동시간비'
                ]
            else:
                info = [
                    '고저평균대비등락율', '매도수5호가잔량합', '당일거래대금', '누적초당매수수량', '누적초당매도수량',
                    '등락율각도', '당일거래대금각도'
                ]

        data = []
        for col_name in info:
            data.append(self.ui.ctpg_arry[xpoint, fi(col_name)])
        df2 = pd.DataFrame({'체결수량': info, '체결강도': data})

        gubun_ = 'C' if gubun == ui_num['C호가종목'] else 'S'
        self.ui.windowQ.put((ui_num[f'{gubun_}호가체결'], df1))
        self.ui.windowQ.put((ui_num[f'{gubun_}호가체결2'], df2))

        coin = gubun == ui_num['C호가종목']
        for i in range(len(self.ui.ctpg_legend)):
            self.ui.ctpg_legend[i].setText(get_label_text(False, coin, self.ui.ctpg_name, is_min, self.ui.ctpg_arry, xpoint, self.ui.ctpg_factors[i], hms_text))
            self.ui.ctpg_labels[i].setText('')
