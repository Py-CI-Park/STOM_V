import zmq
import socket
import subprocess
from PyQt5.QtWidgets import QCompleter
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QThread

from ui.set_icon import SetIcon
from ui.set_table import SetTable
from ui.set_log_tap import SetLogTap
from ui.set_stg_coin_tap import SetCoinBack
from ui.set_stg_stock_tap import SetStockBack
from ui.set_widget import WidgetCreater
from ui.set_setup_tap import SetSetupTap
from ui.set_order_tap import SetOrderTap
from ui.set_main_menu import SetMainMenu
from ui.set_dialog_etc import SetDialogEtc
from ui.set_dialog_back import SetDialogBack
from ui.set_dialog_chart import SetDialogChart

from ui.ui_etc import *
from ui.ui_draw_chart import *
from ui.ui_activated_back import *
from ui.ui_activated_coin_stg import *
from ui.ui_activated_stock_stg import *
from ui.ui_show_dialog import *
from ui.ui_vars_change import *
from ui.ui_draw_treemap import *
from ui.ui_cell_clicked import *
from ui.ui_text_changed import *
from ui.ui_process_kill import *
from ui.ui_return_press import *
from ui.ui_event_filter import *
from ui.ui_activated_etc import *
from ui.ui_process_alive import *
from ui.ui_extend_window import *
from ui.ui_draw_realchart import *
from ui.ui_draw_jisuchart import *
from ui.ui_betting_cotrol import *
from ui.ui_update_textedit import *
from ui.ui_process_starter import *
from ui.ui_backtest_engine import *
from ui.ui_key_press_event import *
from ui.ui_checkbox_changed import *
from ui.ui_button_clicked_dialog_database import *
from ui.ui_button_clicked_order import *
from ui.ui_button_clicked_settings import *
from ui.ui_button_clicked_chart import *
from ui.ui_button_clicked_shortcut import *
from ui.ui_button_clicked_dialog_backengine import *
from ui.ui_button_clicked_dialog_elapsed_tick_number import *
from ui.ui_button_clicked_editer_backlog import *
from ui.ui_button_clicked_editer_coin import *
from ui.ui_button_clicked_editer_ga_coin import *
from ui.ui_button_clicked_editer_ga_stock import *
from ui.ui_button_clicked_editer_opti_coin import *
from ui.ui_button_clicked_editer_opti_stock import *
from ui.ui_button_clicked_editer_stg_buy_coin import *
from ui.ui_button_clicked_editer_stg_buy_stock import *
from ui.ui_button_clicked_editer_stg_sell_coin import *
from ui.ui_button_clicked_editer_stg_sell_stock import *
from ui.ui_button_clicked_editer_stock import *
from ui.ui_update_tablewidget import *
from ui.ui_update_progressbar import *
from ui.ui_button_clicked_etc import *
from ui.ui_chart_count_change import *
from ui.ui_button_clicked_zoom import *

from utility.hoga import *
from utility.chart import *
from utility.sound import *
from utility.query import *
from utility.static import *
from utility.setting import *
from utility.webcrawling import *
from utility.telegram_msg import *
from utility.database_read_only import DatabaseReadOnly
from ui.set_dialog_strategy import SetDialogStrategy
from ui.set_text_stg_button import *
from ui.ui_button_clicked_strategy import *


class LiveSender(Thread):
    def __init__(self, sock, liveQ):
        super().__init__()
        self.sock  = sock
        self.liveQ = liveQ

    def run(self):
        # STOM Live disabled
        pass


class LiveClient:
    def __init__(self, _qlist):
        self.windowQ = _qlist[0]
        self.liveQ   = _qlist[11]
        self.sock    = None
        # STOM Live disabled - do not call Start()
        # self.Start()

    def Start(self):
        # STOM Live disabled
        pass

    def UpdateStomLiveData(self, data):
        # STOM Live disabled
        pass

    @staticmethod
    def tatal_text_conv(i, t):
        try:
            if i == 0:
                return t
            elif i == 5:
                return float(t)
            else:
                return int(float(t))
        except:
            return 0

    @staticmethod
    def back_text_conv(i, t):
        try:
            if i in (0, 1):
                return str(t)
            elif i in (2, 3, 4, 5, 6, 7, 8, 10, 11, 16):
                return int(float(t))
            else:
                return float(t)
        except:
            return 0


class Writer(QThread):
    signal1  = pyqtSignal(tuple)
    signal2  = pyqtSignal(tuple)
    signal3  = pyqtSignal(tuple)
    signal4  = pyqtSignal(tuple)
    signal5  = pyqtSignal(tuple)
    signal6  = pyqtSignal(tuple)
    signal7  = pyqtSignal(tuple)
    signal8  = pyqtSignal(tuple)
    signal9  = pyqtSignal(str)
    signal10 = pyqtSignal()

    def __init__(self, _windowQ):
        super().__init__()
        self.windowQ = _windowQ
        self.df_list = [None, None, None, None, None, None, None, None]
        self.test    = None

    def run(self):
        gsjm_count = 0
        while True:
            try:
                data = self.windowQ.get()
                if type(data[0]) != str:
                    if data[0] <= ui_num['DB관리'] or data[0] == ui_num['기업개요']:
                        self.signal1.emit(data)
                    elif ui_num['S실현손익'] <= data[0] <= ui_num['C상세기록']:
                        if data[0] == ui_num['S관심종목']:
                            if not self.test:
                                index = data[1]
                                self.df_list[index] = data[2]
                                gsjm_count += 1
                                if gsjm_count == 8:
                                    gsjm_count = 0
                                    df_list = [x for x in self.df_list if x is not None]
                                    # noinspection PyTypeChecker
                                    df = pd.concat(df_list)
                                    df.sort_values(by=['d_money'], ascending=False, inplace=True)
                                    self.signal2.emit((ui_num['S관심종목'], df))
                            else:
                                self.signal2.emit((ui_num['S관심종목'], data[2]))
                        else:
                            self.signal2.emit(data)
                    elif data[0] == ui_num['차트']:
                        self.signal3.emit(data)
                    elif data[0] == ui_num['실시간차트']:
                        self.signal4.emit(data)
                    elif data[0] == ui_num['풍경사진']:
                        self.signal7.emit(data)
                    elif data[0] in (ui_num['코스피'], ui_num['코스닥']):
                        self.signal5.emit(data)
                    elif data[0] >= ui_num['트리맵']:
                        self.signal6.emit(data)
                else:
                    if data[0] == 'qsize':
                        self.signal8.emit(data[1])
                    elif '라이브' in data:
                        self.signal9.emit(data)
                    elif data == '키움매니저구동완료':
                        self.signal10.emit()
            except:
                pass


class ZmqServ(QThread):
    def __init__(self, wdzservQ_, port_num):
        super().__init__()
        self.wdzservQ_ = wdzservQ_
        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.PUB)
        self.sock.bind(f'tcp://*:{port_num}')

    def run(self):
        while True:
            msg, data = self.wdzservQ_.get()
            self.sock.send_string(msg, zmq.SNDMORE)
            self.sock.send_pyobj(data)
            if data == '통신종료':
                QThread.sleep(1)
                break
        self.sock.close()
        self.zctx.term()


