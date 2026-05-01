
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QLabel
from ui.ui_button_clicked_strategy import *
# noinspection PyUnusedImports
from ui.ui_button_clicked_editer_backlog import *
from ui.ui_button_clicked_editer_unified import *
from ui.ui_button_clicked_editer_ga_unified import *
from ui.ui_button_clicked_editer_opti_unified import *
from ui.ui_button_clicked_editer_stg_buy_unified import *
from ui.ui_button_clicked_editer_stg_sell_unified import *
from utility.setting_base import columns_bt
from ui.ui_cell_clicked import cell_clicked_06
from ui import ui_activated_stg, ui_activated_etc
from utility.static import dt_hms, str_hms, timedelta_sec
from ui.set_text import optistandard, optitext, train_period, valid_period, test_period, optimized_count, opti_standard
from ui.ui_strategy_version import dactivated_04, strategy_version_delete
from ui.set_style import qfont12, qfont13, qfont14, style_pgbar, style_bc_dk
from ui.ui_button_clicked_zoom import cz_button_clicked_01, cz_button_clicked_02, sz_button_clicked_01, sz_button_clicked_02


class SetStrategyTab:
    """코인과 주식 전략 탭을 통합한 클래스"""

    def __init__(self, ui_class, wc, market_type='stock'):
        self.ui = ui_class
        self.wc = wc
        self.market_type = market_type
        self.is_coin = market_type == 'coin'
        self.is_stock = market_type == 'stock'
        self.prefix = 'cs' if self.is_coin else 'ss'
        self.zoom_prefix = 'cz' if self.is_coin else 'sz'
        self.tab = self.ui.cs_tab if self.is_coin else self.ui.ss_tab
        self.vjb_prefix = 'cvjb' if self.is_coin else 'svjb'
        self.vj_prefix = 'cvj' if self.is_coin else 'svj'
        self.vjs_prefix = 'cvjs' if self.is_coin else 'svjs'
        self.vc_prefix = 'cvc' if self.is_coin else 'svc'
        self.va_prefix = 'cva' if self.is_coin else 'sva'
        self.vo_prefix = 'cvo' if self.is_coin else 'svo'
        self.list_prefix = 'coin' if self.is_coin else 'stock'

        self.set()

    @error_decorator
    def set(self):
        self._setup_text_edits()
        self._setup_zoom_buttons()
        self._setup_version_controls()
        self._setup_detail_records()
        self._setup_backlog()
        self._setup_strategy_buttons()
        self._setup_editer_buttons()
        self._setup_optimization()
        self._setup_optest_buttons()
        self._setup_rwft_buttons()
        self._setup_ga_optimization()
        self._setup_area_editors()
        self._setup_vars_editors()
        self._setup_condition_optimization()
        self._setup_geometries()

    def _setup_text_edits(self):
        """텍스트 에디터 설정"""
        for i in range(1, 9):
            visible = i < 3
            setattr(self.ui, f'{self.prefix}_textEditttt_0{i}', 
                    self.wc.setTextEdit(self.tab, vscroll=True, visible=visible, filter_=True, font=qfont14))

    def _setup_zoom_buttons(self):
        """확대 버튼 설정"""
        zoom1_click = cz_button_clicked_01 if self.is_coin else sz_button_clicked_01
        zoom2_click = cz_button_clicked_02 if self.is_coin else sz_button_clicked_02

        setattr(self.ui, f'{self.zoom_prefix}oo_pushButon_01',
                self.wc.setPushbutton('확대(esc)', parent=self.tab, bounced=True, click=lambda: zoom1_click(self.ui)))
        setattr(self.ui, f'{self.zoom_prefix}oo_pushButon_02',
                self.wc.setPushbutton('확대(esc)', parent=self.tab, bounced=True, click=lambda: zoom2_click(self.ui)))

        setattr(self.ui, f'{self.list_prefix}_esczom_list',
                [getattr(self.ui, f'{self.zoom_prefix}oo_pushButon_01'), getattr(self.ui, f'{self.zoom_prefix}oo_pushButon_02')])

    def _setup_version_controls(self):
        """버전 관리 컨트롤 설정"""
        setattr(self.ui, f'{self.prefix}_textEditttt_10',
                self.wc.setTextEdit(self.tab, vscroll=True, visible=False, filter_=True, event_filter=False, font=qfont14))
        setattr(self.ui, f'{self.prefix}_comboBoxxxx_41',
                self.wc.setCombobox(self.tab, font=qfont12, activated=lambda: dactivated_04(self.ui)))
        setattr(self.ui, f'{self.prefix}_comboBoxxxx_42',
                self.wc.setCombobox(self.tab, font=qfont12, activated=lambda: dactivated_04(self.ui)))
        setattr(self.ui, f'{self.prefix}_pushButtonn_41',
                self.wc.setPushbutton('버전삭제', parent=self.tab, bounced=True, click=lambda: strategy_version_delete(self.ui),
                                      tip='선택된 버전의 데이터를 삭제합니다.'))

        setattr(self.ui, f'{self.list_prefix}_version_list',
                [getattr(self.ui, f'{self.prefix}_textEditttt_10'), getattr(self.ui, f'{self.prefix}_comboBoxxxx_41'),
                 getattr(self.ui, f'{self.prefix}_comboBoxxxx_42'), getattr(self.ui, f'{self.prefix}_pushButtonn_41')])

        for widget in getattr(self.ui, f'{self.list_prefix}_version_list'):
            widget.setVisible(False)

    def _setup_detail_records(self):
        """상세 기록 테이블 설정"""
        setattr(self.ui, f'{self.prefix}_tableWidget_01',
                self.wc.setTablewidget(self.tab, columns_bt, 32, vscroll=True, fixed=True,
                                       clicked=lambda row, col: cell_clicked_06(self.ui, row, col)))

        btn_prefix = self.prefix[:2]  # 'cs' 또는 'ss'
        btn_texts = {
            1: ('백테스트상세기록', '백테스트 상세기록을 불러온다.'),
            2: ('그래프', '선택된 상세기록의 그래프를 표시한다.'),
            3: ('최적화상세기록', '최적화 상세기록을 불러온다.'),
            5: ('분석상세기록' if self.is_coin else '그외상세기록', 
                '최적화 테스트 및 전진분석 상세기록을 불러온다.'),
            7: ('비교', '두개 이상의 그래프를 선택 비교한다.')
        }

        for i in range(1, 8):
            if i in [1, 3, 5]:
                handler = globals()[f'{btn_prefix}button_clicked_0{1 if i==1 else 2 if i==3 else 3}']
            elif i in [2, 4, 6]:
                handler = globals()[f'{btn_prefix}button_clicked_04']
            else:
                handler = globals()[f'{btn_prefix}button_clicked_05']

            text, tip = btn_texts.get(i, ('그래프', ''))
            setattr(self.ui, f'{self.prefix}_pushButtonn_{i:02d}',
                    self.wc.setPushbutton(text, parent=self.tab, bounced=True, click=lambda _, h=handler: h(self.ui),
                                          color=4 if i == 7 else None, tip=tip))

        for i in range(1, 4):
            setattr(self.ui, f'{self.prefix}_comboBoxxxx_{i:02d}',
                    self.wc.setCombobox(self.tab, font=qfont12, activated=lambda: ui_activated_etc.dactivated_01(self.ui)))

        setattr(self.ui, f'{self.list_prefix}_detail_list',
                [getattr(self.ui, f'{self.prefix}_tableWidget_01'),
                 getattr(self.ui, f'{self.prefix}_comboBoxxxx_01'), getattr(self.ui, f'{self.prefix}_pushButtonn_01'),
                 getattr(self.ui, f'{self.prefix}_pushButtonn_02'), getattr(self.ui, f'{self.prefix}_comboBoxxxx_02'),
                 getattr(self.ui, f'{self.prefix}_pushButtonn_03'), getattr(self.ui, f'{self.prefix}_pushButtonn_04'),
                 getattr(self.ui, f'{self.prefix}_comboBoxxxx_03'), getattr(self.ui, f'{self.prefix}_pushButtonn_05'),
                 getattr(self.ui, f'{self.prefix}_pushButtonn_06'), getattr(self.ui, f'{self.prefix}_pushButtonn_07')])

        for widget in getattr(self.ui, f'{self.list_prefix}_detail_list'):
            widget.setVisible(False)

    def _setup_backlog(self):
        """백로그 설정"""
        setattr(self.ui, f'{self.prefix}_textEditttt_09', self.wc.setTextEdit(self.tab, visible=False, vscroll=True))
        setattr(self.ui, f'{self.prefix}_progressBar_01', self.wc.setProgressBar(self.tab, style=style_pgbar, visible=False))
        handler = globals()[f'{self.prefix[:2]}button_clicked_06']
        btn = self.wc.setPushbutton('백테스트 중지', parent=self.tab, bounced=True, click=lambda: handler(self.ui),
                                    color=2, visible=False, tip='(Alt+Enter) 실행중인 백테스트를 중지한다.')
        setattr(self.ui, f'{self.prefix}_pushButtonn_08', btn)

        setattr(self.ui, f'{self.list_prefix}_baklog_list', [
            getattr(self.ui, f'{self.prefix}_textEditttt_09'),
            getattr(self.ui, f'{self.prefix}_progressBar_01'),
            btn
        ])

    def _setup_strategy_buttons(self):
        """매수/매도 전략 버튼 설정"""
        # 매수 기본 버튼
        setattr(self.ui, f'{self.vjb_prefix}_comboBoxx_01',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_01(self.ui, self.market_type)))
        setattr(self.ui, f'{self.vjb_prefix}_lineEditt_01',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F2, F3', style=style_bc_dk))

        buy_handlers = [
            ('매수전략 로딩(F1)', lambda: buy_stg_load(self.ui, self.market_type), 1, '작성된 매수전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'),
            ('매수전략 저장(F4)', lambda: buy_stg_save(self.ui, self.market_type), 1, '작성된 매수전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'),
            ('매수변수 로딩', lambda: buy_factor(self.ui, self.market_type), 1, '매수전략에 사용할 수 있는 변수목록을 불러온다.'),
            ('매수전략 시작', lambda: buy_stg_start(self.ui, self.market_type), 1, '작성한 전략을 저장 후 콤보박스에서 선택해야 적용된다.'),
        ]

        for i, (text, handler, color, tip) in enumerate(buy_handlers, start=1):
            setattr(self.ui, f'{self.vjb_prefix}_pushButon_{i:02d}',
                    self.wc.setPushbutton(text, parent=self.tab, bounced=True, click=handler, color=color, tip=tip))

        # 매수 전략 버튼 텍스트와 전략 코드 매핑
        if self.is_coin:
            buy_buttons = [
                ('등락율제한', 220), ('고저평균등락율', 211), ('현재가시가비교', 222),
                ('체결강도하한', 223), ('체결강도평균차이', 224), ('최고체결강도', 225)
            ]
        else:
            buy_buttons = [
                ('VI해제시간비교', 206), ('VI아래5호가비교', 207), ('등락율제한', 208),
                ('고저평균대비등락율', 209), ('체결강도하한', 210), ('체결강도차이', 211)
            ]

        for i, (text, code) in enumerate(buy_buttons, start=5):
            setattr(self.ui, f'{self.vjb_prefix}_pushButon_{i:02d}',
                    self.wc.setPushbutton(text, parent=self.tab, bounced=True,
                                          click=lambda _, c=code: button_clicked_strategy(self.ui, c)))

        setattr(self.ui, f'{self.vjb_prefix}_pushButon_11',
                self.wc.setPushbutton('매수시그널', parent=self.tab, bounced=True,
                                      click=lambda: buy_signal_insert(self.ui, self.market_type), color=3))
        setattr(self.ui, f'{self.vjb_prefix}_pushButon_12',
                self.wc.setPushbutton('매수전략 중지', parent=self.tab, bounced=True,
                                      click=lambda: buy_stg_stop(self.ui, self.market_type), color=1,
                                      tip='실행중인 매수전략을 중지한다.'))

        # 백테스트 버튼
        setattr(self.ui, f'{self.vj_prefix}_pushButton_01',
                self.wc.setPushbutton('백테스트', parent=self.tab, bounced=True,
                                      click=lambda: backtest_start(self.ui, self.market_type), color=2,
                                      tip='(Alt+Enter) 기본전략을 백테스팅한다.\nCtrl키와 함께 누르면 백테스트 엔진을 재시작할 수 있습니다.\nCtrl + Alt 키와 함계 누르면 백테 완료 후 변수목록이 포함된 그래프가 저장됩니다.'))
        setattr(self.ui, f'{self.vj_prefix}_pushButton_02',
                self.wc.setPushbutton('백파인더', parent=self.tab, bounced=True,
                                      click=lambda: backfinder_start(self.ui, self.market_type), color=2,
                                      tip='구간등락율을 기준으로 변수를 탐색한다.'))
        setattr(self.ui, f'{self.vj_prefix}_pushButton_03',
                self.wc.setPushbutton('백파인더 예제', parent=self.tab, bounced=True,
                                      click=lambda: backfinder_sample(self.ui, self.market_type), color=3))
        setattr(self.ui, f'{self.vj_prefix}_pushButton_04',
                self.wc.setPushbutton('전략모듈', parent=self.tab, bounced=True,
                                      click=lambda: strategy_custom_button_show(self.ui), color=3))

        # 매도 기본 버튼
        setattr(self.ui, f'{self.vjs_prefix}_comboBoxx_01',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_02(self.ui, self.market_type)))
        setattr(self.ui, f'{self.vjs_prefix}_lineEditt_01',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F6, F7', style=style_bc_dk))

        sell_handlers = [
            ('매도전략 로딩(F5)', lambda: sell_stg_load(self.ui, self.market_type), '작성된 매도전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'),
            ('매도전략 저장(F8)', lambda: sell_stg_save(self.ui, self.market_type), '작성된 매도전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'),
            ('매도변수 로딩', lambda: sell_factor(self.ui, self.market_type), '매도전략에 사용할 수 있는 변수목록을 불러온다.'),
            ('매도전략 시작', lambda: sell_stg_start(self.ui, self.market_type), '작성한 전략을 저장 후 콤보박스에서 선택해야 적용된다.'),
        ]

        for i, (text, handler, tip) in enumerate(sell_handlers, start=1):
            setattr(self.ui, f'{self.vjs_prefix}_pushButon_{i:02d}',
                    self.wc.setPushbutton(text, parent=self.tab, bounced=True, click=handler, color=1, tip=tip))

        # 매도 전략 설정
        if self.is_coin:
            sell_buttons = [
                ('손절라인청산', 226), ('익절라인청산', 227), ('수익률보존청산', 228),
                ('보유시간기준청산', 229), ('체결강도평균비교', 230), ('최고체결강도비교', 231),
                ('고저평균등락율', 232), ('호가총잔량비교', 233)
            ]
        else:
            sell_buttons = [
                ('손절라인청산', 212), ('익절라인청산', 213), ('수익률보존청산', 214),
                ('보유시간기준청산', 215), ('VI직전매도', 216), ('고저평균등락율', 217),
                ('최고체결강도비교', 218), ('호가총잔량비교', 219)
            ]

        for i, (text, code) in enumerate(sell_buttons, start=5):
            setattr(self.ui, f'{self.vjs_prefix}_pushButon_{i:02d}',
                    self.wc.setPushbutton(text, parent=self.tab, bounced=True,
                                          click=lambda _, c=code: button_clicked_strategy(self.ui, c)))

        setattr(self.ui, f'{self.vjs_prefix}_pushButon_13',
                self.wc.setPushbutton('매도시그널', parent=self.tab, bounced=True,
                                      click=lambda: sell_signal_insert(self.ui, self.market_type), color=3))
        setattr(self.ui, f'{self.vjs_prefix}_pushButon_14',
                self.wc.setPushbutton('매도전략 중지', parent=self.tab, bounced=True,
                                      click=lambda: sell_stg_stop(self.ui, self.market_type), color=1, tip='실행중인 매도전략을 당장 중지한다.'))

        # backte 리스트 구성
        backte_items = [
            getattr(self.ui, f'{self.vjb_prefix}_comboBoxx_01'), getattr(self.ui, f'{self.vjb_prefix}_lineEditt_01'),
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_01'), getattr(self.ui, f'{self.vjb_prefix}_pushButon_02'),
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_03'), getattr(self.ui, f'{self.vjb_prefix}_pushButon_04'),
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_05'), getattr(self.ui, f'{self.vjb_prefix}_pushButon_06'),
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_07'), getattr(self.ui, f'{self.vjb_prefix}_pushButon_08'),
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_09'), getattr(self.ui, f'{self.vjb_prefix}_pushButon_10'),
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_11'), getattr(self.ui, f'{self.vjb_prefix}_pushButon_12'),
            getattr(self.ui, f'{self.vj_prefix}_pushButton_01'), getattr(self.ui, f'{self.vj_prefix}_pushButton_02'),
            getattr(self.ui, f'{self.vj_prefix}_pushButton_03'), getattr(self.ui, f'{self.vjs_prefix}_comboBoxx_01'),
            getattr(self.ui, f'{self.vjs_prefix}_lineEditt_01'), getattr(self.ui, f'{self.vj_prefix}_pushButton_04'),
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_01'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_02'),
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_03'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_04'),
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_05'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_06'),
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_07'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_08'),
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_09'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_10'),
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_11'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_12'),
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_13'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_14')
        ]
        setattr(self.ui, f'{self.list_prefix}_backte_list', backte_items)

    def _setup_editer_buttons(self):
        """에디터 버튼 설정"""
        # 시간/날짜 설정
        labelll_01_text = '백테스트 기간설정                                         ~'
        labelll_02_text = '백테스트 시간설정     시작시간                         종료시간'
        labelll_03_text = '백테스트 기본설정   배팅(백만)                        평균틱수   self.vars[0]'

        setattr(self.ui, f'{self.vjb_prefix}_labelllll_01', QLabel(labelll_01_text, self.tab))
        setattr(self.ui, f'{self.vjb_prefix}_labelllll_02', QLabel(labelll_02_text, self.tab))
        setattr(self.ui, f'{self.vjb_prefix}_labelllll_03', QLabel(labelll_03_text, self.tab))

        # 날짜 설정
        if self.ui.dict_set is not None:
            if self.ui.dict_set['백테날짜고정']:
                date1 = self.wc.setDateEdit(self.tab, qday=QDate.fromString(self.ui.dict_set['백테날짜'], 'yyyyMMdd'))
            else:
                date1 = self.wc.setDateEdit(self.tab, addday=-int(self.ui.dict_set['백테날짜']))
        else:
            date1 = self.wc.setDateEdit(self.tab)
        setattr(self.ui, f'{self.vjb_prefix}_dateEditt_01', date1)
        setattr(self.ui, f'{self.vjb_prefix}_dateEditt_02', self.wc.setDateEdit(self.tab))

        # 시간 설정
        if self.ui.dict_set is not None:
            if self.is_stock:
                if '해외선물' in self.ui.dict_set['증권사'] and self.ui.dict_set['주식타임프레임']:
                    starttime = '093000'
                else:
                    starttime = '090000'
                endtime = str_hms(timedelta_sec(-120, dt_hms(str(self.ui.dict_set['주식전략종료시간'])))).zfill(6)
                tujagm = str(self.ui.dict_set['주식투자금'])
            else:
                starttime = '000000'
                endtime = str_hms(timedelta_sec(-120, dt_hms(str(self.ui.dict_set['코인전략종료시간'])))).zfill(6)
                tujagm = str(self.ui.dict_set['코인투자금'])
        else:
            starttime = '090000' if self.is_stock else '000000'
            endtime = '093000' if self.is_stock else '235000'
            tujagm = '20.0'

        setattr(self.ui, f'{self.vjb_prefix}_lineEditt_02', self.wc.setLineedit(self.tab, ltext=starttime, style=style_bc_dk))
        setattr(self.ui, f'{self.vjb_prefix}_lineEditt_03', self.wc.setLineedit(self.tab, ltext=endtime, style=style_bc_dk))
        setattr(self.ui, f'{self.vjb_prefix}_lineEditt_04', self.wc.setLineedit(self.tab, ltext=tujagm, style=style_bc_dk))
        setattr(self.ui, f'{self.vjb_prefix}_lineEditt_05', self.wc.setLineedit(self.tab, ltext='30', style=style_bc_dk))

        setattr(self.ui, f'{self.list_prefix}_datedt_list',
                [getattr(self.ui, f'{self.vjb_prefix}_labelllll_01'), getattr(self.ui, f'{self.vjb_prefix}_dateEditt_01'),
                 getattr(self.ui, f'{self.vjb_prefix}_dateEditt_02'), getattr(self.ui, f'{self.vjb_prefix}_lineEditt_05')])

        # 에디터 버튼들
        editer_buttons = [
            ('전략 편집기', lambda: stg_editer(self.ui, self.market_type), 5, '단축키(Alt+1)'),
            ('최적화 편집기', lambda: opti_editer(self.ui, self.market_type), 4, '단축키(Alt+2)'),
            ('테스트 편집기', lambda: opti_test_editer(self.ui, self.market_type), 4, '단축키(Alt+3)'),
            ('전진분석', lambda: rwf_test_editer(self.ui, self.market_type), 4, '단축키(Alt+4)'),
            ('GA 편집기', lambda: opti_ga_editer(self.ui, self.market_type), 4, '단축키(Alt+5)'),
            ('조건 편집기', lambda: cond_editer(self.ui, self.market_type), 4, '단축키(Alt+6)'),
            ('범위 편집기', lambda: opti_vars_editer(self.ui, self.market_type), 4, '단축키(Alt+7)'),
            ('변수 편집기', lambda: vars_editer(self.ui, self.market_type), 4, '단축키(Alt+8)'),
            ('백테스트 로그', lambda: backtest_log(self.ui, self.market_type), 4, '단축키(Alt+9)'),
            ('상세기록', lambda: backtest_detail(self.ui, self.market_type), 4, '단축키(Alt+0)'),
        ]

        btn_indices = [9, 8, 7, 6, 10, 11, 12, 13, 14, 15]
        editer_list = []
        for idx, (text, handler, color, tip) in zip(btn_indices, editer_buttons):
            btn = self.wc.setPushbutton(text, parent=self.tab, bounced=True, click=handler, color=color, tip=tip)
            setattr(self.ui, f'{self.vj_prefix}_pushButton_{idx:02d}', btn)
            editer_list.append(btn)

        setattr(self.ui, f'{self.list_prefix}_editer_list', editer_list)

    def _setup_optimization(self):
        """최적화 설정"""
        opti_start_method = self.ui.CoinOptiStart if self.is_coin else self.ui.StockOptiStart

        # 매수/변수범위 콤보 및 라인에딧
        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_01',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_03(self.ui, self.market_type)))
        setattr(self.ui, f'{self.vc_prefix}_lineEdittt_01',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F2, F3', style=style_bc_dk))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_01',
                self.wc.setPushbutton('최적화 매수전략 로딩(F1)', parent=self.tab, bounced=True,
                                      click=lambda: opti_buy_load(self.ui, self.market_type), color=1,
                                      tip='작성된 최적화 매수전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_02',
                self.wc.setPushbutton('최적화 매수전략 저장(F4)', parent=self.tab, bounced=True,
                                      click=lambda: opti_buy_save(self.ui, self.market_type), color=1,
                                      tip='작성된 최적화 매수전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'))

        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_02',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_04(self.ui, self.market_type)))
        setattr(self.ui, f'{self.vc_prefix}_lineEdittt_02',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F10, F11', style=style_bc_dk))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_03',
                self.wc.setPushbutton('최적화 변수범위 로딩(F9)', parent=self.tab, bounced=True,
                                      click=lambda: opti_vars_load(self.ui, self.market_type), color=1,
                                      tip='작성된 최적화 변수설정을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_04',
                self.wc.setPushbutton('최적화 변수범위 저장(F12)', parent=self.tab, bounced=True,
                                      click=lambda: opti_vars_save(self.ui, self.market_type), color=1,
                                      tip='작성된 최적화 변수설정을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'))

        # 기간 설정
        setattr(self.ui, f'{self.vc_prefix}_labellllll_01',
                QLabel('▣ 일반은 학습기간, 검증은 검증기간, 테스트는 확인기간까지 선택', self.tab))
        setattr(self.ui, f'{self.vc_prefix}_labellllll_02',
                QLabel('최적화 학습기간                   검증기간                   확인기간', self.tab))
        getattr(self.ui, f'{self.vc_prefix}_labellllll_02').setToolTip('모든 기간은 주단위로 입력하십시오.')
        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_03', self.wc.setCombobox(self.tab, items=train_period))
        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_04', self.wc.setCombobox(self.tab, items=valid_period))
        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_05', self.wc.setCombobox(self.tab, items=test_period))
        setattr(self.ui, f'{self.vc_prefix}_labellllll_03',
                QLabel('최적화 실행횟수                   기준값', self.tab))
        getattr(self.ui, f'{self.vc_prefix}_labellllll_03').setToolTip( f'최적화 횟수 0선택 시 최적값이 변하지 않을 때까지 반복됩니다.\n{optistandard}')
        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_06', self.wc.setCombobox(self.tab, items=optimized_count))
        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_07', self.wc.setCombobox(self.tab, items=opti_standard))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_05',
                self.wc.setPushbutton('기준값', color=2, parent=self.tab, bounced=True,
                                      click=lambda: opti_std(self.ui),
                                      tip='백테 결과값 중 특정 수치를 만족하지 못하면\n기준값을 0으로 도출하도록 설정한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_36',
                self.wc.setPushbutton('optuna', color=3, parent=self.tab, bounced=True,
                                      click=lambda: opti_optuna(self.ui),
                                      tip='옵튜나의 샘플러를 선택하거나 대시보드를 열람한다'))

        setattr(self.ui, f'{self.list_prefix}_period_list',
                [getattr(self.ui, f'{self.vc_prefix}_labellllll_01'), getattr(self.ui, f'{self.vc_prefix}_labellllll_02'),
                 getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_03'), getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_04'),
                 getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_05'), getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_06'),
                 getattr(self.ui, f'{self.vc_prefix}_labellllll_03'), getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_07'),
                 getattr(self.ui, f'{self.vc_prefix}_pushButton_05'), getattr(self.ui, f'{self.vc_prefix}_pushButton_36')])

        for widget in getattr(self.ui, f'{self.list_prefix}_period_list'):
            widget.setVisible(False)

        # 그리드 최적화 버튼
        opti_tip_base = '''Alt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작한다.
Ctrl+Shift와 함께 누르면 매수변수만 최적화한다.
Ctrl+Alt와 함께 누르면 매도변수만 최적화한다.'''

        opti_grid_tips = {
            'OVC': f'학습기간과 검증기간을 선택하여 진행되며\n검증 최적화는 1회만 검증을 하지만, 교차검증은\n검증기간을 학습기간 / 검증기간 만큼 교차분류하여 그리드 최적화한다.\n{opti_tip_base}',
            'OV': f'학습기간과 검증기간을 선택하여 진행되며\n데이터의 시계열 순서대로 학습, 검증기간을 분류하여 그리드 최적화한다.\n{opti_tip_base}',
            'O': f'학습기간만 선택하여 진행되며\n데이터 전체를 기반으로 그리드 최적화한다.\n{opti_tip_base}'
        }

        setattr(self.ui, f'{self.vc_prefix}_pushButton_06',
                self.wc.setPushbutton('교차검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화OVC', color=2, tip=opti_grid_tips['OVC']))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_07',
                self.wc.setPushbutton('검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화OV', color=2, tip=opti_grid_tips['OV']))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_08',
                self.wc.setPushbutton('그리드', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화O', color=2, tip=opti_grid_tips['O']))

        # 베이지안 최적화 버튼
        opti_bayes_tips = {
            'BVC': f'학습기간과 검증기간을 선택하여 진행되며\n검증 최적화는 1회만 검증을 하지만, 교차검증은\n검증기간을 학습기간 / 검증기간 만큼 교차분류하여 베이지안 최적화한다.\n{opti_tip_base}',
            'BV': f'학습기간과 검증기간을 선택하여 진행되며\n데이터의 시계열 순서대로 학습, 검증기간을 분류하여 베이지안 최적화한다.\n{opti_tip_base}',
            'B': f'학습기간만 선택하여 진행되며\n데이터 전체를 기반으로 베이지안 최적화한다.\n{opti_tip_base}'
        }

        setattr(self.ui, f'{self.vc_prefix}_pushButton_27',
                self.wc.setPushbutton('교차검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화BVC', color=3, tip=opti_bayes_tips['BVC']))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_28',
                self.wc.setPushbutton('검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화BV', color=3, tip=opti_bayes_tips['BV']))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_29',
                self.wc.setPushbutton('베이지안', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화B', color=3, tip=opti_bayes_tips['B']))

        # 매도 전략 설정
        setattr(self.ui, f'{self.vc_prefix}_comboBoxxx_08',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_05(self.ui, self.market_type)))
        setattr(self.ui, f'{self.vc_prefix}_lineEdittt_03',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F6, F7', style=style_bc_dk))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_09',
                self.wc.setPushbutton('최적화 매도전략 로딩(F5)', parent=self.tab, bounced=True,
                                      click=lambda: opti_sell_load(self.ui, self.market_type), color=1,
                                      tip='작성된 최적화 매도전략을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_10',
                self.wc.setPushbutton('최적화 매도전략 저장(F8)', parent=self.tab, bounced=True,
                                      click=lambda: opti_sell_save(self.ui, self.market_type), color=1,
                                      tip='작성된 최적화 매도전략을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'))
        setattr(self.ui, f'{self.vc_prefix}_labellllll_04', QLabel(optitext, self.tab))
        getattr(self.ui, f'{self.vc_prefix}_labellllll_04').setFont(qfont13)
        setattr(self.ui, f'{self.vc_prefix}_pushButton_11',
                self.wc.setPushbutton('예제', parent=self.tab, bounced=True,
                                      click=lambda: opti_sample(self.ui, self.market_type), color=3))

        # 매수/매도 저장 버튼
        setattr(self.ui, f'{self.vc_prefix}_lineEdittt_04',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, visible=False, style=style_bc_dk))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_13',
                self.wc.setPushbutton('매수전략으로 저장', parent=self.tab, bounced=True,
                                      click=lambda: opti_to_buy_save(self.ui, self.market_type), color=1, visible=False,
                                      tip='최적값으로 백테용 매수전략으로 저장한다.'))
        setattr(self.ui, f'{self.vc_prefix}_lineEdittt_05',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, visible=False, style=style_bc_dk))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_14',
                self.wc.setPushbutton('매도전략으로 저장', parent=self.tab, bounced=True,
                                      click=lambda: opti_to_sell_save(self.ui, self.market_type), color=1, visible=False,
                                      tip='최적값으로 백테용 매도전략으로 저장한다.'))

        # optimz 리스트
        optimz_items = [
            getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_01'), getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_02'),
            getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_03'), getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_08'),
            getattr(self.ui, f'{self.vc_prefix}_lineEdittt_01'), getattr(self.ui, f'{self.vc_prefix}_lineEdittt_02'),
            getattr(self.ui, f'{self.vc_prefix}_lineEdittt_03'), getattr(self.ui, f'{self.vc_prefix}_labellllll_04'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_01'), getattr(self.ui, f'{self.vc_prefix}_pushButton_02'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_03'), getattr(self.ui, f'{self.vc_prefix}_pushButton_04'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_06'), getattr(self.ui, f'{self.vc_prefix}_pushButton_07'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_08'), getattr(self.ui, f'{self.vc_prefix}_pushButton_09'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_10'), getattr(self.ui, f'{self.vc_prefix}_pushButton_11'),
            getattr(self.ui, f'{self.vc_prefix}_lineEdittt_04'), getattr(self.ui, f'{self.vc_prefix}_lineEdittt_05'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_13'), getattr(self.ui, f'{self.vc_prefix}_pushButton_14'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_27'), getattr(self.ui, f'{self.vc_prefix}_pushButton_28'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_29')
        ]
        setattr(self.ui, f'{self.list_prefix}_optimz_list', optimz_items)

        for widget in getattr(self.ui, f'{self.list_prefix}_optimz_list'):
            widget.setVisible(False)

    def _setup_optest_buttons(self):
        """최적화 테스트 버튼 설정"""
        opti_start_method = self.ui.CoinOptiStart if self.is_coin else self.ui.StockOptiStart

        test_tip = 'Alt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작한다.'

        setattr(self.ui, f'{self.vc_prefix}_pushButton_15',
                self.wc.setPushbutton('교차검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화OVCT', color=2,
                                      tip=f'학습기간, 검증기간, 확인기간을 선택하여 진행되며\n그리드 교차검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.\n{test_tip}'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_16',
                self.wc.setPushbutton('검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화OVT', color=2,
                                      tip=f'학습기간, 검증기간, 확인기간을 선택하여 진행되며\n그리드 검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.\n{test_tip}'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_17',
                self.wc.setPushbutton('그리드', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화OT', color=2,
                                      tip=f'학습기간, 확인기간을 선택하여 진행되며\n그리드 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.\n{test_tip}'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_30',
                self.wc.setPushbutton('교차검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화BVCT', color=3,
                                      tip='학습기간, 검증기간, 확인기간을 선택하여 진행되며\n베이지안 교차검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_31',
                self.wc.setPushbutton('검증', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화BVT', color=3,
                                      tip='학습기간, 검증기간, 확인기간을 선택하여 진행되며\n베이지안 검증 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_32',
                self.wc.setPushbutton('베이지안', parent=self.tab, bounced=True, click=opti_start_method,
                                      cmd='최적화BT', color=3,
                                      tip='학습기간, 확인기간을 선택하여 진행되며\n베이지안 최적화로 구한 최적값을 확인기간에 대하여 테스트한다.'))

        optest_items = [
            getattr(self.ui, f'{self.vc_prefix}_pushButton_15'), getattr(self.ui, f'{self.vc_prefix}_pushButton_16'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_17'), getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_02'),
            getattr(self.ui, f'{self.vc_prefix}_lineEdittt_02'), getattr(self.ui, f'{self.vc_prefix}_pushButton_03'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_04'), getattr(self.ui, f'{self.vc_prefix}_pushButton_30'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_31'), getattr(self.ui, f'{self.vc_prefix}_pushButton_32')
        ]
        setattr(self.ui, f'{self.list_prefix}_optest_list', optest_items)

        for widget in getattr(self.ui, f'{self.list_prefix}_optest_list'):
            widget.setVisible(False)

    def _setup_rwft_buttons(self):
        """전진분석 버튼 설정"""
        opti_rwft_method = self.ui.CoinOptiRwftStart if self.is_coin else self.ui.StockOptiRwftStart

        test_tip = 'Alt키와 함께 누르면 모든 변수의 최적값을 랜덤 변경하여 시작한다.'

        setattr(self.ui, f'{self.vc_prefix}_pushButton_18',
                self.wc.setPushbutton('교차검증', parent=self.tab, bounced=True, click=opti_rwft_method,
                                      cmd='전진분석ORVC', color=2,
                                      tip=f'학습기간, 확인기간, 전체기간을 선택하여 진행되며\n그리드 교차검증 최적화 테스트를 전진분석한다.\n{test_tip}'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_19',
                self.wc.setPushbutton('검증', parent=self.tab, bounced=True, click=opti_rwft_method,
                                      cmd='전진분석ORV', color=2,
                                      tip=f'학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n그리드 검증 최적화 테스트를 전진분석한다.\n{test_tip}'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_20',
                self.wc.setPushbutton('그리드', parent=self.tab, bounced=True, click=opti_rwft_method,
                                      cmd='전진분석OR', color=2,
                                      tip=f'학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n그리드 최적화 테스트를 전진분석한다.\n{test_tip}'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_33',
                self.wc.setPushbutton('교차검증', parent=self.tab, bounced=True, click=opti_rwft_method,
                                      cmd='전진분석BRVC', color=3,
                                      tip='학습기간, 확인기간, 전체기간을 선택하여 진행되며\n베이지안 교차검증 최적화 테스트를 전진분석한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_34',
                self.wc.setPushbutton('검증', parent=self.tab, bounced=True, click=opti_rwft_method,
                                      cmd='전진분석BRV', color=3,
                                      tip='학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n베이지안 검증 최적화 테스트를 전진분석한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_35',
                self.wc.setPushbutton('베이지안', parent=self.tab, bounced=True, click=opti_rwft_method,
                                      cmd='전진분석BR', color=3,
                                      tip='학습기간, 검증기간, 확인기간, 전체기간을 선택하여 진행되며\n베이지안 최적화 테스트를 전진분석한다.'))

        rwftvd_items = [
            getattr(self.ui, f'{self.vc_prefix}_pushButton_18'), getattr(self.ui, f'{self.vc_prefix}_pushButton_19'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_20'), getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_02'),
            getattr(self.ui, f'{self.vc_prefix}_lineEdittt_02'), getattr(self.ui, f'{self.vc_prefix}_pushButton_03'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_04'), getattr(self.ui, f'{self.vjb_prefix}_labelllll_01'),
            getattr(self.ui, f'{self.vjb_prefix}_dateEditt_01'), getattr(self.ui, f'{self.vjb_prefix}_dateEditt_02'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_33'), getattr(self.ui, f'{self.vc_prefix}_pushButton_34'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_35')
        ]
        setattr(self.ui, f'{self.list_prefix}_rwftvd_list', rwftvd_items)

        for widget in getattr(self.ui, f'{self.list_prefix}_rwftvd_list'):
            if widget not in (getattr(self.ui, f'{self.vjb_prefix}_labelllll_01'), 
                              getattr(self.ui, f'{self.vjb_prefix}_dateEditt_01'),
                              getattr(self.ui, f'{self.vjb_prefix}_dateEditt_02')):
                widget.setVisible(False)

        # 빈 라벨
        setattr(self.ui, f'{self.vc_prefix}_labellllll_05', QLabel('', self.tab))
        getattr(self.ui, f'{self.vc_prefix}_labellllll_05').setVisible(False)

    def _setup_ga_optimization(self):
        """GA 최적화 설정"""
        opti_ga_method = self.ui.CoinOptiGaStart if self.is_coin else self.ui.StockOptiGaStart

        setattr(self.ui, f'{self.va_prefix}_pushButton_01',
                self.wc.setPushbutton('교차검증 GA 최적화', parent=self.tab, bounced=True, click=opti_ga_method,
                                      cmd='최적화OGVC', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n교차 검증 GA최적화한다.'))
        setattr(self.ui, f'{self.va_prefix}_pushButton_02',
                self.wc.setPushbutton('검증 GA 최적화', parent=self.tab, bounced=True, click=opti_ga_method,
                                      cmd='최적화OGV', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n검증 GA최적화한다.'))
        setattr(self.ui, f'{self.va_prefix}_pushButton_03',
                self.wc.setPushbutton('GA 최적화', parent=self.tab, bounced=True, click=opti_ga_method,
                                      cmd='최적화OG', color=2, tip='학습기간을 선택하여 진행되며\n데이터 전체를 사용하여 GA최적화한다.'))

        setattr(self.ui, f'{self.va_prefix}_comboBoxxx_01',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_06(self.ui, self.market_type)))
        setattr(self.ui, f'{self.va_prefix}_lineEdittt_01',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F10, F11', style=style_bc_dk))
        setattr(self.ui, f'{self.va_prefix}_pushButton_04',
                self.wc.setPushbutton('GA 변수범위 로딩(F9)', parent=self.tab, bounced=True,
                                      click=lambda: gavars_load(self.ui, self.market_type), color=1,
                                      tip='작성된 변수범위를 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'))
        setattr(self.ui, f'{self.va_prefix}_pushButton_05',
                self.wc.setPushbutton('GA 변수범위 저장(F12)', parent=self.tab, bounced=True,
                                      click=lambda: gavars_save(self.ui, self.market_type), color=1,
                                      tip='작성된 변수범위를 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'))

        gaopti_items = [
            getattr(self.ui, f'{self.va_prefix}_pushButton_01'), getattr(self.ui, f'{self.va_prefix}_pushButton_02'),
            getattr(self.ui, f'{self.va_prefix}_pushButton_03'), getattr(self.ui, f'{self.va_prefix}_comboBoxxx_01'),
            getattr(self.ui, f'{self.va_prefix}_lineEdittt_01'), getattr(self.ui, f'{self.va_prefix}_pushButton_04'),
            getattr(self.ui, f'{self.va_prefix}_pushButton_05'), getattr(self.ui, f'{self.vc_prefix}_labellllll_04')
        ]
        setattr(self.ui, f'{self.list_prefix}_gaopti_list', gaopti_items)

        for widget in getattr(self.ui, f'{self.list_prefix}_gaopti_list'):
            widget.setVisible(False)

    def _setup_area_editors(self):
        """범위 에디터 설정"""
        setattr(self.ui, f'{self.vc_prefix}_pushButton_21',
                self.wc.setPushbutton('최적화 > GA 범위 변환', parent=self.tab, bounced=True,
                                      click=lambda: optivars_to_gavars(self.ui, self.market_type), color=2, visible=False,
                                      tip='최적화용 범위코드를 GA용으로 변환한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_22',
                self.wc.setPushbutton('GA > 최적화 범위 변환', parent=self.tab, bounced=True,
                                      click=lambda: gavars_to_optivars(self.ui, self.market_type), color=2, visible=False,
                                      tip='GA용 범위코드를 최적화용으로 변환한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_23',
                self.wc.setPushbutton('변수 키값 재정렬', parent=self.tab, bounced=True,
                                      click=lambda: stgvars_key_sort(self.ui, self.market_type), color=2, visible=False,
                                      tip='범위 변수 self.vars의 키값을 재정렬한다.'))

        areaedit_items = [
            getattr(self.ui, f'{self.vc_prefix}_pushButton_21'), getattr(self.ui, f'{self.vc_prefix}_pushButton_22'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_23')
        ]
        setattr(self.ui, f'{self.list_prefix}_areaedit_list', areaedit_items)

    def _setup_vars_editors(self):
        """변수 에디터 설정"""
        setattr(self.ui, f'{self.vc_prefix}_pushButton_24',
                self.wc.setPushbutton('최적화 변수 변환(매수우선)', parent=self.tab, bounced=True,
                                      click=lambda: stg_vars_change(self.ui, self.market_type), color=2, visible=False,
                                      tip='일반 전략의 각종 변수를 매수우선 최적화용 변수로 변환한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_25',
                self.wc.setPushbutton('최적화 변수 변환(매도우선)', parent=self.tab, bounced=True,
                                      click=lambda: stg_vars_change(self.ui, self.market_type), color=2, visible=False,
                                      tip='일반 전략의 각종 변수를 매도우선 최적화용 변수로 변환한다.'))
        setattr(self.ui, f'{self.vc_prefix}_pushButton_26',
                self.wc.setPushbutton('변수 키값 재정렬', parent=self.tab, bounced=True,
                                      click=lambda: optivars_key_sort(self.ui, self.market_type), color=2, visible=False,
                                      tip='변수 self.vars의 키값을 재정렬한다.\n매수, 매도 self.vars의 첫번째 키값을 비교해서\n매수가 빠르면 매수우선, 매도가 빠르면 매도우선으로 재정렬된다.'))

        varsedit_items = [
            getattr(self.ui, f'{self.vc_prefix}_pushButton_24'), getattr(self.ui, f'{self.vc_prefix}_pushButton_25'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_26')
        ]
        setattr(self.ui, f'{self.list_prefix}_varsedit_list', varsedit_items)

    def _setup_condition_optimization(self):
        """조건 최적화 설정"""
        opti_cond_method = self.ui.CoinOptiCondStart if self.is_coin else self.ui.StockOptiCondStart

        setattr(self.ui, f'{self.vo_prefix}_comboBoxxx_01',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_07(self.ui, self.market_type)))
        setattr(self.ui, f'{self.vo_prefix}_lineEdittt_01',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F2, F3', style=style_bc_dk))
        setattr(self.ui, f'{self.vo_prefix}_pushButton_01',
                self.wc.setPushbutton('매수조건 로딩(F1)', parent=self.tab, bounced=True,
                                      click=lambda: condbuy_load(self.ui, self.market_type), color=1,
                                      tip='작성된 매수조건을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'))
        setattr(self.ui, f'{self.vo_prefix}_pushButton_02',
                self.wc.setPushbutton('매수조건 저장(F4)', parent=self.tab, bounced=True,
                                      click=lambda: condbuy_save(self.ui, self.market_type), color=1,
                                      tip='작성된 매수조건을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'))
        setattr(self.ui, f'{self.vo_prefix}_comboBoxxx_02',
                self.wc.setCombobox(self.tab, font=qfont14, activated=lambda: ui_activated_stg.activated_08(self.ui, self.market_type)))
        setattr(self.ui, f'{self.vo_prefix}_lineEdittt_02',
                self.wc.setLineedit(self.tab, font=qfont14, aleft=True, ltext='F6, F7', style=style_bc_dk))
        setattr(self.ui, f'{self.vo_prefix}_pushButton_03',
                self.wc.setPushbutton('매도조건 로딩(F5)', parent=self.tab, bounced=True,
                                      click=lambda: condsell_load(self.ui, self.market_type), color=1,
                                      tip='작성된 매도조건을 로딩한다.\nCtrl 키와 함께 누르면 버전관리 상태로 전환합니다.'))
        setattr(self.ui, f'{self.vo_prefix}_pushButton_04',
                self.wc.setPushbutton('매도조건 저장(F8)', parent=self.tab, bounced=True,
                                      click=lambda: condsell_save(self.ui, self.market_type), color=1,
                                      tip='작성된 매도조건을 저장한다.\nCtrl 키와 함께 누르면 코드 테스트 과정을 생략한다.'))

        setattr(self.ui, f'{self.vo_prefix}_labellllll_04',
                QLabel('매수조건수                     매도조건수                    최적화횟수', self.tab))
        setattr(self.ui, f'{self.vo_prefix}_lineEdittt_03', self.wc.setLineedit(self.tab, ltext='10', style=style_bc_dk))
        setattr(self.ui, f'{self.vo_prefix}_lineEdittt_04', self.wc.setLineedit(self.tab, ltext='5', style=style_bc_dk))
        setattr(self.ui, f'{self.vo_prefix}_lineEdittt_05', self.wc.setLineedit(self.tab, ltext='1000', style=style_bc_dk))

        setattr(self.ui, f'{self.vo_prefix}_pushButton_05',
                self.wc.setPushbutton('교차검증 조건 최적화', parent=self.tab, bounced=True, click=opti_cond_method,
                                      cmd='최적화OCVC', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n교차 검증 조건최적화한다.'))
        setattr(self.ui, f'{self.vo_prefix}_pushButton_06',
                self.wc.setPushbutton('검증 조건 최적화', parent=self.tab, bounced=True, click=opti_cond_method,
                                      cmd='최적화OCV', color=2, tip='학습기간과 검증기간을 선택하여 진행되며\n검증 조건최적화한다.'))
        setattr(self.ui, f'{self.vo_prefix}_pushButton_07',
                self.wc.setPushbutton('조건 최적화', parent=self.tab, bounced=True, click=opti_cond_method,
                                      cmd='최적화OC', color=2, tip='학습기간을 선택하여 진행되며\n데이터 전체를 사용하여 조건최적화한다.'))
        setattr(self.ui, f'{self.vo_prefix}_pushButton_08',
                self.wc.setPushbutton('예제', parent=self.tab, bounced=True,
                                      click=lambda: opti_sample(self.ui, self.market_type), color=3))

        opcond_items = [
            getattr(self.ui, f'{self.prefix}_textEditttt_07'), getattr(self.ui, f'{self.prefix}_textEditttt_08'),
            getattr(self.ui, f'{self.vo_prefix}_comboBoxxx_01'), getattr(self.ui, f'{self.vo_prefix}_lineEdittt_01'),
            getattr(self.ui, f'{self.vo_prefix}_pushButton_01'), getattr(self.ui, f'{self.vo_prefix}_pushButton_02'),
            getattr(self.ui, f'{self.vo_prefix}_comboBoxxx_02'), getattr(self.ui, f'{self.vo_prefix}_lineEdittt_02'),
            getattr(self.ui, f'{self.vo_prefix}_pushButton_03'), getattr(self.ui, f'{self.vo_prefix}_pushButton_04'),
            getattr(self.ui, f'{self.vo_prefix}_pushButton_05'), getattr(self.ui, f'{self.vo_prefix}_pushButton_06'),
            getattr(self.ui, f'{self.vo_prefix}_pushButton_07'), getattr(self.ui, f'{self.vo_prefix}_labellllll_04'),
            getattr(self.ui, f'{self.vo_prefix}_lineEdittt_03'), getattr(self.ui, f'{self.vo_prefix}_lineEdittt_04'),
            getattr(self.ui, f'{self.vo_prefix}_lineEdittt_05'), getattr(self.ui, f'{self.vo_prefix}_pushButton_08'),
            getattr(self.ui, f'{self.vc_prefix}_labellllll_04')
        ]
        setattr(self.ui, f'{self.list_prefix}_opcond_list', opcond_items)

        for widget in getattr(self.ui, f'{self.list_prefix}_opcond_list'):
            widget.setVisible(False)

        # load 리스트
        load_items = [
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_01'), getattr(self.ui, f'{self.vjs_prefix}_pushButon_01'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_01'), getattr(self.ui, f'{self.vc_prefix}_pushButton_03'),
            getattr(self.ui, f'{self.vc_prefix}_pushButton_09'), getattr(self.ui, f'{self.va_prefix}_pushButton_04'),
            getattr(self.ui, f'{self.vo_prefix}_pushButton_01'), getattr(self.ui, f'{self.vo_prefix}_pushButton_03')
        ]
        setattr(self.ui, f'{self.list_prefix}_load_list', load_items)

    def _setup_geometries(self):
        """UI 위치 설정"""
        # 텍스트 에디터
        geometries = [
            (f'{self.prefix}_textEditttt_01', 7, 10, 1000, 463),
            (f'{self.prefix}_textEditttt_02', 7, 480, 1000, 272),
            (f'{self.prefix}_textEditttt_03', 509, 10, 497, 463),
            (f'{self.prefix}_textEditttt_04', 509, 480, 497, 272),
            (f'{self.prefix}_textEditttt_05', 659, 10, 347, 740),
            (f'{self.prefix}_textEditttt_06', 659, 10, 347, 740),
            (f'{self.prefix}_textEditttt_07', 7, 10, 497, 740),
            (f'{self.prefix}_textEditttt_08', 509, 10, 497, 740),
            (f'{self.prefix}_textEditttt_10', 509, 40, 497, 700),
        ]
        for name, x, y, w, h in geometries:
            getattr(self.ui, name).setGeometry(x, y, w, h)

        # 버전 관리
        getattr(self.ui, f'{self.prefix}_comboBoxxxx_41').setGeometry(7, 10, 497, 25)
        getattr(self.ui, f'{self.prefix}_comboBoxxxx_42').setGeometry(509, 10, 400, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_41').setGeometry(914, 10, 92, 25)

        # 확대 버튼
        getattr(self.ui, f'{self.zoom_prefix}oo_pushButon_01').setGeometry(937, 15, 50, 20)
        getattr(self.ui, f'{self.zoom_prefix}oo_pushButon_02').setGeometry(937, 483, 50, 20)

        # 상세 기록
        getattr(self.ui, f'{self.prefix}_tableWidget_01').setGeometry(7, 40, 1000, 713)
        getattr(self.ui, f'{self.prefix}_comboBoxxxx_01').setGeometry(7, 10, 150, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_01').setGeometry(162, 10, 100, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_02').setGeometry(267, 10, 55, 25)
        getattr(self.ui, f'{self.prefix}_comboBoxxxx_02').setGeometry(327, 10, 150, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_03').setGeometry(482, 10, 100, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_04').setGeometry(587, 10, 55, 25)
        getattr(self.ui, f'{self.prefix}_comboBoxxxx_03').setGeometry(647, 10, 150, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_05').setGeometry(802, 10, 100, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_06').setGeometry(907, 10, 55, 25)
        getattr(self.ui, f'{self.prefix}_pushButtonn_07').setGeometry(967, 10, 40, 25)

        # 백로그
        getattr(self.ui, f'{self.prefix}_textEditttt_09').setGeometry(7, 10, 1000, 703)
        getattr(self.ui, f'{self.prefix}_progressBar_01').setGeometry(7, 718, 830, 30)
        getattr(self.ui, f'{self.prefix}_pushButtonn_08').setGeometry(842, 718, 165, 30)

        # 매수 전략
        getattr(self.ui, f'{self.vjb_prefix}_comboBoxx_01').setGeometry(1012, 10, 165, 25)
        getattr(self.ui, f'{self.vjb_prefix}_lineEditt_01').setGeometry(1182, 10, 165, 25)
        for i in range(1, 13):
            y_pos = 40 + int((i - 1) // 2 * 35)
            getattr(self.ui, f'{self.vjb_prefix}_pushButon_{i:02d}').setGeometry(1012 if i % 2 == 1 else 1182, y_pos, 165, 30)

        # 백테스트 버튼
        getattr(self.ui, f'{self.vj_prefix}_pushButton_01').setGeometry(1012, 335, 165, 30)
        getattr(self.ui, f'{self.vj_prefix}_pushButton_02').setGeometry(1012, 370, 165, 30)
        getattr(self.ui, f'{self.vj_prefix}_pushButton_03').setGeometry(1012, 405, 80, 30)
        getattr(self.ui, f'{self.vj_prefix}_pushButton_04').setGeometry(1097, 405, 80, 30)

        # 매도 전략
        getattr(self.ui, f'{self.vjs_prefix}_comboBoxx_01').setGeometry(1012, 478, 165, 25)
        getattr(self.ui, f'{self.vjs_prefix}_lineEditt_01').setGeometry(1182, 478, 165, 25)
        for i in range(1, 15):
            y_pos = 508 + int((i - 1) // 2 * 35)
            getattr(self.ui, f'{self.vjs_prefix}_pushButon_{i:02d}').setGeometry(1012 if i % 2 == 1 else 1182, y_pos, 165, 30)

        # 시간 설정 라벨
        getattr(self.ui, f'{self.vjb_prefix}_labelllll_01').setGeometry(1012, 255, 340, 20)
        getattr(self.ui, f'{self.vjb_prefix}_labelllll_02').setGeometry(1012, 280, 340, 20)
        getattr(self.ui, f'{self.vjb_prefix}_labelllll_03').setGeometry(1012, 305, 335, 20)

        # 날짜/시간 설정
        getattr(self.ui, f'{self.vjb_prefix}_dateEditt_01').setGeometry(1112, 255, 110, 20)
        getattr(self.ui, f'{self.vjb_prefix}_dateEditt_02').setGeometry(1237, 255, 110, 20)
        getattr(self.ui, f'{self.vjb_prefix}_lineEditt_02').setGeometry(1167, 280, 60, 20)
        getattr(self.ui, f'{self.vjb_prefix}_lineEditt_03').setGeometry(1287, 280, 60, 20)
        getattr(self.ui, f'{self.vjb_prefix}_lineEditt_04').setGeometry(1167, 305, 60, 20)
        getattr(self.ui, f'{self.vjb_prefix}_lineEditt_05').setGeometry(1287, 305, 60, 20)

        # 에디터 버튼
        editer_positions = [
            (6, 1182, 335), (7, 1182, 370), (8, 1182, 405), (9, 1182, 440),
            (10, 1267, 335), (11, 1267, 370), (12, 1267, 405), (13, 1267, 440),
            (14, 1012, 440), (15, 1097, 440)
        ]
        for idx, x, y in editer_positions:
            getattr(self.ui, f'{self.vj_prefix}_pushButton_{idx:02d}').setGeometry(x, y, 80, 30)

        # 최적화 설정
        opti_positions = [
            (f'{self.vc_prefix}_comboBoxxx_01', 1012, 45, 165, 30),
            (f'{self.vc_prefix}_lineEdittt_01', 1182, 45, 165, 30),
            (f'{self.vc_prefix}_pushButton_01', 1012, 80, 165, 30),
            (f'{self.vc_prefix}_pushButton_02', 1182, 80, 165, 30),
            (f'{self.vc_prefix}_comboBoxxx_02', 1012, 115, 165, 30),
            (f'{self.vc_prefix}_lineEdittt_02', 1182, 115, 165, 30),
            (f'{self.vc_prefix}_pushButton_03', 1012, 150, 165, 30),
            (f'{self.vc_prefix}_pushButton_04', 1182, 150, 165, 30),
        ]
        for name, x, y, w, h in opti_positions:
            getattr(self.ui, name).setGeometry(x, y, w, h)

        # 기간 설정
        getattr(self.ui, f'{self.vc_prefix}_labellllll_01').setGeometry(1012, 250, 335, 25)
        getattr(self.ui, f'{self.vc_prefix}_labellllll_02').setGeometry(1012, 190, 335, 25)
        getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_03').setGeometry(1097, 190, 45, 25)
        getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_04').setGeometry(1197, 190, 45, 25)
        getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_05').setGeometry(1302, 190, 45, 25)
        getattr(self.ui, f'{self.vc_prefix}_labellllll_03').setGeometry(1012, 220, 335, 25)
        getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_06').setGeometry(1097, 220, 45, 25)
        getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_07').setGeometry(1187, 220, 55, 25)
        getattr(self.ui, f'{self.vc_prefix}_pushButton_05').setGeometry(1247, 220, 47, 25)
        getattr(self.ui, f'{self.vc_prefix}_pushButton_36').setGeometry(1299, 220, 48, 25)

        # 최적화 실행 버튼
        opti_btn_positions = [
            (6, 1012, 335), (7, 1012, 370), (8, 1012, 405),
            (27, 1097, 335), (28, 1097, 370), (29, 1097, 405),
        ]
        for idx, x, y in opti_btn_positions:
            getattr(self.ui, f'{self.vc_prefix}_pushButton_{idx:02d}').setGeometry(x, y, 80, 30)

        # 매도 최적화
        getattr(self.ui, f'{self.vc_prefix}_comboBoxxx_08').setGeometry(1012, 513, 165, 30)
        getattr(self.ui, f'{self.vc_prefix}_lineEdittt_03').setGeometry(1182, 513, 165, 30)
        getattr(self.ui, f'{self.vc_prefix}_pushButton_09').setGeometry(1012, 548, 165, 30)
        getattr(self.ui, f'{self.vc_prefix}_pushButton_10').setGeometry(1182, 548, 165, 30)
        getattr(self.ui, f'{self.vc_prefix}_labellllll_04').setGeometry(1012, 583, 335, 130)
        getattr(self.ui, f'{self.vc_prefix}_pushButton_11').setGeometry(1012, 718, 335, 30)

        # 저장 버튼
        getattr(self.ui, f'{self.vc_prefix}_lineEdittt_04').setGeometry(1012, 10, 165, 30)
        getattr(self.ui, f'{self.vc_prefix}_pushButton_13').setGeometry(1182, 10, 165, 30)
        getattr(self.ui, f'{self.vc_prefix}_lineEdittt_05').setGeometry(1012, 478, 165, 30)
        getattr(self.ui, f'{self.vc_prefix}_pushButton_14').setGeometry(1182, 478, 165, 30)

        # 테스트 버튼
        test_btn_positions = [
            (15, 1012, 335), (16, 1012, 370), (17, 1012, 405),
            (30, 1097, 335), (31, 1097, 370), (32, 1097, 405),
        ]
        for idx, x, y in test_btn_positions:
            getattr(self.ui, f'{self.vc_prefix}_pushButton_{idx:02d}').setGeometry(x, y, 80, 30)

        # 전진분석 버튼
        rwft_btn_positions = [
            (18, 1012, 335), (19, 1012, 370), (20, 1012, 405),
            (33, 1097, 335), (34, 1097, 370), (35, 1097, 405),
        ]
        for idx, x, y in rwft_btn_positions:
            getattr(self.ui, f'{self.vc_prefix}_pushButton_{idx:02d}').setGeometry(x, y, 80, 30)

        # GA 버튼
        getattr(self.ui, f'{self.va_prefix}_pushButton_01').setGeometry(1012, 335, 165, 30)
        getattr(self.ui, f'{self.va_prefix}_pushButton_02').setGeometry(1012, 370, 165, 30)
        getattr(self.ui, f'{self.va_prefix}_pushButton_03').setGeometry(1012, 405, 165, 30)
        getattr(self.ui, f'{self.va_prefix}_comboBoxxx_01').setGeometry(1012, 115, 165, 30)
        getattr(self.ui, f'{self.va_prefix}_lineEdittt_01').setGeometry(1182, 115, 165, 30)
        getattr(self.ui, f'{self.va_prefix}_pushButton_04').setGeometry(1012, 150, 165, 30)
        getattr(self.ui, f'{self.va_prefix}_pushButton_05').setGeometry(1182, 150, 165, 30)

        # 영역 에디터
        for i in range(21, 24):
            y_pos = 335 + (i-21) * 35
            getattr(self.ui, f'{self.vc_prefix}_pushButton_{i:02d}').setGeometry(1012, y_pos, 165, 30)

        # 변수 에디터
        for i in range(24, 27):
            y_pos = 335 + (i-24) * 35
            getattr(self.ui, f'{self.vc_prefix}_pushButton_{i:02d}').setGeometry(1012, y_pos, 165, 30)

        getattr(self.ui, f'{self.vc_prefix}_labellllll_05').setGeometry(1012, 150, 335, 40)

        # 조건 최적화
        getattr(self.ui, f'{self.vo_prefix}_comboBoxxx_01').setGeometry(1012, 10, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_lineEdittt_01').setGeometry(1182, 10, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_01').setGeometry(1012, 45, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_02').setGeometry(1182, 45, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_comboBoxxx_02').setGeometry(1012, 80, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_lineEdittt_02').setGeometry(1182, 80, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_03').setGeometry(1012, 115, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_04').setGeometry(1182, 115, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_labellllll_04').setGeometry(1012, 255, 335, 20)
        getattr(self.ui, f'{self.vo_prefix}_lineEdittt_03').setGeometry(1072, 255, 45, 20)
        getattr(self.ui, f'{self.vo_prefix}_lineEdittt_04').setGeometry(1197, 255, 45, 20)
        getattr(self.ui, f'{self.vo_prefix}_lineEdittt_05').setGeometry(1302, 255, 45, 20)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_05').setGeometry(1012, 335, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_06').setGeometry(1012, 370, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_07').setGeometry(1012, 405, 165, 30)
        getattr(self.ui, f'{self.vo_prefix}_pushButton_08').setGeometry(1012, 718, 335, 30)
