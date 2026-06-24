"""Phase 11 — 프로세스 플로우 React Flow + Dagre 전환 소스 계약 테스트.

빌드 없는 in-browser Babel JSX 라 텍스트(소스 grep) 계약 + 벤더 babel 트랜스폼으로
검증한다(기존 dashboard 테스트 관행: 소스 substring 단언 + 문법 무결 확인).

검증 대상(phase-detail.jsx, ProcessFlowPanel/ProcessFlowDiagram):
  - 평면 .process-box 행을 React Flow + Dagre 그래프로 교체:
      · styles.css 가 소유한 .stom-rf-* 클래스 사용(노드 상태/라벨/엣지).
      · ReactFlow 렌더 + Background/Controls + Dagre LR 레이아웃을 사용한다.
  - 데이터/인덱스 로직 보존: current_step + step_timings 를 여전히 읽는다.
  - 노드 상태 분기(done/active/pending) + 완료/활성 경로 edge 점등/animation.
  - 하드코딩 amber rgba(240,179,90,...) 리터럴 부재(토큰화).

phase-detail.jsx 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다.
"""

from __future__ import annotations

import os
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


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


# ============================================================ phase-detail.jsx
class TestProcessFlowSvg:
    def test_uses_stom_flow_classes(self) -> None:
        """평면 박스 대신 .stom-rf-* React Flow 그래프 클래스를 쓴다(styles.css 소유)."""
        src = _read("phase-detail.jsx")
        # 노드 상태별 클래스.
        assert "stom-rf-node-${status}" in src
        assert "stom-rf-node-label" in src
        assert "stom-rf-node-step" in src
        # 컨테이너 + 엣지 상태.
        assert "stom-rf-wrap" in src
        assert "stom-rf-edge-lit" in src
        assert "stom-rf-edge" in src

    def test_renders_react_flow_dagre_graph(self) -> None:
        """플로우 다이어그램이 React Flow + Dagre 그래프로 렌더된다."""
        src = _read("phase-detail.jsx")
        # 전용 다이어그램 컴포넌트.
        assert "ProcessFlowDiagram" in src
        block = src.split("function ProcessFlowDiagram", 1)[1].split("\nfunction ", 1)[0]
        # React Flow 렌더 + Dagre 자동 레이아웃.
        assert "<ReactFlow" in block
        assert "dagre.graphlib.Graph" in block
        assert 'rankdir: "LR"' in block
        assert "<Background" in block
        assert "<Controls" in block
        assert "MarkerType.ArrowClosed" in block
        assert "fitView" in block

    def test_flat_process_box_row_removed(self) -> None:
        """평면 .process-flow-row / .process-box 노드 렌더 블록이 사라졌다."""
        src = _read("phase-detail.jsx")
        # 구 평면 행 컨테이너 + 박스 렌더가 제거되고 SVG 다이어그램으로 대체됐다.
        assert "process-flow-row" not in src
        assert 'className={`process-box' not in src

    def test_still_reads_current_step_and_step_timings(self) -> None:
        """데이터/인덱스 로직 보존 — current_step + step_timings 를 여전히 읽는다."""
        src = _read("phase-detail.jsx")
        assert "current_step" in src
        assert "step_timings" in src
        # 다이어그램이 currentStep / stepTimings 를 props 로 받아 노드 상태를 결정.
        block = src.split("function ProcessFlowDiagram", 1)[1].split("\nfunction ", 1)[0]
        assert "currentStep" in block
        assert "stepTimings" in block
        assert "normalizeFlowStepIndex" in src

    def test_node_status_and_lit_arrow_branches(self) -> None:
        """노드 done/active/pending 분기 + 활성 직전 화살표 .lit 점등 로직 존재."""
        src = _read("phase-detail.jsx")
        block = src.split("function ProcessFlowDiagram", 1)[1].split("\nfunction ", 1)[0]
        # 상태 분기.
        assert "flowStepStatus(index, currentStep)" in block
        assert 'status === "active"' in block
        assert 'status === "done"' in block
        # 완료/활성 경로 edge 점등/animation.
        assert "stom-rf-edge-lit" in block
        assert "animated: lit && running" in block

    def test_live_strip_and_timing_grid_added(self) -> None:
        """운영 콘솔용 현재 노드/phase/current_step/최근 로그와 단계별 timing grid를 노출한다."""
        src = _read("phase-detail.jsx")
        assert "process-live-strip" in src
        assert "process-timing-grid" in src
        assert "현재 노드" in src
        assert "최근 로그" in src
        assert "flowStepStatus" in src
        css = _read("styles.css")
        assert ".process-live-strip" in css
        assert ".process-timing-cell.active" in css
    def test_process_slice_adds_selector_pipeline_and_authority_markers(self) -> None:
        """프로세스 projection selector, full pipeline, advisory/promotion authority labels를 고정한다."""
        src = _read("phase-detail.jsx")
        css = _read("styles.css")
        for marker in (
            "process-selector-panel",
            "process-selector-option",
            "process-readout-grid",
            "process-pipeline-panel",
            "process-warm-panel",
            "PROCESS_FALLBACK_CATALOG",
            "FULL_PIPELINE_STEPS",
            "state.page_data.condition_discovery.process",
            "process_catalog projection",
            "research_validation",
            "advisory_split",
            "can_promote",
            "selected?.label",
            "selected?.title",
            "can_export",
            "can_live",
        ):
            assert marker in src
        assert "score_can_promote" not in src
        assert "score_can_export" not in src
        assert "score_can_live" not in src
        for marker in (
            ".process-selector-panel",
            ".process-selector-option.active",
            ".process-pipeline-steps",
            ".process-capability-pill",
            ".process-warm-grid",
        ):
            assert marker in css
    def test_no_hardcoded_amber_rgba_literal(self) -> None:
        """amber 하드코딩 rgba(240,179,90,...) 리터럴이 소스에 남지 않는다(토큰화)."""
        src = _read("phase-detail.jsx")
        assert "rgba(240,179,90" not in src
        assert "rgba(240, 179, 90" not in src


# ------------------------------------------------------------- vendor-babel 트랜스폼
def test_p11_phase_detail_transforms_with_vendor_babel(tmp_path: Path) -> None:
    """편집된 phase-detail.jsx 가 vendor-babel(브라우저와 동일 엔진) 로 문법 무결하게 트랜스폼된다."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 브라우저 babel 트랜스폼 검증 생략")
    if not (FRONTEND.parent / "webui-build" / "node_modules" / "esbuild").exists():
        pytest.skip("esbuild 미설치(webui-build/node_modules gitignored) — 트랜스폼 검증 생략")
    script = r"""
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const esbuild = require(path.join(dir, '..', 'webui-build', 'node_modules', 'esbuild'));
const files = ['phase-detail.jsx'];
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
