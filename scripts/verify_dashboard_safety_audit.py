from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

try:  # Pillow is optional at import time; screenshot evidence requires it at runtime.
    from PIL import Image, ImageDraw, ImageStat
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]

REPO = Path(__file__).resolve().parents[1]
FRONTEND = REPO / "ai_strategy_loop" / "dashboard" / "frontend"

COMMON_SAFETY_TEXT = (
    "No Live Order",
    "No Broker Login",
    "No Account Trading",
    "Research Only",
    "Human Approval Gate",
    "Append-Only Audit",
)

AUDIT_TEXT = (
    "최종 전략 추출(Export) 승인과 결정 감사(Decision Audit)는 별개입니다.",
    "Evidence → Validation → Human Decision",
    "Append-Only",
    "PROMOTE",
    "Human Decision",
    "결정 히스토리",
    "dev/reference",
)

SOURCE_REQUIRED = {
    "ai_strategy_loop/dashboard/frontend/app.jsx": ("No Live Order", "No Broker Login", "No Account Trading", "Human Approval Gate", "Append-Only Audit"),
    "ai_strategy_loop/dashboard/frontend/remodel/src/app.js": ("No Live Order", "No Broker Login", "No Account Trading", "Decision Audit", "Append-Only"),
    "ai_strategy_loop/dashboard/frontend/cards.jsx": ("연구 산출물 승인", "실거래/주문/계좌/브로커 연동은 없습니다", "Human Approval Gate"),
    "ai_strategy_loop/dashboard/frontend/sim-tab-root.jsx": ("사용자 게이트", "autoStart", "applyDemo(\"latest\", true, false)"),
}

SOURCE_FILES = (
    FRONTEND / "app.jsx",
    FRONTEND / "cards.jsx",
    FRONTEND / "conn-backend.jsx",
    FRONTEND / "sim-tab-root.jsx",
    FRONTEND / "dashboard-inventory.jsx",
    FRONTEND / "bundle" / "app.js",
    FRONTEND / "remodel" / "src" / "app.js",
    FRONTEND / "remodel" / "remodel-bootstrap.js",
    FRONTEND / "remodel" / "styles" / "theme.css",
)
HTML_ENTRY_FILES = (
    FRONTEND / "index.html",
    FRONTEND / "lab.html",
    FRONTEND / "pro.html",
    FRONTEND / "verdict.html",
    FRONTEND / "STOM AI Dashboard.html",
)
EXTERNAL_ORIGIN_RE = re.compile(r"https?://(?!127\.0\.0\.1(?::\d+)?(?:[/'\"]|$)|localhost(?::\d+)?(?:[/'\"]|$))", re.I)


FORBIDDEN_SOURCE_PATTERNS = (
    ("legacy_live_deploy", re.compile(r"live-deploy", re.I)),
    ("legacy_operating_db_copy", re.compile(r"운영\s*DB|운영용|운영 시스템")),
    ("legacy_real_strategy_copy", re.compile(r"실전 전략|실거래 자동매매|즉시 사용 가능|덮어쓰기 됩니다")),
    ("hidden_live_action", re.compile(r"data-action=[\"'](?:live-order|broker-login|account-trade|replay-live-order)[\"']", re.I)),
    ("live_order_endpoint_literal", re.compile(r"(?<![A-Za-z0-9_-])[\"'`](?:/(?:orders?|live_order|broker/login|account/trade))(?:\b|[/?#\"'`])", re.I)),
    ("order_sender_symbol", re.compile(r"\b(?:place_order|send_order|submit_order|broker_login|account_trade)\b", re.I)),
)

RUNTIME_FORBIDDEN_PATHS = (
    "/bt/run",
    "/bt/strategy/validate",
    "/bt/strategy/delete",
    "/bt/extract_vars",
    "/bt/job/cancel",
    "/bt/job/meta",
    "/bt/portfolio",
    "/bt/ws_job",
    "/sim/ws",
    "/order",
    "/orders",
    "/broker/login",
    "/account/trade",
    "/live_order",
)
ALLOWED_WEBSOCKET_PATHS = {"/ws"}

