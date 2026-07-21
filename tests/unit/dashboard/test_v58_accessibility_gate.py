"""Contracts for the local-only V5.8 Playwright/axe accessibility gate."""
from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "verify_dashboard_v58_accessibility.py"
spec = importlib.util.spec_from_file_location("verify_dashboard_v58_accessibility", SCRIPT)
assert spec and spec.loader
v58 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v58)


class FakeAxePage:
    def __init__(self, violations):
        self.violations = violations

    def evaluate(self, _script):
        return {"version": "4.10.2", "result": {"violations": self.violations}}


def test_axe_boundary_only_hard_fails_serious_and_critical():
    page = FakeAxePage([
        {"id": "minor-only", "impact": "minor", "nodes": [{}]},
        {"id": "serious-rule", "impact": "serious", "nodes": [{}, {}]},
        {"id": "critical-rule", "impact": "critical", "nodes": [{}]},
    ])

    assert v58._axe_errors(page) == [
        {"id": "serious-rule", "impact": "serious", "nodes": "2", "targets": []},
        {"id": "critical-rule", "impact": "critical", "nodes": "1", "targets": []},
    ]


def test_axe_boundary_failure_is_a_failed_case_not_a_skipped_check(tmp_path):
    class BrokenPage:
        def goto(self, *_args, **_kwargs):
            raise RuntimeError("browser unavailable")

        def close(self):
            pass

    class BrokenBrowser:
        def new_page(self, **_kwargs):
            return BrokenPage()

    source = tmp_path / "axe.min.js"
    source.write_text("window.axe = {};", encoding="utf-8")
    case = v58._run_case(BrokenBrowser(), "http://127.0.0.1:8000/ui/", source, "4.10.2", "research",
                         375, "dark", "reduce", 1000)
    assert case["passed"] is False
    assert case["axe"] == []
    assert "browser boundary failed" in case["errors"][0]


def test_main_fails_closed_and_emits_json_when_gate_raises():
    output = io.StringIO()
    with patch.object(v58, "run_gate", side_effect=RuntimeError("axe injection failed")), redirect_stdout(output):
        exit_code = v58.main(["--base-url", "http://127.0.0.1:9999/ui/"])

    assert exit_code == 1
    assert '"status":"failed"' in output.getvalue()
    assert "axe injection failed" in output.getvalue()


def test_external_base_urls_are_rejected_before_browser_startup():
    with pytest.raises(SystemExit):
        v58.parse_args(["--base-url", "https://example.invalid/ui/"])
    for url in (
        "http://127.0.0.1.evil.invalid/ui/",
        "http://localhost.evil.invalid/ui/",
        "http://user@127.0.0.1:8000/ui/",
        "http://127.0.0.1@evil.invalid/ui/",
        "http://[::1].evil.invalid/ui/",
    ):
        with pytest.raises(SystemExit):
            v58.parse_args(["--base-url", url])


def test_exact_loopback_authorities_accept_ipv6_and_reject_stale_or_stub_axe():
    assert v58._assert_loopback_url("http://localhost:8000/ui/") == "http://localhost:8000/ui/"
    assert v58._assert_loopback_url("http://127.0.0.1:8000/ui/") == "http://127.0.0.1:8000/ui/"
    assert v58._assert_loopback_url("http://[::1]:8000/ui/") == "http://[::1]:8000/ui/"

    class StubAxePage:
        def evaluate(self, _script):
            return {"version": "", "result": {"violations": []}}

    with pytest.raises(v58.GateError, match="runtime did not report a version"):
        v58._axe_violations(StubAxePage())
    with pytest.raises(v58.GateError, match="does not match installed"):
        v58._assert_axe_runtime_version("4.9.0", "4.10.2")


def test_axe_evidence_preserves_minor_violations_while_hard_impacts_block():
    page = FakeAxePage([
        {"id": "minor-only", "impact": "minor", "nodes": [{}]},
        {"id": "serious-rule", "impact": "serious", "nodes": [{}]},
    ])
    version, violations = v58._axe_violations(page)

    assert version == "4.10.2"
    assert [violation["id"] for violation in violations] == ["minor-only", "serious-rule"]
    assert [violation["id"] for violation in v58._axe_errors(page)] == ["serious-rule"]
