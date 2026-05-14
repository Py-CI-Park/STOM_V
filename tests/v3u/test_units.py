"""V3U 분석기/유틸 단위 테스트.

Constraint: V3 official source 0줄 수정. 한글 키 dict_findex는 conftest 픽스처 경유.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def test_b1_risk_analyzer_min_data_default_30(qapp, dict_findex_min) -> None:
    """B1: AnalyzerRisk가 min_data 디폴트 30으로 인스턴스화된다."""
    from strategy.analyzer_risk import AnalyzerRisk

    rk = AnalyzerRisk(market_type="stock", dict_findex=dict_findex_min)
    assert rk.min_data == 30, f"디폴트 min_data 30 기대, 실제 {rk.min_data}"


def test_b1_risk_analyzer_explicit_min_data(qapp, dict_findex_min) -> None:
    """B1: min_data를 명시 주입할 때도 정상 적용된다."""
    from strategy.analyzer_risk import AnalyzerRisk

    rk = AnalyzerRisk(market_type="stock", dict_findex=dict_findex_min, min_data=50)
    assert rk.min_data == 50


def test_b2_realtime_trade_paths_have_no_prange() -> None:
    """B2: 실시간 매매 경로(trade/, ui/event_click/, ui/update_widget/)에
    prange 사용이 없다 (CPU<90% 보장)."""
    targets = [Path("trade"), Path("ui/event_click"), Path("ui/update_widget")]
    offenders = []
    for d in targets:
        if not d.is_dir():
            continue
        for py in d.rglob("*.py"):
            text = py.read_text(encoding="utf-8", errors="replace")
            if "prange" in text:
                offenders.append(str(py))
    assert not offenders, (
        f"실시간 경로에 prange 발견 (CPU<90% 위험): {offenders}. "
        f"V3 upstream에서 prange가 추가됐다면 trade 경로 외부로 분리 필요."
    )


def test_b2_numba_paths_still_use_prange() -> None:
    """B2 보강: numba 가속 경로(backtest/, strategy/)에는 prange가 의도대로 잔존한다.

    이게 0이 되면 V3 upstream이 numba 의존을 제거했다는 신호.
    """
    targets = [Path("backtest"), Path("strategy")]
    found = 0
    for d in targets:
        for py in d.rglob("*.py"):
            text = py.read_text(encoding="utf-8", errors="replace")
            if "prange" in text:
                found += 1
                break  # 디렉토리당 1개라도 있으면 OK
    assert found >= 1, (
        "numba 가속 경로에 prange가 모두 사라졌음. "
        "V3 upstream의 numba 의존 제거 가능성 — 의도된 변경인지 확인 필요."
    )


def test_settings_module_imports(qapp) -> None:
    """utility/settings/ 핵심 모듈이 모두 import된다."""
    import importlib

    for mod_name in (
        "utility.settings.setting_base",
        "utility.settings.setting_market",
        "utility.settings.setting_user",
    ):
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"{mod_name} import 실패"

    from utility.settings.setting_base import (
        DB_PATH, LOG_PATH, ICON_PATH,
        DB_SETTING, DB_CODE_INFO, DB_STRATEGY, DB_TRADELIST,
    )
    for name, value in [
        ("DB_PATH", DB_PATH), ("LOG_PATH", LOG_PATH), ("ICON_PATH", ICON_PATH),
        ("DB_SETTING", DB_SETTING), ("DB_CODE_INFO", DB_CODE_INFO),
        ("DB_STRATEGY", DB_STRATEGY), ("DB_TRADELIST", DB_TRADELIST),
    ]:
        assert isinstance(value, str) and value, f"{name}이 비어있음"
