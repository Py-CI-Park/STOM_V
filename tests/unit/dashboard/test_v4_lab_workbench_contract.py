from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_lab_exposes_honest_factor_evidence_regions_and_states() -> None:
    # Given: the V4 Lab wrapper around the existing factor-analysis panels.
    source = _read("v4-lab.jsx")

    # When/Then: its primary evidence, provenance, and async states are explicit.
    assert '<section' in source and 'className="v4-lab v4-cjk-safe"' in source
    assert 'aria-labelledby="v4-lab-title"' in source
    assert '<h2 id="v4-lab-title"' in source
    assert 'role="status"' in source and 'aria-live="polite"' in source
    assert 'aria-busy={surfaceState === "loading"}' in source
    assert 'role="alert"' in source
    assert 'data-state={surfaceState}' in source
    assert 'data-v4-scroll-owner="lab-factor-evidence"' in source
    assert 'tabIndex={0}' in source
    assert 'aria-describedby="v4-lab-provenance"' in source
    assert 'id="v4-lab-provenance"' in source
    assert '표본 외 구간' in source


def test_workbench_is_hof_only_and_compare_moved_to_history() -> None:
    # V6.1(W2·W3): 성과 탭은 명예의 전당 전용. RunCompare 는 History 로 이동(중복 제거).
    source = _read("v4-workbench.jsx")
    assert '<section' in source and 'className="v4-workbench v4-cjk-safe"' in source
    assert 'aria-labelledby="v4-workbench-title"' in source
    assert '<h2 id="v4-workbench-title"' in source
    assert 'role="status"' in source and 'aria-live="polite"' in source
    assert 'data-state={surfaceState}' in source
    assert '명예의 전당' in source
    assert '<HallOfFamePanel' in source and '<HofInventoryGate' in source
    # 중복 제거: 정밀분석·비교는 이 탭에 없다.
    assert '<ResearchProPanel' not in source
    assert '<RunComparePanel' not in source
    # 위험 행동 경계 문구는 유지.
    assert '승격·최종 승인·운영 반영은 이 탭에서 실행되지 않습니다.' in source
    assert '서버 검증' in source and '차단' in source
    # 비교 owner 는 History.
    history = _read("v4-history.jsx")
    assert '<RunComparePanel' in history


@pytest.mark.parametrize("name", ["v4-lab.jsx", "v4-workbench.jsx"])
def test_lab_and_workbench_jsx_transform(name: str, tmp_path: Path) -> None:
    # Given: an installed esbuild and one V4 tab wrapper.
    esbuild = FRONTEND.parent / "webui-build" / "node_modules" / "esbuild"
    if not esbuild.exists():
        pytest.skip("esbuild unavailable")
    output = tmp_path / f"{name}.js"
    script = """
const fs = require('fs');
const esbuild = require(process.argv[1]);
const source = fs.readFileSync(process.argv[2], 'utf8');
const result = esbuild.transformSync(source, { loader: 'jsx', format: 'esm' });
fs.writeFileSync(process.argv[3], result.code);
"""

    # When: the exact production JSX syntax is transformed.
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(esbuild),
            str(FRONTEND / name),
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    # Then: both wrappers remain valid in the production transform lane.
    assert result.returncode == 0, result.stderr
    assert output.exists()
