
import pandas as pd
from PyQt5.QtCore import Qt
from ui.draw_chart.draw_label_text import get_label_text
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from ui.etcetera.process_alive import receiver_process_alive
from utility.settings.setting_base import ui_num, columns_hg, columns_hj
from utility.static_method.static import change_format, comma2int, comma2float, dt_ymdhms
from ui.create_widget.set_style import color_fg_bt, color_fg_dk, color_fg_bc, color_bf_bt, color_bf_dk, color_ct_hg


class NumericItem(QTableWidgetItem):
    """숫자 정렬을 위한 테이블 위젯 아이템 클래스입니다.
    UserRole 데이터를 기반으로 정렬합니다.
    """
    def __lt__(self, other):
        """비교 연산을 수행합니다.
        Args:
            other: 비교할 다른 아이템
        Returns:
            비교 결과
        """
        return self.data(Qt.UserRole) < other.data(Qt.UserRole)


class UpdateTablewidget:
    """테이블 위젯 업데이트 클래스입니다.
    다양한 데이터를 테이블 위젯에 표시합니다.
    """
    def __init__(self, ui):
        """테이블 위젯 업데이트를 초기화합니다.
        Args:
            ui: UI 클래스 인스턴스
        """
        self.ui = ui

        self.dict_table = {
            ui_num['실현손익']: self.ui.tt_tableWidgettt,
            ui_num['거래목록']: self.ui.td_tableWidgettt,
            ui_num['잔고평가']: self.ui.tj_tableWidgettt,
            ui_num['잔고목록']: self.ui.jg_tableWidgettt,
            ui_num['체결목록']: self.ui.cj_tableWidgettt,
            ui_num['당일합계']: self.ui.dt_tableWidgetttt,
            ui_num['당일상세']: self.ui.ds_tableWidgetttt,
            ui_num['누적합계']: self.ui.nt_tableWidgetttt,
            ui_num['누적상세']: self.ui.ns_tableWidgetttt,
            ui_num['관심종목']: self.ui.gj_tableWidgettt,
            ui_num['상세기록']: self.ui.ss_tableWidget_01,
            ui_num['호가종목']: self.ui.hj_tableWidgett_01,
            ui_num['호가체결']: self.ui.hc_tableWidgett_01,
            ui_num['호가체결2']: self.ui.hc_tableWidgett_02,
            ui_num['호가잔량']: self.ui.hg_tableWidgett_01,
            ui_num['기업공시']: self.ui.gs_tableWidgett_01,
            ui_num['기업뉴스']: self.ui.ns_tableWidgett_01,
            ui_num['재무년도']: self.ui.jm_tableWidgett_01,
            ui_num['재무분기']: self.ui.jm_tableWidgett_02,
            ui_num['스톰라이브1']: self.ui.slsd_tableWidgett,
            ui_num['스톰라이브2']: self.ui.slsn_tableWidgett,
            ui_num['스톰라이브3']: self.ui.sltd_tableWidgett,
            ui_num['스톰라이브4']: self.ui.slcd_tableWidgett,
            ui_num['스톰라이브5']: self.ui.slcn_tableWidgett,
            ui_num['스톰라이브6']: self.ui.slct_tableWidgett,
            ui_num['스톰라이브7']: self.ui.slfd_tableWidgett,
            ui_num['스톰라이브8']: self.ui.slfn_tableWidgett,
            ui_num['스톰라이브9']: self.ui.slft_tableWidgett,
            ui_num['스톰라이브10']: self.ui.slbt_tableWidgett,
            ui_num['스톰라이브11']: self.ui.slbd_tableWidgett,
            ui_num['김프']: self.ui.kp_tableWidget_01
        }

        self.dict_minrowcnt = {
            ui_num['거래목록']: 13,
            ui_num['잔고목록']: 13,
            ui_num['체결목록']: 15,
            ui_num['관심종목']: 15,
            ui_num['당일상세']: 19,
            ui_num['누적상세']: 28,
            ui_num['상세기록']: 32,
            ui_num['호가체결2']: 12,
            ui_num['스톰라이브1']: 30,
            ui_num['스톰라이브3']: 28,
            ui_num['스톰라이브4']: 30,
            ui_num['스톰라이브6']: 28,
            ui_num['스톰라이브7']: 30,
            ui_num['스톰라이브9']: 28,
            ui_num['스톰라이브10']: 26,
            ui_num['기업공시']: 20,
            ui_num['기업뉴스']: 10,
            ui_num['김프']: 50
        }

        self.table_change_uinums = (ui_num['거래목록'], ui_num['잔고목록'], ui_num['당일상세'])

        self.header_change_uinums = (ui_num['상세기록'], ui_num['재무년도'], ui_num['재무분기'])

        self.sorted_uinums = (ui_num['상세기록'], ui_num['관심종목'], ui_num['당일상세'], ui_num['김프'], ui_num['누적상세'],
                              ui_num['스톰라이브1'], ui_num['스톰라이브3'], ui_num['스톰라이브4'],
                              ui_num['스톰라이브6'], ui_num['스톰라이브7'], ui_num['스톰라이브9'], ui_num['스톰라이브10'])

        self.col_auto_resize_uinums = (ui_num['상세기록'], ui_num['잔고목록'], ui_num['체결목록'])

        self.col_fixed_size_uinums = (ui_num['호가종목'], ui_num['호가잔량'], ui_num['기업공시'], ui_num['기업뉴스'],
                                      ui_num['재무년도'], ui_num['재무분기'])

        self.columns_time = ('체결시간', '매수시간', '매도시간')
        self.columns_day = ('거래일자', '일자', '일자 및 시간')

        self.uinums_dot4 = (ui_num['체결목록'], ui_num['잔고목록'], ui_num['잔고평가'], ui_num['거래목록'], ui_num['실현손익'])
        self.columns_dot4 = ('매입금액', '평가금액', '평가손익', '매수금액', '매도금액', '수익금', '총매수금액', '총매도금액',
                             '총수익금액', '총손실금액', '수익금합계', '총평가손익', '총매입금액', '총평가금액')

        self.columns_str = ('종목명', '포지션', '주문번호', '주문구분', '공시', '정보제공', '언론사', '제목', '링크', '구분',
                            'period', 'time', '추가매수시간')

        self.uinums_dot8 = (ui_num['잔고목록'], ui_num['체결목록'], ui_num['거래목록'], ui_num['호가체결'], ui_num['호가잔량'])

        self.uinums_numeric = (ui_num['관심종목'], ui_num['상세기록'], ui_num['당일상세'], ui_num['누적상세'],
                               ui_num['스톰라이브1'], ui_num['스톰라이브3'], ui_num['스톰라이브4'], ui_num['스톰라이브6'],
                               ui_num['스톰라이브7'], ui_num['스톰라이브9'], ui_num['스톰라이브10'], ui_num['김프'])

        self.columns_numeric = ('수익률', '누적수익률', 'per', 'hlp', 'lhp', 'ch', '대비(원)',
                                '대비율(%)', 'aht', 'wr', 'app', 'tpp', 'mdd', 'cagr')

        self.columns_notdotx = ('수익률', '누적수익률', '등락율', '체결강도')

        self.columns_acenter = ('포지션', '거래횟수', '추정예탁자산', '추정예수금', '보유종목수', '정보제공', '언론사', '주문구분',
                                '매수시간', '매도시간', '체결시간', '거래일자', '기간', '일자', '일자 및 시간', '구분', 'period', 'time')

        self.uinums_hogatick = (ui_num['호가체결'], ui_num['호가체결'])
        self.uinums_hogarem = (ui_num['호가잔량'], ui_num['호가잔량'])
        self.uinums_detail1 = (ui_num['상세기록'], ui_num['상세기록'])
        self.uinums_detail2 = (ui_num['당일상세'], ui_num['당일상세'])

        self.uinums_str = (ui_num['재무년도'], ui_num['재무분기'])
        self.uinums_giup = (ui_num['기업공시'], ui_num['기업뉴스'])
        self.uinums_jemu = (ui_num['재무년도'], ui_num['재무분기'])

        self.columns_price1 = ('매수가', '현재가')
        self.columns_price2 = ('체결가', '주문가격')
        self.columns_price3 = ('현재가', '시가', '고가', '저가')
        self.columns_price4 = ('매수가', '매도가')

        self.columns_aleft = ('종목명', '공시', '제목', '링크', '매도조건')
        self.warning_text = ('단기과열', '투자주의', '투자경고', '투자위험', '거래정지', '환기종목', '불성실공시', '관리종목',
                             '정리매매', '유상증자', '무상증자')

        self.hoga_info1 = [
            '이동평균5', '이동평균10', '이동평균20', '이동평균60', '이동평균120', '당일거래대금',
            '분당거래대금', '분당거래대금평균', '분당매수금액', '분당매도금액', '매도총잔량', '매수총잔량'
        ]
        self.hoga_info2 = [
            '이동평균60', '이동평균150', '이동평균300', '이동평균600', '이동평균1200', '당일거래대금',
            '초당거래대금', '초당거래대금평균', '초당매수금액', '초당매도금액', '매도총잔량', '매수총잔량'
        ]
        self.hoga_info3 = [
            '등락율각도', '고저평균대비등락율', '저가대비고가등락율', '당일매수금액', '당일매도금액', '최고매수금액',
            '최고매도금액', '최고매수가격', '최고매도가격', '누적분당매수수량', '누적분당매도수량', '매도수5호가잔량합'
        ]
        self.hoga_info4 = [
            '등락율각도', '고저평균대비등락율', '저가대비고가등락율', '당일매수금액', '당일매도금액', '최고매수금액',
            '최고매도금액', '최고매수가격', '최고매도가격', '누적초당매수수량', '누적초당매도수량', '매도수5호가잔량합'
        ]

    # noinspection PyUnresolvedReferences
    def update_tablewidget(self, data):
        """테이블 위젯을 업데이트합니다.
        수신된 데이터를 기반으로 테이블 위젯에 내용을 표시합니다.
        Args:
            data: 데이터 (구분, 데이터프레임, 추가정보)
        """
        if len(data) == 2:
            gubun, df = data
        else:
            if data[2].__class__ == str:
                gubun, df, ymshms = data
                if self.ui.ctpg_xticks is not None:
                    self.update_hogainfo_for_chart(ymshms)
            else:
                gubun, df, usdtokrw = data
                self.ui.dialog_kimp.setWindowTitle(f'STOM KIMP - 환율 {usdtokrw:,}원/달러')

        tableWidget = self.dict_table.get(gubun)
        if tableWidget is None:
            return

        len_df = len(df)
        if len_df == 0:
            tableWidget.clearContents()
            return

        if gubun in self.uinums_hogatick:
            if not self.ui.dialog_hoga.isVisible():
                if receiver_process_alive(self.ui):
                    self.ui.receivQ.put(('호가종목코드', '000000'))
                return

        elif gubun == ui_num['김프']:
            if not self.ui.dialog_kimp.isVisible():
                return

        columns_list = list(df.columns)
        columns_cnt  = len(columns_list)

        if gubun in self.table_change_uinums:
            self.tablewidget_change(gubun, tableWidget, columns_cnt, columns_list)

        elif gubun in self.header_change_uinums:
            tableWidget.setHorizontalHeaderLabels(columns_list)

        arry = df.values

        tableWidget.setRowCount(len_df)
        if gubun in self.sorted_uinums:
            tableWidget.setSortingEnabled(False)

        for i in range(len_df):
            for j, column in enumerate(columns_list):
                value = arry[i, j]

                if column in self.columns_time:
                    cgtime = str(value)
                    if column == '체결시간':
                        cgtime = f'{cgtime[8:10]}:{cgtime[10:12]}:{cgtime[12:14]}'
                    item = QTableWidgetItem(cgtime)

                elif column in self.columns_day:
                    day = value
                    if '.' not in day:
                        day = f'{day[:4]}.{day[4:6]}.{day[6:]}'
                    item = QTableWidgetItem(day)

                elif self.ui.market_gubun in (5, 9) and gubun in self.uinums_dot4 and column in self.columns_dot4:
                    item = QTableWidgetItem(change_format(value, 4))

                elif column in self.columns_str or (self.ui.database_chart and column == '체결수량'):
                    item = QTableWidgetItem(str(value))

                elif '량' in column and gubun in self.uinums_dot8:
                    if self.ui.market_gubun in (5, 9):
                        item = QTableWidgetItem(change_format(value, 8))
                    else:
                        item = QTableWidgetItem(change_format(value, 0))

                elif (gubun == ui_num['잔고목록'] and column in self.columns_price1) or \
                        (gubun == ui_num['체결목록'] and column in self.columns_price2) or \
                        (gubun == ui_num['호가종목'] and column in self.columns_price3) or \
                        (gubun == ui_num['호가잔량'] and column == '호가'):
                    if self.ui.market_gubun < 4:
                        item = QTableWidgetItem(change_format(value, 0))
                    elif self.ui.market_gubun in (5, 9):
                        item = QTableWidgetItem(change_format(value, 8))
                    else:
                        item = QTableWidgetItem(change_format(value))

                elif gubun in self.uinums_numeric:
                    value = str(value)
                    if column in self.columns_numeric:
                        item = NumericItem(change_format(value))
                    elif gubun == ui_num['상세기록'] and column in self.columns_price4:
                        if self.ui.market_gubun < 4:
                            item = NumericItem(change_format(value, 0))
                        elif self.ui.market_gubun in (5, 9):
                            item = NumericItem(change_format(value, 8))
                        else:
                            item = NumericItem(change_format(value))
                    elif column == '바이낸스(달러)':
                        item = NumericItem(change_format(value, 8))
                    elif column == '업비트(원)':
                        item = NumericItem(change_format(value, 4))
                    elif column == '매도조건':
                        item = QTableWidgetItem(value)
                    else:
                        item = NumericItem(change_format(value, 0))

                    if column != '매도조건':
                        value = float(value)
                        item.setData(Qt.UserRole, value)

                elif column not in self.columns_notdotx:
                    item = QTableWidgetItem(change_format(value, 0))
                else:
                    item = QTableWidgetItem(change_format(value))

                if column in self.columns_aleft:
                    item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignLeft))
                elif column in self.columns_acenter:
                    item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
                else:
                    item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignRight))

                if gubun in self.uinums_hogatick and not self.ui.database_chart:
                    if column == '체결수량':
                        if i == 0:    item.setIcon(self.ui.icon_totalb)
                        elif i == 11: item.setIcon(self.ui.icon_totals)
                    elif column == '체결강도':
                        if i == 0:    item.setIcon(self.ui.icon_up)
                        elif i == 11: item.setIcon(self.ui.icon_down)

                elif gubun in self.uinums_hogarem:
                    if column == '잔량':
                        if i == 0:    item.setIcon(self.ui.icon_totalb)
                        elif i == 11: item.setIcon(self.ui.icon_totals)
                    elif column == '호가':
                        if i == 0:    item.setIcon(self.ui.icon_up)
                        elif i == 11: item.setIcon(self.ui.icon_down)
                        else:
                            if self.ui.hj_tableWidgett_01.item(0, 0) is not None:
                                func = comma2int if gubun == ui_num['호가잔량'] else comma2float
                                o    = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('시가')).text())
                                h    = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('고가')).text())
                                low  = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('저가')).text())
                                uvi  = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('UVI')).text())
                                if o != 0:
                                    if value == o:     item.setIcon(self.ui.icon_open)
                                    elif value == h:   item.setIcon(self.ui.icon_high)
                                    elif value == low: item.setIcon(self.ui.icon_low)
                                    elif value == uvi: item.setIcon(self.ui.icon_vi)

                if '수익금' in columns_list and gubun not in self.uinums_detail1:
                    color = color_fg_bt if arry[i, columns_list.index('수익금')] >= 0 else color_fg_dk
                    item.setForeground(color)

                elif '누적수익금' in columns_list and gubun not in self.uinums_detail1:
                    color = color_fg_bt if arry[i, columns_list.index('누적수익금')] >= 0 else color_fg_dk
                    item.setForeground(color)

                elif '수익금합계' in columns_list and gubun not in self.uinums_detail1:
                    color = color_fg_bt if arry[i, columns_list.index('수익금합계')] >= 0 else color_fg_dk
                    item.setForeground(color)

                elif '평가손익' in columns_list and gubun not in self.uinums_detail1:
                    color = color_fg_bt if arry[i, columns_list.index('평가손익')] >= 0 else color_fg_dk
                    item.setForeground(color)

                elif '총평가손익' in columns_list and gubun not in self.uinums_detail1:
                    color = color_fg_bt if arry[i, columns_list.index('총평가손익')] >= 0 else color_fg_dk
                    item.setForeground(color)

                elif gubun == ui_num['체결목록']:
                    order_gubun = arry[i, 1]
                    if order_gubun == '매수' or order_gubun == 'BUY_LONG' or order_gubun == 'SELL_SHORT':
                        item.setForeground(color_fg_bt)
                    elif order_gubun == '매도':
                        item.setForeground(color_fg_dk)
                    elif '취소' in order_gubun or 'CANCEL' in order_gubun:
                        item.setForeground(color_fg_bc)

                elif gubun in self.uinums_hogatick and not self.ui.database_chart:
                    if column == '체결수량':
                        if i in (0, 11):
                            color = color_fg_bt if value > arry[11 if i == 0 else 0, 0] else color_fg_dk
                            item.setForeground(color)
                        else:
                            if self.ui.market_gubun < 6 or gubun == ui_num['호가체결']:
                                func = comma2int if gubun == ui_num['호가체결'] else comma2float
                                c = func(self.ui.hg_tableWidgett_01.item(5, columns_hg.index('호가')).text())
                                if value > 0:
                                    item.setForeground(color_fg_bt)
                                    if value * c > (90_000_000 if self.ui.market_gubun != 4 else 60_000):
                                        item.setBackground(color_bf_bt)
                                else:
                                    item.setForeground(color_fg_dk)
                                    if value * c < (-90_000_000 if self.ui.market_gubun != 4 else -60_000):
                                        item.setBackground(color_bf_dk)

                    elif column == '체결강도':
                        color = color_fg_bt if value >= 100 else color_fg_dk
                        item.setForeground(color)

                elif gubun in self.uinums_hogarem:
                    if column == '잔량':
                        if i in (0, 11):
                            color = color_fg_bt if value > arry[11 if i == 0 else 0, 0] else color_fg_dk
                            item.setForeground(color)
                        elif i < 11:
                            item.setForeground(color_fg_bt)
                        else:
                            item.setForeground(color_fg_dk)
                    elif column == '호가':
                        if column == '호가' and value != 0:
                            if self.ui.hj_tableWidgett_01.item(0, 0) is not None:
                                func = comma2int if gubun == ui_num['호가잔량'] and self.ui.market_gubun < 4 else comma2float
                                c    = func(self.ui.hj_tableWidgett_01.item(0, columns_hj.index('현재가')).text())
                                if i not in (0, 11) and value == c:
                                    item.setBackground(color_bf_bt)

                elif gubun in self.uinums_giup:
                    text = arry[i, 2]
                    warning = any(warn in text for warn in self.warning_text)
                    item.setForeground(color_fg_bt if warning else color_fg_dk)

                elif gubun in self.uinums_jemu:
                    color = color_fg_bt if '-' not in value else color_fg_dk
                    item.setForeground(color)

                tableWidget.setItem(i, j, item)

        if gubun in self.sorted_uinums:
            tableWidget.setSortingEnabled(True)

        row_min_cnt = self.dict_minrowcnt.get(gubun)
        if row_min_cnt and len_df < row_min_cnt:
            tableWidget.setRowCount(row_min_cnt)

        if gubun in self.col_auto_resize_uinums:
            header = tableWidget.horizontalHeader()
            hwidth = header.width() if gubun in self.uinums_detail1 else 668
            if gubun in self.uinums_detail1:
                header_count = 12
            elif columns_cnt in (9, 11):
                header_count = 7
            else:
                header_count = 8
            width = []
            for i in range(header_count):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
                width.append(header.sectionSize(i))
            wfactor = hwidth / sum(width)
            cumsum_width = 0
            last = header_count - 1
            for i in range(header_count):
                header.setSectionResizeMode(i, QHeaderView.Interactive)
                if i != last:
                    column_width = int(width[i] * wfactor)
                    header.resizeSection(i, column_width)
                    cumsum_width += column_width
                else:
                    column_width = hwidth - cumsum_width
                    header.resizeSection(i, column_width)

        elif gubun not in self.col_fixed_size_uinums:
            header = tableWidget.horizontalHeader()
            hwidth = header.width()
            header_count = header.count()
            width = []
            for i in range(header_count):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
                width.append(header.sectionSize(i))
            wfactor = hwidth / sum(width)
            cumsum_width = 0
            last = header_count - 1
            for i in range(header_count):
                header.setSectionResizeMode(i, QHeaderView.Interactive)
                if i != last:
                    column_width = int(width[i] * wfactor)
                    header.resizeSection(i, column_width)
                    cumsum_width += column_width
                else:
                    column_width = hwidth - cumsum_width
                    header.resizeSection(i, column_width)

    def tablewidget_change(self, gubun, tableWidget, columns_cnt, columns_list):
        """테이블 위젯 컬럼을 변경합니다.
        컬럼 수가 변경된 경우 컬럼을 재설정합니다.
        Args:
            gubun: 구분
            tableWidget: 테이블 위젯
            columns_cnt: 컬럼 수
            columns_list: 컬럼 리스트
        """
        if tableWidget.columnCount() != columns_cnt:
            tableWidget.setColumnCount(columns_cnt)
            tableWidget.setHorizontalHeaderLabels(columns_list)
            if gubun in self.uinums_detail2:
                if columns_cnt == 7:
                    tableWidget.setColumnWidth(0, 90)
                    tableWidget.setColumnWidth(1, 101)
                    tableWidget.setColumnWidth(2, 95)
                    tableWidget.setColumnWidth(3, 95)
                    tableWidget.setColumnWidth(4, 95)
                    tableWidget.setColumnWidth(5, 95)
                    tableWidget.setColumnWidth(6, 95)
                elif columns_cnt == 8:
                    tableWidget.setColumnWidth(0, 90)
                    tableWidget.setColumnWidth(1, 96)
                    tableWidget.setColumnWidth(2, 80)
                    tableWidget.setColumnWidth(3, 80)
                    tableWidget.setColumnWidth(4, 80)
                    tableWidget.setColumnWidth(5, 80)
                    tableWidget.setColumnWidth(6, 80)
                    tableWidget.setColumnWidth(7, 80)
            else:
                if columns_cnt == 8:
                    tableWidget.setColumnWidth(0, 96)
                    tableWidget.setColumnWidth(1, 90)
                    tableWidget.setColumnWidth(2, 90)
                    tableWidget.setColumnWidth(3, 90)
                    tableWidget.setColumnWidth(4, 140)
                    tableWidget.setColumnWidth(5, 70)
                    tableWidget.setColumnWidth(6, 90)
                    tableWidget.setColumnWidth(7, 90)
                elif columns_cnt == 12:
                    tableWidget.setColumnWidth(0, 96)
                    tableWidget.setColumnWidth(1, 70)
                    tableWidget.setColumnWidth(2, 115)
                    tableWidget.setColumnWidth(3, 115)
                    tableWidget.setColumnWidth(4, 90)
                    tableWidget.setColumnWidth(5, 90)
                    tableWidget.setColumnWidth(6, 90)
                    tableWidget.setColumnWidth(7, 90)
                    tableWidget.setColumnWidth(8, 90)
                    tableWidget.setColumnWidth(9, 90)
                    tableWidget.setColumnWidth(10, 90)
                    tableWidget.setColumnWidth(11, 90)

    def update_hogainfo_for_chart(self, ymdhms):
        """차트용 호가 정보를 업데이트합니다.
        차트에서 선택된 시점의 호가 정보를 표시합니다.
        Args:
            ymdhms: 연월일시분초
        """
        def fi(fname):
            return self.ui.dict_findex[fname]

        def setInfiniteLine():
            import pyqtgraph as pg
            vhline = pg.InfiniteLine()
            vhline.setPen(pg.mkPen(color_ct_hg, width=1))
            return vhline

        is_min = len(ymdhms) == 12
        if is_min:
            x = dt_ymdhms(f'{ymdhms}00').timestamp()
        else:
            x = dt_ymdhms(ymdhms).timestamp()
        try:
            xpoint = self.ui.ctpg_xticks.index(x)
        except Exception:
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

            self.ui.ctpg[0].addItem(vLine1)
            self.ui.ctpg[1].addItem(vLine2)
            self.ui.ctpg[2].addItem(vLine3)
            self.ui.ctpg[3].addItem(vLine4)
            self.ui.ctpg[4].addItem(vLine5)
            self.ui.ctpg[5].addItem(vLine6)
            self.ui.ctpg_hline = [vLine1, vLine2, vLine3, vLine4, vLine5, vLine6]
            if len(self.ui.ctpg) > 6:
                self.ui.ctpg[6].addItem(vLine7)
                self.ui.ctpg_hline += [vLine7]
            if len(self.ui.ctpg) > 7:
                self.ui.ctpg[7].addItem(vLine8)
                self.ui.ctpg_hline += [vLine8]
            if len(self.ui.ctpg) > 9:
                self.ui.ctpg[8].addItem(vLine9)
                self.ui.ctpg[9].addItem(vLine10)
                self.ui.ctpg_hline += [vLine9, vLine10]
            if len(self.ui.ctpg) > 12:
                self.ui.ctpg[10].addItem(vLine11)
                self.ui.ctpg[11].addItem(vLine12)
                self.ui.ctpg[12].addItem(vLine13)
                self.ui.ctpg_hline += [vLine11, vLine12, vLine13]

        for vline in self.ui.ctpg_hline:
            vline.setPos(x)

        ymd = ymdhms[:8]
        hms = ymdhms[8:]
        ymd_text = f'{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}'
        hms_text = f'{hms[:2]}:{hms[2:]}' if is_min else f'{hms[:2]}:{hms[2:4]}:{hms[4:]}'
        self.ui.hg_labellllllll_01.setText(f'{ymd_text} {hms_text}')

        data = []
        info = self.hoga_info1 if is_min else self.hoga_info2
        for col_name in info:
            data.append(self.ui.ctpg_arry[xpoint, fi(col_name)])
        df1 = pd.DataFrame({'체결수량': info, '체결강도': data})

        data = []
        info = self.hoga_info3 if is_min else self.hoga_info4
        for col_name in info:
            data.append(self.ui.ctpg_arry[xpoint, fi(col_name)])
        df2 = pd.DataFrame({'체결수량': info, '체결강도': data})

        self.ui.windowQ.put((ui_num['호가체결'], df1))
        self.ui.windowQ.put((ui_num['호가체결2'], df2))

        for i in range(len(self.ui.ctpg_legend)):
            self.ui.ctpg_legend[i].setText(get_label_text(self.ui, is_min, xpoint, self.ui.ctpg_factors[i], hms_text))
            self.ui.ctpg_labels[i].setText('')
