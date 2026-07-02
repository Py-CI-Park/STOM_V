from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"
APP = REMODEL / "src" / "app.js"
THEME = REMODEL / "styles" / "theme.css"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_decision_audit_exports_append_only_contracts_and_payload_builder() -> None:
    app = _text(APP)

    for marker in [
        "const DecisionAuditContracts = [",
        "function decisionAuditDraftContext(input = {})",
        "function buildRecordDecisionPayload(draft = decisionAuditDraftContext())",
        "function validateRecordDecisionPayload(payload)",
        "function recordDecisionAfterConfirm(payload, confirmFn = window.confirm)",
        "function renderDecisionAuditSurface(draft = decisionAuditDraftContext())",
        "const DecisionAuditAdapter = {",
        "window.DecisionAuditSurface = {",
        "draftContext: decisionAuditDraftContext",
        "buildPayload: buildRecordDecisionPayload",
        "validatePayload: validateRecordDecisionPayload",
        "recordAfterConfirm: recordDecisionAfterConfirm",
        "render: renderDecisionAuditSurface",
    ]:
        assert marker in app

    for endpoint in ["/decisions", "/record_decision"]:
        assert endpoint in app


def test_decision_audit_ui_is_manual_gated_and_separate_from_export_approval() -> None:
    app = _text(APP)
    theme = _text(THEME)

    for marker in [
        "data-decision-audit-surface",
        'data-decisions-endpoint="/decisions"',
        'data-record-decision-endpoint="/record_decision"',
        'data-record-decision-gate="manual-confirm-required"',
        "data-record-decision-payload",
        "data-record-decision-disabled-reason",
        'data-approval-boundary="separate-route"',
        "Append-only record only; this does not export or place orders.",
        "final approval remains separate from /record_decision.",
        "Missing verdict/note/context blocks record_decision.",
        "Record failure, duplicate context, missing context, and validation errors stay visible.",
    ]:
        assert marker in app

    for marker in [
        ".decision-audit-surface",
        ".decision-contract-grid",
        ".decision-context-grid",
        ".decision-record-grid",
        ".decision-draft-card",
        ".decision-boundary-card",
    ]:
        assert marker in theme

    surface_block = app.split("function renderDecisionAuditSurface", 1)[1].split("const DecisionAuditAdapter", 1)[0]
    assert "new WebSocket" not in surface_block
    assert "/bt/run" not in surface_block
    assert "final_approval" not in app
