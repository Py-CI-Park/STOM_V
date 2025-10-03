from ui.set_style import style_bc_dk
from PyQt5.QtWidgets import QGroupBox, QLabel, QTabWidget, QWidget


class SetSetupTap:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        self.ui.set_tapWidgett_01 = QTabWidget(self.ui.sj_tab)

        self.ui.ssd_tab = QWidget()
        self.ui.sod_tab = QWidget()
        self.ui.cer_tab = QWidget()

        self.ui.sj_set_labelll_01 = QLabel('설정 관리', self.ui.sj_tab)
        self.ui.sj_set_comBoxx_01 = self.wc.setCombobox(self.ui.sj_tab, activated=self.ui.Activated_02)
        self.ui.sj_set_pButton_01 = self.wc.setPushbutton('로딩', box=self.ui.sj_tab, click=self.ui.sjButtonClicked_27)
        self.ui.sj_set_pButton_02 = self.wc.setPushbutton('설정', box=self.ui.sj_tab, click=self.ui.sjButtonClicked_28)
        self.ui.sj_set_pButton_03 = self.wc.setPushbutton('삭제', box=self.ui.sj_tab, click=self.ui.sjButtonClicked_29)
        self.ui.sj_set_liEditt_01 = self.wc.setLineedit(self.ui.sj_tab, style=style_bc_dk)
        self.ui.sj_set_pButton_04 = self.wc.setPushbutton('저장', box=self.ui.sj_tab, click=self.ui.sjButtonClicked_30)

        self.ui.set_tapWidgett_01.addTab(self.ui.ssd_tab, '일반설정')
        self.ui.set_tapWidgett_01.addTab(self.ui.sod_tab, '주문설정')

        self.ui.sj_bs_groupBox_01 = QGroupBox(' 증권사, 거래소, 프로세스 : 사용할 증권사 및 거래소를 선택하고 실행될 프로세스를 설정한다.', self.ui.ssd_tab)
        self.ui.sj_bs_groupBox_02 = QGroupBox(' 주식 계정 : 트레이더용 첫번째 계정과 리시버용 두번째 계정을 설정한다.', self.ui.ssd_tab)
        self.ui.sj_bs_groupBox_03 = QGroupBox(' 코인 계정 : Access 키와 Secret 키를 설정한다.', self.ui.ssd_tab)
        self.ui.sj_bs_groupBox_04 = QGroupBox(' 텔레그램 : 봇토큰 및 사용자 채팅 아이디를 설정한다.', self.ui.ssd_tab)
        self.ui.sj_bs_groupBox_05 = QGroupBox(' 주식 : 모의투자, 알림소리, 전략를 설정한다.', self.ui.ssd_tab)
        self.ui.sj_bs_groupBox_06 = QGroupBox(' 코인 : 모의투자, 알림소리, 전략를 설정한다.', self.ui.ssd_tab)
        self.ui.sj_bs_groupBox_07 = QGroupBox(' 백테 : 백테스트 엔진 및 백테 관련 옵션을 설정한다.', self.ui.ssd_tab)
        self.ui.sj_bs_groupBox_08 = QGroupBox(' 기타 : 휴장 종료 유무, 해상도, 창위치, 스톰라이브를 설정한다.', self.ui.ssd_tab)

        self.ui.sj_main_comBox_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, tip='사용할 증권사를 선택하십시오.', items=['키움증권1', '키움증권2', '키움증권3', '키움증권4'])
        self.ui.sj_main_cheBox_01 = self.wc.setCheckBox('주식 리시버', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_01, tip='두번째 계정으로 로그인하여 실시간조건검색 및 데이터를 수신한다.')
        self.ui.sj_main_cheBox_02 = self.wc.setCheckBox('주식 트레이더', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_02, tip='첫번째 계정으로 로그인하여 주문 및 잔고 관리하는 프로세스와\n리시버로부터 데이터를 넘겨받아 전략연산하는 프로세스로 분리되어 있다.')
        self.ui.sj_main_cheBox_03 = self.wc.setCheckBox('데이터 저장', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_03, tip='전략연산 프로세스가 모아둔 데이터를 데이터베이스에 저장한다.')

        self.ui.sj_main_comBox_02 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, tip='사용할 거래소를 선택하십시오.', items=['업비트', '바이낸스선물'])
        self.ui.sj_main_cheBox_04 = self.wc.setCheckBox('코인 리시버', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_04, tip='코인 리시버는 체결정보와 호가정보 프로세스로 분리하여 수신한다.')
        self.ui.sj_main_cheBox_05 = self.wc.setCheckBox('코인 트레이더', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_05, tip='트레이더는 전략연산과 주문 및 잔고 관리 프로세스로 분리되어 있다.')
        self.ui.sj_main_cheBox_06 = self.wc.setCheckBox('데이터 저장', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_06, tip='전략연산 프로세스가 모아둔 데이터를 데이터베이스에 저장한다.')

        self.ui.sj_main_cheBox_07 = self.wc.setCheckBox('버전 업그레이드', self.ui.sj_bs_groupBox_01, tip='버전업을 실행합니다. 멀티 스톰일 경우 첫번째 실행할 클라이언트에서 실행하십시오.')
        self.ui.sj_main_cheBox_08 = self.wc.setCheckBox('서버 (동일PC에서 하나만 지정)', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_18, tip='로컬에서 서버 역활을 한다. 이 리시버에서 받은 데이터를 ZMQ를 이용하여 클라이언트로 보낸다.')
        self.ui.sj_main_cheBox_09 = self.wc.setCheckBox('클라이언트 (여러개 가능)', self.ui.sj_bs_groupBox_01, changed=self.ui.CheckboxChanged_18, tip='로컬에서 클라이언트 역활을 한다. 동일 PC에서 서버는 하나만 가능하지만, 클라이언트는 여러개가 가능하다.')

        self.ui.sj_main_labell_01 = QLabel('바이낸스 선물   |                                                         마진타입                     포지션', self.ui.sj_bs_groupBox_01)
        self.ui.sj_lvrg_Button_01 = self.wc.setPushbutton('레버리지 유형 및 수치 설정', box=self.ui.sj_bs_groupBox_01, click=self.ui.lvButtonClicked_01, tip='바이낸스 선물 레버리지를 고정, 변동 형태 중 선택하여 설정한다.')
        self.ui.sj_main_comBox_03 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, items=['격리', '교차'], activated=self.ui.cActivated_10)
        self.ui.sj_main_comBox_04 = self.wc.setCombobox(self.ui.sj_bs_groupBox_01, items=['단방향', '양방향'], activated=self.ui.cActivated_11)

        text = '첫번째 계정 아이디                                                         ' \
               '비밀번호                                                           ' \
               '인증서비밀번호                                                       ' \
               '계좌비밀번호'
        self.ui.sj_sacc_labell_01 = QLabel(text, self.ui.sj_bs_groupBox_02)
        self.ui.sj_sacc_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)
        self.ui.sj_sacc_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)
        self.ui.sj_sacc_liEdit_03 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)
        self.ui.sj_sacc_liEdit_04 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)

        text = '두번째 계정 아이디                                                         ' \
               '비밀번호                                                           ' \
               '인증서비밀번호                                                       ' \
               '계좌비밀번호'
        self.ui.sj_sacc_labell_02 = QLabel(text, self.ui.sj_bs_groupBox_02)
        self.ui.sj_sacc_liEdit_05 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)
        self.ui.sj_sacc_liEdit_06 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)
        self.ui.sj_sacc_liEdit_07 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)
        self.ui.sj_sacc_liEdit_08 = self.wc.setLineedit(self.ui.sj_bs_groupBox_02, passhide=True)

        text = 'Access Key                                                                                  ' \
               '                                                            Secret Key'
        self.ui.sj_cacc_labell_01 = QLabel(text, self.ui.sj_bs_groupBox_03)
        self.ui.sj_cacc_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_03, passhide=True)
        self.ui.sj_cacc_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_03, passhide=True)

        text = 'Bot Token                                                                                   ' \
               '                                                             Chat Id'
        self.ui.sj_tele_labell_01 = QLabel(text, self.ui.sj_bs_groupBox_04)
        self.ui.sj_tele_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04, passhide=True)
        self.ui.sj_tele_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_04, passhide=True)

        self.ui.sj_stock_ckBox_01 = self.wc.setCheckBox('모의투자     |', self.ui.sj_bs_groupBox_05, changed=self.ui.CheckboxChanged_07, tip='모의투자 체크 시 주문이 전송되지 않고\n매수, 매도를 기록한다. 체크 해제 시 실제 주문이 전송된다.')
        self.ui.sj_stock_ckBox_02 = self.wc.setCheckBox('알림소리     |', self.ui.sj_bs_groupBox_05, tip='각종 알림소리를 끄고 켠다.')
        text = '매수                                       ' \
               '매도                                       ' \
               '데이터                              평균값계산틱수                       최대종목수                       종료시간'
        self.ui.sj_stock_label_01 = QLabel(text, self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_cbBox_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_05, activated=self.ui.sActivated_09, tip='매수전략을 선택하십시오.\n저장한 전략이 보이지 않을 경우 우측 불러오기를 누르십시오.')
        self.ui.sj_stock_cbBox_02 = self.wc.setCombobox(self.ui.sj_bs_groupBox_05, tip='매도전략을 선택하십시오.\n저장한 전략이 보이지 않을 경우 우측 불러오기를 누르십시오.')
        self.ui.sj_stock_cbBox_03 = self.wc.setCombobox(self.ui.sj_bs_groupBox_05, tip='사용할 데이터 유형을 선택하십시오.', items=['1초스냅샷', '1분봉'])
        self.ui.sj_stock_lEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_lEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_lEdit_03 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_ckBox_03 = self.wc.setCheckBox('잔고청산', self.ui.sj_bs_groupBox_05, tip='전략 종료 시 보유잔고를 시장가청산한다.')
        self.ui.sj_stock_ckBox_04 = self.wc.setCheckBox('프로세스 종료', self.ui.sj_bs_groupBox_05, tip='전략 마감 후 리시버, 전략연산, 트레이더 프로세스를 종료한다.')
        self.ui.sj_stock_ckBox_05 = self.wc.setCheckBox('컴퓨터 종료', self.ui.sj_bs_groupBox_05, changed=self.ui.CheckboxChanged_09, tip='프로세스를 종료 후 컴퓨터를 종료한다.')

        self.ui.sj_stock_ckBox_09 = self.wc.setCheckBox('종목당 투자금 고정   |', self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_label_03 = QLabel('종목당투자금                          백만원                                  전략중지 및 잔고청산   |', self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_lEdit_07 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)

        self.ui.sj_stock_ckBox_10 = self.wc.setCheckBox('손실중지 - 총자산 대비 수익률 (-)           %', self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_lEdit_09 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_ckBox_11 = self.wc.setCheckBox('수익중지 - 총자산 대비 수익률 (+)           %', self.ui.sj_bs_groupBox_05)
        self.ui.sj_stock_lEdit_10 = self.wc.setLineedit(self.ui.sj_bs_groupBox_05)

        self.ui.sj_coin_cheBox_01 = self.wc.setCheckBox('모의투자    |', self.ui.sj_bs_groupBox_06, changed=self.ui.CheckboxChanged_08, tip='모의투자 체크 시 주문이 전송되지 않고\n매수, 매도를 기록한다. 체크 해제 시 실제 주문이 전송된다.')
        self.ui.sj_coin_cheBox_02 = self.wc.setCheckBox('알림소리    |', self.ui.sj_bs_groupBox_06, tip='각종 알림소리를 끄고 켠다.')
        self.ui.sj_coin_labell_01 = QLabel(text, self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_comBox_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_06, activated=self.ui.cActivated_09, tip='매수전략을 선택하십시오.\n저장한 전략이 보이지 않을 경우 우측 불러오기를 누르십시오.')
        self.ui.sj_coin_comBox_02 = self.wc.setCombobox(self.ui.sj_bs_groupBox_06, tip='매도전략을 선택하십시오.\n저장한 전략이 보이지 않을 경우 우측 불러오기를 누르십시오.')
        self.ui.sj_coin_comBox_03 = self.wc.setCombobox(self.ui.sj_bs_groupBox_06, tip='사용할 데이터 유형을 선택하십시오.', items=['1초스냅샷', '1분봉'])
        self.ui.sj_coin_liEdit_01 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_liEdit_03 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_cheBox_03 = self.wc.setCheckBox('잔고청산', self.ui.sj_bs_groupBox_06, tip='전략 종료 시 보유잔고를 시장가청산한다.')
        self.ui.sj_coin_cheBox_04 = self.wc.setCheckBox('프로세스 종료', self.ui.sj_bs_groupBox_06, tip='전략 마감 후 리시버, 전략연산, 트레이더 프로세스를 종료한다.')
        self.ui.sj_coin_cheBox_05 = self.wc.setCheckBox('컴퓨터 종료', self.ui.sj_bs_groupBox_06, changed=self.ui.CheckboxChanged_09, tip='프로세스를 종료 후 컴퓨터를 종료한다.')

        self.ui.sj_coin_cheBox_09 = self.wc.setCheckBox('종목당 투자금 고정   |', self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_labell_03 = QLabel('종목당투자금                          백만원                                  전략중지 및 잔고청산   |', self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_liEdit_07 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06)

        self.ui.sj_coin_cheBox_10 = self.wc.setCheckBox('손실중지 - 총자산 대비 수익률 (-)           %', self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_liEdit_09 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_cheBox_11 = self.wc.setCheckBox('수익중지 - 총자산 대비 수익률 (+)           %', self.ui.sj_bs_groupBox_06)
        self.ui.sj_coin_liEdit_10 = self.wc.setLineedit(self.ui.sj_bs_groupBox_06)

        self.ui.sj_back_cheBox_01 = self.wc.setCheckBox('백테스트 시 거래횟수 10회 이상이며 수익금이 마이너스일 경우 블랙리스트에 추가하기', self.ui.sj_bs_groupBox_07)
        self.ui.sj_back_cheBox_02 = self.wc.setCheckBox('백테스트에 주문관리 설정 적용하기(최유리 및 IOC 주문 제외)', self.ui.sj_bs_groupBox_07, tip='설정 변경 시 백테엔진을 재로딩해야 합니다. 체크해제 시 시장가 호가범위선택 및 비중조절은 적용됨')
        self.ui.sj_back_cheBox_03 = self.wc.setCheckBox('백테스트 그래프 매수시간 기준으로 표시하기', self.ui.sj_bs_groupBox_07, tip='체크해제 시 매도시간 기준으로 표시됩니다.')

        self.ui.sj_back_cheBox_04 = self.wc.setCheckBox('일괄 로딩(모든 종목의 데이터를 램에 올려두고 백테스트합니다. 백테속도↑, 램사용량↑)', self.ui.sj_bs_groupBox_07, changed=self.ui.CheckboxChanged_11)
        self.ui.sj_back_cheBox_05 = self.wc.setCheckBox('분할 로딩(피클덤프한 다음 한종목씩 램에 올려 백테스트합니다. 백테속도↓, 램사용량↓)', self.ui.sj_bs_groupBox_07, changed=self.ui.CheckboxChanged_11)

        self.ui.sj_back_cheBox_13 = self.wc.setCheckBox('일반 백테스트 시 그래프 저장하지 않기', self.ui.sj_bs_groupBox_07, changed=self.ui.CheckboxChanged_12)
        self.ui.sj_back_cheBox_14 = self.wc.setCheckBox('일반 백테스트 시 그래프 띄우지 않기', self.ui.sj_bs_groupBox_07, changed=self.ui.CheckboxChanged_13)
        self.ui.sj_back_cheBox_21 = self.wc.setCheckBox('최적화 도중 로그 기록하지 않기', self.ui.sj_bs_groupBox_07)

        self.ui.sj_back_cheBox_15 = self.wc.setCheckBox('데이터베이스 자동관리(일자DB분리, 백테DB추가)', self.ui.sj_bs_groupBox_07, tip='데이터 저장 후 일자별분리 및 백테디비추가가 자동실행됨')
        self.ui.sj_back_cheBox_16 = self.wc.setCheckBox('교차검증 최적화에 가중치 적용하기', self.ui.sj_bs_groupBox_07, tip='교차검증 최적화 시 최근데이터일수록 가중치를 줘서 기준값을 계산한다.')
        self.ui.sj_back_cheBox_19 = self.wc.setCheckBox('스케쥴러 자동실행 | 요일                 시간                                                                                     엔진시작일자', self.ui.sj_bs_groupBox_07, tip='백테 스케쥴러를 자동실행한다.')
        self.ui.sj_back_comBox_05 = self.wc.setCombobox(self.ui.sj_bs_groupBox_07, items=['금', '토', '일'])
        self.ui.sj_back_liEdit_03 = self.wc.setLineedit(self.ui.sj_bs_groupBox_07)
        self.ui.sj_back_comBox_03 = self.wc.setCombobox(self.ui.sj_bs_groupBox_07, items=['주식', '코인'])
        self.ui.sj_back_comBox_04 = self.wc.setCombobox(self.ui.sj_bs_groupBox_07)
        self.ui.sj_back_cheBox_17 = self.wc.setCheckBox('                   일전', self.ui.sj_bs_groupBox_07, changed=self.ui.CheckboxChanged_16)
        self.ui.sj_back_liEdit_02 = self.wc.setLineedit(self.ui.sj_bs_groupBox_07)
        self.ui.sj_back_cheBox_18 = self.wc.setCheckBox('                                        고정', self.ui.sj_bs_groupBox_07, changed=self.ui.CheckboxChanged_17)
        self.ui.sj_back_daEdit_01 = self.wc.setDateEdit(self.ui.sj_bs_groupBox_07)
        self.ui.sj_back_cheBox_20 = self.wc.setCheckBox('그리드 최적화 범위 자동 관리(고정, 추가, 삭제)', self.ui.sj_bs_groupBox_07, tip='그리드 최적화 시에 범위에서 불필요한 값을 제거하고\n최소최대가 최적값일 경우 자동으로 범위를 추가하며\n범위의 기준값이 같을 경우 최적값으로 고정합니다.')

        self.ui.sj_ilbunback_listtt = [self.ui.sj_back_cheBox_04, self.ui.sj_back_cheBox_05]

        self.ui.com_exit_list = [
            self.ui.sj_stock_ckBox_05, self.ui.sj_coin_cheBox_05
        ]

        self.ui.sj_etc_labelll_01 = QLabel('▣  UI 테마 선택                                (재구동 후 적용)', self.ui.sj_bs_groupBox_08)
        self.ui.sj_etc_comBoxx_01 = self.wc.setCombobox(self.ui.sj_bs_groupBox_08, items=['다크블루', '다크브라운', '다크그린', '다크옐로', '다크라임', '다크퍼플'])
        self.ui.sj_etc_checBox_02 = self.wc.setCheckBox('저해상도 설정 (해상도 1920 x 1080일 경우, 재구동 후 적용)', self.ui.sj_bs_groupBox_08)
        self.ui.sj_etc_checBox_03 = self.wc.setCheckBox('프로그램 종료 시 창위치 기억하기 (재구동 후 적용)', self.ui.sj_bs_groupBox_08)
        self.ui.sj_etc_checBox_04 = self.wc.setCheckBox('주식 실행 후 9시1분 또는 10분간까지 장운영알림을 받지 못할 경우 프로세스 종료하기', self.ui.sj_bs_groupBox_08)
        self.ui.sj_etc_checBox_05 = self.wc.setCheckBox('휴무종료일 경우 프로세스 종료 후 컴퓨터 종료', self.ui.sj_bs_groupBox_08)
        self.ui.sj_etc_checBox_06 = self.wc.setCheckBox('스톰라이브 참여하기', self.ui.sj_bs_groupBox_08, tip='당일실현손익 정보를 공유하고 익명으로 된 스토머분들의 정보 및 통계를 볼 수 있음')
        self.ui.sj_etc_checBox_07 = self.wc.setCheckBox('프로세스 종료 시 프로그램종료', self.ui.sj_bs_groupBox_08)

        self.ui.sj_load_Button_01 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_01, click=self.ui.sjButtonClicked_01)
        self.ui.sj_load_Button_02 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_02, click=self.ui.sjButtonClicked_02)
        self.ui.sj_load_Button_03 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_03, click=self.ui.sjButtonClicked_03)
        self.ui.sj_load_Button_04 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_04, click=self.ui.sjButtonClicked_04)
        self.ui.sj_load_Button_05 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_05, click=self.ui.sjButtonClicked_05)
        self.ui.sj_load_Button_06 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_06, click=self.ui.sjButtonClicked_06)
        self.ui.sj_load_Button_07 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_07, click=self.ui.sjButtonClicked_07)
        self.ui.sj_load_Button_08 = self.wc.setPushbutton('불러오기', box=self.ui.sj_bs_groupBox_08, click=self.ui.sjButtonClicked_08)

        self.ui.sj_save_Button_01 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_01, click=self.ui.sjButtonClicked_09)
        self.ui.sj_save_Button_02 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_02, click=self.ui.sjButtonClicked_10)
        self.ui.sj_save_Button_03 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_03, click=self.ui.sjButtonClicked_11)
        self.ui.sj_save_Button_04 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_04, click=self.ui.sjButtonClicked_12)
        self.ui.sj_save_Button_05 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_05, click=self.ui.sjButtonClicked_13)
        self.ui.sj_save_Button_06 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_06, click=self.ui.sjButtonClicked_14)
        self.ui.sj_save_Button_07 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_07, click=self.ui.sjButtonClicked_15)
        self.ui.sj_save_Button_08 = self.wc.setPushbutton('저장하기', box=self.ui.sj_bs_groupBox_08, click=self.ui.sjButtonClicked_16)

        self.ui.sj_etc_pButton_01 = self.wc.setPushbutton('계정 텍스트 보기', box=self.ui.sj_bs_groupBox_02, click=self.ui.sjButtonClicked_17)
        self.ui.sj_etc_pButton_02 = self.wc.setPushbutton('경과틱수 변수설정', box=self.ui.sj_bs_groupBox_05, click=self.ui.sjButtonClicked_33)
        self.ui.sj_etc_pButton_03 = self.wc.setPushbutton('경과틱수 변수설정', box=self.ui.sj_bs_groupBox_06, click=self.ui.sjButtonClicked_34)

        self.ui.set_tapWidgett_01.setGeometry(7, 10, 1341, 742)
        self.ui.sj_set_labelll_01.setGeometry(847, 10, 50, 20)
        self.ui.sj_set_comBoxx_01.setGeometry(902, 10, 120, 20)
        self.ui.sj_set_pButton_01.setGeometry(1027, 10, 50, 20)
        self.ui.sj_set_pButton_02.setGeometry(1082, 10, 50, 20)
        self.ui.sj_set_pButton_03.setGeometry(1137, 10, 50, 20)
        self.ui.sj_set_liEditt_01.setGeometry(1192, 10, 100, 20)
        self.ui.sj_set_pButton_04.setGeometry(1297, 10, 50, 20)

        self.ui.sj_bs_groupBox_01.setGeometry(5, 5, 1326, 75)
        self.ui.sj_bs_groupBox_02.setGeometry(5, 90, 1326, 75)
        self.ui.sj_bs_groupBox_03.setGeometry(5, 175, 1326, 50)
        self.ui.sj_bs_groupBox_04.setGeometry(5, 235, 1326, 50)
        self.ui.sj_bs_groupBox_05.setGeometry(5, 295, 1326, 75)
        self.ui.sj_bs_groupBox_06.setGeometry(5, 380, 1326, 75)
        self.ui.sj_bs_groupBox_07.setGeometry(5, 465, 1326, 125)
        self.ui.sj_bs_groupBox_08.setGeometry(5, 600, 1326, 107)

        self.ui.sj_main_comBox_01.setGeometry(10, 25, 140, 20)
        self.ui.sj_main_cheBox_01.setGeometry(170, 25, 90, 20)
        self.ui.sj_main_cheBox_02.setGeometry(270, 25, 90, 20)
        self.ui.sj_main_cheBox_03.setGeometry(370, 25, 90, 20)

        self.ui.sj_main_comBox_02.setGeometry(500, 25, 140, 20)
        self.ui.sj_main_cheBox_04.setGeometry(660, 25, 90, 20)
        self.ui.sj_main_cheBox_05.setGeometry(760, 25, 90, 20)
        self.ui.sj_main_cheBox_06.setGeometry(860, 25, 90, 20)

        self.ui.sj_main_cheBox_07.setGeometry(10, 50, 200, 20)
        self.ui.sj_main_cheBox_08.setGeometry(120, 50, 220, 20)
        self.ui.sj_main_cheBox_09.setGeometry(305, 50, 220, 20)

        self.ui.sj_main_labell_01.setGeometry(500, 50, 500, 20)
        self.ui.sj_lvrg_Button_01.setGeometry(590, 50, 150, 20)
        self.ui.sj_main_comBox_03.setGeometry(800, 50, 50, 20)
        self.ui.sj_main_comBox_04.setGeometry(900, 50, 50, 20)

        self.ui.sj_sacc_labell_01.setGeometry(10, 25, 1000, 20)
        self.ui.sj_sacc_liEdit_01.setGeometry(115, 25, 130, 20)
        self.ui.sj_sacc_liEdit_02.setGeometry(330, 25, 130, 20)
        self.ui.sj_sacc_liEdit_03.setGeometry(585, 25, 130, 20)
        self.ui.sj_sacc_liEdit_04.setGeometry(820, 25, 130, 20)
        self.ui.sj_sacc_labell_02.setGeometry(10, 50, 1000, 20)
        self.ui.sj_sacc_liEdit_05.setGeometry(115, 50, 130, 20)
        self.ui.sj_sacc_liEdit_06.setGeometry(330, 50, 130, 20)
        self.ui.sj_sacc_liEdit_07.setGeometry(585, 50, 130, 20)
        self.ui.sj_sacc_liEdit_08.setGeometry(820, 50, 130, 20)

        self.ui.sj_cacc_labell_01.setGeometry(10, 25, 1000, 20)
        self.ui.sj_cacc_liEdit_01.setGeometry(85, 25, 375, 20)
        self.ui.sj_cacc_liEdit_02.setGeometry(575, 25, 375, 20)

        self.ui.sj_tele_labell_01.setGeometry(10, 25, 1000, 20)
        self.ui.sj_tele_liEdit_01.setGeometry(85, 25, 375, 20)
        self.ui.sj_tele_liEdit_02.setGeometry(575, 25, 375, 20)

        self.ui.sj_stock_ckBox_01.setGeometry(10, 25, 100, 20)
        self.ui.sj_stock_ckBox_02.setGeometry(10, 50, 100, 20)

        self.ui.sj_stock_label_01.setGeometry(100, 25, 920, 20)
        self.ui.sj_stock_cbBox_01.setGeometry(130, 25, 100, 20)
        self.ui.sj_stock_cbBox_02.setGeometry(270, 25, 100, 20)
        self.ui.sj_stock_cbBox_03.setGeometry(415, 25, 70, 20)
        self.ui.sj_stock_lEdit_01.setGeometry(590, 25, 50, 20)
        self.ui.sj_stock_lEdit_02.setGeometry(715, 25, 50, 20)
        self.ui.sj_stock_lEdit_03.setGeometry(825, 25, 50, 20)
        self.ui.sj_stock_ckBox_03.setGeometry(885, 25, 120, 20)
        self.ui.sj_stock_ckBox_04.setGeometry(960, 25, 120, 20)
        self.ui.sj_stock_ckBox_05.setGeometry(1060, 25, 120, 20)

        self.ui.sj_stock_ckBox_09.setGeometry(85, 50, 150, 20)
        self.ui.sj_stock_label_03.setGeometry(220, 50, 1000, 20)
        self.ui.sj_stock_lEdit_07.setGeometry(295, 50, 60, 20)

        self.ui.sj_stock_ckBox_10.setGeometry(625, 50, 300, 20)
        self.ui.sj_stock_lEdit_09.setGeometry(810, 50, 25, 20)
        self.ui.sj_stock_ckBox_11.setGeometry(860, 50, 300, 20)
        self.ui.sj_stock_lEdit_10.setGeometry(1050, 50, 25, 20)

        self.ui.sj_coin_cheBox_01.setGeometry(10, 25, 90, 20)
        self.ui.sj_coin_cheBox_02.setGeometry(10, 50, 90, 20)

        self.ui.sj_coin_labell_01.setGeometry(100, 25, 920, 20)
        self.ui.sj_coin_comBox_01.setGeometry(130, 25, 100, 20)
        self.ui.sj_coin_comBox_02.setGeometry(270, 25, 100, 20)
        self.ui.sj_coin_comBox_03.setGeometry(415, 25, 70, 20)
        self.ui.sj_coin_liEdit_01.setGeometry(590, 25, 50, 20)
        self.ui.sj_coin_liEdit_02.setGeometry(715, 25, 50, 20)
        self.ui.sj_coin_liEdit_03.setGeometry(825, 25, 50, 20)
        self.ui.sj_coin_cheBox_03.setGeometry(885, 25, 120, 20)
        self.ui.sj_coin_cheBox_04.setGeometry(960, 25, 120, 20)
        self.ui.sj_coin_cheBox_05.setGeometry(1060, 25, 120, 20)

        self.ui.sj_coin_cheBox_09.setGeometry(85, 50, 150, 20)
        self.ui.sj_coin_labell_03.setGeometry(220, 50, 1000, 20)
        self.ui.sj_coin_liEdit_07.setGeometry(295, 50, 60, 20)

        self.ui.sj_coin_cheBox_10.setGeometry(625, 50, 300, 20)
        self.ui.sj_coin_liEdit_09.setGeometry(810, 50, 25, 20)
        self.ui.sj_coin_cheBox_11.setGeometry(860, 50, 300, 20)
        self.ui.sj_coin_liEdit_10.setGeometry(1050, 50, 25, 20)

        self.ui.sj_back_cheBox_01.setGeometry(10, 25, 500, 20)
        self.ui.sj_back_cheBox_02.setGeometry(500, 25, 700, 20)
        self.ui.sj_back_cheBox_03.setGeometry(500, 50, 400, 20)

        self.ui.sj_back_cheBox_04.setGeometry(10, 50, 500, 20)
        self.ui.sj_back_cheBox_05.setGeometry(10, 75, 500, 20)

        self.ui.sj_back_cheBox_13.setGeometry(835, 50, 400, 20)
        self.ui.sj_back_cheBox_14.setGeometry(835, 75, 400, 20)
        self.ui.sj_back_cheBox_21.setGeometry(1060, 50, 300, 20)

        self.ui.sj_back_cheBox_15.setGeometry(10, 100, 500, 20)
        self.ui.sj_back_cheBox_16.setGeometry(835, 25, 250, 20)
        self.ui.sj_back_cheBox_19.setGeometry(500, 100, 800, 20)
        self.ui.sj_back_comBox_05.setGeometry(645, 100, 40, 20)
        self.ui.sj_back_liEdit_03.setGeometry(720, 100, 70, 20)
        self.ui.sj_back_comBox_03.setGeometry(800, 100, 50, 20)
        self.ui.sj_back_comBox_04.setGeometry(855, 100, 100, 20)
        self.ui.sj_back_cheBox_17.setGeometry(1040, 100, 110, 20)
        self.ui.sj_back_liEdit_02.setGeometry(1060, 100, 50, 20)
        self.ui.sj_back_cheBox_18.setGeometry(1150, 100, 220, 20)
        self.ui.sj_back_daEdit_01.setGeometry(1170, 100, 110, 20)
        self.ui.sj_back_cheBox_20.setGeometry(500, 75, 300, 20)

        self.ui.sj_etc_labelll_01.setGeometry(10, 25, 300, 20)
        self.ui.sj_etc_comBoxx_01.setGeometry(100, 25, 85, 20)
        self.ui.sj_etc_checBox_02.setGeometry(500, 25, 350, 20)
        self.ui.sj_etc_checBox_03.setGeometry(835, 25, 300, 20)
        self.ui.sj_etc_checBox_04.setGeometry(10, 50, 500, 20)
        self.ui.sj_etc_checBox_05.setGeometry(500, 50, 300, 20)
        self.ui.sj_etc_checBox_06.setGeometry(835, 50, 130, 20)
        self.ui.sj_etc_checBox_07.setGeometry(970, 50, 200, 20)

        self.ui.sj_load_Button_01.setGeometry(1175, 25, 70, 20)
        self.ui.sj_load_Button_02.setGeometry(1175, 25, 70, 20)
        self.ui.sj_load_Button_03.setGeometry(1175, 25, 70, 20)
        self.ui.sj_load_Button_04.setGeometry(1175, 25, 70, 20)
        self.ui.sj_load_Button_05.setGeometry(1175, 25, 70, 20)
        self.ui.sj_load_Button_06.setGeometry(1175, 25, 70, 20)
        self.ui.sj_load_Button_07.setGeometry(1175, 25, 70, 20)
        self.ui.sj_load_Button_08.setGeometry(1175, 25, 70, 20)

        self.ui.sj_save_Button_01.setGeometry(1250, 25, 70, 20)
        self.ui.sj_save_Button_02.setGeometry(1250, 25, 70, 20)
        self.ui.sj_save_Button_03.setGeometry(1250, 25, 70, 20)
        self.ui.sj_save_Button_04.setGeometry(1250, 25, 70, 20)
        self.ui.sj_save_Button_05.setGeometry(1250, 25, 70, 20)
        self.ui.sj_save_Button_06.setGeometry(1250, 25, 70, 20)
        self.ui.sj_save_Button_07.setGeometry(1250, 25, 70, 20)
        self.ui.sj_save_Button_08.setGeometry(1250, 25, 70, 20)

        self.ui.sj_etc_pButton_01.setGeometry(1175, 50, 145, 20)
        self.ui.sj_etc_pButton_02.setGeometry(1175, 50, 145, 20)
        self.ui.sj_etc_pButton_03.setGeometry(1175, 50, 145, 20)
