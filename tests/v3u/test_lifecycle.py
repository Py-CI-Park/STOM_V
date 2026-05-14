"""V3U 라이프사이클 통합 테스트 (백테 / 변손익분석 / 미시구조).

Constraint: V3 official source 0줄 수정. 실제 multiprocessing.Process spawn 회피하여
좀비 프로세스를 만들지 않는다. import + 인스턴스화 + 메서드 callable까지만 검증한다.
"""
from __future__ import annotations

import importlib

import pytest


pytestmark = pytest.mark.integration


def test_a4_backtest_module_imports() -> None:
    """A4: 백테 엔진 모듈이 모두 import되며 핵심 클래스가 노출된다."""
    expected = {
        "backtest.backengine_base": ["BackEngineBase"],
        "backtest.backengine_base_oms": ["BackEngineBaseOms"],
        "backtest.backtest": [],  # 모듈만 import 가능하면 OK
    }
    for module_name, expected_names in expected.items():
        mod = importlib.import_module(module_name)
        for name in expected_names:
            assert hasattr(mod, name), f"{module_name}에서 {name} 미노출"


def test_a4_backtest_proc_spawn_methods_present(main_window) -> None:
    """A4: V3U MainWindow가 백테 spawn 관련 메서드를 보유한다 (실 spawn은 안 함)."""
    expected_methods = (
        "ProcessStarter",
        "AutoBackSchedule",
        "UpdateProgressBar",
    )
    for m in expected_methods:
        assert hasattr(main_window, m), f"백테 spawn 메서드 누락: {m}"
        assert callable(getattr(main_window, m)), f"{m}가 callable이 아님"


def test_b6_volatility_analyzer_callable_paths_in_backengine() -> None:
    """B6: backengine_base.py가 변손익분석 학습/분석 함수를 일관되게 호출한다."""
    from pathlib import Path

    src = Path("backtest/backengine_base.py").read_text(encoding="utf-8")
    load_count = src.count("vt_analyzer.load_volatility_code_data")
    analyze_count = src.count("vt_analyzer.analyze_current_volatility")
    assert load_count >= 1, "변손익분석 학습데이터 로드 함수 호출 누락"
    assert analyze_count >= 1, "변손익분석 분석 함수 호출 누락"


def test_b7_microstructure_instantiation_stock(qapp, dict_findex_min) -> None:
    """B7: AnalyzerMicrostructure(stock)가 V3.18 dict_findex로 인스턴스화된다."""
    from strategy.analyzer_microstructure import AnalyzerMicrostructure

    am = AnalyzerMicrostructure(market_type="stock", dict_findex=dict_findex_min)
    assert hasattr(am, "_radar_history")
    assert hasattr(am, "_radar_axis_names")
    assert len(am._radar_axis_names) == 8, "radar 축은 8개여야 함"
    assert hasattr(am, "params")
    assert "layering_multiplier" in am.params


def test_b7_microstructure_instantiation_coin(qapp, dict_findex_tick) -> None:
    """B7: AnalyzerMicrostructure(coin)도 동일하게 인스턴스화된다."""
    from strategy.analyzer_microstructure import AnalyzerMicrostructure

    am = AnalyzerMicrostructure(market_type="coin", dict_findex=dict_findex_tick)
    assert am.market_type == "coin"
    assert am.params["layering_multiplier"] != 6.0  # 코인은 stock과 다른 임계값
