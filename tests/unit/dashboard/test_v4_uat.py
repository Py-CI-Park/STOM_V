from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Callable


ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_uat_cli_exposes_explicit_execute_gate() -> None:
    # Given: the UAT command line boundary.
    # When: help is requested without launching a browser.
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "v4_uat.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )

    # Then: an explicit execution gate is documented.
    assert completed.returncode == 0
    assert "--execute" in completed.stdout


def test_uat_omitting_execute_is_nonzero_and_creates_no_output(tmp_path: Path) -> None:
    # Given: a fresh requested output path.
    out = tmp_path / "not-created"

    # When: execution authorization is omitted.
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "v4_uat.py"), "--out", str(out)],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )

    # Then: the command fails closed and leaves no misleading artifact.
    assert completed.returncode != 0
    assert "--execute is required" in completed.stderr
    assert not out.exists()


def test_uat_partial_result_cannot_exit_zero(monkeypatch, tmp_path: Path) -> None:
    # Given: an execution adapter that returns a misleading partial result.
    module = _load_script("v4_uat")
    monkeypatch.setattr(module, "execute", lambda _out: ({"status": "partial"}, True))

    # When/Then: main rejects it even though cleanup claims success.
    assert module.main(["--execute", "--out", str(tmp_path / "partial")]) == 1


def test_uat_observer_classifies_console_page_request_and_non2xx() -> None:
    # Given: a page event adapter and empty observation receipt.
    module = _load_script("v4_uat")
    callbacks: dict[str, Callable] = {}

    class Page:
        def on(self, event: str, callback: Callable) -> None:
            callbacks[event] = callback

    class Request:
        method = "GET"
        url = "http://127.0.0.1:1/broken"
        failure = "net::ERR_FAILED"

    class Response:
        status = 500
        url = Request.url
        request = Request()

    class Message:
        type = "error"
        text = "canvas draw exploded"

    obs = module.Observation()
    module._observe(Page(), obs)

    # When: every unclassified browser error channel fires.
    callbacks["console"](Message())
    callbacks["pageerror"](RuntimeError("page exploded"))
    callbacks["requestfailed"](Request())
    callbacks["response"](Response())

    # Then: none is ignored.
    assert obs.console_errors == ["canvas draw exploded"]
    assert obs.page_errors == ["page exploded"]
    assert len(obs.request_failures) == 1
    assert len(obs.unexpected_responses) == 1


def test_uat_capture_rejects_noop_or_wrong_run_marker(tmp_path: Path) -> None:
    # Given: a screenshot writer whose DOM event counter never advances and marker is stale.
    module = _load_script("v4_uat")

    class Locator:
        def __init__(self, value: str) -> None:
            self.value = value

        def get_attribute(self, _name: str) -> str:
            return self.value

        def inner_text(self) -> str:
            return self.value

    class Page:
        def screenshot(self, *, path: str) -> None:
            Path(path).write_bytes(b"x" * 256)

        def locator(self, selector: str) -> Locator:
            return Locator("7" if selector == "body" else "old-run")

    # When: the capture is evaluated against this execution.
    receipt = module._capture(Page(), tmp_path, "research", "new-run", 0, 7)

    # Then: it is rejected despite being non-empty and freshly written.
    assert receipt["valid"] is False
    assert receipt["dom_state_changed"] is False


def test_capture_rejects_duplicate_or_unknown_inventory() -> None:
    # Given: the capture boundary parser.
    module = _load_script("v4_capture")

    # When/Then: duplicate, empty and unknown inventories fail before browser launch.
    for raw in ("research,research", "", "research,live"):
        try:
            module.parse_inventory(raw, module.VIEWS, "views")
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid inventory accepted: {raw}")


def test_capture_cli_rejects_duplicate_tabs_before_output(tmp_path: Path) -> None:
    # Given: a malformed duplicate capture request.
    module = _load_script("v4_capture")
    out = tmp_path / "captures"

    # When/Then: it fails before browser/output creation.
    assert module.main(["--base", "http://127.0.0.1:1", "--out", str(out), "--views", "research,research"]) == 2
    assert not out.exists()


def test_archive_cli_rejects_malformed_or_duplicate_runs(tmp_path: Path) -> None:
    # Given: malformed archive identifiers at the command boundary.
    module = _load_script("v4_archive_check")

    # When/Then: unsafe and duplicate values fail before browser/output creation.
    for index, raw in enumerate(("../operating.db", "run-1,run-1", "")):
        out = tmp_path / f"archive-{index}"
        assert module.main(["--base", "http://127.0.0.1:1", "--runs", raw, "--out", str(out)]) == 2
        assert not out.exists()


