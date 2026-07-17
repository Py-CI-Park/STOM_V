from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

try:  # Pillow is optional at import time; runtime visual evidence needs it.
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except Exception:  # pragma: no cover - exercised only when Pillow is absent.
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[1]
INVENTORY_DEFAULT = REPO / "artifacts" / "dashboard-v2-v3-inventory" / "v2-v3-inventory.json"
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"

REQUIRED_V3_SAFETY_TEXT = (
    "No Live Order",
    "No Broker Login",
    "No Account Trading",
    "Research Only",
    "Human Approval Gate",
    "Append-Only Audit",
)

FORBIDDEN_URL_PATTERNS = (
    "/bt/run",
    "/bt/ws_job",
    "/sim/ws",
    "/order",
    "/orders",
    "/broker/login",
    "/account/trade",
    "/live_order",
)

FORBIDDEN_DOM_MARKERS = (
    'data-action="live-order"',
    'data-action="broker-login"',
    'data-action="account-trade"',
    'data-action="replay-live-order"',
    "hidden production export",
)

ALLOWED_WS_PATHS = {"/ws"}


@dataclass(frozen=True)
class CompareRoute:
    id: str
    page: str
    v2_path: str
    v3_path: str
    v2_required: tuple[str, ...]
    v3_required: tuple[str, ...]
    inventory_pages: tuple[str, ...]


ROUTES: tuple[CompareRoute, ...] = (
    CompareRoute(
        "01_condition_ai",
        "condition",
        "/ui/evolution?dashboard_version=legacy",
        "/ui/remodel/condition?demo=reference",
        ("STOM AI", "조건식", "V3 Preview"),
        ("현재 세대 라이브 상태", "세대 테이블", "BEST / WINNER", "Human Approval", "Strategy Inspector"),
        ("condition", "shell"),
    ),
    CompareRoute(
        "02_process",
        "process",
        "/ui/evolution/process?dashboard_version=legacy",
        "/ui/remodel/process?demo=reference",
        ("프로세스", "백테스트", "V3 Preview"),
        ("프로세스 맵", "Generation", "Backtest", "Scoring", "Autopsy", "Repeat", "라이브 로그"),
        ("process", "shell"),
    ),
    CompareRoute(
        "03_history",
        "history",
        "/ui/evolution/records?dashboard_version=legacy",
        "/ui/remodel/history?demo=reference",
        ("히스토리", "Research", "V3 Preview"),
        ("실행/생성 히스토리", "Research Records", "ResultDetail", "Compare", "Lineage"),
        ("history", "shell"),
    ),
    CompareRoute(
        "04_lab",
        "lab",
        "/ui/evolution/lab?dashboard_version=legacy",
        "/ui/remodel/lab?demo=reference",
        ("연구실", "Edge", "V3 Preview"),
        ("Edge Ratio", "변수 중요도", "상관관계", "변수 조합", "검증 요약"),
        ("lab", "shell"),
    ),
    CompareRoute(
        "05_workbench",
        "workbench",
        "/ui/evolution/workbench?dashboard_version=legacy",
        "/ui/remodel/workbench?demo=reference",
        ("분석 워크벤치", "후보", "V3 Preview"),
        ("Hall of Fame 워크벤치", "History Compare", "Backtest Result Review", "후보 상세 분석", "리뷰 큐"),
        ("workbench", "shell"),
    ),
    CompareRoute(
        "06_decision_audit",
        "audit",
        "/ui/evolution/verdict?dashboard_version=legacy",
        "/ui/remodel/audit?demo=reference",
        ("결정 감사", "append", "V3 Preview"),
        ("결정 감사", "Append-Only", "PROMOTE", "OOS 성과 차이", "결정 히스토리"),
        ("audit", "shell"),
    ),
    CompareRoute(
        "07_backtest",
        "backtest",
        "/ui/backtest?dashboard_version=legacy",
        "/ui/remodel/backtest?demo=reference",
        ("백테스트", "조건식", "V3 Preview"),
        ("REFERENCE mode", "Backtest API Contract Matrix", "실행 파라미터", "최적화", "WFO", "스윕", "조건식 편집", "결과 분석", "독립 HTML 보고서"),
        ("backtest", "shell"),
    ),
    CompareRoute(
        "08_chart_replay",
        "chart_replay",
        "/ui/chart-replay?dashboard_version=legacy",
        "/ui/remodel/chart-replay?demo=reference",
        ("차트 리플레이", "V3 Preview"),
        ("데이터 소스", "재생 컨트롤", "실시간 리플레이 차트", "/sim/ws 수동 게이트", "전략 신호 로그"),
        ("chart_replay", "shell"),
    ),
)


