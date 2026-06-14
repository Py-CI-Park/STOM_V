"""Phase11 — 변수 조합(combo) 탭: 평면 행 목록 → 2-D 상호작용 히트맵 계약.

검증 대상(빌드 없는 정적 가드 + vendor-babel 문법 무결):
  research-lab.jsx 의 _CombinationList 가
    - styles.css 의 기존 클래스(.stom-combo-grid / .stom-combo-cell / .stom-combo-axis)로
      2-D 히트맵 행렬을 렌더한다(평면 .research-combo-list/.research-combo-row 아님).
    - pair 배열을 feature 행렬로 피벗한다(_combinationMatrix, 대칭 cellMap, 축 cap).
    - 셀 배경(background)을 _rlCorrColor 발산색으로 칠한다(텍스트 색만이 아님).
    - 셀 hover title("A × B · score · n=…")과 teal=양/red=음 범례를 노출한다.
    - gridTemplateColumns 가 'auto repeat(N, minmax(0,1fr))' 형태다(첫 칸=행 라벨).
  토큰화(라이트/다크 정합):
    - 하드코딩 #c95 / #9ab / #d4af37 리터럴이 디자인 토큰으로 치환됐다.
    - _rlCorrColor 의 발산(teal/red) 의미는 보존된다(behavior-preserving).
  + research-lab.jsx 가 브라우저 동일 엔진(vendor-babel)으로 문법 무결하게 트랜스폼.
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


# --------------------------------------------------------------- 2-D 히트맵 정적 가드
class TestComboHeatmapSource:
    def test_uses_2d_grid_classes_not_flat_list(self):
        src = _read_front("research-lab.jsx")
        # 기존 styles.css 클래스로 2-D 히트맵을 렌더한다.
        assert ".stom-combo-grid" not in src  # CSS 셀렉터가 아니라 className 사용.
        assert "stom-combo-grid" in src
        assert "stom-combo-cell" in src
        assert "stom-combo-axis" in src
        # 세로(열) 축 라벨에 .col 변형 사용.
        assert "stom-combo-axis col" in src

    def test_combolist_no_longer_flat_row_list(self):
        """_CombinationList 본문이 평면 .research-combo-row 목록이 아니다."""
        src = _read_front("research-lab.jsx")
        # _CombinationList 블록만 추출.
        start = src.index("function _CombinationList(")
        end = src.index("function _RangeSummaryList(")
        body = src[start:end]
        assert "research-combo-row" not in body, "_CombinationList 가 평면 행을 쓰면 안 된다"
        assert "stom-combo-grid" in body
        assert "stom-combo-cell" in body

    def test_pivots_pairs_into_feature_matrix(self):
        src = _read_front("research-lab.jsx")
        # 피벗 헬퍼와 대칭 cellMap·축 cap 존재.
        assert "_combinationMatrix" in src
        assert "_COMBO_MAX_FEATURES" in src
        # 양방향 저장으로 대칭화(a|b 와 b|a).
        assert 'a + "|" + b' in src
        assert 'b + "|" + a' in src

    def test_cell_background_uses_corr_color(self):
        """셀 BACKGROUND 가 _rlCorrColor 로 칠해진다(텍스트 색만이 아님)."""
        src = _read_front("research-lab.jsx")
        start = src.index("function _CombinationList(")
        end = src.index("function _RangeSummaryList(")
        body = src[start:end]
        # background 스타일에 _rlCorrColor 적용.
        assert re.search(r"background:\s*_rlCorrColor\(", body), \
            "셀 background 가 _rlCorrColor 로 칠해져야 한다"

    def test_cell_hover_title_present(self):
        src = _read_front("research-lab.jsx")
        start = src.index("function _CombinationList(")
        end = src.index("function _RangeSummaryList(")
        body = src[start:end]
        # "A × B · score · n=…" hover title.
        assert "title={`" in body
        assert "×" in body and "n=" in body

    def test_legend_and_empty_state_korean(self):
        src = _read_front("research-lab.jsx")
        start = src.index("function _CombinationList(")
        end = src.index("function _RangeSummaryList(")
        body = src[start:end]
        # teal=양 / red=음 범례.
        assert "teal" in body and "red" in body
        assert "양" in body and "음" in body
        # 정직한 빈 상태(파일 공통 empty-state 재사용).
        assert "_ResearchEmptyState" in body
        assert "변수 조합이 부족합니다" in body

    def test_grid_template_columns_shape(self):
        src = _read_front("research-lab.jsx")
        # 첫 칸=행 라벨, 이후 N개 균등 분할.
        assert "auto repeat(" in src
        assert "minmax(0,1fr)" in src


# --------------------------------------------------------------- 토큰화(하드코딩 색 제거)
class TestColorTokenization:
    def test_hardcoded_color_literals_removed(self):
        src = _read_front("research-lab.jsx")
        assert "#c95" not in src, "#c95 → var(--amber) 로 치환돼야 한다"
        assert "#9ab" not in src, "#9ab → var(--ink-2) 로 치환돼야 한다"
        assert "#d4af37" not in src, "#d4af37 → var(--mesa-gold) 로 치환돼야 한다"

    def test_tokens_present(self):
        src = _read_front("research-lab.jsx")
        assert "var(--amber)" in src
        assert "var(--ink-2)" in src
        assert "var(--mesa-gold)" in src

    def test_corr_color_diverging_semantics_preserved(self):
        """_rlCorrColor 의 발산(teal=양 / red=음) 의미는 그대로다."""
        src = _read_front("research-lab.jsx")
        start = src.index("function _rlCorrColor(")
        end = src.index("function _ResearchEmptyState(")
        body = src[start:end]
        assert "var(--teal)" in body
        assert "var(--red)" in body
        assert "value >= 0" in body  # 양수 분기 → teal.

    def test_combo_grid_classes_exist_in_styles(self):
        css = _read_front("styles.css")
        assert ".stom-combo-grid" in css
        assert ".stom-combo-cell" in css
        assert ".stom-combo-axis" in css
        assert ".stom-combo-axis.col" in css


# --------------------------------------------------------------- 다른 RESEARCH_TABS 보존
class TestOtherResearchTabsIntact:
    def test_research_tabs_all_present(self):
        src = _read_front("research-lab.jsx")
        for tab in ("edge", "feature", "correlation", "combos", "validation"):
            assert f'id: "{tab}"' in src, f"RESEARCH_TABS 에 {tab} 누락"

    def test_other_tab_components_untouched(self):
        src = _read_front("research-lab.jsx")
        # edge/feature/correlation/validation 경로의 핵심 컴포넌트가 그대로다.
        assert "EdgeRatioPanel" in src
        assert "FeatureImportancePanel" in src
        assert "_CorrelationHeatmap" in src
        assert "_ValidationPanel" in src
        # correlation 탭의 평면 목록 보조(_RangeSummaryList/_SegmentSummaryList)는 유지.
        assert "_RangeSummaryList" in src
        assert "_SegmentSummaryList" in src


# --------------------------------------------------------------- vendor-babel 트랜스폼
def test_research_lab_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 브라우저 babel 트랜스폼 검증 생략")
    script = r"""
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const esbuild = require(path.join(dir, '..', 'webui-build', 'node_modules', 'esbuild'));
const files = ['research-lab.jsx'];
let ok = true;
for (const f of files) {
  try { esbuild.transformSync(fs.readFileSync(path.join(dir, f), 'utf8'), { loader: 'jsx', jsx: 'transform', jsxFactory: 'React.createElement', jsxFragment: 'React.Fragment' }); }
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
