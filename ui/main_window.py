"""V3U pyd-free MainWindow entry point.

This module replaces the upstream ``ui/main_window.pyd`` extension only in the
V3U lane.  The official V3 lane must keep the upstream pyd intact.  The class is
kept intentionally close to the V3 Python package boundaries: widget builders,
event handlers, update helpers, chart drawers, and etcetera helpers remain in
their existing V3 modules and are imported lazily from ``__init__``/wrapper
methods.
"""

from __future__ import annotations

import logging
import os
from multiprocessing import Queue
from typing import Any, Callable

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow


_BACKTEST_PROCESS_ATTRS = (
    "proc_backtester_bs",
    "proc_backtester_bf",
    "proc_backtester_o",
    "proc_backtester_ov",
    "proc_backtester_ovc",
    "proc_backtester_ot",
    "proc_backtester_ovt",
    "proc_backtester_ovct",
    "proc_backtester_or",
    "proc_backtester_orv",
    "proc_backtester_orvc",
    "proc_backtester_b",
    "proc_backtester_bv",
    "proc_backtester_bvc",
    "proc_backtester_bt",
    "proc_backtester_bvt",
    "proc_backtester_bvct",
    "proc_backtester_br",
    "proc_backtester_brv",
    "proc_backtester_brvc",
    "proc_backtester_og",
    "proc_backtester_ogv",
    "proc_backtester_ogvc",
    "proc_backtester_oc",
    "proc_backtester_ocv",
    "proc_backtester_ocvc",
)