@dataclass
class Capture:
    route_id: str
    version: str
    url: str
    status: int | None
    headers: dict[str, str]
    title: str
    text: str
    html_hash: str
    text_hash: str
    actions: list[str]
    buttons: list[str]
    forms: list[str]
    scripts: list[str]
    local_storage_keys: list[str]
    requests: list[dict[str, Any]]
    websockets: list[str]
    console_errors: list[dict[str, str]]
    page_errors: list[str]
    screenshot: str
    image_metrics: dict[str, Any]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare V2 default and explicit V3 dashboard routes with visual, DOM, route, and safety gates.")
    parser.add_argument("--v2-base-url", required=True, help="Running V2/default dashboard base URL, e.g. http://127.0.0.1:8770")
    parser.add_argument("--v3-base-url", required=True, help="Running V3/preview dashboard base URL, e.g. http://127.0.0.1:8776")
    parser.add_argument("--out", required=True, type=Path, help="Output artifact directory")
    parser.add_argument("--min-page-score", type=float, default=95.0)
    parser.add_argument("--min-average-score", type=float, default=97.0)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_DEFAULT)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def ratio_score(required: tuple[str, ...], text: str) -> tuple[float, list[str]]:
    missing = [needle for needle in required if needle not in text]
    score = (1.0 - len(missing) / max(1, len(required))) * 100.0
    return round(score, 2), missing


def image_metrics(path: Path) -> dict[str, Any]:
    if Image is None:
        return {"available": False, "status": "FAIL", "reason": "Pillow unavailable"}
    with Image.open(path) as raw:
        img = raw.convert("RGB")
        width, height = img.size
        stat = ImageStat.Stat(img.resize((160, 90)).convert("L"))
        stddev = float(stat.stddev[0])
        mean = float(stat.mean[0])
        non_uniform = stddev >= 2.0 and width >= 1000 and height >= 700
        return {
            "available": True,
            "status": "PASS" if non_uniform else "FAIL",
            "size": [width, height],
            "lumaMean": round(mean, 2),
            "lumaStddev": round(stddev, 2),
            "nonUniform": non_uniform,
        }


def simplified_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path + (("?" + parsed.query) if parsed.query else "")


def is_forbidden_request(req: dict[str, Any]) -> str | None:
    url = req.get("url", "")
    parsed = urlparse(url)
    path = parsed.path
    method = str(req.get("method") or "GET").upper()
    kind = str(req.get("kind") or "request")
    if kind == "websocket" and path not in ALLOWED_WS_PATHS:
        return f"forbidden_websocket:{path}"
    if method not in {"GET", "HEAD", "OPTIONS"}:
        return f"non_readonly_method:{method}:{path}"
    for pattern in FORBIDDEN_URL_PATTERNS:
        if pattern in path:
            return f"forbidden_url:{pattern}"
    return None


def detect_forbidden_dom(html: str) -> list[str]:
    lowered = html.lower()
    return [marker for marker in FORBIDDEN_DOM_MARKERS if marker.lower() in lowered]


def load_inventory(path: Path) -> dict[str, Any]:
    if not path.is_absolute():
        path = REPO / path
    if not path.is_file():
        return {"status": "MISSING", "path": str(path), "items": [], "failures": [{"reason": "missing_inventory"}]}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "path": str(path), "items": [], "failures": [{"reason": "invalid_inventory_json", "error": str(exc)}]}
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return {"status": "FAIL", "path": str(path), "items": [], "failures": [{"reason": "inventory_items_not_list"}]}
    return {"status": "PASS", "path": str(path), "items": items, "failures": []}


def inventory_page_score(inventory: dict[str, Any], pages: tuple[str, ...]) -> dict[str, Any]:
    if inventory.get("status") != "PASS":
        return {"score": 0.0, "missingPages": list(pages), "itemCount": 0, "status": "FAIL"}
    items = inventory.get("items", [])
    page_items = [item for item in items if item.get("page") in pages]
    by_page = {page: 0 for page in pages}
    for item in page_items:
        by_page[item.get("page")] = by_page.get(item.get("page"), 0) + 1
    missing_pages = [page for page, count in by_page.items() if count == 0]
    score = 100.0 if not missing_pages and len(page_items) >= max(4, len(pages) * 3) else max(0.0, 70.0 - 20.0 * len(missing_pages))
    return {"score": round(score, 2), "missingPages": missing_pages, "itemCount": len(page_items), "byPage": by_page, "status": "PASS" if score >= 95.0 else "FAIL"}


