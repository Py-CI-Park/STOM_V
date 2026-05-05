
from ui.event_change.changed_checkbox import *
from ui.create_widget.set_style import style_bc_dk
from ui.event_click.button_clicked_settings import *
from PyQt5.QtWidgets import QLabel, QTabWidget, QWidget
from ui.event_activate import activated_etc, activated_stg
from ui.event_click.button_clicked_etc import lvbutton_clicked_01
from ui.event_click.button_clicked_show_dialog import show_pattern_dialog


class SetSetupTap:
    """설정 탭 설정 클래스입니다.
    일반설정과 주문설정 탭을 설정합니다.
    """
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """설정 탭을 설정합니다."""
        self.ui.set_tapWidgett_01 = QTabWidget(self.ui.sj_tab)

        self.ui.ssd_tab = QWidget()
        self.ui.sod_tab = QWidget()

        self.ui.sj_set_labelll_01 = QLabel('설정 관리', self.ui.sj_tab)
        self.ui.sj_set_comBoxx_01 = self.wc.setCombobox(self.ui.sj_tab, activated=lambda: activated_etc.dactivated_02(self.ui))
        self.ui.sj_set_pButton_01 = self.wc.setPushbutton('로딩', parent=self.ui.sj_tab, click=lambda: setting_all_load(self.ui))
        self.ui.sj_set_pButton_02 = self.wc.setPushbutton('설정', parent=self.ui.sj_tab, click=lambda: setting_all_app(self.ui))
        self.ui.sj_set_pButton_03 = self.wc.setPushbutton('삭제', parent=self.ui.sj_tab, click=lambda: setting_all_del(self.ui))
        self.ui.sj_set_liEditt_01 = self.wc.setLineedit(self.ui.sj_tab, style=style_bc_dk)
        self.ui.sj_set_pButton_04 = self.wc.setPushbutton('저장', parent=self.ui.sj_tab, click=lambda: setting_all_save(self.ui))

        self.ui.set_tapWidgett_01.addTab(self.ui.ssd_tab, '일반설정')
        self.ui.set_tapWidgett_01.addTab(self.ui.sod_tab, '주문설정')

        self.ui.sj_bs_groupBox_01 = self.wc.setQGroupBox(' 기본설정', self.ui.ssd_tab, hover=True)
        self.ui.sj_bs_groupBox_02 = self.wc.setQGroupBox(' 계정설정', self.ui.ssd_tab, hover=True)
        self.ui.sj_bs_groupBox_03 = self.wc.setQGroupBox(' 텔레그램', self.ui.ssd_tab, hover=True)
        self.ui.sj_bs_groupBox_04 = self.wc.setQGroupBox(' 전략설정', self.ui.ssd_tab, hover=True)
        self.ui.sj_bs_groupBox_05 = self.wc.setQGroupBox(' 백테설정', self.ui.ssd_tab, hover=True)
        self.ui.sj_bs_groupBox_06 = self.wc.setQGroupBox(' 기타설정', self.ui.ssd_tab, hover=True)

        # --------------------------------------------------------------------------------------------------------------

        from utility.settings.setting_market import DICT_MARKET_GUBUN
        self.ui.sj_main_labell_01 = QLabel('▣  거래소 선택', self.ui.sj_bs_groupBox_01)
        self.ui.sj_main_comBox_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, items=list(DICT_MARKET_GUBUN.keys()), tip='사용할 거래소를 선택하십시오.')
        self.ui.sj_main_cheBox_01 = self.wc.setCheckBox('모의투자', self.ui.sj_bs_groupBox_01, changed=lambda state: checkbox_changed_01(self.ui, state), tip='체크 해제 시 실매매')
        self.ui.sj_main_cheBox_02 = self.wc.setCheckBox('데이터저장', self.ui.sj_bs_groupBox_01, tip='전략종료 후 데이터 저장 여부를 설정한다.')
        self.ui.sj_main_cheBox_03 = self.wc.setCheckBox('알림소리', self.ui.sj_bs_groupBox_01, tip='시스템 이벤트를 tts를 통해 소리로 알려준다.')
        self.ui.sj_main_labell_02 = QLabel('▣  타임프레임 선택                                          ▣  프로그램 비밀번호', self.ui.sj_bs_groupBox_01)
        self.ui.sj_main_comBox_02 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, items=['1초스냅샷', '1분봉'], tip='사용할 타임프레임을 설정한다.')
        self.ui.sj_main_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_01, passhide=True)

        self.ui.sj_main_labell_03 = QLabel('▣  바이낸스선물                                                     마진타입                            포지션', self.ui.sj_bs_groupBox_01)
        self.ui.sj_lvrg_Button_01 = self.wc.setPushbutton('레버리지 유형 설정', parent=self.ui.sj_bs_groupBox_01, click=lambda: lvbutton_clicked_01(self.ui), tip='바이낸스 선물 레버리지를 고정, 변동 형태 중 선택하여 설정한다.')
        self.ui.sj_main_comBox_03 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, items=['격리', '교차'], activated=activated_stg.activated_10)
        self.ui.sj_main_comBox_04 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, items=['단방향', '양방향'], activated=activated_stg.activated_11)

        # --------------------------------------------------------------------------------------------------------------

        text = '▣  access key                                                                                  ' \
               '                                                                             ▣  secret key'
        self.ui.sj_accc_labell_01 = QLabel(text, self.ui.sj_bs_groupBox_02)
        self.ui.sj_accc_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)
        self.ui.sj_accc_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)

        # --------------------------------------------------------------------------------------------------------------

        text = '▣  bot token                                                                                   ' \
               '                                                                              ▣  chat id'
        self.ui.sj_tele_labell_01 = QLabel(text, self.ui.sj_bs_groupBox_03)
        self.ui.sj_tele_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_03, passhide=True)
        self.ui.sj_tele_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_03, passhide=True)

        # --------------------------------------------------------------------------------------------------------------

        text = '▣  매수전략                                       ' \
               '▣  매도전략                                          ' \
               '▣  평균값계산틱수                         ' \
               '▣  최대종목수                         ' \
               '▣  종료시간'
        self.ui.sj_strgy_label_01 = QLabel(text, self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_cbBox_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_04, activated=lambda: activated_stg.activated_09(self.ui))
        self.ui.sj_strgy_cbBox_02 = self.wc.setCombobox(self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_lEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_lEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_lEdit_03 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_ckBox_01 = self.wc.setCheckBox('잔고청산', self.ui.sj_bs_groupBox_04, tip='전략 종료 시 보유잔고를 시장가청산한다.')
        self.ui.sj_strgy_ckBox_02 = self.wc.setCheckBox('프로세스 종료', self.ui.sj_bs_groupBox_04, tip='전략 마감 후 리시버, 전략연산, 트레이더 프로세스를 종료한다.')
        self.ui.sj_strgy_ckBox_03 = self.wc.setCheckBox('컴퓨터 종료', self.ui.sj_bs_groupBox_04, tip='프로세스를 종료 후 컴퓨터를 종료한다.')

        self.ui.sj_strgy_ckBox_04 = self.wc.setCheckBox('종목당 투자금 고정   |', self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_label_02 = QLabel('', self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_lEdit_04 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04)

        self.ui.sj_strgy_ckBox_05 = self.wc.setCheckBox('손실중지 - 총자산 대비 수익률 (-)           %', self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_lEdit_05 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_ckBox_06 = self.wc.setCheckBox('수익중지 - 총자산 대비 수익률 (+)           %', self.ui.sj_bs_groupBox_04)
        self.ui.sj_strgy_lEdit_06 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04)

        # --------------------------------------------------------------------------------------------------------------

        self.ui.sj_back_cheBox_01 = self.wc.setCheckBox('백테스트 시 거래횟수 10회 이상이며 수익금이 마이너스일 경우 블랙리스트에 추가하기', self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_cheBox_02 = self.wc.setCheckBox('일괄 로딩(모든 종목의 데이터를 램에 올려두고 백테스트합니다. 백테속도↑, 램사용량↑)', self.ui.sj_bs_groupBox_05, changed=lambda state: checkbox_changed_03(self.ui, state))
        self.ui.sj_back_cheBox_03 = self.wc.setCheckBox('분할 로딩(피클덤프한 다음 한종목씩 램에 올려 백테스트합니다. 백테속도↓, 램사용량↓)', self.ui.sj_bs_groupBox_05, changed=lambda state: checkbox_changed_03(self.ui, state))
        self.ui.sj_back_cheBox_04 = self.wc.setCheckBox('데이터베이스 자동관리(일자DB분리, 백테DB추가)', self.ui.sj_bs_groupBox_05, tip='데이터 저장 후 일자별분리 및 백테디비추가가 자동실행됨')

        self.ui.sj_ilbunback_listtt = [self.ui.sj_back_cheBox_02, self.ui.sj_back_cheBox_03]

        self.ui.sj_back_cheBox_05 = self.wc.setCheckBox('스케쥴러 자동실행  |  요일                    시간', self.ui.sj_bs_groupBox_05, tip='백테 스케쥴러를 자동실행한다.')
        self.ui.sj_back_comBox_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_05, items=['금', '토', '일'])
        self.ui.sj_back_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_comBox_02 = self.wc.setCombobox(self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_cheBox_06 = self.wc.setCheckBox('스케쥴러 자동실행 전, 각종 분석 학습하기', self.ui.sj_bs_groupBox_05)

        self.ui.sj_back_labell_02 = QLabel(' ▣  엔진시작일자', self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_cheBox_07 = self.wc.setCheckBox('                  일전', self.ui.sj_bs_groupBox_05, changed=lambda state: checkbox_changed_07(self.ui, state))
        self.ui.sj_back_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_cheBox_08 = self.wc.setCheckBox('고정', self.ui.sj_bs_groupBox_05, changed=lambda state: checkbox_changed_08(self.ui, state))
        self.ui.sj_back_daEdit_01 = self.wc.setDateEdit(self.ui.sj_bs_groupBox_05)

        # --------------------------------------------------------------------------------------------------------------

        self.ui.sj_back_cheBox_09 = self.wc.setCheckBox('백테스트에 주문관리 설정 적용하기(최유리 및 IOC 주문 제외)', self.ui.sj_bs_groupBox_05, tip='설정 변경 시 백테엔진을 재로딩해야 합니다. 체크해제 시 시장가 호가범위선택 및 비중조절은 적용됨')
        self.ui.sj_back_cheBox_10 = self.wc.setCheckBox('교차검증 최적화에 최근 가중치 적용하기', self.ui.sj_bs_groupBox_05, tip='교차검증 최적화 시 최근데이터일수록 가중치를 줘서 기준값을 계산한다.')
        self.ui.sj_back_cheBox_11 = self.wc.setCheckBox('그리드 최적화 범위 자동 관리(고정 및 삭제)', self.ui.sj_bs_groupBox_05, tip='그리드 최적화 시에 범위에서 불필요한 값을 삭제하고\n범위의 기준값이 같을 경우 최적값으로 고정합니다.\n선택하지 않더라도 최소 및 최대가 최적값일 경우 자동으로 범위가 추가됩니다.')
        self.ui.sj_back_labell_01 = QLabel(' ▣  그리드 최적화 기준값 최소상승률                    %', self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_labell_01.setToolTip('그리드 최적화 시 직전 대비 기준값 상승률이 설정값보다 적을 경우 종료됩니다.\n0%로 설정 시 최고기준값을 갱신하지 못하면 최적화가 종료됩니다.')
        self.ui.sj_back_liEdit_03 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_cheBox_12 = self.wc.setCheckBox('백테스트 그래프 매수시간 기준으로 표시하기', self.ui.sj_bs_groupBox_05, tip='체크해제 시 매도시간 기준으로 표시됩니다.')
        self.ui.sj_back_cheBox_13 = self.wc.setCheckBox('백테스트로그 기록하지 않기', self.ui.sj_bs_groupBox_05)
        self.ui.sj_back_cheBox_14 = self.wc.setCheckBox('일반 백테스트 시 그래프 저장하지 않기', self.ui.sj_bs_groupBox_05, changed=lambda state: checkbox_changed_04(self.ui, state))
        self.ui.sj_back_cheBox_15 = self.wc.setCheckBox('띄우지 않기', self.ui.sj_bs_groupBox_05, changed=lambda state: checkbox_changed_05(self.ui, state))

        # --------------------------------------------------------------------------------------------------------------

        tip_text = "시장미시구조(microstructure)분석은 호가 데이터를 기반으로\n"\
                   "호가깊이비율, 불균형, 집중도, 압력레벨 및 각종 조작 패턴\n"\
                   "(레이어링, 펌프앤덤프, 아이스버그, 털기)을 분석하여\n"\
                   "시그널(buy, sell, hold), 신뢰도(0~1), 리스크(0~1)를 리턴합니다."
        self.ui.sj_back_cheBox_16 = self.wc.setCheckBox('1초스냅샷 전략에 시장미시구조분석 적용하기', self.ui.sj_bs_groupBox_05, tip=tip_text)
        tip_text = "리스크분석(risk_analyzer)은 체결 데이터를 기반으로\n"\
                   "RSI, 변동성, 모멘텀, 체결강도, 수량불균형, 가격위치,\n"\
                   "각도추세, 거래량추세를 분석하여 리스크점수(0~100)를 리턴합니다."
        self.ui.sj_back_cheBox_17 = self.wc.setCheckBox('1초스냅샷 전략에 리스크분석 적용하기', self.ui.sj_bs_groupBox_05, tip=tip_text)
        tip_text = "캔들분석(pattern_analyzer)은 talib 라이브러리에 있는\n"\
                   "60여개의 패턴을 활용하여 종목별 패턴 발생과 이후 등락율을 분석하여\n"\
                   "패턴점수(+100~-100) 및 패턴신뢰도(0~1)를 리턴합니다."
        self.ui.sj_back_cheBox_18 = self.wc.setCheckBox('1분봉 전략에 캔들분석 적용하기', self.ui.sj_bs_groupBox_05, tip=tip_text)
        tip_text = "가격대분석(volume_profile_analyzer)은 가격 데이터를 기반으로\n"\
                   "단위 분할한 가격대에서 기준 등락율 이상의 돌파 및 반등 이벤트를 분석하여\n"\
                   "가격대점수(+100~-100) 및 가격대신뢰도(0~1)를 리턴합니다."
        self.ui.sj_back_cheBox_19 = self.wc.setCheckBox('1분봉 전략에 가격대분석 적용하기', self.ui.sj_bs_groupBox_05, tip=tip_text)
        tip_text = "거래량분석(volume_spike_analyzer)은 거래량 데이터를 기반으로\n"\
                   "단위 분할한 거래량평균대비거래량별로 이후의 가격 움직임을 분석하여\n"\
                   "거래량점수(+100~-100) 및 거래량신뢰도(0~1)를 리턴합니다."
        self.ui.sj_back_cheBox_20 = self.wc.setCheckBox('1분봉 전략에 거래량분석 적용하기', self.ui.sj_bs_groupBox_05, tip=tip_text)
        tip_text = "변동성분석(volatility_analyzer)은 변동성 데이터를 기반으로\n"\
                   "단위 분할한 변동성별로 이후의 가격 움직임을 분석하여\n"\
                   "변동성점수(+100~-100) 및 변동성신뢰도(0~1)를 리턴합니다."
        self.ui.sj_back_cheBox_21 = self.wc.setCheckBox('1분봉 전략에 변동성분석 적용하기', self.ui.sj_bs_groupBox_05, tip=tip_text)

        # --------------------------------------------------------------------------------------------------------------

        self.ui.sj_etc_labelll_01 = QLabel('▣  UI 테마 선택                                  (재구동 후 적용)', self.ui.sj_bs_groupBox_06)
        items = ['다크블루', '다크브라운', '다크그린', '다크옐로', '다크라임', '다크퍼플', '다크레드', '다크오렌지', '다크핑크', '다크그레이', '다크네이비']
        self.ui.sj_etc_comBoxx_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_06, items=items)
        self.ui.sj_etc_checBox_02 = self.wc.setCheckBox('저해상도 설정 (해상도 1920 x 1080일 경우, 재구동 후 적용)', self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_checBox_03 = self.wc.setCheckBox('스톰라이브 참여하기', self.ui.sj_bs_groupBox_06, tip='당일실현손익 정보를 공유하고 익명으로 된 스토머분들의 정보 및 통계를 볼 수 있음')
        self.ui.sj_etc_checBox_04 = self.wc.setCheckBox('거래소가 미개장일 경우 프로세스 종료(휴무종료)', self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_checBox_05 = self.wc.setCheckBox('휴무종료일 경우 프로세스 종료 후 컴퓨터 종료', self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_checBox_06 = self.wc.setCheckBox('웹대시보드 사용하기, 포트번호(3000~4000) : ', self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_liEditt_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_checBox_07 = self.wc.setCheckBox('프로그램 종료 시 창위치 기억하기', self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_checBox_08 = self.wc.setCheckBox('프로세스 종료 시 프로그램종료', self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_labelll_02 = QLabel('▣  시리얼키', self.ui.sj_bs_groupBox_06)
        self.ui.sj_etc_liEditt_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06, passhide=True)
        self.ui.sj_etc_daEditt_01 = self.wc.setDateEdit(self.ui.sj_bs_groupBox_06, popup=False)

        # --------------------------------------------------------------------------------------------------------------

        self.ui.sj_load_Button_01 = self.wc.setPushbutton('불러오기', parent=self.ui.sj_bs_groupBox_01, click=lambda: setting_load_01(self.ui))
        self.ui.sj_load_Button_02 = self.wc.setPushbutton('불러오기', parent=self.ui.sj_bs_groupBox_02, click=lambda: setting_load_02(self.ui))
        self.ui.sj_load_Button_03 = self.wc.setPushbutton('불러오기', parent=self.ui.sj_bs_groupBox_03, click=lambda: setting_load_03(self.ui))
        self.ui.sj_load_Button_04 = self.wc.setPushbutton('불러오기', parent=self.ui.sj_bs_groupBox_04, click=lambda: setting_load_04(self.ui))
        self.ui.sj_load_Button_05 = self.wc.setPushbutton('불러오기', parent=self.ui.sj_bs_groupBox_05, click=lambda: setting_load_05(self.ui))
        self.ui.sj_load_Button_06 = self.wc.setPushbutton('불러오기', parent=self.ui.sj_bs_groupBox_06, click=lambda: setting_load_06(self.ui))

        self.ui.sj_save_Button_01 = self.wc.setPushbutton('저장하기', parent=self.ui.sj_bs_groupBox_01, click=lambda: setting_save_01(self.ui))
        self.ui.sj_save_Button_02 = self.wc.setPushbutton('저장하기', parent=self.ui.sj_bs_groupBox_02, click=lambda: setting_save_02(self.ui))
        self.ui.sj_save_Button_03 = self.wc.setPushbutton('저장하기', parent=self.ui.sj_bs_groupBox_03, click=lambda: setting_save_03(self.ui))
        self.ui.sj_save_Button_04 = self.wc.setPushbutton('저장하기', parent=self.ui.sj_bs_groupBox_04, click=lambda: setting_save_04(self.ui))
        self.ui.sj_save_Button_05 = self.wc.setPushbutton('저장하기', parent=self.ui.sj_bs_groupBox_05, click=lambda: setting_save_05(self.ui))
        self.ui.sj_save_Button_06 = self.wc.setPushbutton('저장하기', parent=self.ui.sj_bs_groupBox_06, click=self.ui.setting_serial_save)

        self.ui.sj_etc_pButton_01 = self.wc.setPushbutton('계정 텍스트 보기', parent=self.ui.sj_bs_groupBox_01, click=lambda: setting_acc_view(self.ui))
        self.ui.sj_etc_pButton_02 = self.wc.setPushbutton('경과틱수 변수설정', parent=self.ui.sj_bs_groupBox_04, click=lambda: setting_passticks(self.ui))
        self.ui.sj_etc_pButton_03 = self.wc.setPushbutton('각종 분석 학습', parent=self.ui.sj_bs_groupBox_05, click=lambda: show_pattern_dialog(self.ui))

        # --------------------------------------------------------------------------------------------------------------

        self.ui.set_tapWidgett_01.setGeometry(7, 10, 1341, 742)
        self.ui.sj_set_labelll_01.setGeometry(847, 10, 50, 20)
        self.ui.sj_set_comBoxx_01.setGeometry(902, 10, 120, 20)
        self.ui.sj_set_pButton_01.setGeometry(1027, 10, 50, 20)
        self.ui.sj_set_pButton_02.setGeometry(1082, 10, 50, 20)
        self.ui.sj_set_pButton_03.setGeometry(1137, 10, 50, 20)
        self.ui.sj_set_liEditt_01.setGeometry(1192, 10, 100, 20)
        self.ui.sj_set_pButton_04.setGeometry(1297, 10, 50, 20)

        self.ui.sj_bs_groupBox_01.setGeometry(5, 5, 1326, 90)
        self.ui.sj_bs_groupBox_02.setGeometry(5, 105, 1326, 60)
        self.ui.sj_bs_groupBox_03.setGeometry(5, 175, 1326, 60)
        self.ui.sj_bs_groupBox_04.setGeometry(5, 245, 1326, 90)
        self.ui.sj_bs_groupBox_05.setGeometry(5, 345, 1326, 210)
        self.ui.sj_bs_groupBox_06.setGeometry(5, 565, 1326, 143)

        self.ui.sj_main_labell_01.setGeometry(10, 30, 90, 20)
        self.ui.sj_main_comBox_01.setGeometry(110, 30, 120, 20)
        self.ui.sj_main_cheBox_01.setGeometry(250, 30, 90, 20)
        self.ui.sj_main_cheBox_02.setGeometry(345, 30, 90, 20)
        self.ui.sj_main_cheBox_03.setGeometry(440, 30, 90, 20)
        self.ui.sj_main_labell_02.setGeometry(562, 30, 500, 20)
        self.ui.sj_main_comBox_02.setGeometry(672, 30, 100, 20)
        self.ui.sj_main_liEdit_01.setGeometry(910, 30, 165, 20)

        self.ui.sj_main_labell_03.setGeometry(10, 55, 500, 20)
        self.ui.sj_lvrg_Button_01.setGeometry(110, 55, 120, 20)
        self.ui.sj_main_comBox_03.setGeometry(300, 55, 60, 20)
        self.ui.sj_main_comBox_04.setGeometry(420, 55, 85, 20)

        self.ui.sj_accc_labell_01.setGeometry(10, 30, 1000, 20)
        self.ui.sj_accc_liEdit_01.setGeometry(110, 30, 425, 20)
        self.ui.sj_accc_liEdit_02.setGeometry(650, 30, 425, 20)

        self.ui.sj_tele_labell_01.setGeometry(10, 30, 1000, 20)
        self.ui.sj_tele_liEdit_01.setGeometry(110, 30, 425, 20)
        self.ui.sj_tele_liEdit_02.setGeometry(650, 30, 425, 20)

        self.ui.sj_strgy_label_01.setGeometry(10, 30, 920, 20)
        self.ui.sj_strgy_cbBox_01.setGeometry(80, 30, 100, 20)
        self.ui.sj_strgy_cbBox_02.setGeometry(260, 30, 100, 20)
        self.ui.sj_strgy_lEdit_01.setGeometry(480, 30, 50, 20)
        self.ui.sj_strgy_lEdit_02.setGeometry(625, 30, 50, 20)
        self.ui.sj_strgy_lEdit_03.setGeometry(760, 30, 50, 20)
        self.ui.sj_strgy_ckBox_01.setGeometry(820, 30, 120, 20)
        self.ui.sj_strgy_ckBox_02.setGeometry(895, 30, 120, 20)
        self.ui.sj_strgy_ckBox_03.setGeometry(995, 30, 120, 20)

        self.ui.sj_strgy_ckBox_04.setGeometry(10, 55, 150, 20)
        self.ui.sj_strgy_label_02.setGeometry(145, 55, 1000, 20)
        self.ui.sj_strgy_lEdit_04.setGeometry(220, 55, 60, 20)

        self.ui.sj_strgy_ckBox_05.setGeometry(530, 55, 300, 20)
        self.ui.sj_strgy_lEdit_05.setGeometry(720, 55, 70, 20)
        self.ui.sj_strgy_ckBox_06.setGeometry(807, 55, 300, 20)
        self.ui.sj_strgy_lEdit_06.setGeometry(1005, 55, 70, 20)

        self.ui.sj_back_cheBox_01.setGeometry(10, 30, 490, 20)
        self.ui.sj_back_cheBox_02.setGeometry(10, 55, 490, 20)
        self.ui.sj_back_cheBox_03.setGeometry(10, 80, 490, 20)
        self.ui.sj_back_cheBox_04.setGeometry(10, 105, 490, 20)

        self.ui.sj_back_cheBox_05.setGeometry(10, 130, 800, 20)
        self.ui.sj_back_comBox_01.setGeometry(160, 130, 50, 20)
        self.ui.sj_back_liEdit_01.setGeometry(245, 130, 70, 20)
        self.ui.sj_back_comBox_02.setGeometry(330, 130, 130, 20)
        self.ui.sj_back_cheBox_06.setGeometry(10, 155, 330, 20)

        self.ui.sj_back_labell_02.setGeometry(10, 180, 130, 20)
        self.ui.sj_back_cheBox_07.setGeometry(105, 180, 110, 20)
        self.ui.sj_back_liEdit_02.setGeometry(125, 180, 50, 20)
        self.ui.sj_back_cheBox_08.setGeometry(210, 180, 220, 20)
        self.ui.sj_back_daEdit_01.setGeometry(260, 180, 110, 20)

        self.ui.sj_back_cheBox_09.setGeometry(480, 30, 330, 20)
        self.ui.sj_back_cheBox_10.setGeometry(480, 55, 330, 20)
        self.ui.sj_back_cheBox_11.setGeometry(480, 80, 330, 20)
        self.ui.sj_back_labell_01.setGeometry(480, 105, 330, 20)
        self.ui.sj_back_liEdit_03.setGeometry(678, 105, 40, 20)
        self.ui.sj_back_cheBox_12.setGeometry(480, 130, 300, 20)
        self.ui.sj_back_cheBox_13.setGeometry(480, 155, 330, 20)
        self.ui.sj_back_cheBox_14.setGeometry(480, 180, 220, 20)
        self.ui.sj_back_cheBox_15.setGeometry(700, 180, 100, 20)

        self.ui.sj_back_cheBox_16.setGeometry(820, 30, 300, 20)
        self.ui.sj_back_cheBox_17.setGeometry(820, 55, 300, 20)
        self.ui.sj_back_cheBox_18.setGeometry(820, 80, 300, 20)
        self.ui.sj_back_cheBox_19.setGeometry(820, 105, 300, 20)
        self.ui.sj_back_cheBox_20.setGeometry(820, 130, 300, 20)
        self.ui.sj_back_cheBox_21.setGeometry(820, 155, 300, 20)

        self.ui.sj_etc_labelll_01.setGeometry(10, 30, 490, 20)
        self.ui.sj_etc_comBoxx_01.setGeometry(100, 30, 85, 20)
        self.ui.sj_etc_checBox_02.setGeometry(10, 55, 490, 20)
        self.ui.sj_etc_checBox_03.setGeometry(10, 80, 490, 20)

        self.ui.sj_etc_checBox_04.setGeometry(480, 30, 335, 20)
        self.ui.sj_etc_checBox_05.setGeometry(480, 55, 335, 20)
        self.ui.sj_etc_checBox_06.setGeometry(480, 80, 335, 20)
        self.ui.sj_etc_liEditt_01.setGeometry(740, 80, 60, 20)

        self.ui.sj_etc_checBox_07.setGeometry(820, 30, 250, 20)
        self.ui.sj_etc_checBox_08.setGeometry(820, 55, 250, 20)
        self.ui.sj_etc_labelll_02.setGeometry(10, 110, 80, 20)
        self.ui.sj_etc_liEditt_02.setGeometry(80, 110, 880, 20)
        self.ui.sj_etc_daEditt_01.setGeometry(965, 110, 120, 20)

        self.ui.sj_load_Button_01.setGeometry(1175, 30, 70, 20)
        self.ui.sj_load_Button_02.setGeometry(1175, 30, 70, 20)
        self.ui.sj_load_Button_03.setGeometry(1175, 30, 70, 20)
        self.ui.sj_load_Button_04.setGeometry(1175, 30, 70, 20)
        self.ui.sj_load_Button_05.setGeometry(1175, 30, 70, 20)
        self.ui.sj_load_Button_06.setGeometry(1175, 30, 70, 20)

        self.ui.sj_save_Button_01.setGeometry(1250, 30, 70, 20)
        self.ui.sj_save_Button_02.setGeometry(1250, 30, 70, 20)
        self.ui.sj_save_Button_03.setGeometry(1250, 30, 70, 20)
        self.ui.sj_save_Button_04.setGeometry(1250, 30, 70, 20)
        self.ui.sj_save_Button_05.setGeometry(1250, 30, 70, 20)
        self.ui.sj_save_Button_06.setGeometry(1250, 30, 70, 20)

        self.ui.sj_etc_pButton_01.setGeometry(1175, 55, 145, 20)
        self.ui.sj_etc_pButton_02.setGeometry(1175, 55, 145, 20)
        self.ui.sj_etc_pButton_03.setGeometry(1175, 55, 145, 30)
