from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_program_overview_is_wired_into_v4_research_only():
    research = _source("v4-research.jsx")
    component = _source("v4-research-program.jsx")
    legacy = _source("app.jsx")
    assert 'import { V516ResearchProgramOverview } from "./v4-research-program.jsx"' in research
    assert "<V516ResearchProgramOverview baseUrl={baseUrl}" in research
    assert "/research-program/summary" in component
    assert "V516ResearchProgramOverview" not in legacy


def test_program_overview_separates_platform_and_economic_verdicts():
    source = _source("v4-research-program.jsx")
    assert 'label="플랫폼"' in source
    assert 'label="경제 판정"' in source
    assert "플랫폼 PASS와 경제적 성공은 별도 판정" in source
    assert "DEVELOPMENT ONLY" in source
    assert "OOS·실전·자동채택 근거가 아닙니다" in source
    assert "승인 후 Export" not in source
    assert "final_approval" not in source


def test_scope_funnel_timeline_and_failure_states_are_accessible():
    source = _source("v4-research-program.jsx")
    for marker in (
        'role="list"',
        'aria-label="연구 데이터 범위와 권위"',
        'aria-label="조건식 연구 퍼널"',
        'role="alert"',
        "다시 시도",
        "D1",
        "D2",
        "PAIRED",
    ):
        assert marker in source


def test_program_overview_css_has_responsive_and_reduced_motion_contracts():
    css = _source("v4.css")
    assert ".rp16-overview" in css
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 430px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "minmax(0, 1fr)" in css


def test_family_explorer_and_fold_heatmap_are_v4_read_only_surfaces():
    research = _source("v4-research.jsx")
    source = _source("v4-research-family.jsx")
    assert 'import { V516FamilyFoldExplorer } from "./v4-research-family.jsx"' in research
    assert "<V516FamilyFoldExplorer baseUrl={baseUrl}" in research
    assert "/research-program/families" in source
    assert "/research-program/folds" in source
    assert "Development fold evidence · OOS 아님" in source
    assert "표본부족" in source
    assert "색상과 함께 상태 텍스트" in source
    assert "fetch(" in source
    assert "method:" not in source


def test_family_fold_css_has_keyboard_scroll_and_color_independent_patterns():
    css = _source("v4.css")
    source = _source("v4-research-family.jsx")
    assert 'tabIndex={0}' in source
    assert ".rf16-fold-scroll:focus-visible" in css
    assert "repeating-linear-gradient" in css
    assert ".rf16-cell.insufficient" in css


def test_failure_atlas_and_evidence_inspector_use_allowlisted_read_only_api():
    research = _source("v4-research.jsx")
    source = _source("v4-research-evidence.jsx")
    assert 'import { V516FailureEvidence } from "./v4-research-evidence.jsx"' in research
    assert "<V516FailureEvidence baseUrl={baseUrl}" in research
    assert "/research-program/failures" in source
    assert "/research-program/evidence/" in source
    for state in ("PROVEN", "REFUTED", "FIXED", "OPEN", "LIMITATION"):
        assert state in source
    assert "source_missing" not in source
    assert "method:" not in source
    assert "경제적 성공 권한은 부여하지 않습니다" in source


def test_evidence_inspector_is_bounded_and_keyboard_accessible():
    source = _source("v4-research-evidence.jsx")
    css = _source("v4.css")
    assert ".slice(0, 12000)" in source
    assert "<pre tabIndex={0}>" in source
    assert ".re16-evidence pre:focus-visible" in css
    assert 'aria-pressed={evidence.id === id}' in source


def test_market_cap_native_health_and_designer_are_wired():
    research = _source("v4-research.jsx")
    source = _source("v4-research-mcap.jsx")
    assert 'import { V516MarketCapNativeLab } from "./v4-research-mcap.jsx"' in research
    assert "<V516MarketCapNativeLab baseUrl={baseUrl}" in research
    assert "/research-program/market-cap-census" in source
    assert "/research-program/jobs/health" in source
    assert "/research-program/preregistration/preview" in source
    for marker in ("BackFinder", "OptimizeConditions", "Genetic", "QMC/TPE", "RWFT"):
        assert marker in source
    assert 'min="24" max="48"' in source
    assert 'min="1" max="8"' in source
    assert 'min="1" max="6"' in source
    assert "저장·실행·승인·Export를 수행하지 않습니다" in source


def test_market_cap_lab_preserves_four_band_and_source_missing_states():
    source = _source("v4-research-mcap.jsx")
    css = _source("v4.css")
    assert "시가총액 4개 고정 구간" in source
    assert "SOURCE_MISSING" in source
    assert "immutable connector N0 통과 전 실행 금지" in source
    assert ".rm16-band-grid" in css
    assert "@media (max-width: 460px)" in css