class _NullQueue:
    """Small queue-compatible fallback used when multiprocessing queues fail."""

    def put(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def get(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def qsize(self) -> int:
        return 0


class _NullWorker:
    """Signal/worker fallback for side-effect-safe offline construction."""

    def start(self) -> None:
        return None

    def terminate(self) -> None:
        return None

    def is_alive(self) -> bool:
        return False


class MainWindow(QMainWindow):
    """V3 MainWindow import contract implemented in Python for V3U.

    The upstream V3 application imports ``MainWindow`` from ``ui.main_window``.
    In the official V3 lane that name resolves to ``main_window.pyd``.  In V3U it
    resolves to this pyd-free Python class while preserving the same high-level
    construction sequence and runtime attributes that V3 UI modules expect.
    """

    def __init__(self, auto_run: int = 0, splash: Any | None = None):
        super().__init__()
        self.splash = splash
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log = self.logger
        # V3U lane: runtime 에러를 사용자 cmd 창에서 직접 볼 수 있도록 stderr 핸들러를
        # 한 번만 부착한다. 헤드리스 테스트 환경에서는 pytest가 캡처한다.
        if not any(
            isinstance(h, logging.StreamHandler) and getattr(h, "_v3u_console", False)
            for h in logging.getLogger().handlers
        ):
            _console = logging.StreamHandler()
            _console.setLevel(logging.INFO)
            _console.setFormatter(
                logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
                                   datefmt="%H:%M:%S")
            )
            setattr(_console, "_v3u_console", True)
            logging.getLogger().addHandler(_console)
            logging.getLogger().setLevel(logging.INFO)

        self.auto_run = auto_run
        self._offline_smoke = os.environ.get("STOM_OFFLINE_SMOKE") == "1"
        self._strict_widget_build = os.environ.get("STOM_V3U_STRICT_WIDGET_BUILD") == "1"
        self._widget_build_error: str | None = None
        self._missing_slot_calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.logger.info("V3U MainWindow boot: auto_run=%s, offline=%s", auto_run, self._offline_smoke)

        self._init_queues()
        self._init_runtime_state()
        self._load_user_settings()
        self._init_market_state()
        self._build_v3_widgets()
        self._init_update_and_chart_helpers()
        self._init_timers()
        self._init_workers()

        if splash is not None and hasattr(splash, "finish_splash"):
            splash.finish_splash()

        if os.environ.get("STOM_V3U_SHOW_MAINWINDOW", "1") != "0":
            self.show()

    # -----------------------------------------------------------------------------------------------------------------
    # Initialization boundaries
    # -----------------------------------------------------------------------------------------------------------------
    def _make_queue(self) -> Queue | _NullQueue:
        try:
            return Queue()
        except Exception:
            self.logger.exception("failed to create multiprocessing Queue; using null queue")
            return _NullQueue()

    def _init_queues(self) -> None:
        # V3 worker 컨벤션 큐 (인덱스 0~12). 외부 worker(WebCrawling, ChartHogaQuery,
        # TelegramBot, base_receiver, base_trader, base_strategy)가 qlist[N]을 직접
        # 인덱싱하므로 순서가 정확해야 한다.
        # 0:windowQ 1:soundQ 2:queryQ 3:teleQ 4:chartQ 5:hogaQ 6:webcQ 7:backQ
        # 8:receivQ 9:traderQ 10:stgQs(list) 11:liveQ 12:testQ
        v3_names = (
            "windowQ", "soundQ", "queryQ", "teleQ",
            "chartQ", "hogaQ", "webcQ", "backQ",
            "receivQ", "traderQ",
            # stgQs는 인덱스 10에 list로 들어감 (worker가 qlist[10][0] 참조)
            "liveQ", "testQ",
        )
        for name in v3_names:
            setattr(self, name, self._make_queue())
        self.stgQs = [self._make_queue()]
        # qlist V3 컨벤션 정확한 순서
        self.qlist = [
            self.windowQ, self.soundQ, self.queryQ, self.teleQ,
            self.chartQ, self.hogaQ, self.webcQ, self.backQ,
            self.receivQ, self.traderQ,
            self.stgQs,           # 인덱스 10 (list)
            self.liveQ, self.testQ,
        ]
        # V3U lane 추가 명명 큐 (qlist 인덱스 외부, 외부 코드가 ui.<name>으로 직접 access)
        for extra in ("totalQ", "kimpQ", "wdzservQ"):
            setattr(self, extra, self._make_queue())

    def _init_runtime_state(self) -> None:
        self.main_btn = 0
        self.counter = 0
        self.cpu_per = 0
        self.int_time = 0

        self.dict_name: dict[Any, Any] = {}
        self.dict_code: dict[Any, Any] = {}
        self.dict_stg_btn: dict[Any, Any] = {}
        self.dict_sgbn = None
        self.dict_cn = None
        self.dict_mt = None
        self.dict_fm: dict[Any, Any] = {}
        self.dict_fn = None
        self.dict_findex: dict[str, int] = {}

        self.dialog_list: list[Any] = []
        self.main_btn_list: list[Any] = []
        self.main_box_list: list[Any] = []
        self.home_gbox_all_list: list[Any] = []
        self.home_gbox_center_list: list[Any] = []
        self.home_gbox_left_up_list: list[Any] = []
        self.home_gbox_right_up_list: list[Any] = []
        self.home_gbox_left_down_list: list[Any] = []
        self.home_gbox_right_down_list: list[Any] = []

        self.back_schedul = False
        self.showQsize = False
        self.image_search = False
        self.auto_mode = False
        self.database_control = False
        self.ssicon_alert = False
        self.csicon_alert = False
        self.lgicon_alert = False
        self.database_chart = False
        self.data_save = False
        self.trading = False
        self.back_engining = False
        self.backengine_running = False
        self.backengine_starting = False
        self.backtest_engine = False
        self.extend_window = False
        self.back_cancelling = False
        self.back_tick_cunsum = 0
        self.ctpg_cvb = None

        self.animation = None
        self.webEngineView = None
        self.vars: dict[Any, Any] = {}
        self.buy_index: list[Any] = []
        self.sell_index: list[Any] = []
        self.back_eprocs: list[Any] = []
        self.back_eques: list[Any] = []
        self.back_sprocs: list[Any] = []
        self.back_sques: list[Any] = []
        self.shared_cnt = None
        self.shared_lock = None
        self.shared_info: list[Any] = []
        self.avg_list: list[Any] = []
        self.back_count = 0
        self.back_scount = 0
        self.multi = 0
        self.divide_mode = str
        self.back_start_time = None
        self.optuna_current_cnt = 0
        self.optuna_remain_cnt = 0
        self.backengin_window_open = False
        self.optuna_window_open = False
        self.stg_btn_number = 1
        self.backdetail_list = None
        self.backcheckbox_list = None
        self.order_combo_name_list: list[Any] = []
        self.fm_list: list[Any] = []
        self.fm_tcnt = 0

        self.proc_receiver = None
        self.proc_trader = None
        self.proc_strategys: list[Any] = []
        self.proc_coin_kimp = None
        self.proc_tele = None
        self.proc_chqs = None
        self.proc_livec = None
        self.proc_manager = None
        for attr in _BACKTEST_PROCESS_ATTRS:
            setattr(self, attr, None)

        self.ctpg_code = None
        self.ctpg_name = None
        self.ctpg_cline = None
        self.ctpg_hline = None
        self.ctpg_xticks = None
        self.ctpg_arry = None
        self.ctpg_last_candlestick = None
        self.ctpg_last_volumebar = None
        self.ctpg_last_xtick = None
        self.ctpg_legend: dict[Any, Any] = {}
        self.ctpg_item: dict[Any, Any] = {}
        self.ctpg_data: dict[Any, Any] = {}
        self.ctpg_factors: list[Any] = []
        self.ctpg_labels: list[Any] = []
        self.ctpg: list[Any] = []

        self.saqsize = 0
        self.srqsize = 0
        self.stqsize = 0
        self.ssqsize = 0
        self.df_kp = None
        self.df_kd = None
        self.canvas = None
        self.tm_ax1 = None
        self.tm_ax2 = None
        self.df_tm1 = None
        self.df_tm2 = None
        self.tm_cl1 = None
        self.tm_cl2 = None
        self.tm_dt = False
        self.tm_mc1 = 0
        self.tm_mc2 = 0
        self.port_num = 5100

    def _load_user_settings(self) -> None:
        default = self._default_settings()
        try:
            from utility.settings.setting_user import load_settings

            loaded, _location_list = load_settings()
            self.dict_set = loaded if isinstance(loaded, dict) else default
        except Exception:
            self.logger.exception("failed to load user settings; using safe defaults")
            self.dict_set = default

    def _default_settings(self) -> dict[str, Any]:
        return {
            "거래소": "국내주식01",
            "타임프레임": 0,
            "데이터저장": False,
            "모의투자": True,
            "알림소리": False,
            "백테스케쥴실행": False,
            "백테스케쥴요일": 0,
            "백테스케쥴시간": 0,
            "백테스케쥴명": "",
            "매수전략": "",
            "매도전략": "",
            "전략종료시간": 153000,
            "투자금": 20.0,
            "백테날짜고정": False,
            "백테날짜": "1",
            "창위치기억": False,
            "창위치": [["0", "0"] for _ in range(20)],
            "테마": "다크레드",
            "저해상도": False,
            "스톰라이브": False,
            "웹대시보드": False,
            "웹대시보드포트번호": 5100,
            "프로그램종료": False,
            "휴무프로세스종료": False,
            "휴무컴퓨터종료": False,
            "팩터선택": "",
            "보조지표설정": [],
            "백테엔진프로파일링": False,
        }

    def _init_market_state(self) -> None:
        try:
            from utility.settings.setting_market import DICT_MARKET_GUBUN, DICT_MARKET_INFO

            self.market_gubun = DICT_MARKET_GUBUN.get(self.dict_set.get("거래소"), 1)
            self.market_info = DICT_MARKET_INFO.get(self.market_gubun, next(iter(DICT_MARKET_INFO.values())))
        except Exception:
            self.logger.exception("failed to load market settings; using safe market defaults")
            self.market_gubun = 1
            self.market_info = {
                "마켓이름": "국내주식",
                "마켓구분": "stock",
                "전략구분": "stock",
                "시작시간": 90000,
                "프로세스종료시간": 153030,
                "팩터목록": {0: [], 1: []},
                "팩터개수": {0: 0, 1: 0},
            }

        factors = self.market_info.get("팩터목록", {}).get(self.dict_set.get("타임프레임", 0), [])
        self.dict_findex = {name: index for index, name in enumerate(factors)}

    def _build_v3_widgets(self) -> None:
        if os.environ.get("STOM_V3U_SKIP_WIDGET_BUILD") == "1":
            return
        try:
            from ui.create_widget.set_dialog_back import SetDialogBack
            from ui.create_widget.set_dialog_chart import SetDialogChart
            from ui.create_widget.set_dialog_etc import SetDialogEtc
            from ui.create_widget.set_dialog_formula import SetDialogFormula
            from ui.create_widget.set_dialog_strategy import SetDialogStrategy
            from ui.create_widget.set_home_tap import SetHomeTap
            from ui.create_widget.set_icon import SetIcon
            from ui.create_widget.set_log_tap import SetLogTap
            from ui.create_widget.set_main_menu import SetMainMenu
            from ui.create_widget.set_order_tap import SetOrderTap
            from ui.create_widget.set_setup_tap import SetSetupTap
            from ui.create_widget.set_stg_tap import SetStrategyTab
            from ui.create_widget.set_table import SetTable
            from ui.create_widget.set_text_stg_button import dict_stg_button
            from ui.create_widget.set_widget import WidgetCreater

            self.dict_stg_btn = dict(dict_stg_button)
            self.wc = WidgetCreater(self)
            SetIcon(self)
            SetMainMenu(self, self.wc)
            SetTable(self, self.wc)
            SetStrategyTab(self, self.wc)
            SetLogTap(self, self.wc)
            SetSetupTap(self, self.wc)
            SetOrderTap(self, self.wc)
            SetDialogChart(self, self.wc)
            SetDialogEtc(self, self.wc)
            SetDialogBack(self, self.wc)
            SetDialogStrategy(self, self.wc)
            SetDialogFormula(self, self.wc)
            SetHomeTap(self, self.wc)
        except Exception as exc:
            self._widget_build_error = repr(exc)
            self.logger.exception("V3 widget build failed")
            if self._strict_widget_build:
                raise

    def _init_update_and_chart_helpers(self) -> None:
        try:
            from ui.draw_chart.draw_chart_db import DrawDBChart
            from ui.draw_chart.draw_chart_real import DrawRealChart
            from ui.draw_chart.draw_home_chart import DrawHomeChart
            from ui.draw_chart.draw_treemap import DrawTremap
            from ui.update_widget.update_tablewidget import UpdateTablewidget
            from ui.update_widget.update_textedit import UpdateTextedit
            from ui.update_widget.update_crawling_data import UpdateCrawlingData
            from ui.update_widget.update_telegram_msg import UpdateTelegramMsg

            self.update_textedit = UpdateTextedit(self)
            self.update_tablewidget = UpdateTablewidget(self)
            self.update_telegram_msg = UpdateTelegramMsg(self)
            self.update_crawling_data = UpdateCrawlingData(self)
            self.draw_chart = DrawDBChart(self)
            self.draw_realchart = DrawRealChart(self)
            self.draw_treemap = DrawTremap(self)
            # V3 expected attr 이름: draw_homechart (밑줄 없음). draw_home_chart는 alias.
            self.draw_homechart = DrawHomeChart(self)
            self.draw_home_chart = self.draw_homechart
        except Exception:
            self.logger.exception("failed to initialize update/chart helpers")
            self.update_textedit = _NullWorker()
            self.update_tablewidget = _NullWorker()
            self.update_telegram_msg = _NullWorker()
            self.update_crawling_data = _NullWorker()
            self.draw_chart = _NullWorker()
            self.draw_realchart = _NullWorker()
            self.draw_treemap = _NullWorker()
            self.draw_homechart = _NullWorker()
            self.draw_home_chart = self.draw_homechart

    def _init_timers(self) -> None:
        self.qtimer1 = QTimer(self)
        self.qtimer1.setInterval(1000)
        self.qtimer1.timeout.connect(self.ProcessStarter)

        self.qtimer2 = QTimer(self)
        self.qtimer2.setInterval(500)
        self.qtimer2.timeout.connect(self.UpdateProgressBar)

        self.qtimer3 = QTimer(self)
        self.qtimer3.setInterval(1000)
        self.qtimer3.timeout.connect(self.UpdateCpuper)

        if not self._offline_smoke:
            self.qtimer1.start()
            self.qtimer2.start()
            self.qtimer3.start()

    def _init_workers(self) -> None:
        """V3 startup worker thread/process를 시작한다.

        V3 official pyd MainWindow가 부팅 시 자동 시작했던 worker들을 V3U에서도 동일하게
        시작해 외부 핸들러가 `ui.webc.is_alive()`, `ui.proc_chqs.is_alive()` 등을 안전하게
        호출하도록 한다. 헤드리스 smoke 모드에서는 worker 시작을 건너뛰고 None placeholder
        만 부착해 외부 코드의 hasattr 검사가 통과하도록 한다.
        """
        # placeholder (외부 hasattr 검사용)
        self.webc = None
        self.proc_chqs = None
        self.proc_tele = None

        if self._offline_smoke:
            self.logger.info("offline_smoke: worker 시작 생략 (webc/proc_chqs/proc_tele = None)")
            return

        # pytest 환경에서 mid-network-call WebCrawling이 fixture teardown에서
        # Windows access violation을 일으키므로 명시적으로 비활성화 가능.
        if os.environ.get("STOM_V3U_DISABLE_WEBC") == "1":
            self.logger.info("STOM_V3U_DISABLE_WEBC=1: WebCrawling 시작 생략")
            return

        # WebCrawling: 홈 대시보드 트리맵·기업정보·풍경사진 fetch source.
        # webcQ로 ('트리맵',''), ('기업정보', code) 등을 받고, 결과는 pyqtSignal로 emit.
        # V3 official MainWindow가 했어야 할 것: webc.signal.connect로 수신 핸들러 연결.
        try:
            from utility.sub_process_and_thread.webcrawling import WebCrawling
            self.webc = WebCrawling(self.qlist)
            handler = getattr(self.update_crawling_data, "update_crawling_data", None)
            if callable(handler):
                self.webc.signal.connect(handler)
                self.logger.info("worker WebCrawling.signal connected to update_crawling_data")
            else:
                self.logger.warning("update_crawling_data 핸들러 없음 — 홈차트 데이터가 표시되지 않을 수 있음")
            self.webc.start()
            self.logger.info("worker WebCrawling 시작 OK (홈 대시보드 데이터 source)")
        except Exception as exc:
            self.logger.exception("WebCrawling 시작 실패 — 홈 대시보드 데이터가 비어있을 수 있음: %s", exc)

    # -----------------------------------------------------------------------------------------------------------------
    # Core wrappers used by timers and existing UI modules
    # -----------------------------------------------------------------------------------------------------------------
    def Qtimer1Start(self) -> None:
        self.qtimer1.start()

    # -----------------------------------------------------------------------------------------------------------------
    # Shutdown / cleanup (V3 close_event delegates here)
    # -----------------------------------------------------------------------------------------------------------------
    def process_kill(self) -> None:
        """V3 ui/event_keypress/overwrite_event_filter.py:close_event가 호출하는 shutdown hook.

        timer/worker를 안전하게 정지해 종료 시 multiprocessing.Queue 핸들 invalid OSError를
        방지한다. 향후 추가 worker(proc_chqs, proc_tele 등) 시작되면 본 메서드에 종료 호출
        추가 필요.
        """
        try:
            for tname in ("qtimer1", "qtimer2", "qtimer3"):
                t = getattr(self, tname, None)
                if t is not None and t.isActive():
                    t.stop()
            self.logger.info("process_kill: timers stopped")
        except Exception:
            self.logger.exception("process_kill: timer stop 실패")

        webc = getattr(self, "webc", None)
        if webc is not None:
            try:
                if hasattr(webc, "isRunning") and webc.isRunning():
                    # WebCrawling.run()은 while True + 네트워크 IO. mid-request
                    # terminate()는 Windows access violation 발생 가능. quit() +
                    # wait(short timeout)로 polite 종료 후 그래도 안 죽으면
                    # silent skip — main process 종료 시 OS가 cleanup 처리.
                    webc.quit()
                    if hasattr(webc, "wait"):
                        webc.wait(500)
                    if webc.isRunning():
                        self.logger.info(
                            "process_kill: webc graceful 종료 timeout — main exit에 위임"
                        )
                    else:
                        self.logger.info("process_kill: webc 종료 OK")
            except Exception:
                self.logger.exception("process_kill: webc 종료 실패")

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        """창 닫기 이벤트. V3 close_event 핸들러로 위임 (없으면 process_kill 직접 호출)."""
        try:
            from ui.event_keypress.overwrite_event_filter import close_event
            close_event(self, event)
        except Exception:
            self.logger.exception("closeEvent: V3 close_event 호출 실패 — process_kill 직접 호출")
            try:
                self.process_kill()
            finally:
                event.accept()

    def ProcessStarter(self) -> None:
        from ui.etcetera.process_starter import process_starter

        process_starter(self)

    def AutoBackSchedule(self, gubun: int) -> None:
        from ui.etcetera.process_starter import auto_back_schedule

        auto_back_schedule(self, gubun)

    def UpdateProgressBar(self) -> None:
        try:
            from ui.update_widget.update_progressbar import update_back_progressbar, update_progressbar

            update_back_progressbar(self)
            update_progressbar(self)
        except Exception:
            self.logger.debug("UpdateProgressBar skipped", exc_info=True)

    def UpdateCpuper(self) -> None:
        try:
            import psutil

            self.cpu_per = int(psutil.cpu_percent(interval=None))
        except Exception:
            self.cpu_per = 0

    def UpdateImage(self, data: Any) -> None:
        from ui.etcetera.etc import update_image

        update_image(self, data)

    def UpdateDictSet(self) -> None:
        from ui.etcetera.etc import update_dictset

        update_dictset(self)

    def ChartClear(self) -> None:
        from ui.etcetera.etc import chart_clear

        chart_clear(self)

    def CalendarClicked(self) -> None:
        from ui.etcetera.etc import calendar_clicked

        calendar_clicked(self)

    def ChartScreenShot(self) -> None:
        from ui.etcetera.etc import chart_screenshot

        chart_screenshot(self)

    def ChartScreenShot2(self) -> None:
        from ui.etcetera.etc import chart_screenshot2

        chart_screenshot2(self)

    def ChartCountChange(self) -> None:
        from ui.event_click.button_clicked_chart_count import chart_count_change

        chart_count_change(self)

    def ShowDialogGraph(self, df: Any) -> None:
        from ui.event_click.button_clicked_show_dialog import show_dialog_graph

        show_dialog_graph(self, df)

    def ShowDialog(self, code: str, name: str, tickcount: int, searchdate: str, col: int) -> None:
        from ui.event_click.button_clicked_show_dialog import show_dialog

        show_dialog(self, code, name, tickcount, searchdate, col)

    def ShowDialogWeb(self, show: bool, code: str) -> None:
        from ui.event_click.button_clicked_show_dialog import show_dialog_web

        show_dialog_web(self, show, code)

    def ShowDialogHoga(self, show: bool, code: str) -> None:
        from ui.event_click.button_clicked_show_dialog import show_dialog_hoga

        show_dialog_hoga(self, show, code)

    def ShowDialogChart(self, real: bool, code: str, tickcount: int | None = None, searchdate: str | None = None,
                        starttime: str | None = None, endtime: str | None = None, detail: Any | None = None,
                        buytimes: Any | None = None) -> None:
        from ui.event_click.button_clicked_show_dialog import show_dialog_chart

        show_dialog_chart(self, real, code, tickcount, searchdate, starttime, endtime, detail, buytimes)

    def ShowQsize(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_qsize

        show_qsize(self)

    def ShowDialogFactor(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_dialog_factor

        show_dialog_factor(self)

    def ShowChart(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_chart

        show_chart(self)

    def ShowHoga(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_hoga

        show_hoga(self)

    def ShowGiup(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_giup

        show_giup(self)

    def ShowTreemap(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_treemap

        show_treemap(self)

    def ShowDB(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_db

        show_db(self)

    def ShowBackScheduler(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_backscheduler

        show_backscheduler(self)

    def ShowKimp(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_kimp

        show_kimp(self)

    def ShowOrder(self) -> None:
        from ui.event_click.button_clicked_show_dialog import show_order

        show_order(self)

    def PutHogaCode(self, code: str) -> None:
        from ui.event_click.button_clicked_show_dialog import put_hoga_code

        put_hoga_code(self, code)

    def ChartMoneyTopList(self) -> None:
        from ui.event_click.button_clicked_chart import chart_moneytop_list

        chart_moneytop_list(self)

    def ChartSizeChange(self) -> None:
        from ui.event_click.button_clicked_chart import chart_size_change

        chart_size_change(self)

    def __getattr__(self, name: str) -> Callable[..., None]:
        """Return a guarded no-op for legacy pyd slots not yet reified.

        V3 widget builders connect many signal names that used to live inside
        the pyd.  Python-side V3 modules already own the actual behavior for the
        main buttons and dialogs.  This fallback prevents construction-time
        AttributeError for rare legacy slot names while making calls auditable in
        ``_missing_slot_calls``.
        """

        if name.startswith("__"):
            raise AttributeError(name)

        def _missing_slot(*args: Any, **kwargs: Any) -> None:
            self._missing_slot_calls.append((name, args, kwargs))
            self.logger.debug("missing legacy slot %s called", name)

        return _missing_slot


__all__ = ["MainWindow"]
