
import psutil
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QGroupBox, QLabel
from ui.event_click.button_clicked_backtest_start import *
from ui.event_change.changed_checkbox import checkbox_changed_06
from utility.static_method.static import str_hms, dt_hms, timedelta_sec
from ui.create_widget.set_style import style_ck_bx, style_pgbar, style_bc_dk
from ui.event_click.button_clicked_etc import change_back_sdate, change_back_edate
from ui.event_activate.activated_back import bactivated_01, bactivated_02, bactivated_03
from ui.event_change.changed_text import text_changed_01, text_changed_02, text_changed_03, text_changed_04


class SetDialogBack:
    """백테스트 다이얼로그 설정 클래스입니다.
    백테스트 엔진과 스케줄러 다이얼로그를 설정합니다.
    """
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def _create_widget_list(self, count, prefix, widget_type, parent, **kwargs):
        """위젯 리스트를 동적으로 생성하는 헬퍼 메서드
        Args:
            count: 생성할 위젯 개수
            prefix: 위젯명 접두사 (예: 'sd_gcomboBoxxxx')
            widget_type: 위젯 타입 ('combobox', 'dateedit', 'lineedit', 'checkbox')
            parent: 부모 위젯
            **kwargs: 위젯 생성에 필요한 추가 인자
        Returns:
            생성된 위젯 리스트
        """
        widgets = []
        for i in range(1, count + 1):
            widget_name = f'{prefix}_{i:02d}'
            if widget_type == 'combobox':
                widget = self.wc.setCombobox(parent, **kwargs)
            elif widget_type == 'dateedit':
                widget = self.wc.setDateEdit(parent, **kwargs)
            elif widget_type == 'lineedit':
                widget = self.wc.setLineedit(parent, **kwargs)
            elif widget_type == 'checkbox':
                widget = self.wc.setCheckBox(kwargs.get('text', ''), parent, **{k: v for k, v in kwargs.items() if k != 'text'})
            elif widget_type == 'progressbar':
                widget = self.wc.setProgressBar(parent, **kwargs)
            else:
                continue
            setattr(self.ui, widget_name, widget)
            widgets.append(widget)
        return widgets

    def set(self):
        """백테스트 다이얼로그를 설정합니다."""
        self.ui.dialog_backengine = self.wc.setDialog('STOM BACKTEST ENGINE')
        self.ui.dialog_backengine.geometry().center()
        self.ui.dialog_list.append(self.ui.dialog_backengine)

        self.ui.be_groupBoxxxxx_01 = QGroupBox('', self.ui.dialog_backengine)
        self.ui.be_labellllllll_04 = QLabel('▣ 백테엔진의 데이터 로딩 시 분류 방법을 선택하십시오. 한종목 백테 시 우측 콤보박스 선택', self.ui.be_groupBoxxxxx_01)
        self.ui.be_comboBoxxxxx_01 = self.wc.setCombobox(self.ui.be_groupBoxxxxx_01, items=['종목코드별 분류', '일자별 분류', '한종목 로딩'])
        self.ui.be_comboBoxxxxx_02 = self.wc.setCombobox(self.ui.be_groupBoxxxxx_01, items=['데이터없음'])
        self.ui.be_labellllllll_01 = QLabel('▣ 백테엔진에 로딩할 데이터의 시작 및 종료 날짜와 시간를 입력하십시오.', self.ui.be_groupBoxxxxx_01)
        if self.ui.dict_set is not None:
            if self.ui.dict_set['백테날짜고정']:
                self.ui.be_dateEdittttt_01 = self.wc.setDateEdit(self.ui.be_groupBoxxxxx_01, qday=QDate.fromString(self.ui.dict_set['백테날짜'], 'yyyyMMdd'))
            else:
                self.ui.be_dateEdittttt_01 = self.wc.setDateEdit(self.ui.be_groupBoxxxxx_01, addday=-int(self.ui.dict_set['백테날짜']))
        else:
            self.ui.be_dateEdittttt_01 = self.wc.setDateEdit(self.ui.be_groupBoxxxxx_01)
        self.ui.be_dateEdittttt_02 = self.wc.setDateEdit(self.ui.be_groupBoxxxxx_01)
        self.ui.be_lineEdittttt_01 = self.wc.setLineedit(self.ui.be_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.be_lineEdittttt_02 = self.wc.setLineedit(self.ui.be_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.be_labellllllll_02 = QLabel('▣ 사용할 평균값틱수를 콤머로 구분입력하고 백테엔진의 멀티수를 입력하십시오.', self.ui.be_groupBoxxxxx_01)
        self.ui.be_lineEdittttt_03 = self.wc.setLineedit(self.ui.be_groupBoxxxxx_01, ltext='30', style=style_bc_dk, tip='예제: 30, 60, 90, 120')
        tip = '논리프로세스 개수의 1.5배 정도가 최고성능\n안정적인 개수는 논리프로세스 개수만큼 설정(기본)\n여유있는 개수는 논리프로세스 개수 나누기 2만큼 설정'
        self.ui.be_lineEdittttt_04 = self.wc.setLineedit(self.ui.be_groupBoxxxxx_01, ltext=f'{psutil.cpu_count()}', style=style_bc_dk, tip=tip)
        text = '▣ 백테엔진을 시작하면 20개의 중간집계용, 멀티수만큼의 백테엔진용 프로세스가 실행되고\n\n' \
               '설정탭 기타에서 설정한 일괄로딩 또는 분할로딩의 선택에 따라 공유메모리 또는 피클덤프의\n\n' \
               '형태로 데이터를 로드합니다. 백테엔진은 프로그램을 종료하기 전까지 종료되지 않습니다.'
        self.ui.be_labellllllll_03 = QLabel(text, self.ui.be_groupBoxxxxx_01)
        self.ui.be_pushButtonnn_01 = self.wc.setPushbutton('백테스트 엔진 시작', parent=self.ui.be_groupBoxxxxx_01, click=lambda: bebutton_clicked_01(self.ui))
        self.ui.be_textEditxxxx_01 = self.wc.setTextEdit(self.ui.be_groupBoxxxxx_01, vscroll=True)

        self.ui.dialog_scheduler = self.wc.setDialog('STOM BACKTEST SCHEDULER')
        self.ui.dialog_scheduler.geometry().center()
        self.ui.dialog_list.append(self.ui.dialog_scheduler)

        self.ui.sd_groupBoxxxxx_01 = QGroupBox('', self.ui.dialog_scheduler)
        self.ui.sd_groupBoxxxxx_02 = QGroupBox('', self.ui.dialog_scheduler)

        self.ui.sd_labellllllll_00 = QLabel('▣ 매수조건수                     매도조건수                    최적화횟수', self.ui.sd_groupBoxxxxx_01)
        self.ui.sd_oclineEdittt_01 = self.wc.setLineedit(self.ui.sd_groupBoxxxxx_01, ltext='10', style=style_bc_dk)
        self.ui.sd_oclineEdittt_02 = self.wc.setLineedit(self.ui.sd_groupBoxxxxx_01, ltext='5', style=style_bc_dk)
        self.ui.sd_oclineEdittt_03 = self.wc.setLineedit(self.ui.sd_groupBoxxxxx_01, ltext='1000', style=style_bc_dk)
        tip = '일괄변경 체크 시 같은 열의 모든 값이 동시에 변경됩니다.'
        self.ui.sd_scheckBoxxxx_01 = self.wc.setCheckBox('일괄변경', self.ui.sd_groupBoxxxxx_01, checked=True, style=style_ck_bx, tip=tip)
        self.ui.sd_scheckBoxxxx_02 = self.wc.setCheckBox('완료 후 컴퓨터 종료', self.ui.sd_groupBoxxxxx_01, style=style_ck_bx)

        self.ui.sd_dcomboBoxxxx_01 = self.wc.setCombobox(self.ui.sd_groupBoxxxxx_01, activated=lambda: bactivated_03(self.ui))
        self.ui.sd_dpushButtonn_01 = self.wc.setPushbutton('스케쥴 로딩', parent=self.ui.sd_groupBoxxxxx_01, click=lambda: sdbutton_clicked_04(self.ui))
        self.ui.sd_dlineEditttt_01 = self.wc.setLineedit(self.ui.sd_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.sd_dpushButtonn_02 = self.wc.setPushbutton('스케쥴 저장', parent=self.ui.sd_groupBoxxxxx_01, click=lambda: sdbutton_clicked_05(self.ui))

        self.ui.sd_pushButtonnn_01 = self.wc.setPushbutton('시작', parent=self.ui.sd_groupBoxxxxx_01, color=2, click=lambda: sdbutton_clicked_02(self.ui))
        self.ui.sd_pushButtonnn_02 = self.wc.setPushbutton('중지', parent=self.ui.sd_groupBoxxxxx_01, color=2, click=lambda: sdbutton_clicked_03(self.ui))

        text = '                           백테유형                           시작일자                   ' \
               '종료일자               시작시간      종료시간     배팅    틱수      ' \
               '학습         검증         확인          횟수      최적화기준                  매수                                 ' \
               '매도                                   범위                                         상태'
        self.ui.sd_labellllllll_01 = QLabel(text, self.ui.sd_groupBoxxxxx_02)

        self.ui.list_checkBoxxxxxx = self._create_widget_list(
            16, 'sd_checkBoxxxxx', 'checkbox', self.ui.sd_groupBoxxxxx_02, text='    ', changed=lambda state: checkbox_changed_06(self.ui, state), style=style_ck_bx
        )

        self.ui.list_gcomboBoxxxxx = self._create_widget_list(
            16, 'sd_gcomboBoxxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_01(self.ui)
        )

        if self.ui.dict_set is not None:
            if self.ui.dict_set['백테날짜고정']:
                sdate_kwargs = {'qday': QDate.fromString(self.ui.dict_set['백테날짜'], 'yyyyMMdd'), 'changed': lambda: change_back_sdate(self.ui)}
            else:
                sdate_kwargs = {'addday': -int(self.ui.dict_set['백테날짜']), 'changed': lambda: change_back_sdate(self.ui)}
        else:
            sdate_kwargs = {'changed': lambda: change_back_sdate(self.ui)}

        self.ui.list_sdateEdittttt = self._create_widget_list(
            16, 'sd_sdateEditttt', 'dateedit', self.ui.sd_groupBoxxxxx_02, **sdate_kwargs
        )

        self.ui.list_edateEdittttt = self._create_widget_list(
            16, 'sd_edateEditttt', 'dateedit', self.ui.sd_groupBoxxxxx_02, changed=lambda: change_back_edate(self.ui)
        )

        if self.ui.dict_set is not None:
            starttime = str(self.ui.market_info['시작시간']).zfill(6)
            endtime   = str_hms(timedelta_sec(-120, dt_hms(str(self.ui.dict_set['전략종료시간'])))).zfill(6)
        else:
            starttime = '090000'
            endtime   = '093000'

        self.ui.list_slineEdittttt = self._create_widget_list(
            16, 'sd_slineEditttt', 'lineedit', self.ui.sd_groupBoxxxxx_02, ltext=starttime, style=style_bc_dk, change=lambda: text_changed_01(self.ui)
        )

        self.ui.list_elineEdittttt = self._create_widget_list(
            16, 'sd_elineEditttt', 'lineedit', self.ui.sd_groupBoxxxxx_02, ltext=endtime, style=style_bc_dk, change=lambda: text_changed_02(self.ui)
        )

        self.ui.list_blineEdittttt = self._create_widget_list(
            16, 'sd_blineEditttt', 'lineedit', self.ui.sd_groupBoxxxxx_02, ltext='20', style=style_bc_dk, change=lambda: text_changed_03(self.ui)
        )

        self.ui.list_alineEdittttt = self._create_widget_list(
            16, 'sd_alineEditttt', 'lineedit', self.ui.sd_groupBoxxxxx_02, ltext='30', style=style_bc_dk, change=lambda: text_changed_04(self.ui)
        )

        self.ui.list_p1comboBoxxxx = self._create_widget_list(
            16, 'sd_p1comboBoxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_p2comboBoxxxx = self._create_widget_list(
            16, 'sd_p2comboBoxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_p3comboBoxxxx = self._create_widget_list(
            16, 'sd_p3comboBoxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_p4comboBoxxxx = self._create_widget_list(
            16, 'sd_p4comboBoxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_tcomboBoxxxxx = self._create_widget_list(
            16, 'sd_tcomboBoxxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_bcomboBoxxxxx = self._create_widget_list(
            16, 'sd_bcomboBoxxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_scomboBoxxxxx = self._create_widget_list(
            16, 'sd_scomboBoxxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_vcomboBoxxxxx = self._create_widget_list(
            16, 'sd_vcomboBoxxxx', 'combobox', self.ui.sd_groupBoxxxxx_02, hover=False, activated=lambda: bactivated_02(self.ui)
        )

        self.ui.list_progressBarrr = self._create_widget_list(
            16, 'sd_progressBarr', 'progressbar', self.ui.sd_groupBoxxxxx_02, style=style_pgbar
        )

        self.ui.dialog_backengine.setFixedSize(480, 600)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_backengine.move(self.ui.dict_set['창위치'][16], self.ui.dict_set['창위치'][17])
            except Exception:
                pass
        self.ui.be_groupBoxxxxx_01.setGeometry(5, 5, 470, 590)
        self.ui.be_labellllllll_04.setGeometry(10, 5, 450, 30)
        self.ui.be_comboBoxxxxx_01.setGeometry(15, 40, 220, 30)
        self.ui.be_comboBoxxxxx_02.setGeometry(245, 40, 220, 30)
        self.ui.be_labellllllll_01.setGeometry(10, 70, 450, 30)
        self.ui.be_dateEdittttt_01.setGeometry(10, 105, 220, 30)
        self.ui.be_dateEdittttt_02.setGeometry(240, 105, 220, 30)
        self.ui.be_lineEdittttt_01.setGeometry(10, 140, 220, 30)
        self.ui.be_lineEdittttt_02.setGeometry(240, 140, 220, 30)
        self.ui.be_labellllllll_02.setGeometry(10, 175, 450, 30)
        self.ui.be_lineEdittttt_03.setGeometry(10, 210, 220, 30)
        self.ui.be_lineEdittttt_04.setGeometry(240, 210, 220, 30)
        self.ui.be_labellllllll_03.setGeometry(10, 245, 450, 80)
        self.ui.be_pushButtonnn_01.setGeometry(10, 335, 450, 30)
        self.ui.be_textEditxxxx_01.setGeometry(10, 375, 450, 205)

        self.ui.dialog_scheduler.setFixedSize(1403, 575)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_scheduler.move(self.ui.dict_set['창위치'][4], self.ui.dict_set['창위치'][5])
            except Exception:
                pass
        self.ui.sd_groupBoxxxxx_01.setGeometry(5, 5, 1390, 40)
        self.ui.sd_groupBoxxxxx_02.setGeometry(5, 50, 1390, 520)

        self.ui.sd_labellllllll_00.setGeometry(10, 7, 400, 30)
        self.ui.sd_oclineEdittt_01.setGeometry(85, 12, 45, 20)
        self.ui.sd_oclineEdittt_02.setGeometry(205, 12, 45, 20)
        self.ui.sd_oclineEdittt_03.setGeometry(320, 12, 45, 20)
        self.ui.sd_scheckBoxxxx_01.setGeometry(410, 7, 70, 30)
        self.ui.sd_scheckBoxxxx_02.setGeometry(490, 7, 120, 30)

        self.ui.sd_dcomboBoxxxx_01.setGeometry(620, 7, 140, 30)
        self.ui.sd_dpushButtonn_01.setGeometry(770, 7, 80, 30)
        self.ui.sd_dlineEditttt_01.setGeometry(860, 7, 140, 30)
        self.ui.sd_dpushButtonn_02.setGeometry(1010, 7, 80, 30)

        self.ui.sd_pushButtonnn_01.setGeometry(1198, 7, 89, 30)
        self.ui.sd_pushButtonnn_02.setGeometry(1297, 7, 89, 30)

        self.ui.sd_labellllllll_01.setGeometry(10, 8, 1380, 30)

        def set_geometry(widgets, x1, y1, x2, y2):
            for i, widget in enumerate(widgets):
                change_y = y1 + i * 30
                widget.setGeometry(x1, change_y, x2, y2)

        set_geometry(self.ui.list_checkBoxxxxxx, 10, 40, 40, 25)
        set_geometry(self.ui.list_gcomboBoxxxxx, 35, 40, 160, 25)
        set_geometry(self.ui.list_sdateEdittttt, 200, 40, 95, 25)
        set_geometry(self.ui.list_edateEdittttt, 300, 40, 95, 25)
        set_geometry(self.ui.list_slineEdittttt, 400, 40, 55, 25)
        set_geometry(self.ui.list_elineEdittttt, 460, 40, 55, 25)
        set_geometry(self.ui.list_blineEdittttt, 520, 40, 30, 25)
        set_geometry(self.ui.list_alineEdittttt, 555, 40, 30, 25)
        set_geometry(self.ui.list_p1comboBoxxxx, 590, 40, 45, 25)
        set_geometry(self.ui.list_p2comboBoxxxx, 640, 40, 45, 25)
        set_geometry(self.ui.list_p3comboBoxxxx, 690, 40, 45, 25)
        set_geometry(self.ui.list_p4comboBoxxxx, 740, 40, 45, 25)
        set_geometry(self.ui.list_tcomboBoxxxxx, 790, 40, 55, 25)
        set_geometry(self.ui.list_bcomboBoxxxxx, 850, 40, 120, 25)
        set_geometry(self.ui.list_scomboBoxxxxx, 975, 40, 120, 25)
        set_geometry(self.ui.list_vcomboBoxxxxx, 1100, 40, 120, 25)
        set_geometry(self.ui.list_progressBarrr, 1225, 40, 160, 25)
