"""P4-functional 계약 테스트 — 백테 CSV·WFO/스윕 드릴다운·엔진 DEMO 라벨·LWC 비대칭 캡션.

ralplan 계획 P4-functional(2026-06-14). 순수 Python(소스 grep) — node/esbuild 비의존이라
P0.5 의 esbuild-skip 클러스터에 들어가지 않고 wt-webbt/wt-dev 어디서나 동일 실행된다.
(빌드 없는 정적 계약 검증: 다른 dashboard 테스트와 동일 관행 — 소스 substring 단언.)

검증 대상:
  · 백테 CSV 내보내기(backtest-charts.jsx): sim 체결로그 CSV 와 동일 규약(BOM·\\r\\n·Blob).
  · WFO/스윕 결과표 행 드릴다운(backtest.jsx): 클릭 → 선택 파라미터·전체 메트릭 펼침.
  · 엔진 게이지 DEMO 라벨(engine.jsx): 데모 소스면 런타임 게이지가 시뮬값임을 명시.
  · 시뮬 LWC 비대칭 캡션(simulation.jsx): LWC 선택 시 미표시 서브패인을 토글 옆에 명시.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _slice(src: str, start_marker: str, end_marker: str) -> str:
    i = src.index(start_marker)
    j = src.index(end_marker, i + len(start_marker))
    return src[i:j]


# ============================================================ 백테 CSV 내보내기
class TestBacktestCsvExport:
    """backtest-charts.jsx — 일별 수익곡선 CSV(클라이언트 Blob, sim 규약 미러)."""

    # P5.1 분해 — CSV 헬퍼 정의는 backtest-charts.jsx(배럴)에서 bt-chart-utils.jsx 로,
    #   버튼 와이어링은 bt-result-area.jsx 로 이동(동작 불변, 코드 이동만).
    def test_csv_helpers_defined(self) -> None:
        src = _read("bt-chart-utils.jsx")
        assert "function _btCsvCell(" in src
        assert "function _btAnalysisCsv(" in src
        assert "function _btDownloadAnalysisCsv(" in src

    def test_csv_has_column_headers(self) -> None:
        src = _read("bt-chart-utils.jsx")
        csvfn = _slice(src, "function _btAnalysisCsv(", "function _btDownloadAnalysisCsv(")
        for col in ("날짜", "일별손익(원)", "누적수익(원)"):
            assert col in csvfn, f"누락된 CSV 컬럼: {col}"

    def test_csv_has_utf8_bom(self) -> None:
        src = _read("bt-chart-utils.jsx")
        csvfn = _slice(src, "function _btAnalysisCsv(", "function _btDownloadAnalysisCsv(")
        assert "﻿" in csvfn, "CSV 출력에 utf-8 BOM 이 없습니다"

    def test_csv_blob_download_clientside(self) -> None:
        src = _read("bt-chart-utils.jsx")
        # _btDownloadAnalysisCsv 본문(고정 오프셋 슬라이스 — 함수 직전 주석이 종료마커라 _slice 부적합).
        i = src.index("function _btDownloadAnalysisCsv(")
        dl = src[i:i + 900]
        assert "new Blob(" in dl
        assert "text/csv" in dl
        assert "URL.createObjectURL" in dl
        assert "a.download = fname" in dl or ".download = fname" in dl
        assert ".click()" in dl
        assert '"백테스트_"' in dl
        assert '".csv"' in dl

    def test_csv_button_wired_and_gated(self) -> None:
        src = _read("bt-result-area.jsx")
        # BtResultArea 헤더에서 호출 + 버튼 라벨 + equity daily 존재로 게이팅.
        assert "_btDownloadAnalysisCsv(analysis)" in src
        assert "⬇ CSV" in src
        assert "(analysis.equity || {}).daily || []).length > 0" in src


# ============================================================ WFO/스윕 드릴다운
class TestWfoSweepDrilldown:
    """결과표 행 클릭 → 선택 파라미터·전체 메트릭 펼침(백엔드 무변경, 프론트 전용).

    P5.2 분해 — _BtRowDetail 은 bt-tab-utils.jsx, BtWfoTable/BtSweepTable/BtModeResultPanel 은
    bt-tab-mode-results.jsx 로 이동(backtest.jsx 는 THIN BARREL).
    """

    def test_row_detail_component_defined(self) -> None:
        src = _read("bt-tab-utils.jsx")
        assert "function _BtRowDetail(" in src

    def test_wfo_rows_expandable(self) -> None:
        src = _read("bt-tab-mode-results.jsx")
        wfo = _slice(src, "function BtWfoTable(", "function BtSweepTable(")
        # 펼침 상태 + 행 클릭 토글 + 드릴다운 데이터(선택 파라미터·전체 메트릭).
        assert "const [expanded, setExpanded]" in wfo
        assert "setExpanded(isOpen ? null : r.round)" in wfo
        assert "cursor: \"pointer\"" in wfo
        assert "best_params" in wfo
        assert "<_BtRowDetail" in wfo

    def test_sweep_rows_expandable(self) -> None:
        src = _read("bt-tab-mode-results.jsx")
        sweep = _slice(src, "function BtSweepTable(", "function BtModeResultPanel(")
        assert "const [expanded, setExpanded]" in sweep
        assert "setExpanded(isOpen ? null : r.__idx)" in sweep
        assert "cursor: \"pointer\"" in sweep
        assert "_metrics: m" in sweep
        assert "<_BtRowDetail" in sweep
        # 동적 컬럼 colSpan(전폭 상세 행).
        assert "colSpan={span}" in sweep


# ============================================================ 엔진 DEMO 라벨
class TestEngineDemoGaugeLabel:
    """engine.jsx — 데모 소스면 런타임 게이지가 backend 미발행 시뮬값임을 게이지 위에 명시."""

    def test_demo_caption_present_and_gated(self) -> None:
        src = _read("engine.jsx")
        # isDemo 게이팅 캡션이 engine-grid 안에 존재.
        assert "DEMO 시뮬값 — CPU·메모리·워커·처리량 게이지는 데모 시뮬레이션 값입니다(backend 미발행)" in src
        # 데모 분기로 감싸짐.
        grid = _slice(src, '<div className="engine-grid">', '{/* CPU')
        assert "isDemo &&" in grid

    def test_no_hardcoded_colors_in_caption(self) -> None:
        # 회귀: test_p11_engine_gauges 의 하드코딩 색상 금지와 일관 — 캡션도 토큰만.
        import re
        src = _read("engine.jsx")
        assert not re.findall(r"#[0-9a-fA-F]{3,6}\b", src), "engine.jsx 에 하드코딩 hex 색상"
        assert not re.findall(r"rgba?\(", src), "engine.jsx 에 하드코딩 rgba 색상"


# ============================================================ LWC 비대칭 캡션
class TestSimLwcAsymmetryCaption:
    """simulation.jsx — LWC 선택 시 미표시 서브패인을 토글 옆 캡션으로 명시(의도된 비대칭)."""

    def test_lwc_caption_present_and_gated(self) -> None:
        src = _read("simulation.jsx")
        # engineMode === "lwc" 게이팅.
        assert 'engineMode === "lwc" && (' in src
        # 비대칭 캡션 — 미표시 지표 열거.
        assert "LWC 비대칭" in src
        for token in ("RSI", "MACD", "호가불균형", "net-delta"):
            assert token in src, f"LWC 캡션에 {token} 누락"

    def test_caption_is_label_only_not_in_charts(self) -> None:
        # 캡션은 simulation.jsx(토글 옆)에만 — sim 차트 컴포넌트 코드(배럴 + P5.3 sibling)는 무영향.
        for name in ("simulation-charts.jsx", "sim-chart-utils.jsx", "sim-chart-subpanes.jsx",
                     "sim-chart-shell.jsx", "sim-chart-engines.jsx", "sim-signal-log.jsx"):
            assert "LWC 비대칭 —" not in _read(name), f"{name} 에 캡션 누출"
