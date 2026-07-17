from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

try:  # Pillow is optional at import time; the capture path requires it for sheets.
    from PIL import Image, ImageDraw, ImageStat
except Exception:  # pragma: no cover - depends on local toolchain.
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[1]
DEFAULT_VIEWPORTS = "1440x900,1920x1080,1280x720"

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

ALLOWED_AUTO_WS_PATHS = {"/ws"}

CATEGORY_WEIGHTS = {
    "taskOrientation": 20,
    "visualHierarchy": 15,
    "chartHeatmapReadability": 15,
    "workflowQuality": 15,
    "cognitiveLoad": 12,
    "safetyHierarchy": 10,
    "accessibilityResponsive": 8,
    "v2PreservationEvidence": 5,
}
SELECTOR_CONTRACTS = (
    "data-backtest-step=select|edit|validate|gated-run|analyze",
    "data-replay-step=source|strategy|preview|manual-start|investigate",
)


@dataclass(frozen=True)
class Scenario:
    id: str
    page: str
    label: str
    v2_path: str
    v3_path: str
    task: str
    primary_terms: tuple[str, ...]
    chart_terms: tuple[str, ...]
    workflow_terms: tuple[str, ...]


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "UX-S01",
        "condition",
        "Condition review",
        "/ui/evolution",
        "/ui/remodel/condition?demo=reference",
        "Review current generation, candidate quality, provenance, and gated export state.",
        ("조건식 AI", "현재 세대", "BEST", "Human"),
        ("Fitness", "Profit", "Equity", "백테스트"),
        ("Strategy Inspector", "Human Approval", "Export"),
    ),
    Scenario(
        "UX-S02",
        "process",
        "Process diagnose",
        "/ui/evolution/process",
        "/ui/remodel/process?demo=reference",
        "Diagnose current run state, process nodes, logs, queues, workers, and contracts.",
        ("프로세스", "Generation", "Backtest", "Scoring"),
        ("프로세스 맵", "node", "Queue", "Workers"),
        ("라이브 로그", "Route Boundary", "drilldown"),
    ),
    Scenario(
        "UX-S03",
        "history",
        "History compare",
        "/ui/evolution/records",
        "/ui/remodel/history?demo=reference",
        "Find a run, inspect result details, compare lineage, and confirm provenance.",
        ("히스토리", "Research Records", "ResultDetail", "Compare"),
        ("PnL", "Equity", "Lineage"),
        ("Compare", "Lineage", "Research Records"),
    ),
    Scenario(
        "UX-S04",
        "lab",
        "Lab heatmap",
        "/ui/evolution/lab",
        "/ui/remodel/lab?demo=reference",
        "Read factor heatmap, inspect selected cell meaning, and connect it to holdout proof.",
        ("연구실", "Edge Ratio", "변수 중요도", "검증"),
        ("히트맵", "상관관계", "누적 수익률"),
        ("변수 조합", "Holdout", "컨텍스트"),
    ),
    Scenario(
        "UX-S05",
        "workbench",
        "Workbench handoff",
        "/ui/evolution/workbench",
        "/ui/remodel/workbench?demo=reference",
        "Select a candidate, compare evidence, and understand review handoff state.",
        ("분석 워크벤치", "Hall of Fame", "후보", "리뷰"),
        ("히트맵", "누적 수익률", "IC"),
        ("History Compare", "Backtest Result Review", "리뷰 큐"),
    ),
    Scenario(
        "UX-S06",
        "audit",
        "Audit decision",
        "/ui/evolution/verdict",
        "/ui/remodel/audit?demo=reference",
        "Understand decision state, OOS evidence, append-only ledger, and human decision input.",
        ("결정 감사", "Append-Only", "PROMOTE", "OOS"),
        ("Sharpe", "OOS", "spark"),
        ("Human Decision", "결정 히스토리", "Ledger"),
    ),
    Scenario(
        "UX-S07",
        "backtest",
        "Backtest edit/validate",
        "/ui/backtest",
        "/ui/remodel/backtest?demo=reference",
        "Select strategy/data, inspect or edit buy/sell conditions, validate, then review gated run and results.",
        ("백테스트", "조건식", "매수", "매도"),
        ("에쿼티", "결과", "report"),
        ("실행 파라미터", "조건식 편집", "검증", "결과 분석"),
    ),
    Scenario(
        "UX-S08",
        "chart_replay",
        "Replay investigate signal",
        "/ui/chart-replay",
        "/ui/remodel/chart-replay?demo=reference",
        "Choose source/date/symbol, preview bars/signals, manually start replay, and inspect the signal log.",
        ("차트 리플레이", "데이터 소스", "재생", "종목"),
        ("리플레이 차트", "candle", "시장 미니맵"),
        ("재생 컨트롤", "전략 신호 로그", "/sim/ws"),
    ),
)

