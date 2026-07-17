"""셸 배선 파리티 가드 — 2026-07-17 전수검사 재발 방지 #1.

배경: v4.1 History 트리·A/B 시각화가 legacy 셸(app.jsx)에만 배선되고 V4 graph-first
셸(v4-*.jsx)엔 누락돼, "V4를 열면 신기능이 안 보이는" 신뢰 훼손 버그가 발생했다.
셋 다 단일 번들을 공유하므로 컴파일·테스트는 통과해 조용히 새어나갔다.

이 테스트는 **legacy 셸이 렌더하는 컴포넌트는 V4 셸 트리도 렌더한다**를 소스 대조로
강제한다. 예외는 아래 WHITELIST(셸 크롬·레이아웃 헬퍼·V4 상위호환 대체)뿐이며, 새
연구/분석 패널이 legacy 에만 추가되면 화이트리스트에 없어 테스트가 실패한다 →
개발자는 V4(v4-*.jsx)에도 배선하거나, 명시적 사유와 함께 화이트리스트에 등록해야 한다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"

_TAG = re.compile(r"<([A-Z][A-Za-z0-9]+)[\s/>]")


def _tags(path: Path) -> set[str]:
    return set(_TAG.findall(path.read_text(encoding="utf-8")))


# legacy 셸에만 존재해도 되는 컴포넌트 = V4 레일/토프바/온보딩이 대체했거나 상위호환.
#   연구/분석 데이터 패널은 여기에 없어야 한다(있으면 그 자체가 배선 누락 신호).
_LEGACY_ONLY_WHITELIST = {
    "App": "V4는 DashboardV4Shell 이 루트",
    "TabNav": "V4 좌측 레일이 대체",
    "EvolutionSubtabNav": "V4 좌측 레일이 대체",
    "ResearchSuiteCards": "V4 레일/온보딩이 대체",
    "IdleState": "V4ResearchLive 온보딩이 대체",
    "RunSelector": "V4RunControls 가 대체",
    "BaseUrlControl": "V4BaseControl 이 대체",
    "ThemeToggle": "V4ThemeToggle 이 대체",
    "SunMoonIcon": "V4ThemeToggle 내부 아이콘이 대체",
    "Logo": "V4 레일 인라인 SVG 로고가 대체",
    "MetricList": "V4 토프바가 대체",
    "UiStateBlock": "V4 토프바/안전 strip 이 대체",
    "SectionLabel": "V4 stom-section-label 마크업이 대체",
    "FitnessChart": "V4HeroChart(대형 canvas)가 상위호환 대체",
    "LabPage": "V4Lab 이 하부 패널(Heatmap/Lab/Wiki)을 직접 마운트",
    "ProPage": "V4Workbench 가 하부 패널(Pro/RunCompare/HoF)을 직접 마운트",
}


def _v4_tree_tags() -> set[str]:
    tags: set[str] = set()
    for path in sorted(FRONTEND.glob("v4-*.jsx")):
        tags |= _tags(path)
    tags |= _tags(FRONTEND / "dashboard-v4-shell.jsx")
    return tags


def test_v4_shell_mounts_every_legacy_research_panel() -> None:
    legacy = _tags(FRONTEND / "app.jsx")
    v4 = _v4_tree_tags()

    legacy_only = legacy - v4
    unexplained = sorted(legacy_only - set(_LEGACY_ONLY_WHITELIST))

    assert not unexplained, (
        "legacy 셸(app.jsx)에만 배선되고 V4 셸(v4-*.jsx)에 누락된 컴포넌트: "
        f"{unexplained}. 신규 연구/분석 패널이라면 V4 탭에도 마운트하라(이번 전수검사에서 "
        "History 트리·A/B 시각화가 이 경로로 누락됐다). 셸 크롬/상위호환 대체라면 "
        "_LEGACY_ONLY_WHITELIST 에 사유와 함께 등록하라."
    )


def test_whitelist_stays_minimal_and_has_no_stale_entries() -> None:
    # 화이트리스트가 실제로 legacy-only 인 항목만 담아 과잉 억제를 막는다(부패 방지).
    legacy = _tags(FRONTEND / "app.jsx")
    v4 = _v4_tree_tags()
    legacy_only = legacy - v4
    stale = sorted(set(_LEGACY_ONLY_WHITELIST) - legacy_only)
    assert not stale, (
        f"화이트리스트에 더 이상 legacy-only 가 아닌 stale 항목이 있다: {stale}. "
        "제거하거나 배선 상태를 재확인하라."
    )


def test_v4_history_tab_mounts_ported_research_visualizations() -> None:
    # 이번 전수검사에서 실제 누락됐던 4개 패널이 V4 History 탭에 배선돼 있는지 직접 단정.
    v4_history = (FRONTEND / "v4-history.jsx").read_text(encoding="utf-8")
    for panel in ("HistoryConditionTreePanel", "AbPairCompareView", "CellHeatmap", "HoldoutFunnel"):
        assert f"<{panel} " in v4_history, f"V4 History 탭에 {panel} 미배선"
