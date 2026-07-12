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


def test_workbench_exposes_selection_caveats_and_promotion_blockers() -> None:
    # Given: the V4 Workbench wrapper around candidate comparison panels.
    source = _read("v4-workbench.jsx")

    # When/Then: comparison ownership and dangerous-action boundaries are announced.
    assert '<section' in source and 'className="v4-workbench v4-cjk-safe"' in source
    assert 'aria-labelledby="v4-workbench-title"' in source
    assert '<h2 id="v4-workbench-title"' in source
    assert 'role="status"' in source and 'aria-live="polite"' in source
    assert 'data-state={surfaceState}' in source
    assert 'data-v4-scroll-owner="workbench-candidate-compare"' in source
    assert 'aria-describedby="v4-workbench-caveat"' in source
    assert 'id="v4-workbench-caveat"' in source
    assert '후보 선택 상태' in source
    assert '승격·최종 승인·운영 반영은 이 탭에서 실행되지 않습니다.' in source
    assert '서버 검증' in source and '차단' in source


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
