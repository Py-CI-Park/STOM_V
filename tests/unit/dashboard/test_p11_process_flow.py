"""Phase 11 — 프로세스 플로우 SVG 다이어그램 전환 소스 계약 테스트.

빌드 없는 in-browser Babel JSX 라 텍스트(소스 grep) 계약 + 벤더 babel 트랜스폼으로
검증한다(기존 dashboard 테스트 관행: 소스 substring 단언 + 문법 무결 확인).

검증 대상(phase-detail.jsx, ProcessFlowPanel/ProcessFlowDiagram):
  - 평면 .process-box 행을 SVG 노드+화살표 플로우로 교체:
      · styles.css 가 소유한 .stom-flow-* 클래스 사용(노드 상태/라벨/sub/화살표).
      · 플로우용 <svg> 를 렌더(viewBox + preserveAspectRatio 반응형).
  - 데이터/인덱스 로직 보존: current_step + step_timings 를 여전히 읽는다.
  - 노드 상태 분기(done/active/pending) + 활성 직전 화살표 .lit 점등.
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
        """평면 박스 대신 .stom-flow-* SVG 플로우 클래스를 쓴다(styles.css 소유)."""
        src = _read("phase-detail.jsx")
        # 노드 상태별 클래스.
        assert "stom-flow-node-done" in src
        assert "stom-flow-node-active" in src
        assert "stom-flow-node-pend" in src
        # 컨테이너 + 라벨/sub + 화살표.
        assert "stom-flow-wrap" in src
        assert "stom-flow-label" in src
        assert "stom-flow-sub" in src
        assert "stom-flow-arrow" in src

    def test_renders_svg_for_flow(self) -> None:
        """플로우 다이어그램이 <svg>(viewBox + preserveAspectRatio)로 렌더된다."""
        src = _read("phase-detail.jsx")
        # 전용 다이어그램 컴포넌트.
        assert "ProcessFlowDiagram" in src
        block = src.split("function ProcessFlowDiagram", 1)[1].split("\nfunction ", 1)[0]
        # SVG 요소 + 반응형 속성.
        assert "<svg" in block
        assert "viewBox" in block
        assert "preserveAspectRatio" in block
        # 노드는 rounded-rect(rx), 연결은 line + 화살표머리 polygon.
        assert "<rect" in block and "rx" in block
        assert "<line" in block
        assert "<polygon" in block

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

    def test_node_status_and_lit_arrow_branches(self) -> None:
        """노드 done/active/pending 분기 + 활성 직전 화살표 .lit 점등 로직 존재."""
        src = _read("phase-detail.jsx")
        block = src.split("function ProcessFlowDiagram", 1)[1].split("\nfunction ", 1)[0]
        # 상태 분기.
        assert "i === currentStep" in block  # active
        assert "currentStep > i" in block    # done
        # 완료 경로 화살표 점등(.lit).
        assert "lit" in block
        assert "stom-flow-arrow${lit" in block or '" lit"' in block

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