def test_persistent_active_shadow_does_not_satisfy_focus_contract():
    class Locator:
        def __init__(self, name):
            self.name = name
            self.evaluate_calls = 0

        def click(self):
            pass

        def focus(self):
            pass

        def press(self, key):
            assert key == "ArrowRight"

        def count(self):
            return 1

        def get_attribute(self, name):
            if self.name == "tablist":
                return "horizontal"
            if name == "id":
                return "v4-tab-history"
            return None

        def evaluate(self, _script):
            self.evaluate_calls += 1
            if self.evaluate_calls == 1:
                return {"active": True, "outlinePainted": False, "shadowPainted": True,
                        "outlineStyle": "solid", "outlineWidth": "2px", "outlineColor": "rgba(0, 0, 0, 0)",
                        "boxShadow": "inset 3px 0 0 teal"}
            if self.evaluate_calls == 2:
                return None
            return {"outlineStyle": "none", "outlineWidth": "0px", "outlineColor": "rgba(0, 0, 0, 0)",
                    "boxShadow": "inset 3px 0 0 teal"}

    class Page:
        def __init__(self):
            self.selected = Locator("selected")

        def locator(self, selector):
            if "tablist" in selector:
                return Locator("tablist")
            if selector == "#v4-tab-research":
                return Locator("research")
            return self.selected

    assert v58._keyboard_and_focus_contract(Page()) == [
        "keyboard focus has no focus-only painted visible indicator on the V4 rail"
    ]


def test_transparent_or_offset_only_focus_does_not_satisfy_focus_contract():
    class Locator:
        def __init__(self, name):
            self.name = name
            self.evaluate_calls = 0

        def click(self):
            pass

        def focus(self):
            pass

        def press(self, _key):
            pass

        def count(self):
            return 1

        def get_attribute(self, name):
            if self.name == "tablist":
                return "horizontal"
            if name == "id":
                return "v4-tab-history"
            return None

        def evaluate(self, _script):
            self.evaluate_calls += 1
            if self.evaluate_calls == 1:
                return {"active": True, "outlinePainted": False, "shadowPainted": False,
                        "outlineStyle": "solid", "outlineWidth": "2px",
                        "outlineColor": "rgba(0, 0, 0, 0)", "boxShadow": "none"}
            if self.evaluate_calls == 2:
                return None
            return {"outlineStyle": "none", "outlineWidth": "0px",
                    "outlineColor": "rgba(0, 0, 0, 0)", "boxShadow": "none"}

    class Page:
        def __init__(self):
            self.selected = Locator("selected")

        def locator(self, selector):
            if "tablist" in selector:
                return Locator("tablist")
            if selector == "#v4-tab-research":
                return Locator("research")
            return self.selected

    assert v58._keyboard_and_focus_contract(Page()) == [
        "keyboard focus has no focus-only painted visible indicator on the V4 rail"
    ]


def test_loopback_redirect_and_websocket_authorities_are_rejected():
    assert v58._websocket_is_external("wss://example.invalid/socket") is True
    assert v58._websocket_is_external("ws://127.0.0.1:8000/socket") is False
    with pytest.raises(v58.GateError, match="exact loopback"):
        v58._assert_loopback_url("https://example.invalid/redirect")
def test_tab_url_replaces_existing_tab_query_and_strips_fragment():
    assert v58._with_tab("http://127.0.0.1:8000/ui/?filter=open&tab=history#reports", "research") == (
        "http://127.0.0.1:8000/ui/?filter=open&tab=research"
    )