SCENARIOS_BY_PAGE = {scenario.page: scenario for scenario in SCENARIOS}
SCENARIOS_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}


@dataclass
class BrowserCapture:
    scenario_id: str
    page: str
    version: str
    viewport: str
    url: str
    status: int | None
    headers: dict[str, str]
    title: str
    text: str
    html: str
    scripts: list[str]
    requests: list[dict[str, Any]]
    websockets: list[str]
    console_errors: list[dict[str, str]]
    page_errors: list[str]
    screenshot: str
    dom_metrics: dict[str, Any]
    image_metrics: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_url(base_url: str, route_path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", route_path.lstrip("/"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def parse_viewports(value: str) -> list[tuple[int, int]]:
    viewports: list[tuple[int, int]] = []
    for raw_item in value.split(","):
        item = raw_item.strip().lower()
        if not item:
            continue
        match = re.fullmatch(r"(\d{3,5})x(\d{3,5})", item)
        if not match:
            raise ValueError(f"invalid viewport {raw_item!r}; expected WIDTHxHEIGHT")
        width = int(match.group(1))
        height = int(match.group(2))
        if width < 320 or height < 240:
            raise ValueError(f"viewport too small: {raw_item!r}")
        viewports.append((width, height))
    if not viewports:
        raise ValueError("at least one viewport is required")
    return viewports


def parse_pages(value: str | None) -> list[Scenario]:
    if not value:
        return list(SCENARIOS)
    selected: list[Scenario] = []
    unknown: list[str] = []
    for raw_item in value.split(","):
        key = raw_item.strip().replace("-", "_")
        if not key:
            continue
        scenario = SCENARIOS_BY_PAGE.get(key)
        if scenario is None:
            unknown.append(raw_item.strip())
        else:
            selected.append(scenario)
    if unknown:
        allowed = ", ".join(sorted(SCENARIOS_BY_PAGE))
        raise ValueError(f"unknown page(s): {unknown}; allowed: {allowed}")
    if not selected:
        raise ValueError("at least one page is required")
    return selected


def image_metrics(path: Path) -> dict[str, Any]:
    if Image is None or ImageStat is None:
        return {"available": False, "status": "SKIPPED", "reason": "Pillow unavailable"}
    with Image.open(path) as raw:
        image = raw.convert("RGB")
        width, height = image.size
        stat = ImageStat.Stat(image.resize((160, 90)).convert("L"))
        luma_stddev = float(stat.stddev[0])
        luma_mean = float(stat.mean[0])
    non_uniform = luma_stddev >= 2.0 and width >= 1000 and height >= 700
    return {
        "available": True,
        "status": "PASS" if non_uniform else "FAIL",
        "size": [width, height],
        "lumaMean": round(luma_mean, 2),
        "lumaStddev": round(luma_stddev, 2),
        "nonUniform": non_uniform,
    }


def is_forbidden_request(req: dict[str, Any]) -> str | None:
    parsed = urlparse(str(req.get("url") or ""))
    path = parsed.path
    method = str(req.get("method") or "GET").upper()
    kind = str(req.get("kind") or "request")
    if kind == "websocket" and path not in ALLOWED_AUTO_WS_PATHS:
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


def ratio(needles: tuple[str, ...], text: str) -> float:
    if not needles:
        return 100.0
    found = sum(1 for needle in needles if needle in text)
    return round(found / len(needles) * 100.0, 2)


def clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def capture_dom_metrics(page: Any, scenario: Scenario) -> dict[str, Any]:
    script = """
    ([scenarioPage, scenarioTerms]) => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const visible = Array.from(document.querySelectorAll('body *')).filter((el) => {
        const r = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return r.width > 2 && r.height > 2 && style.display !== 'none' && style.visibility !== 'hidden' && r.bottom > 0 && r.right > 0 && r.top < vh && r.left < vw;
      });
      const inFirstFold = visible.filter((el) => {
        const r = el.getBoundingClientRect();
        return r.top < vh && r.bottom > 0;
      });
      const focusable = inFirstFold.filter((el) => {
        const tag = el.tagName;
        return ['A','BUTTON','INPUT','SELECT','TEXTAREA'].includes(tag) || el.getAttribute('tabindex') !== null || el.getAttribute('role') === 'button';
      });
      const textOf = (el) => (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().replace(/\\s+/g, ' ');
      const panels = inFirstFold
        .map((el) => {
          const r = el.getBoundingClientRect();
          return { tag: el.tagName, cls: String(el.className || ''), text: textOf(el).slice(0, 90), x: r.x, y: r.y, w: r.width, h: r.height, area: r.width * r.height };
        })
        .filter((item) => item.area > 9000 && (item.cls.includes('panel') || item.cls.includes('grid') || item.tag === 'SECTION' || item.tag === 'MAIN'));
      const chartSelectors = 'svg, canvas, [data-ux-chart], [class*="chart"], [class*="heatmap"], [class*="replay"]';
      const chartLike = Array.from(document.querySelectorAll(chartSelectors))
        .map((el) => {
          const r = el.getBoundingClientRect();
          return { tag: el.tagName, cls: String(el.className || ''), text: textOf(el).slice(0, 100), w: Math.round(r.width), h: Math.round(r.height), area: Math.round(r.width * r.height), firstFold: r.top < vh && r.bottom > 0 };
        })
        .filter((item) => item.w > 20 && item.h > 20);
      const heatmaps = Array.from(document.querySelectorAll('[data-ux-heatmap], .heatmap'))
        .map((el) => {
          const r = el.getBoundingClientRect();
          return { text: textOf(el).slice(0, 140), w: Math.round(r.width), h: Math.round(r.height), cells: el.querySelectorAll('[data-heatmap-cell], .heat-cell').length, values: Array.from(el.querySelectorAll('[data-heatmap-cell], .heat-cell')).filter((cell) => textOf(cell).length > 0).length };
        });
      const text = document.body.innerText || '';
      const termHits = Object.fromEntries(scenarioTerms.map((term) => [term, text.includes(term)]));
      const primaryAction = Array.from(document.querySelectorAll('[data-ux-primary-action], button, a')).find((el) => scenarioTerms.some((term) => textOf(el).includes(term)));
      const primaryRect = primaryAction ? primaryAction.getBoundingClientRect() : null;
      const taskHeader = document.querySelector(`[data-ux-task-header="${scenarioPage}"]`) || document.querySelector('header') || document.querySelector('h1') || document.body;
      const taskRect = taskHeader.getBoundingClientRect();
      const maxChart = chartLike.reduce((best, item) => item.area > best.area ? item : best, {w: 0, h: 0, area: 0, text: '', firstFold: false});
      return {
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
        viewportWidth: vw,
        viewportHeight: vh,
        horizontalOverflow: document.documentElement.scrollWidth > vw + 3,
        visibleCount: visible.length,
        firstFoldElementCount: inFirstFold.length,
        focusableFirstFoldCount: focusable.length,
        panelCountFirstFold: panels.length,
        sameWeightPanelCount: panels.filter((item) => item.area > 18000 && item.area < 180000).length,
        taskHeaderTopRatio: Math.max(0, Math.round((taskRect.top / vh) * 1000) / 1000),
        primaryActionVisible: Boolean(primaryRect && primaryRect.top >= 0 && primaryRect.top < vh && primaryRect.left >= 0 && primaryRect.left < vw),
        primaryActionText: primaryAction ? textOf(primaryAction) : '',
        chartLikeCount: chartLike.length,
        maxChart,
        firstFoldChartCount: chartLike.filter((item) => item.firstFold).length,
        heatmaps,
        hasFutureTaskSelector: Boolean(document.querySelector(`[data-ux-task-header="${scenarioPage}"]`)),
        hasPrimaryCanvasSelector: Boolean(document.querySelector(`[data-ux-primary-canvas="${scenarioPage}"]`)),
        hasEvidenceDrawerSelector: Boolean(document.querySelector(`[data-ux-evidence-drawer="${scenarioPage}"]`)),
        dataContractMarkerCount: document.querySelectorAll('[data-contract-marker]').length,
        dataManualGateCount: document.querySelectorAll('[data-manual-gate]').length,
        dataSafetyBoundaryCount: document.querySelectorAll('[data-safety-boundary]').length,
        textLength: text.length,
        termHits,
        bodySample: text.slice(0, 700)
      };
    }
    """
    terms = sorted(set(scenario.primary_terms + scenario.chart_terms + scenario.workflow_terms))
    return page.evaluate(script, [scenario.page, terms])


def capture_pages(
    v2_base_url: str,
    v3_base_url: str,
    out_dir: Path,
    scenarios: list[Scenario],
    viewports: list[tuple[int, int]],
    timeout_ms: int,
) -> tuple[list[BrowserCapture], list[dict[str, Any]]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent.
        raise RuntimeError(f"Playwright is required for browser capture: {exc}") from exc

    captures: list[BrowserCapture] = []
    hard_failures: list[dict[str, Any]] = []
    screenshots_dir = out_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    def record_failure(failure: dict[str, Any]) -> None:
        hard_failures.append(failure)

    def capture_one(context: Any, scenario: Scenario, version: str, base_url: str, route_path: str, viewport_label: str) -> BrowserCapture:
        requests: list[dict[str, Any]] = []
        websockets: list[str] = []
        console_errors: list[dict[str, str]] = []
        page_errors: list[str] = []
        page = context.new_page()
        page.on("console", lambda msg: console_errors.append({"type": msg.type, "text": msg.text}) if msg.type in {"error", "assert"} else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("request", lambda req: requests.append({"kind": "request", "method": req.method, "url": req.url, "resourceType": req.resource_type}))
        page.on("websocket", lambda ws: websockets.append(ws.url))
        url = norm_url(base_url, route_path)
        response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(250)
        text = page.locator("body").inner_text(timeout=timeout_ms)
        html = page.content()
        scripts = page.evaluate("Array.from(document.scripts).map((s) => s.src || 'inline').filter(Boolean)")
        screenshot = screenshots_dir / f"{scenario.id}-{scenario.page}-{version}-{viewport_label}.png"
        page.screenshot(path=str(screenshot), full_page=False)
        dom_metrics = capture_dom_metrics(page, scenario)
        status = None if response is None else response.status
        headers = {} if response is None else {k.lower(): v for k, v in response.headers.items()}
        title = page.title()
        page.close()

        capture = BrowserCapture(
            scenario_id=scenario.id,
            page=scenario.page,
            version=version,
            viewport=viewport_label,
            url=url,
            status=status,
            headers=headers,
            title=title,
            text=text,
            html=html,
            scripts=list(scripts),
            requests=requests,
            websockets=websockets,
            console_errors=console_errors,
            page_errors=page_errors,
            screenshot=str(screenshot),
            dom_metrics=dom_metrics,
            image_metrics=image_metrics(screenshot),
        )

        for req in requests:
            reason = is_forbidden_request(req)
            if reason:
                record_failure({"scenarioId": scenario.id, "page": scenario.page, "version": version, "viewport": viewport_label, "url": req.get("url"), "method": req.get("method"), "reason": reason})
        for ws_url in websockets:
            reason = is_forbidden_request({"kind": "websocket", "method": "GET", "url": ws_url})
            if reason:
                record_failure({"scenarioId": scenario.id, "page": scenario.page, "version": version, "viewport": viewport_label, "url": ws_url, "method": "WEBSOCKET", "reason": reason})
        for marker in detect_forbidden_dom(html):
            record_failure({"scenarioId": scenario.id, "page": scenario.page, "version": version, "viewport": viewport_label, "url": url, "method": "DOM", "reason": f"forbidden_dom_marker:{marker}"})
        return capture

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for width, height in viewports:
            viewport_label = f"{width}x{height}"
            context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
            for scenario in scenarios:
                captures.append(capture_one(context, scenario, "v2", v2_base_url, scenario.v2_path, viewport_label))
                captures.append(capture_one(context, scenario, "v3", v3_base_url, scenario.v3_path, viewport_label))
            context.close()
        browser.close()
    return captures, hard_failures


def route_identity_failures(capture: BrowserCapture) -> list[str]:
    script_blob = "\n".join(capture.scripts + [req.get("url", "") for req in capture.requests])
    header_version = capture.headers.get("x-stom-dashboard-version", "")
    cache_control = capture.headers.get("cache-control", "")
    failures: list[str] = []
    if capture.status is None or capture.status >= 400:
        failures.append(f"bad_status:{capture.status}")
    if capture.version == "v2":
        if header_version != "v4-ops":
            failures.append(f"unexpected_v2_header:{header_version or 'missing'}")
        if "/ui/bundle/app.js" not in script_blob:
            failures.append("missing_v2_bundle")
        if "/ui/remodel/src/app.js" in script_blob:
            failures.append("v2_loaded_v3_remodel_asset")
    else:
        if header_version != "v3-remodel":
            failures.append(f"unexpected_v3_header:{header_version or 'missing'}")
        if "/ui/remodel/src/app.js" not in script_blob:
            failures.append("missing_v3_remodel_asset")
        if "/ui/bundle/app.js" in script_blob:
            failures.append("v3_loaded_v2_bundle")
        if "no-store" not in cache_control.lower():
            failures.append("v3_html_not_no_store")
    return failures


def score_capture(capture: BrowserCapture, scenario: Scenario) -> dict[str, Any]:
    metrics = capture.dom_metrics
    text = capture.text
    route_failures = route_identity_failures(capture)
    missing_safety = [] if capture.version == "v2" else [needle for needle in REQUIRED_V3_SAFETY_TEXT if needle not in text]
    image_ok = bool(capture.image_metrics.get("nonUniform"))
    term_scores = {
        "primary": ratio(scenario.primary_terms, text),
        "chart": ratio(scenario.chart_terms, text),
        "workflow": ratio(scenario.workflow_terms, text),
    }
    max_chart = metrics.get("maxChart") or {}
    max_chart_w = float(max_chart.get("w") or 0)
    max_chart_h = float(max_chart.get("h") or 0)
    heatmaps = metrics.get("heatmaps") or []
    heatmap_with_values = any(int(hm.get("values") or 0) > 0 for hm in heatmaps)
    heatmap_with_cells = any(int(hm.get("cells") or 0) > 0 for hm in heatmaps)
    task_orientation = clamp(
        term_scores["primary"] * 0.45
        + (100 if metrics.get("taskHeaderTopRatio", 1) <= 0.25 else 55) * 0.20
        + (100 if metrics.get("primaryActionVisible") else 45) * 0.20
        + (100 if int(metrics.get("focusableFirstFoldCount") or 0) <= 24 else 70) * 0.15
    )
    visual_hierarchy = clamp(
        (0 if metrics.get("horizontalOverflow") else 100) * 0.30
        + (100 if int(metrics.get("sameWeightPanelCount") or 0) <= 5 else 60) * 0.25
        + (100 if int(metrics.get("panelCountFirstFold") or 0) <= 10 else 65) * 0.20
        + (100 if image_ok else 0) * 0.25
    )
    chart_readability = clamp(
        term_scores["chart"] * 0.30
        + (100 if max_chart_w >= 360 and max_chart_h >= 180 else 55 if max_chart_w >= 260 and max_chart_h >= 120 else 25) * 0.35
        + (100 if not heatmap_with_cells or heatmap_with_values else 45) * 0.15
        + (100 if int(metrics.get("chartLikeCount") or 0) > 0 else 20) * 0.20
    )
    workflow_quality = clamp(term_scores["workflow"] * 0.70 + (100 if metrics.get("primaryActionVisible") else 50) * 0.30)
    cognitive_load = clamp(
        (100 if int(metrics.get("sameWeightPanelCount") or 0) <= 5 else 55) * 0.35
        + (100 if int(metrics.get("firstFoldElementCount") or 0) <= 240 else 70 if int(metrics.get("firstFoldElementCount") or 0) <= 420 else 45) * 0.35
        + (100 if text.count("Contract Matrix") <= 1 else 70) * 0.15
        + (100 if text.count("REFERENCE") <= 10 else 75) * 0.15
    )
    manual_gate_count = int(metrics.get("dataManualGateCount") or 0)
    manual_gate_score = 100 if capture.version == "v2" or manual_gate_count > 0 else 70
    safety_hierarchy = clamp(
        (100 if not missing_safety else max(0, 100 - len(missing_safety) * 16)) * 0.45
        + (100 if not route_failures else 0) * 0.35
        + manual_gate_score * 0.20
    )
    accessibility = clamp(
        (100 if int(metrics.get("focusableFirstFoldCount") or 0) > 0 else 40) * 0.30
        + (100 if int(metrics.get("chartLikeCount") or 0) == 0 or "active" in text.lower() or "status=" in text else 65) * 0.35
        + (0 if metrics.get("horizontalOverflow") else 100) * 0.35
    )
    v2_preservation = clamp((100 if not route_failures else 0) * 0.70 + (100 if image_ok else 0) * 0.30)
    category_scores = {
        "taskOrientation": task_orientation,
        "visualHierarchy": visual_hierarchy,
        "chartHeatmapReadability": chart_readability,
        "workflowQuality": workflow_quality,
        "cognitiveLoad": cognitive_load,
        "safetyHierarchy": safety_hierarchy,
        "accessibilityResponsive": accessibility,
        "v2PreservationEvidence": v2_preservation,
    }
    total = round(sum(category_scores[key] * CATEGORY_WEIGHTS[key] / 100.0 for key in CATEGORY_WEIGHTS), 2)
    hard_failures = [*route_failures]
    if missing_safety:
        hard_failures.append(f"missing_v3_safety_text:{','.join(missing_safety)}")
    if not image_ok:
        hard_failures.append("blank_or_unreadable_screenshot")
    if capture.console_errors or capture.page_errors:
        hard_failures.append("browser_errors")
    capped_total = min(total, 69.0) if any(failure.startswith(("unexpected_", "missing_v", "v2_loaded", "v3_loaded", "forbidden")) for failure in hard_failures) else total
    return {
        "scenarioId": capture.scenario_id,
        "page": capture.page,
        "version": capture.version,
        "viewport": capture.viewport,
        "url": capture.url,
        "statusCode": capture.status,
        "title": capture.title,
        "totalScore": round(capped_total, 2),
        "uncappedTotalScore": total,
        "categoryScores": category_scores,
        "categoryWeights": CATEGORY_WEIGHTS,
        "termScores": term_scores,
        "routeIdentityFailures": route_failures,
        "missingSafetyText": missing_safety,
        "hardFailures": hard_failures,
        "domMetrics": metrics,
        "imageMetrics": capture.image_metrics,
        "screenshot": capture.screenshot,
        "requests": capture.requests,
        "websockets": capture.websockets,
        "consoleErrors": capture.console_errors,
        "pageErrors": capture.page_errors,
        "htmlHash": sha256_text(capture.html),
        "textHash": sha256_text(capture.text),
    }


def scenario_delta_rows(score_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in score_rows:
        grouped.setdefault((row["scenarioId"], row["viewport"]), {})[row["version"]] = row
    delta_rows: list[dict[str, Any]] = []
    for (scenario_id, viewport), versions in sorted(grouped.items()):
        v2 = versions.get("v2")
        v3 = versions.get("v3")
        if not v2 or not v3:
            continue
        deltas = {
            key: round(v3["categoryScores"].get(key, 0.0) - v2["categoryScores"].get(key, 0.0), 2)
            for key in CATEGORY_WEIGHTS
        }
        delta_rows.append(
            {
                "scenarioId": scenario_id,
                "page": v3["page"],
                "viewport": viewport,
                "v2Total": v2["totalScore"],
                "v3Total": v3["totalScore"],
                "totalDelta": round(v3["totalScore"] - v2["totalScore"], 2),
                "categoryDelta": deltas,
            }
        )
    return delta_rows


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def validate_storyboards(path: Path | None, required_pages: set[str] | None = None) -> dict[str, Any]:
    if path is None:
        return {"status": "SKIPPED", "path": None, "failures": []}
    failures: list[dict[str, Any]] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "path": str(path), "failures": [{"reason": "invalid_json", "error": str(exc)}]}
    if not isinstance(payload, dict):
        failures.append({"reason": "root_not_object"})
        scenarios = []
    else:
        scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        failures.append({"reason": "scenarios_not_list"})
        scenarios = []
    seen_pages: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            failures.append({"reason": "scenario_not_object", "index": index})
            continue
        page = str(scenario.get("page") or "")
        scenario_id = str(scenario.get("id") or "")
        seen_pages.add(page)
        if page not in SCENARIOS_BY_PAGE:
            failures.append({"reason": "unknown_page", "scenarioId": scenario_id, "page": page})
        steps = scenario.get("steps")
        if not isinstance(steps, list) or not steps:
            failures.append({"reason": "missing_steps", "scenarioId": scenario_id, "page": page})
            continue
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                failures.append({"reason": "step_not_object", "scenarioId": scenario_id, "stepIndex": step_index})
                continue
            for required in ("id", "label", "route", "expectedObservation"):
                if not step.get(required):
                    failures.append({"reason": f"missing_{required}", "scenarioId": scenario_id, "stepIndex": step_index})
            selector_assertions = step.get("selectorAssertions")
            safety_assertions = step.get("safetyAssertions")
            rubric_observations = step.get("rubricObservations")
            if not isinstance(selector_assertions, list) or not selector_assertions:
                failures.append({"reason": "missing_selector_assertions", "scenarioId": scenario_id, "stepIndex": step_index})
            else:
                for selector in selector_assertions:
                    if not isinstance(selector, dict) or not selector.get("selector"):
                        failures.append({"reason": "invalid_selector_assertion", "scenarioId": scenario_id, "stepIndex": step_index})
            if not isinstance(safety_assertions, list) or not safety_assertions:
                failures.append({"reason": "missing_safety_assertions", "scenarioId": scenario_id, "stepIndex": step_index})
            if not isinstance(rubric_observations, list) or not rubric_observations:
                failures.append({"reason": "missing_rubric_observations", "scenarioId": scenario_id, "stepIndex": step_index})
            else:
                for observation in rubric_observations:
                    if not isinstance(observation, dict) or observation.get("category") not in CATEGORY_WEIGHTS:
                        failures.append({"reason": "invalid_rubric_observation", "scenarioId": scenario_id, "stepIndex": step_index})
    required_pages = required_pages or {"condition", "backtest", "chart_replay"}
    missing_pages = sorted(required_pages - seen_pages)
    for page in missing_pages:
        failures.append({"reason": "missing_required_storyboard_page", "page": page})
    return {
        "status": "PASS" if not failures else "FAIL",
        "path": str(path),
        "scenarioCount": len(scenarios),
        "pages": sorted(seen_pages),
        "requiredPages": sorted(required_pages),
        "failures": failures,
    }


def make_contact_sheet(out_dir: Path, score_rows: list[dict[str, Any]], scenarios: list[Scenario], viewports: list[tuple[int, int]]) -> dict[str, Any]:
    path = out_dir / "side-by-side-contact-sheet.png"
    if Image is None or ImageDraw is None:
        return {"status": "SKIPPED", "path": str(path), "reason": "Pillow unavailable"}
    first_viewport = f"{viewports[0][0]}x{viewports[0][1]}"
    row_h = 250
    label_h = 34
    thumb_w = 384
    thumb_h = 216
    width = thumb_w * 2
    height = (row_h + label_h) * len(scenarios)
    sheet = Image.new("RGB", (width, height), "#07131d")
    draw = ImageDraw.Draw(sheet)
    lookup: dict[tuple[str, str, str], dict[str, Any]] = {(row["scenarioId"], row["version"], row["viewport"]): row for row in score_rows}
    for index, scenario in enumerate(scenarios):
        y = index * (row_h + label_h)
        draw.rectangle((0, y, width, y + label_h), fill="#0b2030")
        draw.text((10, y + 9), f"{scenario.id} {scenario.page} | V2 default left vs explicit V3 right | {first_viewport}", fill="#d8eefc")
        for col, version in enumerate(("v2", "v3")):
            row = lookup.get((scenario.id, version, first_viewport))
            if not row:
                continue
            with Image.open(row["screenshot"]) as raw:
                image = raw.convert("RGB").resize((thumb_w, thumb_h))
            sheet.paste(image, (col * thumb_w, y + label_h))
            draw.text((col * thumb_w + 8, y + label_h + thumb_h + 3), f"{version.upper()} score {row['totalScore']}", fill="#d8eefc")
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return {"status": "PASS", "path": str(path), "viewport": first_viewport}


def build_scorecard(
    args: argparse.Namespace,
    scenarios: list[Scenario],
    viewports: list[tuple[int, int]],
    score_rows: list[dict[str, Any]],
    request_hard_failures: list[dict[str, Any]],
    storyboard_validation: dict[str, Any],
    contact_sheet: dict[str, Any],
) -> dict[str, Any]:
    delta_rows = scenario_delta_rows(score_rows)
    v3_scores = [row["totalScore"] for row in score_rows if row["version"] == "v3"]
    category_means = {
        version: {
            category: mean([row["categoryScores"].get(category, 0.0) for row in score_rows if row["version"] == version])
            for category in CATEGORY_WEIGHTS
        }
        for version in ("v2", "v3")
    }
    named_delta_categories = ["taskOrientation", "chartHeatmapReadability", "workflowQuality", "cognitiveLoad"]
    named_delta = mean([row["categoryDelta"].get(category, 0.0) for row in delta_rows for category in named_delta_categories])
    route_hard_failures = [
        {"scenarioId": row["scenarioId"], "page": row["page"], "version": row["version"], "viewport": row["viewport"], "failures": row["hardFailures"]}
        for row in score_rows
        if row["hardFailures"]
    ]
    threshold_failures: list[dict[str, Any]] = []
    if args.min_v3_score is not None and mean(v3_scores) < args.min_v3_score:
        threshold_failures.append({"reason": "min_v3_score_not_met", "expected": args.min_v3_score, "actual": mean(v3_scores)})
    if args.min_delta is not None and named_delta < args.min_delta:
        threshold_failures.append({"reason": "min_named_delta_not_met", "expected": args.min_delta, "actual": named_delta, "categories": named_delta_categories})
    storyboard_failures = storyboard_validation.get("failures") or []
    hard_failures = [*request_hard_failures, *route_hard_failures]
    status = "PASS" if not hard_failures and not threshold_failures and not storyboard_failures else "FAIL"
    return {
        "schemaVersion": 1,
        "kind": "dashboard-human-ux-rubric",
        "generatedAt": utc_now(),
        "status": status,
        "tranche": args.tranche,
        "thresholds": {"minV3Score": args.min_v3_score, "minDelta": args.min_delta, "viewports": [f"{w}x{h}" for w, h in viewports]},
        "routes": [
            {"scenarioId": scenario.id, "page": scenario.page, "label": scenario.label, "v2Route": scenario.v2_path, "v3Route": scenario.v3_path, "task": scenario.task}
            for scenario in scenarios
        ],
        "categoryWeights": CATEGORY_WEIGHTS,
        "categoryScoreMeans": category_means,
        "meanV3Score": mean(v3_scores),
        "meanNamedDelta": named_delta,
        "deltaCategories": named_delta_categories,
        "scoreRows": score_rows,
        "deltaRows": delta_rows,
        "hardFailures": hard_failures,
        "thresholdFailures": threshold_failures,
        "storyboardValidation": storyboard_validation,
        "artifacts": {"contactSheet": contact_sheet, "outDir": str(args.out)},
        "scoreDocumentation": {
            "purpose": "Tranche 0 human-centered UX baseline. Baseline may fail final UX thresholds; route/safety hard failures still fail.",
            "hardFailureCap": "Route/default/safety failures cap affected V3 score at 69 and fail the run.",
            "v2Delta": "Deltas are computed from the same route/scenario/viewport score rows for V2 and explicit V3.",
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture V2/V3 dashboard routes and score human-centered UX rubric evidence.")
    parser.add_argument("--v2-base-url", required=True)
    parser.add_argument("--v3-base-url", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--viewports", default=DEFAULT_VIEWPORTS)
    parser.add_argument("--pages", default=None, help="Comma-separated pages: condition,process,history,lab,workbench,audit,backtest,chart_replay")
    parser.add_argument("--tranche", default="baseline", choices=("baseline", "shared", "a", "b", "c", "final"))
    parser.add_argument("--min-v3-score", type=float, default=None)
    parser.add_argument("--min-delta", type=float, default=None)
    parser.add_argument("--storyboard", type=Path, default=None)
    parser.add_argument("--timeout-ms", type=int, default=20000)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        viewports = parse_viewports(args.viewports)
        scenarios = parse_pages(args.pages)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    args.out.mkdir(parents=True, exist_ok=True)
    captures, request_hard_failures = capture_pages(args.v2_base_url, args.v3_base_url, args.out, scenarios, viewports, args.timeout_ms)
    score_rows: list[dict[str, Any]] = []
    for capture in captures:
        score_rows.append(score_capture(capture, SCENARIOS_BY_ID[capture.scenario_id]))
    required_pages = {scenario.page for scenario in scenarios} & {"condition", "backtest", "chart_replay"}
    if args.storyboard is not None and not args.storyboard.is_absolute():
        args.storyboard = REPO / args.storyboard
    storyboard_validation = validate_storyboards(args.storyboard, required_pages=required_pages or None)
    contact_sheet = make_contact_sheet(args.out, score_rows, scenarios, viewports)
    write_json(args.out / "network-trace.json", {"generatedAt": utc_now(), "captures": [{"scenarioId": c.scenario_id, "page": c.page, "version": c.version, "viewport": c.viewport, "url": c.url, "requests": c.requests, "websockets": c.websockets} for c in captures]})
    scorecard = build_scorecard(args, scenarios, viewports, score_rows, request_hard_failures, storyboard_validation, contact_sheet)
    write_json(args.out / "scorecard.json", scorecard)
    print(f"Dashboard human UX rubric {scorecard['status']}")
    print(f"Mean V3 score: {scorecard['meanV3Score']}")
    print(f"Mean named V3-V2 delta: {scorecard['meanNamedDelta']}")
    print(f"Scorecard: {args.out / 'scorecard.json'}")
    if scorecard["hardFailures"]:
        print(f"Hard failures: {len(scorecard['hardFailures'])}")
    if scorecard["thresholdFailures"]:
        print(f"Threshold failures: {len(scorecard['thresholdFailures'])}")
    if storyboard_validation.get("failures"):
        print(f"Storyboard failures: {len(storyboard_validation['failures'])}")
    return 0 if scorecard["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
