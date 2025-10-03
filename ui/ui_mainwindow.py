import zmq
import socket
import subprocess
from PyQt5.QtWidgets import QCompleter
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QThread

from ui.set_icon import SetIcon
from ui.set_table import SetTable
from ui.set_logtap import SetLogTap
from ui.set_cbtap import SetCoinBack
from ui.set_sbtap import SetStockBack
from ui.set_widget import WidgetCreater
from ui.set_setuptap import SetSetupTap
from ui.set_ordertap import SetOrderTap
from ui.set_mainmenu import SetMainMenu
from ui.set_dialog_etc import SetDialogEtc
from ui.set_dialog_back import SetDialogBack
from ui.set_dialog_chart import SetDialogChart

from ui.ui_etc import *
from ui.ui_draw_chart import *
from ui.ui_activated_b import *
from ui.ui_activated_c import *
from ui.ui_activated_s import *
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
from ui.ui_button_clicked_db import *
from ui.ui_button_clicked_ob import *
from ui.ui_button_clicked_sd import *
from ui.ui_button_clicked_mn import *
from ui.ui_button_clicked_sj import *
from ui.ui_update_tablewidget import *
from ui.ui_update_progressbar import *
from ui.ui_button_clicked_etc import *
from ui.ui_chart_count_change import *
from ui.ui_button_clicked_svc import *
from ui.ui_button_clicked_svj import *
from ui.ui_button_clicked_cvc import *
from ui.ui_button_clicked_cvj import *
from ui.ui_button_clicked_svjs import *
from ui.ui_button_clicked_svjb import *
from ui.ui_button_clicked_cvoa import *
from ui.ui_button_clicked_cvjs import *
from ui.ui_button_clicked_cvjb import *
from ui.ui_button_clicked_svoa import *
from ui.ui_button_clicked_zoom import *
from ui.ui_button_clicked_etsj import *
from ui.ui_button_clicked_ss_cs import *
from ui.ui_button_clicked_chart import *

from utility.hoga import *
from utility.chart import *
from utility.sound import *
from utility.query import *
from utility.static import *
from utility.setting import *
from utility.webcrawling import *
from utility.telegram_msg import *


class LiveSender(Thread):
    def __init__(self, sock, liveQ):
        super().__init__()
        self.sock  = sock
        self.liveQ = liveQ

    def run(self):
        send_time = timedelta_sec(5)
        while True:
            try:
                if not self.liveQ.empty():
                    data = self.liveQ.get()
                    if type(data) == tuple:
                        if self.liveQ.empty() and now() > send_time:
                            gubun, df = data
                            data = list(df.iloc[0])
                            data = [str(int(x)) if i != 5 else str(float(x)) for i, x in enumerate(data)]
                            text = f"{gubun};{';'.join(data)}"
                            self.sock.sendall(text.encode('utf-8'))
                            send_time = timedelta_sec(5)
                    else:
                        self.sock.sendall(data.encode('utf-8'))
                time.sleep(0.01)
            except:
                pass


