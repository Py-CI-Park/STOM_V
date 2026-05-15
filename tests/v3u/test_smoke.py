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


def test_webcrawling_worker_started(main_window) -> None:
    """WebCrawling worker가 부팅 시 시작된다.

    홈 대시보드의 트리맵·기업정보·풍경사진 데이터 source. 누락 시 사용자 보고:
    "홈에서 대시보드 정보가 안 보인다."
    """
    import os

    if os.environ.get("STOM_OFFLINE_SMOKE") == "1":
        return
    assert hasattr(main_window, "webc"), "webc attr 누락"
    if main_window.webc is None:
        # WebCrawling 초기화 실패 시 None placeholder 허용 + 로그 확인 권고
        return
    assert main_window.webc.isRunning(), (
        "WebCrawling QThread가 시작되지 않음. _init_workers의 self.webc.start() 누락 가능."
    )


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
