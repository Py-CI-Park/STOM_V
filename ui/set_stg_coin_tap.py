
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QLabel
from utility.setting_base import columns_bt
from ui.ui_button_clicked_editer_coin import *
from ui.ui_button_clicked_editer_ga_coin import *
from ui.ui_button_clicked_editer_backlog import *
from ui.ui_button_clicked_editer_opti_coin import *
from ui.ui_button_clicked_editer_stg_buy_coin import *
from ui.ui_button_clicked_editer_stg_sell_coin import *
from ui.ui_cell_clicked import cell_clicked_06
from ui import ui_activated_stg, ui_activated_etc
from utility.static import str_hms, dt_hms, timedelta_sec
from ui.ui_strategy_version import dactivated_04, strategy_version_delete
from ui.set_style import qfont12, qfont13, qfont14, style_pgbar, style_bc_dk
from ui.ui_button_clicked_zoom import cz_button_clicked_01, cz_button_clicked_02
from ui.ui_button_clicked_strategy import button_clicked_strategy, strategy_custom_button_show
from ui.set_text import optistandard, optitext, train_period, valid_period, test_period, optimized_count, opti_standard


class SetCoinBack:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    @error_decorator
    def set(self):
        self.ui.cs_textEditttt_01 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, filter_=True, font=qfont14)
        self.ui.cs_textEditttt_02 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, filter_=True, font=qfont14)
        self.ui.cs_textEditttt_03 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, visible=False, filter_=True, font=qfont14)
        self.ui.cs_textEditttt_04 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, visible=False, filter_=True, font=qfont14)
        self.ui.cs_textEditttt_05 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, visible=False, filter_=True, font=qfont14)
        self.ui.cs_textEditttt_06 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, visible=False, filter_=True, font=qfont14)
        self.ui.cs_textEditttt_07 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, visible=False, filter_=True, font=qfont14)
        self.ui.cs_textEditttt_08 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, visible=False, filter_=True, font=qfont14)

    # =================================================================================================================

        self.ui.czoo_pushButon_01 = self.wc.setPushbutton('확대(esc)', parent=self.ui.cs_tab, bounced=True, click=lambda: cz_button_clicked_01(self.ui))
        self.ui.czoo_pushButon_02 = self.wc.setPushbutton('확대(esc)', parent=self.ui.cs_tab, bounced=True, click=lambda: cz_button_clicked_02(self.ui))

        self.ui.coin_esczom_list  = [self.ui.czoo_pushButon_01, self.ui.czoo_pushButon_02]

    # =================================================================================================================

        self.ui.cs_textEditttt_10 = self.wc.setTextEdit(self.ui.cs_tab, vscroll=True, visible=False, filter_=True, event_filter=False, font=qfont14)
        self.ui.cs_comboBoxxxx_41 = self.wc.setCombobox(self.ui.cs_tab, font=qfont12, activated=lambda: dactivated_04(self.ui))
        self.ui.cs_comboBoxxxx_42 = self.wc.setCombobox(self.ui.cs_tab, font=qfont12, activated=lambda: dactivated_04(self.ui))
        self.ui.cs_pushButtonn_41 = self.wc.setPushbutton('버전삭제', parent=self.ui.cs_tab, bounced=True, click=lambda: strategy_version_delete(self.ui), tip='선택된 버전의 데이터를 삭제합니다.')

        self.ui.coin_version_list = [
            self.ui.cs_textEditttt_10, self.ui.cs_comboBoxxxx_41, self.ui.cs_comboBoxxxx_42, self.ui.cs_pushButtonn_41
        ]

        for widget in self.ui.coin_version_list:
            widget.setVisible(False)

    # =================================================================================================================

        self.ui.cs_tableWidget_01 = self.wc.setTablewidget(self.ui.cs_tab, columns_bt, 32, vscroll=True, fixed=True, clicked=lambda row, col: cell_clicked_06(self.ui, row, col))
        self.ui.cs_comboBoxxxx_01 = self.wc.setCombobox(self.ui.cs_tab, font=qfont12, activated=lambda: ui_activated_etc.dactivated_01(self.ui))
        self.ui.cs_pushButtonn_01 = self.wc.setPushbutton('백테스트상세기록', parent=self.ui.cs_tab, bounced=True, click=lambda: csbutton_clicked_01(self.ui), tip='백테스트 상세기록을 불러온다.')
        self.ui.cs_pushButtonn_02 = self.wc.setPushbutton('그래프', parent=self.ui.cs_tab, bounced=True, click=lambda: csbutton_clicked_04(self.ui), tip='선택된 상세기록의 그래프를 표시한다.')
        self.ui.cs_comboBoxxxx_02 = self.wc.setCombobox(self.ui.cs_tab, font=qfont12, activated=lambda: ui_activated_etc.dactivated_01(self.ui))
        self.ui.cs_pushButtonn_03 = self.wc.setPushbutton('최적화상세기록', parent=self.ui.cs_tab, bounced=True, click=lambda: csbutton_clicked_02(self.ui), tip='최적화 상세기록을 불러온다.')
        self.ui.cs_pushButtonn_04 = self.wc.setPushbutton('그래프', parent=self.ui.cs_tab, bounced=True, click=lambda: csbutton_clicked_04(self.ui), tip='선택된 상세기록의 그래프를 표시한다.')
        self.ui.cs_comboBoxxxx_03 = self.wc.setCombobox(self.ui.cs_tab, font=qfont12, activated=lambda: ui_activated_etc.dactivated_01(self.ui))
        self.ui.cs_pushButtonn_05 = self.wc.setPushbutton('분석상세기록', parent=self.ui.cs_tab, bounced=True, click=lambda: csbutton_clicked_03(self.ui), tip='최적화 테스트 및 전진분석 상세기록을 불러온다.')
        self.ui.cs_pushButtonn_06 = self.wc.setPushbutton('그래프', parent=self.ui.cs_tab, bounced=True, click=lambda: csbutton_clicked_04(self.ui), tip='선택된 상세기록의 그래프를 표시한다.')
        self.ui.cs_pushButtonn_07 = self.wc.setPushbutton('비교', parent=self.ui.cs_tab, bounced=True, color=4, click=lambda: csbutton_clicked_05(self.ui), tip='두개 이상의 그래프를 선택 비교한다.')

        self.ui.coin_detail_list  = [
            self.ui.cs_tableWidget_01, self.ui.cs_comboBoxxxx_01, self.ui.cs_pushButtonn_01, self.ui.cs_pushButtonn_02,
            self.ui.cs_comboBoxxxx_02, self.ui.cs_pushButtonn_03, self.ui.cs_pushButtonn_04, self.ui.cs_comboBoxxxx_03,
            self.ui.cs_pushButtonn_05, self.ui.cs_pushButtonn_06, self.ui.cs_pushButtonn_07
        ]

        for widget in self.ui.coin_detail_list:
            widget.setVisible(False)

    # =================================================================================================================

        self.ui.cs_textEditttt_09 = self.wc.setTextEdit(self.ui.cs_tab, visible=False, vscroll=True)
        self.ui.cs_progressBar_01 = self.wc.setProgressBar(self.ui.cs_tab, style=style_pgbar, visible=False)
        self.ui.cs_pushButtonn_08 = self.wc.setPushbutton('백테스트 중지', parent=self.ui.cs_tab, bounced=True, click=lambda: csbutton_clicked_06(self.ui), color=2, visible=False, tip='(Alt+Enter) 실행중인 백테스트를 중지한다.')

        self.ui.coin_baklog_list  = [self.ui.cs_textEditttt_09, self.ui.cs_progressBar_01, self.ui.cs_pushButtonn_08]

    # =================================================================================================================

        self.ui.cvjb_comboBoxx_01 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_01(self.ui, 'coin'))
        self.ui.cvjb_lineEditt_01 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F2, F3', style=style_bc_dk)
        self.ui.cvjb_pushButon_01 = self.wc.setPushbutton('매수전략 로딩(F1)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_buy_stg_load(self.ui), color=1, tip='작성된 매수전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cvjb_pushButon_02 = self.wc.setPushbutton('매수전략 저장(F4)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_buy_stg_save(self.ui), color=1, tip='작성된 매수전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')
        self.ui.cvjb_pushButon_03 = self.wc.setPushbutton('매수변수 로딩', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_buy_factor(self.ui), color=1, tip='매수전략에 사용할 수 있는 변수목록을 불러온다.')
        self.ui.cvjb_pushButon_04 = self.wc.setPushbutton('매수전략 시작', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_buy_stg_start(self.ui), color=1, tip='작성한 전략을 저장 후 콤보박스에서 선택해야 적용된다.')
        self.ui.cvjb_pushButon_05 = self.wc.setPushbutton('등락율제한', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 220))
        self.ui.cvjb_pushButon_06 = self.wc.setPushbutton('고저평균등락율', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 211))
        self.ui.cvjb_pushButon_07 = self.wc.setPushbutton('현재가시가비교', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 222))
        self.ui.cvjb_pushButon_08 = self.wc.setPushbutton('체결강도하한', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 223))
        self.ui.cvjb_pushButon_09 = self.wc.setPushbutton('체결강도평균차이', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 224))
        self.ui.cvjb_pushButon_10 = self.wc.setPushbutton('최고체결강도', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 225))
        self.ui.cvjb_pushButon_11 = self.wc.setPushbutton('매수시그널', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_buy_signal_insert(self.ui), color=3)
        self.ui.cvjb_pushButon_12 = self.wc.setPushbutton('매수전략 중지', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_buy_stg_stop(self.ui), color=1, tip='실행중인 매수전략을 중지한다.')

        self.ui.cvj_pushButton_01 = self.wc.setPushbutton('백테스트', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_backtest_start(self.ui), color=2, tip='(Alt+Enter) 기본전략을 백테스팅한다.\nCtrl키와 함께 누르면 백테스트 엔진을 재시작할 수 있습니다.\nCtrl + Alt 키와 함계 누르면 백테 완료 후 변수목록이 포함된 그래프가 저장됩니다.')
        self.ui.cvj_pushButton_02 = self.wc.setPushbutton('백파인더', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_backfinder_start(self.ui), color=2, tip='구간등락율을 기준으로 변수를 탐색한다.')
        self.ui.cvj_pushButton_03 = self.wc.setPushbutton('백파인더 예제', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_backfinder_sample(self.ui), color=3)
        self.ui.cvj_pushButton_04 = self.wc.setPushbutton('전략모듈', parent=self.ui.cs_tab, bounced=True, click=lambda: strategy_custom_button_show(self.ui), color=3)

        self.ui.cvjs_comboBoxx_01 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_02(self.ui, 'coin'))
        self.ui.cvjs_lineEditt_01 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F6, F7', style=style_bc_dk)
        self.ui.cvjs_pushButon_01 = self.wc.setPushbutton('매도전략 로딩(F5)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_sell_stg_load(self.ui), color=1, tip='작성된 매도전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cvjs_pushButon_02 = self.wc.setPushbutton('매도전략 저장(F8)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_sell_stg_save(self.ui), color=1, tip='작성된 매도전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')
        self.ui.cvjs_pushButon_03 = self.wc.setPushbutton('매도변수 로딩', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_sell_factor(self.ui), color=1, tip='매도전략에 사용할 수 있는 변수목록을 불러온다.')
        self.ui.cvjs_pushButon_04 = self.wc.setPushbutton('매도전략 시작', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_sell_stg_start(self.ui), color=1, tip='작성한 전략을 저장 후 콤보박스에서 선택해야 적용된다.')
        self.ui.cvjs_pushButon_05 = self.wc.setPushbutton('손절라인청산', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 226))
        self.ui.cvjs_pushButon_06 = self.wc.setPushbutton('익절라인청산', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 227))
        self.ui.cvjs_pushButon_07 = self.wc.setPushbutton('수익률보존청산', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 228))
        self.ui.cvjs_pushButon_08 = self.wc.setPushbutton('보유시간기준청산', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 229))
        self.ui.cvjs_pushButon_09 = self.wc.setPushbutton('체결강도평균비교', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 230))
        self.ui.cvjs_pushButon_10 = self.wc.setPushbutton('최고체결강도비교', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 231))
        self.ui.cvjs_pushButon_11 = self.wc.setPushbutton('고저평균등락율', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 232))
        self.ui.cvjs_pushButon_12 = self.wc.setPushbutton('호가총잔량비교', parent=self.ui.cs_tab, bounced=True, click=lambda: button_clicked_strategy(self.ui, 233))
        self.ui.cvjs_pushButon_13 = self.wc.setPushbutton('매도시그널', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_sell_signal_insert(self.ui), color=3)
        self.ui.cvjs_pushButon_14 = self.wc.setPushbutton('매도전략 중지', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_sell_stg_stop(self.ui), color=1, tip='실행중인 매도전략을 당장 중지한다.')

        self.ui.coin_backte_list  = [
            self.ui.cvjb_comboBoxx_01, self.ui.cvjb_lineEditt_01, self.ui.cvjb_pushButon_01, self.ui.cvjb_pushButon_02,
            self.ui.cvjb_pushButon_03, self.ui.cvjb_pushButon_04, self.ui.cvjb_pushButon_05, self.ui.cvjb_pushButon_06,
            self.ui.cvjb_pushButon_07, self.ui.cvjb_pushButon_08, self.ui.cvjb_pushButon_09, self.ui.cvjb_pushButon_10,
            self.ui.cvjb_pushButon_11, self.ui.cvjb_pushButon_12, self.ui.cvj_pushButton_01, self.ui.cvj_pushButton_02,
            self.ui.cvj_pushButton_03, self.ui.cvjs_comboBoxx_01, self.ui.cvjs_lineEditt_01, self.ui.cvj_pushButton_04,
            self.ui.cvjs_pushButon_01, self.ui.cvjs_pushButon_02, self.ui.cvjs_pushButon_03, self.ui.cvjs_pushButon_04,
            self.ui.cvjs_pushButon_05, self.ui.cvjs_pushButon_06, self.ui.cvjs_pushButon_07, self.ui.cvjs_pushButon_08,
            self.ui.cvjs_pushButon_09, self.ui.cvjs_pushButon_10, self.ui.cvjs_pushButon_11, self.ui.cvjs_pushButon_12,
            self.ui.cvjs_pushButon_13, self.ui.cvjs_pushButon_14
        ]

    # =================================================================================================================

        self.ui.cvjb_labelllll_01 = QLabel('백테스트 기간설정                                         ~', self.ui.cs_tab)
        self.ui.cvjb_labelllll_02 = QLabel('백테스트 시간설정     시작시간                         종료시간', self.ui.cs_tab)
        self.ui.cvjb_labelllll_03 = QLabel('백테스트 기본설정   배팅(백만)                        평균틱수   self.vars[0]', self.ui.cs_tab)
        if self.ui.dict_set is not None:
            if self.ui.dict_set['백테날짜고정']:
                self.ui.cvjb_dateEditt_01 = self.wc.setDateEdit(self.ui.cs_tab, qday=QDate.fromString(self.ui.dict_set['백테날짜'], 'yyyyMMdd'))
            else:
                self.ui.cvjb_dateEditt_01 = self.wc.setDateEdit(self.ui.cs_tab, addday=-int(self.ui.dict_set['백테날짜']))
        else:
            self.ui.cvjb_dateEditt_01 = self.wc.setDateEdit(self.ui.ss_tab)
        self.ui.cvjb_dateEditt_02 = self.wc.setDateEdit(self.ui.cs_tab)

        if self.ui.dict_set is not None:
            endtime = str_hms(timedelta_sec(-120, dt_hms(str(self.ui.dict_set['코인전략종료시간'])))).zfill(6)
            tujagm  = str(self.ui.dict_set['코인투자금'])
        else:
            endtime = '235000'
            tujagm  = '20.0'

        self.ui.cvjb_lineEditt_02 = self.wc.setLineedit(self.ui.cs_tab, ltext='000000', style=style_bc_dk)
        self.ui.cvjb_lineEditt_03 = self.wc.setLineedit(self.ui.cs_tab, ltext=endtime, style=style_bc_dk)
        self.ui.cvjb_lineEditt_04 = self.wc.setLineedit(self.ui.cs_tab, ltext=tujagm, style=style_bc_dk)
        self.ui.cvjb_lineEditt_05 = self.wc.setLineedit(self.ui.cs_tab, ltext='30', style=style_bc_dk)

        self.ui.coin_datedt_list  = [self.ui.cvjb_labelllll_01, self.ui.cvjb_dateEditt_01, self.ui.cvjb_dateEditt_02, self.ui.cvjb_lineEditt_05]

    # =================================================================================================================

        self.ui.cvj_pushButton_09 = self.wc.setPushbutton('전략 편집기', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_stg_editer(self.ui), color=5, tip='단축키(Alt+1)')
        self.ui.cvj_pushButton_08 = self.wc.setPushbutton('최적화 편집기', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_editer(self.ui), color=4, tip='단축키(Alt+2)')
        self.ui.cvj_pushButton_07 = self.wc.setPushbutton('테스트 편집기', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_test_editer(self.ui), color=4, tip='단축키(Alt+3)')
        self.ui.cvj_pushButton_06 = self.wc.setPushbutton('전진분석', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_rwf_test_editer(self.ui), color=4, tip='단축키(Alt+4)')
        self.ui.cvj_pushButton_10 = self.wc.setPushbutton('GA 편집기', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_ga_editer(self.ui), color=4, tip='단축키(Alt+5)')
        self.ui.cvj_pushButton_11 = self.wc.setPushbutton('조건 편집기', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_cond_editer(self.ui), color=4, tip='단축키(Alt+6)')
        self.ui.cvj_pushButton_12 = self.wc.setPushbutton('범위 편집기', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_vars_editer(self.ui), color=4, tip='단축키(Alt+7)')
        self.ui.cvj_pushButton_13 = self.wc.setPushbutton('변수 편집기', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_vars_editer(self.ui), color=4, tip='단축키(Alt+8)')
        self.ui.cvj_pushButton_14 = self.wc.setPushbutton('백테스트 로그', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_backtest_log(self.ui), color=4, tip='단축키(Alt+9)')
        self.ui.cvj_pushButton_15 = self.wc.setPushbutton('상세기록', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_backtest_detail(self.ui), color=4, tip='단축키(Alt+0)')

        self.ui.coin_editer_list = [
            self.ui.cvj_pushButton_06, self.ui.cvj_pushButton_07, self.ui.cvj_pushButton_08, self.ui.cvj_pushButton_09,
            self.ui.cvj_pushButton_10, self.ui.cvj_pushButton_11, self.ui.cvj_pushButton_12, self.ui.cvj_pushButton_13,
            self.ui.cvj_pushButton_14, self.ui.cvj_pushButton_15
        ]

    # =================================================================================================================

        self.ui.cvc_comboBoxxx_01 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_03(self.ui, 'coin'))
        self.ui.cvc_lineEdittt_01 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F2, F3', style=style_bc_dk)
        self.ui.cvc_pushButton_01 = self.wc.setPushbutton('최적화 매수전략 로딩(F1)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_buy_load(self.ui), color=1, tip='작성된 최적화 매수전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cvc_pushButton_02 = self.wc.setPushbutton('최적화 매수전략 저장(F4)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_buy_save(self.ui), color=1, tip='작성된 최적화 매수전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')

        self.ui.cvc_comboBoxxx_02 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_04(self.ui, 'coin'))
        self.ui.cvc_lineEdittt_02 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F10, F11', style=style_bc_dk)
        self.ui.cvc_pushButton_03 = self.wc.setPushbutton('최적화 변수범위 로딩(F9)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_vars_load(self.ui), color=1, tip='작성된 최적화 변수설정을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cvc_pushButton_04 = self.wc.setPushbutton('최적화 변수범위 저장(F12)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_vars_save(self.ui), color=1, tip='작성된 최적화 변수설정을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')

        self.ui.cvc_labellllll_01 = QLabel('▣ 일반은 학습기간, 검증은 검증기간, 테스트는 확인기간까지 선택', self.ui.cs_tab)
        self.ui.cvc_labellllll_02 = QLabel('최적화 학습기간                   검증기간                   확인기간', self.ui.cs_tab)
        self.ui.cvc_labellllll_02.setToolTip('모든 기간은 주단위로 입력하십시오.')
        self.ui.cvc_comboBoxxx_03 = self.wc.setCombobox(self.ui.cs_tab, items=train_period)
        self.ui.cvc_comboBoxxx_04 = self.wc.setCombobox(self.ui.cs_tab, items=valid_period)
        self.ui.cvc_comboBoxxx_05 = self.wc.setCombobox(self.ui.cs_tab, items=test_period)
        self.ui.cvc_labellllll_03 = QLabel('최적화 실행횟수                   기준값', self.ui.cs_tab)
        self.ui.cvc_labellllll_03.setToolTip(f'최적화 횟수 0선택 시 최적값이 변하지 않을 때까지 반복됩니다.\n{optistandard}')
        self.ui.cvc_comboBoxxx_06 = self.wc.setCombobox(self.ui.cs_tab, items=optimized_count)
        self.ui.cvc_comboBoxxx_07 = self.wc.setCombobox(self.ui.cs_tab, items=opti_standard)
        self.ui.cvc_pushButton_05 = self.wc.setPushbutton('기준값', color=2, parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_std(self.ui), tip='백테 결과값 중 특정 수치를 만족하지 못하면\n기준값을 0으로 도출하도록 설정한다.')
        self.ui.cvc_pushButton_36 = self.wc.setPushbutton('optuna', color=3, parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_optuna(self.ui), tip='옵튜나의 샘플러를 선택하거나 대시보드를 열람한다')

        self.ui.coin_period_list  = [
            self.ui.cvc_labellllll_01, self.ui.cvc_labellllll_02, self.ui.cvc_comboBoxxx_03, self.ui.cvc_comboBoxxx_04,
            self.ui.cvc_comboBoxxx_05, self.ui.cvc_comboBoxxx_06, self.ui.cvc_labellllll_03, self.ui.cvc_comboBoxxx_07,
            self.ui.cvc_pushButton_05, self.ui.cvc_pushButton_36
        ]

        for widget in self.ui.coin_period_list:
            widget.setVisible(False)

    # =================================================================================================================

        self.ui.cvc_pushButton_06 = self.wc.setPushbutton('교차검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화OVC', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n검증 최적화는 1회만 검증을 하지만, 교차검증은\n검증기간을 학습기간 / 검증기간 만큼 교차분류하여 그리드 최적화한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.\nCtrl+Shift와 함께 누르면 매수변수만 최적화한다.\nCtrl+Alt와 함께 누르면 매도변수만 최적화한다.')
        self.ui.cvc_pushButton_07 = self.wc.setPushbutton('검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화OV', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n데이터의 시계열 순서대로 학습, 검증기간을 분류하여 그리드 최적화한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.\nCtrl+Shift와 함께 누르면 매수변수만 최적화한다.\nCtrl+Alt와 함께 누르면 매도변수만 최적화한다.')
        self.ui.cvc_pushButton_08 = self.wc.setPushbutton('그리드', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화O', color=2, tip='학습기간만 선택하여 진행되며\n데이터 전체를 기반으로 그리드 최적화한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.\nCtrl+Shift와 함께 누르면 매수변수만 최적화한다.\nCtrl+Alt와 함께 누르면 매도변수만 최적화한다.')
        self.ui.cvc_pushButton_27 = self.wc.setPushbutton('교차검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화BVC', color=3, tip='학습기간과 검증기간을 선택하여 진행되며\n검증 최적화는 1회만 검증을 하지만, 교차검증은\n검증기간을 학습기간 / 검증기간 만큼 교차분류하여 베이지안 최적화한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.\nCtrl+Shift와 함께 누르면 매수변수만 최적화한다.\nCtrl+Alt와 함께 누르면 매도변수만 최적화한다.')
        self.ui.cvc_pushButton_28 = self.wc.setPushbutton('검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화BV', color=3, tip='학습기간과 검증기간을 선택하여 진행되며\n데이터의 시계열 순서대로 학습, 검증기간을 분류하여 베이지안 최적화한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.\nCtrl+Shift와 함께 누르면 매수변수만 최적화한다.\nCtrl+Alt와 함께 누르면 매도변수만 최적화한다.')
        self.ui.cvc_pushButton_29 = self.wc.setPushbutton('베이지안', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화B', color=3, tip='학습기간만 선택하여 진행되며\n데이터 전체를 기반으로 베이지안 최적화한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.\nCtrl+Shift와 함께 누르면 매수변수만 최적화한다.\nCtrl+Alt와 함께 누르면 매도변수만 최적화한다.')

    # =================================================================================================================

        self.ui.cvc_comboBoxxx_08 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_05(self.ui, 'coin'))
        self.ui.cvc_lineEdittt_03 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F6, F7', style=style_bc_dk)
        self.ui.cvc_pushButton_09 = self.wc.setPushbutton('최적화 매도전략 로딩(F5)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_sell_load(self.ui), color=1, tip='작성된 최적화 매도전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cvc_pushButton_10 = self.wc.setPushbutton('최적화 매도전략 저장(F8)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_sell_save(self.ui), color=1, tip='작성된 최적화 매도전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')
        self.ui.cvc_labellllll_04 = QLabel(optitext, self.ui.cs_tab)
        self.ui.cvc_labellllll_04.setFont(qfont13)
        self.ui.cvc_pushButton_11 = self.wc.setPushbutton('예제', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_sample(self.ui), color=3)

        self.ui.cvc_lineEdittt_04 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, visible=False, style=style_bc_dk)
        self.ui.cvc_pushButton_13 = self.wc.setPushbutton('매수전략으로 저장', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_to_buy_save(self.ui), color=1, visible=False, tip='최적값으로 백테용 매수전략으로 저장한다.')
        self.ui.cvc_lineEdittt_05 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, visible=False, style=style_bc_dk)
        self.ui.cvc_pushButton_14 = self.wc.setPushbutton('매도전략으로 저장', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_to_sell_save(self.ui), color=1, visible=False, tip='최적값으로 백테용 매도전략으로 저장한다.')

        self.ui.coin_optimz_list  = [
            self.ui.cvc_comboBoxxx_01, self.ui.cvc_comboBoxxx_02, self.ui.cvc_comboBoxxx_03, self.ui.cvc_comboBoxxx_08,
            self.ui.cvc_lineEdittt_01, self.ui.cvc_lineEdittt_02, self.ui.cvc_lineEdittt_03, self.ui.cvc_labellllll_04,
            self.ui.cvc_pushButton_01, self.ui.cvc_pushButton_02, self.ui.cvc_pushButton_03, self.ui.cvc_pushButton_04,
            self.ui.cvc_pushButton_06, self.ui.cvc_pushButton_07, self.ui.cvc_pushButton_08, self.ui.cvc_pushButton_09,
            self.ui.cvc_pushButton_10, self.ui.cvc_pushButton_11, self.ui.cvc_lineEdittt_04, self.ui.cvc_lineEdittt_05,
            self.ui.cvc_pushButton_13, self.ui.cvc_pushButton_14, self.ui.cvc_pushButton_27, self.ui.cvc_pushButton_28,
            self.ui.cvc_pushButton_29
        ]

        for widget in self.ui.coin_optimz_list:
            widget.setVisible(False)

    # =================================================================================================================

        self.ui.cvc_pushButton_15 = self.wc.setPushbutton('교차검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화OVCT', color=2, tip='학습기간, 검증기간, 확인기간을 선택하여 진행되며\n그리드 교차검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.')
        self.ui.cvc_pushButton_16 = self.wc.setPushbutton('검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화OVT', color=2, tip='학습기간, 검증기간, 확인기간을 선택하여 진행되며\n그리드 검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.')
        self.ui.cvc_pushButton_17 = self.wc.setPushbutton('그리드', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화OT', color=2, tip='학습기간, 확인기간을 선택하여 진행되며\n그리드 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.')
        self.ui.cvc_pushButton_30 = self.wc.setPushbutton('교차검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화BVCT', color=3, tip='학습기간, 검증기간, 확인기간을 선택하여 진행되며\n베이지안 교차검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.')
        self.ui.cvc_pushButton_31 = self.wc.setPushbutton('검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화BVT', color=3, tip='학습기간, 검증기간, 확인기간을 선택하여 진행되며\n베이지안 검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.')
        self.ui.cvc_pushButton_32 = self.wc.setPushbutton('베이지안', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiStart, cmd='최적화BT', color=3, tip='학습기간, 확인기간을 선택하여 진행되며\n베이지안 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.')

        self.ui.coin_optest_list  = [
            self.ui.cvc_pushButton_15, self.ui.cvc_pushButton_16, self.ui.cvc_pushButton_17, self.ui.cvc_comboBoxxx_02,
            self.ui.cvc_lineEdittt_02, self.ui.cvc_pushButton_03, self.ui.cvc_pushButton_04, self.ui.cvc_pushButton_30,
            self.ui.cvc_pushButton_31, self.ui.cvc_pushButton_32
        ]

        for widget in self.ui.coin_optest_list:
            widget.setVisible(False)

    # =================================================================================================================

        self.ui.cvc_pushButton_18 = self.wc.setPushbutton('교차검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiRwftStart, cmd='전진분석ORVC', color=2, tip='학습기간, 확인기간, 전체기간을 선택하여 진행되며\n그리드 교차검증 최적화 테스트를 전진분석한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.')
        self.ui.cvc_pushButton_19 = self.wc.setPushbutton('검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiRwftStart, cmd='전진분석ORV', color=2, tip='학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n그리드 검증 최적화 테스트를 전진분석한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.')
        self.ui.cvc_pushButton_20 = self.wc.setPushbutton('그리드', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiRwftStart, cmd='전진분석OR', color=2, tip='학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n그리드 최적화 테스트를 전진분석한다.\nAlt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작힌다.')
        self.ui.cvc_pushButton_33 = self.wc.setPushbutton('교차검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiRwftStart, cmd='전진분석BRVC', color=3, tip='학습기간, 확인기간, 전체기간을 선택하여 진행되며\n베이지안 교차검증 최적화 테스트를 전진분석한다.')
        self.ui.cvc_pushButton_34 = self.wc.setPushbutton('검증', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiRwftStart, cmd='전진분석BRV', color=3, tip='학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n베이지안 검증 최적화 테스트를 전진분석한다.')
        self.ui.cvc_pushButton_35 = self.wc.setPushbutton('베이지안', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiRwftStart, cmd='전진분석BR', color=3, tip='학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n베이지안 최적화 테스트를 전진분석한다.')

        self.ui.coin_rwftvd_list  = [
            self.ui.cvc_pushButton_18, self.ui.cvc_pushButton_19, self.ui.cvc_pushButton_20, self.ui.cvc_comboBoxxx_02,
            self.ui.cvc_lineEdittt_02, self.ui.cvc_pushButton_03, self.ui.cvc_pushButton_04, self.ui.cvjb_labelllll_01,
            self.ui.cvjb_dateEditt_01, self.ui.cvjb_dateEditt_02, self.ui.cvc_pushButton_33, self.ui.cvc_pushButton_34,
            self.ui.cvc_pushButton_35
        ]

        for widget in self.ui.coin_rwftvd_list:
            if widget not in (self.ui.cvjb_labelllll_01, self.ui.cvjb_dateEditt_01, self.ui.cvjb_dateEditt_02):
                widget.setVisible(False)

    # =================================================================================================================

        self.ui.cvc_labellllll_05 = QLabel('', self.ui.cs_tab)
        self.ui.cvc_labellllll_05.setVisible(False)

    # =================================================================================================================

        self.ui.cva_pushButton_01 = self.wc.setPushbutton('교차검증 GA 최적화', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiGaStart, cmd='최적화OGVC', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n교차 검증 GA최적화한다.')
        self.ui.cva_pushButton_02 = self.wc.setPushbutton('검증 GA 최적화', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiGaStart, cmd='최적화OGV', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n검증 GA최적화한다.')
        self.ui.cva_pushButton_03 = self.wc.setPushbutton('GA 최적화', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiGaStart, cmd='최적화OG', color=2, tip='학습기간을 선택하여 진행되며\n데이터 전체를 사용하여 GA최적화한다.')

        self.ui.cva_comboBoxxx_01 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_06(self.ui, 'coin'))
        self.ui.cva_lineEdittt_01 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F10, F11', style=style_bc_dk)
        self.ui.cva_pushButton_04 = self.wc.setPushbutton('GA 변수범위 로딩(F9)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_gavars_load(self.ui), color=1, tip='작성된 변수범위를 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cva_pushButton_05 = self.wc.setPushbutton('GA 변수범위 저장(F12)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_gavars_save(self.ui), color=1, tip='작성된 변수범위를 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')

        self.ui.coin_gaopti_list  = [
            self.ui.cva_pushButton_01, self.ui.cva_pushButton_02, self.ui.cva_pushButton_03, self.ui.cva_comboBoxxx_01,
            self.ui.cva_lineEdittt_01, self.ui.cva_pushButton_04, self.ui.cva_pushButton_05, self.ui.cvc_labellllll_04
        ]

        for widget in self.ui.coin_gaopti_list:
            widget.setVisible(False)

    # =================================================================================================================

        self.ui.cvc_pushButton_21 = self.wc.setPushbutton('최적화 > GA 범위 변환', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_optivars_to_gavars(self.ui), color=2, visible=False, tip='최적화용 범위코드를 GA용으로 변환한다.')
        self.ui.cvc_pushButton_22 = self.wc.setPushbutton('GA > 최적화 범위 변환', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_gavars_to_optivars(self.ui), color=2, visible=False, tip='GA용 범위코드를 최적화용으로 변환한다.')
        self.ui.cvc_pushButton_23 = self.wc.setPushbutton('변수 키값 재정렬', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_stgvars_key_sort(self.ui), color=2, visible=False, tip='범위 변수 self.vars의 키값을 재정렬한다.')

        self.ui.coin_areaedit_list = [
            self.ui.cvc_pushButton_21, self.ui.cvc_pushButton_22, self.ui.cvc_pushButton_23
        ]

    # =================================================================================================================

        self.ui.cvc_pushButton_24 = self.wc.setPushbutton('최적화 변수 변환(매수우선)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_stg_vars_change(self.ui), color=2, visible=False, tip='일반 전략의 각종 변수를 매수우선 최적화용 변수로 변환한다.')
        self.ui.cvc_pushButton_25 = self.wc.setPushbutton('최적화 변수 변환(매도우선)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_stg_vars_change(self.ui), color=2, visible=False, tip='일반 전략의 각종 변수를 매도우선 최적화용 변수로 변환한다.')
        self.ui.cvc_pushButton_26 = self.wc.setPushbutton('변수 키값 재정렬', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_optivars_key_sort(self.ui), color=2, visible=False, tip='변수 self.vars의 키값을 재정렬한다.\n매수, 매도 self.vars의 첫번째 키값을 비교해서\n매수가 빠르면 매수우선, 매도가 빠르면 매도우선으로 재정렬된다.')

        self.ui.coin_varsedit_list = [
            self.ui.cvc_pushButton_24, self.ui.cvc_pushButton_25, self.ui.cvc_pushButton_26
        ]

    # =================================================================================================================

        self.ui.cvo_comboBoxxx_01 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_07(self.ui, 'coin'))
        self.ui.cvo_lineEdittt_01 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F2, F3', style=style_bc_dk)
        self.ui.cvo_pushButton_01 = self.wc.setPushbutton('매수조건 로딩(F1)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_condbuy_load(self.ui), color=1, tip='작성된 매수조건을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cvo_pushButton_02 = self.wc.setPushbutton('매수조건 저장(F4)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_condbuy_save(self.ui), color=1, tip='작성된 매수조건을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')
        self.ui.cvo_comboBoxxx_02 = self.wc.setCombobox(self.ui.cs_tab, font=qfont14, activated=lambda: ui_activated_stg.activated_08(self.ui, 'coin'))
        self.ui.cvo_lineEdittt_02 = self.wc.setLineedit(self.ui.cs_tab, font=qfont14, aleft=True, ltext='F6, F7', style=style_bc_dk)
        self.ui.cvo_pushButton_03 = self.wc.setPushbutton('매도조건 로딩(F5)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_condsell_load(self.ui), color=1, tip='작성된 매도조건을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.')
        self.ui.cvo_pushButton_04 = self.wc.setPushbutton('매도조건 저장(F8)', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_condsell_save(self.ui), color=1, tip='작성된 매도조건을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.')

        self.ui.cvo_labellllll_04 = QLabel('매수조건수                     매도조건수                    최적화횟수', self.ui.cs_tab)
        self.ui.cvo_lineEdittt_03 = self.wc.setLineedit(self.ui.cs_tab, ltext='10', style=style_bc_dk)
        self.ui.cvo_lineEdittt_04 = self.wc.setLineedit(self.ui.cs_tab, ltext='5', style=style_bc_dk)
        self.ui.cvo_lineEdittt_05 = self.wc.setLineedit(self.ui.cs_tab, ltext='1000', style=style_bc_dk)

        self.ui.cvo_pushButton_05 = self.wc.setPushbutton('교차검증 조건 최적화', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiCondStart, cmd='최적화OCVC', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n교차 검증 조건최적화한다.')
        self.ui.cvo_pushButton_06 = self.wc.setPushbutton('검증 조건 최적화', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiCondStart, cmd='최적화OCV', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n검증 조건최적화한다.')
        self.ui.cvo_pushButton_07 = self.wc.setPushbutton('조건 최적화', parent=self.ui.cs_tab, bounced=True, click=self.ui.CoinOptiCondStart, cmd='최적화OC', color=2, tip='학습기간을 선택하여 진행되며\n데이터 전체를 사용하여 조건최적화한다.')

        self.ui.cvo_pushButton_08 = self.wc.setPushbutton('예제', parent=self.ui.cs_tab, bounced=True, click=lambda: coin_opti_sample(self.ui), color=3)

        self.ui.coin_opcond_list  = [
            self.ui.cs_textEditttt_07, self.ui.cs_textEditttt_08, self.ui.cvo_comboBoxxx_01, self.ui.cvo_lineEdittt_01,
            self.ui.cvo_pushButton_01, self.ui.cvo_pushButton_02, self.ui.cvo_comboBoxxx_02, self.ui.cvo_lineEdittt_02,
            self.ui.cvo_pushButton_03, self.ui.cvo_pushButton_04, self.ui.cvo_pushButton_05, self.ui.cvo_pushButton_06,
            self.ui.cvo_pushButton_07, self.ui.cvo_labellllll_04, self.ui.cvo_lineEdittt_03, self.ui.cvo_lineEdittt_04,
            self.ui.cvo_lineEdittt_05, self.ui.cvo_pushButton_08, self.ui.cvc_labellllll_04
        ]

        for widget in self.ui.coin_opcond_list:
            widget.setVisible(False)

        self.ui.coin_load_list = [
            self.ui.cvjb_pushButon_01, self.ui.cvjs_pushButon_01, self.ui.cvc_pushButton_01, self.ui.cvc_pushButton_03,
            self.ui.cvc_pushButton_09, self.ui.cva_pushButton_04, self.ui.cvo_pushButton_01, self.ui.cvo_pushButton_03
        ]

    # =================================================================================================================

        self.ui.cs_textEditttt_01.setGeometry(7, 10, 1000, 463)
        self.ui.cs_textEditttt_02.setGeometry(7, 480, 1000, 272)
        self.ui.cs_textEditttt_03.setGeometry(509, 10, 497, 463)
        self.ui.cs_textEditttt_04.setGeometry(509, 480, 497, 272)
        self.ui.cs_textEditttt_05.setGeometry(659, 10, 347, 740)
        self.ui.cs_textEditttt_06.setGeometry(659, 10, 347, 740)
        self.ui.cs_textEditttt_07.setGeometry(7, 10, 497, 740)
        self.ui.cs_textEditttt_08.setGeometry(509, 10, 497, 740)

        self.ui.cs_textEditttt_10.setGeometry(509, 40, 497, 700)
        self.ui.cs_comboBoxxxx_41.setGeometry(7, 10, 497, 25)
        self.ui.cs_comboBoxxxx_42.setGeometry(509, 10, 400, 25)
        self.ui.cs_pushButtonn_41.setGeometry(914, 10, 92, 25)

        self.ui.czoo_pushButon_01.setGeometry(937, 15, 50, 20)
        self.ui.czoo_pushButon_02.setGeometry(937, 483, 50, 20)

        self.ui.cs_tableWidget_01.setGeometry(7, 40, 1000, 713)
        self.ui.cs_comboBoxxxx_01.setGeometry(7, 10, 150, 25)
        self.ui.cs_pushButtonn_01.setGeometry(162, 10, 100, 25)
        self.ui.cs_pushButtonn_02.setGeometry(267, 10, 55, 25)
        self.ui.cs_comboBoxxxx_02.setGeometry(327, 10, 150, 25)
        self.ui.cs_pushButtonn_03.setGeometry(482, 10, 100, 25)
        self.ui.cs_pushButtonn_04.setGeometry(587, 10, 55, 25)
        self.ui.cs_comboBoxxxx_03.setGeometry(647, 10, 150, 25)
        self.ui.cs_pushButtonn_05.setGeometry(802, 10, 100, 25)
        self.ui.cs_pushButtonn_06.setGeometry(907, 10, 55, 25)
        self.ui.cs_pushButtonn_07.setGeometry(967, 10, 40, 25)

        self.ui.cs_textEditttt_09.setGeometry(7, 10, 1000, 703)
        self.ui.cs_progressBar_01.setGeometry(7, 718, 830, 30)
        self.ui.cs_pushButtonn_08.setGeometry(842, 718, 165, 30)

        self.ui.cvjb_comboBoxx_01.setGeometry(1012, 10, 165, 25)
        self.ui.cvjb_lineEditt_01.setGeometry(1182, 10, 165, 25)
        self.ui.cvjb_pushButon_01.setGeometry(1012, 40, 165, 30)
        self.ui.cvjb_pushButon_02.setGeometry(1182, 40, 165, 30)
        self.ui.cvjb_pushButon_03.setGeometry(1012, 75, 165, 30)
        self.ui.cvjb_pushButon_04.setGeometry(1182, 75, 165, 30)
        self.ui.cvjb_pushButon_05.setGeometry(1012, 110, 165, 30)
        self.ui.cvjb_pushButon_06.setGeometry(1182, 110, 165, 30)
        self.ui.cvjb_pushButon_07.setGeometry(1012, 145, 165, 30)
        self.ui.cvjb_pushButon_08.setGeometry(1182, 145, 165, 30)
        self.ui.cvjb_pushButon_09.setGeometry(1012, 180, 165, 30)
        self.ui.cvjb_pushButon_10.setGeometry(1182, 180, 165, 30)
        self.ui.cvjb_pushButon_11.setGeometry(1012, 215, 165, 30)
        self.ui.cvjb_pushButon_12.setGeometry(1182, 215, 165, 30)

        self.ui.cvj_pushButton_01.setGeometry(1012, 335, 165, 30)
        self.ui.cvj_pushButton_02.setGeometry(1012, 370, 165, 30)
        self.ui.cvj_pushButton_03.setGeometry(1012, 405, 80, 30)
        self.ui.cvj_pushButton_04.setGeometry(1097, 405, 80, 30)

        self.ui.cvjs_comboBoxx_01.setGeometry(1012, 478, 165, 25)
        self.ui.cvjs_lineEditt_01.setGeometry(1182, 478, 165, 25)
        self.ui.cvjs_pushButon_01.setGeometry(1012, 508, 165, 30)
        self.ui.cvjs_pushButon_02.setGeometry(1182, 508, 165, 30)
        self.ui.cvjs_pushButon_03.setGeometry(1012, 543, 165, 30)
        self.ui.cvjs_pushButon_04.setGeometry(1182, 543, 165, 30)
        self.ui.cvjs_pushButon_05.setGeometry(1012, 578, 165, 30)
        self.ui.cvjs_pushButon_06.setGeometry(1182, 578, 165, 30)
        self.ui.cvjs_pushButon_07.setGeometry(1012, 613, 165, 30)
        self.ui.cvjs_pushButon_08.setGeometry(1182, 613, 165, 30)
        self.ui.cvjs_pushButon_09.setGeometry(1012, 648, 165, 30)
        self.ui.cvjs_pushButon_10.setGeometry(1182, 648, 165, 30)
        self.ui.cvjs_pushButon_11.setGeometry(1012, 683, 165, 30)
        self.ui.cvjs_pushButon_12.setGeometry(1182, 683, 165, 30)
        self.ui.cvjs_pushButon_13.setGeometry(1012, 718, 165, 30)
        self.ui.cvjs_pushButon_14.setGeometry(1182, 718, 165, 30)

        self.ui.cvjb_labelllll_01.setGeometry(1012, 255, 340, 20)
        self.ui.cvjb_labelllll_02.setGeometry(1012, 280, 340, 20)
        self.ui.cvjb_labelllll_03.setGeometry(1012, 305, 335, 20)

        self.ui.cvjb_dateEditt_01.setGeometry(1112, 255, 110, 20)
        self.ui.cvjb_dateEditt_02.setGeometry(1237, 255, 110, 20)
        self.ui.cvjb_lineEditt_02.setGeometry(1167, 280, 60, 20)
        self.ui.cvjb_lineEditt_03.setGeometry(1287, 280, 60, 20)
        self.ui.cvjb_lineEditt_04.setGeometry(1167, 305, 60, 20)
        self.ui.cvjb_lineEditt_05.setGeometry(1287, 305, 60, 20)

        self.ui.cvj_pushButton_06.setGeometry(1182, 335, 80, 30)
        self.ui.cvj_pushButton_07.setGeometry(1182, 370, 80, 30)
        self.ui.cvj_pushButton_08.setGeometry(1182, 405, 80, 30)
        self.ui.cvj_pushButton_09.setGeometry(1182, 440, 80, 30)
        self.ui.cvj_pushButton_10.setGeometry(1267, 335, 80, 30)
        self.ui.cvj_pushButton_11.setGeometry(1267, 370, 80, 30)
        self.ui.cvj_pushButton_12.setGeometry(1267, 405, 80, 30)
        self.ui.cvj_pushButton_13.setGeometry(1267, 440, 80, 30)
        self.ui.cvj_pushButton_14.setGeometry(1012, 440, 80, 30)
        self.ui.cvj_pushButton_15.setGeometry(1097, 440, 80, 30)

        self.ui.cvc_comboBoxxx_01.setGeometry(1012, 45, 165, 30)
        self.ui.cvc_lineEdittt_01.setGeometry(1182, 45, 165, 30)
        self.ui.cvc_pushButton_01.setGeometry(1012, 80, 165, 30)
        self.ui.cvc_pushButton_02.setGeometry(1182, 80, 165, 30)

        self.ui.cvc_comboBoxxx_02.setGeometry(1012, 115, 165, 30)
        self.ui.cvc_lineEdittt_02.setGeometry(1182, 115, 165, 30)
        self.ui.cvc_pushButton_03.setGeometry(1012, 150, 165, 30)
        self.ui.cvc_pushButton_04.setGeometry(1182, 150, 165, 30)

        self.ui.cvc_labellllll_01.setGeometry(1012, 250, 335, 25)
        self.ui.cvc_labellllll_02.setGeometry(1012, 190, 335, 25)
        self.ui.cvc_comboBoxxx_03.setGeometry(1097, 190, 45, 25)
        self.ui.cvc_comboBoxxx_04.setGeometry(1197, 190, 45, 25)
        self.ui.cvc_comboBoxxx_05.setGeometry(1302, 190, 45, 25)

        self.ui.cvc_labellllll_03.setGeometry(1012, 220, 335, 25)
        self.ui.cvc_comboBoxxx_06.setGeometry(1097, 220, 45, 25)
        self.ui.cvc_comboBoxxx_07.setGeometry(1187, 220, 55, 25)
        self.ui.cvc_pushButton_05.setGeometry(1247, 220, 47, 25)
        self.ui.cvc_pushButton_36.setGeometry(1299, 220, 48, 25)

        self.ui.cvc_pushButton_06.setGeometry(1012, 335, 80, 30)
        self.ui.cvc_pushButton_07.setGeometry(1012, 370, 80, 30)
        self.ui.cvc_pushButton_08.setGeometry(1012, 405, 80, 30)
        self.ui.cvc_pushButton_27.setGeometry(1097, 335, 80, 30)
        self.ui.cvc_pushButton_28.setGeometry(1097, 370, 80, 30)
        self.ui.cvc_pushButton_29.setGeometry(1097, 405, 80, 30)

        self.ui.cvc_comboBoxxx_08.setGeometry(1012, 513, 165, 30)
        self.ui.cvc_lineEdittt_03.setGeometry(1182, 513, 165, 30)
        self.ui.cvc_pushButton_09.setGeometry(1012, 548, 165, 30)
        self.ui.cvc_pushButton_10.setGeometry(1182, 548, 165, 30)
        self.ui.cvc_labellllll_04.setGeometry(1012, 583, 335, 130)
        self.ui.cvc_pushButton_11.setGeometry(1012, 718, 335, 30)

        self.ui.cvc_lineEdittt_04.setGeometry(1012, 10, 165, 30)
        self.ui.cvc_pushButton_13.setGeometry(1182, 10, 165, 30)
        self.ui.cvc_lineEdittt_05.setGeometry(1012, 478, 165, 30)
        self.ui.cvc_pushButton_14.setGeometry(1182, 478, 165, 30)

        self.ui.cvc_pushButton_15.setGeometry(1012, 335, 80, 30)
        self.ui.cvc_pushButton_16.setGeometry(1012, 370, 80, 30)
        self.ui.cvc_pushButton_17.setGeometry(1012, 405, 80, 30)
        self.ui.cvc_pushButton_30.setGeometry(1097, 335, 80, 30)
        self.ui.cvc_pushButton_31.setGeometry(1097, 370, 80, 30)
        self.ui.cvc_pushButton_32.setGeometry(1097, 405, 80, 30)

        self.ui.cvc_pushButton_18.setGeometry(1012, 335, 80, 30)
        self.ui.cvc_pushButton_19.setGeometry(1012, 370, 80, 30)
        self.ui.cvc_pushButton_20.setGeometry(1012, 405, 80, 30)
        self.ui.cvc_pushButton_33.setGeometry(1097, 335, 80, 30)
        self.ui.cvc_pushButton_34.setGeometry(1097, 370, 80, 30)
        self.ui.cvc_pushButton_35.setGeometry(1097, 405, 80, 30)

        self.ui.cva_pushButton_01.setGeometry(1012, 335, 165, 30)
        self.ui.cva_pushButton_02.setGeometry(1012, 370, 165, 30)
        self.ui.cva_pushButton_03.setGeometry(1012, 405, 165, 30)

        self.ui.cva_comboBoxxx_01.setGeometry(1012, 115, 165, 30)
        self.ui.cva_lineEdittt_01.setGeometry(1182, 115, 165, 30)
        self.ui.cva_pushButton_04.setGeometry(1012, 150, 165, 30)
        self.ui.cva_pushButton_05.setGeometry(1182, 150, 165, 30)

        self.ui.cvc_pushButton_21.setGeometry(1012, 335, 165, 30)
        self.ui.cvc_pushButton_22.setGeometry(1012, 370, 165, 30)
        self.ui.cvc_pushButton_23.setGeometry(1012, 405, 165, 30)
        self.ui.cvc_pushButton_24.setGeometry(1012, 335, 165, 30)
        self.ui.cvc_pushButton_25.setGeometry(1012, 370, 165, 30)
        self.ui.cvc_pushButton_26.setGeometry(1012, 405, 165, 30)
        self.ui.cvc_labellllll_05.setGeometry(1012, 150, 335, 40)

        self.ui.cvo_comboBoxxx_01.setGeometry(1012, 10, 165, 30)
        self.ui.cvo_lineEdittt_01.setGeometry(1182, 10, 165, 30)
        self.ui.cvo_pushButton_01.setGeometry(1012, 45, 165, 30)
        self.ui.cvo_pushButton_02.setGeometry(1182, 45, 165, 30)
        self.ui.cvo_comboBoxxx_02.setGeometry(1012, 80, 165, 30)
        self.ui.cvo_lineEdittt_02.setGeometry(1182, 80, 165, 30)
        self.ui.cvo_pushButton_03.setGeometry(1012, 115, 165, 30)
        self.ui.cvo_pushButton_04.setGeometry(1182, 115, 165, 30)

        self.ui.cvo_labellllll_04.setGeometry(1012, 255, 335, 20)
        self.ui.cvo_lineEdittt_03.setGeometry(1072, 255, 45, 20)
        self.ui.cvo_lineEdittt_04.setGeometry(1197, 255, 45, 20)
        self.ui.cvo_lineEdittt_05.setGeometry(1302, 255, 45, 20)

        self.ui.cvo_pushButton_05.setGeometry(1012, 335, 165, 30)
        self.ui.cvo_pushButton_06.setGeometry(1012, 370, 165, 30)
        self.ui.cvo_pushButton_07.setGeometry(1012, 405, 165, 30)

        self.ui.cvo_pushButton_08.setGeometry(1012, 718, 335, 30)