def route_matrix_entry(capture: Capture, expected_version: str, expected_asset: str, forbidden_asset: str) -> dict[str, Any]:
    script_blob = "\n".join(capture.scripts + [r.get("url", "") for r in capture.requests])
    header_version = capture.headers.get("x-stom-dashboard-version") or capture.headers.get("X-STOM-Dashboard-Version") or ""
    cache_control = capture.headers.get("cache-control") or capture.headers.get("Cache-Control") or ""
    violations: list[str] = []
    if capture.status is None or capture.status >= 400:
        violations.append(f"bad_status:{capture.status}")
    if expected_version == "v2" and header_version != "legacy":
        violations.append(f"unexpected_version_header:{header_version or 'missing'}")
    if expected_version == "v3-remodel" and header_version != "v3-remodel":
        violations.append(f"unexpected_version_header:{header_version or 'missing'}")
    if expected_asset not in script_blob:
        violations.append(f"missing_expected_asset:{expected_asset}")
    if forbidden_asset in script_blob:
        violations.append(f"forbidden_asset_loaded:{forbidden_asset}")
    if expected_version == "v3-remodel" and "no-store" not in cache_control.lower():
        violations.append("v3_html_not_no_store")
    if any(key.lower() in {"stom_dashboard_version", "dashboard_version", "stom_dashboard_profile"} for key in capture.local_storage_keys):
        violations.append("persistent_dashboard_selector_key")
    return {
        "routeId": capture.route_id,
        "version": expected_version,
        "url": capture.url,
        "statusCode": capture.status,
        "headerVersion": header_version,
        "cacheControl": cache_control,
        "title": capture.title,
        "expectedAsset": expected_asset,
        "forbiddenAsset": forbidden_asset,
        "scripts": capture.scripts,
        "localStorageKeys": capture.local_storage_keys,
        "violations": violations,
        "status": "PASS" if not violations else "FAIL",
    }


