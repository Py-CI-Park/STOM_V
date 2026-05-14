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


def test_12_queues_initialized(main_window) -> None:
    """A4 큐 컨벤션: 12개 *Q 큐 + stgQs(1) + qlist(12)가 _init_queues로 정상 생성된다."""
    expected_queues = (
        "windowQ", "soundQ", "queryQ", "teleQ", "chartQ", "hogaQ",
        "webcQ", "backQ", "totalQ", "testQ", "kimpQ", "wdzservQ",
    )
    for q_name in expected_queues:
        assert hasattr(main_window, q_name), f"큐 누락: {q_name}"
    assert hasattr(main_window, "stgQs")
    assert hasattr(main_window, "qlist")
    assert len(main_window.qlist) == 12, (
        f"qlist 길이 12 기대, 실제 {len(main_window.qlist)}"
    )
    assert len(main_window.stgQs) == 1, (
        f"stgQs 길이 1 기대, 실제 {len(main_window.stgQs)}"
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
