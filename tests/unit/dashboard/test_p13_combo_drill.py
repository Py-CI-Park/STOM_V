"""Phase13 (C-5) — 콤보 매트릭스 셀 드릴다운 계약.

검증 대상(빌드 없는 정적 가드 + vendor-babel 문법 무결):
  research-lab.jsx 의 _CombinationList / _ComboPairPopover / _rlPairInterpret 가
    - 채워진 셀에 onClick 이 달려 선택 변수쌍 상태(useState)를 연다(기존 hover title 유지).
    - 팝오버가 feature_a/feature_b(변수쌍) + score + sample_count 를 노출한다.
    - 1줄 한국어 해석(부호=양/음, |값| 강도 라벨, n<임계 표본 부족 경고)을 제공한다.
    - .rp-overlay 패턴을 재사용하고 click-outside + Esc 로 닫힌다.
    - 선택 셀 하이라이트(outline)를 표시한다.
    - 데이터에 없는 통계는 만들지 않고, 더 깊은 분석은 향후 백엔드가 필요함을 정직히 안내한다.
  + research-lab.jsx 가 브라우저 동일 엔진(vendor-babel)으로 문법 무결하게 트랜스폼.
  + 다른 RESEARCH_TABS(edge/feature/correlation/validation)는 손대지 않는다.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _combolist_body(src: str) -> str:
    """_CombinationList 함수 본문만 추출(다음 함수 경계까지)."""
    start = src.index("function _CombinationList(")
    end = src.index("function _RangeSummaryList(")
    return src[start:end]


def _popover_body(src: str) -> str:
    """_ComboPairPopover 함수 본문만 추출(_CombinationList 직전까지)."""
    start = src.index("function _ComboPairPopover(")
    end = src.index("function _CombinationList(")
    return src[start:end]


# --------------------------------------------------------------- 셀 드릴다운(클릭 → 팝오버)
class TestComboDrillCell:
    def test_cell_has_onclick_opening_drill(self):
        """채워진 셀에 onClick 핸들러가 달려 선택 변수쌍 상태를 연다."""
        body = _combolist_body(_read_front("research-lab.jsx"))
        assert "onClick=" in body, "셀에 onClick 드릴다운 핸들러가 있어야 한다"
        # 선택 상태(드릴다운 대상)를 setSelected 로 채운다.
        assert "setSelected(" in body
        assert re.search(r"a:\s*rowF", body) and re.search(r"b:\s*colF", body), \
            "선택 변수쌍에 feature_a(rowF)/feature_b(colF)가 담겨야 한다"
        assert "score: cell.score" in body and "n: cell.n" in body

    def test_uses_usestate_for_selected_pair(self):
        """드릴다운 선택은 per-file hook alias(useState_rl)로 관리한다."""
        body = _combolist_body(_read_front("research-lab.jsx"))
        assert "useState_rl(" in body, "selected 상태는 useState_rl 로 관리해야 한다"

    def test_hover_title_preserved(self):
        """기존 hover title("A × B · score · n=…")이 유지된다."""
        body = _combolist_body(_read_front("research-lab.jsx"))
        assert "title={`" in body
        assert "×" in body and "n=" in body

    def test_selected_cell_highlight(self):
        """선택 셀 하이라이트(outline)를 표시한다."""
        body = _combolist_body(_read_front("research-lab.jsx"))
        assert "outline" in body, "선택 셀 하이라이트(outline)가 있어야 한다"
        # 선택 여부 판별(선택 키 비교).
        assert "isSel" in body or "selKey" in body

    def test_popover_rendered_when_selected(self):
        """선택이 있을 때만 팝오버를 렌더한다."""
        body = _combolist_body(_read_front("research-lab.jsx"))
        assert "_ComboPairPopover" in body
        assert "onClose={() => setSelected(null)}" in body


# --------------------------------------------------------------- 팝오버 내용/닫기
class TestComboPairPopover:
    def test_popover_shows_pair_score_sample(self):
        """팝오버가 변수쌍(a×b) + score + sample_count 를 노출한다."""
        body = _popover_body(_read_front("research-lab.jsx"))
        assert "pair.a" in body and "pair.b" in body, "변수쌍(feature_a/feature_b) 노출"
        assert "pair.score" in body, "research_score/correlation 노출"
        assert "pair.n" in body, "sample_count 노출"
        assert "sample_count" in body

    def test_popover_reuses_rp_overlay(self):
        """경량 오버레이로 .rp-overlay 패턴을 재사용한다."""
        body = _popover_body(_read_front("research-lab.jsx"))
        assert "rp-overlay" in body
        assert "rp-overlay-card" in body

    def test_popover_click_outside_and_esc_close(self):
        """click-outside(onClick=onClose) + Esc(keydown) 로 닫힌다."""
        body = _popover_body(_read_front("research-lab.jsx"))
        # 바깥 클릭으로 닫고, 카드 내부 클릭은 stopPropagation.
        assert "onClick={onClose}" in body
        assert "stopPropagation()" in body
        # Esc 키로 닫기.
        assert 'e.key === "Escape"' in body
        assert "addEventListener" in body and "keydown" in body

    def test_popover_korean_interpretation(self):
        """1줄 한국어 해석(부호·강도 + 예시 문구)을 보여준다."""
        src = _read_front("research-lab.jsx")
        # 해석 헬퍼 존재.
        assert "_rlPairInterpret" in src
        # 강도 라벨(강함/중간/약함/미미)과 부호(양/음) 해석.
        start = src.index("function _rlPairInterpret(")
        end = src.index("function _ComboPairPopover(")
        helper = src[start:end]
        assert "강함" in helper and "약함" in helper
        assert "양의 상호작용" in helper and "음의 상호작용" in helper

    def test_low_sample_warning_present(self):
        """n<임계 표본 부족 경고가 해석에 포함된다(데이터 기반)."""
        src = _read_front("research-lab.jsx")
        start = src.index("function _rlPairInterpret(")
        end = src.index("function _ComboPairPopover(")
        helper = src[start:end]
        assert "_COMBO_MIN_SAMPLE" in helper
        assert "표본 부족" in helper
        assert "lowSample" in helper

    def test_honest_future_backend_note_no_fabrication(self):
        """더 깊은 분석은 향후 백엔드가 필요함을 정직히 안내(통계 날조 금지)."""
        body = _popover_body(_read_front("research-lab.jsx"))
        assert "향후 백엔드" in body
        # 화면 데이터(score·n)에 없는 통계를 만들지 않는다는 정직성 명시.
        assert "만들어 표시하지 않습니다" in body or "지어내지" in body


# --------------------------------------------------------------- 다른 RESEARCH_TABS 보존
class TestOtherResearchTabsIntact:
    def test_research_tabs_all_present(self):
        src = _read_front("research-lab.jsx")
        for tab in ("edge", "feature", "correlation", "combos", "validation"):
            assert f'id: "{tab}"' in src, f"RESEARCH_TABS 에 {tab} 누락"

    def test_other_tab_components_untouched(self):
        src = _read_front("research-lab.jsx")
        assert "EdgeRatioPanel" in src
        assert "FeatureImportancePanel" in src
        assert "_CorrelationHeatmap" in src
        assert "_ValidationPanel" in src
        assert "_RangeSummaryList" in src
        assert "_SegmentSummaryList" in src

    def test_combo_heatmap_grid_still_present(self):
        """P11 2-D 히트맵 골격(grid/cell/axis)이 드릴다운 추가 후에도 유지된다."""
        body = _combolist_body(_read_front("research-lab.jsx"))
        assert "stom-combo-grid" in body
        assert "stom-combo-cell" in body
        assert "stom-combo-axis" in body
        assert "auto repeat(" in body


# --------------------------------------------------------------- vendor-babel 트랜스폼
def test_research_lab_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 브라우저 babel 트랜스폼 검증 생략")
    script = r"""
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const Babel = require(path.join(dir, 'vendor-babel.js'));
const files = ['research-lab.jsx'];
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