def score_route(case: CompareRoute, v2: Capture, v3: Capture, inventory: dict[str, Any], forbidden_failures: list[dict[str, Any]]) -> dict[str, Any]:
    v2_text_score, missing_v2 = ratio_score(case.v2_required, v2.text)
    v3_text_score, missing_v3 = ratio_score(case.v3_required, v3.text)
    v3_safety_score, missing_v3_safety = ratio_score(REQUIRED_V3_SAFETY_TEXT, v3.text)
    inv = inventory_page_score(inventory, case.inventory_pages)

    v2_matrix = route_matrix_entry(v2, "v2", "/ui/bundle/app.js", "/ui/remodel/src/app.js")
    v3_matrix = route_matrix_entry(v3, "v3-remodel", "/ui/remodel/src/app.js", "/ui/bundle/app.js")
    v2_identity_score = 100.0 - 20.0 * len(v2_matrix["violations"])
    v3_identity_score = 100.0 - 20.0 * len(v3_matrix["violations"])
    v2_identity_score = max(0.0, min(100.0, v2_identity_score))
    v3_identity_score = max(0.0, min(100.0, v3_identity_score))

    screenshot_score = 100.0 if v2.image_metrics.get("nonUniform") and v3.image_metrics.get("nonUniform") else 0.0
    dom_forbidden = detect_forbidden_dom(v2.html_hash + v3.html_hash)  # hash cannot contain markers; keep schema stable below.
    v2_dom_forbidden = detect_forbidden_dom(getattr(v2, "_html", "")) if hasattr(v2, "_html") else []
    v3_dom_forbidden = detect_forbidden_dom(getattr(v3, "_html", "")) if hasattr(v3, "_html") else []
    route_forbidden = [failure for failure in forbidden_failures if failure.get("routeId") == case.id]
    safety_network_score = 100.0 if not route_forbidden and not v2_dom_forbidden and not v3_dom_forbidden else 0.0

    corrected = (
        v2_identity_score * 0.18
        + v2_text_score * 0.10
        + v3_identity_score * 0.22
        + v3_text_score * 0.18
        + v3_safety_score * 0.14
        + inv["score"] * 0.10
        + safety_network_score * 0.05
        + screenshot_score * 0.03
    )
    hard_failures: list[str] = []
    if v2_matrix["violations"]:
        hard_failures.append("v2_route_identity_violation")
    if v3_matrix["violations"]:
        hard_failures.append("v3_route_identity_violation")
    if missing_v2:
        hard_failures.append("missing_v2_required_text")
    if missing_v3:
        hard_failures.append("missing_v3_required_text")
    if missing_v3_safety:
        hard_failures.append("missing_v3_safety_text")
    if inv["status"] != "PASS":
        hard_failures.append("inventory_page_coverage_missing")
    if route_forbidden or v2_dom_forbidden or v3_dom_forbidden:
        hard_failures.append("forbidden_network_or_dom")
    if screenshot_score < 100.0:
        hard_failures.append("blank_or_unreadable_screenshot")
    if v2.console_errors or v2.page_errors or v3.console_errors or v3.page_errors:
        hard_failures.append("browser_errors")
    if hard_failures:
        corrected = min(corrected, 94.0)
    return {
        "id": case.id,
        "page": case.page,
        "v2Route": case.v2_path,
        "v3Route": case.v3_path,
        "scores": {
            "v2Identity": round(v2_identity_score, 2),
            "v2RequiredText": v2_text_score,
            "v3Identity": round(v3_identity_score, 2),
            "v3RequiredText": v3_text_score,
            "v3SafetyText": v3_safety_score,
            "inventoryCoverage": inv["score"],
            "safetyNetworkDom": safety_network_score,
            "screenshotEvidence": screenshot_score,
            "totalCorrectedScore": round(corrected, 2),
        },
        "missing": {
            "v2RequiredText": missing_v2,
            "v3RequiredText": missing_v3,
            "v3SafetyText": missing_v3_safety,
        },
        "inventoryCoverage": inv,
        "routeMatrix": {"v2": v2_matrix, "v3": v3_matrix},
        "forbiddenFindings": route_forbidden,
        "hardFailures": hard_failures,
        "status": "PASS" if not hard_failures else "FAIL",
    }


def make_contact_sheet(out_dir: Path, cases: tuple[CompareRoute, ...]) -> dict[str, Any]:
    path = out_dir / "side-by-side-contact-sheet.png"
    if Image is None or ImageDraw is None:
        return {"status": "FAIL", "path": str(path), "reason": "Pillow unavailable"}
    thumb_w, thumb_h = 384, 216
    label_h = 34
    width = thumb_w * 2
    height = (thumb_h + label_h) * len(cases)
    sheet = Image.new("RGB", (width, height), "#07131d")
    draw = ImageDraw.Draw(sheet)
    for idx, case in enumerate(cases):
        y = idx * (thumb_h + label_h)
        draw.rectangle((0, y, width, y + label_h), fill="#0b2030")
        draw.text((10, y + 9), f"{case.id} {case.page}  |  V2 default (left) vs V3 explicit (right)", fill="#d8eefc")
        for col, version in enumerate(("v2", "v3")):
            shot = out_dir / f"{case.id}-{version}.png"
            with Image.open(shot) as raw:
                img = raw.convert("RGB").resize((thumb_w, thumb_h))
            sheet.paste(img, (col * thumb_w, y + label_h))
    sheet.save(path)
    return {"status": "PASS", "path": str(path), "layout": "Each row shows V2 default left and explicit V3 right at 384x216."}


