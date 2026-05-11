from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


NEXT_CANDIDATE = "gui-setting-sidecar-persistence-design"

HELD_ITEMS = (
    {
        "item": "formula-global-runtime-hook",
        "risk": "high",
        "status": "defer",
        "reason": "VERIFY-1A protects trade runtime files and live formula namespace mutation.",
    },
    {
        "item": "gui-setting-persistence",
        "risk": "medium",
        "status": "next",
        "reason": "Can be specified as sidecar design before any setting.db or runtime trade mutation.",
    },
    {
        "item": "analyzer-db-constructor-runtime-use",
        "risk": "high",
        "status": "defer",
        "reason": "Needs production DB read boundary, locking policy, and rollback proof.",
    },
    {
        "item": "live-order-exit-rule-consumption",
        "risk": "critical",
        "status": "defer",
        "reason": "Touches live trading decisions and must follow mock/backtest proof.",
    },
    {
        "item": "production-learning-db-read",
        "risk": "high",
        "status": "defer",
        "reason": "Needs read-only production DB lock/performance/rollback evidence.",
    },
    {
        "item": "db-cutover-migration",
        "risk": "critical",
        "status": "defer",
        "reason": "Needs migration, backup, cutover, and rollback plan before implementation.",
    },
)

REQUIRED_DOCS = (
    "docs/update_log/2026-05-12_v3k_phase_d2_formula_runtime_hook_decision.md",
    "docs/update_log/2026-05-12_v3k_phase_e0_runtime_activation_gap_review.md",
    "docs/plans/2026-05-12_v3k_page_019_phase_e0_runtime_activation_gap_review_plan.md",
    "docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md",
)

RUNTIME_GUARDED_FILES = (
    "trade/base_strategy.py",
    "trade/formula_manager.py",
)


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _assert_required_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing runtime activation review docs: {missing}")


def _assert_single_next_candidate() -> None:
    next_items = [item for item in HELD_ITEMS if item["status"] == "next"]
    if [item["item"] for item in next_items] != ["gui-setting-persistence"]:
        raise AssertionError(f"unexpected next runtime activation candidates: {next_items}")
    if NEXT_CANDIDATE != "gui-setting-sidecar-persistence-design":
        raise AssertionError(f"unexpected next candidate slug: {NEXT_CANDIDATE}")


def _assert_trade_runtime_guard_still_active() -> None:
    audit = (ROOT / "scripts" / "audit_v3k_verify_1a.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    for guarded_file in RUNTIME_GUARDED_FILES:
        if f'"{guarded_file}"' not in audit:
            raise AssertionError(f"VERIFY-1A no longer guards {guarded_file}")

    hits: list[str] = []
    for rel_path in RUNTIME_GUARDED_FILES:
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if "V3K" in text or "v3k_" in text.lower():
            hits.append(rel_path)
    if hits:
        raise AssertionError(f"runtime guarded files unexpectedly reference V3K: {hits}")


def _assert_no_runtime_artifacts_changed() -> None:
    status = _run_git(
        "status",
        "--short",
        "--",
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
        "v3k_settings*.json",
    )
    if status:
        raise AssertionError(f"runtime artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_single_next_candidate()
    _assert_trade_runtime_guard_still_active()
    _assert_no_runtime_artifacts_changed()

    print("V3K runtime activation gap audit passed")
    print(f"Next candidate: {NEXT_CANDIDATE}")
    print("Held item matrix:")
    for item in HELD_ITEMS:
        print(f"  - {item['item']}: {item['status']} ({item['risk']})")


if __name__ == "__main__":
    main()
