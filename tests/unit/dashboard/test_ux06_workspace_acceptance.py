"""UX-06 — 14 연구 페이지 수용 감사 + Holdout 용어 정본 계약.

각 연구 표면이 V4 셸에 배선돼 있고, 권위·정체성·차단 사유·다음 행동 증거를
렌더하는지 소스 수준으로 강제한다. 용어 정본:
  internal_validation_split / graduation_validation / FROZEN_OOS_HOLDOUT
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FE = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"
BE = ROOT / "ai_strategy_loop" / "dashboard"


def _read(name: str) -> str:
    return (FE / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------- 14 surfaces

def test_v4_shell_tab_registry_covers_required_surfaces():
    shell = _read("dashboard-v4-shell.jsx")
    for key in ("research", "history", "reports", "workbench",
                "backtest", "replay", "catalog", "settings", "glossary"):
        assert f'key: "{key}"' in shell, f"V4 탭 누락: {key}"


def test_research_surfaces_exist_and_are_wired():
    shell = _read("dashboard-v4-shell.jsx")
    # P01 종합/미션, P05 리플레이, P13 보고서, P14 설정, 용어
    for comp in ("V4ResearchLive", "V4Backtest", "V4Replay",
                 "V4HistoryWithAuthority", "V4Reports", "V4Catalog",
                 "V4SettingsTab", "V4GlossaryTab"):
        assert comp in shell, f"V4 셸 배선 누락: {comp}"


def test_decision_result_page_renders_authority_and_next_gate():
    src = _read("v4-research-result.jsx")
    assert "next_gate" in src
    assert "DEVELOPMENT ONLY" in src
    assert "SEALED DECISION / READ ONLY" in src


def test_failure_autopsy_marks_no_adoption_authority():
    src = _read("v4-research-failure-autopsy.jsx")
    assert "자동채택 권한 없음" in src


def test_hypothesis_registry_exposes_machine_readable_states():
    src = (BE / "hypothesis_registry.py").read_text(encoding="utf-8")
    for state in ("HYPOTHESIS_DRAFT", "ACCEPTED_FOR_PREREG",
                  "PREREG_DRAFT", "PREREG_SEALED", "REJECTED", "NEEDS_DATA"):
        assert state in src, f"상태 머신 누락: {state}"
    assert "seal_requires_human_approval" in src


# ---------------------------------------------------------------- terminology

def test_holdout_terminology_canonical_split():
    glossary = _read("v4-glossary.jsx")
    for term in ("internal_validation_split", "graduation_validation",
                 "FROZEN_OOS_HOLDOUT"):
        assert term in glossary, f"용어 정본 누락: {term}"


def test_frozen_oos_labelled_in_result_workspace():
    src = _read("v4-research-result.jsx")
    assert "FROZEN_OOS" in src
    assert "사람 승인" in src or "승인" in src


def test_internal_split_labelled_in_oos_gate():
    src = _read("bt-oos-gate.jsx")
    assert "internal_validation_split" in src
    # split-mode 홀드아웃이 독립 OOS로 표시되면 안 된다.
    assert "독립 OOS 가 아닙니다" in src


def test_graduation_validation_labelled_in_holdout_panel():
    src = _read("panels-analysis.jsx")
    assert "graduation_validation" in src
    assert "FROZEN_OOS_HOLDOUT" in src


# ---------------------------------------------------------------- compiled bundle

def test_compiled_bundle_contains_ux06_markers():
    bundle = FE / "bundle" / "app.js"
    src = bundle.read_text(encoding="utf-8", errors="replace")
    for marker in ("internal_validation_split", "graduation_validation",
                   "FROZEN_OOS"):
        assert marker in src, f"번들 미반영: {marker}"
