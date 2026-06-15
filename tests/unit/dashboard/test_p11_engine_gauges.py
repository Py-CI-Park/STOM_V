"""Phase 11 — 엔진 메트릭 패널 그래픽 게이지 + 임계값 경고 소스 계약 테스트.

빌드 없는 in-browser Babel JSX 라 텍스트(소스 grep) 계약 + 벤더 babel 트랜스폼으로
검증한다(기존 dashboard 테스트 관행: 소스 substring 단언 + 문법 무결 확인).

목표(feature/webbt-phase11):
  EnginePanel 의 핵심 수치 메트릭(CPU/메모리/진행률)을 텍스트 숫자에서 그래픽 게이지
  바(.stom-gauge — styles.css 에 이미 존재)로 전환하고, 임계값 색상(.warn/.danger)을
  토큰(--amber/--red)으로만 표현한다. null/부재 값은 빈 바 + "—" 로 크래시 없이 표기.

검증 대상(engine.jsx):
  - .stom-gauge / .stom-gauge-row / .stom-gauge-fill / .stom-gauge-label /
    .stom-gauge-val 클래스 사용.
  - CPU/메모리/진행률 게이지 렌더 + warn/danger 임계값 로직.
  - null-safe(값 부재 시 "—").
  - DEMO/LIVE 분리 + "실시간 데이터 대기"(LivePending) 동작 보존.
  - 인라인 하드코딩 색상(amber/teal/red hex·rgba) 부재 — 토큰만 사용.

편집 JSX 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다.
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


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


# ============================================================ 게이지 클래스 사용
class TestGaugeClasses:
    def test_uses_stom_gauge_css_classes(self) -> None:
        """styles.css 에 이미 존재하는 게이지 클래스를 그대로 사용(메인 소유 CSS 미변경)."""
        src = _read("engine.jsx")
        for cls in (
            "stom-gauge-row",
            "stom-gauge-label",
            "stom-gauge",
            "stom-gauge-fill",
            "stom-gauge-val",
        ):
            assert cls in src, f"게이지 클래스 누락: {cls}"

    def test_fill_uses_warn_and_danger_modifiers(self) -> None:
        """임계값 색상은 .warn/.danger modifier 로만(토큰 매핑은 styles.css)."""
        src = _read("engine.jsx")
        assert "danger" in src, ".danger modifier 누락"
        assert "warn" in src, ".warn modifier 누락"
        # fill 클래스 베이스가 존재.
        assert '"stom-gauge-fill"' in src


# ============================================================ CPU/Mem/Progress 게이지
class TestGaugeMetrics:
    def test_cpu_memory_progress_gauges_rendered(self) -> None:
        """CPU / 메모리 / 진행률 세 게이지가 렌더된다."""
        src = _read("engine.jsx")
        # 게이지 컴포넌트가 세 메트릭 모두에 사용.
        assert src.count("<GaugeRow") >= 3, "GaugeRow 사용이 3 미만"
        # 라벨로 메트릭 식별(CPU/Mem/전체 진행). Phase12-A: 진행 게이지 라벨 'Progress'→'전체'
        #   (숫자=세대 내 진행 vs 게이지=세대 누적 전체를 구분).
        assert 'label="CPU"' in src
        assert "Mem" in src
        assert 'label="전체"' in src

    def test_cpu_thresholds_70_90(self) -> None:
        """CPU 게이지: warn ≥70, danger ≥90."""
        src = _read("engine.jsx")
        # CPU GaugeRow 라인에 warn=70 / danger=90 동시 존재.
        cpu_line = next(
            (ln for ln in src.splitlines() if 'label="CPU"' in ln and "GaugeRow" in ln),
            "",
        )
        assert "warn={70}" in cpu_line, f"CPU warn 임계값 70 아님: {cpu_line}"
        assert "danger={90}" in cpu_line, f"CPU danger 임계값 90 아님: {cpu_line}"

    def test_memory_thresholds_75_90(self) -> None:
        """메모리 게이지: warn ≥75, danger ≥90."""
        src = _read("engine.jsx")
        mem_line = next(
            (ln for ln in src.splitlines() if "Mem" in ln and "GaugeRow" in ln),
            "",
        )
        assert "warn={75}" in mem_line, f"Mem warn 임계값 75 아님: {mem_line}"
        assert "danger={90}" in mem_line, f"Mem danger 임계값 90 아님: {mem_line}"

    def test_progress_gauge_always_teal_no_thresholds(self) -> None:
        """진행률 게이지는 항상 teal — warn/danger 미지정(기본 .stom-gauge-fill)."""
        src = _read("engine.jsx")
        prog_line = next(
            (ln for ln in src.splitlines() if 'label="전체"' in ln and "GaugeRow" in ln),
            "",
        )
        assert prog_line, "전체 진행 GaugeRow 라인 없음"
        assert "warn=" not in prog_line, "Progress 게이지에 warn 임계값이 있으면 안 됨"
        assert "danger=" not in prog_line, "Progress 게이지에 danger 임계값이 있으면 안 됨"


# ============================================================ 임계값 로직 / null-safe
class TestThresholdLogicAndNullSafety:
    def test_threshold_logic_uses_gte_comparison(self) -> None:
        """임계값 로직: value >= danger / value >= warn 비교로 modifier 부여."""
        src = _read("engine.jsx")
        assert "value >= danger" in src, "danger 임계 비교(>=) 누락"
        assert "value >= warn" in src, "warn 임계 비교(>=) 누락"

    def test_fill_width_clamped_0_100(self) -> None:
        """fill width = clamp(value, 0, 100)% — Math.max(0, Math.min(100, ...))."""
        src = _read("engine.jsx")
        assert "Math.max(0, Math.min(100, value))" in src, "0~100 clamp 누락"

    def test_null_absent_value_shows_dash_no_crash(self) -> None:
        """null/부재 값 → 빈 바 + '—' (크래시 금지)."""
        src = _read("engine.jsx")
        # 숫자 유효성 검사 후 미충족 시 "—".
        assert "Number.isFinite(value)" in src, "값 유효성 검사 누락"
        assert "—" in src, "부재 값 표기(—) 누락"
        # 게이지 값 소스가 null-safe(0 과 부재 구분).
        assert "cpuGauge" in src and "memPctGauge" in src

    def test_demo_live_split_preserved(self) -> None:
        """DEMO/LIVE 분리 + '실시간 데이터 대기'(LivePending) 동작 보존."""
        src = _read("engine.jsx")
        assert "liveNoEngine" in src, "LIVE-무엔진 분기 누락"
        assert "window.LivePending" in src, "LivePending 분기 누락"
        assert "isDemo" in src


# ============================================================ 하드코딩 색상 제거
class TestNoHardcodedColors:
    def test_no_hex_or_rgba_literals(self) -> None:
        """토큰이 존재하는 색상은 인라인 hex/rgba 리터럴로 남기지 않는다(--teal/--red 등)."""
        src = _read("engine.jsx")
        # #rgb / #rrggbb hex.
        hex_hits = re.findall(r"#[0-9a-fA-F]{3,6}\b", src)
        assert not hex_hits, f"하드코딩 hex 색상 잔존: {hex_hits}"
        # rgb()/rgba() 리터럴.
        rgba_hits = re.findall(r"rgba?\(", src)
        assert not rgba_hits, f"하드코딩 rgba 색상 잔존: {rgba_hits}"

    def test_svg_gradient_uses_color_tokens(self) -> None:
        """LiveBacktestChart SVG 그라디언트 stopColor 가 토큰(var(--teal)/var(--red))을 사용."""
        src = _read("engine.jsx")
        assert 'stopColor="var(--teal)"' in src, "eq-grad teal 토큰 미사용"
        assert 'stopColor="var(--red)"' in src, "dd-grad red 토큰 미사용"


# ============================================================ in-browser Babel 제약
class TestInBrowserBabelConstraints:
    def test_no_import_export_no_ts(self) -> None:
        """JSX 소스 계약 — TS 금지 + ESM 은 Track Z dual-safe 형태만 허용.

        RELAXED (Track Z PR-3): build-app.mjs 의 `_stripTopLevelEsm` 가 concat 경로에서
        제거하는 단일라인 dual-safe ESM(`import { … } from "./x.jsx";` / `export { … };`)
        은 허용한다(FLAGGED 번들이 실 모듈 스코프로 사용, 기본 concat 은 strip → byte-unchanged).
        가드의 실의도는 유지: (a) TypeScript 문법 금지, (b) dual-safe 외 모든 import/export
        형태 금지(`import X from`, `import * as`, `export default`, `export const/function`,
        `import type` 등). 즉 임의 ESM 으로의 확산을 계속 막되, Track Z 변환만 통과시킨다."""
        import re as _re

        src = _read("engine.jsx")
        # Track Z dual-safe 허용 패턴(단일 물리 라인; _stripTopLevelEsm 와 동일 표면).
        _ALLOW_IMPORT = _re.compile(r"""^import\s*\{[^}]*\}\s*from\s*["']\./[^"']+\.jsx["']\s*;?\s*$""")
        _ALLOW_EXPORT = _re.compile(r"""^export\s*\{[^}]*\}\s*;?\s*$""")
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("import "):
                assert _ALLOW_IMPORT.match(stripped), (
                    f"dual-safe 아닌 import 금지(Track Z 는 `import {{…}} from \"./x.jsx\";` 만 허용): {stripped}"
                )
            if stripped.startswith("export "):
                assert _ALLOW_EXPORT.match(stripped), (
                    f"dual-safe 아닌 export 금지(Track Z 는 `export {{ … }};` 만 허용): {stripped}"
                )
        # TS 문법 금지(가드의 핵심 의도 유지): 타입 주석/인터페이스/제네릭 선언 등.
        assert "import type" not in src and "export type" not in src, "TS type import/export 금지"
        assert not _re.search(r"\binterface\s+[A-Z]\w*\s*\{", src), "TS interface 선언 금지"
        assert not _re.search(r"\benum\s+[A-Z]\w*\s*\{", src), "TS enum 선언 금지"

    def test_per_file_hook_aliases_preserved(self) -> None:
        """파일별 훅 별칭(전역 충돌 방지) — useState_e/useMemo_e/useRef_e 보존."""
        src = _read("engine.jsx")
        assert "useState: useState_e" in src
        assert "useMemo: useMemo_e" in src
        assert "useRef: useRef_e" in src

    def test_window_global_export_preserved(self) -> None:
        """EnginePanel/LiveBacktestChart 전역 노출 보존(window 글로벌 패턴)."""
        src = _read("engine.jsx")
        assert "Object.assign(window, {" in src
        assert "EnginePanel" in src and "LiveBacktestChart" in src


# ------------------------------------------------------------- vendor-babel 트랜스폼
def test_p11_engine_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    """편집 JSX(engine.jsx) 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼."""
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
const files = ['engine.jsx'];
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
