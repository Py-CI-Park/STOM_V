"""Phase13 백테탭 C-1 — 다중 잡 오버레이 겹침↔분할 토글 정적 가드.

검증 대상(빌드 없는 정적 소스 가드 + vendor-babel 문법 무결):
  - BtOverlayPanel 에 viewMode 상태(overlay|split) + 헤더 토글 버튼([겹침|분할]).
  - BtSplitGrid 컴포넌트 정의 + small-multiple 그리드 렌더(잡별 셀 SVG).
  - viewMode==split 일 때 BtSplitGrid, 아니면 BtOverlayCurves 렌더 분기.
  - normalize 토글이 겹침/분할 양쪽에 동일 전달(BtSplitGrid·BtOverlayCurves 모두 normalize prop).
  - backtest.jsx 가 브라우저 동일 엔진(vendor-babel)으로 문법 무결하게 트랜스폼.

오버레이/분할 컴포넌트는 backtest.jsx 에 산다(backtest-charts.jsx 아님 — 2026-06-13 실측:
BtOverlayCurves·_BT_OVERLAY_COLORS·_btNum 이 backtest.jsx 스코프). 따라서 BtSplitGrid 도 동거.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _component_body(src: str, header: str) -> str:
    """header(함수 선언) 이후부터 다음 최상위 함수 선언 직전까지의 본문을 잘라 반환한다."""
    start = src.find(header)
    assert start != -1, f"{header} 선언을 찾지 못함"
    tail = src[start + len(header):]
    nxt = re.search(r"\nfunction ", tail)
    return tail[: nxt.start()] if nxt else tail


class TestViewModeToggle:
    """BtOverlayPanel 의 겹침↔분할 보기 토글."""

    def test_view_mode_state_default_overlay(self):
        src = _read_front("backtest.jsx")
        body = _component_body(src, "function BtOverlayPanel(")
        # viewMode 상태가 있고 기본값이 overlay 여야 한다.
        assert re.search(r'viewMode.*=.*useState_bt\(\s*"overlay"\s*\)', body), \
            "viewMode 상태(기본 overlay)가 없습니다"
        assert "setViewMode" in body

    def test_header_has_overlay_and_split_buttons(self):
        src = _read_front("backtest.jsx")
        body = _component_body(src, "function BtOverlayPanel(")
        assert '"overlay"' in body and '"split"' in body
        # 한글 라벨 [겹침|분할].
        assert "겹침" in body and "분할" in body
        assert "setViewMode(m)" in body or "setViewMode(" in body

    def test_render_branches_on_view_mode(self):
        src = _read_front("backtest.jsx")
        body = _component_body(src, "function BtOverlayPanel(")
        # split 이면 BtSplitGrid, 아니면 BtOverlayCurves.
        assert 'viewMode === "split"' in body
        assert "BtSplitGrid" in body
        assert "BtOverlayCurves" in body

    def test_normalize_passed_to_both_modes(self):
        src = _read_front("backtest.jsx")
        body = _component_body(src, "function BtOverlayPanel(")
        # 두 렌더 경로 모두 normalize 를 전달(정규화 토글이 양쪽 모드에서 동작).
        assert re.search(r"<BtSplitGrid[^>]*normalize=\{normalize\}", body), \
            "BtSplitGrid 에 normalize 가 전달되지 않음"
        assert re.search(r"<BtOverlayCurves[^>]*normalize=\{normalize\}", body), \
            "BtOverlayCurves 에 normalize 가 전달되지 않음"


class TestBtSplitGrid:
    """BtSplitGrid small-multiple 그리드 컴포넌트."""

    def test_component_defined(self):
        src = _read_front("backtest.jsx")
        assert "function BtSplitGrid(" in src

    def test_uses_responsive_grid(self):
        src = _read_front("backtest.jsx")
        body = _component_body(src, "function BtSplitGrid(")
        # CSS grid 로 small-multiple 배치(2열).
        assert "display:" in body and "grid" in body
        assert "gridTemplateColumns" in body
        assert "repeat(2" in body

    def test_renders_per_job_cells(self):
        src = _read_front("backtest.jsx")
        body = _component_body(src, "function BtSplitGrid(")
        # series 를 셀로 매핑 + 각 셀에 svg path.
        assert "series.map(" in body
        assert "<svg" in body
        assert "<path" in body
        # 잡별 색상은 오버레이와 동일 팔레트 재사용.
        assert "_BT_OVERLAY_COLORS" in body

    def test_reuses_normalize_first_point_logic(self):
        src = _read_front("backtest.jsx")
        # 셀 경로 계산이 normalize 시 첫 포인트 기준 평행이동(BtOverlayCurves 와 동형).
        assert "_btSplitCellPath" in src
        body = _component_body(src, "function _btSplitCellPath(")
        assert "cum_profit" in body
        assert "normalize" in body
        assert "cums[0]" in body

    def test_empty_state_korean(self):
        src = _read_front("backtest.jsx")
        body = _component_body(src, "function BtSplitGrid(")
        assert "research-empty" in body
        assert "곡선이 없습니다" in body


# --------------------------------------------------------------- vendor-babel 트랜스폼
def test_backtest_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 브라우저 babel 트랜스폼 검증 생략")
    script = r"""
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const Babel = require(path.join(dir, 'vendor-babel.js'));
const files = ['backtest.jsx', 'backtest-charts.jsx'];
let ok = true;
for (const f of files) {
  try { Babel.transform(fs.readFileSync(path.join(dir, f), 'utf8'), { presets: ['react'], filename: f }); }
  catch (e) { ok = false; console.error('FAIL ' + f + ': ' + e.message); }
}
process.exit(ok ? 0 : 1);
"""
    script_path = tmp_path / "check.js"
    script_path.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [node, str(script_path), str(FRONTEND)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"babel transform failed: {result.stderr}"