class LiveClient:
    def __init__(self, _qlist):
        self.windowQ = _qlist[0]
        self.liveQ   = _qlist[11]
        self.sock    = None
        self.Start()

    def Start(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect(('139.150.82.209', 5728))
                sender = LiveSender(self.sock, self.liveQ)
                sender.start()
                print('스톰 라이브 서버에 연결되었습니다.')
                while True:
                    data = self.sock.recv(1024000).decode('utf-8')
                    self.UpdateStomLiveData(data)
                    time.sleep(0.01)
            except:
                print('스톰 라이브 서버 연결이 해제되었습니다. 10초 후 재연결합니다.')
                time.sleep(10)

    def UpdateStomLiveData(self, data):
        data1, data2, data3, data4, data5, data6 = None, None, None, None, None, None
        df1, df2, df3, df4, df5, df6, df7, df8 = None, None, None, None, None, None, None, None

        if '주식당일시작' in data:
            data1 = data.split('주식당일시작')[1].split('주식당일종료')[0].split('^')
        if '주식통계시작' in data:
            data2 = data.split('주식통계시작')[1].split('주식통계종료')[0].split('^')
        if '코인당일시작' in data:
            data3 = data.split('코인당일시작')[1].split('코인당일종료')[0].split('^')
        if '코인통계시작' in data:
            data4 = data.split('코인통계시작')[1].split('코인통계종료')[0].split('^')
        if '백테당일시작' in data:
            data5 = data.split('백테당일시작')[1].split('백테당일종료')[0].split('^')
        if '백테통계시작' in data:
            data6 = data.split('백테통계시작')[1].split('백테통계종료')[0].split('^')

        if data1 is not None:
            data1 = [[int(x) if '.' not in x else float(x) for x in d.split(';')] for i, d in enumerate(data1)]
            df1 = pd.DataFrame(dict(zip(columns_tt, data1)))
            df1.sort_values(by=['수익금합계'], ascending=False, inplace=True)

        if data2 is not None:
            data2 = [[self.tatal_text_conv(i, x) for x in d.split(';')] for i, d in enumerate(data2)]
            df3 = pd.DataFrame(dict(zip(columns_nd, data2)))
            df3 = df3[::-1]

            df2 = pd.DataFrame({
                '기간': [len(df3)],
                '누적매수금액': [df3['총매수금액'].sum()],
                '누적매도금액': [df3['총매도금액'].sum()],
                '누적수익금액': [df3['총수익금액'].sum()],
                '누적손실금액': [df3['총손실금액'].sum()],
                '누적수익률': [round(df3['수익금합계'].sum() / df3['총매수금액'].sum() * 100, 2)],
                '누적수익금': [df3['수익금합계'].sum()]
            })

        if data3 is not None:
            data3 = [[int(x) if '.' not in x else float(x) for x in d.split(';')] for i, d in enumerate(data3)]
            df4 = pd.DataFrame(dict(zip(columns_tt, data3)))

        if data4 is not None:
            data4 = [[self.tatal_text_conv(i, x) for x in d.split(';')] for i, d in enumerate(data4)]
            df6 = pd.DataFrame(dict(zip(columns_nd, data4)))
            df6 = df6[::-1]

            df5 = pd.DataFrame({
                '기간': [len(df6)],
                '누적매수금액': [df6['총매수금액'].sum()],
                '누적매도금액': [df6['총매도금액'].sum()],
                '누적수익금액': [df6['총수익금액'].sum()],
                '누적손실금액': [df6['총손실금액'].sum()],
                '누적수익률': [round(df6['수익금합계'].sum() / df6['총매수금액'].sum() * 100, 2)],
                '누적수익금': [df6['수익금합계'].sum()]
            })

        if data5 is not None:
            data5 = [[self.back_text_conv(i, x) for x in d.split(';')] for i, d in enumerate(data5)]
            df7 = pd.DataFrame(dict(zip(columns_sd, data5)))
            df7.sort_values(by=['tsg', 'cagr'], ascending=False, inplace=True)

        if data6 is not None:
            df8 = pd.DataFrame(columns=['백테스트', '백파인더', '최적화', '최적화V', '최적화VC', '최적화T', '최적화VT', '최적화VCT',
                                        '최적화OG', '최적화OGV', '최적화OGVC', '최적화OC', '최적화OCV', '최적화OCVC', '전진분석', '전진분석V', '전진분석VC'])
            for i, d in enumerate(data6):
                df8.loc[i] = [int(x) for x in d.split(';')]

            tbk   = df8['백테스트'].iloc[:-1].sum()
            tbf   = df8['백파인더'].iloc[:-1].sum()
            toh   = df8['최적화'].iloc[:-1].sum()
            tov   = df8['최적화V'].iloc[:-1].sum()
            tovc  = df8['최적화VC'].iloc[:-1].sum()
            toht  = df8['최적화T'].iloc[:-1].sum()
            tovt  = df8['최적화VT'].iloc[:-1].sum()
            tovct = df8['최적화VCT'].iloc[:-1].sum()
            tog   = df8['최적화OG'].iloc[:-1].sum()
            togv  = df8['최적화OGV'].iloc[:-1].sum()
            togvc = df8['최적화OGVC'].iloc[:-1].sum()
            toc   = df8['최적화OC'].iloc[:-1].sum()
            tocv  = df8['최적화OCV'].iloc[:-1].sum()
            tocvc = df8['최적화OCVC'].iloc[:-1].sum()
            trh   = df8['전진분석'].iloc[:-1].sum()
            trv   = df8['전진분석V'].iloc[:-1].sum()
            trvc  = df8['전진분석VC'].iloc[:-1].sum()
            ttb   = tbk + tbf + toh + tov + tovc + toht + tovt + tovct + tog + togv + togvc + toc + tocv + tocvc + trh + trv + trvc
            abk   = df8['백테스트'].iloc[:-1].mean()
            abf   = df8['백파인더'].iloc[:-1].mean()
            aoh   = df8['최적화'].iloc[:-1].mean()
            aov   = df8['최적화V'].iloc[:-1].mean()
            aovc  = df8['최적화VC'].iloc[:-1].mean()
            aoht  = df8['최적화T'].iloc[:-1].mean()
            aovt  = df8['최적화VT'].iloc[:-1].mean()
            aovct = df8['최적화VCT'].iloc[:-1].mean()
            aog   = df8['최적화OG'].iloc[:-1].mean()
            aogv  = df8['최적화OGV'].iloc[:-1].mean()
            aogvc = df8['최적화OGVC'].iloc[:-1].mean()
            aoc   = df8['최적화OC'].iloc[:-1].mean()
            aocv  = df8['최적화OCV'].iloc[:-1].mean()
            aocvc = df8['최적화OCVC'].iloc[:-1].mean()
            arh   = df8['전진분석'].iloc[:-1].mean()
            arv   = df8['전진분석V'].iloc[:-1].mean()
            arvc  = df8['전진분석VC'].iloc[:-1].mean()
            tta   = abk + abf + aoh + aov + aovc + aoht + aovt + aovct + aog + aogv + aogvc + aoc + aocv + aocvc + arh + arv + arvc
            mbk, mbf, moh, mov, movc, moht, movt, movct, mog, mogv, mogvc, moc, mocv, mocvc, mrh, mrv, mrvc = df8.iloc[-1]
            ttm   = mbk + mbf + moh + mov + movc + moht + movt + movct + mog + mogv + mogvc + moc + mocv + mocvc + mrh + mrv + mrvc
            df8   = pd.DataFrame(columns=columns_sb)
            df8.loc[0] = '합계', tbk, tbf, toh, tov, tovc, toht, tovt, tovct, tog, togv, togvc, toc, tocv, tocvc, trh, trv, trvc, ttb
            df8.loc[1] = '평균', abk, abf, aoh, aov, aovc, aoht, aovt, aovct, aog, aogv, aogvc, aoc, aocv, aocvc, arh, arv, arvc, tta
            df8.loc[2] = 'MY', mbk, mbf, moh, mov, movc, moht, movt, movct, mog, mogv, mogvc, moc, mocv, mocvc, mrh, mrv, mrvc, ttm

        if df1 is not None:
            self.windowQ.put((ui_num['스톰라이브1'], df1))
        if df2 is not None:
            self.windowQ.put((ui_num['스톰라이브2'], df2))
        if df3 is not None:
            self.windowQ.put((ui_num['스톰라이브3'], df3))
        if df4 is not None:
            self.windowQ.put((ui_num['스톰라이브4'], df4))
        if df5 is not None:
            self.windowQ.put((ui_num['스톰라이브5'], df5))
        if df6 is not None:
            self.windowQ.put((ui_num['스톰라이브6'], df6))
        if df7 is not None:
            self.windowQ.put((ui_num['스톰라이브7'], df7))
        if df8 is not None:
            self.windowQ.put((ui_num['스톰라이브8'], df8))

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
        self.proc_live  = Process(target=LiveClient, args=(self.qlist,), daemon=True)

        self.proc_tele.start()
        self.proc_webc.start()
        self.proc_sound.start()
        self.proc_query.start()
        self.proc_chart.start()
        self.proc_hoga.start()
        self.proc_live.start()

        self.auto_run = auto_run_
        self.dict_set = DICT_SET
        self.main_btn = 0
        self.counter  = 0
        self.cpu_per  = 0
        self.int_time = int_hms()
        self.wc       = WidgetCreater(self)

        SetLogFile(self)
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

        con1 = sqlite3.connect(DB_SETTING)
        con2 = sqlite3.connect(DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN)
        try:
            df = pd.read_sql('SELECT * FROM codename', con1).set_index('index')
        except:
            df = pd.read_sql('SELECT * FROM codename', con2).set_index('index')
        con1.close()
        con2.close()

        self.dict_name = {code: df['종목명'][code] for code in df.index}
        self.dict_code = {name: code for code, name in self.dict_name.items()}

        if len(df) < 10:
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
    def Activated_01(self): activated_01(self)
    def Activated_02(self): activated_02(self)
    def Activated_03(self): activated_03(self)
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
    # =================================================================================================================
    def svjbButtonClicked_01(self): svjb_button_clicked_01(self)
    def svjbButtonClicked_02(self): svjb_button_clicked_02(self)
    def svjbButtonClicked_03(self): svjb_button_clicked_03(self)
    def svjbButtonClicked_04(self): svjb_button_clicked_04(self)
    def svjbButtonClicked_05(self): svjb_button_clicked_05(self)
    def svjbButtonClicked_06(self): svjb_button_clicked_06(self)
    def svjbButtonClicked_07(self): svjb_button_clicked_07(self)
    def svjbButtonClicked_08(self): svjb_button_clicked_08(self)
    def svjbButtonClicked_09(self): svjb_button_clicked_09(self)
    def svjbButtonClicked_10(self): svjb_button_clicked_10(self)
    def svjbButtonClicked_11(self): svjb_button_clicked_11(self)
    def svjbButtonClicked_12(self): svjb_button_clicked_12(self)
    # =================================================================================================================
    def svjButtonClicked_01(self): svj_button_clicked_01(self)
    def svjButtonClicked_02(self): svj_button_clicked_02(self)
    def svjButtonClicked_03(self): svj_button_clicked_03(self)
    def svjButtonClicked_04(self): svj_button_clicked_04(self)
    def svjButtonClicked_05(self): svj_button_clicked_05(self)
    def svjButtonClicked_06(self): svj_button_clicked_06(self)
    def svjButtonClicked_07(self): svj_button_clicked_07(self)
    def svjButtonClicked_08(self): svj_button_clicked_08(self)
    def svjButtonClicked_09(self): svj_button_clicked_09(self)
    def svjButtonClicked_10(self): svj_button_clicked_10(self)
    def svjButtonClicked_11(self): svj_button_clicked_11(self)
    def svjButtonClicked_12(self): svj_button_clicked_12(self)
    def svjButtonClicked_13(self): svj_button_clicked_13(self)
    def svjButtonClicked_14(self, back_name): svj_button_clicked_14(self, back_name)
    def svjButtonClicked_15(self, back_name): svj_button_clicked_15(self, back_name)
    def svjButtonClicked_16(self, back_name): svj_button_clicked_16(self, back_name)
    def svjButtonClicked_17(self, back_name): svj_button_clicked_17(self, back_name)
    def svjButtonClicked_18(self): svj_button_clicked_18(self)
    def svjButtonClicked_19(self): svj_button_clicked_19(self)
    def svjButtonClicked_20(self): svj_button_clicked_20(self)
    def svjButtonClicked_21(self): svj_button_clicked_21(self)
    def svjButtonClicked_22(self): svj_button_clicked_22(self)
    # =================================================================================================================
    def svjsButtonClicked_01(self): svjs_button_clicked_01(self)
    def svjsButtonClicked_02(self): svjs_button_clicked_02(self)
    def svjsButtonClicked_03(self): svjs_button_clicked_03(self)
    def svjsButtonClicked_04(self): svjs_button_clicked_04(self)
    def svjsButtonClicked_05(self): svjs_button_clicked_05(self)
    def svjsButtonClicked_06(self): svjs_button_clicked_06(self)
    def svjsButtonClicked_07(self): svjs_button_clicked_07(self)
    def svjsButtonClicked_08(self): svjs_button_clicked_08(self)
    def svjsButtonClicked_09(self): svjs_button_clicked_09(self)
    def svjsButtonClicked_10(self): svjs_button_clicked_10(self)
    def svjsButtonClicked_11(self): svjs_button_clicked_11(self)
    def svjsButtonClicked_12(self): svjs_button_clicked_12(self)
    def svjsButtonClicked_13(self): svjs_button_clicked_13(self)
    def svjsButtonClicked_14(self): svjs_button_clicked_14(self)
    # =================================================================================================================
    def svcButtonClicked_01(self): svc_button_clicked_01(self)
    def svcButtonClicked_02(self): svc_button_clicked_02(self)
    def svcButtonClicked_03(self): svc_button_clicked_03(self)
    def svcButtonClicked_04(self): svc_button_clicked_04(self)
    def svcButtonClicked_05(self): svc_button_clicked_05(self)
    def svcButtonClicked_06(self): svc_button_clicked_06(self)
    def svcButtonClicked_07(self): svc_button_clicked_07(self)
    def svcButtonClicked_08(self): svc_button_clicked_08(self)
    def svcButtonClicked_09(self): svc_button_clicked_09(self)
    def svcButtonClicked_10(self): svc_button_clicked_10(self)
    def svcButtonClicked_11(self): svc_button_clicked_11(self)
    # =================================================================================================================
    def svaButtonClicked_01(self): sva_button_clicked_01(self)
    def svaButtonClicked_02(self): sva_button_clicked_02(self)
    # =================================================================================================================
    def svoButtonClicked_01(self): svo_button_clicked_01(self)
    def svoButtonClicked_02(self): svo_button_clicked_02(self)
    def svoButtonClicked_03(self): svo_button_clicked_03(self)
    def svoButtonClicked_04(self): svo_button_clicked_04(self)
    # =================================================================================================================
    def cvjbButtonClicked_01(self): cvjb_button_clicked_01(self)
    def cvjbButtonClicked_02(self): cvjb_button_clicked_02(self)
    def cvjbButtonClicked_03(self): cvjb_button_clicked_03(self)
    def cvjbButtonClicked_04(self): cvjb_button_clicked_04(self)
    def cvjbButtonClicked_05(self): cvjb_button_clicked_05(self)
    def cvjbButtonClicked_06(self): cvjb_button_clicked_06(self)
    def cvjbButtonClicked_07(self): cvjb_button_clicked_07(self)
    def cvjbButtonClicked_08(self): cvjb_button_clicked_08(self)
    def cvjbButtonClicked_09(self): cvjb_button_clicked_09(self)
    def cvjbButtonClicked_10(self): cvjb_button_clicked_10(self)
    def cvjbButtonClicked_11(self): cvjb_button_clicked_11(self)
    def cvjbButtonClicked_12(self): cvjb_button_clicked_12(self)
    # =================================================================================================================
    def cvjButtonClicked_01(self): cvj_button_clicked_01(self)
    def cvjButtonClicked_02(self): cvj_button_clicked_02(self)
    def cvjButtonClicked_03(self): cvj_button_clicked_03(self)
    def cvjButtonClicked_04(self): cvj_button_clicked_04(self)
    def cvjButtonClicked_05(self): cvj_button_clicked_05(self)
    def cvjButtonClicked_06(self): cvj_button_clicked_06(self)
    def cvjButtonClicked_07(self): cvj_button_clicked_07(self)
    def cvjButtonClicked_08(self): cvj_button_clicked_08(self)
    def cvjButtonClicked_09(self): cvj_button_clicked_09(self)
    def cvjButtonClicked_10(self): cvj_button_clicked_10(self)
    def cvjButtonClicked_11(self): cvj_button_clicked_11(self)
    def cvjButtonClicked_12(self): cvj_button_clicked_12(self)
    def cvjButtonClicked_13(self): cvj_button_clicked_13(self)
    def cvjButtonClicked_14(self, back_name): cvj_button_clicked_14(self, back_name)
    def cvjButtonClicked_15(self, back_name): cvj_button_clicked_15(self, back_name)
    def cvjButtonClicked_16(self, back_name): cvj_button_clicked_16(self, back_name)
    def cvjButtonClicked_17(self, back_name): cvj_button_clicked_17(self, back_name)
    def cvjButtonClicked_18(self): cvj_button_clicked_18(self)
    def cvjButtonClicked_19(self): cvj_button_clicked_19(self)
    def cvjButtonClicked_20(self): cvj_button_clicked_20(self)
    def cvjButtonClicked_21(self): cvj_button_clicked_21(self)
    def cvjButtonClicked_22(self): cvj_button_clicked_22(self)
    # =================================================================================================================
    def cvjsButtonClicked_01(self): cvjs_button_clicked_01(self)
    def cvjsButtonClicked_02(self): cvjs_button_clicked_02(self)
    def cvjsButtonClicked_03(self): cvjs_button_clicked_03(self)
    def cvjsButtonClicked_04(self): cvjs_button_clicked_04(self)
    def cvjsButtonClicked_05(self): cvjs_button_clicked_05(self)
    def cvjsButtonClicked_06(self): cvjs_button_clicked_06(self)
    def cvjsButtonClicked_07(self): cvjs_button_clicked_07(self)
    def cvjsButtonClicked_08(self): cvjs_button_clicked_08(self)
    def cvjsButtonClicked_09(self): cvjs_button_clicked_09(self)
    def cvjsButtonClicked_10(self): cvjs_button_clicked_10(self)
    def cvjsButtonClicked_11(self): cvjs_button_clicked_11(self)
    def cvjsButtonClicked_12(self): cvjs_button_clicked_12(self)
    def cvjsButtonClicked_13(self): cvjs_button_clicked_13(self)
    def cvjsButtonClicked_14(self): cvjs_button_clicked_14(self)
    # =================================================================================================================
    def cvcButtonClicked_01(self): cvc_button_clicked_01(self)
    def cvcButtonClicked_02(self): cvc_button_clicked_02(self)
    def cvcButtonClicked_03(self): cvc_button_clicked_03(self)
    def cvcButtonClicked_04(self): cvc_button_clicked_04(self)
    def cvcButtonClicked_05(self): cvc_button_clicked_05(self)
    def cvcButtonClicked_06(self): cvc_button_clicked_06(self)
    def cvcButtonClicked_07(self): cvc_button_clicked_07(self)
    def cvcButtonClicked_08(self): cvc_button_clicked_08(self)
    def cvcButtonClicked_09(self): cvc_button_clicked_09(self)
    def cvcButtonClicked_10(self): cvc_button_clicked_10(self)
    def cvcButtonClicked_11(self): cvc_button_clicked_11(self)
    # =================================================================================================================
    def cvaButtonClicked_01(self): cva_button_clicked_01(self)
    def cvaButtonClicked_02(self): cva_button_clicked_02(self)
    def cvoButtonClicked_01(self): cvo_button_clicked_01(self)
    def cvoButtonClicked_02(self): cvo_button_clicked_02(self)
    def cvoButtonClicked_03(self): cvo_button_clicked_03(self)
    def cvoButtonClicked_04(self): cvo_button_clicked_04(self)
    # =================================================================================================================
    def BackTestengineShow(self, gubun):                 backengine_show(self, gubun)
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
    def setButtonClicked_01(self): set_button_clicked_01(self)
    def setButtonClicked_02(self): set_button_clicked_02(self)
    def setButtonClicked_03(self): set_button_clicked_03(self)
    def cetButtonClicked_01(self): cet_button_clicked_01(self)
    def cetButtonClicked_02(self): cet_button_clicked_02(self)
    def cetButtonClicked_03(self): cet_button_clicked_03(self)
    # =================================================================================================================
    def StomLiveProcessAlive(self):     return stom_live_process_alive(self)
    def CoinReceiverProcessAlive(self): return coin_receiver_process_alive(self)
    def CoinTraderProcessAlive(self):   return coin_trader_process_alive(self)
    def CoinStrategyProcessAlive(self): return coin_strategy_process_alive(self)
    def CoinKimpProcessAlive(self):     return coinkimp_process_alive(self)
    def BacktestProcessAlive(self):     return backtest_process_alive(self)
    # =================================================================================================================
    def keyPressEvent(self, event):              key_press_event(self, event)
    def eventFilter(self, widget, event): return event_filter(self, widget, event)
    def closeEvent(self, a):                     close_event(self, a)
    # =================================================================================================================
    def ProcessKill(self):                       process_kill(self)
    # =================================================================================================================