def test_late_blocked_websocket_is_included_in_final_case_failure(tmp_path):
    class Response:
        url = "http://127.0.0.1:8000/ui/bundle/app.js"
        headers = {}

        def body(self):
            return b"bundle"

    class Locator:
        def __init__(self, selector):
            self.selector = selector

        def get_attribute(self, _name):
            return "dark" if self.selector == "html" else None

        def evaluate_all(self, _script):
            return [
                {"label": "dark", "pressed": True, "active": True},
                {"label": "light", "pressed": False, "active": False},
            ]

        def wait_for(self, **_kwargs):
            pass

    class Page:
        url = "http://127.0.0.1:8000/ui/?tab=research"

        def __init__(self):
            self.callbacks = {}

        def on(self, event, callback):
            self.callbacks[event] = callback

        def goto(self, *_args, **_kwargs):
            self.callbacks["response"](Response())

        def locator(self, selector):
            return Locator(selector)

        def wait_for_timeout(self, timeout):
            if timeout == 0:
                self.callbacks["websocket"](type("WebSocket", (), {"url": "wss://example.invalid/socket"})())

        def add_script_tag(self, **_kwargs):
            pass

        def evaluate(self, _script):
            return ["http://127.0.0.1:8000/ui/bundle/app.js"]

    class Context:
        def __init__(self):
            self.page = Page()
            self.websocket_handler = None

        def add_init_script(self, **_kwargs):
            pass

        def route(self, *_args):
            pass

        def route_web_socket(self, _pattern, handler):
            self.websocket_handler = handler

        def new_page(self):
            return self.page

        def close(self):
            pass

    class Browser:
        def __init__(self):
            self.context = None

        def new_context(self, **_kwargs):
            self.context = Context()
            return self.context


    axe_source = tmp_path / "axe.min.js"
    axe_source.write_text("window.axe = {};", encoding="utf-8")
    browser = Browser()
    with patch.object(v58, "_axe_violations", return_value=("4.10.2", [])), \
            patch.object(v58, "_tab_contract", return_value=[]), \
            patch.object(v58, "_overflow_contract", return_value=[]), \
            patch.object(v58, "_keyboard_and_focus_contract", return_value=[]):
        case = v58._run_case(browser, "http://127.0.0.1:8000/ui/", axe_source, "4.10.2", "research",
                             375, "dark", "reduce", 1000)

    assert case["passed"] is False
    assert case["errors"] == ["blocked non-loopback browser WebSockets: ['wss://example.invalid/socket']"]
    assert browser.context and browser.context.websocket_handler

    class WebSocketRoute:
        def __init__(self, url):
            self.url = url
            self.close_calls = []
            self.connected = False

        def close(self, **kwargs):
            self.close_calls.append(kwargs)

        def connect_to_server(self):
            self.connected = True

    external = WebSocketRoute("wss://example.invalid/socket")
    browser.context.websocket_handler(external)
    assert external.close_calls == [{"code": 1008, "reason": "non-loopback WebSocket blocked"}]
    assert external.connected is False

    loopback = WebSocketRoute("ws://127.0.0.1:8000/socket")
    browser.context.websocket_handler(loopback)
    assert loopback.close_calls == []
    assert loopback.connected is True


def test_readiness_rejects_local_redirect_without_following_it():
    class RedirectingOpener:
        def open(self, url, timeout):
            raise v58.HTTPError(url, 302, "Found", {}, None)

    with patch.object(v58, "build_opener", return_value=RedirectingOpener()) as build_opener:
        with pytest.raises(v58.GateError, match="readiness probe redirected"):
            v58._wait_for_server("http://127.0.0.1:8000/ui/", 1)

    assert isinstance(build_opener.call_args.args[0], v58._NoRedirect)


def test_run_case_requires_websocket_routing_support(tmp_path):
    class ContextWithoutWebSocketRouting:
        def add_init_script(self, **_kwargs):
            pass

        def route(self, *_args):
            pass

        def close(self):
            pass

    class Browser:
        def new_context(self, **_kwargs):
            return ContextWithoutWebSocketRouting()

    axe_source = tmp_path / "axe.min.js"
    axe_source.write_text("window.axe = {};", encoding="utf-8")
    case = v58._run_case(Browser(), "http://127.0.0.1:8000/ui/", axe_source, "4.10.2", "research",
                         375, "dark", "reduce", 1000)

    assert case["passed"] is False
    assert "route_web_socket support is required" in case["errors"][0]
