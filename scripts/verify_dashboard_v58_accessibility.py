#!/usr/bin/env python3
"""Local-only Playwright + axe-core accessibility gate for the canonical V4 UI.

The verifier never downloads browser scripts or contacts a CDN: axe is injected from
webui-build/node_modules and the dashboard is either supplied by --base-url or
started on loopback for the duration of the check.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
WEBUI_BUILD = ROOT / "ai_strategy_loop" / "dashboard" / "webui-build"
AXE_SOURCE = WEBUI_BUILD / "node_modules" / "axe-core" / "axe.min.js"
AXE_PACKAGE = WEBUI_BUILD / "node_modules" / "axe-core" / "package.json"
APP_BUNDLE = ROOT / "ai_strategy_loop" / "dashboard" / "frontend" / "bundle" / "app.js"
TABS = ("research", "history", "reports", "workbench", "backtest", "replay", "catalog", "settings", "glossary")
VIEWPORTS = (375, 768, 1199, 1200, 1920, 2560, 3440)
THEMES = ("dark", "light")
MOTIONS = ("no-preference", "reduce")
HARD_IMPACTS = frozenset(("serious", "critical"))


class GateError(RuntimeError):
    """A deterministic, fail-closed gate failure."""
_ALLOWED_LOOPBACK_HOSTS = frozenset(("localhost", "127.0.0.1", "::1"))


def _assert_loopback_url(url: str) -> str:
    """Accept only credential-free HTTP(S) URLs addressed to an exact loopback host."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as error:
        raise GateError(f"invalid loopback URL: {url!r}") from error
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise GateError(f"URL must use an absolute HTTP(S) authority: {url!r}")
    if parsed.username is not None or parsed.password is not None:
        raise GateError(f"loopback URL must not include credentials: {url!r}")
    if parsed.hostname not in _ALLOWED_LOOPBACK_HOSTS:
        raise GateError(f"URL host is not an exact loopback authority: {url!r}")
    if port is not None and not 0 < port < 65536:
        raise GateError(f"loopback URL port is invalid: {url!r}")
    return url