def capture_pages(
    v2_base: str,
    v3_base: str,
    out_dir: Path,
    timeout_ms: int,
) -> tuple[dict[str, dict[str, Capture]], list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent.
        raise RuntimeError(f"Playwright is required for capture: {exc}") from exc

    captures: dict[str, dict[str, Capture]] = {}
    all_forbidden: list[dict[str, Any]] = []
    legacy_observations: list[dict[str, Any]] = []

    def record_forbidden(finding: dict[str, Any]) -> None:
        if finding.get("version") == "v2" and "/sim/ws" in str(finding.get("reason", "")):
            finding["classification"] = "legacy_v2_observation_not_v3_blocker"
            legacy_observations.append(finding)
        else:
            all_forbidden.append(finding)

    def do_capture(context: Any, case: CompareRoute, version: str, base: str, route_path: str) -> Capture:
        request_log: list[dict[str, Any]] = []
        websockets: list[str] = []
        console_errors: list[dict[str, str]] = []
        page_errors: list[str] = []
        page = context.new_page()
        page.on("console", lambda msg: console_errors.append({"type": msg.type, "text": msg.text}) if msg.type in {"error", "assert"} else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("request", lambda req: request_log.append({"kind": "request", "method": req.method, "url": req.url, "resourceType": req.resource_type}))
        page.on("websocket", lambda ws: websockets.append(ws.url))
        url = norm_url(base, route_path)
        response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(250)
        body = page.locator("body")
        text = body.inner_text(timeout=timeout_ms)
        html = page.content()
        actions = page.locator("[data-action]").evaluate_all("els => els.map(el => el.getAttribute('data-action')).filter(Boolean)")
        buttons = page.locator("button").evaluate_all("els => els.map(el => (el.innerText || el.getAttribute('aria-label') || '').trim()).filter(Boolean).slice(0, 80)")
        forms = page.locator("form").evaluate_all("els => els.map((el, idx) => el.getAttribute('aria-label') || el.id || `form-${idx}`)")
        scripts = page.evaluate("Array.from(document.scripts).map(s => s.src || 'inline').filter(Boolean)")
        local_keys = page.evaluate("Object.keys(window.localStorage || {})")
        shot = out_dir / f"{case.id}-{version}.png"
        page.screenshot(path=str(shot), full_page=False)
        status = None if response is None else response.status
        headers = {} if response is None else {k.lower(): v for k, v in response.headers.items()}
        title = page.title()
        page.close()
        cap = Capture(
            route_id=case.id,
            version=version,
            url=url,
            status=status,
            headers=headers,
            title=title,
            text=text,
            html_hash=sha256_text(html),
            text_hash=sha256_text(text),
            actions=list(actions),
            buttons=list(buttons),
            forms=list(forms),
            scripts=list(scripts),
            local_storage_keys=list(local_keys),
            requests=request_log,
            websockets=websockets,
            console_errors=console_errors,
            page_errors=page_errors,
            screenshot=str(shot),
            image_metrics=image_metrics(shot),
        )
        setattr(cap, "_html", html)
        for req in request_log:
            reason = is_forbidden_request(req)
            if reason:
                record_forbidden({"routeId": case.id, "version": version, "url": req.get("url"), "method": req.get("method"), "reason": reason})
        for ws_url in websockets:
            reason = is_forbidden_request({"kind": "websocket", "method": "GET", "url": ws_url})
            if reason:
                record_forbidden({"routeId": case.id, "version": version, "url": ws_url, "method": "WEBSOCKET", "reason": reason})
        for marker in detect_forbidden_dom(html):
            record_forbidden({"routeId": case.id, "version": version, "url": url, "method": "DOM", "reason": f"forbidden_dom_marker:{marker}"})
        return cap

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        for case in ROUTES:
            captures[case.id] = {
                "v2": do_capture(context, case, "v2", v2_base, case.v2_path),
                "v3": do_capture(context, case, "v3", v3_base, case.v3_path),
            }
        browser.close()
    return captures, all_forbidden, legacy_observations


def capture_selector_matrix(v2_base: str, v3_base: str, timeout_ms: int) -> list[dict[str, Any]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Playwright is required for selector matrix: {exc}") from exc

    selector_cases = [
        {"id": "default_root_v4_ops", "base": v2_base, "path": "/ui/evolution", "expectedStatus": 200, "expectedHeader": "v4-ops", "expectedAsset": "/ui/bundle/app.js", "forbiddenAsset": "/ui/remodel/src/app.js"},
        {"id": "v2_forced_legacy", "base": v2_base, "path": "/ui/evolution?dashboard_version=legacy", "expectedStatus": 200, "expectedHeader": "legacy", "expectedAsset": "/ui/bundle/app.js", "forbiddenAsset": "/ui/remodel/src/app.js"},
        {"id": "v3_query_preview", "base": v3_base, "path": "/ui/evolution?dashboard_version=v3", "expectedStatus": 200, "expectedHeader": "v3-remodel", "expectedAsset": "/ui/remodel/src/app.js", "forbiddenAsset": "/ui/bundle/app.js"},
        {"id": "v3_hard_remodel", "base": v3_base, "path": "/ui/remodel/condition", "expectedStatus": 200, "expectedHeader": "v3-remodel", "expectedAsset": "/ui/remodel/src/app.js", "forbiddenAsset": "/ui/bundle/app.js"},
        {"id": "unknown_remodel_404", "base": v3_base, "path": "/ui/remodel/not-a-real-dashboard-route", "expectedStatus": 404, "expectedHeader": "", "expectedAsset": "", "forbiddenAsset": "/ui/bundle/app.js"},
    ]
    rows: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        for spec in selector_cases:
            page = context.new_page()
            requests: list[str] = []
            page.on("request", lambda req, sink=requests: sink.append(req.url))
            url = norm_url(spec["base"], spec["path"])
            response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(150)
            scripts = page.evaluate("Array.from(document.scripts).map(s => s.src || 'inline').filter(Boolean)") if response and response.status < 500 else []
            header = "" if response is None else response.headers.get("x-stom-dashboard-version", "")
            status = None if response is None else response.status
            asset_blob = "\n".join(scripts + requests)
            violations = []
            if status != spec["expectedStatus"]:
                violations.append(f"status:{status}:expected:{spec['expectedStatus']}")
            if spec["expectedHeader"] and header != spec["expectedHeader"]:
                violations.append(f"header:{header or 'missing'}:expected:{spec['expectedHeader']}")
            if spec["expectedAsset"] and spec["expectedAsset"] not in asset_blob:
                violations.append(f"missing_asset:{spec['expectedAsset']}")
            if spec["forbiddenAsset"] and spec["forbiddenAsset"] in asset_blob:
                violations.append(f"forbidden_asset:{spec['forbiddenAsset']}")
            rows.append({
                "id": spec["id"],
                "url": url,
                "statusCode": status,
                "expectedStatus": spec["expectedStatus"],
                "headerVersion": header,
                "expectedHeader": spec["expectedHeader"],
                "scripts": scripts,
                "requestPaths": [simplified_url(item) for item in requests],
                "violations": violations,
                "status": "PASS" if not violations else "FAIL",
            })
            page.close()
        browser.close()
    return rows


def compact_capture(cap: Capture) -> dict[str, Any]:
    return {
        "routeId": cap.route_id,
        "version": cap.version,
        "url": cap.url,
        "statusCode": cap.status,
        "headers": {k: cap.headers.get(k) for k in ("x-stom-dashboard-version", "cache-control", "pragma", "expires") if k in cap.headers},
        "title": cap.title,
        "textHash": cap.text_hash,
        "htmlHash": cap.html_hash,
        "textLength": len(cap.text),
        "actions": cap.actions,
        "buttons": cap.buttons,
        "forms": cap.forms,
        "scripts": cap.scripts,
        "localStorageKeys": cap.local_storage_keys,
        "requests": [{"method": r.get("method"), "path": simplified_url(r.get("url", "")), "resourceType": r.get("resourceType")} for r in cap.requests],
        "websockets": cap.websockets,
        "consoleErrors": cap.console_errors,
        "pageErrors": cap.page_errors,
        "screenshot": cap.screenshot,
        "imageMetrics": cap.image_metrics,
    }


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = args.out if args.out.is_absolute() else REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory = load_inventory(args.inventory)
    captures, forbidden_findings, legacy_forbidden_observations = capture_pages(args.v2_base_url, args.v3_base_url, out_dir, args.timeout_ms)
    selector_matrix = capture_selector_matrix(args.v2_base_url, args.v3_base_url, args.timeout_ms)
    contact_sheet = make_contact_sheet(out_dir, ROUTES)

    page_rows = []
    route_matrix_rows = []
    dom_inventory_rows = []
    for case in ROUTES:
        v2 = captures[case.id]["v2"]
        v3 = captures[case.id]["v3"]
        row = score_route(case, v2, v3, inventory, forbidden_findings)
        page_rows.append(row)
        route_matrix_rows.extend([row["routeMatrix"]["v2"], row["routeMatrix"]["v3"]])
        dom_inventory_rows.append({"id": case.id, "page": case.page, "v2": compact_capture(v2), "v3": compact_capture(v3)})

    route_matrix_rows.extend(selector_matrix)
    route_failures = [row for row in route_matrix_rows if row.get("status") != "PASS"]
    forbidden_scan = {
        "generatedAt": utc_now(),
        "status": "PASS" if not forbidden_findings else "FAIL",
        "readOnly": True,
        "forbiddenUrlPatterns": list(FORBIDDEN_URL_PATTERNS),
        "allowedWebSocketPaths": sorted(ALLOWED_WS_PATHS),
        "findings": forbidden_findings,
        "legacyV2Observations": legacy_forbidden_observations,
    }
    average_score = round(sum(row["scores"]["totalCorrectedScore"] for row in page_rows) / len(page_rows), 2)
    failures: list[dict[str, Any]] = []
    for row in page_rows:
        if row["scores"]["totalCorrectedScore"] < args.min_page_score:
            failures.append({"id": row["id"], "reason": "below_min_page_score", "score": row["scores"]["totalCorrectedScore"], "minimum": args.min_page_score})
        if row["hardFailures"]:
            failures.append({"id": row["id"], "reason": "hard_failures", "failures": row["hardFailures"]})
    if average_score < args.min_average_score:
        failures.append({"reason": "below_min_average_score", "score": average_score, "minimum": args.min_average_score})
    if route_failures:
        failures.append({"reason": "route_version_matrix_failed", "count": len(route_failures)})
    if forbidden_scan["status"] != "PASS":
        failures.append({"reason": "forbidden_network_scan_failed", "count": len(forbidden_findings)})
    if contact_sheet["status"] != "PASS":
        failures.append({"reason": "contact_sheet_failed", "detail": contact_sheet})
    if inventory.get("status") != "PASS":
        failures.append({"reason": "inventory_unavailable", "detail": inventory.get("failures")})

    scorecard = {
        "schemaVersion": 1,
        "kind": "dashboard-v2-v3-compare-scorecard",
        "generatedAt": utc_now(),
        "basis": "V2 default routes versus explicit V3 remodel routes captured with Playwright at 1920x1080; scores assert selectable version ownership, DOM/feature inventory coverage, V3 safety text, no forbidden network calls, and non-uniform visual evidence.",
        "baseUrls": {"v2": args.v2_base_url, "v3": args.v3_base_url},
        "thresholds": {"minPageScore": args.min_page_score, "minAverageScore": args.min_average_score},
        "averageCorrectedTotalScore": average_score,
        "rows": page_rows,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "scoreDocumentation": {
            "v2Identity": "Legacy route (?dashboard_version=legacy) returns x-stom-dashboard-version=legacy, loads /ui/bundle/app.js, and does not load V3 remodel assets. Default routes serve the promoted V4 graph-first shell (v4-ops).",
            "v3Identity": "Explicit V3 route returns x-stom-dashboard-version=v3-remodel, no-store HTML, loads /ui/remodel/src/app.js, and does not load ops bundle.",
            "totalCorrectedScore": "0.18 V2 identity + 0.10 V2 text + 0.22 V3 identity + 0.18 V3 text + 0.14 V3 safety + 0.10 inventory + 0.05 safety/network + 0.03 screenshot; hard failures cap below threshold.",
        },
    }

    manifest = {
        "schemaVersion": 1,
        "kind": "dashboard-v2-v3-compare-manifest",
        "generatedAt": utc_now(),
        "readOnly": True,
        "artifacts": {
            "compareScorecard": str((out_dir / "compare-scorecard.json").resolve()),
            "routeVersionMatrix": str((out_dir / "route-version-matrix.json").resolve()),
            "domInventory": str((out_dir / "dom-inventory.json").resolve()),
            "forbiddenNetworkScan": str((out_dir / "forbidden-network-scan.json").resolve()),
            "contactSheet": str((out_dir / "side-by-side-contact-sheet.png").resolve()),
        },
        "screenshots": {case.id: {"v2": str((out_dir / f"{case.id}-v2.png").resolve()), "v3": str((out_dir / f"{case.id}-v3.png").resolve())} for case in ROUTES},
        "status": scorecard["status"],
    }

    write_json(out_dir / "route-version-matrix.json", {"generatedAt": utc_now(), "rows": route_matrix_rows, "failures": route_failures, "status": "PASS" if not route_failures else "FAIL"})
    write_json(out_dir / "dom-inventory.json", {"generatedAt": utc_now(), "rows": dom_inventory_rows, "inventorySource": inventory.get("path"), "status": "PASS"})
    write_json(out_dir / "forbidden-network-scan.json", forbidden_scan)
    write_json(out_dir / "compare-scorecard.json", scorecard)
    write_json(out_dir / "manifest.json", manifest)

    print(json.dumps({"status": scorecard["status"], "averageCorrectedTotalScore": average_score, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if scorecard["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
