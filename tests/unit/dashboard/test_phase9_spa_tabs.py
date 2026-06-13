"""Phase 9 — SPA 6탭 통합 소스 계약 테스트.

빌드 없는 in-browser Babel JSX 라 텍스트(소스 grep) 계약 + 벤더 babel 트랜스폼으로
검증한다(기존 dashboard 테스트 관행: 소스 substring 단언 + 문법 무결 확인).

통합 목표(PHASE8_AUDIT_AND_IA.md §4):
  별도 HTML(lab/pro/verdict) 풀 리로드 → 단일 SPA 6탭으로 통일. 본문 로직은
  dashboard-pages.jsx 전역(LabPage/ProPage/VerdictPanel)이 단일 정본으로 담당하고,
  app.jsx 는 그 전역을 인페이지 탭으로 마운트하며, 각 standalone HTML 은 같은 전역을
  마운트한다(로직 중복 제거·하드링크 제거).

검증 대상:
  dashboard-pages.jsx
    - window.LabPage / window.ProPage / window.VerdictPanel 정의 + Object.assign 노출.
    - VerdictPanel: append-only /record_decision POST + promote_checklist + ICON 맵 보존.
  app.jsx
    - STOM_TABS 6개(evolution/backtest/simulation + lab/pro/verdict).
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
        # PROMOTE 체크리스트 렌더.
        assert "promote_checklist" in src
        # ICON 맵 보존(verdict.html 원본과 동일 의미).
        assert "const ICON = {" in src
        assert '"pass"' not in src  # 키는 식별자형(pass/warn/fail/pending)
        assert "pass:" in src and "warn:" in src and "fail:" in src and "pending:" in src

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
        """in-browser Babel JSX — import/export·TS 금지."""
        src = _read("dashboard-pages.jsx")
        for line in src.splitlines():
            stripped = line.strip()
            assert not stripped.startswith("import "), f"import 금지: {stripped}"
            assert not stripped.startswith("export "), f"export 금지: {stripped}"


# =================================================================== app.jsx
class TestAppTabs:
    def test_stom_tabs_has_six_entries(self) -> None:
        src = _read("app.jsx")
        block = src.split("const STOM_TABS", 1)[1].split("];", 1)[0]
        for key in ('"evolution"', '"backtest"', '"simulation"',
                    '"lab"', '"pro"', '"verdict"'):
            assert key in block, f"STOM_TABS 누락: {key}"
        # 6개 탭 엔트리(key: 줄 기준).
        key_lines = [ln for ln in block.splitlines() if "key:" in ln]
        assert len(key_lines) == 6, f"탭 개수 6 아님: {len(key_lines)}"

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
        for name in ("lab.html", "pro.html"):
            src = _read(name)
            pos_lab = src.find('src="research-lab.jsx')
            pos_pro = src.find('src="research-pro.jsx')
            pos_dp = src.find('src="dashboard-pages.jsx')
            assert pos_dp > pos_lab > -1, f"{name}: dashboard-pages 가 research-lab 뒤가 아님"
            assert pos_dp > pos_pro > -1, f"{name}: dashboard-pages 가 research-pro 뒤가 아님"


# ------------------------------------------------------------- vendor-babel 트랜스폼
def test_phase9_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    """편집/신규 JSX 가 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 브라우저 babel 트랜스폼 검증 생략")
    script = r"""
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const Babel = require(path.join(dir, 'vendor-babel.js'));
const files = ['dashboard-pages.jsx', 'app.jsx'];
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
