"""V3U 위젯 통합 테스트 (탭 시그널 / 차트 helper / 아이콘 전수).

Constraint: V3 official source 0줄 수정. 위젯 인스턴스화와 시그널 emit만 검증한다.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QTabWidget


pytestmark = pytest.mark.integration


def test_a3_tab_widget_currentChanged_signal_emits(main_window, qtbot) -> None:
    """A3 확장: setCurrentIndex 호출 시 currentChanged(int) 시그널이 emit된다."""
    tabs = main_window.findChildren(QTabWidget)
    assert tabs, "QTabWidget 인스턴스 없음"

    # 첫 번째 탭에서 시그널 emit 검증
    first = tabs[0]
    if first.count() < 2:
        pytest.skip("탭이 1개 이하라 전환 시그널 검증 불가")

    target_idx = (first.currentIndex() + 1) % first.count()
    with qtbot.waitSignal(first.currentChanged, timeout=2000) as blocker:
        first.setCurrentIndex(target_idx)
    assert blocker.args == [target_idx], (
        f"currentChanged 인자 mismatch: 기대 [{target_idx}], 실제 {blocker.args}"
    )


def test_a5_chart_helpers_callable(main_window) -> None:
    """A5: V3U MainWindow가 차트 helper 3개를 lazy import로 보유한다."""
    expected = ("draw_chart", "draw_realchart", "draw_home_chart")
    for attr in expected:
        helper = getattr(main_window, attr, None)
        assert helper is not None, f"차트 helper 누락: {attr}"
        # 핵심 메서드가 callable인지 (call까지는 안 함 — 데이터 의존성)
        for method_name in ("clear", "draw") if attr != "draw_home_chart" else ("clear",):
            method = getattr(helper, method_name, None)
            if method is not None:
                assert callable(method), f"{attr}.{method_name}가 callable이 아님"


def test_b8_icon_path_full_inventory(qapp, project_root) -> None:
    """B8 확장: ICON_PATH의 모든 png 아이콘이 QPixmap으로 로드된다."""
    from utility.settings.setting_base import ICON_PATH

    icon_dir = (project_root / ICON_PATH.lstrip("./").lstrip(".\\")).resolve()
    assert icon_dir.is_dir(), f"ICON_PATH 디렉토리 없음: {icon_dir}"

    pngs = sorted(icon_dir.glob("*.png"))
    assert len(pngs) >= 10, f"아이콘 수 비정상: {len(pngs)}개 (최소 10개 기대)"

    null_icons = []
    for p in pngs:
        pixmap = QPixmap(str(p))
        if pixmap.isNull() or pixmap.width() == 0:
            null_icons.append(p.name)
    assert not null_icons, f"로드 실패 아이콘: {null_icons}"
