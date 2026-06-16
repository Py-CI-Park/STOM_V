"""Phase 7.7 트랙 L — 기타 탭 결함 수정(Req 10) 소스 계약 테스트.

빌드 없는 in-browser Babel JSX 라 텍스트(소스 grep) 계약 + 벤더 babel 트랜스폼으로
검증한다(기존 dashboard 테스트 관행: 소스 substring 단언 + 문법 무결 확인).

검증 대상(plan §7.7):
  research-lab.jsx
    - 영문 누수 제거: "insufficient data" 부재(하드 제약) · 그 외 "insufficient*" 영문
      빈상태 문자열도 한국어화.
    - RESEARCH_TABS 라벨이 한국어.
    - _rlCorrColor 가 하드코딩 rgba 가 아닌 디자인 토큰(color-mix + var(--teal/--red/--ink-2))
      기반 발산 스케일(0 중심 의미 유지).
  backtest.jsx
    - 모드 선택기에 WFO(전진분석)·스윕(sweep) 용어 설명 tooltip.
    - 2025 하드코딩 예시 날짜 제거(현재 연도 동적 파생).
    - isDemo 일 때 보이는 데모 모드 배지/설명.
  evolution-analysis.jsx
    - 흐린(게이트 탈락) 산점 점 범례 라벨.
    - MDD 범례 키에 "%" 단위.
    - onOpenWorkbench 누락 시 비활성/툴팁 가드(조용한 무동작 방지).

세 편집 JSX 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다.
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


def _has_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


# =========================================================== research-lab.jsx
# P5.6 분해: research-lab.jsx → THIN BARREL + rl-vdt-shell/rl-analysis/rl-validation/rl-panel.
#   RESEARCH_TABS·ResearchLabPanel 은 rl-panel.jsx, _rlCorrColor 등 상관 보조는 rl-analysis.jsx.
_RL_FILES = ("research-lab.jsx", "rl-vdt-shell.jsx", "rl-analysis.jsx",
             "rl-validation.jsx", "rl-panel.jsx")


class TestResearchLab:
    def test_no_insufficient_data_leak(self) -> None:
        """하드 제약 — 'insufficient data' 문자열이 어느 rl-* 소스에도 남지 않는다."""
        src = "".join(_read(f) for f in _RL_FILES)
        assert "insufficient data" not in src
        # 그 외 영문 빈상태 누수(insufficient*)도 전부 제거됐다.
        assert "insufficient" not in src

    def test_research_tabs_labels_are_korean(self) -> None:
        # RESEARCH_TABS 정의는 rl-panel.jsx 로 이동.
        src = _read("rl-panel.jsx")
        # RESEARCH_TABS 블록을 잘라 라벨이 한국어인지 확인.
        block = src.split("const RESEARCH_TABS", 1)[1].split("]", 1)[0]
        # 이전 영문 라벨이 사라졌다.
        for old in ('"Feature Importance"', '"Correlation"',
                    '"Variable Combinations"', '"Validation"'):
            assert old not in block, f"영문 라벨 잔존: {old}"
        # 각 탭 라벨에 한글이 포함된다(label: 키 라인 기준).
        label_lines = [ln for ln in block.splitlines() if "label:" in ln]
        assert len(label_lines) >= 5
        for ln in label_lines:
            assert _has_hangul(ln), f"한국어 라벨 아님: {ln.strip()}"

    def test_corr_color_uses_tokens_not_raw_rgba(self) -> None:
        """_rlCorrColor 가 토큰 기반 color-mix 스케일을 쓰고 원시 rgba 리터럴이 없다."""
        src = _read("rl-analysis.jsx")  # _rlCorrColor 정의는 rl-analysis.jsx 로 이동.
        body = src.split("function _rlCorrColor", 1)[1].split("\n}", 1)[0]
        # 디자인 토큰 발산 스케일.
        assert "color-mix" in body
        assert "var(--teal)" in body and "var(--red)" in body
        assert "var(--ink-2)" in body
        # 0 중심(부호) 의미 유지 — 양/음 분기.
        assert "value >= 0" in body
        # 하드코딩 rgba(...) 컬러 리터럴이 _rlCorrColor 에서 제거됐다.
        assert "rgba(" not in body, "원시 rgba 리터럴이 corr 스케일에 잔존"


# =============================================================== backtest.jsx
# P5.2 분해 — backtest.jsx 는 THIN BARREL 로 축소되고 실제 코드는 bt-tab-* sibling 으로 이동.
#   모드 팁 상수(_BT_MODE_TIP)·기간 예시(_BT_START_EG/_BT_END_EG) → bt-tab-utils.jsx,
#   모드 토글/placeholder 사용처(BtRunPanel) → bt-tab-run.jsx, 데모 배지(BacktestTab) → bt-tab-root.jsx.
class TestBacktest:
    def test_mode_tooltips_explain_wfo_and_sweep(self) -> None:
        utils = _read("bt-tab-utils.jsx")
        run = _read("bt-tab-run.jsx")
        # WFO 전진분석 용어 설명 + Walk-Forward (모드 팁 상수 정의: bt-tab-utils).
        assert "전진분석" in utils
        assert "Walk-Forward" in utils
        # 스윕(sweep) 용어 설명.
        assert "스윕(sweep)" in utils
        # 모드 토글 버튼에 tooltip 매핑이 연결된다(사용처: bt-tab-run).
        assert "_BT_MODE_TIP" in run
        assert "title={_BT_MODE_TIP[m]}" in run

    def test_no_hardcoded_2025_example_date(self) -> None:
        # 노후화되는 2025 하드코딩 예시 날짜가 백테탭 소스 어디에도 없다(배럴+sibling 전부).
        for name in ("backtest.jsx", "bt-tab-utils.jsx", "bt-tab-run.jsx", "bt-tab-root.jsx"):
            assert "2025" not in _read(name), f"노후화되는 2025 하드코딩 예시 날짜 잔존: {name}"
        # 현재 연도 동적 파생 예시(상수 정의: bt-tab-utils).
        utils = _read("bt-tab-utils.jsx")
        assert "getFullYear()" in utils
        assert "_BT_START_EG" in utils and "_BT_END_EG" in utils
        # placeholder 사용처(BtRunPanel: bt-tab-run).
        run = _read("bt-tab-run.jsx")
        assert "placeholder={_BT_START_EG}" in run
        assert "placeholder={_BT_END_EG}" in run

    def test_demo_mode_badge_visible(self) -> None:
        # isDemo 분기로 보이는 데모 배지/설명(탭 루트: bt-tab-root).
        src = _read("bt-tab-root.jsx")
        assert "isDemo && (" in src
        assert "데모 모드" in src
        # 빈/예시 화면을 버그로 오인하지 않도록 설명.
        assert "예시" in src and "백엔드 미연결" in src


# ====================================================== evolution-analysis.jsx
class TestEvolutionAnalysis:
    def test_gate_failed_scatter_legend_label(self) -> None:
        src = _read("evolution-analysis.jsx")
        # 흐린(게이트 탈락) 점 범례 라벨이 명시적이다.
        assert "게이트 탈락(흐린 점)" in src
        # 통과 범례와 짝.
        assert 'label="게이트 통과"' in src

    def test_mdd_legend_key_has_percent_unit(self) -> None:
        src = _read("evolution-analysis.jsx")
        # EA_SERIES 의 mdd 라벨에 % 단위.
        assert 'label: "mdd(%)"' in src

    def test_workbench_button_guarded_when_callback_missing(self) -> None:
        src = _read("evolution-analysis.jsx")
        # onOpenWorkbench 누락 시 비활성/툴팁 가드(조용한 무동작 방지).
        assert "canOpenWorkbench" in src
        assert 'typeof onOpenWorkbench === "function"' in src
        # 버튼 disabled 조건에 가드가 포함된다.
        assert "!canOpenWorkbench" in src
        assert "disabled={!g.has_csv || !canOpenWorkbench}" in src


# ------------------------------------------------------------- vendor-babel 트랜스폼
def test_phase7_other_tabs_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    """편집된 3개 JSX 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다."""
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
const files = ['research-lab.jsx', 'rl-vdt-shell.jsx', 'rl-analysis.jsx', 'rl-validation.jsx', 'rl-panel.jsx', 'backtest.jsx', 'bt-tab-utils.jsx', 'bt-tab-library.jsx', 'bt-tab-run.jsx', 'bt-tab-mode-results.jsx', 'bt-tab-analysis.jsx', 'bt-tab-root.jsx', 'evolution-analysis.jsx'];
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
