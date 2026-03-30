
from PyQt5.QtWidgets import QLabel
from ui.set_widget import error_decorator


class SetOrderTap:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    @error_decorator
    def set(self):
        self.ui.ss_od_groupBoxxx_01 = self.wc.setQGroupBox(' 주식 및 해선 매수주문 설정', self.ui.sod_tab)
        self.ui.ss_od_groupBoxxx_02 = self.wc.setQGroupBox(' 주식 및 해선 매도주문 설정', self.ui.sod_tab)

        self.ui.ss_od_groupBoxxx_03 = self.wc.setQGroupBox('주문유형', self.ui.ss_od_groupBoxxx_01, hover=True)
        self.ui.ss_od_groupBoxxx_04 = self.wc.setQGroupBox('분할매수', self.ui.ss_od_groupBoxxx_01, hover=True)
        self.ui.ss_od_groupBoxxx_05 = self.wc.setQGroupBox('지정가 기준가격 및 시장가 호가범위', self.ui.ss_od_groupBoxxx_01, hover=True)
        self.ui.ss_od_groupBoxxx_06 = self.wc.setQGroupBox('매수주문취소', self.ui.ss_od_groupBoxxx_01, hover=True)
        self.ui.ss_od_groupBoxxx_07 = self.wc.setQGroupBox('매수금지', self.ui.ss_od_groupBoxxx_01, hover=True)
        self.ui.ss_od_groupBoxxx_08 = self.wc.setQGroupBox('매수정정', self.ui.ss_od_groupBoxxx_01, hover=True)
        self.ui.ss_od_groupBoxxx_09 = self.wc.setQGroupBox('비중조절', self.ui.ss_od_groupBoxxx_01, hover=True)

        self.ui.ss_od_groupBoxxx_10 = self.wc.setQGroupBox('주문유형', self.ui.ss_od_groupBoxxx_02, hover=True)
        self.ui.ss_od_groupBoxxx_11 = self.wc.setQGroupBox('분할매도', self.ui.ss_od_groupBoxxx_02, hover=True)
        self.ui.ss_od_groupBoxxx_12 = self.wc.setQGroupBox('지정가 기준가격 및 시장가 호가범위', self.ui.ss_od_groupBoxxx_02, hover=True)
        self.ui.ss_od_groupBoxxx_13 = self.wc.setQGroupBox('매도주문취소', self.ui.ss_od_groupBoxxx_02, hover=True)
        self.ui.ss_od_groupBoxxx_14 = self.wc.setQGroupBox('매도금지', self.ui.ss_od_groupBoxxx_02, hover=True)
        self.ui.ss_od_groupBoxxx_15 = self.wc.setQGroupBox('매도정정', self.ui.ss_od_groupBoxxx_02, hover=True)
        self.ui.ss_od_groupBoxxx_16 = self.wc.setQGroupBox('익절청산', self.ui.ss_od_groupBoxxx_02, hover=True)
        self.ui.ss_od_groupBoxxx_17 = self.wc.setQGroupBox('손절청산', self.ui.ss_od_groupBoxxx_02, hover=True)

        self.ui.ss_buyy_checkBox_01 = self.wc.setCheckBox('시장가', self.ui.ss_od_groupBoxxx_03,      changed=self.ui.sbCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하는 방식')
        self.ui.ss_buyy_checkBox_02 = self.wc.setCheckBox('지정가', self.ui.ss_od_groupBoxxx_03,      changed=self.ui.sbCheckboxChanged_01, tip='원하는 가격에 원하는 수량만큼 주문하는 방식')
        self.ui.ss_buyy_checkBox_03 = self.wc.setCheckBox('최유리지정가', self.ui.ss_od_groupBoxxx_03, changed=self.ui.sbCheckboxChanged_01, tip='매수는 매도1호가에 매도는 매수1호가에 원하는 수량만큼 주문하고 부족한 수량은 잔량 대기하는 방식')
        self.ui.ss_buyy_checkBox_04 = self.wc.setCheckBox('최우선지정가', self.ui.ss_od_groupBoxxx_03, changed=self.ui.sbCheckboxChanged_01, tip='매수는 매수1호가에 매도는 매도1호가에 원하는 수량만큼 주문하는 방식, 체결이 안될 수도 있음')
        self.ui.ss_buyy_checkBox_05 = self.wc.setCheckBox('지정가IOC', self.ui.ss_od_groupBoxxx_03,   changed=self.ui.sbCheckboxChanged_01, tip='원하는 가격에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.ss_buyy_checkBox_06 = self.wc.setCheckBox('시장가IOC', self.ui.ss_od_groupBoxxx_03,   changed=self.ui.sbCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.ss_buyy_checkBox_07 = self.wc.setCheckBox('최유리IOC', self.ui.ss_od_groupBoxxx_03,   changed=self.ui.sbCheckboxChanged_01, tip='매수는 매도1호가에 매도는 매수1호가에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.ss_buyy_checkBox_08 = self.wc.setCheckBox('지정가FOK', self.ui.ss_od_groupBoxxx_03,   changed=self.ui.sbCheckboxChanged_01, tip='원하는 가격에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')
        self.ui.ss_buyy_checkBox_09 = self.wc.setCheckBox('시장가FOK', self.ui.ss_od_groupBoxxx_03,   changed=self.ui.sbCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')
        self.ui.ss_buyy_checkBox_10 = self.wc.setCheckBox('최유리FOK', self.ui.ss_od_groupBoxxx_03,   changed=self.ui.sbCheckboxChanged_01, tip='매수는 매도호1가에 매도는 매수1호가에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')

        self.ui.sodb_checkbox_list1 = [
            self.ui.ss_buyy_checkBox_01, self.ui.ss_buyy_checkBox_02, self.ui.ss_buyy_checkBox_03,
            self.ui.ss_buyy_checkBox_04, self.ui.ss_buyy_checkBox_05, self.ui.ss_buyy_checkBox_06,
            self.ui.ss_buyy_checkBox_07, self.ui.ss_buyy_checkBox_08, self.ui.ss_buyy_checkBox_09,
            self.ui.ss_buyy_checkBox_10
        ]

        self.ui.ss_buyy_labellll_01 = QLabel('▣ 분할매수횟수 (1:분할매수X)', self.ui.ss_od_groupBoxxx_04)
        self.ui.ss_buyy_lineEdit_01 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_04)
        self.ui.ss_buyy_labellll_02 = QLabel('▣ 분할매수방법 : 복수선택 불가능', self.ui.ss_od_groupBoxxx_04)
        self.ui.ss_buyy_checkBox_11 = self.wc.setCheckBox('균등분할', self.ui.ss_od_groupBoxxx_04, changed=self.ui.sbCheckboxChanged_02, tip='종목당배팅금액을 분할횟수로 균등분할매수\n(예 0: 20., 1: 20., 2: 20., 3: 20., 4: 20.)')
        self.ui.ss_buyy_checkBox_12 = self.wc.setCheckBox('비율감소', self.ui.ss_od_groupBoxxx_04, changed=self.ui.sbCheckboxChanged_02, tip='다음 추가매수 시 이전 매수비율의 절반으로 매수\n(예 0: 51.61, 1: 25.81, 2: 12.90, 3: 6.45, 4: 3.23)')
        self.ui.ss_buyy_checkBox_13 = self.wc.setCheckBox('비율증가', self.ui.ss_od_groupBoxxx_04, changed=self.ui.sbCheckboxChanged_02, tip='다음 추가매수 시 이전 매수비율의 두배로 매수\n(예 0: 3.23, 1: 6.45, 2: 12.90, 3: 25.81, 4: 51.61)')
        self.ui.ss_buyy_labellll_03 = QLabel('▣ 추가매수방법 : 복수선택 가능', self.ui.ss_od_groupBoxxx_04)
        self.ui.ss_buyy_checkBox_14 = self.wc.setCheckBox('매수시그널', self.ui.ss_od_groupBoxxx_04, tip='매수시그널을 통해서 추가매수')
        self.ui.ss_buyy_checkBox_15 = self.wc.setCheckBox('수익률(-)', self.ui.ss_od_groupBoxxx_04, tip='잔고의 - 수익률를 기준으로 추가매수')
        self.ui.ss_buyy_lineEdit_02 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_04)
        self.ui.ss_buyy_checkBox_16 = self.wc.setCheckBox('수익률(+)', self.ui.ss_od_groupBoxxx_04, tip='잔고의 + 수익률를 기준으로 추가매수')
        self.ui.ss_buyy_lineEdit_03 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_04)
        self.ui.ss_buyy_checkBox_17 = self.wc.setCheckBox('고정수익률', self.ui.ss_od_groupBoxxx_04, tip='수익률(-), 수익률(+)의 수익률기준을 잔고수익률이 아닌\n마지막 매수시점의 현재가 대비 잔고수익률로 변경한다.')

        self.ui.sodb_checkbox_list2 = [self.ui.ss_buyy_checkBox_11, self.ui.ss_buyy_checkBox_12, self.ui.ss_buyy_checkBox_13]

        self.ui.ss_buyy_labellll_04 = QLabel('▣ 지정가유형 주문가격 기준가', self.ui.ss_od_groupBoxxx_05)
        self.ui.ss_buyy_labellll_04.setToolTip('지정가 주문시 주문가격을 정하기 위한 기준가을 선택하십시오.\n0은 기준가격이며 ± 호가단위를 선택하십시오.\n선택한 기준가격에서 ± 호가단위 만큼의 가격이 주문가격이 됨')
        self.ui.ss_buyy_comboBox_01 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_05, items=['현재가', '매도1호가', '매수1호가'])
        self.ui.ss_buyy_comboBox_02 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_05, items=['5', '4', '3', '2', '1', '0', '-1', '-2', '-3', '-4', '-5'])
        self.ui.ss_buyy_labellll_05 = QLabel('▣ 시장가 유형 주문 시 호가범위 선택    매도                   호가', self.ui.ss_od_groupBoxxx_05)
        self.ui.ss_buyy_labellll_05.setToolTip('지정한 호가범위 내의 잔량이 주문수량을 만족할 경우 주문이 전송됨')
        self.ui.ss_buyy_comboBox_03 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_05, items=['1', '2', '3', '4', '5'])

        self.ui.ss_buyy_checkBox_18 = self.wc.setCheckBox('관심이탈', self.ui.ss_od_groupBoxxx_06)
        self.ui.ss_buyy_checkBox_19 = self.wc.setCheckBox('매도시그널', self.ui.ss_od_groupBoxxx_06)
        self.ui.ss_buyy_checkBox_20 = self.wc.setCheckBox('주문 후                      초 경과', self.ui.ss_od_groupBoxxx_06)
        self.ui.ss_buyy_lineEdit_04 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_06)

        self.ui.ss_buyy_checkBox_21 = self.wc.setCheckBox('블랙리스트', self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_checkBox_22 = self.wc.setCheckBox('라운드피겨 ↑                                  호가 이내', self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_lineEdit_05 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_checkBox_23 = self.wc.setCheckBox('손절횟수                                         회 이상', self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_lineEdit_06 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_checkBox_24 = self.wc.setCheckBox('거래횟수                                         회 이상', self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_lineEdit_07 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_checkBox_25 = self.wc.setCheckBox('매수금지시간                                  ~', self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_lineEdit_08 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_lineEdit_09 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_checkBox_26 = self.wc.setCheckBox('이전거래시간                                  초 이내', self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_lineEdit_10 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_checkBox_27 = self.wc.setCheckBox('손절청산 후                                     초 이내', self.ui.ss_od_groupBoxxx_07)
        self.ui.ss_buyy_lineEdit_11 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_07)

        self.ui.ss_buyy_labellll_06 = QLabel('▣ 정정가능 최대횟수 (0:매수정정X)', self.ui.ss_od_groupBoxxx_08)
        self.ui.ss_buyy_lineEdit_12 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_08)
        self.ui.ss_buyy_labellll_07 = QLabel('▣ 정정조건 : 주문가격과 현재가의 차이                    호가이상', self.ui.ss_od_groupBoxxx_08)
        self.ui.ss_buyy_comboBox_04 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_08, items=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        self.ui.ss_buyy_labellll_08 = QLabel('▣ 정정주문 시 정정가격 선택 현재가(-)                    호가', self.ui.ss_od_groupBoxxx_08)
        self.ui.ss_buyy_comboBox_05 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_08, items=['0', '1', '2', '3', '4', '5'])
        self.ui.ss_load_Button_01   = self.wc.setPushbutton('불러오기', parent=self.ui.ss_od_groupBoxxx_08, click=self.ui.SettingOrderLoad_01)
        self.ui.ss_save_Button_01   = self.wc.setPushbutton('저장하기', parent=self.ui.ss_od_groupBoxxx_08, click=self.ui.SettingOrderSave_01)

        bjjj_text = "사용자비중조절기준 선택 시 매수전략에서 아래의 예제와 같이 작성합니다.\n"\
                    "지정한 비중조절기준으로 오른쪽 배팅금액당 배수를 설정하면 적용됩니다.\n"\
                    "예제1: self.비중조절기준 = 체결강도평균대비비율(30)\n"\
                    "예제2: self.비중조절기준 = 구간호가총잔량비율(30)\n"\
                    "예제3: self.비중조절기준 = 저점기준등락율각도(10)\n"\
                    "예제4: self.비중조절기준 = 변동성(30)\n"\
                    "예제5: self.비중조절기준 = 시가총액 <- 국내주식 전용\n"\
                    "예제6: self.비중조절기준 = 리스크 <- 시장미시구조분석 전용\n"\
                    "예제7: self.비중조절기준 = 리스크점수 <- 시장리스크분석 전용"

        self.ui.ss_bj_checkBoxxx_01 = self.wc.setCheckBox('비중조절사용안함', self.ui.ss_od_groupBoxxx_09, changed=self.ui.SettingStockWeightCotrolChanged)
        self.ui.ss_bj_checkBoxxx_02 = self.wc.setCheckBox('저가대비고가등락율', self.ui.ss_od_groupBoxxx_09, changed=self.ui.SettingStockWeightCotrolChanged)
        self.ui.ss_bj_checkBoxxx_03 = self.wc.setCheckBox('거래대금평균대비비율', self.ui.ss_od_groupBoxxx_09, changed=self.ui.SettingStockWeightCotrolChanged)
        self.ui.ss_bj_checkBoxxx_04 = self.wc.setCheckBox('등락율각도', self.ui.ss_od_groupBoxxx_09, changed=self.ui.SettingStockWeightCotrolChanged)
        self.ui.ss_bj_checkBoxxx_05 = self.wc.setCheckBox('당일거래대금각도', self.ui.ss_od_groupBoxxx_09, changed=self.ui.SettingStockWeightCotrolChanged)
        self.ui.ss_bj_checkBoxxx_06 = self.wc.setCheckBox('사용자비중조절기준', self.ui.ss_od_groupBoxxx_09, changed=self.ui.SettingStockWeightCotrolChanged, tip=bjjj_text)
        self.ui.ss_bj_labellllll_01 = QLabel('if    비중조절기준값 <                         :   배팅금액 * ', self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_labellllll_02 = QLabel('elif 비중조절기준값 <                         :   배팅금액 * ', self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_labellllll_03 = QLabel('elif 비중조절기준값 <                         :   배팅금액 * ', self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_labellllll_04 = QLabel('elif 비중조절기준값 <                         :   배팅금액 * ', self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_labellllll_05 = QLabel('else                                                     :   배팅금액 * ', self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_01 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_02 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_03 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_04 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_05 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_06 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_07 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_08 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)
        self.ui.ss_bj_lineEdittt_09 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_09)

        self.ui.ss_bj_check_button_list = [
            self.ui.ss_bj_checkBoxxx_01, self.ui.ss_bj_checkBoxxx_02, self.ui.ss_bj_checkBoxxx_03, self.ui.ss_bj_checkBoxxx_04,
            self.ui.ss_bj_checkBoxxx_05, self.ui.ss_bj_checkBoxxx_06
        ]

        # =============================================================================================================

        self.ui.ss_sell_checkBox_01 = self.wc.setCheckBox('시장가', self.ui.ss_od_groupBoxxx_10,      changed=self.ui.ssCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하는 방식')
        self.ui.ss_sell_checkBox_02 = self.wc.setCheckBox('지정가', self.ui.ss_od_groupBoxxx_10,      changed=self.ui.ssCheckboxChanged_01, tip='원하는 가격에 원하는 수량만큼 주문하는 방식')
        self.ui.ss_sell_checkBox_03 = self.wc.setCheckBox('최유리지정가', self.ui.ss_od_groupBoxxx_10, changed=self.ui.ssCheckboxChanged_01, tip='매수는 매도1호가에 매도는 매수1호가에 원하는 수량만큼 주문하고 부족한 수량은 잔량 대기하는 방식')
        self.ui.ss_sell_checkBox_04 = self.wc.setCheckBox('최우선지정가', self.ui.ss_od_groupBoxxx_10, changed=self.ui.ssCheckboxChanged_01, tip='매수는 매수1호가에 매도는 매도1호가에 원하는 수량만큼 주문하는 방식, 체결이 안될 수도 있음')
        self.ui.ss_sell_checkBox_05 = self.wc.setCheckBox('지정가IOC', self.ui.ss_od_groupBoxxx_10,   changed=self.ui.ssCheckboxChanged_01, tip='원하는 가격에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.ss_sell_checkBox_06 = self.wc.setCheckBox('시장가IOC', self.ui.ss_od_groupBoxxx_10,   changed=self.ui.ssCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.ss_sell_checkBox_07 = self.wc.setCheckBox('최유리IOC', self.ui.ss_od_groupBoxxx_10,   changed=self.ui.ssCheckboxChanged_01, tip='매수는 매도1호가에 매도는 매수1호가에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.ss_sell_checkBox_08 = self.wc.setCheckBox('지정가FOK', self.ui.ss_od_groupBoxxx_10,   changed=self.ui.ssCheckboxChanged_01, tip='원하는 가격에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')
        self.ui.ss_sell_checkBox_09 = self.wc.setCheckBox('시장가FOK', self.ui.ss_od_groupBoxxx_10,   changed=self.ui.ssCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')
        self.ui.ss_sell_checkBox_10 = self.wc.setCheckBox('최유리FOK', self.ui.ss_od_groupBoxxx_10,   changed=self.ui.ssCheckboxChanged_01, tip='매수는 매도호1가에 매도는 매수1호가에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')

        self.ui.sods_checkbox_list1 = [
            self.ui.ss_sell_checkBox_01, self.ui.ss_sell_checkBox_02, self.ui.ss_sell_checkBox_03,
            self.ui.ss_sell_checkBox_04, self.ui.ss_sell_checkBox_05, self.ui.ss_sell_checkBox_06,
            self.ui.ss_sell_checkBox_07, self.ui.ss_sell_checkBox_08, self.ui.ss_sell_checkBox_09,
            self.ui.ss_sell_checkBox_10
        ]

        self.ui.ss_sell_labellll_01 = QLabel('▣ 분할매도횟수 (1:분할매도X)', self.ui.ss_od_groupBoxxx_11)
        self.ui.ss_sell_lineEdit_01 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_11)
        self.ui.ss_sell_labellll_02 = QLabel('▣ 분할매도방법 : 복수선택 불가능', self.ui.ss_od_groupBoxxx_11)
        self.ui.ss_sell_checkBox_11 = self.wc.setCheckBox('균등분할', self.ui.ss_od_groupBoxxx_11, changed=self.ui.ssCheckboxChanged_02, tip='종목당배팅금액을 분할횟수로 균등분할매도\n(예 0: 20., 1: 20., 2: 20., 3: 20., 4: 20.)')
        self.ui.ss_sell_checkBox_12 = self.wc.setCheckBox('비율감소', self.ui.ss_od_groupBoxxx_11, changed=self.ui.ssCheckboxChanged_02, tip='다음 추가매도 시 이전 매도비율의 절반으로 매도\n(예 0: 51.61, 1: 25.81, 2: 12.90, 3: 6.45, 4: 3.23)')
        self.ui.ss_sell_checkBox_13 = self.wc.setCheckBox('비율증가', self.ui.ss_od_groupBoxxx_11, changed=self.ui.ssCheckboxChanged_02, tip='다음 추가매도 시 이전 매도비율의 두배로 매도\n(예 0: 3.23, 1: 6.45, 2: 12.90, 3: 25.81, 4: 51.61)')
        self.ui.ss_sell_labellll_03 = QLabel('▣ 추가매도방법 : 복수선택 가능', self.ui.ss_od_groupBoxxx_11)
        self.ui.ss_sell_checkBox_14 = self.wc.setCheckBox('매도시그널', self.ui.ss_od_groupBoxxx_11, tip='매도시그널을 통해서 추가매도')
        self.ui.ss_sell_checkBox_15 = self.wc.setCheckBox('수익률(-)', self.ui.ss_od_groupBoxxx_11, tip='잔고의 - 수익률를 기준으로 추가매도(0.5설정 시 예: -0.5, -1.0, -1.5, -2.0, -2.5)')
        self.ui.ss_sell_lineEdit_02 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_11)
        self.ui.ss_sell_checkBox_16 = self.wc.setCheckBox('수익률(+)', self.ui.ss_od_groupBoxxx_11, tip='잔고의 + 수익률를 기준으로 추가매도(0.5설정 시 예: +0.5, +1.0, +1.5, +2.0, +2.5)')
        self.ui.ss_sell_lineEdit_03 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_11)

        self.ui.sods_checkbox_list2 = [self.ui.ss_sell_checkBox_11, self.ui.ss_sell_checkBox_12, self.ui.ss_sell_checkBox_13]

        self.ui.ss_sell_labellll_04 = QLabel('▣ 지정가유형 주문가격 기준가', self.ui.ss_od_groupBoxxx_12)
        self.ui.ss_sell_labellll_04.setToolTip('지정가 주문시 주문가격을 정하기 위한 기준가을 선택하십시오.\n0은 기준가격이며 ± 호가단위를 선택하십시오.\n선택한 기준가격에서 ± 호가단위 만큼의 가격이 주문가격이 됨')
        self.ui.ss_sell_comboBox_01 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_12, items=['현재가', '매도1호가', '매수1호가'])
        self.ui.ss_sell_comboBox_02 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_12, items=['5', '4', '3', '2', '1', '0', '-1', '-2', '-3', '-4', '-5'])
        self.ui.ss_sell_labellll_05 = QLabel('▣ 시장가 유형 주문 시 호가범위 선택    매수                   호가', self.ui.ss_od_groupBoxxx_12)
        self.ui.ss_sell_labellll_05.setToolTip('지정한 호가범위 내의 잔량이 주문수량을 만족할 경우 주문이 전송됨')
        self.ui.ss_sell_comboBox_03 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_12, items=['1', '2', '3', '4', '5'])

        self.ui.ss_sell_checkBox_17 = self.wc.setCheckBox('관심진입', self.ui.ss_od_groupBoxxx_13)
        self.ui.ss_sell_checkBox_18 = self.wc.setCheckBox('매수시그널', self.ui.ss_od_groupBoxxx_13)
        self.ui.ss_sell_checkBox_19 = self.wc.setCheckBox('주문 후                      초 경과', self.ui.ss_od_groupBoxxx_13)
        self.ui.ss_sell_lineEdit_04 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_13)

        self.ui.ss_sell_checkBox_20 = self.wc.setCheckBox('분할매수횟수                                 회 이내', self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_lineEdit_05 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_checkBox_21 = self.wc.setCheckBox('라운드피겨 ↓                                  호가 이내', self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_lineEdit_06 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_checkBox_22 = self.wc.setCheckBox('매도금지시간                                  ~', self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_lineEdit_07 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_lineEdit_08 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_checkBox_23 = self.wc.setCheckBox('이전거래시간                                  초 이내', self.ui.ss_od_groupBoxxx_14)
        self.ui.ss_sell_lineEdit_09 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_14)

        self.ui.ss_sell_labellll_06 = QLabel('▣ 정정가능 최대횟수 (0:매도정정X)', self.ui.ss_od_groupBoxxx_15)
        self.ui.ss_sell_lineEdit_10 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_15)
        self.ui.ss_sell_labellll_07 = QLabel('▣ 정정조건 : 주문가격과 현재가의 차이                    호가이상', self.ui.ss_od_groupBoxxx_15)
        self.ui.ss_sell_comboBox_04 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_15, items=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        self.ui.ss_sell_labellll_08 = QLabel('▣ 정정주문 시 정정가격 선택 현재가(+)                    호가', self.ui.ss_od_groupBoxxx_15)
        self.ui.ss_sell_comboBox_05 = self.wc.setCombobox(self.ui.ss_od_groupBoxxx_15, items=['0', '1', '2', '3', '4', '5'])
        self.ui.ss_load_Button_02 = self.wc.setPushbutton('불러오기', parent=self.ui.ss_od_groupBoxxx_15, click=self.ui.SettingOrderLoad_02)
        self.ui.ss_save_Button_02 = self.wc.setPushbutton('저장하기', parent=self.ui.ss_od_groupBoxxx_15, click=self.ui.SettingOrderSave_02)

        self.ui.ss_sell_checkBox_24 = self.wc.setCheckBox('수익률(+)', self.ui.ss_od_groupBoxxx_16)
        self.ui.ss_sell_lineEdit_11 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_16)
        self.ui.ss_sell_checkBox_25 = self.wc.setCheckBox('수익금(+)', self.ui.ss_od_groupBoxxx_16, tip='원, KRW, USDT 일단위의 금액을 입력하십시오.')
        self.ui.ss_sell_lineEdit_12 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_16)

        self.ui.ss_sell_checkBox_26 = self.wc.setCheckBox('수익률(-)', self.ui.ss_od_groupBoxxx_17)
        self.ui.ss_sell_lineEdit_13 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_17)
        self.ui.ss_sell_checkBox_27 = self.wc.setCheckBox('수익금(-)', self.ui.ss_od_groupBoxxx_17, tip='원, KRW, USDT 일단위의 금액을 입력하십시오.')
        self.ui.ss_sell_lineEdit_14 = self.wc.setLineedit(self.ui.ss_od_groupBoxxx_17)

        # =============================================================================================================

        self.ui.sc_od_groupBoxxx_01 = self.wc.setQGroupBox(' 코인 매수주문 설정', self.ui.cod_tab)
        self.ui.sc_od_groupBoxxx_02 = self.wc.setQGroupBox(' 코인 매도주문 설정', self.ui.cod_tab)

        self.ui.sc_od_groupBoxxx_03 = self.wc.setQGroupBox('주문유형', self.ui.sc_od_groupBoxxx_01, hover=True)
        self.ui.sc_od_groupBoxxx_04 = self.wc.setQGroupBox('분할매수', self.ui.sc_od_groupBoxxx_01, hover=True)
        self.ui.sc_od_groupBoxxx_05 = self.wc.setQGroupBox('지정가 기준가격 및 시장가 호가범위', self.ui.sc_od_groupBoxxx_01, hover=True)
        self.ui.sc_od_groupBoxxx_06 = self.wc.setQGroupBox('매수주문취소', self.ui.sc_od_groupBoxxx_01, hover=True)
        self.ui.sc_od_groupBoxxx_07 = self.wc.setQGroupBox('매수금지', self.ui.sc_od_groupBoxxx_01, hover=True)
        self.ui.sc_od_groupBoxxx_08 = self.wc.setQGroupBox('매수정정', self.ui.sc_od_groupBoxxx_01, hover=True)
        self.ui.sc_od_groupBoxxx_09 = self.wc.setQGroupBox('비중조절', self.ui.sc_od_groupBoxxx_01, hover=True)

        self.ui.sc_od_groupBoxxx_10 = self.wc.setQGroupBox('주문유형', self.ui.sc_od_groupBoxxx_02, hover=True)
        self.ui.sc_od_groupBoxxx_11 = self.wc.setQGroupBox('분할매도', self.ui.sc_od_groupBoxxx_02, hover=True)
        self.ui.sc_od_groupBoxxx_12 = self.wc.setQGroupBox('지정가 기준가격 및 시장가 호가범위', self.ui.sc_od_groupBoxxx_02, hover=True)
        self.ui.sc_od_groupBoxxx_13 = self.wc.setQGroupBox('매도주문취소', self.ui.sc_od_groupBoxxx_02, hover=True)
        self.ui.sc_od_groupBoxxx_14 = self.wc.setQGroupBox('매도금지', self.ui.sc_od_groupBoxxx_02, hover=True)
        self.ui.sc_od_groupBoxxx_15 = self.wc.setQGroupBox('매도정정', self.ui.sc_od_groupBoxxx_02, hover=True)
        self.ui.sc_od_groupBoxxx_16 = self.wc.setQGroupBox('익절청산', self.ui.sc_od_groupBoxxx_02, hover=True)
        self.ui.sc_od_groupBoxxx_17 = self.wc.setQGroupBox('손절청산', self.ui.sc_od_groupBoxxx_02, hover=True)

        self.ui.sc_buyy_checkBox_01 = self.wc.setCheckBox('시장가', self.ui.sc_od_groupBoxxx_03,    changed=self.ui.cbCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하는 방식')
        self.ui.sc_buyy_checkBox_02 = self.wc.setCheckBox('지정가', self.ui.sc_od_groupBoxxx_03,    changed=self.ui.cbCheckboxChanged_01, tip='원하는 가격에 원하는 수량만큼 주문하는 방식')
        self.ui.sc_buyy_checkBox_03 = self.wc.setCheckBox('지정가IOC', self.ui.sc_od_groupBoxxx_03, changed=self.ui.cbCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.sc_buyy_checkBox_04 = self.wc.setCheckBox('지정가FOK', self.ui.sc_od_groupBoxxx_03, changed=self.ui.cbCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')

        self.ui.codb_checkbox_list1 = [self.ui.sc_buyy_checkBox_01, self.ui.sc_buyy_checkBox_02, self.ui.sc_buyy_checkBox_03, self.ui.sc_buyy_checkBox_04]

        self.ui.sc_buyy_labellll_01 = QLabel('▣ 분할매수횟수 (1:분할매수X)', self.ui.sc_od_groupBoxxx_04)
        self.ui.sc_buyy_lineEdit_01 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_04)
        self.ui.sc_buyy_labellll_02 = QLabel('▣ 분할매수방법 : 복수선택 불가능', self.ui.sc_od_groupBoxxx_04)
        self.ui.sc_buyy_checkBox_05 = self.wc.setCheckBox('균등분할', self.ui.sc_od_groupBoxxx_04, changed=self.ui.cbCheckboxChanged_02, tip='종목당배팅금액을 분할횟수로 균등분할매수\n(예 0: 20., 1: 20., 2: 20., 3: 20., 4: 20.)')
        self.ui.sc_buyy_checkBox_06 = self.wc.setCheckBox('비율감소', self.ui.sc_od_groupBoxxx_04, changed=self.ui.cbCheckboxChanged_02, tip='다음 추가매수 시 이전 매수비율의 절반으로 매수\n(예 0: 51.61, 1: 25.81, 2: 12.90, 3: 6.45, 4: 3.23)')
        self.ui.sc_buyy_checkBox_07 = self.wc.setCheckBox('비율증가', self.ui.sc_od_groupBoxxx_04, changed=self.ui.cbCheckboxChanged_02, tip='다음 추가매수 시 이전 매수비율의 두배로 매수\n(예 0: 3.23, 1: 6.45, 2: 12.90, 3: 25.81, 4: 51.61)')
        self.ui.sc_buyy_labellll_03 = QLabel('▣ 추가매수방법 : 복수선택 가능', self.ui.sc_od_groupBoxxx_04)
        self.ui.sc_buyy_checkBox_08 = self.wc.setCheckBox('매수시그널', self.ui.sc_od_groupBoxxx_04, tip='매수시그널을 통해서 추가매수')
        self.ui.sc_buyy_checkBox_09 = self.wc.setCheckBox('수익률(-)', self.ui.sc_od_groupBoxxx_04, tip='잔고의 - 수익률를 기준으로 추가매수')
        self.ui.sc_buyy_lineEdit_02 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_04)
        self.ui.sc_buyy_checkBox_10 = self.wc.setCheckBox('수익률(+)', self.ui.sc_od_groupBoxxx_04, tip='잔고의 + 수익률를 기준으로 추가매수')
        self.ui.sc_buyy_lineEdit_03 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_04)
        self.ui.sc_buyy_checkBox_11 = self.wc.setCheckBox('고정수익률', self.ui.sc_od_groupBoxxx_04, tip='수익률(-), 수익률(+)의 수익률기준을 잔고수익률이 아닌\n마지막 매수시점의 현재가 대비 잔고수익률로 변경한다.')

        self.ui.codb_checkbox_list2 = [self.ui.sc_buyy_checkBox_05, self.ui.sc_buyy_checkBox_06, self.ui.sc_buyy_checkBox_07]

        self.ui.sc_buyy_labellll_04 = QLabel('▣ 지정가유형 주문가격 기준가', self.ui.sc_od_groupBoxxx_05)
        self.ui.sc_buyy_labellll_04.setToolTip('지정가 주문시 주문가격을 정하기 위한 기준가을 선택하십시오.\n0은 기준가격이며 ± 호가단위를 선택하십시오.\n선택한 기준가격에서 ± 호가단위 만큼의 가격이 주문가격이 됨')
        self.ui.sc_buyy_comboBox_01 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_05, items=['현재가', '매도1호가', '매수1호가'])
        self.ui.sc_buyy_comboBox_02 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_05, items=['5', '4', '3', '2', '1', '0', '-1', '-2', '-3', '-4', '-5'])
        self.ui.sc_buyy_labellll_05 = QLabel('▣ 시장가 유형 주문 시 호가범위 선택    매도                   호가', self.ui.sc_od_groupBoxxx_05)
        self.ui.sc_buyy_labellll_05.setToolTip('지정한 호가범위 내의 잔량이 주문수량을 만족할 경우 주문이 전송됨')
        self.ui.sc_buyy_comboBox_03 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_05, items=['1', '2', '3', '4', '5'])

        self.ui.sc_buyy_checkBox_12 = self.wc.setCheckBox('관심이탈', self.ui.sc_od_groupBoxxx_06)
        self.ui.sc_buyy_checkBox_13 = self.wc.setCheckBox('매도시그널', self.ui.sc_od_groupBoxxx_06)
        self.ui.sc_buyy_checkBox_14 = self.wc.setCheckBox('주문 후                      초 경과', self.ui.sc_od_groupBoxxx_06)
        self.ui.sc_buyy_lineEdit_04 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_06)

        self.ui.sc_buyy_checkBox_15 = self.wc.setCheckBox('블랙리스트', self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_checkBox_16 = self.wc.setCheckBox('200이하', self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_checkBox_17 = self.wc.setCheckBox('손절횟수                                         회 이상', self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_lineEdit_05 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_checkBox_18 = self.wc.setCheckBox('거래횟수                                         회 이상', self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_lineEdit_06 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_checkBox_19 = self.wc.setCheckBox('매수금지시간                                  ~', self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_lineEdit_07 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_lineEdit_08 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_checkBox_20 = self.wc.setCheckBox('이전거래시간                                  초 이내', self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_lineEdit_09 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_checkBox_21 = self.wc.setCheckBox('손절청산 후                                     초 이내', self.ui.sc_od_groupBoxxx_07)
        self.ui.sc_buyy_lineEdit_10 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_07)

        self.ui.sc_buyy_labellll_06 = QLabel('▣ 정정가능 최대횟수 (0:매수정정X)', self.ui.sc_od_groupBoxxx_08)
        self.ui.sc_buyy_lineEdit_11 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_08)
        self.ui.sc_buyy_labellll_07 = QLabel('▣ 정정조건 : 주문가격과 현재가의 차이                    호가이상', self.ui.sc_od_groupBoxxx_08)
        self.ui.sc_buyy_comboBox_04 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_08, items=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        self.ui.sc_buyy_labellll_08 = QLabel('▣ 정정주문 시 정정가격 선택 현재가(-)                    호가', self.ui.sc_od_groupBoxxx_08)
        self.ui.sc_buyy_comboBox_05 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_08, items=['0', '1', '2', '3', '4', '5'])
        self.ui.sc_load_Button_01 = self.wc.setPushbutton('불러오기', parent=self.ui.sc_od_groupBoxxx_08, click=self.ui.SettingOrderLoad_03)
        self.ui.sc_save_Button_01 = self.wc.setPushbutton('저장하기', parent=self.ui.sc_od_groupBoxxx_08, click=self.ui.SettingOrderSave_03)

        self.ui.sc_bj_checkBoxxx_01 = self.wc.setCheckBox('비중조절사용안함', self.ui.sc_od_groupBoxxx_09, changed=self.ui.SettingCoinWeightCotrolChanged)
        self.ui.sc_bj_checkBoxxx_02 = self.wc.setCheckBox('저가대비고가등락율', self.ui.sc_od_groupBoxxx_09, changed=self.ui.SettingCoinWeightCotrolChanged)
        self.ui.sc_bj_checkBoxxx_03 = self.wc.setCheckBox('거래대금평균대비비율', self.ui.sc_od_groupBoxxx_09, changed=self.ui.SettingCoinWeightCotrolChanged)
        self.ui.sc_bj_checkBoxxx_04 = self.wc.setCheckBox('등락율각도', self.ui.sc_od_groupBoxxx_09, changed=self.ui.SettingCoinWeightCotrolChanged)
        self.ui.sc_bj_checkBoxxx_05 = self.wc.setCheckBox('당일거래대금각도', self.ui.sc_od_groupBoxxx_09, changed=self.ui.SettingCoinWeightCotrolChanged)
        self.ui.sc_bj_checkBoxxx_06 = self.wc.setCheckBox('사용자비중조절기준', self.ui.sc_od_groupBoxxx_09, changed=self.ui.SettingCoinWeightCotrolChanged, tip=bjjj_text)
        self.ui.sc_bj_labellllll_01 = QLabel('if    비중조절기준값 <                         :   배팅금액 * ', self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_labellllll_02 = QLabel('elif 비중조절기준값 <                         :   배팅금액 * ', self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_labellllll_03 = QLabel('elif 비중조절기준값 <                         :   배팅금액 * ', self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_labellllll_04 = QLabel('elif 비중조절기준값 <                         :   배팅금액 * ', self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_labellllll_05 = QLabel('else                                                     :   배팅금액 * ', self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_01 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_02 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_03 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_04 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_05 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_06 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_07 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_08 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)
        self.ui.sc_bj_lineEdittt_09 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_09)

        self.ui.sc_bj_check_button_list = [
            self.ui.sc_bj_checkBoxxx_01, self.ui.sc_bj_checkBoxxx_02, self.ui.sc_bj_checkBoxxx_03, self.ui.sc_bj_checkBoxxx_04,
            self.ui.sc_bj_checkBoxxx_05, self.ui.sc_bj_checkBoxxx_06
        ]

        # =============================================================================================================

        self.ui.sc_sell_checkBox_01 = self.wc.setCheckBox('시장가', self.ui.sc_od_groupBoxxx_10,    changed=self.ui.csCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하는 방식')
        self.ui.sc_sell_checkBox_02 = self.wc.setCheckBox('지정가', self.ui.sc_od_groupBoxxx_10,    changed=self.ui.csCheckboxChanged_01, tip='원하는 가격에 원하는 수량만큼 주문하는 방식')
        self.ui.sc_sell_checkBox_03 = self.wc.setCheckBox('지정가IOC', self.ui.sc_od_groupBoxxx_10, changed=self.ui.csCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량만큼 주문하고 미체결수량은 취소하는 방식')
        self.ui.sc_sell_checkBox_04 = self.wc.setCheckBox('지정가FOK', self.ui.sc_od_groupBoxxx_10, changed=self.ui.csCheckboxChanged_01, tip='매수는 매도호가에 매도는 매수호가에 원하는 수량이 있을 경우 주문하고 없을 경우 취소하는 방식')

        self.ui.cods_checkbox_list1 = [self.ui.sc_sell_checkBox_01, self.ui.sc_sell_checkBox_02, self.ui.sc_sell_checkBox_03, self.ui.sc_sell_checkBox_04]

        self.ui.sc_sell_labellll_01 = QLabel('▣ 분할매도횟수 (1:분할매도X)', self.ui.sc_od_groupBoxxx_11)
        self.ui.sc_sell_lineEdit_01 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_11)
        self.ui.sc_sell_labellll_02 = QLabel('▣ 분할매도방법 : 복수선택 불가능', self.ui.sc_od_groupBoxxx_11)
        self.ui.sc_sell_checkBox_05 = self.wc.setCheckBox('균등분할', self.ui.sc_od_groupBoxxx_11, changed=self.ui.csCheckboxChanged_02, tip='종목당배팅금액을 분할횟수로 균등분할매도\n(예 0: 20., 1: 20., 2: 20., 3: 20., 4: 20.)')
        self.ui.sc_sell_checkBox_06 = self.wc.setCheckBox('비율감소', self.ui.sc_od_groupBoxxx_11, changed=self.ui.csCheckboxChanged_02, tip='다음 추가매도 시 이전 매도비율의 절반으로 매도\n(예 0: 51.61, 1: 25.81, 2: 12.90, 3: 6.45, 4: 3.23)')
        self.ui.sc_sell_checkBox_07 = self.wc.setCheckBox('비율증가', self.ui.sc_od_groupBoxxx_11, changed=self.ui.csCheckboxChanged_02, tip='다음 추가매도 시 이전 매도비율의 두배로 매도\n(예 0: 3.23, 1: 6.45, 2: 12.90, 3: 25.81, 4: 51.61)')
        self.ui.sc_sell_labellll_03 = QLabel('▣ 추가매도방법 : 복수선택 가능', self.ui.sc_od_groupBoxxx_11)
        self.ui.sc_sell_checkBox_08 = self.wc.setCheckBox('매도시그널', self.ui.sc_od_groupBoxxx_11, tip='매도시그널을 통해서 추가매도')
        self.ui.sc_sell_checkBox_09 = self.wc.setCheckBox('수익률(-)', self.ui.sc_od_groupBoxxx_11, tip='잔고의 - 수익률를 기준으로 추가매도(0.5설정 시 예: -0.5, -1.0, -1.5, -2.0, -2.5)')
        self.ui.sc_sell_lineEdit_02 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_11)
        self.ui.sc_sell_checkBox_10 = self.wc.setCheckBox('수익률(+)', self.ui.sc_od_groupBoxxx_11, tip='잔고의 + 수익률를 기준으로 추가매도(0.5설정 시 예: +0.5, +1.0, +1.5, +2.0, +2.5)')
        self.ui.sc_sell_lineEdit_03 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_11)

        self.ui.cods_checkbox_list2 = [self.ui.sc_sell_checkBox_05, self.ui.sc_sell_checkBox_06, self.ui.sc_sell_checkBox_07]

        self.ui.sc_sell_labellll_04 = QLabel('▣ 지정가유형 주문가격 기준가', self.ui.sc_od_groupBoxxx_12)
        self.ui.sc_sell_labellll_04.setToolTip('지정가 주문시 주문가격을 정하기 위한 기준가을 선택하십시오.\n0은 기준가격이며 ± 호가단위를 선택하십시오.\n선택한 기준가격에서 ± 호가단위 만큼의 가격이 주문가격이 됨')
        self.ui.sc_sell_comboBox_01 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_12, items=['현재가', '매도1호가', '매수1호가'])
        self.ui.sc_sell_comboBox_02 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_12, items=['5', '4', '3', '2', '1', '0', '-1', '-2', '-3', '-4', '-5'])
        self.ui.sc_sell_labellll_05 = QLabel('▣ 시장가 유형 주문 시 호가범위 선택    매수                   호가', self.ui.sc_od_groupBoxxx_12)
        self.ui.sc_sell_labellll_05.setToolTip('지정한 호가범위 내의 잔량이 주문수량을 만족할 경우 주문이 전송됨')
        self.ui.sc_sell_comboBox_03 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_12, items=['1', '2', '3', '4', '5'])

        self.ui.sc_sell_checkBox_11 = self.wc.setCheckBox('관심진입', self.ui.sc_od_groupBoxxx_13)
        self.ui.sc_sell_checkBox_12 = self.wc.setCheckBox('매수시그널', self.ui.sc_od_groupBoxxx_13)
        self.ui.sc_sell_checkBox_13 = self.wc.setCheckBox('주문 후                      초 경과', self.ui.sc_od_groupBoxxx_13)
        self.ui.sc_sell_lineEdit_04 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_13)

        self.ui.sc_sell_checkBox_14 = self.wc.setCheckBox('분할매수횟수                                 회 이내', self.ui.sc_od_groupBoxxx_14)
        self.ui.sc_sell_lineEdit_05 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_14)
        self.ui.sc_sell_checkBox_15 = self.wc.setCheckBox('매도금지시간                                  ~', self.ui.sc_od_groupBoxxx_14)
        self.ui.sc_sell_lineEdit_06 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_14)
        self.ui.sc_sell_lineEdit_07 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_14)
        self.ui.sc_sell_checkBox_16 = self.wc.setCheckBox('이전거래시간                                  초 이내', self.ui.sc_od_groupBoxxx_14)
        self.ui.sc_sell_lineEdit_08 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_14)

        self.ui.sc_sell_labellll_06 = QLabel('▣ 정정가능 최대횟수 (0:매도정정X)', self.ui.sc_od_groupBoxxx_15)
        self.ui.sc_sell_labellll_07 = QLabel('▣ 정정조건 : 주문가격과 현재가의 차이                    호가이상', self.ui.sc_od_groupBoxxx_15)
        self.ui.sc_sell_labellll_08 = QLabel('▣ 정정주문 시 정정가격 선택 현재가(+)                    호가', self.ui.sc_od_groupBoxxx_15)
        self.ui.sc_sell_lineEdit_09 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_15)
        self.ui.sc_sell_comboBox_04 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_15, items=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
        self.ui.sc_sell_comboBox_05 = self.wc.setCombobox(self.ui.sc_od_groupBoxxx_15, items=['0', '1', '2', '3', '4', '5'])
        self.ui.sc_load_Button_02 = self.wc.setPushbutton('불러오기', parent=self.ui.sc_od_groupBoxxx_15, click=self.ui.SettingOrderLoad_04)
        self.ui.sc_save_Button_02 = self.wc.setPushbutton('저장하기', parent=self.ui.sc_od_groupBoxxx_15, click=self.ui.SettingOrderSave_04)

        self.ui.sc_sell_checkBox_17 = self.wc.setCheckBox('수익률(+)', self.ui.sc_od_groupBoxxx_16)
        self.ui.sc_sell_lineEdit_10 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_16)
        self.ui.sc_sell_checkBox_18 = self.wc.setCheckBox('수익금(+)', self.ui.sc_od_groupBoxxx_16, tip='원, KRW, USDT 일단위의 금액을 입력하십시오.')
        self.ui.sc_sell_lineEdit_11 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_16)

        self.ui.sc_sell_checkBox_19 = self.wc.setCheckBox('수익률(-)', self.ui.sc_od_groupBoxxx_17)
        self.ui.sc_sell_lineEdit_12 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_17)
        self.ui.sc_sell_checkBox_20 = self.wc.setCheckBox('수익금(-)', self.ui.sc_od_groupBoxxx_17, tip='원, KRW, USDT 일단위의 금액을 입력하십시오.')
        self.ui.sc_sell_lineEdit_13 = self.wc.setLineedit(self.ui.sc_od_groupBoxxx_17)

        # =============================================================================================================
        # 주식 주문 설정 위젯
        # =============================================================================================================

        # 메인 그룹박스들
        self.ui.ss_od_groupBoxxx_01.setGeometry(5, 5, 660, 703)
        self.ui.ss_od_groupBoxxx_02.setGeometry(670, 5, 660, 703)

        # 매수 그룹 내부 그룹박스들
        self.ui.ss_od_groupBoxxx_03.setGeometry(7, 20, 645, 75)
        self.ui.ss_od_groupBoxxx_04.setGeometry(7, 100, 645, 100)
        self.ui.ss_od_groupBoxxx_05.setGeometry(7, 205, 645, 50)
        self.ui.ss_od_groupBoxxx_06.setGeometry(7, 260, 645, 50)
        self.ui.ss_od_groupBoxxx_07.setGeometry(7, 315, 320, 200)
        self.ui.ss_od_groupBoxxx_08.setGeometry(332, 315, 320, 200)
        self.ui.ss_od_groupBoxxx_09.setGeometry(7, 520, 645, 175)

        # 매도 그룹 내부 그룹박스들
        self.ui.ss_od_groupBoxxx_10.setGeometry(7, 20, 645, 75)
        self.ui.ss_od_groupBoxxx_11.setGeometry(7, 100, 645, 100)
        self.ui.ss_od_groupBoxxx_12.setGeometry(7, 205, 645, 50)
        self.ui.ss_od_groupBoxxx_13.setGeometry(7, 260, 645, 50)
        self.ui.ss_od_groupBoxxx_14.setGeometry(7, 315, 320, 200)
        self.ui.ss_od_groupBoxxx_15.setGeometry(332, 315, 320, 200)
        self.ui.ss_od_groupBoxxx_16.setGeometry(7, 520, 645, 50)
        self.ui.ss_od_groupBoxxx_17.setGeometry(7, 575, 645, 50)

        # 매수 주문유형
        self.ui.ss_buyy_checkBox_01.setGeometry(10, 25, 100, 20)
        self.ui.ss_buyy_checkBox_02.setGeometry(120, 25, 100, 20)
        self.ui.ss_buyy_checkBox_03.setGeometry(230, 25, 110, 20)
        self.ui.ss_buyy_checkBox_04.setGeometry(350, 25, 110, 20)
        self.ui.ss_buyy_checkBox_05.setGeometry(470, 25, 100, 20)
        self.ui.ss_buyy_checkBox_06.setGeometry(10, 50, 100, 20)
        self.ui.ss_buyy_checkBox_07.setGeometry(120, 50, 110, 20)
        self.ui.ss_buyy_checkBox_08.setGeometry(230, 50, 100, 20)
        self.ui.ss_buyy_checkBox_09.setGeometry(350, 50, 100, 20)
        self.ui.ss_buyy_checkBox_10.setGeometry(470, 50, 110, 20)

        # 분할매수
        self.ui.ss_buyy_labellll_01.setGeometry(10, 25, 200, 20)
        self.ui.ss_buyy_lineEdit_01.setGeometry(200, 25, 50, 20)
        self.ui.ss_buyy_labellll_02.setGeometry(10, 50, 200, 20)
        self.ui.ss_buyy_checkBox_11.setGeometry(200, 50, 90, 20)
        self.ui.ss_buyy_checkBox_12.setGeometry(290, 50, 90, 20)
        self.ui.ss_buyy_checkBox_13.setGeometry(380, 50, 90, 20)
        self.ui.ss_buyy_labellll_03.setGeometry(10, 75, 200, 20)
        self.ui.ss_buyy_checkBox_14.setGeometry(200, 75, 90, 20)
        self.ui.ss_buyy_checkBox_15.setGeometry(290, 75, 90, 20)
        self.ui.ss_buyy_lineEdit_02.setGeometry(360, 75, 30, 20)
        self.ui.ss_buyy_checkBox_16.setGeometry(400, 75, 90, 20)
        self.ui.ss_buyy_lineEdit_03.setGeometry(470, 75, 30, 20)
        self.ui.ss_buyy_checkBox_17.setGeometry(510, 75, 90, 20)

        # 지정가 기준가격, 시장가 호가 범위
        self.ui.ss_buyy_labellll_04.setGeometry(10, 25, 200, 20)
        self.ui.ss_buyy_comboBox_01.setGeometry(175, 25, 80, 20)
        self.ui.ss_buyy_comboBox_02.setGeometry(260, 25, 50, 20)
        self.ui.ss_buyy_labellll_05.setGeometry(330, 25, 300, 20)
        self.ui.ss_buyy_comboBox_03.setGeometry(550, 25, 50, 20)

        # 매수주문취소
        self.ui.ss_buyy_checkBox_18.setGeometry(10, 25, 90, 20)
        self.ui.ss_buyy_checkBox_19.setGeometry(100, 25, 90, 20)
        self.ui.ss_buyy_checkBox_20.setGeometry(200, 25, 170, 20)
        self.ui.ss_buyy_lineEdit_04.setGeometry(262, 25, 50, 20)

        # 매수금지
        self.ui.ss_buyy_checkBox_21.setGeometry(10, 25, 310, 20)
        self.ui.ss_buyy_checkBox_22.setGeometry(10, 50, 310, 20)
        self.ui.ss_buyy_lineEdit_05.setGeometry(110, 50, 80, 20)
        self.ui.ss_buyy_checkBox_23.setGeometry(10, 75, 310, 20)
        self.ui.ss_buyy_lineEdit_06.setGeometry(110, 75, 80, 20)
        self.ui.ss_buyy_checkBox_24.setGeometry(10, 100, 310, 20)
        self.ui.ss_buyy_lineEdit_07.setGeometry(110, 100, 80, 20)
        self.ui.ss_buyy_checkBox_25.setGeometry(10, 125, 310, 20)
        self.ui.ss_buyy_lineEdit_08.setGeometry(110, 125, 80, 20)
        self.ui.ss_buyy_lineEdit_09.setGeometry(210, 125, 80, 20)
        self.ui.ss_buyy_checkBox_26.setGeometry(10, 150, 310, 20)
        self.ui.ss_buyy_lineEdit_10.setGeometry(110, 150, 80, 20)
        self.ui.ss_buyy_checkBox_27.setGeometry(10, 175, 310, 20)
        self.ui.ss_buyy_lineEdit_11.setGeometry(110, 175, 80, 20)

        # 매수정정
        self.ui.ss_buyy_labellll_06.setGeometry(10, 25, 310, 20)
        self.ui.ss_buyy_lineEdit_12.setGeometry(210, 25, 50, 20)
        self.ui.ss_buyy_labellll_07.setGeometry(10, 50, 310, 20)
        self.ui.ss_buyy_comboBox_04.setGeometry(210, 50, 50, 20)
        self.ui.ss_buyy_labellll_08.setGeometry(10, 75, 310, 20)
        self.ui.ss_buyy_comboBox_05.setGeometry(210, 75, 50, 20)

        # 불러오기, 저장하기
        self.ui.ss_load_Button_01.setGeometry(8, 162, 150, 30)
        self.ui.ss_save_Button_01.setGeometry(163, 162, 150, 30)

        # 비중조절
        self.ui.ss_bj_checkBoxxx_01.setGeometry(10, 25, 150, 20)
        self.ui.ss_bj_checkBoxxx_02.setGeometry(10, 50, 150, 20)
        self.ui.ss_bj_checkBoxxx_03.setGeometry(10, 75, 150, 20)
        self.ui.ss_bj_checkBoxxx_04.setGeometry(10, 100, 150, 20)
        self.ui.ss_bj_checkBoxxx_05.setGeometry(10, 125, 150, 20)
        self.ui.ss_bj_checkBoxxx_06.setGeometry(10, 150, 150, 20)

        self.ui.ss_bj_labellllll_01.setGeometry(325, 25, 300, 20)
        self.ui.ss_bj_labellllll_02.setGeometry(325, 50, 300, 20)
        self.ui.ss_bj_labellllll_03.setGeometry(325, 75, 300, 20)
        self.ui.ss_bj_labellllll_04.setGeometry(325, 100, 300, 20)
        self.ui.ss_bj_labellllll_05.setGeometry(325, 125, 300, 20)
        self.ui.ss_bj_lineEdittt_01.setGeometry(440, 25, 60, 20)
        self.ui.ss_bj_lineEdittt_02.setGeometry(580, 25, 60, 20)
        self.ui.ss_bj_lineEdittt_03.setGeometry(440, 50, 60, 20)
        self.ui.ss_bj_lineEdittt_04.setGeometry(580, 50, 60, 20)
        self.ui.ss_bj_lineEdittt_05.setGeometry(440, 75, 60, 20)
        self.ui.ss_bj_lineEdittt_06.setGeometry(580, 75, 60, 20)
        self.ui.ss_bj_lineEdittt_07.setGeometry(440, 100, 60, 20)
        self.ui.ss_bj_lineEdittt_08.setGeometry(580, 100, 60, 20)
        self.ui.ss_bj_lineEdittt_09.setGeometry(580, 125, 60, 20)

        # 매도 주문유형
        self.ui.ss_sell_checkBox_01.setGeometry(10, 25, 100, 20)
        self.ui.ss_sell_checkBox_02.setGeometry(120, 25, 100, 20)
        self.ui.ss_sell_checkBox_03.setGeometry(230, 25, 100, 20)
        self.ui.ss_sell_checkBox_04.setGeometry(350, 25, 100, 20)
        self.ui.ss_sell_checkBox_05.setGeometry(470, 25, 100, 20)
        self.ui.ss_sell_checkBox_06.setGeometry(10, 50, 100, 20)
        self.ui.ss_sell_checkBox_07.setGeometry(120, 50, 100, 20)
        self.ui.ss_sell_checkBox_08.setGeometry(230, 50, 100, 20)
        self.ui.ss_sell_checkBox_09.setGeometry(350, 50, 100, 20)
        self.ui.ss_sell_checkBox_10.setGeometry(470, 50, 100, 20)

        # 분할매도
        self.ui.ss_sell_labellll_01.setGeometry(10, 25, 200, 20)
        self.ui.ss_sell_lineEdit_01.setGeometry(200, 25, 50, 20)
        self.ui.ss_sell_labellll_02.setGeometry(10, 50, 200, 20)
        self.ui.ss_sell_checkBox_11.setGeometry(200, 50, 90, 20)
        self.ui.ss_sell_checkBox_12.setGeometry(290, 50, 90, 20)
        self.ui.ss_sell_checkBox_13.setGeometry(380, 50, 90, 20)
        self.ui.ss_sell_labellll_03.setGeometry(10, 75, 200, 20)
        self.ui.ss_sell_checkBox_14.setGeometry(200, 75, 90, 20)
        self.ui.ss_sell_checkBox_15.setGeometry(290, 75, 90, 20)
        self.ui.ss_sell_lineEdit_02.setGeometry(360, 75, 30, 20)
        self.ui.ss_sell_checkBox_16.setGeometry(400, 75, 90, 20)
        self.ui.ss_sell_lineEdit_03.setGeometry(470, 75, 30, 20)

        # 지정가 기준가격, 호가 범위
        self.ui.ss_sell_labellll_04.setGeometry(10, 25, 200, 20)
        self.ui.ss_sell_comboBox_01.setGeometry(175, 25, 80, 20)
        self.ui.ss_sell_comboBox_02.setGeometry(260, 25, 50, 20)
        self.ui.ss_sell_labellll_05.setGeometry(330, 25, 300, 20)
        self.ui.ss_sell_comboBox_03.setGeometry(550, 25, 50, 20)

        # 매도주문취소
        self.ui.ss_sell_checkBox_17.setGeometry(10, 25, 90, 20)
        self.ui.ss_sell_checkBox_18.setGeometry(100, 25, 90, 20)
        self.ui.ss_sell_checkBox_19.setGeometry(200, 25, 170, 20)
        self.ui.ss_sell_lineEdit_04.setGeometry(262, 25, 50, 20)

        # 매도금지
        self.ui.ss_sell_checkBox_20.setGeometry(10, 25, 310, 20)
        self.ui.ss_sell_lineEdit_05.setGeometry(110, 25, 80, 20)
        self.ui.ss_sell_checkBox_21.setGeometry(10, 50, 310, 20)
        self.ui.ss_sell_lineEdit_06.setGeometry(110, 50, 80, 20)
        self.ui.ss_sell_checkBox_22.setGeometry(10, 75, 310, 20)
        self.ui.ss_sell_lineEdit_07.setGeometry(110, 75, 80, 20)
        self.ui.ss_sell_lineEdit_08.setGeometry(210, 75, 80, 20)
        self.ui.ss_sell_checkBox_23.setGeometry(10, 100, 310, 20)
        self.ui.ss_sell_lineEdit_09.setGeometry(110, 100, 80, 20)

        # 매도정정
        self.ui.ss_sell_labellll_06.setGeometry(10, 25, 310, 20)
        self.ui.ss_sell_lineEdit_10.setGeometry(210, 25, 50, 20)
        self.ui.ss_sell_labellll_07.setGeometry(10, 50, 310, 20)
        self.ui.ss_sell_comboBox_04.setGeometry(210, 50, 50, 20)
        self.ui.ss_sell_labellll_08.setGeometry(10, 75, 310, 20)
        self.ui.ss_sell_comboBox_05.setGeometry(210, 75, 50, 20)

        # 불러오기, 저장하기
        self.ui.ss_load_Button_02.setGeometry(8, 162, 150, 30)
        self.ui.ss_save_Button_02.setGeometry(163, 162, 150, 30)

        # 익절청산
        self.ui.ss_sell_checkBox_24.setGeometry(10, 25, 80, 20)
        self.ui.ss_sell_lineEdit_11.setGeometry(90, 25, 50, 20)
        self.ui.ss_sell_checkBox_25.setGeometry(160, 25, 80, 20)
        self.ui.ss_sell_lineEdit_12.setGeometry(240, 25, 80, 20)

        # 손절청산
        self.ui.ss_sell_checkBox_26.setGeometry(10, 25, 80, 20)
        self.ui.ss_sell_lineEdit_13.setGeometry(90, 25, 50, 20)
        self.ui.ss_sell_checkBox_27.setGeometry(160, 25, 80, 20)
        self.ui.ss_sell_lineEdit_14.setGeometry(240, 25, 80, 20)

        # =============================================================================================================
        # 코인 주문 설정 위젯
        # =============================================================================================================

        # 메인 그룹박스들
        self.ui.sc_od_groupBoxxx_01.setGeometry(5, 5, 660, 703)
        self.ui.sc_od_groupBoxxx_02.setGeometry(670, 5, 660, 703)

        # 매수 그룹 내부 그룹박스들
        self.ui.sc_od_groupBoxxx_03.setGeometry(7, 20, 645, 75)
        self.ui.sc_od_groupBoxxx_04.setGeometry(7, 100, 645, 100)
        self.ui.sc_od_groupBoxxx_05.setGeometry(7, 205, 645, 50)
        self.ui.sc_od_groupBoxxx_06.setGeometry(7, 260, 645, 50)
        self.ui.sc_od_groupBoxxx_07.setGeometry(7, 315, 320, 200)
        self.ui.sc_od_groupBoxxx_08.setGeometry(332, 315, 320, 200)
        self.ui.sc_od_groupBoxxx_09.setGeometry(7, 520, 645, 175)

        # 매도 그룹 내부 그룹박스들
        self.ui.sc_od_groupBoxxx_10.setGeometry(7, 20, 645, 75)
        self.ui.sc_od_groupBoxxx_11.setGeometry(7, 100, 645, 100)
        self.ui.sc_od_groupBoxxx_12.setGeometry(7, 205, 645, 50)
        self.ui.sc_od_groupBoxxx_13.setGeometry(7, 260, 645, 50)
        self.ui.sc_od_groupBoxxx_14.setGeometry(7, 315, 320, 200)
        self.ui.sc_od_groupBoxxx_15.setGeometry(332, 315, 320, 200)
        self.ui.sc_od_groupBoxxx_16.setGeometry(7, 520, 645, 50)
        self.ui.sc_od_groupBoxxx_17.setGeometry(7, 575, 645, 50)

        # 매수주문유형
        self.ui.sc_buyy_checkBox_01.setGeometry(10, 25, 100, 20)
        self.ui.sc_buyy_checkBox_02.setGeometry(120, 25, 100, 20)
        self.ui.sc_buyy_checkBox_03.setGeometry(230, 25, 100, 20)
        self.ui.sc_buyy_checkBox_04.setGeometry(350, 25, 100, 20)

        # 분할매수
        self.ui.sc_buyy_labellll_01.setGeometry(10, 25, 200, 20)
        self.ui.sc_buyy_lineEdit_01.setGeometry(200, 25, 50, 20)
        self.ui.sc_buyy_labellll_02.setGeometry(10, 50, 200, 20)
        self.ui.sc_buyy_checkBox_05.setGeometry(200, 50, 90, 20)
        self.ui.sc_buyy_checkBox_06.setGeometry(290, 50, 90, 20)
        self.ui.sc_buyy_checkBox_07.setGeometry(380, 50, 90, 20)
        self.ui.sc_buyy_labellll_03.setGeometry(10, 75, 200, 20)
        self.ui.sc_buyy_checkBox_08.setGeometry(200, 75, 90, 20)
        self.ui.sc_buyy_checkBox_09.setGeometry(290, 75, 90, 20)
        self.ui.sc_buyy_lineEdit_02.setGeometry(360, 75, 30, 20)
        self.ui.sc_buyy_checkBox_10.setGeometry(400, 75, 90, 20)
        self.ui.sc_buyy_lineEdit_03.setGeometry(470, 75, 30, 20)
        self.ui.sc_buyy_checkBox_11.setGeometry(510, 75, 90, 20)

        # 지정가 기준가격, 시장가 호가 범위
        self.ui.sc_buyy_labellll_04.setGeometry(10, 25, 200, 20)
        self.ui.sc_buyy_comboBox_01.setGeometry(175, 25, 80, 20)
        self.ui.sc_buyy_comboBox_02.setGeometry(260, 25, 50, 20)
        self.ui.sc_buyy_labellll_05.setGeometry(330, 25, 300, 20)
        self.ui.sc_buyy_comboBox_03.setGeometry(550, 25, 50, 20)

        # 매수주문취소
        self.ui.sc_buyy_checkBox_12.setGeometry(10, 25, 90, 20)
        self.ui.sc_buyy_checkBox_13.setGeometry(100, 25, 90, 20)
        self.ui.sc_buyy_checkBox_14.setGeometry(200, 25, 170, 20)
        self.ui.sc_buyy_lineEdit_04.setGeometry(262, 25, 50, 20)

        # 매수금지
        self.ui.sc_buyy_checkBox_15.setGeometry(10, 25, 310, 20)
        self.ui.sc_buyy_checkBox_16.setGeometry(10, 50, 310, 20)
        self.ui.sc_buyy_checkBox_17.setGeometry(10, 75, 310, 20)
        self.ui.sc_buyy_lineEdit_05.setGeometry(110, 75, 80, 20)
        self.ui.sc_buyy_checkBox_18.setGeometry(10, 100, 310, 20)
        self.ui.sc_buyy_lineEdit_06.setGeometry(110, 100, 80, 20)
        self.ui.sc_buyy_checkBox_19.setGeometry(10, 125, 310, 20)
        self.ui.sc_buyy_lineEdit_07.setGeometry(110, 125, 80, 20)
        self.ui.sc_buyy_lineEdit_08.setGeometry(210, 125, 80, 20)
        self.ui.sc_buyy_checkBox_20.setGeometry(10, 150, 310, 20)
        self.ui.sc_buyy_lineEdit_09.setGeometry(110, 150, 80, 20)
        self.ui.sc_buyy_checkBox_21.setGeometry(10, 175, 310, 20)
        self.ui.sc_buyy_lineEdit_10.setGeometry(110, 175, 80, 20)

        # 매수정정
        self.ui.sc_buyy_labellll_06.setGeometry(10, 25, 310, 20)
        self.ui.sc_buyy_lineEdit_11.setGeometry(210, 25, 50, 20)
        self.ui.sc_buyy_labellll_07.setGeometry(10, 50, 310, 20)
        self.ui.sc_buyy_comboBox_04.setGeometry(210, 50, 50, 20)
        self.ui.sc_buyy_labellll_08.setGeometry(10, 75, 310, 20)
        self.ui.sc_buyy_comboBox_05.setGeometry(210, 75, 50, 20)

        # 불러오기, 저장하기
        self.ui.sc_load_Button_01.setGeometry(8, 162, 150, 30)
        self.ui.sc_save_Button_01.setGeometry(163, 162, 150, 30)

        # 비중조절
        self.ui.sc_bj_checkBoxxx_01.setGeometry(10, 25, 150, 20)
        self.ui.sc_bj_checkBoxxx_02.setGeometry(10, 50, 150, 20)
        self.ui.sc_bj_checkBoxxx_03.setGeometry(10, 75, 150, 20)
        self.ui.sc_bj_checkBoxxx_04.setGeometry(10, 100, 150, 20)
        self.ui.sc_bj_checkBoxxx_05.setGeometry(10, 125, 150, 20)
        self.ui.sc_bj_checkBoxxx_06.setGeometry(10, 150, 150, 20)

        self.ui.sc_bj_labellllll_01.setGeometry(325, 25, 300, 20)
        self.ui.sc_bj_labellllll_02.setGeometry(325, 50, 300, 20)
        self.ui.sc_bj_labellllll_03.setGeometry(325, 75, 300, 20)
        self.ui.sc_bj_labellllll_04.setGeometry(325, 100, 300, 20)
        self.ui.sc_bj_labellllll_05.setGeometry(325, 125, 300, 20)
        self.ui.sc_bj_lineEdittt_01.setGeometry(440, 25, 60, 20)
        self.ui.sc_bj_lineEdittt_02.setGeometry(580, 25, 60, 20)
        self.ui.sc_bj_lineEdittt_03.setGeometry(440, 50, 60, 20)
        self.ui.sc_bj_lineEdittt_04.setGeometry(580, 50, 60, 20)
        self.ui.sc_bj_lineEdittt_05.setGeometry(440, 75, 60, 20)
        self.ui.sc_bj_lineEdittt_06.setGeometry(580, 75, 60, 20)
        self.ui.sc_bj_lineEdittt_07.setGeometry(440, 100, 60, 20)
        self.ui.sc_bj_lineEdittt_08.setGeometry(580, 100, 60, 20)
        self.ui.sc_bj_lineEdittt_09.setGeometry(580, 125, 60, 20)

        # 매도 주문유형
        self.ui.sc_sell_checkBox_01.setGeometry(10, 25, 100, 20)
        self.ui.sc_sell_checkBox_02.setGeometry(120, 25, 100, 20)
        self.ui.sc_sell_checkBox_03.setGeometry(230, 25, 100, 20)
        self.ui.sc_sell_checkBox_04.setGeometry(350, 25, 100, 20)

        # 분할매도
        self.ui.sc_sell_labellll_01.setGeometry(10, 25, 200, 20)
        self.ui.sc_sell_lineEdit_01.setGeometry(200, 25, 50, 20)
        self.ui.sc_sell_labellll_02.setGeometry(10, 50, 200, 20)
        self.ui.sc_sell_checkBox_05.setGeometry(200, 50, 90, 20)
        self.ui.sc_sell_checkBox_06.setGeometry(290, 50, 90, 20)
        self.ui.sc_sell_checkBox_07.setGeometry(380, 50, 90, 20)
        self.ui.sc_sell_labellll_03.setGeometry(10, 75, 200, 20)
        self.ui.sc_sell_checkBox_08.setGeometry(200, 75, 90, 20)
        self.ui.sc_sell_checkBox_09.setGeometry(290, 75, 90, 20)
        self.ui.sc_sell_lineEdit_02.setGeometry(360, 75, 30, 20)
        self.ui.sc_sell_checkBox_10.setGeometry(400, 75, 90, 20)
        self.ui.sc_sell_lineEdit_03.setGeometry(470, 75, 30, 20)

        # 지정가 기준가격, 호가 범위
        self.ui.sc_sell_labellll_04.setGeometry(10, 25, 200, 20)
        self.ui.sc_sell_comboBox_01.setGeometry(175, 25, 80, 20)
        self.ui.sc_sell_comboBox_02.setGeometry(260, 25, 50, 20)
        self.ui.sc_sell_labellll_05.setGeometry(330, 25, 300, 20)
        self.ui.sc_sell_comboBox_03.setGeometry(550, 25, 50, 20)

        # 매도주문취소
        self.ui.sc_sell_checkBox_11.setGeometry(10, 25, 90, 20)
        self.ui.sc_sell_checkBox_12.setGeometry(100, 25, 90, 20)
        self.ui.sc_sell_checkBox_13.setGeometry(200, 25, 170, 20)
        self.ui.sc_sell_lineEdit_04.setGeometry(262, 25, 50, 20)

        # 매도금지
        self.ui.sc_sell_checkBox_14.setGeometry(10, 25, 310, 20)
        self.ui.sc_sell_lineEdit_05.setGeometry(110, 25, 80, 20)
        self.ui.sc_sell_checkBox_15.setGeometry(10, 50, 310, 20)
        self.ui.sc_sell_lineEdit_06.setGeometry(110, 50, 80, 20)
        self.ui.sc_sell_lineEdit_07.setGeometry(210, 50, 80, 20)
        self.ui.sc_sell_checkBox_16.setGeometry(10, 75, 310, 20)
        self.ui.sc_sell_lineEdit_08.setGeometry(110, 75, 80, 20)

        # 매도정정
        self.ui.sc_sell_labellll_06.setGeometry(10, 25, 310, 20)
        self.ui.sc_sell_lineEdit_09.setGeometry(210, 25, 50, 20)
        self.ui.sc_sell_labellll_07.setGeometry(10, 50, 310, 20)
        self.ui.sc_sell_comboBox_04.setGeometry(210, 50, 50, 20)
        self.ui.sc_sell_labellll_08.setGeometry(10, 75, 310, 20)
        self.ui.sc_sell_comboBox_05.setGeometry(210, 75, 50, 20)

        # 불러오기, 저장하기
        self.ui.sc_load_Button_02.setGeometry(8, 162, 150, 30)
        self.ui.sc_save_Button_02.setGeometry(163, 162, 150, 30)

        # 익절청산
        self.ui.sc_sell_checkBox_17.setGeometry(10, 25, 80, 20)
        self.ui.sc_sell_lineEdit_10.setGeometry(90, 25, 50, 20)
        self.ui.sc_sell_checkBox_18.setGeometry(160, 25, 80, 20)
        self.ui.sc_sell_lineEdit_11.setGeometry(240, 25, 80, 20)

        # 손절청산
        self.ui.sc_sell_checkBox_19.setGeometry(10, 25, 80, 20)
        self.ui.sc_sell_lineEdit_12.setGeometry(90, 25, 50, 20)
        self.ui.sc_sell_checkBox_20.setGeometry(160, 25, 80, 20)
        self.ui.sc_sell_lineEdit_13.setGeometry(240, 25, 80, 20)
