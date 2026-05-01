from pathlib import Path

import json
import pytest
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from gui_contract_manifest import ContractItem
import smoke_offline_gui as smoke


def test_offline_guard_raises_and_records_violation():
    guard = smoke.OfflineGuard()

    with pytest.raises(smoke.OfflineViolation):
        guard.violation("network", "requests GET")

    assert guard.events == [{"kind": "blocked_network", "detail": "requests GET"}]


def test_check_attr_requires_widget_presence():
    class Window:
        existing_button = object()

    passed = smoke.check_attr(
        ContractItem("strategy_button", "id1", "existing", "existing_button", "source.py"),
        Window(),
    )
    failed = smoke.check_attr(
        ContractItem("strategy_button", "id2", "missing", "missing_button", "source.py"),
        Window(),
    )

    assert passed.result == "passed"
    assert failed.result == "failed"
    assert "missing_button" in failed.detail


def test_write_log_uses_branch_and_version_specific_filename(tmp_path):
    payload = {"status": "passed"}

    path = smoke.write_log(payload, tmp_path, "STOM_Version_2U", "V2.78")

    assert path.name == "smoke_STOM_Version_2U_V2_78.json"
    assert json.loads(path.read_text(encoding="utf-8")) == payload