def _websocket_is_external(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme not in ("ws", "wss"):
        return True
    try:
        _assert_loopback_url(("https" if parsed.scheme == "wss" else "http") + url[len(parsed.scheme):])
    except GateError:
        return True
    return False
def _append_network_boundary_errors(errors: list[str], blocked_requests: list[str],
                                    blocked_websockets: list[str]) -> None:
    if blocked_requests:
        errors.append(f"blocked non-loopback browser requests: {blocked_requests}")
    if blocked_websockets:
        errors.append(f"blocked non-loopback browser WebSockets: {blocked_websockets}")





def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _axe_identity(axe_source: Path) -> dict[str, str]:
    if not AXE_PACKAGE.is_file():
        raise GateError(f"local axe-core package metadata is missing: {AXE_PACKAGE}")
    try:
        installed = json.loads(AXE_PACKAGE.read_text(encoding="utf-8"))
        version = installed["version"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise GateError(f"local axe-core package metadata is invalid: {AXE_PACKAGE}") from error
    if not isinstance(version, str) or not version:
        raise GateError(f"local axe-core version is invalid: {AXE_PACKAGE}")
    return {"installedVersion": version, "sourceSha256": _sha256(axe_source)}


def _app_bundle_identity() -> dict[str, str]:
    if not APP_BUNDLE.is_file():
        raise GateError(f"dashboard app bundle is missing: {APP_BUNDLE}")
    return {"path": str(APP_BUNDLE.relative_to(ROOT)), "sha256": _sha256(APP_BUNDLE)}


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _NoRedirect(HTTPRedirectHandler):
    """Reject redirects so readiness never follows a loopback response externally."""

    def redirect_request(self, *_: object, **__: object) -> None:
        return None


def _wait_for_server(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    opener = build_opener(_NoRedirect())
    while time.monotonic() < deadline:
        try:
            with opener.open(url, timeout=1) as response:  # nosec B310: loopback URL only
                if 300 <= response.status < 400:
                    raise GateError(f"dashboard readiness probe redirected: {url}")
                if 200 <= response.status < 500:
                    return
        except HTTPError as error:
            if 300 <= error.code < 400:
                raise GateError(f"dashboard readiness probe redirected: {url}") from error
            time.sleep(0.1)
        except OSError:
            time.sleep(0.1)
    raise GateError(f"dashboard server did not become ready: {url}")


class _LocalDashboardServer:
    def __init__(self, timeout_seconds: float) -> None:
        self.port = _free_loopback_port()
        self.url = f"http://127.0.0.1:{self.port}/ui/"
        self.timeout_seconds = timeout_seconds
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> str:
        command = [
            sys.executable, "-m", "uvicorn", "ai_strategy_loop.dashboard.app:app",
            "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning",
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
        self.process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True)
        try:
            _wait_for_server(self.url, self.timeout_seconds)
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self.url

    def __exit__(self, *_: object) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def _with_tab(base_url: str, tab: str) -> str:
    parsed = urlsplit(base_url)
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "tab"]
    query.append(("tab", tab))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def _assert_local_axe_source() -> Path:
    if not AXE_SOURCE.is_file():
        raise GateError(f"local axe-core source is missing: {AXE_SOURCE}")
    _axe_identity(AXE_SOURCE)
    return AXE_SOURCE


def _assert_no_production_axe_import() -> None:
    frontend = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"
    for path in frontend.rglob("*.js*"):
        if "bundle" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "axe-core" in text or "from 'axe'" in text or 'from "axe"' in text:
            raise GateError(f"production frontend imports axe: {path.relative_to(ROOT)}")


def _tab_contract(page: Any, tab: str) -> list[str]:
    errors: list[str] = []
    page.locator(f"#v4-tab-{tab}").click()
    selected = page.locator('.v4-rail-tabs [role="tab"][aria-selected="true"]')
    if selected.count() != 1:
        errors.append(f"{tab}: expected exactly one selected V4 tab, found {selected.count()}")
    elif selected.get_attribute("id") != f"v4-tab-{tab}":
        errors.append(f"{tab}: selected V4 tab is {selected.get_attribute('id')!r}")
    panel = page.locator(f"#v4-panel-{tab}")
    if panel.count() != 1 or panel.get_attribute("role") != "tabpanel" or panel.is_hidden():
        errors.append(f"{tab}: selected tabpanel is not visible")
    return errors


def _keyboard_and_focus_contract(page: Any) -> list[str]:
    errors: list[str] = []
    first = page.locator("#v4-tab-research")
    first.click()
    first.focus()
    orientation = page.locator('.v4-rail-tabs[role="tablist"]').get_attribute("aria-orientation")
    key = "ArrowDown" if orientation == "vertical" else "ArrowRight"
    first.press(key)
    selected = page.locator('.v4-rail-tabs [role="tab"][aria-selected="true"]')
    if selected.count() != 1 or selected.get_attribute("id") != "v4-tab-history":
        errors.append(f"{key} does not move V4 tab selection from research to history")
        return errors
    focused = selected.evaluate(r"""element => {
        const style = getComputedStyle(element);
        const painted = color => {
            const probe = document.createElement('span');
            probe.style.color = color;
            probe.hidden = true;
            document.body.appendChild(probe);
            const resolved = getComputedStyle(probe).color;
            probe.remove();
            const alpha = resolved.match(/^rgba?\([^,]+,[^,]+,[^,]+(?:,\s*([0-9.]+))?\)$/);
            return !alpha || alpha[1] === undefined || Number(alpha[1]) > 0;
        };
        const outlinePainted = style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0
            && painted(style.outlineColor);
        const shadowPainted = style.boxShadow !== 'none' && !/(transparent|rgba?\([^)]*,\s*0(?:\.0+)?\))/i.test(style.boxShadow);
        return { active: document.activeElement === element, outlinePainted, shadowPainted,
                 outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth,
                 outlineColor: style.outlineColor, boxShadow: style.boxShadow };
    }""")
    selected.evaluate("element => element.blur()")
    blurred = selected.evaluate("""element => {
        const style = getComputedStyle(element);
        return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth,
                 outlineColor: style.outlineColor, boxShadow: style.boxShadow };
    }""")
    focus_outline = (focused["outlineStyle"], focused["outlineWidth"], focused["outlineColor"])
    blurred_outline = (blurred["outlineStyle"], blurred["outlineWidth"], blurred["outlineColor"])
    focus_shadow_delta = focused["shadowPainted"] and focused["boxShadow"] != blurred["boxShadow"]
    focus_outline_delta = focused["outlinePainted"] and focus_outline != blurred_outline
    if not focused["active"] or not (focus_outline_delta or focus_shadow_delta):
        errors.append("keyboard focus has no focus-only painted visible indicator on the V4 rail")
    return errors


def _overflow_contract(page: Any) -> list[str]:
    overflow = page.evaluate("""() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        bodyWidth: document.body ? document.body.scrollWidth : 0
    })""")
    if max(overflow["documentWidth"], overflow["bodyWidth"]) > overflow["viewportWidth"]:
        return [f"global horizontal overflow: {overflow}"]
    return []


def _quality_metrics(page: Any) -> dict[str, Any]:
    return page.evaluate("""() => {
        const rect = selector => {
            const element = document.querySelector(selector);
            if (!element) return null;
            const box = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return {
                width: Math.round(box.width * 100) / 100,
                height: Math.round(box.height * 100) / 100,
                display: style.display,
                gridTemplateColumns: style.gridTemplateColumns,
                overflowX: style.overflowX,
                position: style.position,
                top: style.top
            };
        };
        const resources = performance.getEntriesByType('resource');
        const longTasks = Array.isArray(window.__stomLongTasks) ? window.__stomLongTasks : null;
        return {
            documentHeight: document.documentElement.scrollHeight,
            documentWidth: document.documentElement.scrollWidth,
            viewportWidth: innerWidth,
            viewportHeight: innerHeight,
            domNodes: document.getElementsByTagName('*').length,
            svgCount: document.querySelectorAll('svg').length,
            canvasCount: document.querySelectorAll('canvas').length,
            resourceCount: resources.length,
            longTaskSupported: longTasks !== null,
            longTaskCount: longTasks ? longTasks.length : null,
            longTaskTotalMs: longTasks ? Math.round(longTasks.reduce((sum, value) => sum + value, 0) * 100) / 100 : null,
            longTaskMaxMs: longTasks && longTasks.length ? Math.round(Math.max(...longTasks) * 100) / 100 : 0,
            navigationDomContentLoadedMs: Math.round((performance.getEntriesByType('navigation')[0]?.domContentLoadedEventEnd || 0) * 100) / 100,
            computed: {
                resultFlow: rect('.bt-result-flow'),
                resultSection: rect('.bt-result-section'),
                primaryChart: rect('.bt-primary-chart-grid .chart-frame, .bt-primary-chart-grid .panel'),
                historyCode: rect('.v4-history .rp-code-block'),
                reportsBody: rect('.v4-reports-body'),
                reportsCatalog: rect('.v4-reports-list'),
                resultNav: rect('.bt-result-nav')
            }
        };
    }""")




def _axe_violations(page: Any) -> tuple[str, list[dict[str, Any]]]:
    result = page.evaluate("""async () => {
        if (!window.axe || typeof window.axe.run !== 'function') throw new Error('axe was not injected');
        return { version: window.axe.version, result: await window.axe.run(document, { resultTypes: ['violations'] }) };
    }""")
    version = result.get("version")
    if not isinstance(version, str) or not version:
        raise GateError("injected axe runtime did not report a version")
    violations = []
    for violation in result.get("result", {}).get("violations", []):
        violations.append({
            "id": str(violation.get("id", "unknown")),
            "impact": str(violation.get("impact") or "unknown"),
            "nodes": str(len(violation.get("nodes", []))),
            "targets": sorted({
                str(target)
                for node in violation.get("nodes", [])
                for target in node.get("target", [])
            })[:8],
        })
    return version, violations
def _assert_axe_runtime_version(runtime_version: str, installed_version: str) -> None:
    if runtime_version != installed_version:
        raise GateError(f"axe runtime version {runtime_version!r} does not match installed {installed_version!r}")



def _axe_errors(page: Any) -> list[dict[str, Any]]:
    _, violations = _axe_violations(page)
    return [violation for violation in violations if violation["impact"] in HARD_IMPACTS]


def _run_case(browser: Any, base_url: str, axe_source: Path, axe_version: str, tab: str, width: int,
              theme: str, motion: str, timeout_ms: int, app_bundle_sha256: str | None = None) -> dict[str, Any]:
    context: Any | None = None
    page: Any | None = None
    axe: list[dict[str, Any]] = []
    axe_errors: list[dict[str, Any]] = []
    errors: list[str] = []
    blocked_requests: list[str] = []
    blocked_websockets: list[str] = []
    observed_urls: list[str] = []
    redirect_urls: list[str] = []
    bundle_responses: list[tuple[str, bytes]] = []
    try:
        context = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=theme,
                                      reduced_motion=motion, service_workers="block")
        context.add_init_script(script=f"localStorage.setItem('stom_theme', {json.dumps(theme)});")
        context.add_init_script(script="""(() => {
            window.__stomLongTasks = [];
            if (typeof PerformanceObserver !== 'function') return;
            try {
                const observer = new PerformanceObserver(list => {
                    for (const entry of list.getEntries()) window.__stomLongTasks.push(entry.duration);
                });
                observer.observe({ type: 'longtask', buffered: true });
            } catch (error) {
                window.__stomLongTasks = null;
            }
        })();""")

        def validate_url(url: str, label: str) -> None:
            observed_urls.append(url)
            try:
                _assert_loopback_url(url)
            except GateError:
                errors.append(f"{label} is not loopback: {url}")

        def route_request(route: Any) -> None:
            request_url = route.request.url
            validate_url(request_url, "request")
            if errors:
                blocked_requests.append(request_url)
                route.abort()
                return
            route.continue_()

        def route_websocket(route: Any) -> None:
            websocket_url = route.url
            if _websocket_is_external(websocket_url):
                blocked_websockets.append(websocket_url)
                route.close(code=1008, reason="non-loopback WebSocket blocked")
                return
            route.connect_to_server()

        context.route("**/*", route_request)
        route_web_socket_method = getattr(context, "route_web_socket", None)
        if not callable(route_web_socket_method):
            raise GateError("Playwright route_web_socket support is required for this local gate")
        route_web_socket_method("**/*", route_websocket)
        page = context.new_page()
        page.on("request", lambda request: validate_url(request.url, "request"))
        page.on("websocket", lambda websocket: blocked_websockets.append(websocket.url)
                if _websocket_is_external(websocket.url) else None)

        def record_response(response: Any) -> None:
            validate_url(response.url, "response")
            location = response.headers.get("location")
            if location:
                try:
                    redirect_url = urljoin(response.url, location)
                    redirect_urls.append(redirect_url)
                    validate_url(redirect_url, "redirect")
                except ValueError:
                    errors.append(f"invalid redirect from {response.url}: {location}")
            if "/bundle/app.js" in urlsplit(response.url).path:
                bundle_responses.append((response.url, response.body()))

        page.on("response", record_response)
        page.goto(_with_tab(base_url, tab), wait_until="domcontentloaded", timeout=timeout_ms)
        page.locator(f"#v4-tab-{tab}").wait_for(state="visible", timeout=timeout_ms)
        page.wait_for_timeout(1000)
        validate_url(page.url, "final URL")
        errors += _tab_contract(page, tab)
        if not bundle_responses:
            errors.append("did not capture a loaded V4 app bundle response")
        elif len(bundle_responses) != 1:
            errors.append(f"expected exactly one V4 app bundle response, found {len(bundle_responses)}")
        else:
            bundle_url, bundle_bytes = bundle_responses[0]
            bundle_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
            validate_url(bundle_url, "app bundle response")
            if app_bundle_sha256 is not None and bundle_sha256 != app_bundle_sha256:
                errors.append("served V4 app bundle bytes do not match checkout bundle")
        page.add_script_tag(path=str(axe_source))
        runtime_axe_version, axe = _axe_violations(page)
        _assert_axe_runtime_version(runtime_axe_version, axe_version)
        axe_errors = [violation for violation in axe if violation["impact"] in HARD_IMPACTS]
        errors += _overflow_contract(page)
        errors += _keyboard_and_focus_contract(page)
        document_theme = page.locator("html").get_attribute("data-theme")
        theme_toggles = page.locator(".theme-toggle button[aria-pressed]").evaluate_all("""buttons =>
            buttons.map(button => ({
                label: button.textContent.trim().toLowerCase(),
                pressed: button.getAttribute('aria-pressed') === 'true',
                active: button.classList.contains('active')
            }))""")
        if document_theme != theme:
            errors.append(f"requested {theme} theme but document data-theme is {document_theme!r}")
        if theme_toggles != [
                {"label": "dark", "pressed": theme == "dark", "active": theme == "dark"},
                {"label": "light", "pressed": theme == "light", "active": theme == "light"},
        ]:
            errors.append(f"requested {theme} theme does not have exactly matching aria-pressed toggle")
        app_scripts = page.evaluate(r"""() => Array.from(document.scripts)
            .map(script => script.src).filter(src => /\/bundle\/app\.js(?:[?#]|$)/.test(src))""")
        if len(app_scripts) != 1:
            errors.append(f"expected exactly one V4 app bundle script, found {len(app_scripts)}")
        page.wait_for_timeout(0)
        _append_network_boundary_errors(errors, blocked_requests, blocked_websockets)
        quality_metrics = _quality_metrics(page)
        return {"tab": tab, "width": width, "theme": theme, "reducedMotion": motion == "reduce",
                "finalUrl": page.url, "appBundleUrl": app_scripts[0] if len(app_scripts) == 1 else None,
                "appBundleSha256": (hashlib.sha256(bundle_responses[0][1]).hexdigest()
                                    if len(bundle_responses) == 1 else None),
                "observedUrls": observed_urls, "redirectUrls": redirect_urls,
                "errors": errors, "axe": axe, "axeErrors": axe_errors,
                "qualityMetrics": quality_metrics,
                "passed": not errors and not axe_errors}
    except Exception as error:
        return {"tab": tab, "width": width, "theme": theme, "reducedMotion": motion == "reduce",
                "observedUrls": observed_urls, "redirectUrls": redirect_urls,
                "errors": errors + [f"browser boundary failed: {error}"], "axe": axe,
                "axeErrors": axe_errors, "passed": False}
    finally:
        if context is not None:
            context.close()


def run_gate(base_url: str, timeout_ms: int) -> dict[str, Any]:
    """Run all V4 tab, viewport, theme, and motion cases; all boundary errors fail closed."""
    _assert_loopback_url(base_url)
    axe_source = _assert_local_axe_source()
    axe_identity = _axe_identity(axe_source)
    app_identity = _app_bundle_identity()
    _assert_no_production_axe_import()
    try:
        from playwright.sync_api import sync_playwright
        playwright_version = importlib.metadata.version("playwright")
    except (ImportError, importlib.metadata.PackageNotFoundError) as error:
        raise GateError("Playwright Python package is required for this local gate") from error

    cases: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            chromium_version = browser.version
            for width in VIEWPORTS:
                for theme in THEMES:
                    for motion in MOTIONS:
                        for tab in TABS:
                            cases.append(_run_case(browser, base_url, axe_source, axe_identity["installedVersion"],
                                                   tab, width, theme, motion, timeout_ms, app_identity["sha256"]))
        finally:
            browser.close()
    failures = [case for case in cases if not case["passed"]]
    return {"gate": "dashboard-v5.8-accessibility", "status": "passed" if not failures else "failed",
            "baseUrl": base_url, "caseCount": len(cases), "failureCount": len(failures), "cases": cases,
            "identities": {"axe": axe_identity, "playwrightVersion": playwright_version,
                           "chromiumVersion": chromium_version, "appBundle": app_identity}}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Existing local dashboard URL; skips isolated server startup.")
    parser.add_argument("--output", type=Path, help="Write the deterministic JSON report to this file.")
    parser.add_argument("--timeout-ms", type=int, default=20_000, help="Per-page timeout (default: 20000).")
    parser.add_argument("--server-timeout-seconds", type=float, default=20.0,
                        help="Loopback server startup timeout (default: 20).")
    args = parser.parse_args(argv)
    if args.timeout_ms <= 0 or args.server_timeout_seconds <= 0:
        parser.error("timeouts must be positive")
    if args.base_url:
        try:
            _assert_loopback_url(args.base_url)
        except GateError as error:
            parser.error(str(error))
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report: dict[str, Any]
    try:
        if args.base_url:
            report = run_gate(args.base_url, args.timeout_ms)
        else:
            with _LocalDashboardServer(args.server_timeout_seconds) as base_url:
                report = run_gate(base_url, args.timeout_ms)
    except Exception as error:
        report = {"gate": "dashboard-v5.8-accessibility", "status": "failed", "baseUrl": args.base_url,
                  "caseCount": 0, "failureCount": 1, "cases": [], "errors": [str(error)]}
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
