
from ui.event_activate import activated_etc
from ui.event_click.button_clicked_etc import *
from ui.event_click.button_clicked_order import *
from ui.event_click.button_clicked_database import *
from ui.event_click.button_clicked_passticks import *
from ui.event_change.changed_text import text_changed_05
from PyQt5.QtWidgets import QGroupBox, QLabel, QTabWidget, QWidget
from ui.event_keypress.overwrite_return_press import return_press_02
from ui.create_widget.set_style import style_ck_bx, style_bc_dk, qfont14, style_fc_dk
from ui.event_click.table_cell_clicked import cell_clicked_09, cell_clicked_07, cell_clicked_08
from utility.settings.setting_base import columns_hj, columns_hc, columns_hg, columns_gc, columns_ns, columns_jm1, \
    columns_jm2, columns_stg1, columns_stg2, columns_kp, columns_hc2


class SetDialogEtc:
    """기타 다이얼로그 설정 클래스입니다.
    호가, 정보, 데이터베이스, 주문 등 다양한 다이얼로그를 설정합니다.
    """
    def __init__(self, ui_class, wc):
        """기타 다이얼로그 설정을 초기화합니다.
        Args:
            ui_class: UI 클래스
            wc: 위젯 생성자
        """
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """기타 다이얼로그를 설정합니다."""
        self.ui.dialog_hoga = self.wc.setDialog('STOM HOGA')
        self.ui.dialog_hoga.geometry().center()

        self.ui.hj_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_hoga, columns_hj, 1)
        self.ui.hc_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_hoga, columns_hc, 12)
        self.ui.hc_tableWidgett_02 = self.wc.setTablewidget(self.ui.dialog_hoga, columns_hc2, 12, visible=False)
        self.ui.hg_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_hoga, columns_hg, 12, clicked=lambda row, col: cell_clicked_09(self.ui, row, col))
        self.ui.hg_lineeeeeeeee_01 = self.wc.setLine(self.ui.dialog_hoga, 1)
        self.ui.hg_labellllllll_01 = QLabel('', self.ui.dialog_hoga)
        self.ui.hg_pushButtonnn_01 = self.wc.setPushbutton('이전(Alt+left)', parent=self.ui.dialog_hoga, click=lambda: hg_button_clicked_01(self.ui, '이전'), shortcut='Alt+left')
        self.ui.hg_pushButtonnn_02 = self.wc.setPushbutton('다음(Alt+right)', parent=self.ui.dialog_hoga, click=lambda: hg_button_clicked_01(self.ui, '다음'), shortcut='Alt+right')
        self.ui.hg_pushButtonnn_03 = self.wc.setPushbutton('매수(Alt+up)', parent=self.ui.dialog_hoga, color=2, click=lambda: hg_button_clicked_02(self.ui, '매수'), shortcut='Alt+up')
        self.ui.hg_pushButtonnn_04 = self.wc.setPushbutton('매도(Alt+down)', parent=self.ui.dialog_hoga, color=3, click=lambda: hg_button_clicked_02(self.ui, '매도'), shortcut='Alt+down')

        self.ui.dialog_info = self.wc.setDialog('STOM INFO')
        self.ui.dialog_info.geometry().center()

        self.ui.gg_textEdittttt_01 = self.wc.setTextEdit(self.ui.dialog_info, font=qfont14)
        self.ui.gs_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_info, columns_gc, 20, clicked=lambda row, col: cell_clicked_07(self.ui, row, col))
        self.ui.ns_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_info, columns_ns, 10, clicked=lambda row, col: cell_clicked_07(self.ui, row, col))
        self.ui.jm_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_info, columns_jm1, 13)
        self.ui.jm_tableWidgett_02 = self.wc.setTablewidget(self.ui.dialog_info, columns_jm2, 13)

        self.ui.dialog_web = self.wc.setDialog('STOM WEB')
        self.ui.dialog_web.geometry().center()

        self.ui.dialog_tree = self.wc.setDialog('STOM TREEMAP')
        self.ui.dialog_tree.geometry().center()

        self.ui.dialog_graph = self.wc.setDialog('STOM GRAPH')
        self.ui.dialog_graph.geometry().center()

        self.ui.dialog_db = self.wc.setDialog('STOM DATABASE')
        self.ui.dialog_db.geometry().center()

        self.ui.dbs_tapWidgettt_01 = QTabWidget(self.ui.dialog_db)
        self.ui.dbs_tab1 = QWidget()
        self.ui.dbs_tab2 = QWidget()
        self.ui.dbs_tab3 = QWidget()
        self.ui.dbs_tapWidgettt_01.addTab(self.ui.dbs_tab1, '매수/매도전략')
        self.ui.dbs_tapWidgettt_01.addTab(self.ui.dbs_tab2, '최적화및GA범위')
        self.ui.dbs_tapWidgettt_01.addTab(self.ui.dbs_tab3, '백테스트스케쥴')

        self.ui.db_labellllllll_00 = QLabel('셀클릭 시 데이터 삭제', self.ui.dialog_db)
        self.ui.db_groupBoxxxxx_01 = QGroupBox('', self.ui.dialog_db)

        self.ui.db_labellllllll_18 = QLabel('백테DB의 지정일자 데이터 삭제하기 (일자입력 예: 20220131)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_lineEdittttt_16 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_pushButtonnn_18 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_01(self.ui))
        self.ui.db_labellllllll_01 = QLabel('일자DB의 지정일자 데이터 삭제하기 (일자입력)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_lineEdittttt_01 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_pushButtonnn_01 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_02(self.ui))
        self.ui.db_labellllllll_02 = QLabel('일자DB의 지정시간이후 데이터 삭제하기 (시간입력 예: 93000)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_lineEdittttt_02 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_pushButtonnn_02 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_03(self.ui))
        self.ui.db_labellllllll_03 = QLabel('당일DB의 지정시간이후 데이터 삭제하기 (시간입력)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_lineEdittttt_03 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_pushButtonnn_03 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_04(self.ui))
        self.ui.db_labellllllll_04 = QLabel('당일DB의 연초개장일 및 수능일 시간 조정 (일자 입력)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_lineEdittttt_04 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_pushButtonnn_04 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_05(self.ui))
        self.ui.db_labellllllll_05 = QLabel('일자DB로 백테DB 생성하기 (일자 입력)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_lineEdittttt_05 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_lineEdittttt_06 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_pushButtonnn_05 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_06(self.ui))
        self.ui.db_labellllllll_06 = QLabel('백테DB에 일자DB의 데이터 추가하기', self.ui.db_groupBoxxxxx_01)
        self.ui.db_lineEdittttt_07 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_lineEdittttt_08 = self.wc.setLineedit(self.ui.db_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.db_pushButtonnn_06 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_07(self.ui))
        self.ui.db_labellllllll_07 = QLabel('백테DB에 당일DB의 데이터 추가하기 (추가 후 당일DB는 삭제됨)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_pushButtonnn_07 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_08(self.ui))
        self.ui.db_labellllllll_08 = QLabel('당일DB를 일자DB로 분리하기', self.ui.db_groupBoxxxxx_01)
        self.ui.db_pushButtonnn_08 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_09(self.ui))
        self.ui.db_labellllllll_09 = QLabel('거래기록 테이블 모두 삭제 (체결목록, 잔고목록, 거래목록, 일별실현손익)', self.ui.db_groupBoxxxxx_01)
        self.ui.db_pushButtonnn_09 = self.wc.setPushbutton('실행', parent=self.ui.db_groupBoxxxxx_01, click=lambda: dbbutton_clicked_10(self.ui))

        self.ui.db_tableWidgett_01 = self.wc.setTablewidget(self.ui.dbs_tab1, columns_stg1, 8,    clicked=lambda row, col: cell_clicked_08(self.ui, row, col))
        self.ui.db_tableWidgett_02 = self.wc.setTablewidget(self.ui.dbs_tab2, columns_stg2, 8,    clicked=lambda row, col: cell_clicked_08(self.ui, row, col))
        self.ui.db_tableWidgett_03 = self.wc.setTablewidget(self.ui.dbs_tab3, ['백테스트 스케쥴'], 8, clicked=lambda row, col: cell_clicked_08(self.ui, row, col))
        self.ui.db_textEdittttt_01 = self.wc.setTextEdit(self.ui.dialog_db, vscroll=True)

        self.ui.dialog_order = self.wc.setDialog('STOM ORDER')
        self.ui.dialog_order.geometry().center()

        self.ui.od_groupBoxxxxx_01 = QGroupBox('', self.ui.dialog_order)
        self.ui.od_labellllllll_01 = QLabel('주문종목명', self.ui.od_groupBoxxxxx_01)
        self.ui.od_comboBoxxxxx_01 = self.wc.setCombobox(self.ui.od_groupBoxxxxx_01, hover=False, activated=lambda: activated_etc.dactivated_03(self.ui))
        self.ui.od_labellllllll_02 = QLabel('주문유형', self.ui.od_groupBoxxxxx_01)
        self.ui.od_comboBoxxxxx_02 = self.wc.setCombobox(self.ui.od_groupBoxxxxx_01, hover=False, items=['시장가', '지정가', '최유리지정가', '최우선지정가', '지정가IOC', '시장가IOC', '최유리IOC', '지정가FOK', '시장가FOK', '최유리FOK'])
        self.ui.od_labellllllll_03 = QLabel('주문가격', self.ui.od_groupBoxxxxx_01)
        self.ui.od_lineEdittttt_01 = self.wc.setLineedit(self.ui.od_groupBoxxxxx_01, style=style_bc_dk, enter=lambda: text_changed_05(self.ui))
        self.ui.od_labellllllll_04 = QLabel('주문수량', self.ui.od_groupBoxxxxx_01)
        self.ui.od_lineEdittttt_02 = self.wc.setLineedit(self.ui.od_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.od_pushButtonnn_01 = self.wc.setPushbutton('매수', parent=self.ui.od_groupBoxxxxx_01, color=2, click=lambda: odbutton_clicked_01(self.ui))
        self.ui.od_pushButtonnn_02 = self.wc.setPushbutton('매도', parent=self.ui.od_groupBoxxxxx_01, color=3, click=lambda: odbutton_clicked_02(self.ui))
        self.ui.od_pushButtonnn_03 = self.wc.setPushbutton('BUY_LONG', parent=self.ui.od_groupBoxxxxx_01, color=2, click=lambda: odbutton_clicked_03(self.ui))
        self.ui.od_pushButtonnn_04 = self.wc.setPushbutton('SELL_LONG', parent=self.ui.od_groupBoxxxxx_01, color=3, click=lambda: odbutton_clicked_04(self.ui))
        self.ui.od_pushButtonnn_05 = self.wc.setPushbutton('SELL_SHORT', parent=self.ui.od_groupBoxxxxx_01, color=2, click=lambda: odbutton_clicked_05(self.ui))
        self.ui.od_pushButtonnn_06 = self.wc.setPushbutton('BUY_SHORT', parent=self.ui.od_groupBoxxxxx_01, color=3, click=lambda: odbutton_clicked_06(self.ui))
        self.ui.od_pushButtonnn_07 = self.wc.setPushbutton('매수취소', parent=self.ui.od_groupBoxxxxx_01, click=lambda: odbutton_clicked_07(self.ui))
        self.ui.od_pushButtonnn_08 = self.wc.setPushbutton('매도취소', parent=self.ui.od_groupBoxxxxx_01, click=lambda: odbutton_clicked_08(self.ui))

        self.ui.dialog_optuna = self.wc.setDialog('STOM OPTUNA', parent=self.ui)
        self.ui.dialog_optuna.geometry().center()
        self.ui.op_groupBoxxxx_01 = QGroupBox(' ', self.ui.dialog_optuna)
        text = '''
        "optuna의 범위설정은 최적화 범위
        설정과 동일합니다. 그대로 사용해도
        되지만, 일부 아는 중요한 값들은
        고정하여 사용하면 초기에 보다
        빠르게 최적값을 탐색할 수 있습니다.
        아래의 빈칸에 콤머로 구분하여
        고정할 변수의 번호를 입력하십시오."
        '''
        self.ui.op_labelllllll_01 = QLabel(text, self.ui.op_groupBoxxxx_01)
        self.ui.op_labelllllll_01.setAlignment(Qt.AlignCenter)
        self.ui.op_lineEditttt_01 = self.wc.setLineedit(self.ui.op_groupBoxxxx_01, style=style_bc_dk)
        text = '''
        "optuna은 기본적으로 범위설정에서
        입력한 간격대로 변수를 탐색합니다.
        하지만 범위설정의 간격을 무시하고
        optuna가 최소, 최대의 범위안에서
        자동으로 탐색하게 할 수 있습니다.
        원하시면 아래의 설정을 사용하십시오."
        '''
        self.ui.op_labelllllll_02 = QLabel(text, self.ui.op_groupBoxxxx_01)
        self.ui.op_labelllllll_02.setAlignment(Qt.AlignCenter)
        self.ui.op_checkBoxxxx_01 = self.wc.setCheckBox('범위간격 자동탐색 사용하기', self.ui.op_groupBoxxxx_01, checked=False, style=style_ck_bx)
        text = '''
        "optuna의 기본 최적화 알고리즘은
        베이지안서치(TPESampler)입니다.
        아래 콤보박스에서 다른 최적화
        알고리즘을 선택할 수 있습니다."
        '''
        self.ui.op_labelllllll_03 = QLabel(text, self.ui.op_groupBoxxxx_01)
        self.ui.op_labelllllll_03.setAlignment(Qt.AlignCenter)
        item_list = ['TPESampler', 'BruteForceSampler', 'CmaEsSampler', 'QMCSampler', 'RandomSampler']
        self.ui.op_comboBoxxxx_01 = self.wc.setCombobox(self.ui.op_groupBoxxxx_01, items=item_list)
        text = '''
        "optuna의 실행 횟수는 변수의
        개수만큼 실행되어도 기준값이
        변경되지 않으면 탐색을 종료하도록
        설정되어 있습니다(0입력시적용).
        설정을 무시하고 기준값 미변경 시
        중단할 횟수를 빈칸에 입력하십시오.
        20회 이하의 횟수로 최적값을 빠르게
        랜덤하게 바꿀 수도 있으며
        200회 이상의 횟수로 고강도 탐색을
        유도할 수도 있습니다."
        '''
        self.ui.op_labelllllll_04 = QLabel(text, self.ui.op_groupBoxxxx_01)
        self.ui.op_labelllllll_04.setAlignment(Qt.AlignCenter)
        self.ui.op_lineEditttt_02 = self.wc.setLineedit(self.ui.op_groupBoxxxx_01, style=style_bc_dk)
        self.ui.op_lineEditttt_02.setText('0')
        text = '''
        "optuna로 실행된 최적화의 정보는
        별도의 데이터베이스에 저장됩니다
        해당 DB의 정보를 열람하려면
        아래 버튼을 클릭하십시오."
        '''
        self.ui.op_labelllllll_05 = QLabel(text, self.ui.op_groupBoxxxx_01)
        self.ui.op_labelllllll_05.setAlignment(Qt.AlignCenter)
        self.ui.op_pushButtonn_01 = self.wc.setPushbutton('OPTUNA DASHBOARD', parent=self.ui.op_groupBoxxxx_01, color=3, click=lambda: opbutton_clicked_01(self.ui))

        self.ui.dialog_pass = self.wc.setDialog('STOM PASSWARD', parent=self.ui)
        self.ui.dialog_pass.geometry().center()
        self.ui.pa_groupBoxxxx_01 = QGroupBox(' ', self.ui.dialog_pass)
        self.ui.pa_labelllllll_01 = QLabel('프로그램 비밀번호을 입력하십시오.\n미설정 시 입력없이 엔터!!\n', self.ui.pa_groupBoxxxx_01)
        self.ui.pa_labelllllll_01.setAlignment(Qt.AlignCenter)
        self.ui.pa_lineEditttt_01 = self.wc.setLineedit(self.ui.pa_groupBoxxxx_01, enter=lambda: return_press_02(self.ui), style=style_fc_dk)

        self.ui.dialog_comp = self.wc.setDialog('STOM COMPARISON', parent=self.ui)
        self.ui.dialog_comp.geometry().center()
        self.ui.cp_labelllllll_01 = QLabel('▣ 선택된 두개 이상의 그래프를 비교한다.', self.ui.dialog_comp)
        self.ui.cp_pushButtonn_01 = self.wc.setPushbutton('그래프 비교', parent=self.ui.dialog_comp, click=lambda: cpbutton_clicked_01(self.ui))
        self.ui.cp_tableWidget_01 = self.wc.setTablewidget(self.ui.dialog_comp, ['백테스트 상세기록'], 40, vscroll=True)

        self.ui.dialog_kimp = self.wc.setDialog('STOM KIMP')
        self.ui.dialog_kimp.geometry().center()
        self.ui.kp_tableWidget_01 = self.wc.setTablewidget(self.ui.dialog_kimp, columns_kp, 50, vscroll=True)

        self.ui.dialog_std = self.wc.setDialog('OPTIMIZ STD LIMIT', parent=self.ui)
        self.ui.dialog_std.geometry().center()
        self.ui.st_pushButtonn_01 = self.wc.setPushbutton('불러오기', parent=self.ui.dialog_std, click=lambda: stbutton_clicked_01(self.ui))
        self.ui.st_pushButtonn_02 = self.wc.setPushbutton('저장하기', parent=self.ui.dialog_std, click=lambda: stbutton_clicked_02(self.ui))
        self.ui.st_groupBoxxxx_01 = QGroupBox(' ', self.ui.dialog_std)
        self.ui.st_labelllllll_01 = QLabel('<=    최대낙폭률     <=', self.ui.st_groupBoxxxx_01)
        self.ui.st_labelllllll_02 = QLabel('<=    보유종목수     <=', self.ui.st_groupBoxxxx_01)
        self.ui.st_labelllllll_03 = QLabel('<=          승률          <=', self.ui.st_groupBoxxxx_01)
        self.ui.st_labelllllll_04 = QLabel('<=    평균수익률     <=', self.ui.st_groupBoxxxx_01)
        self.ui.st_labelllllll_05 = QLabel('<= 일평균거래횟수 <=', self.ui.st_groupBoxxxx_01)
        self.ui.st_labelllllll_06 = QLabel('<= 연간예상수익률 <=', self.ui.st_groupBoxxxx_01)
        self.ui.st_labelllllll_07 = QLabel('<=   매매성능지수   <=', self.ui.st_groupBoxxxx_01)
        for i in range(14):
            lineEdit = self.wc.setLineedit(self.ui.st_groupBoxxxx_01, style=style_bc_dk)
            setattr(self.ui, f'st_lineEditttt_{i+1:02d}', lineEdit)

        self.ui.dialog_leverage = self.wc.setDialog('BINACE FUTURE LEVERAGE', parent=self.ui)
        self.ui.dialog_leverage.geometry().center()
        self.ui.lv_pushButtonn_01 = self.wc.setPushbutton('불러오기', parent=self.ui.dialog_leverage, click=lambda: lvbutton_clicked_02(self.ui))
        self.ui.lv_pushButtonn_02 = self.wc.setPushbutton('저장하기', parent=self.ui.dialog_leverage, click=lambda: lvbutton_clicked_03(self.ui))
        self.ui.lv_groupBoxxxx_01 = QGroupBox(' ', self.ui.dialog_leverage)
        self.ui.lv_checkBoxxxx_01 = self.wc.setCheckBox('고정 레버리지 (모든 종목의 레버리지 고정)', self.ui.lv_groupBoxxxx_01, style=style_ck_bx, changed=lambda state: lvcheck_changed_01(self.ui, state))
        self.ui.lv_lineEditttt_01 = self.wc.setLineedit(self.ui.lv_groupBoxxxx_01, style=style_bc_dk)
        self.ui.lv_groupBoxxxx_02 = QGroupBox(' ', self.ui.dialog_leverage)
        self.ui.lv_checkBoxxxx_02 = self.wc.setCheckBox('변동 레버리지 (변동에 따라 레버리지 변경)        [1~125]', self.ui.lv_groupBoxxxx_02, style=style_ck_bx, changed=lambda state: lvcheck_changed_01(self.ui, state))
        self.ui.lv_labelllllll_01 = QLabel('<= 저가대비고가등락율  <', self.ui.lv_groupBoxxxx_02)
        self.ui.lv_labelllllll_02 = QLabel('<= 저가대비고가등락율  <', self.ui.lv_groupBoxxxx_02)
        self.ui.lv_labelllllll_03 = QLabel('<= 저가대비고가등락율  <', self.ui.lv_groupBoxxxx_02)
        self.ui.lv_labelllllll_04 = QLabel('<= 저가대비고가등락율  <', self.ui.lv_groupBoxxxx_02)
        self.ui.lv_labelllllll_05 = QLabel('<= 저가대비고가등락율  <', self.ui.lv_groupBoxxxx_02)
        for i in range(15):
            lineEdit = self.wc.setLineedit(self.ui.lv_groupBoxxxx_02, style=style_bc_dk)
            setattr(self.ui, f'lv_lineEditttt_{i+2:02d}', lineEdit)

        self.ui.lv_checkbox_listt = [self.ui.lv_checkBoxxxx_01, self.ui.lv_checkBoxxxx_02]

        self.ui.dialog_setsj = self.wc.setDialog('STOM SETSJ', parent=self.ui)
        self.ui.dialog_setsj.geometry().center()
        self.ui.set_pushButton_01 = self.wc.setPushbutton('설정예제', parent=self.ui.dialog_setsj, click=lambda: setting_passticks_sample(self.ui))
        self.ui.set_pushButton_02 = self.wc.setPushbutton('불러오기', parent=self.ui.dialog_setsj, click=lambda: setting_passticks_load(self.ui))
        self.ui.set_pushButton_03 = self.wc.setPushbutton('저장하기', parent=self.ui.dialog_setsj, click=lambda: setting_passticks_save(self.ui))
        self.ui.set_groupBoxxx_01 = QGroupBox('', self.ui.dialog_setsj)
        text = '''
        ▣ 백테 및 전략연산에서 사용할 경과틱수('조건명')을 설정한다. 경과틱수는 작성한 조건을 만족한 이후 경과한 틱수이며
        경과틱수 괄호안에 조건명을 넣어서 사용합니다. 조건은 전략탭에서 사용하는 전략(매도팩터제외)과 문법이 동일합니다.
        예제에서 사용한 조건명 이평60데드는 경과틱수('이평60데드') 형태로 사용합니다. 반드시 조건명에 따옴표를 붙여야합니다.'''
        self.ui.set_labellllll_01 = QLabel(text, self.ui.set_groupBoxxx_01)
        self.ui.set_labellllll_02 = QLabel('            조건명                        조건', self.ui.set_groupBoxxx_01)
        for i in range(20):
            lineEdit = self.wc.setLineedit(self.ui.set_groupBoxxx_01, aleft=True, style=style_bc_dk)
            setattr(self.ui, f'set_lineEdittt_{i+1:02d}', lineEdit)

        self.ui.scn_lineedit_list = [
            self.ui.set_lineEdittt_01, self.ui.set_lineEdittt_02, self.ui.set_lineEdittt_03, self.ui.set_lineEdittt_04,
            self.ui.set_lineEdittt_05, self.ui.set_lineEdittt_06, self.ui.set_lineEdittt_07, self.ui.set_lineEdittt_08,
            self.ui.set_lineEdittt_09, self.ui.set_lineEdittt_10
        ]

        self.ui.scc_lineedit_list = [
            self.ui.set_lineEdittt_11, self.ui.set_lineEdittt_12, self.ui.set_lineEdittt_13, self.ui.set_lineEdittt_14,
            self.ui.set_lineEdittt_15, self.ui.set_lineEdittt_16, self.ui.set_lineEdittt_17, self.ui.set_lineEdittt_18,
            self.ui.set_lineEdittt_19, self.ui.set_lineEdittt_20
        ]

        self.ui.dialog_hoga.setFixedSize(572, 355)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_hoga.move(self.ui.dict_set['창위치'][14], self.ui.dict_set['창위치'][15])
            except Exception:
                pass
        self.ui.hj_tableWidgett_01.setGeometry(5, 5, 562, 42)
        self.ui.hc_tableWidgett_01.setGeometry(5, 52, 282, 297)
        self.ui.hc_tableWidgett_02.setGeometry(285, 52, 282, 297)
        self.ui.hg_tableWidgett_01.setGeometry(285, 52, 282, 297)
        self.ui.hg_lineeeeeeeee_01.setGeometry(5, 209, 842, 1)
        self.ui.hg_labellllllll_01.setGeometry(10, 354, 130, 30)
        self.ui.hg_pushButtonnn_01.setGeometry(290, 354, 130, 30)
        self.ui.hg_pushButtonnn_02.setGeometry(430, 354, 130, 30)
        self.ui.hg_pushButtonnn_03.setGeometry(570, 354, 130, 30)
        self.ui.hg_pushButtonnn_04.setGeometry(710, 354, 130, 30)

        self.ui.dialog_info.setFixedSize(1403, 570)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_info.move(self.ui.dict_set['창위치'][6], self.ui.dict_set['창위치'][7])
            except Exception:
                pass
        self.ui.gg_textEdittttt_01.setGeometry(7, 5, 692, 90)
        self.ui.gs_tableWidgett_01.setGeometry(7, 100, 692, 463)
        self.ui.ns_tableWidgett_01.setGeometry(704, 5, 693, 233)
        self.ui.jm_tableWidgett_01.setGeometry(704, 243, 320, 320)
        self.ui.jm_tableWidgett_02.setGeometry(1024, 243, 373, 320)

        self.ui.dialog_web.resize(1000, 1000)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_web.move(self.ui.dict_set['창위치'][8], self.ui.dict_set['창위치'][9])
            except Exception:
                pass

        self.ui.dialog_tree.resize(1000, 1000)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_tree.move(self.ui.dict_set['창위치'][10], self.ui.dict_set['창위치'][11])
            except Exception:
                pass

        self.ui.dialog_graph.setFixedSize(1403, 1010)

        self.ui.dialog_db.setFixedSize(525, 670)
        self.ui.db_groupBoxxxxx_01.setGeometry(5, 5, 515, 260)
        self.ui.dbs_tapWidgettt_01.setGeometry(5, 270, 515, 250)
        self.ui.db_labellllllll_00.setGeometry(405, 270, 110, 20)
        self.ui.db_textEdittttt_01.setGeometry(5, 525, 515, 140)

        self.ui.db_labellllllll_18.setGeometry(10, 10, 320, 20)
        self.ui.db_lineEdittttt_16.setGeometry(345, 10, 80, 20)
        self.ui.db_pushButtonnn_18.setGeometry(430, 10, 80, 20)
        self.ui.db_labellllllll_01.setGeometry(10, 35, 320, 20)
        self.ui.db_lineEdittttt_01.setGeometry(345, 35, 80, 20)
        self.ui.db_pushButtonnn_01.setGeometry(430, 35, 80, 20)
        self.ui.db_labellllllll_02.setGeometry(10, 60, 320, 20)
        self.ui.db_lineEdittttt_02.setGeometry(345, 60, 80, 20)
        self.ui.db_pushButtonnn_02.setGeometry(430, 60, 80, 20)
        self.ui.db_labellllllll_03.setGeometry(10, 85, 300, 20)
        self.ui.db_lineEdittttt_03.setGeometry(345, 85, 80, 20)
        self.ui.db_pushButtonnn_03.setGeometry(430, 85, 80, 20)
        self.ui.db_labellllllll_04.setGeometry(10, 110, 300, 20)
        self.ui.db_lineEdittttt_04.setGeometry(345, 110, 80, 20)
        self.ui.db_pushButtonnn_04.setGeometry(430, 110, 80, 20)
        self.ui.db_labellllllll_05.setGeometry(10, 135, 300, 20)
        self.ui.db_lineEdittttt_05.setGeometry(260, 135, 80, 20)
        self.ui.db_lineEdittttt_06.setGeometry(345, 135, 80, 20)
        self.ui.db_pushButtonnn_05.setGeometry(430, 135, 80, 20)
        self.ui.db_labellllllll_06.setGeometry(10, 160, 300, 20)
        self.ui.db_lineEdittttt_07.setGeometry(260, 160, 80, 20)
        self.ui.db_lineEdittttt_08.setGeometry(345, 160, 80, 20)
        self.ui.db_pushButtonnn_06.setGeometry(430, 160, 80, 20)
        self.ui.db_labellllllll_07.setGeometry(10, 185, 400, 20)
        self.ui.db_pushButtonnn_07.setGeometry(430, 185, 80, 20)
        self.ui.db_labellllllll_08.setGeometry(10, 210, 400, 20)
        self.ui.db_pushButtonnn_08.setGeometry(430, 210, 80, 20)
        self.ui.db_labellllllll_09.setGeometry(10, 235, 400, 20)
        self.ui.db_pushButtonnn_09.setGeometry(430, 235, 80, 20)

        self.ui.db_tableWidgett_01.setGeometry(5, 5, 500, 210)
        self.ui.db_tableWidgett_02.setGeometry(5, 5, 500, 210)
        self.ui.db_tableWidgett_03.setGeometry(5, 5, 500, 210)

        self.ui.dialog_order.setFixedSize(232, 303)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_order.move(self.ui.dict_set['창위치'][18], self.ui.dict_set['창위치'][19])
            except Exception:
                pass
        self.ui.od_groupBoxxxxx_01.setGeometry(5, 5, 222, 293)
        self.ui.od_labellllllll_01.setGeometry(10, 10, 100, 30)
        self.ui.od_comboBoxxxxx_01.setGeometry(115, 10, 100, 30)
        self.ui.od_labellllllll_02.setGeometry(10, 45, 100, 30)
        self.ui.od_comboBoxxxxx_02.setGeometry(115, 45, 100, 30)
        self.ui.od_labellllllll_03.setGeometry(10, 80, 100, 30)
        self.ui.od_lineEdittttt_01.setGeometry(115, 80, 100, 30)
        self.ui.od_labellllllll_04.setGeometry(10, 115, 100, 30)
        self.ui.od_lineEdittttt_02.setGeometry(115, 115, 100, 30)

        for i in range(8):
            x = 10 if i % 2 == 0 else 115
            y = 150 + i // 2 * 35
            getattr(self.ui, f'od_pushButtonnn_{i+1:02d}').setGeometry(x, y, 100, 30)

        self.ui.dialog_optuna.setFixedSize(220, 670)
        self.ui.op_groupBoxxxx_01.setGeometry(5, -10, 210, 675)
        self.ui.op_labelllllll_01.setGeometry(-10, 10, 210, 130)
        self.ui.op_lineEditttt_01.setGeometry(10, 132, 190, 30)
        self.ui.op_labelllllll_02.setGeometry(-10, 160, 210, 100)
        self.ui.op_checkBoxxxx_01.setGeometry(25, 265, 190, 20)
        self.ui.op_labelllllll_03.setGeometry(-10, 277, 210, 70)
        self.ui.op_comboBoxxxx_01.setGeometry(10, 355, 190, 30)
        self.ui.op_labelllllll_04.setGeometry(-10, 382, 210, 155)
        self.ui.op_lineEditttt_02.setGeometry(10, 537, 190, 30)
        self.ui.op_labelllllll_05.setGeometry(-10, 560, 200, 70)
        self.ui.op_pushButtonn_01.setGeometry(10, 637, 190, 30)

        self.ui.dialog_pass.setFixedSize(200, 100)
        self.ui.pa_groupBoxxxx_01.setGeometry(5, -10, 190, 105)
        self.ui.pa_labelllllll_01.setGeometry(5, 25, 190, 60)
        self.ui.pa_lineEditttt_01.setGeometry(50, 75, 100, 25)

        self.ui.dialog_comp.setFixedSize(350, 763)
        self.ui.cp_labelllllll_01.setGeometry(10, 10, 220, 25)
        self.ui.cp_pushButtonn_01.setGeometry(240, 10, 103, 25)
        self.ui.cp_tableWidget_01.setGeometry(5, 40, 340, 718)

        self.ui.dialog_kimp.setFixedSize(535, 763)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_kimp.move(self.ui.dict_set['창위치'][12], self.ui.dict_set['창위치'][13])
            except Exception:
                pass
        self.ui.kp_tableWidget_01.setGeometry(5, 5, 525, 753)

        self.ui.dialog_std.setFixedSize(255, 260)
        self.ui.st_pushButtonn_01.setGeometry(5, 5, 120, 25)
        self.ui.st_pushButtonn_02.setGeometry(130, 5, 120, 25)
        self.ui.st_groupBoxxxx_01.setGeometry(5, 20, 245, 235)

        for i in range(7):
            y = 25 + i * 30
            getattr(self.ui, f'st_labelllllll_{i+1:02d}').setGeometry(68, y, 120, 25)

        for i in range(14):
            x = 10 if i % 2 == 0 else 187
            y = 25 + i // 2 * 30
            getattr(self.ui, f'st_lineEditttt_{i+1:02d}').setGeometry(x, y, 50, 25)

        self.ui.dialog_leverage.setFixedSize(330, 280)
        self.ui.lv_pushButtonn_01.setGeometry(5, 5, 157, 30)
        self.ui.lv_pushButtonn_02.setGeometry(167, 5, 157, 30)
        self.ui.lv_groupBoxxxx_01.setGeometry(5, 25, 320, 57)
        self.ui.lv_checkBoxxxx_01.setGeometry(10, 25, 300, 25)
        self.ui.lv_lineEditttt_01.setGeometry(263, 25, 50, 25)
        self.ui.lv_groupBoxxxx_02.setGeometry(5, 70, 320, 205)
        self.ui.lv_checkBoxxxx_02.setGeometry(10, 25, 300, 25)

        for i in range(5):
            y = 55 + i * 30
            getattr(self.ui, f'lv_labelllllll_{i+1:02d}').setGeometry(65, y, 140, 25)

        for i in range(15):
            x = 10 if i % 3 == 0 else 205 if i % 3 == 1 else 263
            y = 55 + i // 3 * 30
            getattr(self.ui, f'lv_lineEditttt_{i+2:02d}').setGeometry(x, y, 50, 25)

        self.ui.dialog_setsj.setFixedSize(800, 435)
        self.ui.set_pushButton_01.setGeometry(5, 5, 100, 25)
        self.ui.set_pushButton_02.setGeometry(590, 5, 100, 25)
        self.ui.set_pushButton_03.setGeometry(695, 5, 100, 25)
        self.ui.set_groupBoxxx_01.setGeometry(5, 30, 790, 400)
        self.ui.set_labellllll_01.setGeometry(0, 5, 790, 60)
        self.ui.set_labellllll_02.setGeometry(0, 70, 790, 25)

        for i in range(20):
            x = 5 if i < 10 else 110
            y = 100 + i % 10 * 30
            xw = 100 if i < 10 else 675
            getattr(self.ui, f'set_lineEdittt_{i+1:02d}').setGeometry(x, y, xw, 25)
