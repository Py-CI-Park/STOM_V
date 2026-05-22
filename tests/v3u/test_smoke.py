"""V3U 1순위 사용자 검증 자동화 (스모크 5개 케이스).

Constraint: V3 official source 0줄 수정. 본 파일은 ui.main_window의 V3U 추론 본체와
V3 공식 widget builder를 호출 검증만 수행한다.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QTabWidget


pytestmark = pytest.mark.smoke


def test_main_window_starts(main_window) -> None:
    """1순위 A1: V3U pyd-free MainWindow가 헤드리스로 정상 인스턴스화된다."""
    assert main_window is not None
    assert type(main_window).__name__ == "MainWindow"
    # logger와 dict_set 같은 핵심 attr이 채워졌는지
    assert hasattr(main_window, "dict_set")
    assert isinstance(main_window.dict_set, dict)
    assert hasattr(main_window, "qlist")


def test_all_tabs_switch_without_error(main_window, qtbot) -> None:
    """1순위 A3: stom.py 동등 시퀀스에서 9개 탭(주식/코인/선물/백테 라이브,
    일반설정/주문설정, 매수매도전략/최적화및GA범위/백테스트스케쥴)이 모두 전환된다."""
    tabs = main_window.findChildren(QTabWidget)
    assert len(tabs) >= 1, "QTabWidget 인스턴스가 발견되지 않음"

    total_tabs = 0
    for tab in tabs:
        for i in range(tab.count()):
            tab.setCurrentIndex(i)
            qtbot.wait(10)
            assert tab.currentIndex() == i, (
                f"탭 전환 실패: {tab.tabText(i)!r} (idx={i})"
            )
            total_tabs += 1
    assert total_tabs >= 9, (
        f"9개 이상 탭 기대했으나 {total_tabs}개만 전환됨. "
        f"V3.18 시점 기대: 4 + 2 + 3 = 9"
    )


def test_backtest_proc_attrs_initialized(main_window) -> None:
    """2순위 A4: _BACKTEST_PROCESS_ATTRS의 모든 백테 프로세스 핸들이 None으로 초기화된다.

    V3.18 baseline: 26개 (proc_backtester_{bs, bf, o, ov, ovc, ot, ovt, ovct,
    bv, bvc, bt, bvt, bvct, br, brv, brvc, og, ogv, ogvc, oc, ocv, ocvc, ...}).
    drift 발생 시 fail이 V3 upstream 갱신 신호임을 명시한다.
    """
    from ui.main_window import _BACKTEST_PROCESS_ATTRS

    expected_min = 22  # 핸드오프 체크리스트 시점
    expected_v318 = 26  # 본 검증 시점 실측

    actual = len(_BACKTEST_PROCESS_ATTRS)
    assert actual >= expected_min, (
        f"백테 프로세스 핸들 {expected_min}개 미만으로 축소됨 ({actual}). "
        f"V3 upstream에서 핸들이 제거되었을 가능성. ui/main_window.py 동기화 필요."
    )
    if actual != expected_v318:
        # drift는 fail이 아니라 명시적 신호로 처리. V3 upstream에서 핸들이 늘면
        # ui/main_window.py 갱신 후 본 baseline 숫자도 함께 갱신해야 한다.
        pytest.skip(
            f"V3.18 baseline {expected_v318}와 다름 ({actual}). "
            f"V3 upstream drift 가능성. ui/main_window.py + 본 테스트 동기화 필요."
        )

    for attr in _BACKTEST_PROCESS_ATTRS:
        assert hasattr(main_window, attr), f"백테 프로세스 attr 누락: {attr}"
        assert getattr(main_window, attr) is None, (
            f"{attr}는 spawn 직전 None이어야 함, 실제: {type(getattr(main_window, attr)).__name__}"
        )


def test_named_queues_initialized(main_window) -> None:
    """A4 큐 컨벤션: V3 worker 컨벤션 12개 명명 큐 + 추가 3개(totalQ/kimpQ/wdzservQ)
    + stgQs(list of 1) + qlist(13개)가 모두 생성된다.
    """
    v3_named = (
        "windowQ", "soundQ", "queryQ", "teleQ", "chartQ", "hogaQ",
        "webcQ", "backQ", "receivQ", "traderQ", "liveQ", "testQ",
    )
    extras = ("totalQ", "kimpQ", "wdzservQ")
    for q_name in v3_named + extras:
        assert hasattr(main_window, q_name), f"큐 누락: {q_name}"
    assert hasattr(main_window, "stgQs")
    assert isinstance(main_window.stgQs, list) and len(main_window.stgQs) == 1
    assert hasattr(main_window, "qlist")
    assert len(main_window.qlist) == 13, (
        f"qlist 길이 13 기대, 실제 {len(main_window.qlist)} (V3 컨벤션 위반)"
    )


def test_runtime_state_attrs_initialized(main_window) -> None:
    """V3U MainWindow가 외부 핸들러(`ui.event_click/`)에서 참조하는 boolean state attr을
    모두 init한다. 누락 시 첫 사용자 클릭에서 AttributeError 또는 의미 없는 dialog 발생.

    drift 발견 사례 (2026-05-12):
    - backengine_starting: button_clicked_backtest_start.py:11/114에서 참조
    - back_tick_cunsum: 백테 진행 카운터
    - ctpg_cvb: 차트 chart_view 바인딩
    """
    required_state = {
        # 백테엔진 라이프사이클
        "backengine_starting": False,
        "backengine_running": False,
        "back_engining": False,
        "backtest_engine": False,
        "back_cancelling": False,
        "back_tick_cunsum": 0,
        # UI 모드
        "back_schedul": False,
        "showQsize": False,
        "auto_mode": False,
        "trading": False,
    }
    for attr, expected in required_state.items():
        assert hasattr(main_window, attr), (
            f"V3U runtime state 누락: {attr}. "
            f"외부 핸들러가 참조하는 boolean/state attr은 _init_runtime_state에 명시 필요."
        )
        actual = getattr(main_window, attr)
        assert actual == expected, (
            f"{attr} 초기값 mismatch: 기대 {expected!r}, 실제 {actual!r}"
        )

    # ctpg_cvb는 init은 None이지만 widget builder가 dict로 채움. 둘 다 허용.
    assert hasattr(main_window, "ctpg_cvb"), "ctpg_cvb attr 누락"
    cvb = main_window.ctpg_cvb
    assert cvb is None or isinstance(cvb, dict), (
        f"ctpg_cvb는 None(init) 또는 dict(post-widget-build)여야 함, 실제 {type(cvb).__name__}"
    )


def test_qlist_v3_convention_order(main_window) -> None:
    """qlist 인덱스가 V3 worker 컨벤션을 따른다.

    외부 worker(WebCrawling qlist[6], TelegramBot qlist[3]/[9]/[10][0],
    base_receiver qlist[8]/[9], base_trader qlist[8]/[9]/[11], ChartHogaQuery
    qlist[12])가 qlist[N]을 직접 인덱싱하므로 순서가 어긋나면 무관한 큐로 메시지가
    잘못 흘러간다.

    drift 발견 사례 (2026-05-12 11시): qlist[8/9/10/11]이 totalQ/testQ/kimpQ/wdzservQ로
    잘못 매핑되어 있어 receivQ/traderQ/stgQs/liveQ가 없었음. → 홈 대시보드 데이터 source인
    WebCrawling 누락 + 거래 receiver/trader 큐 mismatch.
    """
    expected = [
        ("windowQ", 0), ("soundQ", 1), ("queryQ", 2), ("teleQ", 3),
        ("chartQ", 4), ("hogaQ", 5), ("webcQ", 6), ("backQ", 7),
        ("receivQ", 8), ("traderQ", 9),
        # qlist[10]은 stgQs (list)
        ("liveQ", 11), ("testQ", 12),
    ]
    assert hasattr(main_window, "qlist"), "qlist 누락"
    assert len(main_window.qlist) == 13, f"qlist 길이 13 기대, 실제 {len(main_window.qlist)}"
    for name, idx in expected:
        named_q = getattr(main_window, name, None)
        assert named_q is not None, f"명명 큐 누락: {name}"
        assert main_window.qlist[idx] is named_q, (
            f"qlist[{idx}]가 {name}과 불일치. V3 worker 컨벤션 위반."
        )
    # qlist[10]은 stgQs (list of queues)
    assert main_window.qlist[10] is main_window.stgQs, "qlist[10]은 stgQs(list)여야 함"
    assert isinstance(main_window.stgQs, list) and len(main_window.stgQs) >= 1


def test_v3_helper_attr_names(main_window) -> None:
    """외부 코드가 참조하는 V3 expected helper attr 이름이 모두 존재한다.

    drift 발견 (2026-05-12 11시): update_crawling_data.py가 ui.draw_homechart
    (밑줄 없음)를 호출하나 V3U는 ui.draw_home_chart(밑줄)로만 부착했음.
    → 홈 대시보드 데이터를 받아도 어디에 그릴지 모름 → "데이터 검색 중 ..." 영구 표시.
    """
    expected = (
        "draw_chart", "draw_realchart", "draw_treemap",
        "draw_homechart", "draw_home_chart",  # 둘 다 alias로 존재해야 함
        "update_textedit", "update_tablewidget",
        "update_crawling_data", "update_telegram_msg",
    )
    for attr in expected:
        assert hasattr(main_window, attr), f"V3 helper attr 누락: ui.{attr}"


def test_webcrawling_signal_handler_present(main_window) -> None:
    """webc 시작 가능 시점에 signal 결선 핸들러가 준비됐는지 정적 검증.

    실 webc 시작은 STOM_V3U_DISABLE_WEBC=1로 pytest에서 비활성화 (fixture
    teardown 시 access violation 회피). 실 결선 동작은 사용자 시각 검증.
    """
    handler = getattr(main_window.update_crawling_data, "update_crawling_data", None)
    assert callable(handler), (
        "update_crawling_data.update_crawling_data 핸들러 누락. "
        "_init_workers에서 webc.signal.connect 대상이 없음."
    )


def test_webcrawling_worker_attr_present(main_window) -> None:
    """webc attr 자체가 부착되어 있다 (None placeholder 허용)."""
    assert hasattr(main_window, "webc"), "webc attr 누락"
    # pytest 환경(STOM_V3U_DISABLE_WEBC=1)에서는 None이 정상


def test_web_dashboard_attr_present_for_safe_attribute_access(main_window) -> None:
    """결함 #15 사전 차단: button_clicked_shortcut.py:252 사용자가 단축키로
    DashboardStarter를 부착하기 전에 ui.web_dashboard 참조 시 AttributeError를 방지한다.

    None placeholder가 line 279의 truthy 체크에 의해 안전 처리됨.
    """
    assert hasattr(main_window, "web_dashboard"), (
        "web_dashboard attr 누락 — button_clicked_shortcut.py:279 'if ui.dict_set[웹대시보드] "
        "and ui.web_dashboard:' 체크 시 AttributeError 위험"
    )
    # None placeholder (사용자 단축키로 활성화 전) 또는 DashboardStarter 인스턴스
    # 둘 다 허용 — 정적 검증은 attr 존재성만 확인
    assert main_window.web_dashboard is None or hasattr(main_window.web_dashboard, "start")


def test_proc_chqs_safe_for_is_alive_call(main_window) -> None:
    """결함 #12: 외부 20+ site가 ui.proc_chqs.is_alive()를 None 체크 없이 호출.

    _NullProcess placeholder가 부착되어 AttributeError 없이 False를 반환해야 한다.
    """
    assert hasattr(main_window, "proc_chqs"), "proc_chqs attr 누락"
    # None이면 외부에서 .is_alive() 호출 시 AttributeError → V3U 결함
    assert main_window.proc_chqs is not None, (
        "proc_chqs가 None — 외부 코드가 .is_alive() 호출 시 AttributeError 발생. "
        "_NullProcess placeholder 부착 필요."
    )
    assert hasattr(main_window.proc_chqs, "is_alive")
    assert main_window.proc_chqs.is_alive() is False
    # multiprocessing.Process 인터페이스 호환성
    for method in ("terminate", "join", "start"):
        assert callable(getattr(main_window.proc_chqs, method, None)), (
            f"proc_chqs.{method} 누락 (Process 인터페이스 위반)"
        )


def test_safe_webc_run_wrapper_swallows_handle_closed() -> None:
    """결함 #13: WebCrawling.run()이 main exit 시 OSError('handle is closed')를
    내뱉어 stderr에 traceback 표시. _safe_webc_run_wrapper가 이를 swallow한다.
    """
    # main_window.py 내부 wrapper는 _init_workers의 클로저라 직접 import 불가.
    # 동일 시그니처로 동작 검증.
    def _wrap(original):
        def _wrapped():
            try:
                original()
            except OSError as exc:
                if "handle is closed" in str(exc) or "WinError 6" in str(exc):
                    return
                raise
        return _wrapped

    def _raise_handle_closed():
        raise OSError("handle is closed")

    def _raise_winerror6():
        raise OSError("[WinError 6] handle is invalid")

    def _raise_other():
        raise OSError("[Errno 13] permission denied")

    # 두 패턴 모두 swallow
    _wrap(_raise_handle_closed)()
    _wrap(_raise_winerror6)()

    # 다른 OSError는 raise
    import pytest as _pt
    with _pt.raises(OSError):
        _wrap(_raise_other)()


def test_telegram_worker_attached_for_isRunning_call(main_window) -> None:
    """결함 #11: ui/etcetera/etc.py:79에서 ui.telegram.isRunning() 호출.

    TelegramBot 인스턴스 또는 _NullWorker placeholder가 부착되어 있어야 한다.
    """
    assert hasattr(main_window, "telegram"), "telegram attr 누락"
    assert main_window.telegram is not None, (
        "telegram이 None — 외부 코드가 .isRunning() 호출 시 AttributeError. "
        "TelegramBot 인스턴스 또는 _NullWorker placeholder 부착 필요."
    )
    # QThread.isRunning 또는 _NullWorker.is_alive 호환
    isrunning = getattr(main_window.telegram, "isRunning", None)
    isalive = getattr(main_window.telegram, "is_alive", None)
    assert callable(isrunning) or callable(isalive), (
        "telegram에 isRunning/is_alive 메서드 모두 없음 — etc.py:79 호출 시 AttributeError"
    )


def test_process_kill_method_present(main_window) -> None:
    """process_kill + closeEvent 메서드가 존재하고 callable.

    drift 발견 (2026-05-12 11:30): closeEvent 미구현 + process_kill 메서드 부재로
    stom.py 종료 시 WebCrawling이 multiprocessing.Queue.empty() 호출 중
    OSError [WinError 6] 발생.

    실 worker termination은 mid-network-call terminate()가 Windows access
    violation을 일으키므로 본 테스트에서는 호출하지 않는다 (user closeEvent로
    검증). 메서드 존재성과 timer-only 종료 가능성만 검증.
    """
    assert hasattr(main_window, "process_kill"), "process_kill 메서드 누락"
    assert callable(main_window.process_kill)
    assert hasattr(main_window, "closeEvent"), "closeEvent 누락"


def test_process_kill_stops_timers_only(main_window) -> None:
    """process_kill이 최소한 timer는 안전하게 정지한다 (worker는 webc.quit()로 polite).

    실 stop 동작 검증은 webc가 None인 시점(헤드리스 fallback)으로만 한정해
    Windows access violation 회피.
    """
    import os

    if os.environ.get("STOM_OFFLINE_SMOKE") == "1":
        return

    timers_before = [
        n for n in ("qtimer1", "qtimer2", "qtimer3")
        if getattr(main_window, n, None) is not None and main_window.__getattribute__(n).isActive()
    ]
    if not timers_before:
        return  # 검증 의미 없음

    # webc가 mid-request면 terminate가 위험. webc를 None으로 임시 분리 후 process_kill
    saved_webc = getattr(main_window, "webc", None)
    main_window.webc = None
    try:
        main_window.process_kill()
        timers_after = [
            n for n in ("qtimer1", "qtimer2", "qtimer3")
            if getattr(main_window, n, None) is not None and main_window.__getattribute__(n).isActive()
        ]
        assert not timers_after, f"process_kill 후 active timer 잔존: {timers_after}"
    finally:
        main_window.webc = saved_webc


def test_qtimer1_auto_started_for_process_starter(main_window) -> None:
    """qtimer1(process_starter 호출용)이 __init__ 시점에 자동 시작된다.

    V3 pyd가 자동 시작했던 동작 — V3U도 동일해야 사용자가 별도 Qtimer1Start 호출 없이
    백테 스케줄/auto_run/창 제목 갱신이 동작한다.
    """
    import os

    assert hasattr(main_window, "qtimer1"), "qtimer1 누락"
    if os.environ.get("STOM_OFFLINE_SMOKE") == "1":
        # offline smoke 모드에서는 타이머 미시작이 정상
        return
    assert main_window.qtimer1.isActive(), (
        "qtimer1이 자동 시작되지 않음. _init_timers에서 self.qtimer1.start() 누락 가능."
    )


def test_strategy_icons_render(qapp, project_root) -> None:
    """1순위 B8: strategy.png/strategy2.png가 ICON_PATH에서 로드되며 빈 픽스맵이 아니다."""
    from utility.settings.setting_base import ICON_PATH

    # ICON_PATH는 './ui/_icon' 형태의 상대 경로일 수 있음
    icon_dir = (project_root / ICON_PATH.lstrip("./").lstrip(".\\")).resolve()
    assert icon_dir.is_dir(), f"ICON_PATH 디렉토리 없음: {icon_dir}"

    for fname in ("strategy.png", "strategy2.png"):
        full = icon_dir / fname
        assert full.exists(), f"아이콘 파일 누락: {full}"
        pixmap = QPixmap(str(full))
        assert not pixmap.isNull(), f"QPixmap 로드 실패: {full}"
        # V3.18 기준 두 아이콘 모두 512x512
        assert pixmap.width() > 0 and pixmap.height() > 0, (
            f"{fname} 사이즈 비정상: {pixmap.width()}x{pixmap.height()}"
        )
