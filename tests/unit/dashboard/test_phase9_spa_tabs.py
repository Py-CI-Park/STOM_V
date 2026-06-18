"""Phase 9 — SPA 탭 통합 소스 계약 테스트(7탭: + 프로세스 흐름).

빌드 없는 in-browser Babel JSX 라 텍스트(소스 grep) 계약 + 벤더 babel 트랜스폼으로
검증한다(기존 dashboard 테스트 관행: 소스 substring 단언 + 문법 무결 확인).

통합 목표(PHASE8_AUDIT_AND_IA.md §4):
  별도 HTML(lab/pro/verdict) 풀 리로드 → 단일 SPA 탭으로 통일. 본문 로직은
  dashboard-pages.jsx 전역(LabPage/ProPage/VerdictPanel)이 단일 정본으로 담당하고,
  app.jsx 는 그 전역을 인페이지 탭으로 마운트하며, 각 standalone HTML 은 같은 전역을
  마운트한다(로직 중복 제거·하드링크 제거).

검증 대상:
  dashboard-pages.jsx
    - window.LabPage / window.ProPage / window.VerdictPanel 정의 + Object.assign 노출.
    - VerdictPanel: append-only /record_decision POST + promote_checklist
      (P7: 상태 아이콘 맵은 research-lab.jsx 의 _VDT_STATUS_ICON 단일 정본으로 이전).
  app.jsx
    - STOM_TABS 7개(evolution/backtest/simulation + lab/pro/verdict + process).
    - 새 3탭 전역 마운트(window.LabPage/ProPage/VerdictPanel).
    - stom-pagenav 에 lab.html/pro.html/verdict.html 하드링크 부재.
  verdict.html / lab.html / pro.html
    - 공유 전역(VerdictPanel/LabPage/ProPage) 마운트 + dashboard-pages.jsx 로드.
    - 인라인 루트 정의(VerdictRoot/LabRoot/ProRoot) 부재(정본은 dashboard-pages.jsx).

편집 JSX 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다.
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


# ====================================================== dashboard-pages.jsx (정본)
class TestDashboardPages:
    def test_defines_and_exports_three_globals(self) -> None:
        src = _read("dashboard-pages.jsx")
        # 세 컴포넌트 정의.
        assert "function LabPage(" in src
        assert "function ProPage(" in src
        assert "function VerdictPanel(" in src
        # window 전역 노출.
        assert "Object.assign(window, { LabPage, ProPage, VerdictPanel })" in src

    def test_verdict_append_only_post_and_checklist(self) -> None:
        src = _read("dashboard-pages.jsx")
        # append-only 결정 기록 — /record_decision POST(번복도 새 레코드).
        assert "/record_decision" in src
        assert 'method: "POST"' in src
        assert "append-only" in src
        # PROMOTE 체크리스트 렌더 — P7: 공유 VdtPromoteChecklist 로 위임.
        assert "promote_checklist" in src
        assert "window.VdtPromoteChecklist" in src
        # ICON 맵 보존(verdict.html 원본과 동일 의미) — P7: 공유 VdtPromoteChecklist 로 이전돼
        #   `_VDT_STATUS_ICON` 단일 정본이 됐다(dashboard-pages 의 ICON 제거).
        #   P5.6 분해: 공유 셸(Vdt* + _VDT_STATUS_ICON)은 rl-vdt-shell.jsx 로 이동.
        lab_src = _read("rl-vdt-shell.jsx")
        assert "const _VDT_STATUS_ICON = {" in lab_src
        assert "pass:" in lab_src and "warn:" in lab_src and "fail:" in lab_src and "pending:" in lab_src

    def test_per_file_hook_aliases(self) -> None:
        """파일별 훅 별칭(다른 JSX 와 전역 충돌 방지) — useState_dp/useEffect_dp."""
        src = _read("dashboard-pages.jsx")
        assert "useState: useState_dp" in src
        assert "useEffect: useEffect_dp" in src

    def test_defensive_global_panel_references(self) -> None:
        """ResearchLabPanel/ResearchProPanel 부재 시 크래시 대신 자리표시자."""
        src = _read("dashboard-pages.jsx")
        assert "window.ResearchLabPanel" in src
        assert "window.ResearchProPanel" in src
        assert "_DpLoading" in src

    def test_no_import_export_no_ts(self) -> None:
        """JSX 소스 계약 — TS 금지 + ESM 은 Track Z dual-safe 형태만 허용.

        RELAXED (Track Z PR-3): build-app.mjs 의 `_stripTopLevelEsm` 가 concat 경로에서
        제거하는 단일라인 dual-safe ESM(`import { … } from "./x.jsx";` / `export { … };`)
        은 허용한다(FLAGGED 번들이 실 모듈 스코프로 사용, 기본 concat 은 strip → byte-unchanged).
        가드의 실의도는 유지: (a) TypeScript 문법 금지, (b) dual-safe 외 모든 import/export
        형태 금지(`import X from`, `import * as`, `export default`, `export const/function`,
        `import type` 등). 즉 임의 ESM 으로의 확산을 계속 막되, Track Z 변환만 통과시킨다."""
        import re as _re

        src = _read("dashboard-pages.jsx")
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
        assert "import type" not in src and "export type" not in src, "TS type import/export 금지"
        assert not _re.search(r"\binterface\s+[A-Z]\w*\s*\{", src), "TS interface 선언 금지"
        assert not _re.search(r"\benum\s+[A-Z]\w*\s*\{", src), "TS enum 선언 금지"

    def test_verdict_has_systematic_subtabs(self) -> None:
        """Phase10 — 결정 이력 탭을 다른 탭처럼 .research-tabs 하위 탭으로 체계화.
        4개 하위 탭(검증 결산·레짐·부활·V6 포트폴리오·운용 결정)으로 분류돼야 한다."""
        src = _read("dashboard-pages.jsx")
        # 하위 탭 상태 + localStorage 유지.
        assert "vsub" in src and "setVsub" in src
        assert "stom_verdict_subtab" in src
        # 연구실과 동일한 탭바 클래스/활성 표기.
        assert 'className="research-tabs"' in src
        assert '"research-tab" + (vsub === t.key ? " active" : "")' in src
        # 4개 하위 탭 키 + 라벨.
        for key in ('"summary"', '"regime"', '"portfolio"', '"decide"'):
            assert key in src, f"하위 탭 키 누락: {key}"
        assert "검증 결산" in src and "레짐·부활" in src and "운용 결정" in src
        # 각 그룹은 자기 하위 탭에서만 렌더(분류).
        assert 'vsub === "summary"' in src
        assert 'vsub === "decide"' in src


# =================================================================== app.jsx
class TestAppTabs:
    def test_stom_tabs_has_seven_entries(self) -> None:
        src = _read("app.jsx")
        block = src.split("const STOM_TABS", 1)[1].split("];", 1)[0]
        for key in ('"evolution"', '"backtest"', '"simulation"',
                    '"lab"', '"pro"', '"verdict"', '"process"'):
            assert key in block, f"STOM_TABS 누락: {key}"
        # 7개 탭 엔트리(key: 줄 기준) — 7번째 '프로세스 흐름'(process) 포함.
        key_lines = [ln for ln in block.splitlines() if "key:" in ln]
        assert len(key_lines) == 7, f"탭 개수 7 아님: {len(key_lines)}"

    def test_mounts_three_new_globals(self) -> None:
        src = _read("app.jsx")
        assert "window.LabPage" in src
        assert "window.ProPage" in src
        assert "window.VerdictPanel" in src
        # 각각 activeTab 조건으로 마운트.
        assert 'activeTab === "lab"' in src
        assert 'activeTab === "pro"' in src
        assert 'activeTab === "verdict"' in src

    def test_pagenav_no_hardlinks_to_standalone_html(self) -> None:
        """stom-pagenav 에서 lab.html/pro.html/verdict.html 하드링크 제거."""
        src = _read("app.jsx")
        # 헤더 네비(브랜드 행)에 풀 리로드 하드링크가 남지 않는다.
        assert 'href="/ui/lab.html"' not in src
        assert 'href="/ui/pro.html"' not in src
        assert 'href="/ui/verdict.html"' not in src

    def test_localstorage_tab_persistence_preserved(self) -> None:
        src = _read("app.jsx")
        # 6키 모두 동일 메커니즘으로 영속(키 무관 activeTab 저장).
        assert 'localStorage.setItem("stom_active_tab", activeTab)' in src


# ============================================================ standalone HTML
class TestStandaloneHtml:
    def test_verdict_html_mounts_global_no_inline_root(self) -> None:
        src = _read("verdict.html")
        assert "dashboard-pages.jsx" in src
        assert "window.VerdictPanel" in src
        # 인라인 루트 정의가 사라졌다(정본은 dashboard-pages.jsx).
        assert "function VerdictRoot" not in src

    def test_lab_html_mounts_global_no_inline_root(self) -> None:
        src = _read("lab.html")
        assert "dashboard-pages.jsx" in src
        assert "window.LabPage" in src
        assert "function LabRoot" not in src

    def test_pro_html_mounts_global_no_inline_root(self) -> None:
        src = _read("pro.html")
        assert "dashboard-pages.jsx" in src
        assert "window.ProPage" in src
        assert "function ProRoot" not in src

    def test_standalone_pages_keep_back_link(self) -> None:
        """각 standalone 페이지에 /ui/ 백링크 유지."""
        for name in ("verdict.html", "lab.html", "pro.html"):
            src = _read(name)
            assert 'href="/ui/"' in src, f"{name} 백링크 누락"

    def test_dashboard_pages_loaded_after_deps_in_lab_pro(self) -> None:
        """lab/pro: dashboard-pages.jsx <script> 태그가 research-* 의존 뒤에 로드된다.

        주석/프로즈가 아니라 실제 <script src="..."> 태그 위치로 로드 순서를 본다.
        """
        # Phase14.7: lab/pro 는 단일 컴파일 번들 bundle/app.js 를 로드한다(런타임 babel 제거).
        #   모델-무관 마이그레이션: research-lab/research-pro/dashboard-pages 의 텍스트 concat
        #   순서(==== X.jsx ==== 마커 index 비교)는 모듈 스코프에선 무의미하므로 DROP 하고,
        #   세 모듈이 산출 번들에 모두 존재함을 각자 정의 심볼로 검증한다(concat·bundle 양쪽 통과).
        #   LabPage/ProPage 가 의존(ResearchLabPanel/ResearchProPanel)과 함께 번들에 들어있어야
        #   lab/pro.html 마운트가 성립한다 — 런타임 마운트는 Track Z 하니스 V4 가 별도 검증.
        app_bundle = _read("bundle/app.js")
        for sym in ("ResearchLabPanel", "ResearchProPanel", "LabPage", "ProPage"):
            assert sym in app_bundle, f"app.js 에 {sym} 누락"
        for name in ("lab.html", "pro.html"):
            assert "bundle/app.js" in _read(name), f"{name}: 컴파일 번들 미로드"


# ------------------------------------------------------------- vendor-babel 트랜스폼
def test_phase9_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    """편집/신규 JSX 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다."""
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
const files = ['dashboard-pages.jsx', 'app.jsx'];
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