class ZmqRecv(QThread):
    def __init__(self, qlist_, port_num):
        super().__init__()
        """
        windowQ, soundQ, ui.queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ = qlist_[0]
        self.soundQ  = qlist_[1]
        self.queryQ  = qlist_[2]
        self.teleQ   = qlist_[3]
        self.chartQ  = qlist_[4]
        self.hogaQ   = qlist_[5]
        self.liveQ   = qlist_[11]

        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.SUB)
        self.sock.connect(f'tcp://localhost:{port_num}')
        self.sock.setsockopt_string(zmq.SUBSCRIBE, '')

    def run(self):
        while True:
            msg  = self.sock.recv_string()
            data = self.sock.recv_pyobj()
            if msg == 'window':
                self.windowQ.put(data)
                if data == '통신종료':
                    QThread.sleep(1)
                    break
            elif msg == 'sound':
                self.soundQ.put(data)
            elif msg == 'query':
                self.queryQ.put(data)
            elif msg == 'tele':
                self.teleQ.put(data)
            elif msg == 'chart':
                self.chartQ.put(data)
            elif msg == 'hoga':
                self.hogaQ.put(data)
            elif msg == 'live':
                self.liveQ.put(data)
            elif msg == 'qsize':
                self.windowQ.put(data)
        self.sock.close()
        self.zctx.term()


class MainWindow(QMainWindow):
    def __init__(self, auto_run_):
        super().__init__()

        self.windowQ, self.soundQ, self.queryQ, self.teleQ, self.chartQ, self.hogaQ, self.webcQ, self.backQ, \
            self.creceivQ, self.ctraderQ, self.cstgQ, self.liveQ, self.totalQ, self.testQ, self.kimpQ, self.wdzservQ = \
            Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), \
            Queue(), Queue(), Queue(), Queue()

        self.qlist = [
            self.windowQ, self.soundQ, self.queryQ, self.teleQ, self.chartQ, self.hogaQ, self.webcQ, self.backQ,
            self.creceivQ, self.ctraderQ, self.cstgQ, self.liveQ, self.kimpQ, self.wdzservQ, self.totalQ
        ]

        self.proc_tele  = Process(target=TelegramMsg, args=(self.qlist,), daemon=True)
        self.proc_webc  = Process(target=WebCrawling, args=(self.qlist,), daemon=True)
        self.proc_sound = Process(target=Sound, args=(self.qlist,), daemon=True)
        self.proc_query = Process(target=Query, args=(self.qlist,))
        self.proc_chart = Process(target=Chart, args=(self.qlist,), daemon=True)
        self.proc_hoga  = Process(target=Hoga, args=(self.qlist,), daemon=True)
        # STOM Live disabled
        # self.proc_live  = Process(target=LiveClient, args=(self.qlist,), daemon=True)

        self.proc_tele.start()
        self.proc_webc.start()
        self.proc_sound.start()
        self.proc_query.start()
        self.proc_chart.start()
        self.proc_hoga.start()
        # STOM Live disabled
        # self.proc_live.start()

        self.auto_run = auto_run_
        self.dict_set = DICT_SET
        self.main_btn = 0
        self.counter  = 0
        self.cpu_per  = 0
        self.int_time = int_hms()
        self.wc       = WidgetCreater(self)

        SetIcon(self)
        SetMainMenu(self, self.wc)
        SetTable(self, self.wc)
        SetStockBack(self, self.wc)
        SetCoinBack(self, self.wc)
        SetLogTap(self, self.wc)
        SetSetupTap(self, self.wc)
        SetOrderTap(self, self.wc)
        SetDialogChart(self, self.wc)
        SetDialogEtc(self, self.wc)
        SetDialogBack(self, self.wc)
        SetDialogStrategy(self, self.wc)

        con1 = sqlite3.connect(DB_SETTING)
        con2 = sqlite3.connect(DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN)
        df = None
        try:
            df = pd.read_sql('SELECT * FROM codename', con1).set_index('index')
        except:
            try:
                df = pd.read_sql('SELECT * FROM codename', con2).set_index('index')
            except:
                print('=' * 60)
                print('[WARNING] codename 테이블이 존재하지 않습니다.')
                print('주식로그인을 한번 실행하면 codename 테이블이 생성됩니다.')
                print('=' * 60)
                df = pd.DataFrame(columns=['종목명'])
        con1.close()
        con2.close()

        self.dict_name = {code: df['종목명'][code] for code in df.index} if len(df) > 0 else {}
        self.dict_code = {name: code for code, name in self.dict_name.items()}

        if 0 < len(df) < 10:
            print('setting.db 내에 codename 테이블이 갱신되지 않았습니다.')
            print('주식로그인을 한번 실행하면 codename 테이블이 갱신됩니다.')

        con = sqlite3.connect(DB_COIN_TICK)
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        con.close()

        self.ct_lineEdittttt_04.setCompleter(QCompleter(list(self.dict_code.values())))
        self.ct_lineEdittttt_05.setCompleter(QCompleter(list(self.dict_name.values()) + df['name'].to_list()))

        self.back_schedul     = False
        self.showQsize        = False
        self.image_search     = False
        self.auto_mode        = False
        self.database_control = False
        self.ssicon_alert     = False
        self.csicon_alert     = False
        self.lgicon_alert     = False
        self.database_chart   = False
        self.data_save        = False
        self.back_engining    = False
        self.backtest_engine  = False
        self.extend_window    = False
        self.back_cancelling  = False

        self.animation        = None
        self.webEngineView    = None
        self.dict_sgbn        = None
        self.dict_cn          = None
        self.dict_mt          = None
        self.dbreader         = DatabaseReadOnly()

        self.vars             = {}
        self.buy_index        = []
        self.sell_index       = []
        self.back_eprocs      = []
        self.back_eques       = []
        self.back_sprocs      = []
        self.back_sques       = []
        self.avg_list         = []
        self.back_count       = 0
        self.back_scount      = 0
        self.multi            = 0
        self.divide_mode      = str

        self.backengin_window_open = False
        self.optuna_window_open    = False

        self.proc_backtester_bs    = None
        self.proc_backtester_bf    = None
        self.proc_backtester_o     = None
        self.proc_backtester_ov    = None
        self.proc_backtester_ovc   = None
        self.proc_backtester_ot    = None
        self.proc_backtester_ovt   = None
        self.proc_backtester_ovct  = None
        self.proc_backtester_or    = None
        self.proc_backtester_orv   = None
        self.proc_backtester_orvc  = None
        self.proc_backtester_b     = None
        self.proc_backtester_bv    = None
        self.proc_backtester_bvc   = None
        self.proc_backtester_bt    = None
        self.proc_backtester_bvt   = None
        self.proc_backtester_bvct  = None
        self.proc_backtester_br    = None
        self.proc_backtester_brv   = None
        self.proc_backtester_brvc  = None
        self.proc_backtester_og    = None
        self.proc_backtester_ogv   = None
        self.proc_backtester_ogvc  = None
        self.proc_backtester_oc    = None
        self.proc_backtester_ocv   = None
        self.proc_backtester_ocvc  = None

        self.proc_receiver_coin    = None
        self.proc_strategy_coin    = None
        self.stg_btn_number   = 1
        self.dict_stg_btn     = dict(dict_stg_button)
        self.proc_trader_coin      = None
        self.proc_coin_kimp        = None

        self.backdetail_list       = None
        self.backcheckbox_list     = None
        self.order_combo_name_list = []

        self.ctpg_name             = None
        self.ctpg_cline            = None
        self.ctpg_hline            = None
        self.ctpg_xticks           = None
        self.ctpg_arry             = None
        self.ctpg_last_candlestick = None
        self.ctpg_last_volumebar   = None
        self.ctpg_last_xtick       = None
        self.ctpg_legend           = {}
        self.ctpg_item             = {}
        self.ctpg_data             = {}
        self.ctpg_factors          = []
        self.ctpg_labels           = []

        self.srqsize = 0
        self.stqsize = 0
        self.ssqsize = 0

        self.df_kp   = None
        self.df_kd   = None
        self.tm_ax1  = None
        self.tm_ax2  = None
        self.df_tm1  = None
        self.df_tm2  = None
        self.tm_cl1  = None
        self.tm_cl2  = None
        self.tm_dt   = False
        self.tm_mc1  = 0
        self.tm_mc2  = 0

        font_name = 'C:/Windows/Fonts/malgun.ttf'
        font_family = font_manager.FontProperties(fname=font_name).get_name()
        plt.rcParams['font.family'] = font_family
        plt.rcParams['axes.unicode_minus'] = False

        port_num = 5100
        while True:
            try:
                self.zmqrecv = ZmqRecv(self.qlist, port_num + 1)
                self.zmqrecv.start()
                self.zmqserv = ZmqServ(self.wdzservQ, port_num)
                self.zmqserv.start()
            except:
                self.zmqrecv.terminate()
                port_num += 10
            else:
                break

        subprocess.Popen(f'python ./stock/kiwoom_manager.py {port_num}')

        self.update_textedit    = UpdateTextedit(self)
        self.update_tablewidget = UpdateTablewidget(self)
        self.draw_chart         = DrawChart(self)
        self.draw_realchart     = DrawRealChart(self)
        self.draw_realjisuchart = DrawRealJisuChart(self)
        self.draw_treemap       = DrawTremap(self)

        self.writer = Writer(self.windowQ)
        self.writer.signal1.connect(self.update_textedit.update_texedit)
        self.writer.signal2.connect(self.update_tablewidget.update_tablewidget)
        self.writer.signal3.connect(self.draw_chart.draw_chart)
        self.writer.signal4.connect(self.draw_realchart.draw_realchart)
        self.writer.signal5.connect(self.draw_realjisuchart.draw_realjisuchart)
        self.writer.signal6.connect(self.draw_treemap.draw_treemap)
        self.writer.signal7.connect(self.UpdateImage)
        self.writer.signal8.connect(self.UpdateSQsize)
        self.writer.signal9.connect(self.StomliveScreenshot)
        self.writer.signal10.connect(self.Qtimer1Start)
        self.writer.start()

        self.qtimer1 = QTimer()
        self.qtimer1.setInterval(1 * 1000)
        self.qtimer1.timeout.connect(self.ProcessStarter)

        self.qtimer2 = QTimer()
        self.qtimer2.setInterval(500)
        self.qtimer2.timeout.connect(self.UpdateProgressBar)
        self.qtimer2.start()

        self.qtimer3 = QTimer()
        self.qtimer3.setInterval(1 * 1000)
        self.qtimer3.timeout.connect(self.UpdateCpuper)
        self.qtimer3.start()

        if self.dict_set['코인리시버']: self.mnButtonClicked_01(1)

    # =================================================================================================================
    def Qtimer1Start(self):                self.qtimer1.start()
    # =================================================================================================================
    def ProcessStarter(self):              process_starter(self)
    # =================================================================================================================
    def ChartCountChange(self):            chart_count_change(self)
    # =================================================================================================================
    def UpdateProgressBar(self):           update_progressbar(self)
    def UpdateImage(self, data):           update_image(self, data)
    def UpdateSQsize(self, data):          update_sqsize(self, data)
    def UpdateCpuper(self):                update_cpuper(self)
    def UpdateDictSet(self):               update_dictset(self)
    def ChartClear(self):                  chart_clear(self)
    def ExtendWindow(self):                extend_window(self)
    def CalendarClicked(self, gubun):      calendar_clicked(self, gubun)
    def AutoBackSchedule(self, gubun):     auto_back_schedule(self, gubun)
    def VideoWidgetClose(self, state):     video_widget_close(self, state)
    def StomliveScreenshot(self, cmd):     stom_live_screenshot(self, cmd)
    def ChartScreenShot(self):             chart_screenshot(self)
    def ChartScreenShot2(self):            chart_screenshot2(self)
    # =================================================================================================================
    def CheckboxChanged_01(self, state):   checkbox_changed_01(self, state)
    def CheckboxChanged_02(self, state):   checkbox_changed_02(self, state)
    def CheckboxChanged_03(self, state):   checkbox_changed_03(self, state)
    def CheckboxChanged_04(self, state):   checkbox_changed_04(self, state)
    def CheckboxChanged_05(self, state):   checkbox_changed_05(self, state)
    def CheckboxChanged_06(self, state):   checkbox_changed_06(self, state)
    def CheckboxChanged_07(self, state):   checkbox_changed_07(self, state)
    def CheckboxChanged_08(self, state):   checkbox_changed_08(self, state)
    def CheckboxChanged_09(self, state):   checkbox_changed_09(self, state)
    def CheckboxChanged_10(self, state):   checkbox_changed_10(self, state)
    def CheckboxChanged_11(self, state):   checkbox_changed_11(self, state)
    def CheckboxChanged_12(self, state):   checkbox_changed_12(self, state)
    def CheckboxChanged_13(self, state):   checkbox_changed_13(self, state)
    def CheckboxChanged_14(self, state):   checkbox_changed_14(self, state)
    def CheckboxChanged_15(self, state):   checkbox_changed_15(self, state)
    def CheckboxChanged_16(self, state):   checkbox_changed_16(self, state)
    def CheckboxChanged_17(self, state):   checkbox_changed_17(self, state)
    def CheckboxChanged_18(self, state):   checkbox_changed_18(self, state)
    def CheckboxChanged_19(self, state):   checkbox_changed_19(self, state)
    # =================================================================================================================
    def sbCheckboxChanged_01(self, state): sbcheckbox_changed_01(self, state)
    def sbCheckboxChanged_02(self, state): sbcheckbox_changed_02(self, state)
    def ssCheckboxChanged_01(self, state): sscheckbox_changed_01(self, state)
    def ssCheckboxChanged_02(self, state): sscheckbox_changed_02(self, state)
    # =================================================================================================================
    def cbCheckboxChanged_01(self, state): cbcheckbox_changed_01(self, state)
    def cbCheckboxChanged_02(self, state): cbcheckbox_changed_02(self, state)
    def csCheckboxChanged_01(self, state): cscheckbox_changed_01(self, state)
    def csCheckboxChanged_02(self, state): cscheckbox_changed_02(self, state)
    # =================================================================================================================
    @pyqtSlot(int, int)
    def CellClicked_01(self, row, col): cell_clicked_01(self, row, col)
    @pyqtSlot(int)
    def CellClicked_02(self, row):      cell_clicked_02(self, row)
    @pyqtSlot(int)
    def CellClicked_03(self, row):      cell_clicked_03(self, row)
    @pyqtSlot(int)
    def CellClicked_04(self, row):      cell_clicked_04(self, row)
    @pyqtSlot(int)
    def CellClicked_05(self, row):      cell_clicked_05(self, row)
    @pyqtSlot(int)
    def CellClicked_06(self, row):      cell_clicked_06(self, row)
    @pyqtSlot(int)
    def CellClicked_07(self, row):      cell_clicked_07(self, row)
    @pyqtSlot(int)
    def CellClicked_08(self, row):      cell_clicked_08(self, row)
    @pyqtSlot(int, int)
    def CellClicked_09(self, row, col): cell_clicked_09(self, row, col)
    @pyqtSlot(int, int)
    def CellClicked_10(self, row, col): cell_clicked_10(self, row, col)
    def CellClicked_11(self):           cell_clicked_11(self)
    # =================================================================================================================
    def ReturnPress_01(self): return_press_01(self)
    def ReturnPress_02(self): return_press_02(self)
    # =================================================================================================================
    def TextChanged_01(self): text_changed_01(self)
    def TextChanged_02(self): text_changed_02(self)
    def TextChanged_03(self): text_changed_03(self)
    def TextChanged_04(self): text_changed_04(self)
    def TextChanged_05(self): text_changed_05(self)
    # =================================================================================================================
    def ShowDialogGraph(self, df):                                  show_dialog_graph(self, df)
    def ShowDialog(self, code_or_name, tickcount, searchdate, col): show_dialog(self, code_or_name, tickcount, searchdate, col)
    def ShowDialogWeb(self, show, code):                            show_dialog_web(self, show, code)
    def ShowDialogHoga(self, show, coin, code):                     show_dialog_hoga(self, show, coin, code)

    def ShowDialogChart(self, real, coin, code, tickcount=None, searchdate=None, starttime=None, endtime=None, detail=None, buytimes=None):
        show_dialog_chart(self, real, coin, code, tickcount, searchdate, starttime, endtime, detail, buytimes)

    def ShowQsize(self):         show_qsize(self)
    def ShowDialogFactor(self):  show_dialog_factor(self)
    def ShowChart(self):         show_chart(self)
    def ShowHoga(self):          show_hoga(self)
    def ShowGiup(self):          show_giup(self)
    def ShowTreemap(self):       show_treemap(self)
    def ShowJisu(self):          show_jisu(self)
    def ShowDB(self):            show_db(self)
    def ShowBackScheduler(self): show_backscheduler(self)
    def ShowKimp(self):          show_kimp(self)
    def ShowOrder(self):         show_order(self)
    def PutHogaCode(self, coin, code): put_hoga_code(self, coin, code)
    def ChartMoneyTopList(self): chart_moneytop_list(self)
    def ChartSizeChange(self):   chart_size_change(self)
    # =================================================================================================================
    def dbButtonClicked_01(self): dbbutton_clicked_01(self)
    def dbButtonClicked_02(self): dbbutton_clicked_02(self)
    def dbButtonClicked_03(self): dbbutton_clicked_03(self)
    def dbButtonClicked_04(self): dbbutton_clicked_04(self)
    def dbButtonClicked_05(self): dbbutton_clicked_05(self)
    def dbButtonClicked_06(self): dbbutton_clicked_06(self)
    def dbButtonClicked_07(self): dbbutton_clicked_07(self)
    def dbButtonClicked_08(self): dbbutton_clicked_08(self)
    def dbButtonClicked_09(self): dbbutton_clicked_09(self)
    def dbButtonClicked_10(self): dbbutton_clicked_10(self)
    def dbButtonClicked_11(self): dbbutton_clicked_11(self)
    def dbButtonClicked_12(self): dbbutton_clicked_12(self)
    def dbButtonClicked_13(self): dbbutton_clicked_13(self)
    def dbButtonClicked_14(self): dbbutton_clicked_14(self)
    def dbButtonClicked_15(self): dbbutton_clicked_15(self)
    def dbButtonClicked_16(self): dbbutton_clicked_16(self)
    def dbButtonClicked_17(self): dbbutton_clicked_17(self)
    def dbButtonClicked_18(self): dbbutton_clicked_18(self)
    def dbButtonClicked_19(self): dbbutton_clicked_19(self)
    # =================================================================================================================
    def odButtonClicked_01(self): odbutton_clicked_01(self)
    def odButtonClicked_02(self): odbutton_clicked_02(self)
    def odButtonClicked_03(self): odbutton_clicked_03(self)
    def odButtonClicked_04(self): odbutton_clicked_04(self)
    def odButtonClicked_05(self): odbutton_clicked_05(self)
    def odButtonClicked_06(self): odbutton_clicked_06(self)
    def odButtonClicked_07(self): odbutton_clicked_07(self)
    def odButtonClicked_08(self): odbutton_clicked_08(self)
    # =================================================================================================================
    def opButtonClicked_01(self):        opbutton_clicked_01()
    def cpButtonClicked_01(self):        cpbutton_clicked_01(self)
    def ttButtonClicked_01(self, cmd):   ttbutton_clicked_01(self, cmd)
    def ChangeBacksDate(self):           change_back_sdate(self)
    def ChangeBackeDate(self):           change_back_edate(self)
    def stButtonClicked_01(self):        stbutton_clicked_01(self)
    def stButtonClicked_02(self):        stbutton_clicked_02(self)
    def lvButtonClicked_01(self):        lvbutton_clicked_01(self)
    def lvButtonClicked_02(self):        lvbutton_clicked_02(self)
    def lvButtonClicked_03(self):        lvbutton_clicked_03(self)
    def lvCheckChanged_01(self, state):  lvcheck_changed_01(self, state)
    def hgButtonClicked_01(self, gubun): hg_button_clicked_01(self, gubun)
    def hgButtonClicked_02(self, gubun): hg_button_clicked_02(self, gubun)
    # =================================================================================================================
    def beButtonClicked_01(self): bebutton_clicked_01(self)
    def BacktestEngineKill(self): backtest_engine_kill(self)
    def sdButtonClicked_01(self): sdbutton_clicked_01(self)
    def sdButtonClicked_02(self): sdbutton_clicked_02(self)
    def sdButtonClicked_03(self): sdbutton_clicked_03(self)
    def sdButtonClicked_04(self): sdbutton_clicked_04(self)
    def sdButtonClicked_05(self): sdbutton_clicked_05(self)
    # =================================================================================================================
    def mnButtonClicked_01(self, index):   mnbutton_c_clicked_01(self, index)
    def mnButtonClicked_02(self):          mnbutton_c_clicked_02(self)
    def mnButtonClicked_03(self, login=0): mnbutton_c_clicked_03(self, login)
    def mnButtonClicked_04(self):          mnbutton_c_clicked_04(self)
    def mnButtonClicked_05(self):          mnbutton_c_clicked_05(self)
    def mnButtonClicked_06(self):          mnbutton_c_clicked_06(self)
    # =================================================================================================================
    def ssButtonClicked_01(self): ssbutton_clicked_01(self)
    def ssButtonClicked_02(self): ssbutton_clicked_02(self)
    def ssButtonClicked_03(self): ssbutton_clicked_03(self)
    def ssButtonClicked_04(self): ssbutton_clicked_04(self)
    def ssButtonClicked_05(self): ssbutton_clicked_05(self)
    def ssButtonClicked_06(self): ssbutton_clicked_06(self)
    def csButtonClicked_01(self): csbutton_clicked_01(self)
    def csButtonClicked_02(self): csbutton_clicked_02(self)
    def csButtonClicked_03(self): csbutton_clicked_03(self)
    def csButtonClicked_04(self): csbutton_clicked_04(self)
    def csButtonClicked_05(self): csbutton_clicked_05(self)
    def csButtonClicked_06(self): csbutton_clicked_06(self)
    # =================================================================================================================
    def szooButtonClicked_01(self): szoo_button_clicked_01(self)
    def szooButtonClicked_02(self): szoo_button_clicked_02(self)
    def czooButtonClicked_01(self): czoo_button_clicked_01(self)
    def czooButtonClicked_02(self): czoo_button_clicked_02(self)
    # =================================================================================================================
    # Stock strategy zoom buttons (set_stg_stock_tap.py references)
    def szButtonClicked_01(self): szoo_button_clicked_01(self)
    def szButtonClicked_02(self): szoo_button_clicked_02(self)
    # Coin strategy zoom buttons (set_stg_coin_tap.py references)
    def czButtonClicked_01(self): czoo_button_clicked_01(self)
    def czButtonClicked_02(self): czoo_button_clicked_02(self)
    # =================================================================================================================
    def Activated_01(self): activated_01(self)
    def Activated_02(self): activated_02(self)
    def Activated_03(self): activated_03(self)
    # =================================================================================================================
    # dActivated for detail combo boxes
    def dActivated_01(self): pass  # Placeholder for detail combo activation
    # =================================================================================================================
    def sActivated_01(self): sactivated_01(self)
    def sActivated_02(self): sactivated_02(self)
    def sActivated_03(self): sactivated_03(self)
    def sActivated_04(self): sactivated_04(self)
    def sActivated_05(self): sactivated_05(self)
    def sActivated_06(self): sactivated_06(self)
    def sActivated_07(self): sactivated_07(self)
    def sActivated_08(self): sactivated_08(self)
    def sActivated_09(self): sactivated_09(self)
    # =================================================================================================================
    def cActivated_01(self): cactivated_01(self)
    def cActivated_02(self): cactivated_02(self)
    def cActivated_03(self): cactivated_03(self)
    def cActivated_04(self): cactivated_04(self)
    def cActivated_05(self): cactivated_05(self)
    def cActivated_06(self): cactivated_06(self)
    def cActivated_07(self): cactivated_07(self)
    def cActivated_08(self): cactivated_08(self)
    def cActivated_09(self): cactivated_09(self)
    def cActivated_10(self): cactivated_10(self)
    def cActivated_11(self): cactivated_11(self)
    # =================================================================================================================
    def bActivated_01(self): bactivated_01(self)
    def bActivated_02(self): bactivated_02(self)
    def bActivated_03(self): bactivated_03(self)
    # =================================================================================================================
    def GetFixStrategy(self, strategy, gubun):     return get_fix_strategy(self, strategy, gubun)
    @staticmethod
    def GetOptivarsToGavars(opti_vars_text):       return get_optivars_to_gavars(opti_vars_text)
    @staticmethod
    def GetGavarsToOptivars(ga_vars_text):         return get_gavars_to_optivars(ga_vars_text)
    def GetStgtxtToVarstxt(self, buystg, sellstg): return get_stgtxt_to_varstxt(self, buystg, sellstg)
    @staticmethod
    def GetStgtxtSort(buystg, sellstg):            return get_stgtxt_sort(buystg, sellstg)
    @staticmethod
    def GetStgtxtSort2(optivars, gavars):          return get_stgtxt_sort2(optivars, gavars)
    # =================================================================================================================
    # Stock Buy Strategy Editor Methods (ui_button_clicked_editer_stg_buy_stock.py)
    def StockBuyStgLoad(self):              stock_buy_stg_load(self)
    def StockBuyStgSave(self):              stock_buy_stg_save(self)
    def StockBuyFactor(self):               stock_buy_factor(self)
    def StockBuyStgStart(self):             stock_buy_stg_start(self)
    def StockBuyVitimeComparison(self):     stock_buy_vitime_comparison(self)
    def StockBuyVilowfiveComparison(self):  stock_buy_vilowfive_comparison(self)
    def StockBuyPerLimit(self):             stock_buy_per_limit(self)
    def StockBuyLowHighAvgPer(self):        stock_buy_low_high_avg_per(self)
    def StockChLowerLimit(self):            stock_ch_lower_limit(self)
    def StockChAvgGap(self):                stock_ch_avg_gap(self)
    def StockBuySignalInsert(self):         stock_buy_signal_insert(self)
    def StockBuyStgStop(self):              stock_buy_stg_stop(self)
    # =================================================================================================================
    # Stock Sell Strategy Editor Methods (ui_button_clicked_editer_stg_sell_stock.py)
    def StockSellStgLoad(self):             stock_sell_stg_load(self)
    def StockSellStgSave(self):             stock_sell_stg_save(self)
    def StockSellFactor(self):              stock_sell_factor(self)
    def StockSellStgStart(self):            stock_sell_stg_start(self)
    def StockSellDeadLine(self):            stock_sell_dead_line(self)
    def StockSellProfitLine(self):          stock_sell_profit_line(self)
    def StockSellProfitSave(self):          stock_sell_profit_save(self)
    def StockSellHoldTime(self):            stock_sell_hold_time(self)
    def StockSellBeforeVi(self):            stock_sell_before_vi(self)
    def StockSellLowHighAvgPer(self):       stock_sell_low_high_avg_per(self)
    def StockSellChHighComparison(self):    stock_sell_ch_high_comparison(self)
    def StockSellAskPriceRamainCount(self): stock_sell_ask_price_ramain_count(self)
    def StockSellSignalInsert(self):        stock_sell_signal_insert(self)
    def StockSellStgStop(self):             stock_sell_stg_stop(self)
    # =================================================================================================================
    # Stock Editor Methods (ui_button_clicked_editer_stock.py)
    def StockStgEditer(self):               stock_stg_editer(self)
    def StockOptiEditer(self):              stock_opti_editer(self)
    def StockOptiTestEditer(self):          stock_opti_test_editer(self)
    def StockRwfTestEditer(self):           stock_rwf_test_editer(self)
    def StockOptiGaEditer(self):            stock_opti_ga_editer(self)
    def StockCondEditer(self):              stock_cond_editer(self)
    def StockOptiVarsEditer(self):          stock_opti_vars_editer(self)
    def StockVarsEditer(self):              stock_vars_editer(self)
    def StockBacktestLog(self):             stock_backtest_log(self)
    def StockBacktestDetail(self):          stock_backtest_detail(self)
    def StockBacktestStart(self):           stock_backtest_start(self)
    def StockBackfinderStart(self):         stock_backfinder_start(self)
    def StockBackfinderSample(self):        stock_backfinder_sample(self)
    def StockOptiStart(self, back_name):    stock_opti_start(self, back_name)
    def StockOptiRwftStart(self, back_name): stock_opti_rwft_start(self, back_name)
    def StockOptiGaStart(self, back_name):  stock_opti_ga_start(self, back_name)
    def StockOptiCondStart(self, back_name): stock_opti_cond_start(self, back_name)
    def StockOptivarsToGavars(self):        stock_optivars_to_gavars(self)
    def StockGavarsToOptivars(self):        stock_gavars_to_optivars(self)
    def StockStgVarsChange(self):           stock_stg_vars_change(self)
    def StockStgvarsKeySort(self):          stock_stgvars_key_sort(self)
    def StockOptivarsKeySort(self):         stock_optivars_key_sort(self)
    # =================================================================================================================
    # Stock Opti Methods (ui_button_clicked_editer_opti_stock.py)
    def StockOptiBuyLoad(self):             stock_opti_buy_load(self)
    def StockOptiBuySave(self):             stock_opti_buy_save(self)
    def StockOptiVarsLoad(self):            stock_opti_vars_load(self)
    def StockOptiVarsSave(self):            stock_opti_vars_save(self)
    def StockOptiSellLoad(self):            stock_opti_sell_load(self)
    def StockOptiSellSave(self):            stock_opti_sell_save(self)
    def StockOptiSample(self):              stock_opti_sample(self)
    def StockOptiToBuySave(self):           stock_opti_to_buy_save(self)
    def StockOptiToSellSave(self):          stock_opti_to_sell_save(self)
    def StockOptiStd(self):                 stock_opti_std(self)
    def StockOptiOptuna(self):              stock_opti_optuna(self)
    # =================================================================================================================
    # Stock GA Methods (ui_button_clicked_editer_ga_stock.py)
    def StockGavarsLoad(self):              stock_gavars_load(self)
    def StockGavarsSave(self):              stock_gavars_save(self)
    def StockCondbuyLoad(self):             stock_condbuy_load(self)
    def StockCondbuySave(self):             stock_condbuy_save(self)
    def StockCondsellLoad(self):            stock_condsell_load(self)
    def StockCondsellSave(self):            stock_condsell_save(self)
    # =================================================================================================================
    # Coin Buy Strategy Editor Methods (ui_button_clicked_editer_stg_buy_coin.py)
    def CoinBuyStgLoad(self):               coin_buy_stg_load(self)
    def CoinBuyStgSave(self):               coin_buy_stg_save(self)
    def CoinBuyFactor(self):                coin_buy_factor(self)
    def CoinBuyStgStart(self):              coin_buy_stg_start(self)
    def CoinBuyPerLimit(self):              coin_buy_per_limit(self)
    def CoinBuyLowHighAvgPer(self):         coin_buy_low_high_avg_per(self)
    def CoinBuyOpenCloseComparison(self):   coin_buy_open_close_comparison(self)
    def CoinBuyChLowerLimit(self):          coin_buy_ch_lower_limit(self)
    def CoinBuyChAvgGap(self):              coin_buy_ch_avg_gap(self)
    def CoinBuyChHigh(self):                coin_buy_ch_high(self)
    def CoinBuySignalInsert(self):          coin_buy_signal_insert(self)
    def CoinBuyStgStop(self):               coin_buy_stg_stop(self)
    # =================================================================================================================
    # Coin Sell Strategy Editor Methods (ui_button_clicked_editer_stg_sell_coin.py)
    def CoinSellStgLoad(self):              coin_sell_stg_load(self)
    def CoinSellStgSave(self):              coin_sell_stg_save(self)
    def CoinSellFactor(self):               coin_sell_factor(self)
    def CoinSellStgStart(self):             coin_sell_stg_start(self)
    def CoinSellDeadLine(self):             coin_sell_dead_line(self)
    def CoinSellProfitLine(self):           coin_sell_profit_line(self)
    def CoinSellProfitSave(self):           coin_sell_profit_save(self)
    def CoinSellHoldTime(self):             coin_sell_hold_time(self)
    def CoinSellChAvgComparison(self):      coin_sell_ch_avg_comparison(self)
    def CoinSellChHighComparison(self):     coin_sell_ch_high_comparison(self)
    def CoinSellLowHighAvgPer(self):        coin_sell_low_high_avg_per(self)
    def CoinSellAskPriceRamainCount(self):  coin_sell_ask_price_ramain_count(self)
    def CoinSellSignalInsert(self):         coin_sell_signal_insert(self)
    def CoinSellStgStop(self):              coin_sell_stg_stop(self)
    # =================================================================================================================
    # Coin Editor Methods (ui_button_clicked_editer_coin.py)
    def CoinStgEditer(self):                coin_stg_editer(self)
    def CoinOptiEditer(self):               coin_opti_editer(self)
    def CoinOptiTestEditer(self):           coin_opti_test_editer(self)
    def CoinRwfTestEditer(self):            coin_rwf_test_editer(self)
    def CoinOptiGaEditer(self):             coin_opti_ga_editer(self)
    def CoinCondEditer(self):               coin_cond_editer(self)
    def CoinOptiVarsEditer(self):           coin_opti_vars_editer(self)
    def CoinVarsEditer(self):               coin_vars_editer(self)
    def CoinBacktestLog(self):              coin_backtest_log(self)
    def CoinBacktestDetail(self):           coin_backtest_detail(self)
    def CoinBacktestStart(self):            coin_backtest_start(self)
    def CoinBackfinderStart(self):          coin_backfinder_start(self)
    def CoinBackfinderSample(self):         coin_backfinder_sample(self)
    def CoinOptiStart(self, back_name):     coin_opti_start(self, back_name)
    def CoinOptiRwftStart(self, back_name): coin_opti_rwft_start(self, back_name)
    def CoinOptiGaStart(self, back_name):   coin_opti_ga_start(self, back_name)
    def CoinOptiCondStart(self, back_name): coin_opti_cond_start(self, back_name)
    def CoinOptivarsToGavars(self):         coin_optivars_to_gavars(self)
    def CoinGavarsToOptivars(self):         coin_gavars_to_optivars(self)
    def CoinStgVarsChange(self):            coin_stg_vars_change(self)
    def CoinStgvarsKeySort(self):           coin_stgvars_key_sort(self)
    def CoinOptivarsKeySort(self):          coin_optivars_key_sort(self)
    # =================================================================================================================
    # Coin Opti Methods (ui_button_clicked_editer_opti_coin.py)
    def CoinOptiBuyLoad(self):              coin_opti_buy_load(self)
    def CoinOptiBuySave(self):              coin_opti_buy_save(self)
    def CoinOptiVarsLoad(self):             coin_opti_vars_load(self)
    def CoinOptiVarsSave(self):             coin_opti_vars_save(self)
    def CoinOptiSellLoad(self):             coin_opti_sell_load(self)
    def CoinOptiSellSave(self):             coin_opti_sell_save(self)
    def CoinOptiSample(self):               coin_opti_sample(self)
    def CoinOptiToBuySave(self):            coin_opti_to_buy_save(self)
    def CoinOptiToSellSave(self):           coin_opti_to_sell_save(self)
    def CoinOptiStd(self):                  coin_opti_std(self)
    def CoinOptiOptuna(self):               coin_opti_optuna(self)
    # =================================================================================================================
    # Coin GA Methods (ui_button_clicked_editer_ga_coin.py)
    def CoinGavarsLoad(self):               coin_gavars_load(self)
    def CoinGavarsSave(self):               coin_gavars_save(self)
    def CoinCondbuyLoad(self):              coin_condbuy_load(self)
    def CoinCondbuySave(self):              coin_condbuy_save(self)
    def CoinCondsellLoad(self):             coin_condsell_load(self)
    def CoinCondsellSave(self):             coin_condsell_save(self)
    # =================================================================================================================
    # Settings - Elapsed Tick Number (ui_button_clicked_dialog_elapsed_tick_number.py)
    def SettingStockElapsedTickNumberSample(self): setting_stock_elapsed_tick_number_sample(self)
    def SettingStockElapsedTickNumberLoad(self):   setting_stock_elapsed_tick_number_load(self)
    def SettingStockElapsedTickNumberSave(self):   setting_stock_elapsed_tick_number_save(self)
    def SettingCoinElapsedTickNumberSample(self):  setting_coin_elapsed_tick_number_sample(self)
    def SettingCoinElapsedTickNumberLoad(self):    setting_coin_elapsed_tick_number_load(self)
    def SettingCoinElapsedTickNumberSave(self):    setting_coin_elapsed_tick_number_save(self)
    # Legacy aliases
    def setButtonClicked_01(self):  self.SettingStockElapsedTickNumberSample()
    def setButtonClicked_02(self):  self.SettingStockElapsedTickNumberLoad()
    def setButtonClicked_03(self):  self.SettingStockElapsedTickNumberSave()
    def cetButtonClicked_01(self):  self.SettingCoinElapsedTickNumberSample()
    def cetButtonClicked_02(self):  self.SettingCoinElapsedTickNumberLoad()
    def cetButtonClicked_03(self):  self.SettingCoinElapsedTickNumberSave()
    # =================================================================================================================
    def StomLiveProcessAlive(self):     return stom_live_process_alive(self)
    def CoinReceiverProcessAlive(self): return coin_receiver_process_alive(self)
    def CoinTraderProcessAlive(self):   return coin_trader_process_alive(self)
    def CoinStrategyProcessAlive(self): return coin_strategy_process_alive(self)
    def CoinKimpProcessAlive(self):     return coinkimp_process_alive(self)
    def BacktestProcessAlive(self):     return backtest_process_alive(self)
    # =================================================================================================================
    # Settings Load/Save methods
    def SettingLoad_01(self): setting_load_01(self)
    def SettingLoad_02(self): setting_load_02(self)
    def SettingLoad_03(self): setting_load_03(self)
    def SettingLoad_04(self): setting_load_04(self)
    def SettingLoad_05(self): setting_load_05(self)
    def SettingLoad_06(self): setting_load_06(self)
    def SettingLoad_07(self): setting_load_07(self)
    def SettingLoad_08(self): setting_load_08(self)
    def SettingSave_01(self): setting_save_01(self)
    def SettingSave_02(self): setting_save_02(self)
    def SettingSave_03(self): setting_save_03(self)
    def SettingSave_04(self): setting_save_04(self)
    def SettingSave_05(self): setting_save_05(self)
    def SettingSave_06(self): setting_save_06(self)
    def SettingSave_07(self): setting_save_07(self)
    def SettingSave_08(self): setting_save_08(self)
    # Settings Management methods
    def SettingAllLoad(self): setting_all_load(self)
    def SettingAllApp(self):  setting_all_app(self)
    def SettingAllDel(self):  setting_all_del(self)
    def SettingAllSave(self): setting_all_save(self)
    def SettingAccView(self): setting_acc_view(self)
    # Order Settings methods
    def SettingOrderLoad_01(self): setting_order_load_01(self)
    def SettingOrderLoad_02(self): setting_order_load_02(self)
    def SettingOrderLoad_03(self): setting_order_load_03(self)
    def SettingOrderLoad_04(self): setting_order_load_04(self)
    def SettingOrderSave_01(self): setting_order_save_01(self)
    def SettingOrderSave_02(self): setting_order_save_02(self)
    def SettingOrderSave_03(self): setting_order_save_03(self)
    def SettingOrderSave_04(self): setting_order_save_04(self)
    # Weight Control methods
    def SettingStockWeightControl(self): setting_stock_weight_control(self)
    def SettingCoinWeightControl(self):  setting_coin_weight_control(self)
    def SettingStockWeightCotrolLoad(self): setting_stock_weight_cotrol_load(self)
    def SettingStockWeightCotrolSave(self): setting_stock_weight_cotrol_save(self)
    def SettingStockWeightCotrolChanged(self, state): setting_stock_weight_cotrol_changed(self, state)
    def SettingCoinWeightCotrolLoad(self): setting_coin_weight_cotrol_load(self)
    def SettingCoinWeightCotrolSave(self): setting_coin_weight_cotrol_save(self)
    def SettingCoinWeightCotrolChanged(self, state): setting_coin_weight_cotrol_changed(self, state)
    # Elapsed Tick Number methods
    def SettingStockElapsedTickNumber(self): setting_stock_elapsed_tick_number(self)
    def SettingCoinElapsedTickNumber(self):  setting_coin_elapsed_tick_number(self)
    # Indicator methods (from ui_button_clicked_chart.py)
    def IndicatorSettingBasic(self): indicator_setting_basic(self)
    def IndicatorSettingLoad(self):  indicator_setting_load(self)
    def IndicatorSettingSave(self):  indicator_setting_save(self)
    def GetIndicatorDetail(self, code): return get_indicator_detail(self, code)
    # Scheduler methods
    def StopScheduler(self, gubun=False): StopScheduler(self, gubun)
    # Activated methods
    def dActivated_02(self): pass  # Placeholder for settings combo activation
    def dActivated_03(self): pass  # Placeholder for order dialog combo activation
    # =================================================================================================================
    def keyPressEvent(self, event):              key_press_event(self, event)
    def eventFilter(self, widget, event): return event_filter(self, widget, event)
    def closeEvent(self, a):                     close_event(self, a)
    # =================================================================================================================
    def ProcessKill(self):                       process_kill(self)
    def ManualSaveAndExit(self):
        self.SettingAllSave()
        self.close()
    # =================================================================================================================
    # Legacy svjb/svjs/svc/sva/svo Button Methods (V1.10 compatibility - mapped to new methods)
    def svjbButtonClicked_01(self): self.StockBuyStgLoad()
    def svjbButtonClicked_02(self): self.StockBuyStgSave()
    def svjbButtonClicked_03(self): self.StockBuyFactor()
    def svjbButtonClicked_04(self): self.StockBuyStgStart()
    def svjbButtonClicked_05(self): self.StockBuyVitimeComparison()
    def svjbButtonClicked_06(self): self.StockBuyVilowfiveComparison()
    def svjbButtonClicked_07(self): self.StockBuyPerLimit()
    def svjbButtonClicked_08(self): self.StockBuyLowHighAvgPer()
    def svjbButtonClicked_09(self): self.StockChLowerLimit()
    def svjbButtonClicked_10(self): self.StockChAvgGap()
    def svjbButtonClicked_11(self): self.StockBuySignalInsert()
    def svjbButtonClicked_12(self): self.StockBuyStgStop()
    # =================================================================================================================
    def svjButtonClicked_01(self): self.StockBacktestStart()
    def svjButtonClicked_02(self): self.StockBackfinderStart()
    def svjButtonClicked_03(self): self.StockBackfinderSample()
    def svjButtonClicked_04(self): pass
    def svjButtonClicked_05(self): self.StockRwfTestEditer()
    def svjButtonClicked_06(self): self.StockOptiTestEditer()
    def svjButtonClicked_07(self): self.StockOptiEditer()
    def svjButtonClicked_08(self): self.StockStgEditer()
    def svjButtonClicked_09(self): self.StockOptiGaEditer()
    def svjButtonClicked_10(self): self.StockCondEditer()
    def svjButtonClicked_11(self): self.StockOptiVarsEditer()
    def svjButtonClicked_12(self): self.StockVarsEditer()
    def svjButtonClicked_13(self): self.StockBacktestLog()
    def svjButtonClicked_14(self, back_name): self.StockOptiStart(back_name)
    def svjButtonClicked_15(self, back_name): self.StockOptiStart(back_name)
    def svjButtonClicked_16(self, back_name): self.StockOptiStart(back_name)
    def svjButtonClicked_17(self, back_name): self.StockOptiStart(back_name)
    def svjButtonClicked_18(self): pass
    def svjButtonClicked_19(self): pass
    def svjButtonClicked_20(self): pass
    def svjButtonClicked_21(self): pass
    def svjButtonClicked_22(self): pass
    # =================================================================================================================
    def svjsButtonClicked_01(self): self.StockSellStgLoad()
    def svjsButtonClicked_02(self): self.StockSellStgSave()
    def svjsButtonClicked_03(self): self.StockSellFactor()
    def svjsButtonClicked_04(self): self.StockSellStgStart()
    def svjsButtonClicked_05(self): self.StockSellDeadLine()
    def svjsButtonClicked_06(self): self.StockSellProfitLine()
    def svjsButtonClicked_07(self): self.StockSellProfitSave()
    def svjsButtonClicked_08(self): self.StockSellHoldTime()
    def svjsButtonClicked_09(self): self.StockSellBeforeVi()
    def svjsButtonClicked_10(self): self.StockSellLowHighAvgPer()
    def svjsButtonClicked_11(self): self.StockSellChHighComparison()
    def svjsButtonClicked_12(self): self.StockSellAskPriceRamainCount()
    def svjsButtonClicked_13(self): self.StockSellSignalInsert()
    def svjsButtonClicked_14(self): self.StockSellStgStop()
    # =================================================================================================================
    def svcButtonClicked_01(self): self.StockOptiBuyLoad()
    def svcButtonClicked_02(self): self.StockOptiBuySave()
    def svcButtonClicked_03(self): self.StockOptiVarsLoad()
    def svcButtonClicked_04(self): self.StockOptiVarsSave()
    def svcButtonClicked_05(self): self.StockOptiStd()
    def svcButtonClicked_06(self): pass
    def svcButtonClicked_07(self): pass
    def svcButtonClicked_08(self): pass
    def svcButtonClicked_09(self): self.StockOptiSellLoad()
    def svcButtonClicked_10(self): self.StockOptiSellSave()
    def svcButtonClicked_11(self): self.StockOptiSample()
    # =================================================================================================================
    def svaButtonClicked_01(self): self.StockGavarsLoad()
    def svaButtonClicked_02(self): self.StockGavarsSave()
    # =================================================================================================================
    def svoButtonClicked_01(self): self.StockCondbuyLoad()
    def svoButtonClicked_02(self): self.StockCondbuySave()
    def svoButtonClicked_03(self): self.StockCondsellLoad()
    def svoButtonClicked_04(self): self.StockCondsellSave()
    # =================================================================================================================
    def cvjbButtonClicked_01(self): self.CoinBuyStgLoad()
    def cvjbButtonClicked_02(self): self.CoinBuyStgSave()
    def cvjbButtonClicked_03(self): self.CoinBuyFactor()
    def cvjbButtonClicked_04(self): self.CoinBuyStgStart()
    def cvjbButtonClicked_05(self): self.CoinBuyPerLimit()
    def cvjbButtonClicked_06(self): self.CoinBuyLowHighAvgPer()
    def cvjbButtonClicked_07(self): self.CoinBuyOpenCloseComparison()
    def cvjbButtonClicked_08(self): self.CoinBuyChLowerLimit()
    def cvjbButtonClicked_09(self): self.CoinBuyChAvgGap()
    def cvjbButtonClicked_10(self): self.CoinBuyChHigh()
    def cvjbButtonClicked_11(self): self.CoinBuySignalInsert()
    def cvjbButtonClicked_12(self): self.CoinBuyStgStop()
    # =================================================================================================================
    def cvjButtonClicked_01(self): self.CoinBacktestStart()
    def cvjButtonClicked_02(self): self.CoinBackfinderStart()
    def cvjButtonClicked_03(self): self.CoinBackfinderSample()
    def cvjButtonClicked_04(self): pass
    def cvjButtonClicked_05(self): self.CoinRwfTestEditer()
    def cvjButtonClicked_06(self): self.CoinOptiTestEditer()
    def cvjButtonClicked_07(self): self.CoinOptiEditer()
    def cvjButtonClicked_08(self): self.CoinStgEditer()
    def cvjButtonClicked_09(self): self.CoinOptiGaEditer()
    def cvjButtonClicked_10(self): self.CoinCondEditer()
    def cvjButtonClicked_11(self): self.CoinOptiVarsEditer()
    def cvjButtonClicked_12(self): self.CoinVarsEditer()
    def cvjButtonClicked_13(self): self.CoinBacktestLog()
    def cvjButtonClicked_14(self, back_name): self.CoinOptiStart(back_name)
    def cvjButtonClicked_15(self, back_name): self.CoinOptiStart(back_name)
    def cvjButtonClicked_16(self, back_name): self.CoinOptiStart(back_name)
    def cvjButtonClicked_17(self, back_name): self.CoinOptiStart(back_name)
    def cvjButtonClicked_18(self): pass
    def cvjButtonClicked_19(self): pass
    def cvjButtonClicked_20(self): pass
    def cvjButtonClicked_21(self): pass
    def cvjButtonClicked_22(self): pass
    # =================================================================================================================
    def cvjsButtonClicked_01(self): self.CoinSellStgLoad()
    def cvjsButtonClicked_02(self): self.CoinSellStgSave()
    def cvjsButtonClicked_03(self): self.CoinSellFactor()
    def cvjsButtonClicked_04(self): self.CoinSellStgStart()
    def cvjsButtonClicked_05(self): self.CoinSellDeadLine()
    def cvjsButtonClicked_06(self): self.CoinSellProfitLine()
    def cvjsButtonClicked_07(self): self.CoinSellProfitSave()
    def cvjsButtonClicked_08(self): self.CoinSellHoldTime()
    def cvjsButtonClicked_09(self): self.CoinSellChAvgComparison()
    def cvjsButtonClicked_10(self): self.CoinSellChHighComparison()
    def cvjsButtonClicked_11(self): self.CoinSellLowHighAvgPer()
    def cvjsButtonClicked_12(self): self.CoinSellAskPriceRamainCount()
    def cvjsButtonClicked_13(self): self.CoinSellSignalInsert()
    def cvjsButtonClicked_14(self): self.CoinSellStgStop()
    # =================================================================================================================
    def cvcButtonClicked_01(self): self.CoinOptiBuyLoad()
    def cvcButtonClicked_02(self): self.CoinOptiBuySave()
    def cvcButtonClicked_03(self): self.CoinOptiVarsLoad()
    def cvcButtonClicked_04(self): self.CoinOptiVarsSave()
    def cvcButtonClicked_05(self): self.CoinOptiStd()
    def cvcButtonClicked_06(self): pass
    def cvcButtonClicked_07(self): pass
    def cvcButtonClicked_08(self): pass
    def cvcButtonClicked_09(self): self.CoinOptiSellLoad()
    def cvcButtonClicked_10(self): self.CoinOptiSellSave()
    def cvcButtonClicked_11(self): self.CoinOptiSample()
    # =================================================================================================================
    def cvaButtonClicked_01(self): self.CoinGavarsLoad()
    def cvaButtonClicked_02(self): self.CoinGavarsSave()
    def cvoButtonClicked_01(self): self.CoinCondbuyLoad()
    def cvoButtonClicked_02(self): self.CoinCondbuySave()
    def cvoButtonClicked_03(self): self.CoinCondsellLoad()
    def cvoButtonClicked_04(self): self.CoinCondsellSave()
    # =================================================================================================================
    def BackTestengineShow(self, gubun):                 backengine_show(self, gubun)
    def BacktestEngineStart(self, gubun):                start_backengine(self, gubun)
    def StartBacktestEngine(self, gubun):                start_backengine(self, gubun)
    def BackCodeTest1(self, stg_code):            return back_code_test1(stg_code, self.testQ)
    def BackCodeTest2(self, vars_code, ga=False): return back_code_test2(vars_code, self.testQ, ga)
    def BackCodeTest3(self, gubun, conds_code):   return back_code_test3(gubun, conds_code, self.testQ)
    def ClearBacktestQ(self):                            clear_backtestQ(self)
    def BacktestProcessKill(self, gubun):                backtest_process_kill(self, gubun)
    # =================================================================================================================
    def ctButtonClicked_01(self): ct_button_clicked_01(self)
    def ctButtonClicked_02(self): ct_button_clicked_02(self)
    def ctButtonClicked_03(self): ct_button_clicked_03(self)
    def GetKlist(self, code): return get_k_list(self, code)
    # =================================================================================================================
    def sjButtonClicked_01(self): sj_button_cicked_01(self)
    def sjButtonClicked_02(self): sj_button_cicked_02(self)
    def sjButtonClicked_03(self): sj_button_cicked_03(self)
    def sjButtonClicked_04(self): sj_button_cicked_04(self)
    def sjButtonClicked_05(self): sj_button_cicked_05(self)
    def sjButtonClicked_06(self): sj_button_cicked_06(self)
    def sjButtonClicked_07(self): sj_button_cicked_07(self)
    def sjButtonClicked_08(self): sj_button_cicked_08(self)
    def sjButtonClicked_09(self): sj_button_cicked_09(self)
    def sjButtonClicked_10(self): sj_button_cicked_10(self)
    def sjButtonClicked_11(self): sj_button_cicked_11(self)
    def sjButtonClicked_12(self): sj_button_cicked_12(self)
    def sjButtonClicked_13(self): sj_button_cicked_13(self)
    def sjButtonClicked_14(self): sj_button_cicked_14(self)
    def sjButtonClicked_15(self): sj_button_cicked_15(self)
    def sjButtonClicked_16(self): sj_button_cicked_16(self)
    def sjButtonClicked_17(self): sj_button_cicked_17(self)
    def sjButtonClicked_19(self): sj_button_cicked_19(self)
    def sjButtonClicked_20(self): sj_button_cicked_20(self)
    def sjButtonClicked_21(self): sj_button_cicked_21(self)
    def sjButtonClicked_22(self): sj_button_cicked_22(self)
    def sjButtonClicked_23(self): sj_button_cicked_23(self)
    def sjButtonClicked_24(self): sj_button_cicked_24(self)
    def sjButtonClicked_25(self): sj_button_cicked_25(self)
    def sjButtonClicked_26(self): sj_button_cicked_26(self)
    def sjButtonClicked_27(self): sj_button_cicked_27(self)
    def sjButtonClicked_28(self): sj_button_cicked_28(self)
    def sjButtonClicked_29(self): sj_button_cicked_29(self)
    def sjButtonClicked_30(self): sj_button_cicked_30(self)
    def sjButtonClicked_31(self): sj_button_cicked_31(self)
    def sjButtonClicked_32(self): sj_button_cicked_32(self)
    def sjButtonClicked_33(self): sj_button_cicked_33(self)
    def sjButtonClicked_34(self): sj_button_cicked_34(self)
    # =================================================================================================================
    def bjsButtonClicked_01(self):       bjs_button_clicked_01(self)
    def bjsButtonClicked_02(self):       bjs_button_clicked_02(self)
    def bjcButtonClicked_01(self):       bjc_button_clicked_01(self)
    def bjcButtonClicked_02(self):       bjc_button_clicked_02(self)
    def bjsCheckChanged_01(self, state): bjs_check_changed_01(self, state)
    def bjcCheckChanged_01(self, state): bjc_check_changed_01(self, state)
    # =================================================================================================================
    # Strategy Dialog Methods (pyd→py inference from V2.39 SetDialogStrategy / ui_button_clicked_strategy.py)
    def StrategyButtonClicked(self, cmd):   button_clicked_strategy(self, cmd)
    def StrategyCustomBottunDel(self):      button_clicked_strategy_delete(self)
    def StrategyCustomBottunSave(self):     button_clicked_strategy_save(self)
    def StrategyCustomDialogShow(self):
        if self.stg_btn_number <= 200:
            btn = getattr(self, f'stg_pushButton_{self.stg_btn_number:03d}')
            self.stginput_lineeditt1.setText(btn.text())
            self.stginput_lineeditt2.setText(btn.text())
            self.stginput_textEditt1.clear()
            self.stginput_textEditt1.insertPlainText(self.dict_stg_btn.get(self.stg_btn_number, ''))
            self.dialog_stg_input1.show()
        else:
            btn = getattr(self, f'stg_pushButton_{self.stg_btn_number:03d}')
            self.stginput_lineeditt3.setText(btn.text())
            self.stginput_lineeditt4.setText(btn.text())
            self.stginput_textEditt2.clear()
            self.stginput_textEditt2.insertPlainText(self.dict_stg_btn.get(self.stg_btn_number, ''))
            self.dialog_stg_input2.show()