SURFACES = (
    ("v2_condition", "v2", "/ui/evolution?dashboard_version=legacy", COMMON_SAFETY_TEXT + ("V3 Preview",)),
    ("v2_backtest", "v2", "/ui/backtest?dashboard_version=legacy", COMMON_SAFETY_TEXT + ("백테스트",)),
    ("v2_chart_replay", "v2", "/ui/chart-replay?dashboard_version=legacy", COMMON_SAFETY_TEXT + ("차트 리플레이",)),
    ("v3_condition", "v3", "/ui/remodel/condition", COMMON_SAFETY_TEXT + ("BEST / WINNER", "승인 전 내보내기 불가")),
    ("v3_audit", "v3", "/ui/remodel/audit", COMMON_SAFETY_TEXT + AUDIT_TEXT),
    ("v3_backtest", "v3", "/ui/remodel/backtest", COMMON_SAFETY_TEXT + ("LIVE READ-ONLY MODE", "/bt/* mutating endpoints are not auto-invoked")),
    ("v3_chart_replay", "v3", "/ui/remodel/chart-replay", COMMON_SAFETY_TEXT + ("LIVE READ-ONLY REPLAY MODE", "/sim/ws 수동 게이트")),
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify V2/V3 dashboard safety, audit, and local-only boundaries.")
    parser.add_argument("--v2-base-url", required=True, help="Running canonical/V2 dashboard base URL, e.g. http://127.0.0.1:8770")
    parser.add_argument("--v3-base-url", required=True, help="Running explicit V3 dashboard base URL, e.g. http://127.0.0.1:8776")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    return parser.parse_args(argv)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def norm_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def simplified_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path + (("?" + parsed.query) if parsed.query else "")

def is_local_request(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return host in {"", "127.0.0.1", "localhost"}



def text_coverage(required: tuple[str, ...], text: str) -> dict[str, Any]:
    missing = [needle for needle in required if needle not in text]
    return {"status": "PASS" if not missing else "FAIL", "required": list(required), "missing": missing, "score": round((1.0 - len(missing) / max(1, len(required))) * 100.0, 2)}


def screenshot_metrics(path: Path) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {"available": False, "status": "FAIL", "reason": "Pillow unavailable"}
    with Image.open(path) as raw:
        img = raw.convert("RGB")
        stat = ImageStat.Stat(img.resize((160, 90)).convert("L"))
        stddev = float(stat.stddev[0])
        non_uniform = img.size[0] >= 1000 and img.size[1] >= 700 and stddev >= 2.0
        return {"available": True, "status": "PASS" if non_uniform else "FAIL", "size": list(img.size), "lumaStddev": round(stddev, 2), "nonUniform": non_uniform}


def source_scan() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    required_failures: list[dict[str, Any]] = []
    scanned: list[str] = []
    for path in SOURCE_FILES:
        rel = path.relative_to(REPO).as_posix()
        if not path.exists():
            findings.append({"type": "missing_source", "file": rel})
            continue
        scanned.append(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern_id, pattern in FORBIDDEN_SOURCE_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end == -1:
                    line_end = len(text)
                excerpt = text[line_start:line_end].strip()
                findings.append({"type": pattern_id, "file": rel, "line": line_no, "excerpt": excerpt[:240]})
    for rel, needles in SOURCE_REQUIRED.items():
        path = REPO / rel
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        missing = [needle for needle in needles if needle not in text]
        if missing:
            required_failures.append({"file": rel, "missing": missing})
    for path in HTML_ENTRY_FILES:
        rel = path.relative_to(REPO).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        if path.exists() and rel not in scanned:
            scanned.append(rel)
        for match in EXTERNAL_ORIGIN_RE.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            findings.append({"type": "external_origin_entrypoint", "file": rel, "line": line_no, "excerpt": text[line_start:line_end].strip()[:240]})
    return {
        "schemaVersion": 1,
        "kind": "dashboard-source-safety-scan",
        "generatedAt": utc_now(),
        "status": "PASS" if not findings and not required_failures else "FAIL",
        "scannedFiles": scanned,
        "forbiddenPatterns": [pid for pid, _ in FORBIDDEN_SOURCE_PATTERNS],
        "findings": findings,
        "requiredSafetyCopyFailures": required_failures,
    }


def forbidden_request_reason(entry: dict[str, Any]) -> str | None:
    url = str(entry.get("url") or "")
    parsed = urlparse(url)
    if not is_local_request(url):
        return f"external_origin:{parsed.netloc}"
    path = parsed.path
    method = str(entry.get("method") or "GET").upper()
    kind = str(entry.get("kind") or "request")
    if kind == "websocket" and path not in ALLOWED_WEBSOCKET_PATHS:
        return f"forbidden_websocket:{path}"
    if method not in {"GET", "HEAD", "OPTIONS"}:
        return f"non_readonly_method:{method}:{path}"
    for needle in RUNTIME_FORBIDDEN_PATHS:
        if needle in path:
            return f"forbidden_runtime_path:{needle}"
    return None


def capture_surfaces(v2_base_url: str, v3_base_url: str, out_dir: Path, timeout_ms: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Playwright is required for safety audit capture: {exc}") from exc

    captures: list[dict[str, Any]] = []
    runtime_findings: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc)

    def ts() -> str:
        return datetime.now(timezone.utc).isoformat()

    def capture_one(context: Any, route_id: str, version: str, path: str, required: tuple[str, ...]) -> dict[str, Any]:
        base = v2_base_url if version == "v2" else v3_base_url
        url = norm_url(base, path)
        requests: list[dict[str, Any]] = []
        websockets: list[str] = []
        console_errors: list[dict[str, str]] = []
        page_errors: list[str] = []
        page = context.new_page()
        page.on("request", lambda req: requests.append({"kind": "request", "method": req.method, "url": req.url, "resourceType": req.resource_type}))
        page.on("websocket", lambda ws: websockets.append(ws.url))
        page.on("console", lambda msg: console_errors.append({"type": msg.type, "text": msg.text}) if msg.type in {"error", "assert"} else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2200)
        text = page.locator("body").inner_text(timeout=timeout_ms)
        coverage = text_coverage(required, text)
        screenshot = out_dir / f"{route_id}.png"
        page.screenshot(path=str(screenshot), full_page=False)
        buttons = page.locator("button").evaluate_all("els => els.map(e => (e.innerText || e.textContent || '').trim()).filter(Boolean).slice(0, 80)")
        inputs = page.locator("input, textarea, select").evaluate_all("els => els.map(e => ({tag:e.tagName.toLowerCase(), type:e.getAttribute('type') || '', placeholder:e.getAttribute('placeholder') || '', value:e.value || '', label:e.getAttribute('aria-label') || ''})).slice(0, 80)")
        html = page.content()
        for req in requests:
            reason = forbidden_request_reason(req)
            if reason:
                runtime_findings.append({"routeId": route_id, "version": version, "url": req.get("url"), "method": req.get("method"), "reason": reason})
        for ws_url in websockets:
            reason = forbidden_request_reason({"kind": "websocket", "method": "GET", "url": ws_url})
            if reason:
                runtime_findings.append({"routeId": route_id, "version": version, "url": ws_url, "method": "GET", "reason": reason})
        actions.append({"type": "navigate", "timestamp": ts(), "selector": "browser-url", "target": url, "status": "passed", "assertion": f"{route_id} loaded with status {None if response is None else response.status}"})
        actions.append({"type": "assert", "timestamp": ts(), "selector": "body", "target": route_id, "status": "passed" if coverage["status"] == "PASS" else "failed", "assertion": f"safety text missing={coverage['missing']}"})
        payload = {
            "routeId": route_id,
            "version": version,
            "path": path,
            "url": url,
            "statusCode": None if response is None else response.status,
            "headers": {} if response is None else {k.lower(): v for k, v in response.headers.items() if k.lower() in {"cache-control", "x-stom-dashboard-version"}},
            "title": page.title(),
            "textCoverage": coverage,
            "buttons": buttons,
            "inputs": inputs,
            "requests": [{"method": r.get("method"), "path": simplified_url(r.get("url", "")), "resourceType": r.get("resourceType")} for r in requests],
            "websockets": websockets,
            "consoleErrors": console_errors,
            "pageErrors": page_errors,
            "screenshot": str(screenshot),
            "imageMetrics": screenshot_metrics(screenshot),
            "htmlForbiddenMarkers": html_forbidden_markers(html),
            "bodyTextExcerpt": text[:12000],
        }
        page.close()
        return payload

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        for route_id, version, path, required in SURFACES:
            captures.append(capture_one(context, route_id, version, path, required))
        browser.close()

    dom_failures = [c for c in captures if c["textCoverage"]["status"] != "PASS" or c["htmlForbiddenMarkers"] or c["consoleErrors"] or c["pageErrors"] or not c["imageMetrics"].get("nonUniform")]
    dom_scan = {
        "schemaVersion": 1,
        "kind": "dashboard-dom-safety-scan",
        "generatedAt": utc_now(),
        "status": "PASS" if not dom_failures else "FAIL",
        "surfaces": captures,
        "failures": [{"routeId": c["routeId"], "missing": c["textCoverage"].get("missing"), "htmlForbiddenMarkers": c["htmlForbiddenMarkers"], "consoleErrors": c["consoleErrors"], "pageErrors": c["pageErrors"], "imageMetrics": c["imageMetrics"]} for c in dom_failures],
    }
    runtime_scan = {
        "schemaVersion": 1,
        "kind": "dashboard-runtime-network-safety-scan",
        "generatedAt": utc_now(),
        "status": "PASS" if not runtime_findings else "FAIL",
        "readOnly": True,
        "allowedWebSocketPaths": sorted(ALLOWED_WEBSOCKET_PATHS),
        "forbiddenRuntimePaths": list(RUNTIME_FORBIDDEN_PATHS),
        "findings": runtime_findings,
    }
    audit_capture = next(c for c in captures if c["routeId"] == "v3_audit")
    condition_capture = next(c for c in captures if c["routeId"] == "v3_condition")
    audit_required = {
        "auditPageHasAppendOnlyDecisionLedger": all(n in audit_capture["bodyTextExcerpt"] for n in ("Append-Only", "결정 히스토리", "Human Decision")),
        "auditExportSeparationCopyVisible": "최종 전략 추출(Export) 승인과 결정 감사(Decision Audit)는 별개입니다." in audit_capture["bodyTextExcerpt"],
        "conditionApprovalGateVisible": all(n in condition_capture["bodyTextExcerpt"] for n in ("Human Approval Gate", "승인 전 내보내기 불가")),
        "noAutoApprovalModalOnLoad": "Winner 승인 / Export · Human Confirm" not in condition_capture["bodyTextExcerpt"],
    }
    audit_gate = {
        "schemaVersion": 1,
        "kind": "dashboard-audit-export-separation",
        "generatedAt": utc_now(),
        "status": "PASS" if all(audit_required.values()) else "FAIL",
        "checks": audit_required,
    }
    transcript = {
        "schemaVersion": 1,
        "kind": "browser-automation",
        "tool": "playwright+verify_dashboard_safety_audit",
        "surface": "web",
        "verdict": "passed" if dom_scan["status"] == "PASS" and runtime_scan["status"] == "PASS" and audit_gate["status"] == "PASS" else "failed",
        "startedAt": started.isoformat(),
        "endedAt": utc_now(),
        "actions": actions,
    }
    return dom_scan, runtime_scan, audit_gate, transcript


def html_forbidden_markers(html: str) -> list[dict[str, str]]:
    markers: list[dict[str, str]] = []
    for marker in ('data-action="live-order"', 'data-action="broker-login"', 'data-action="account-trade"', 'data-action="replay-live-order"'):
        if marker in html:
            markers.append({"marker": marker})
    return markers


def make_contact_sheet(out_dir: Path, dom_scan: dict[str, Any]) -> dict[str, Any]:
    path = out_dir / "safety-contact-sheet.png"
    if Image is None or ImageDraw is None:
        return {"status": "FAIL", "path": str(path), "reason": "Pillow unavailable"}
    captures = dom_scan.get("surfaces", [])
    thumb_w, thumb_h = 480, 270
    label_h = 34
    cols = 2
    rows = (len(captures) + cols - 1) // cols
    sheet = Image.new("RGB", (thumb_w * cols, rows * (thumb_h + label_h)), "#07131d")
    draw = ImageDraw.Draw(sheet)
    for idx, capture in enumerate(captures):
        x = (idx % cols) * thumb_w
        y = (idx // cols) * (thumb_h + label_h)
        draw.rectangle((x, y, x + thumb_w, y + label_h), fill="#0b2030")
        draw.text((x + 8, y + 9), f"{capture['routeId']} · {capture['version']} · {capture['textCoverage']['status']}", fill="#d8eefc")
        with Image.open(capture["screenshot"]) as raw:
            img = raw.convert("RGB")
            img.thumbnail((thumb_w, thumb_h))
            canvas = Image.new("RGB", (thumb_w, thumb_h), "#020710")
            canvas.paste(img, ((thumb_w - img.width) // 2, (thumb_h - img.height) // 2))
        sheet.paste(canvas, (x, y + label_h))
    sheet.save(path)
    return {"status": "PASS", "path": str(path), "surfaceCount": len(captures), "layout": "2-column V2/V3 safety screenshot contact sheet"}


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = args.out if args.out.is_absolute() else REPO / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    source = source_scan()
    dom_scan, runtime_scan, audit_gate, transcript = capture_surfaces(args.v2_base_url, args.v3_base_url, out_dir, args.timeout_ms)
    contact = make_contact_sheet(out_dir, dom_scan)

    scores = {
        "sourceSafety": 100.0 if source["status"] == "PASS" else 0.0,
        "domSafety": 100.0 if dom_scan["status"] == "PASS" else 0.0,
        "runtimeNetwork": 100.0 if runtime_scan["status"] == "PASS" else 0.0,
        "auditExportSeparation": 100.0 if audit_gate["status"] == "PASS" else 0.0,
        "visualEvidence": 100.0 if contact["status"] == "PASS" else 0.0,
    }
    average = round(sum(scores.values()) / len(scores), 2)
    failures: list[dict[str, Any]] = []
    if source["status"] != "PASS":
        failures.append({"reason": "source_safety_failed", "detail": source})
    if dom_scan["status"] != "PASS":
        failures.append({"reason": "dom_safety_failed", "failures": dom_scan["failures"]})
    if runtime_scan["status"] != "PASS":
        failures.append({"reason": "runtime_network_failed", "findings": runtime_scan["findings"]})
    if audit_gate["status"] != "PASS":
        failures.append({"reason": "audit_export_separation_failed", "checks": audit_gate["checks"]})
    if contact["status"] != "PASS":
        failures.append({"reason": "contact_sheet_failed", "detail": contact})

    scorecard = {
        "schemaVersion": 1,
        "kind": "dashboard-safety-audit-scorecard",
        "generatedAt": utc_now(),
        "v2BaseUrl": args.v2_base_url,
        "v3BaseUrl": args.v3_base_url,
        "status": "PASS" if not failures else "FAIL",
        "averageSafetyScore": average,
        "scores": scores,
        "failures": failures,
    }

    write_json(out_dir / "source-safety-scan.json", source)
    write_json(out_dir / "dom-safety-scan.json", dom_scan)
    write_json(out_dir / "runtime-network-scan.json", runtime_scan)
    write_json(out_dir / "audit-export-separation.json", audit_gate)
    write_json(out_dir / "browser-transcript.json", transcript)
    write_json(out_dir / "safety-scorecard.json", scorecard)
    write_json(out_dir / "manifest.json", {
        "schemaVersion": 1,
        "kind": "dashboard-safety-audit-manifest",
        "generatedAt": utc_now(),
        "status": scorecard["status"],
        "artifacts": {
            "scorecard": str((out_dir / "safety-scorecard.json").resolve()),
            "sourceSafetyScan": str((out_dir / "source-safety-scan.json").resolve()),
            "domSafetyScan": str((out_dir / "dom-safety-scan.json").resolve()),
            "runtimeNetworkScan": str((out_dir / "runtime-network-scan.json").resolve()),
            "auditExportSeparation": str((out_dir / "audit-export-separation.json").resolve()),
            "browserTranscript": str((out_dir / "browser-transcript.json").resolve()),
            "contactSheet": str((out_dir / "safety-contact-sheet.png").resolve()),
        },
    })

    print(json.dumps({"status": scorecard["status"], "averageSafetyScore": average, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if scorecard["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