def test_capture_chrome_launch_failure_has_no_fallback(monkeypatch, tmp_path: Path) -> None:
    # Given: installed Chrome launch fails and records every attempted launch.
    module = _load_script("v4_capture")
    calls: list[dict[str, str | bool]] = []

    class Chromium:
        def launch(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("installed Chrome unavailable")

    class Playwright:
        chromium = Chromium()

    class Manager:
        def __enter__(self):
            return Playwright()

        def __exit__(self, *_args) -> None:
            return None

    fake = ModuleType("playwright.sync_api")
    fake.sync_playwright = lambda: Manager()
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake)
    out = tmp_path / "capture-failed"

    # When: capture tries to launch the required installed Chrome.
    result = module.main(["--base", "http://127.0.0.1:1", "--out", str(out)])

    # Then: one exact channel launch occurs and no bundled fallback is attempted.
    assert result == 1
    assert calls == [{"channel": "chrome", "headless": True}]
    report = (out / "capture-report.json").read_text(encoding="utf-8")
    assert "installed Chrome unavailable" in report


def test_archive_chrome_launch_failure_has_no_fallback(monkeypatch, tmp_path: Path) -> None:
    # Given: the archive checker sees an installed-Chrome launch failure.
    module = _load_script("v4_archive_check")
    calls: list[dict[str, str | bool]] = []

    class Chromium:
        def launch(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("installed Chrome unavailable")

    class Playwright:
        chromium = Chromium()

    class Manager:
        def __enter__(self):
            return Playwright()

        def __exit__(self, *_args) -> None:
            return None

    fake = ModuleType("playwright.sync_api")
    fake.sync_playwright = lambda: Manager()
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake)
    out = tmp_path / "archive-failed"

    # When/Then: it fails after one channel=chrome attempt and emits a failure report.
    assert module.main(["--base", "http://127.0.0.1:1", "--runs", "run-1", "--out", str(out)]) == 1
    assert calls == [{"channel": "chrome", "headless": True}]
    assert "installed Chrome unavailable" in (out / "archive-report.json").read_text(encoding="utf-8")


def test_uat_rejects_conforming_synthetic_ui_fixture() -> None:
    # Given: a synthetic UI fixture that could imitate the product DOM.
    module = _load_script("v4_uat")

    # When/Then: the former synthetic fixture path is rejected before serving.
    try:
        module._fixture_app("fake-run", [])
    except RuntimeError as exc:
        assert "synthetic UI fixtures are rejected" in str(exc)
    else:
        raise AssertionError("synthetic UI fixture was accepted")


def test_capture_and_archive_reject_hash_self_consistent_nonproduct_bundle() -> None:
    # Given: a fake bundle containing every marker and a self-consistent URL hash.
    payload = b"winner_gen review_hash evidence_hash buy_code_hash sell_code_hash fake"
    digest = hashlib.sha256(payload).hexdigest()
    url = f"http://127.0.0.1/ui/bundle/app.js?v={digest[:8]}"

    # When/Then: both tools reject it because it is not the repository product bundle.
    for name in ("v4_capture", "v4_archive_check"):
        module = _load_script(name)
        assert module.product_identity_valid(url, payload, "0" * 64) is False
        assert module.product_identity_valid(url, payload, digest) is False
        identity = {
            "html_sha256": "h",
            "expected_html_sha256": "h",
            "css_sha256": ["c"],
            "expected_css_sha256": ["c"],
            "source_graph_sha256": "s",
            "expected_source_graph_sha256": "s",
        }
        assert module.product_identity_valid(url, payload, digest, **identity) is True
        identity["html_sha256"] = hashlib.sha256(b"fake copied-bundle server").hexdigest()
        assert module.product_identity_valid(url, payload, digest, **identity) is False


def test_archive_outcome_requires_active_history_and_visible_exact_alert() -> None:
    module = _load_script("v4_uat")
    valid = {
        "active_tab": "history",
        "panel_visible": True,
        "alert_visible": True,
        "alert_text": "아카이브 run 로드 실패 · ARCHIVE_FAIL · HTTP 503",
        "alert_in_viewport": True,
    }

    assert module.archive_outcome_valid(valid)
    for key, bad in (
        ("active_tab", "lab"),
        ("panel_visible", False),
        ("alert_visible", False),
        ("alert_text", "fixture archive unavailable"),
        ("alert_in_viewport", False),
    ):
        receipt = dict(valid)
        receipt[key] = bad
        assert not module.archive_outcome_valid(receipt)


def test_default_off_denial_requires_observed_matching_browser_close() -> None:
    module = _load_script("v4_uat")
    payload = {"action": "final_approval", "run_id": "uat-123"}

    assert module.default_off_denial_valid(
        payload,
        {"code": 4403, "reason": "capability_disabled", "url": "ws://127.0.0.1/ws"},
    )
    assert not module.default_off_denial_valid(payload, {})
    assert not module.default_off_denial_valid(payload, {"code": 4403, "reason": "hard-coded"})
    assert not module.default_off_denial_valid({}, {"code": 4403, "reason": "capability_disabled"})


def test_capture_inventory_is_exactly_all_eight_unique_tabs() -> None:
    # Given: the capture inventory.
    module = _load_script("v4_capture")

    # When/Then: History is present and the complete inventory is exact and duplicate-free.
    assert module.VIEWS == [
        "research",
        "backtest",
        "replay",
        "history",
        "lab",
        "workbench",
        "audit",
        "context",
    ]
    assert len(module.VIEWS) == len(set(module.VIEWS)) == 8
