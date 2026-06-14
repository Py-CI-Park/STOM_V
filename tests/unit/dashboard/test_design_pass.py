"""Design Pass 계약 테스트 — 섹션 헤더 시각 승격 + WCAG + 캐시버스트 + 연구패널 유지.

ralplan 계획 Design Pass(2026-06-14). 순수 Python(소스 grep) — node 비의존(P0.5 skip 클러스터 밖).

검증:
  · SectionLabel 이 .stom-section-label 클래스로 승격(dim 인라인 ink-3 제거).
  · .stom-section-label 가 ink-1(AA+) + teal accent(::before) 시각 위계.
  · styles.css 캐시버스트 핀이 갱신됨(5 HTML 동일).
  · 사이드바 연구패널 4종 유지(field-check 로 제거 차단 — 회귀 가드).
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


class TestSectionLabelPromotion:
    def test_section_label_uses_class_not_dim_inline(self) -> None:
        app = _read("app.jsx")
        # 승격: 클래스 사용 + 옛 dim 인라인(ink-3·10.5) 제거.
        assert 'className="stom-section-label"' in app
        # 옛 인라인 정의 흔적(ink-3 dim 섹션 라벨) 제거.
        assert 'fontSize: 10.5, color: "var(--ink-3)", letterSpacing: ".12em"' not in app

    def test_section_label_call_sites_preserved(self) -> None:
        # 통합 레이아웃 계약(연구패널 순서) 유지 — 호출부 text= 단언 보존.
        app = _read("app.jsx")
        assert 'text="Research Lab"' in app
        assert 'text="Run Monitor"' in app

    def test_section_label_css_visual_hierarchy(self) -> None:
        css = _read("styles.css")
        i = css.index(".stom-section-label {")
        block = css[i:i + 600]
        assert "var(--ink-1)" in block          # AA+ 가독.
        assert "::before" in css[i:i + 900]      # accent 마커.
        assert "var(--teal)" in css[i:i + 900]   # teal accent.


class TestStylesCacheBust:
    def test_styles_cache_bust_bumped_uniformly(self) -> None:
        htmls = ["index.html", "lab.html", "pro.html", "verdict.html", "STOM AI Dashboard.html"]
        vers = set()
        for h in htmls:
            src = _read(h)
            assert "styles.css?v=20260614f" not in src, f"{h}: 옛 캐시버스트 핀 잔존"
            import re
            m = re.search(r"styles\.css\?v=([0-9a-z]+)", src)
            assert m, f"{h}: styles.css ?v= 핀 없음"
            vers.add(m.group(1))
        assert len(vers) == 1, f"HTML 간 styles.css 캐시버스트 불일치: {vers}"


class TestResearchPanelsRetained:
    """field-check 로 제거 차단된 연구패널 4종이 진화 탭에 유지됨(기능 무손실 회귀 가드)."""

    def test_all_four_research_panels_still_mounted(self) -> None:
        app = _read("app.jsx")
        assert "<ResearchLabPanel" in app          # 통합 레이아웃 계약 락.
        assert "<ResearchWikiPanel" in app          # 진화 전용(타 홈 없음).
        assert "<AIContextPanel" in app             # 진화 전용(타 홈 없음).
        assert "ResearchHeatmapPanel" in app        # 사용자 요청 + test_sim_phase6_1 계약.
