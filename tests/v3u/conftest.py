"""V3U 자동 GUI 검증 conftest.

Constraint: V3 official runtime source 0줄 수정. 본 파일은 V3U lane 전용 픽스처.
Constraint: 자격증명·실거래 API 호출 0건. mock 거래소만 사용.
Constraint: tests/v3u/ 외부 코드는 import만 허용, 수정 불가.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# tests/v3u/ → 프로젝트 루트
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# stom.py와 동일하게 QApplication 생성 전 OpenGL 컨텍스트 공유 속성을 설정해야
# ui/event_click/button_clicked_show_dialog.py의 QtWebEngineWidgets import 가드가
# 통과한다. 본 환경 변수도 stom.py와 동일하게 사전 설정한다.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("STOM_ALLOW_MINIMAL_SETTING", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
# pytest 환경에서 mid-network-call WebCrawling은 fixture teardown 시 Windows
# access violation 위험. webc 동작 검증은 사용자 시각 검증 영역으로 위임.
os.environ.setdefault("STOM_V3U_DISABLE_WEBC", "1")


@pytest.fixture(scope="session")
def qapp():
    """세션 단위 QApplication 단일 인스턴스.

    pytest-qt가 자체 QApplication을 만들지만 본 픽스처는 stom.py와 동일한 시퀀스
    (`Qt.AA_ShareOpenGLContexts` 사전 설정)를 보장한다.
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication

    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("fusion")
    yield app


@pytest.fixture
def main_window(qapp):
    """V3U pyd-free MainWindow 함수 단위 픽스처.

    매 테스트마다 새 MainWindow를 만들고 종료 시 안전하게 close 한다.
    splash는 None으로 주입해 splash 의존을 끊고, auto_run=0으로 자동 로그인을 막는다.
    """
    from ui.main_window import MainWindow

    mw = MainWindow(auto_run=0, splash=None)
    yield mw
    # pytest teardown에서 mw.close()는 V3 close_event(QMessageBox.question modal)를
    # 거치며 Windows access violation을 일으킨다. close() 우회하고 process_kill만
    # 호출 후 deleteLater로 안전 정리.
    try:
        if hasattr(mw, "process_kill"):
            mw.process_kill()
    except Exception:
        pass
    try:
        mw.hide()
        mw.deleteLater()
    except Exception:
        pass


@pytest.fixture(scope="session")
def factor_lists():
    """V3 setting_market의 LIST_STOCK_TICK / LIST_STOCK_MIN 라이브 import.

    V3 upstream 흡수 시 키가 추가되거나 순서가 바뀌면 즉시 본 픽스처로 노출된다.
    """
    from utility.settings.setting_market import LIST_STOCK_TICK, LIST_STOCK_MIN

    return {"tick": list(LIST_STOCK_TICK), "min": list(LIST_STOCK_MIN)}


@pytest.fixture(scope="session")
def dict_findex_snapshot():
    """V3.18 시점 dict_findex 키 스냅샷 (drift 감지용)."""
    snapshot_path = Path(__file__).parent / "fixtures" / "dict_findex_v318.json"
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


@pytest.fixture
def dict_findex_min(factor_lists):
    """분봉 모드용 dict_findex.

    backtest/backengine_base.py:140~159의 round-trip 규칙을 그대로 따른다.
    """
    base = {factor: i for i, factor in enumerate(factor_lists["min"])}
    base["분당매도수금액"] = base["분당매수금액"]
    base["누적분당매도수수량"] = base["누적분당매수수량"]
    base["당일매도수금액"] = base["당일매수금액"]
    base["최고매도수금액"] = base["최고매수금액"]
    base["최고매도수가격"] = base["최고매수가격"]
    base["호가총잔량"] = base["매수총잔량"]
    base["매도수호가잔량1"] = base["매수잔량1"]
    return base


@pytest.fixture
def dict_findex_tick(factor_lists):
    """틱 모드용 dict_findex."""
    base = {factor: i for i, factor in enumerate(factor_lists["tick"])}
    base["초당매도수금액"] = base["초당매수금액"]
    base["누적초당매도수수량"] = base["누적초당매수수량"]
    base["당일매도수금액"] = base["당일매수금액"]
    base["최고매도수금액"] = base["최고매수금액"]
    base["최고매도수가격"] = base["최고매수가격"]
    base["호가총잔량"] = base["매수총잔량"]
    base["매도수호가잔량1"] = base["매수잔량1"]
    return base


@pytest.fixture
def synthetic_ohlcv():
    """합성 OHLCV 생성 함수 픽스처."""
    from tests.v3u.fixtures.synthetic_ohlcv import build_min_array, build_tick_array

    return {"min": build_min_array, "tick": build_tick_array}


@pytest.fixture(scope="session")
def project_root():
    return _PROJECT_ROOT


@pytest.fixture(scope="session")
def v3u_log_dir(tmp_path_factory):
    """세션 단위 로그 디렉토리. .omx/logs/v3u/automation_<session>/와 별도."""
    return tmp_path_factory.mktemp("v3u_pytest_logs")
